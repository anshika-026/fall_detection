"""Pulls frames off a camera in a background reader process and fans them out to
the websocket viewers and to fall detection, so N browser tabs plus the detector
share ONE connection to the camera.

ADAPTED from SMC backend/app/camera_stream.py. Kept as it was (it is the
proven part): the separate reader PROCESS (rtsp_reader.py) that always keeps only
the newest frame in shared memory, the watchdog that kills and restarts a hung
reader with backoff, the connection-state model, the subscriber/width logic and
the once-per-width JPEG encode. Removed: face recognition, footfall, staff count,
visitors and analytics switches, and their imports (they cannot exist in this
module). Added: the frame is handed to pose_worker (fall detection) and to the
clip recorder, and frame-rate / last-frame bookkeeping for the dashboard."""
from __future__ import annotations

import logging
import multiprocessing
import queue
import threading
import time
from multiprocessing import shared_memory

import cv2
import numpy as np

from falldet import config
from falldet.camera import camera_db, clips, rtsp_reader, stream_source
from falldet.core import resilience
from falldet.detection import pose_worker

log = logging.getLogger("camera_stream")

S_IDLE, S_CONNECTING, S_RUNNING = "IDLE", "CONNECTING", "RUNNING"
S_RECONNECTING, S_STALLED, S_FAILED, S_STOPPED = "RECONNECTING", "STALLED", "FAILED", "STOPPED"

PUSH_RECONNECT_MAX_DELAY = 5.0


def _reader_settings(protocol: str = "rtsp") -> dict:
    s = {"connect_timeout": config.RTSP_CONNECT_TIMEOUT, "read_timeout": config.RTSP_READ_TIMEOUT,
         "reconnect_delay": config.RTSP_RECONNECT_DELAY, "reconnect_max_delay": config.RTSP_RECONNECT_MAX_DELAY}
    if protocol == stream_source.PUSH_PROTOCOL:
        s["reconnect_max_delay"] = min(s["reconnect_max_delay"], PUSH_RECONNECT_MAX_DELAY)
    return s


