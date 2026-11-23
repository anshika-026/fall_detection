"""Preflight check for ONE camera before any recording. It never records and never starts a long job.

  PowerShell:  $env:CCTV_URL_OFFICE1 = "rtsp://user:pass@192.168.1.20:554/stream1"
               python -m tools.cctv_preflight --camera office-1=CCTV_URL_OFFICE1
               python -m tools.cctv_preflight --db-camera office-1=3        # camera #3 of the backend database
  Options:     --probe-seconds 8 (max 30)   --out ..\\validation\\recordings   --json result.json

Checks, in this order (each prints OK / WARN / FAIL and, on trouble, the likely cause):
  dependencies (PyAV, OpenCV, numpy, h264/hevc decoders, ultralytics + weights for validation)
  recording folder (created if missing, write test) and free disk space
  available memory
  camera network reachability: DNS, TCP connect to the RTSP port   <- is it reachable from THIS machine?
  RTSP open (authentication, stream path, timeouts, protocol)
  video stream, codec (h264 / hevc / mjpeg supported), resolution, decoding of real frames
  actual frame rate over the probe window, keyframe interval, timestamp sanity, bitrate -> disk per hour
One camera per run on purpose: get one camera working before trying several. The URL (password) is never printed or saved.
A local file given as the "camera" is accepted for testing the tools and is labelled "FILE, NOT A CAMERA".
Exit code 0 = no FAIL, 1 = at least one FAIL.
"""
from __future__ import annotations

import argparse
import ctypes
import ipaddress
import json
import os
import re
import shutil
import socket
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.cctv_record import resolve_cameras, scrub  # noqa: E402

OK, WARN, FAIL = "OK", "WARN", "FAIL"
SUPPORTED_CODECS = {"h264": "H.264", "hevc": "H.265", "mjpeg": "MJPEG", "mpeg4": "MPEG-4"}
ANALYSIS_FPS = 5.0


@dataclass
class Check:
    name: str
    status: str
    detail: str
    hint: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)
    info: dict = field(default_factory=dict)

    def add(self, name, status, detail, hint=""):
        self.checks.append(Check(name, status, detail, hint))
        return status

    @property
    def failed(self) -> bool:
        return any(c.status == FAIL for c in self.checks)


# ------------------------------------------------------------------------------------ helpers
def classify_open_error(text: str) -> tuple[str, str]:
    """-> (what happened, what to check) from FFmpeg's error text."""
    t = text.lower()
    if "protocol not found" in t or "invalid data" in t or "unsupported" in t:
        return ("the stream or protocol is not supported", "use an rtsp:// URL to an H.264/H.265 stream; HTTP/ONVIF-only or proprietary streams are not supported")
    if "401" in t or "unauthorized" in t or "authorization failed" in t:
        return ("the camera answered but rejected the login (HTTP 401)",
                "check user name and password in the URL (special characters such as @ : / # must be percent-encoded), and that the account may view RTSP")
    if "403" in t or "forbidden" in t:
        return ("the camera refused access (403)", "the account lacks RTSP permission, or RTSP/ONVIF access is disabled in the camera settings")
    if "404" in t or "not found" in t:
        return ("the camera is there but has no stream at that path (404)",
                "check the stream path / channel: it differs per vendor (e.g. /stream1, /Streaming/Channels/101, /cam/realmonitor?channel=1&subtype=0)")
    if "timed out" in t or "timeout" in t or "etimedout" in t:
        return ("no answer within the timeout", "firewall, wrong IP/port, camera on another VLAN/network, or the camera is overloaded or offline")
    if "connection refused" in t or "econnrefused" in t:
        return ("the host is reachable but nothing accepts connections on that port", "wrong port (554 is the default), or RTSP is switched off in the camera")
    if "no route" in t or "network is unreachable" in t or "unreachable" in t:
        return ("no network route to the camera", "this machine is not on the camera's network: check the LAN/VPN")
    if "name or service not known" in t or "getaddrinfo" in t or "nodename" in t or "could not resolve" in t:
        return ("the host name does not resolve", "check the host name, or use the camera's IP address")
    return ("the stream could not be opened", "run with --probe-seconds 15 once more; if it persists the message above is all FFmpeg reported")


