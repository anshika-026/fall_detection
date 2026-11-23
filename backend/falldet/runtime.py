"""Wires the pieces together:

    camera_stream (frames) -> pose_worker (one pose+ByteTrack pass per camera)
        -> CameraFallEngine (one per camera) -> IncidentManager -> DB / hub

and keeps the set of cameras being analysed in step with the camera table and
the settings (cameras switched on/off, settings edited, cameras deleted)."""
from __future__ import annotations

import logging
import threading
import time

from falldet.camera import camera_db, camera_stream, clips
from falldet.core import settings_store
from falldet.detection import pose_worker
from falldet.event_manager import incidents
from falldet.event_manager.hub import hub
from falldet.event_manager.manager import IncidentManager
from falldet.fall_analysis.engine import CameraFallEngine

log = logging.getLogger("runtime")


class _KeepAlive:
    """A frameless subscriber that keeps a camera's read loop running with no viewer."""

    def put_nowait(self, item):  # never called: wants_frames=False
        pass


class Live:
    """Latest analysis of one camera, for the live overlay websocket."""

    def __init__(self):
        self.people: list[dict] = []
        self.frame_wh: tuple[int, int] | None = None
        self.updated_at: float | None = None


class Runtime:
    def __init__(self):
        self.engines: dict[int, CameraFallEngine] = {}
        self.engine_locks: dict[int, threading.Lock] = {}
        self.live: dict[int, Live] = {}
        self._keepalive: dict[int, _KeepAlive] = {}
        self._names: dict[int, str] = {}
        self._cam_state: dict[int, dict] = {}
        self._lock = threading.Lock()
        self._settings_version = -1
        self.manager = IncidentManager(lambda cid: self._names.get(cid, f"Camera {cid}"))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- consumer callbacks for pose_worker ----------------------------------------
    def wants(self, camera_id: int) -> float:
        cam = self._cam_state.get(camera_id)
        if not cam:
            return 0.0
        return float(settings_store.get("processing")["detect_fps"])

    def deliver(self, camera_id: int, frame, people: list[dict], ts: float) -> None:
        with self._lock:
            engine = self.engines.get(camera_id)
            lock = self.engine_locks.get(camera_id)
        if engine is None or lock is None:
            return
        h, w = frame.shape[:2]
        with lock:
            events = engine.update(ts, people, (w, h))
            for ev in events:
                if ev.fsm is not None:
                    self.manager.handle(ev, ev.fsm, frame)
            snap = {s["track_id"]: s for s in engine.snapshot()}
        out = []
        for p in people:
            tid = p.get("track_id")
            st = snap.get(tid, {})
            kp = p.get("keypoints")
            out.append({"track_id": tid, "bbox": [round(v, 1) for v in p["bbox"]], "confidence": round(p["confidence"], 3),
                        "state": st.get("state", "NORMAL"), "fall_confidence": st.get("confidence", 0.0),
                        "posture": st.get("posture", "other"), "incident_id": st.get("incident_id"),
                        "keypoints": None if kp is None else [[round(float(a), 1), round(float(b), 1), round(float(c), 2)] for a, b, c in kp]})
        lv = self.live.setdefault(camera_id, Live())
        lv.people, lv.frame_wh, lv.updated_at = out, (w, h), time.time()

    # -- lifecycle -------------------------------------------------------------------
    def start(self) -> None:
        n = incidents.close_stale_on_startup()
        if n:
            log.info("dismissed %s unconfirmed possible fall(s) left from the previous run", n)
        pose_worker.service.register("fall", self.wants, self.deliver)
        self.sync()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="runtime-sync")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        pose_worker.service.shutdown()
        camera_stream.stop_all()

    def _loop(self) -> None:
        while not self._stop.wait(5.0):
            try:
                self.sync()
            except Exception:
                log.exception("runtime sync failed")

    def sync(self) -> None:
        """Make the running engines/streams match the camera table and settings."""
        cams = {c["id"]: camera_db.get_camera_connection(c["id"]) for c in camera_db.list_cameras()}
        wanted = {cid: c for cid, c in cams.items() if c and camera_db.wants_detection(c)}
        self._names = {cid: (c or {}).get("name", f"Camera {cid}") for cid, c in cams.items()}
        self._cam_state = {cid: {"on": True} for cid in wanted}
        ver = settings_store.version()
        changed = ver != self._settings_version
        self._settings_version = ver
        with self._lock:
            for cid, c in wanted.items():
                cfg = settings_store.fall_config(c.get("sensitivity") or "")
                if cid not in self.engines:
                    self.engines[cid] = CameraFallEngine(cid, cfg)
                    self.engine_locks[cid] = threading.Lock()
                    log.info("camera %s: fall detection on", cid)
                elif changed:
                    with self.engine_locks[cid]:
                        self.engines[cid].set_config(cfg)
            for cid in [c for c in self.engines if c not in wanted]:
                log.info("camera %s: fall detection off", cid)
                self.engines.pop(cid, None)
                self.engine_locks.pop(cid, None)
                self.live.pop(cid, None)
                pose_worker.service.remove_camera(cid)
        # keep wanted cameras streaming with no viewer; stop streaming ones nobody needs
        for cid in wanted:
            if cid not in self._keepalive:
                ka = self._keepalive[cid] = _KeepAlive()
                camera_stream.get_stream(cid).subscribe(ka, wants_frames=False)
        for cid in [c for c in self._keepalive if c not in wanted]:
            camera_stream.get_stream(cid).unsubscribe(self._keepalive.pop(cid))
        clips.recorder.want("falldet", wanted.keys())

    def camera_changed(self, camera_id: int, connection_changed: bool = True) -> None:
        """A camera was edited: reconnect if its address changed, then re-sync."""
        if connection_changed:
            s = camera_stream.existing_stream(camera_id)
            if s is not None:
                s.restart()
        self.sync()

    def camera_deleted(self, camera_id: int) -> None:
        ka = self._keepalive.pop(camera_id, None)
        camera_stream.remove_stream(camera_id)
        with self._lock:
            self.engines.pop(camera_id, None)
            self.engine_locks.pop(camera_id, None)
            self.live.pop(camera_id, None)
        self.sync()

    def resolve_in_engine(self, camera_id: int, track_id: int | None) -> None:
        if track_id is None:
            return
        with self._lock:
            engine, lock = self.engines.get(camera_id), self.engine_locks.get(camera_id)
        if engine is not None and lock is not None:
            with lock:
                engine.resolve_track(track_id)

    def camera_runtime(self, camera_id: int) -> dict:
        st = camera_stream.existing_stream(camera_id)
        lv = self.live.get(camera_id)
        det = {s["camera_id"]: s for s in pose_worker.service.status()}.get(camera_id)
        return {"stream": st.status() if st else None, "detection": det,
                "detecting": camera_id in self.engines,
                "people_now": len(lv.people) if lv else 0,
                "worst_state": _worst([p["state"] for p in lv.people]) if lv else "NORMAL",
                "analysis_age": None if not lv or not lv.updated_at else round(time.time() - lv.updated_at, 1)}


_ORDER = ["NORMAL", "RESOLVED", "RECOVERED", "POSSIBLE", "CONFIRMED"]


def _worst(states: list[str]) -> str:
    return max(states, key=_ORDER.index) if states else "NORMAL"


runtime = Runtime()
