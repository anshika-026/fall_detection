"""
clips.py

Short event video clips (~5 s before + ~5 s after an event) for any feature
that needs them: Visitor Management and Footfall.

One rolling buffer per camera that ANY feature wants (want(owner, cameras)),
so a camera that is both a footfall gate and a visitor area is buffered once.
camera_stream hands every frame to tap(); unless the camera is wanted that is a
dictionary lookup. A wanted camera keeps a small JPEG at most BUFFER_FPS times
a second (on a worker, skipped when busy). schedule() waits for the "after"
half, then one encoder thread writes an H.264 MP4 - live video and detection
never wait for it.
"""

from __future__ import annotations

import collections
import concurrent.futures
import logging
import os
import threading
import time
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger("clips")

# Environment names renamed from SMC's VISITOR_* to FALLDET_*; pre/post defaults raised for fall evidence.
PRE_SECONDS = float(os.environ.get("FALLDET_CLIP_PRE_SECONDS", "8"))
POST_SECONDS = float(os.environ.get("FALLDET_CLIP_POST_SECONDS", "8"))
BUFFER_FPS = float(os.environ.get("FALLDET_BUFFER_FPS", "6"))
BUFFER_WIDTH = int(os.environ.get("FALLDET_BUFFER_WIDTH", "640"))
# Extra room: a fall is confirmed several seconds after it started.
# footfall entry is confirmed when the person vanishes through the door, up to
# the line tracker's lost-track timeout later).
BUFFER_SECONDS = PRE_SECONDS + POST_SECONDS + 14.0

NO_VIDEO = "No video was available from this camera (it may have been offline)."
DISK_FULL = "Clip storage limit reached."


def dir_mb(path: Path) -> float:
    if not path.is_dir():
        return 0.0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


class ClipRecorder:
    def __init__(self):
        self._owners: dict[str, frozenset[int]] = {}
        self._wanted: frozenset[int] = frozenset()
        self._buffers: dict[int, collections.deque] = {}
        self._buffer_lock = threading.Lock()
        self._last_tap: dict[int, float] = {}
        self._tap_executors: dict[int, concurrent.futures.ThreadPoolExecutor] = {}
        self._tap_futures: dict[int, concurrent.futures.Future] = {}
        self._encoder = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="clip-encode")

    def want(self, owner: str, camera_ids) -> None:
        """The cameras `owner` needs buffered (replaces its previous set)."""
        self._owners[owner] = frozenset(camera_ids)
        self._wanted = frozenset().union(*self._owners.values())
        with self._buffer_lock:
            for cid in [c for c in self._buffers if c not in self._wanted]:
                self._buffers.pop(cid, None)

    def is_wanted(self, camera_id: int) -> bool:
        return camera_id in self._wanted

    # ---- rolling buffer ------------------------------------------------------

    def tap(self, camera_id: int, frame: np.ndarray) -> None:
        """Called by camera_stream for every frame. Cheap unless the camera is wanted."""
        if camera_id not in self._wanted:
            return
        now = time.time()
        if now - self._last_tap.get(camera_id, 0.0) < 1.0 / BUFFER_FPS:
            return
        fut = self._tap_futures.get(camera_id)
        if fut is not None and not fut.done():
            return
        self._last_tap[camera_id] = now
        ex = self._tap_executors.setdefault(camera_id, concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"clip-tap-{camera_id}"))
        self._tap_futures[camera_id] = ex.submit(self._buffer_frame, camera_id, frame, now)

    def _buffer_frame(self, camera_id: int, frame: np.ndarray, ts: float) -> None:
        try:
            h, w = frame.shape[:2]
            img = frame if w <= BUFFER_WIDTH else cv2.resize(frame, (BUFFER_WIDTH, round(h * BUFFER_WIDTH / w)), interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ok:
                return
            with self._buffer_lock:
                if camera_id not in self._wanted:
                    return
                dq = self._buffers.get(camera_id)
                if dq is None:
                    dq = self._buffers[camera_id] = collections.deque(maxlen=int(BUFFER_SECONDS * BUFFER_FPS) + 4)
                dq.append((ts, buf.tobytes()))
        except Exception:
            log.exception("clips: could not buffer a frame from camera %s", camera_id)

    def frames(self, camera_id: int, t0: float) -> list[tuple[float, bytes]]:
        with self._buffer_lock:
            return [(ts, jpg) for ts, jpg in self._buffers.get(camera_id, ()) if t0 - PRE_SECONDS <= ts <= t0 + POST_SECONDS]

    # ---- clips ------------------------------------------------------------------

    def schedule(self, camera_id: int, t0: float, final: Path, on_done, max_dir_mb: float | None = None) -> None:
        """Writes the clip around t0 to `final` once the 'after' half is in.
        on_done(status, frames=None, error=None): status 'ready' | 'failed'.
        max_dir_mb caps the total size of final's parent's parent folder."""
        wait = max(0.0, t0 + POST_SECONDS - time.time()) + 0.8   # t0 may already be in the past
        timer = threading.Timer(wait, lambda: self._encoder.submit(self._write, camera_id, t0, final, on_done, max_dir_mb))
        timer.daemon = True
        timer.start()

    def _write(self, camera_id: int, t0: float, final: Path, on_done, max_dir_mb: float | None) -> None:
        try:
            frames = self.frames(camera_id, t0)
            if not frames:
                on_done("failed", error=NO_VIDEO)
                return
            if max_dir_mb is not None and dir_mb(final.parent.parent) > max_dir_mb:
                on_done("failed", error=DISK_FULL)
                return
            final.parent.mkdir(parents=True, exist_ok=True)
            part = final.with_suffix(".part.mp4")
            span = max(0.5, frames[-1][0] - frames[0][0])
            fps = max(2, min(12, round(len(frames) / span)))
            encode_mp4(part, [jpg for _ts, jpg in frames], fps)
            os.replace(part, final)
            on_done("ready", frames=len(frames))
        except Exception as e:
            log.exception("clips: could not write %s", final.name)
            try:
                on_done("failed", error=f"Recording failed ({type(e).__name__}).")
            except Exception:
                pass


def encode_mp4(path: Path, jpegs: list[bytes], fps: int) -> None:
    """H.264 (yuv420p) MP4 with the index at the front, so browsers play and seek it."""
    import av

    first = cv2.imdecode(np.frombuffer(jpegs[0], np.uint8), cv2.IMREAD_COLOR)
    h, w = first.shape[:2]
    w, h = w - w % 2, h - h % 2
    container = av.open(str(path), "w", options={"movflags": "+faststart"})
    try:
        stream = container.add_stream("libx264", rate=fps)
        stream.width, stream.height, stream.pix_fmt = w, h, "yuv420p"
        stream.options = {"crf": "28", "preset": "veryfast"}
        for jpg in jpegs:
            img = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                continue
            frame = av.VideoFrame.from_ndarray(img[:h, :w], format="bgr24")
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    finally:
        container.close()


recorder = ClipRecorder()
