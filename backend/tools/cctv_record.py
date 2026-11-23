"""Record continuous footage from existing RTSP cameras, for validation (not part of the live backend).

  python -m tools.cctv_record --camera office-1=CCTV_URL_OFFICE1 --duration 3600 --segment-seconds 300
  python -m tools.cctv_record --config ../validation/cameras.json --duration 7200
  python -m tools.cctv_record --db-camera office-2=3            # reuse camera #3 of the backend's own database

How a camera is given (the URL, which holds the password, is NEVER on the command line, in a config file or in a log):
  --camera ID=ENVVAR   the URL is read from the environment variable ENVVAR (set it in your shell session)
  --db-camera ID=N     the URL is built from camera N in the backend database (credentials stay where they already are)
  --config FILE        JSON {"cameras":[{"id":"office-1","url_env":"CCTV_URL_OFFICE1"} | {"id":"x","db_camera_id":3}]}

Output (never overwritten; a name collision gets a _dupN suffix):
  <out>/<camera_id>/<camera_id>_<UTC start>_<nn>.mkv     Matroska: a killed process / power cut leaves a playable file
  <out>/<camera_id>/<same name>.json                      sidecar: UTC start/end, mode, frames, why the segment ended
Default mode REMUXES the camera's own H.264/H.265 packets (no decoding or re-encoding): near-zero CPU and the
original quality. --width/--height/--fps switch to decode + scale + x264 re-encode (costs CPU; use for fewer pixels).
A dropped stream closes the current segment (everything recorded so far is kept) and reconnects with backoff
(2 s doubling to 60 s); each reconnect starts a new segment. Segments rotate every --segment-seconds, at a keyframe.
Recording stops when --duration elapses, on Ctrl+C, or when free disk space falls below --min-free-gb.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import av

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

log = logging.getLogger("cctv_record")
_SECRET = re.compile(r"(://[^:/@\s]+:)[^@/\s]+@")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def scrub(text: str, *secrets: str) -> str:
    """Mask credentials in anything that gets logged (URL userinfo and the raw URLs themselves)."""
    for s in secrets:
        if s:
            text = text.replace(s, "<url>")
    return _SECRET.sub(r"\1***@", text)


def utc_stamp(t: float | None = None) -> str:
    return datetime.fromtimestamp(t if t is not None else time.time(), timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def unique_path(folder: Path, stem: str, ext: str) -> Path:
    """A path that does not exist yet (existing recordings are never overwritten)."""
    p = folder / f"{stem}{ext}"
    n = 1
    while p.exists() or p.with_suffix(".json").exists():
        p = folder / f"{stem}_dup{n}{ext}"
        n += 1
    return p


class Segment:
    """One output file. Remux or re-encode; both write Matroska."""

    def __init__(self, path: Path, in_stream, mode: dict, cam_id: str, source_kind: str = "rtsp"):
        self.path, self.cam_id, self.mode = path, cam_id, mode
        self.source_kind = source_kind                       # "rtsp" (a network camera) or "file" (a test source)
        self.codec = in_stream.codec_context.name
        self.start = time.time()
        self.frames = 0
        self.t_first: float | None = None                    # media time (s) of the first / last packet written
        self.t_last: float | None = None
        self.out = av.open(str(path), "w", format="matroska")
        self.remux = not mode.get("reencode")
        self.base: int | None = None
        if self.remux:
            self.vs = self.out.add_stream_from_template(in_stream)
            self.width, self.height = in_stream.codec_context.width, in_stream.codec_context.height
            self.fps = float(in_stream.average_rate or 0) or None
        else:
            self.width = int(mode["width"] or in_stream.codec_context.width) & ~1
            self.height = int(mode["height"] or in_stream.codec_context.height) & ~1
            self.fps = float(mode["fps"] or in_stream.average_rate or 15)
            self.vs = self.out.add_stream("libx264", rate=int(round(self.fps)))
            self.vs.width, self.vs.height, self.vs.pix_fmt = self.width, self.height, "yuv420p"
            self.vs.options = {"preset": "ultrafast", "crf": "23"}
            self._next_t = 0.0

    def write_packet(self, pkt) -> None:
        if pkt.dts is None:
            return
        if self.base is None:
            self.base = pkt.dts
        if pkt.pts is not None and pkt.time_base:
            t = float(pkt.pts * pkt.time_base)
            self.t_first = t if self.t_first is None else self.t_first
            self.t_last = t
        pkt.dts -= self.base
        pkt.pts = None if pkt.pts is None else pkt.pts - self.base
        pkt.stream = self.vs
        self.out.mux(pkt)
        self.frames += 1

    def write_frame(self, frame, t: float) -> None:
        """Re-encode path: keep ~mode fps by dropping frames."""
        if t < self._next_t:
            return
        self._next_t = max(self._next_t + 1.0 / self.fps, t)
        f = frame.reformat(width=self.width, height=self.height, format="yuv420p")
        f.pts = self.frames
        f.time_base = __import__("fractions").Fraction(1, int(round(self.fps)))
        for p in self.vs.encode(f):
            self.out.mux(p)
        self.frames += 1

    def close(self, why: str) -> None:
        end = time.time()
        try:
            if not self.remux:
                for p in self.vs.encode(None):
                    self.out.mux(p)
            self.out.close()
        except Exception as e:                                        # a half-written file is still kept
            log.warning("%s: closing %s: %s", self.cam_id, self.path.name, scrub(str(e)))
        side = {"camera_id": self.cam_id, "file": self.path.name, "segment_start_utc": iso(self.start), "segment_end_utc": iso(end),
                "duration_s": round(end - self.start, 1),
                "media_span_s": round(self.t_last - self.t_first, 2) if self.t_first is not None and self.t_last is not None else None, "mode": "remux" if self.remux else "reencode",
                "source_kind": self.source_kind, "source_codec": self.codec, "frames_or_packets": self.frames, "width": self.width, "height": self.height, "fps_nominal": self.fps, "ended_by": why}
        try:
            self.path.with_suffix(".json").write_text(json.dumps(side, indent=2), encoding="utf-8")
        except OSError as e:
            log.warning("%s: sidecar not written: %s", self.cam_id, e)
        log.info("%s: closed %s (%s, %.0f s, %d %s)", self.cam_id, self.path.name, why, end - self.start, self.frames,
                 "packets" if self.remux else "frames")


class CameraRecorder(threading.Thread):
    def __init__(self, cam_id: str, url: str, out_dir: Path, seconds: float | None, segment_s: float, mode: dict,
                 stop: threading.Event, min_free_gb: float):
        super().__init__(daemon=True, name=f"rec-{cam_id}")
        self.cam_id, self._url, self.dir = cam_id, url, out_dir / cam_id
        self.seconds, self.segment_s, self.mode, self.stop_evt, self.min_free = seconds, segment_s, mode, stop, min_free_gb
        self.segments = 0
        self.reconnects = 0
        self.disk_stop = False

    def _disk_ok(self) -> bool:
        return shutil.disk_usage(self.dir).free / 1e9 >= self.min_free

    def run(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + self.seconds if self.seconds else None
        backoff = 2.0
        while not self.stop_evt.is_set() and (deadline is None or time.time() < deadline):
            got = False
            try:
                got = self._session(deadline)
            except Exception as e:                                    # network / decoder / disk error: log, back off, retry
                log.warning("%s: %s", self.cam_id, scrub(f"{type(e).__name__}: {e}", self._url))
            if self.disk_stop:
                return
            if got:
                backoff = 2.0
            if self.stop_evt.is_set() or (deadline and time.time() >= deadline):
                break
            self.reconnects += 1
            log.info("%s: stream lost, retrying in %.0f s", self.cam_id, backoff)
            self.stop_evt.wait(backoff)
            backoff = min(backoff * 2, 60.0)

    def _session(self, deadline) -> bool:
        opts = {"rtsp_transport": "tcp"} if self._url.lower().startswith("rtsp") else {}
        inp = av.open(self._url, options=opts, timeout=(10.0, 10.0))
        got = False
        seg: Segment | None = None
        why = "disconnect"
        try:
            vs = inp.streams.video[0]
            vs.thread_type = "AUTO"
            log.info("%s: connected (%s %dx%d)", self.cam_id, vs.codec_context.name, vs.codec_context.width, vs.codec_context.height)
            reencode = self.mode.get("reencode")
            for pkt in inp.demux(vs):
                if self.stop_evt.is_set():
                    why = "stop"
                    break
                if deadline and time.time() >= deadline:
                    why = "duration"
                    break
                if pkt.size == 0 or pkt.dts is None:
                    continue
                rotate = seg is not None and time.time() - seg.start >= self.segment_s
                if seg is None or (rotate and (pkt.is_keyframe or reencode)):
                    if seg is not None:
                        seg.close("rotate")
                    if not self._disk_ok():
                        log.error("%s: free disk below %.1f GB: stopping", self.cam_id, self.min_free)
                        self.disk_stop, why, seg = True, "disk-full", None
                        self.stop_evt.set()
                        break
                    if not reencode and not pkt.is_keyframe:
                        continue                                       # a segment must start on a keyframe to be playable
                    path = unique_path(self.dir, f"{self.cam_id}_{utc_stamp()}_{self.segments:02d}", ".mkv")
                    seg = Segment(path, vs, self.mode, self.cam_id, "rtsp" if self._url.lower().startswith(("rtsp://", "rtsps://")) else "file")
                    self.segments += 1
                    log.info("%s: recording to %s", self.cam_id, path.name)
                got = True
                if reencode:
                    for fr in pkt.decode():
                        seg.write_frame(fr, time.time() - seg.start)
                else:
                    seg.write_packet(pkt)
            else:
                why = "disconnect"                                      # demux ended: stream closed by the camera / EOF
        finally:
            if seg is not None:
                seg.close(why)
            inp.close()
        return got


def resolve_cameras(args) -> dict[str, str]:
    """camera id -> URL, from the environment / backend DB. The URL never leaves this dict."""
    cams: dict[str, str] = {}

    def add(cid: str, url: str | None, how: str):
        if not _SAFE_ID.match(cid):
            raise SystemExit(f"camera id '{cid}' must be 1-40 letters, digits, _ or -")
        if not url:
            raise SystemExit(f"camera '{cid}': {how} gave no URL")
        if cid in cams:
            raise SystemExit(f"camera id '{cid}' given twice")
        cams[cid] = url

    for spec in args.camera or []:
        cid, _, var = spec.partition("=")
        add(cid, os.environ.get(var), f"environment variable {var or '(missing)'}")
    for spec in args.db_camera or []:
        cid, _, num = spec.partition("=")
        from falldet.camera import camera_db
        from falldet.camera.stream_source import build_source_url

        cam = camera_db.get_camera_connection(int(num)) if num.isdigit() else None
        add(cid, build_source_url(cam) if cam else None, f"backend camera #{num}")
    if args.config:
        for c in json.loads(Path(args.config).read_text(encoding="utf-8")).get("cameras", []):
            if "url" in c:
                raise SystemExit("the config file must not contain a URL (it would hold the password): use url_env or db_camera_id")
            if "url_env" in c:
                add(c["id"], os.environ.get(c["url_env"]), f"environment variable {c['url_env']}")
            elif "db_camera_id" in c:
                from falldet.camera import camera_db
                from falldet.camera.stream_source import build_source_url

                cam = camera_db.get_camera_connection(int(c["db_camera_id"]))
                add(c["id"], build_source_url(cam) if cam else None, f"backend camera #{c['db_camera_id']}")
            else:
                raise SystemExit(f"camera entry {c.get('id')!r} needs url_env or db_camera_id")
    if not cams:
        raise SystemExit("no cameras given (use --camera, --db-camera or --config)")
    return cams


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--camera", action="append", metavar="ID=ENVVAR")
    ap.add_argument("--db-camera", action="append", metavar="ID=N")
    ap.add_argument("--config")
    ap.add_argument("--out", default=str(ROOT.parent / "validation" / "recordings"))
    ap.add_argument("--duration", type=float, default=0, help="total seconds to record (0 = until Ctrl+C)")
    ap.add_argument("--segment-seconds", type=float, default=300.0)
    ap.add_argument("--width", type=int, default=0)
    ap.add_argument("--height", type=int, default=0)
    ap.add_argument("--fps", type=float, default=0, help="with width/height/fps set the video is re-encoded")
    ap.add_argument("--min-free-gb", type=float, default=2.0)
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for noisy in ("libav", "av"):
        logging.getLogger(noisy).setLevel(logging.ERROR)
    cams = resolve_cameras(a)
    mode = {"reencode": bool(a.width or a.height or a.fps), "width": a.width, "height": a.height, "fps": a.fps}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    t0, cpu0 = time.time(), time.process_time()
    recs = [CameraRecorder(cid, url, out, a.duration or None, a.segment_seconds, mode, stop, a.min_free_gb) for cid, url in cams.items()]
    for r in recs:
        r.start()
    try:
        while any(r.is_alive() for r in recs):
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop.set()
    for r in recs:
        r.join(timeout=15)
    wall, cpu = time.time() - t0, time.process_time() - cpu0
    summary = {"started_utc": iso(t0), "wall_s": round(wall, 1), "cpu_s": round(cpu, 1),
               "cpu_percent_of_one_core": round(100 * cpu / max(wall, 1e-6), 1), "mode": "reencode" if mode["reencode"] else "remux",
               "cameras": {r.cam_id: {"segments": r.segments, "reconnects": r.reconnects} for r in recs}}
    (out / f"recording_summary_{utc_stamp(t0)}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
