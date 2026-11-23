"""One shared pose detector + ByteTrack tracker per camera.

ADAPTED from SMC backend/app/person_detection.py (SharedPersonDetection). That
class is the proven worker architecture this module reuses unchanged in shape:

  - one `_Cam` per camera, each with its OWN model instance and a single-thread
    executor, so ultralytics' persistent ByteTrack state (persist=True) is per
    camera: track ids and histories can never leak between cameras;
  - a frame is dropped (never queued) while the previous one is still being
    processed, so a slow camera sheds load instead of building latency;
  - nothing runs for a camera nobody wants (wants() returns 0);
  - failures pause the camera on a backoff and rebuild the model after repeated
    failures (resilience.FeatureHealth), instead of silently stopping forever;
  - consumers register(name, wants_fps, deliver) and are fed on a fixed
    schedule from the SAME inference pass.

Why it could not be reused as-is (and why this is not a second pipeline):
  1. person_detection hard-codes yolov8n.pt and returns only boxes. Fall analysis
     needs the 17 COCO keypoints, which only a pose model produces.
  2. A pose model ALSO detects and tracks people (box + id + keypoints in one
     forward pass), so this replaces SMC's person detector rather than running
     beside it: exactly ONE inference per processed frame per camera, no
     separate person-detection pass followed by a pose pass.
  3. The detection rate, input size and confidence are runtime settings here
     (Settings > Processing), and SMC's consumers (footfall, staff, intrusion)
     do not exist in this module.

The consumer registry is kept so a future temporal classifier (ST-GCN etc.) can be
fed from the same inference without a second model run.
"""
from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
from pathlib import Path

import numpy as np

from falldet import config
from falldet.core import resilience, settings_store

log = logging.getLogger("pose_worker")


def ensure_weights() -> Path:
    """Path to the pose weights in MODEL_DIR, downloading them once (ultralytics'
    asset downloader) if absent."""
    path = Path(config.MODEL_DIR) / config.POSE_MODEL
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    from ultralytics.utils.downloads import attempt_download_asset

    log.info("downloading %s to %s", config.POSE_MODEL, path)
    got = Path(attempt_download_asset(str(path)))
    if not got.exists():
        raise FileNotFoundError(f"pose weights {config.POSE_MODEL} unavailable (offline?). Put the file in {path.parent}")
    return got


class _Cam:
    def __init__(self, camera_id: int):
        self.camera_id = camera_id
        self.model = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"pose-{camera_id}")
        self.future = None
        self.last_run = 0.0
        self.last_log = 0.0
        self.last_delivery: dict[str, float] = {}
        self.health = resilience.health_for("pose_detection", camera_id)
        self.ms: list[int] = []
        self.frames_in = 0
        self.frames_run = 0
        self.frames_skipped_busy = 0
        self.last_people = 0

    @property
    def failed(self) -> bool:
        return self.health.failed