class CameraStream:
    def __init__(self, camera_id: int):
        self.camera_id = camera_id
        self._lock = threading.Lock()
        self._subscribers: set = set()
        self._frameless: set = set()          # keep-alives: keep the read loop running, no JPEG encoded
        self._widths: dict = {}
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.state = S_IDLE
        self.state_detail: str | None = None
        self.connect_failures = 0
        self.watchdog_restarts = 0
        self.last_jpeg: bytes | None = None
        self.last_frame_at: float | None = None
        self.frame_size: tuple[int, int] | None = None   # (w, h) of the decoded frames
        self._frame_times: list[float] = []

    # -- subscription ---------------------------------------------------------------
    def subscribe(self, q, width: int | None = None, wants_frames: bool = True) -> None:
        """wants_frames=False is a keep-alive (used for background fall detection)."""
        with self._lock:
            self._subscribers.add(q)
            if not wants_frames:
                self._frameless.add(q)
            elif width:
                self._widths[q] = int(width)
            self._ensure_running_locked()

    def unsubscribe(self, q) -> None:
        with self._lock:
            self._subscribers.discard(q)
            self._frameless.discard(q)
            self._widths.pop(q, None)
            if not self._subscribers:
                self._stop.set()

    def _ensure_running_locked(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, daemon=True, name=f"camera-{self.camera_id}")
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def resume(self) -> None:
        with self._lock:
            if self._subscribers:
                self._ensure_running_locked()

    def restart(self) -> None:
        """Connection details changed: stop the loop (and reader), then reconnect with the new details."""
        threading.Thread(target=self._restart_blocking, daemon=True, name=f"restart-cam{self.camera_id}").start()

    def _restart_blocking(self) -> None:
        self._stop.set()
        t = self._thread
        if t is not None and t.is_alive():
            t.join(timeout=20)
            if t.is_alive():
                log.warning("camera %s: stream did not stop in time; keeping the current connection", self.camera_id)
                self._stop.clear()
                return
        self.resume()

    def fps(self) -> float:
        t = [x for x in self._frame_times if x > time.time() - 5]
        return round(len(t) / 5.0, 1) if t else 0.0

    def status(self) -> dict:
        return {"camera_id": self.camera_id, "state": self.state, "detail": self.state_detail,
                "last_frame_at": self.last_frame_at, "connect_failures": self.connect_failures,
                "watchdog_restarts": self.watchdog_restarts, "subscribers": len(self._subscribers),
                "stream_fps": self.fps(), "frame_size": self.frame_size}

    # -- reader supervision (unchanged logic from SMC) ------------------------------
    def _handle_reader_message(self, msg) -> None:
        kind = msg[0]
        if kind == "log":
            log.info("camera %s: %s", self.camera_id, msg[1])
        elif kind == "status":
            state, info = msg[1], (msg[2] if len(msg) > 2 else {})
            if state == "connecting":
                if self.state not in (S_RECONNECTING, S_FAILED):
                    self.state = S_CONNECTING
            elif state == "connected":
                self.connect_failures = 0
                self.state, self.state_detail = S_RUNNING, None
            elif state == "reconnecting":
                self.connect_failures = int(info.get("attempt", self.connect_failures + 1))
                self.state_detail = info.get("reason")
                self.state = S_FAILED if self.connect_failures >= config.RTSP_MAX_RETRIES else S_RECONNECTING

    def _run(self) -> None:
        try:
            self._run_inner()
        except Exception:
            log.exception("camera %s: stream loop crashed", self.camera_id)
            self.state = S_FAILED
        finally:
            if self.state != S_FAILED:
                self.state = S_STOPPED if self._subscribers else S_IDLE

    def _run_inner(self) -> None:
        cam = camera_db.get_camera_connection(self.camera_id)
        if cam and not camera_db.is_streamable(cam):
            log.info("camera %s: feed switched off, not connecting", self.camera_id)
            self.state, self.state_detail = S_STOPPED, "feed switched off"
            return
        url = stream_source.build_source_url(cam) if cam else None
        if not url:
            log.warning("camera %s: no address configured", self.camera_id)
            self.state, self.state_detail = S_STOPPED, "no address configured"
            return
        self.state, self.state_detail = S_CONNECTING, None

        ctx = multiprocessing.get_context("spawn")
        proc = stop = seq = meta_q = None
        shm = slots = None
        last_seq = 0
        last_progress = time.monotonic()
        last_watchdog_check = 0.0
        restarts = 0

        def start_reader():
            nonlocal proc, stop, seq, meta_q, last_seq, last_progress
            stop = ctx.Event()
            seq = ctx.Value("Q", 0, lock=False)
            meta_q = ctx.Queue(maxsize=256)
            last_seq = 0
            proc = ctx.Process(target=rtsp_reader.run,
                               args=(url, config.LIVE_STREAM_FPS, stop, seq, meta_q,
                                     _reader_settings(stream_source.protocol_of(cam))),
                               daemon=True, name=f"rtsp-reader-{self.camera_id}")
            proc.start()
            last_progress = time.monotonic() + config.RTSP_CONNECT_TIMEOUT

        def kill_reader(reason: str):
            nonlocal shm, slots
            if stop is not None:
                stop.set()
            if proc is not None:
                proc.join(timeout=3)
                if proc.is_alive():
                    proc.terminate()
                    proc.join(timeout=3)
                if proc.is_alive():
                    proc.kill()
                    proc.join(timeout=2)
            if shm is not None:
                slots = None
                shm.close()
                shm = None
            (log.info if reason == "stopped" else log.warning)("camera %s: reader %s", self.camera_id, reason)

        def restart_reader(reason: str) -> bool:
            nonlocal restarts
            restarts += 1
            kill_reader(reason)
            delay = resilience.backoff_delay(restarts, config.RTSP_RECONNECT_DELAY, config.RTSP_RECONNECT_MAX_DELAY)
            if self._stop.wait(delay):
                return False
            start_reader()
            return True

        try:
            start_reader()
            while not self._stop.is_set():
                while True:
                    try:
                        msg = meta_q.get_nowait()
                    except queue.Empty:
                        break
                    except (EOFError, OSError):
                        break
                    last_progress = max(last_progress, time.monotonic())
                    if msg[0] == "shm":
                        if shm is not None:
                            slots = None
                            shm.close()
                        shm = shared_memory.SharedMemory(name=msg[1])
                        slots = np.ndarray((2, *msg[2]), dtype=np.uint8, buffer=shm.buf)
                    else:
                        self._handle_reader_message(msg)

                if not proc.is_alive():
                    if not restart_reader(f"process exited (code {proc.exitcode}), restarting"):
                        break
                    continue

                now = time.monotonic()
                if now - last_watchdog_check >= config.CAMERA_WATCHDOG_INTERVAL:
                    last_watchdog_check = now
                    if now - last_progress > config.CAMERA_FRAME_TIMEOUT:
                        self.state, self.state_detail = S_STALLED, "no frames or heartbeat from reader"
                        self.watchdog_restarts += 1
                        if not restart_reader(f"stalled for {now - last_progress:.0f}s, restarting"):
                            break
                        continue

                current = seq.value
                if slots is None or current == last_seq:
                    time.sleep(0.01)
                    continue
                last_seq = current
                frame = slots[current % 2].copy()
                last_progress = time.monotonic()
                restarts = 0
                self.last_frame_at = time.time()
                self._frame_times = (self._frame_times + [self.last_frame_at])[-120:]
                self.frame_size = (frame.shape[1], frame.shape[0])
                if self.state != S_RUNNING:
                    self.state, self.state_detail = S_RUNNING, None

                # Fall detection: one pose inference per camera, on the worker's own
                # thread; a busy worker simply skips this frame. Guarded so a detector
                # bug can never stop the video.
                try:
                    pose_worker.service.feed(self.camera_id, frame)
                except Exception:
                    log.exception("camera %s: detection dispatch failed", self.camera_id)
                try:
                    clips.recorder.tap(self.camera_id, frame)
                except Exception:
                    log.exception("camera %s: clip buffer failed", self.camera_id)

                with self._lock:
                    receivers = [(q, self._widths.get(q)) for q in self._subscribers if q not in self._frameless]
                encoded: dict = {}
                fh, fw = frame.shape[:2]
                for q, width in receivers:
                    key = width if width and width < fw else None
                    if key not in encoded:
                        img = frame if key is None else cv2.resize(frame, (key, round(fh * key / fw)), interpolation=cv2.INTER_AREA)
                        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70 if key is None else 72])
                        encoded[key] = buf.tobytes() if ok else None
                        if ok and key is None:
                            self.last_jpeg = encoded[key]
                    data = encoded[key]
                    if data is None:
                        continue
                    try:
                        q.put_nowait(data)
                    except Exception:  # noqa: S110
                        pass   # a full/closed viewer queue drops this frame for that viewer only
        finally:
            kill_reader("stopped")