def memory_gb() -> tuple[float | None, float | None]:
    """(total, available) in GB, or (None, None) when it cannot be read (no extra dependency used)."""
    try:
        if os.name == "nt":
            class MS(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                            ("tpf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong),
                            ("ae", ctypes.c_ulonglong)]
            m = MS()
            m.l = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.tp / 1e9, m.ap / 1e9
        info = {k: int(v.split()[0]) for k, v in (ln.split(":", 1) for ln in open("/proc/meminfo"))}
        return info["MemTotal"] / 1e6, info["MemAvailable"] / 1e6
    except Exception:
        return None, None


def source_kind(url: str) -> str:
    return "rtsp" if url.lower().startswith(("rtsp://", "rtsps://")) else "file"


# ------------------------------------------------------------------------------------ checks
def check_dependencies(r: Report) -> None:
    try:
        import av

        r.add("PyAV", OK, f"version {av.__version__}")
        for name in ("h264", "hevc"):
            try:
                av.codec.Codec(name, "r")
                r.add(f"{name} decoder", OK, "available")
            except Exception:
                r.add(f"{name} decoder", WARN if name == "hevc" else FAIL, "missing", "reinstall PyAV (pip install --force-reinstall av)")
    except ImportError:
        r.add("PyAV", FAIL, "not installed", "pip install av  (see backend/requirements.txt)")
    for mod, need in (("cv2", "validation (video decoding)"), ("numpy", "validation"), ("ultralytics", "validation (pose model)")):
        try:
            __import__(mod)
            r.add(mod, OK, "installed")
        except ImportError:
            r.add(mod, WARN, f"not installed (needed for {need}; recording does not need it)", "pip install -r requirements.txt")
    w = ROOT / "models" / "yolov8n-pose.pt"
    r.add("pose weights", OK if w.exists() else WARN, str(w.name) + (" present" if w.exists() else " missing (needed for validation only)"),
          "" if w.exists() else "python -m tools.fetch_models")


def check_output_and_disk(r: Report, out: Path, min_free_gb: float) -> None:
    try:
        out.mkdir(parents=True, exist_ok=True)
        probe = out / f".write_test_{os.getpid()}"
        probe.write_bytes(b"x")
        probe.unlink()
        r.add("recording folder", OK, f"{out} is writable")
    except OSError as e:
        r.add("recording folder", FAIL, f"{out}: {e.strerror or e}", "choose another folder with --out, or fix the permissions")
        return
    free = shutil.disk_usage(out).free / 1e9
    r.info["disk_free_gb"] = round(free, 1)
    st = FAIL if free < min_free_gb else WARN if free < 20 else OK
    r.add("disk space", st, f"{free:.1f} GB free", "the recorder stops below its --min-free-gb (default 2) ; free some space" if st != OK else "")


def check_memory(r: Report) -> None:
    total, avail = memory_gb()
    if total is None:
        r.add("memory", WARN, "could not be read on this system")
        return
    r.info["memory_gb"] = {"total": round(total, 1), "available": round(avail, 1)}
    st = FAIL if avail < 0.5 else WARN if avail < 2.0 else OK
    r.add("memory", st, f"{avail:.1f} GB available of {total:.1f} GB", "recording needs little, but validation (the pose model) wants about 2 GB free" if st != OK else "")


def check_network(r: Report, url: str) -> bool:
    parts = urlsplit(url)
    host, port = parts.hostname, parts.port or (322 if parts.scheme == "rtsps" else 554)
    if not host:
        r.add("camera URL", FAIL, "no host in the URL", "expected rtsp://user:pass@host:554/path")
        return False
    r.info["camera_host"] = f"{host}:{port}"                    # host and port are not secrets; user and password never are shown
    try:
        addrs = {a[4][0] for a in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    except socket.gaierror:
        what, hint = classify_open_error("name or service not known")
        r.add("DNS", FAIL, f"{host}: {what}", hint)
        return False
    ip = sorted(addrs)[0]
    private = False
    try:
        private = ipaddress.ip_address(ip).is_private
    except ValueError:
        pass
    r.add("DNS", OK, f"{host} -> {ip} ({'private/LAN address' if private else 'public address'})")
    try:
        with socket.create_connection((ip, port), timeout=5):
            pass
        r.add("TCP connect", OK, f"{ip}:{port} accepts connections from this machine")
        return True
    except socket.timeout:
        what, hint = classify_open_error("timed out")
    except ConnectionRefusedError:
        what, hint = classify_open_error("connection refused")
    except OSError as e:
        what, hint = classify_open_error(f"{e.strerror or e}")
    if private:
        hint += " (it is a private address: the recorder must run on, or be VPN-connected to, that network)"
    r.add("TCP connect", FAIL, f"{ip}:{port}: {what}", hint)
    return False


def probe_stream(r: Report, url: str, kind: str, seconds: float) -> None:
    import av

    opts = {"rtsp_transport": "tcp"} if kind == "rtsp" else {}
    try:
        inp = av.open(url, options=opts, timeout=(8.0, 8.0))
    except Exception as e:
        what, hint = classify_open_error(f"{type(e).__name__}: {e}")
        r.add("RTSP open" if kind == "rtsp" else "file open", FAIL, what + f"  [FFmpeg: {scrub(str(e), url)[:160]}]", hint)
        return
    try:
        r.add("RTSP open" if kind == "rtsp" else "file open", OK, "stream opened and described by the camera" if kind == "rtsp" else "file opened (FILE, NOT A CAMERA)")
        if not inp.streams.video:
            r.add("video stream", FAIL, "no video stream (audio-only or an unsupported stream)", "pick the video channel/sub-stream of the camera in the URL")
            return
        vs = inp.streams.video[0]
        cc = vs.codec_context
        codec = cc.name
        r.info.update({"codec": codec, "width": cc.width, "height": cc.height, "profile": getattr(cc, "profile", None)})
        if codec in SUPPORTED_CODECS:
            r.add("codec", OK if codec in ("h264", "hevc") else WARN, f"{SUPPORTED_CODECS[codec]} ({codec})",
                  "" if codec in ("h264", "hevc") else "supported, but MJPEG streams are large: expect high disk use")
        else:
            r.add("codec", FAIL, f"{codec}: not supported", "set the camera's stream to H.264 (or H.265)")
        r.add("resolution", OK if min(cc.width, cc.height) >= 360 else WARN, f"{cc.width}x{cc.height}",
              "" if min(cc.width, cc.height) >= 360 else "very small: the pose model may struggle; use the main stream, not a thumbnail sub-stream")
        # ---- probe: arrival times, timestamps, keyframes, real decode
        t0 = time.time()
        n = key = corrupt = backwards = 0
        first = last = None
        arr, pts_s, key_t, nbytes = [], [], [], 0
        prev_dts = None
        decoded = decode_err = 0
        size = None
        for pkt in inp.demux(vs):
            now = time.time()
            if pkt.size == 0:
                continue
            n += 1
            nbytes += pkt.size
            arr.append(now - t0)
            if pkt.pts is not None:
                pts_s.append(float(pkt.pts * vs.time_base))
            if pkt.dts is not None:
                if prev_dts is not None and pkt.dts < prev_dts:
                    backwards += 1
                prev_dts = pkt.dts
            if pkt.is_keyframe:
                key += 1
                key_t.append(arr[-1] if kind == "rtsp" else (pts_s[-1] if pts_s else arr[-1]))
            if pkt.is_corrupt:
                corrupt += 1
            if decoded < 20 and not decode_err:
                try:
                    for fr in pkt.decode():
                        decoded += 1
                        size = (fr.width, fr.height)
                except Exception as e:
                    decode_err = str(e)
            if (kind == "rtsp" and now - t0 >= seconds) or (kind == "file" and n >= int(seconds * 60)):
                break
        if n < 3:
            r.add("frames", FAIL, f"only {n} packets arrived in {seconds:.0f} s", "the stream opened but does not deliver video: check bandwidth, the camera load and the URL's sub-stream")
            return
        span_wall = max(arr[-1] - arr[0], 1e-6)
        span_pts = (pts_s[-1] - pts_s[0]) if len(pts_s) > 2 else 0.0
        fps_wall = (n - 1) / span_wall
        fps_pts = (len(pts_s) - 1) / span_pts if span_pts > 0 else None
        fps = fps_wall if kind == "rtsp" else (fps_pts or fps_wall)
        r.info["fps_measured"] = round(fps, 2)
        r.info["fps_nominal"] = float(vs.average_rate) if vs.average_rate else None
        st = OK if fps >= ANALYSIS_FPS else WARN
        extra = f" (timestamps say {fps_pts:.1f}; delivered {fps_wall:.1f})" if kind == "rtsp" and fps_pts and abs(fps_pts - fps_wall) / fps_pts > 0.3 else ""
        r.add("frame rate", st, f"{fps:.1f} fps measured over {span_wall if kind == 'rtsp' else span_pts:.1f} s{extra}",
              "" if st == OK else f"below the {ANALYSIS_FPS:.0f} fps analysis rate: raise the camera fps or reduce load" if fps < ANALYSIS_FPS else "")
        if kind == "rtsp" and fps_pts and abs(fps_pts - fps_wall) / fps_pts > 0.3:
            r.add("frame delivery", WARN, "frames arrive at a clearly different rate than their timestamps", "network congestion or packet loss: recordings will have gaps; prefer a wired link / TCP")
        if len(key_t) >= 2:
            gop = float(sorted(b - a for a, b in zip(key_t, key_t[1:]))[len(key_t) // 2 - 1 if len(key_t) > 2 else 0])
            r.info["keyframe_interval_s"] = round(gop, 2)
            r.add("keyframe interval", OK if gop <= 4 else WARN, f"about {gop:.1f} s",
                  "" if gop <= 4 else "long: recordings can only start/rotate at keyframes, so segments start up to this late; set the camera's I-frame interval to 1-2 s")
        else:
            r.add("keyframe interval", WARN, f"fewer than 2 keyframes seen in the probe ({key})", "lengthen --probe-seconds, or the camera's I-frame interval is very long")
        r.add("timestamps", OK if backwards == 0 else WARN, "monotonic" if backwards == 0 else f"{backwards} backwards step(s)", "" if backwards == 0 else "unstable timestamps: recordings may stutter")
        if corrupt:
            r.add("packet integrity", WARN, f"{corrupt} corrupt packet(s) of {n}", "packet loss on the path")
        if decode_err:
            r.add("decoding", FAIL, f"could not decode frames: {scrub(decode_err, url)[:120]}", "the decoder cannot read this stream (H.265 profile or camera-specific extension): try the camera's H.264 sub-stream")
        elif decoded:
            r.add("decoding", OK, f"{decoded} frames decoded, size {size[0]}x{size[1]}")
        else:
            r.add("decoding", WARN, "no frame decoded in the first packets (waiting for a keyframe)", "lengthen --probe-seconds")
        mbit = nbytes * 8 / span_wall / 1e6 if kind == "rtsp" else nbytes * 8 / max(span_pts, 1e-6) / 1e6
        per_hour = mbit / 8 * 3600 / 1000
        r.info["bitrate_mbit"] = round(mbit, 2)
        free = r.info.get("disk_free_gb")
        r.add("bitrate / disk", OK if (free is None or free > per_hour * 3) else WARN, f"{mbit:.1f} Mbit/s = about {per_hour:.1f} GB per hour per camera",
              "" if (free is None or free > per_hour * 3) else "free disk would last under 3 hours")
    finally:
        inp.close()


def run(args) -> Report:
    r = Report()
    r.info["source_kind"] = None
    check_dependencies(r)
    check_output_and_disk(r, Path(args.out), args.min_free_gb)
    check_memory(r)
    try:
        cams = resolve_cameras(args)
    except SystemExit as e:
        r.add("camera input", FAIL, str(e), "give exactly one of --camera ID=ENVVAR or --db-camera ID=N (see --help)")
        return r
    if len(cams) != 1:
        r.add("camera input", FAIL, f"{len(cams)} cameras given", "preflight one camera per run: get one working before trying several")
        return r
    (cid, url), = cams.items()
    kind = source_kind(url)
    r.info.update({"camera_id": cid, "source_kind": kind})
    r.add("camera input", OK, f"'{cid}' ({'RTSP network camera' if kind == 'rtsp' else 'LOCAL FILE, NOT A CAMERA: this only tests the tools'})")
    if kind == "rtsp":
        if not check_network(r, url):
            return r
    probe_stream(r, url, kind, min(max(args.probe_seconds, 2.0), 30.0))
    return r


def render(r: Report, cam_spec: str) -> str:
    sym = {OK: "[ OK ]", WARN: "[WARN]", FAIL: "[FAIL]"}
    L = []
    for c in r.checks:
        L.append(f"{sym[c.status]} {c.name:<18} {c.detail}")
        if c.hint:
            L.append(f"       -> {c.hint}")
    kind = r.info.get("source_kind")
    L.append("")
    if r.failed:
        L.append("RESULT: NOT READY. Fix the FAIL items above and run the preflight again.")
    else:
        L.append("RESULT: ready to record." + ("  (WARN items are worth reading first.)" if any(c.status == WARN for c in r.checks) else ""))
        if kind == "file":
            L.append("NOTE: the source was a local file, so this says nothing about a real camera.")
        else:
            L.append("Next, a 60-second test recording (this does NOT start a long recording):")
            L.append(f"  python -m tools.cctv_record {cam_spec} --duration 60 --out ..\\validation\\recordings\\first_test")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--camera", action="append", metavar="ID=ENVVAR")
    ap.add_argument("--db-camera", action="append", metavar="ID=N")
    ap.add_argument("--config", default=None, help="a cameras.json with exactly one camera")
    ap.add_argument("--out", default=str(ROOT.parent / "validation" / "recordings"))
    ap.add_argument("--probe-seconds", type=float, default=8.0)
    ap.add_argument("--min-free-gb", type=float, default=2.0)
    ap.add_argument("--json", default="", help="also write the result (no URL, no password) to this file")
    a = ap.parse_args()
    r = run(a)
    spec = (f"--camera {a.camera[0]}" if a.camera else f"--db-camera {a.db_camera[0]}" if a.db_camera else f"--config {a.config}") if (a.camera or a.db_camera or a.config) else "--camera ID=ENVVAR"
    print(render(r, spec))
    if a.json:
        Path(a.json).write_text(json.dumps({"checks": [c.__dict__ for c in r.checks], "info": r.info, "ready": not r.failed}, indent=2), encoding="utf-8")
    sys.exit(1 if r.failed else 0)


if __name__ == "__main__":
    main()