class PoseDetectionService:
    def __init__(self):
        self._consumers: list[tuple[str, object, object]] = []
        self._cams: dict[int, _Cam] = {}
        self._lock = threading.Lock()

    def register(self, name: str, wants, deliver) -> None:
        self._consumers.append((name, wants, deliver))

    def _wanted(self, camera_id: int) -> dict[str, float]:
        out = {}
        for name, wants, _ in self._consumers:
            try:
                fps = float(wants(camera_id) or 0)
            except Exception:
                fps = 0.0
            if fps > 0:
                out[name] = fps
        return out

    def feed(self, camera_id: int, frame: np.ndarray) -> None:
        """Called by the camera stream for every decoded frame; cheap unless due."""
        wanted = self._wanted(camera_id)
        if not wanted:
            return
        cam = self._cams.get(camera_id)
        if cam is None:
            with self._lock:
                cam = self._cams.setdefault(camera_id, _Cam(camera_id))
        cam.frames_in += 1
        if not cam.health.allow():
            return
        now = time.time()
        if now - cam.last_run < 1.0 / max(wanted.values()):
            return
        if cam.future is not None and not cam.future.done():
            cam.frames_skipped_busy += 1
            return  # still processing the previous frame: skip, do not queue
        cam.last_run = now
        cam.future = cam.executor.submit(self._run, cam, frame, now, wanted)

    def _run(self, cam: _Cam, frame: np.ndarray, ts: float, wanted: dict[str, float]) -> None:
        proc = settings_store.get("processing")
        try:
            if cam.model is None:
                import torch
                from ultralytics import YOLO

                # By default torch uses every core for one inference, which starves the thread that decodes and sends the
                # video (it fell to ~7 fps on a 4-core laptop). Keep a few cores free for decoding/streaming.
                torch.set_num_threads(config.POSE_THREADS)
                cam.model = YOLO(str(ensure_weights()))
            t = time.time()
            kw = {"persist": True, "tracker": config.POSE_TRACKER, "conf": float(proc["conf"]),
                  "imgsz": int(proc["imgsz"]), "verbose": False}
            if config.POSE_DEVICE:
                kw["device"] = config.POSE_DEVICE
            res = cam.model.track(frame, **kw)[0]
            cam.ms = (cam.ms + [round((time.time() - t) * 1000)])[-20:]
            if time.time() - cam.last_log > 60:
                cam.last_log = time.time()
                log.info("camera %s: pose analysis %d ms average (%d threads), %d run / %d skipped busy", cam.camera_id,
                         sum(cam.ms) / len(cam.ms), config.POSE_THREADS, cam.frames_run, cam.frames_skipped_busy)
            people = self._people(res)
        except Exception as e:
            log.warning("camera %s: pose inference failed: %s", cam.camera_id, e)
            if cam.health.failure(e):
                cam.model = None  # reload the model (and a fresh tracker) next time
            return
        cam.health.success()
        cam.frames_run += 1
        cam.last_people = len(people)
        half_step = 0.5 / max(wanted.values())
        for name, _, deliver in self._consumers:
            fps = wanted.get(name)
            if not fps:
                continue
            due = cam.last_delivery.get(name)
            if due is not None and ts + half_step < due:
                continue
            interval = 1.0 / fps
            cam.last_delivery[name] = ts + interval if due is None else max(due + interval, ts)
            try:
                deliver(cam.camera_id, frame, people, ts)
            except Exception:
                log.exception("pose consumer %s failed on camera %s", name, cam.camera_id)

    @staticmethod
    def _people(res) -> list[dict]:
        """Ultralytics result -> [{track_id, bbox, confidence, keypoints (17,3)}]."""
        people: list[dict] = []
        if res.boxes is None or not len(res.boxes):
            return people
        n = len(res.boxes)
        ids = res.boxes.id.cpu().numpy().astype(int) if res.boxes.id is not None else [None] * n
        xyxy = res.boxes.xyxy.cpu().numpy()
        conf = res.boxes.conf.cpu().numpy()
        kp = res.keypoints.data.cpu().numpy() if getattr(res, "keypoints", None) is not None and res.keypoints.data is not None else None
        for i in range(n):
            people.append({"track_id": None if ids[i] is None else int(ids[i]),
                           "bbox": [float(v) for v in xyxy[i]], "confidence": float(conf[i]),
                           "keypoints": None if kp is None or i >= len(kp) else kp[i]})
        return people

    def remove_camera(self, camera_id: int) -> None:
        """Camera deleted or detection switched off: drop its model, tracker and executor."""
        with self._lock:
            cam = self._cams.pop(camera_id, None)
        if cam is not None:
            cam.executor.shutdown(wait=False, cancel_futures=True)
            cam.model = None
        resilience.unregister("pose_detection", camera_id)

    def shutdown(self) -> None:
        with self._lock:
            cams = list(self._cams.values())
            self._cams.clear()
        for c in cams:
            c.executor.shutdown(wait=False, cancel_futures=True)

    def status(self) -> list[dict]:
        return [
            {"camera_id": cid, "failed": c.failed, "state": c.health.state, "wanted": self._wanted(cid),
             "inference_ms": round(sum(c.ms) / len(c.ms)) if c.ms else None,
             "frames_in": c.frames_in, "frames_processed": c.frames_run, "frames_skipped_busy": c.frames_skipped_busy,
             "people": c.last_people, "running": time.time() - c.last_run < 3}
            for cid, c in list(self._cams.items())
        ]


service = PoseDetectionService()