_streams: dict[int, CameraStream] = {}
_streams_lock = threading.Lock()


def get_stream(camera_id: int) -> CameraStream:
    with _streams_lock:
        s = _streams.get(camera_id)
        if s is None:
            s = _streams[camera_id] = CameraStream(camera_id)
        return s


def existing_stream(camera_id: int) -> CameraStream | None:
    return _streams.get(camera_id)


def remove_stream(camera_id: int, timeout: float = 20.0) -> None:
    """Camera deleted: stop its loop and reader, drop its detection state, forget the stream."""
    with _streams_lock:
        s = _streams.pop(camera_id, None)
    if s is not None:
        s._stop.set()
        t = s._thread
        if t is not None and t.is_alive():
            t.join(timeout=timeout)
    pose_worker.service.remove_camera(camera_id)


class _StillSink:
    def __init__(self):
        self.event = threading.Event()
        self.data: bytes | None = None

    def put_nowait(self, item):
        self.data = item
        self.event.set()


def grab_still(camera_id: int, timeout: float = 12.0) -> bytes | None:
    s = get_stream(camera_id)
    if s.last_jpeg and s.last_frame_at and time.time() - s.last_frame_at < 5:
        return s.last_jpeg
    sink = _StillSink()
    s.subscribe(sink)
    try:
        sink.event.wait(timeout)
        return sink.data
    finally:
        s.unsubscribe(sink)


def all_status() -> list[dict]:
    return [s.status() for s in list(_streams.values())]


def stop_all(timeout: float = 10.0) -> None:
    for s in list(_streams.values()):
        s._stop.set()
    for s in list(_streams.values()):
        t = s._thread
        if t is not None and t.is_alive():
            t.join(timeout=timeout)
