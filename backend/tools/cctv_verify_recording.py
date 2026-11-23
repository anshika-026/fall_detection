"""Verify a recording made by tools.cctv_record (use it on the 60-second first test, and on any later recording).

  python -m tools.cctv_verify_recording ..\\validation\\recordings\\first_test --expect-seconds 60 --camera-env CCTV_URL_OFFICE1 --require-rtsp

Checks per segment: sidecar present and complete; file playable (every frame decodes); timestamps monotonic and the
duration agrees with the sidecar; sidecar UTC start agrees with the file name and is not in the future; the file can be read
the way the validation runner reads it (OpenCV, with increasing timestamps). Across segments: gaps, total duration vs --expect-seconds.
Credentials: every sidecar / summary / .log / .txt file AND the video files' bytes are searched for the camera's password and
URL (taken from the environment variable named by --camera-env) and for any user:password@ pattern.
--require-rtsp makes a recording from a local file FAIL (a file is not a camera). It prints what kind of source produced
the recording so a file test is never mistaken for a real-camera test. Exit code 0 = all checks passed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REQUIRED = ("camera_id", "file", "segment_start_utc", "segment_end_utc", "duration_s", "mode", "frames_or_packets", "width", "height", "ended_by",
            "source_kind")
_USERINFO = re.compile(rb"://[^:/@\s\x00]{1,64}:[^@/\s\x00]{1,128}@")
_NAME = re.compile(r"^(?P<cam>[A-Za-z0-9_-]+)_(?P<stamp>\d{8}T\d{6}Z)_\d{2}(_dup\d+)?$")


def parse_utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def secrets_from_env(var: str | None) -> list[bytes]:
    """The camera URL, its password (raw and percent-decoded) and user name: what must never appear in any output."""
    if not var or not os.environ.get(var):
        return []
    url = os.environ[var]
    out = [url.encode()]
    try:
        p = urlsplit(url)
        for v in (p.password, unquote(p.password or "")):
            if v and len(v) >= 3:
                out.append(v.encode())
    except ValueError:
        pass
    return list(dict.fromkeys(out))


def file_contains(path: Path, needles: list[bytes], pattern=None, chunk: int = 1 << 20) -> str | None:
    """Returns what was found ('secret' / 'url-with-password') or None. Streams the file; handles needles at chunk borders."""
    keep = max([len(n) for n in needles] + [200])
    tail = b""
    with open(path, "rb") as fh:
        while True:
            data = fh.read(chunk)
            if not data:
                return None
            buf = tail + data
            if any(n in buf for n in needles):
                return "secret value"
            if pattern is not None and pattern.search(buf):
                return "user:password@ pattern"
            tail = buf[-keep:]


class Verdict:
    def __init__(self):
        self.rows: list[tuple[str, str, str]] = []

    def add(self, ok: bool | None, name: str, detail: str):
        self.rows.append(("PASS" if ok else "WARN" if ok is None else "FAIL", name, detail))

    @property
    def failed(self) -> bool:
        return any(s == "FAIL" for s, _, _ in self.rows)


def check_segment(v: Verdict, mkv: Path, now: float) -> dict | None:
    import av

    name = mkv.name
    side_p = mkv.with_suffix(".json")
    if not side_p.exists():
        v.add(False, f"{name}: sidecar", "missing .json next to the video")
        side = None
    else:
        try:
            side = json.loads(side_p.read_text(encoding="utf-8"))
            miss = [k for k in REQUIRED if k not in side]
            v.add(not miss, f"{name}: sidecar", "complete" if not miss else f"missing fields {miss}")
        except ValueError:
            v.add(False, f"{name}: sidecar", "not valid JSON")
            side = None
    # playable + timestamps
    n = 0
    pts, bad_order = [], 0
    try:
        with av.open(str(mkv)) as c:
            vs = c.streams.video[0]
            for fr in c.decode(vs):
                n += 1
                if fr.pts is not None:
                    t = float(fr.pts * vs.time_base)
                    if pts and t < pts[-1] - 1e-6:
                        bad_order += 1
                    pts.append(t)
        v.add(n > 0, f"{name}: playable", f"{n} frames decoded" if n else "no frames decode")
    except Exception as e:
        v.add(False, f"{name}: playable", f"{type(e).__name__}: {str(e)[:100]}")
        return side
    span = (pts[-1] - pts[0]) if len(pts) > 1 else 0.0
    v.add(bad_order == 0, f"{name}: timestamps", f"monotonic, {span:.1f} s long, starts at {pts[0]:.2f} s" if bad_order == 0 and pts else f"{bad_order} out-of-order frame(s)")
    if side and side.get("media_span_s") is not None:
        v.add(abs(span - float(side["media_span_s"])) <= 1.5, f"{name}: video length vs sidecar", f"video {span:.1f} s, sidecar media span {side['media_span_s']} s")
    if side and "duration_s" in side:
        if side.get("source_kind") == "rtsp":
            # a live camera delivers in real time: footage length should equal the time spent recording; a big shortfall means stalls / lost frames
            tol = max(3.0, 0.1 * float(side["duration_s"]))
            v.add(abs(span - float(side["duration_s"])) <= tol, f"{name}: footage vs wall-clock", f"video {span:.1f} s, recorded for {side['duration_s']} s (tolerance {tol:.1f} s)")
        else:
            v.add(None, f"{name}: footage vs wall-clock", "not applicable: a file is read faster than real time")
    if side and "segment_start_utc" in side:
        try:
            start = parse_utc(side["segment_start_utc"])
            m = _NAME.match(mkv.stem)
            if m:
                stamp = datetime.strptime(m["stamp"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                v.add(abs((start - stamp).total_seconds()) <= 3, f"{name}: UTC start", f"{side['segment_start_utc']} matches the file name stamp")
            v.add(start.timestamp() <= now + 5 and parse_utc(side["segment_end_utc"]) >= start, f"{name}: UTC times", "start not in the future, end after start")
        except (ValueError, KeyError) as e:
            v.add(False, f"{name}: UTC times", f"unreadable ({e})")
    # read the way the runner does
    try:
        import cv2

        cap = cv2.VideoCapture(str(mkv))
        last, ok_pos, cnt = -1.0, True, 0
        while cnt < 120 and cap.grab():
            t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            ok_pos &= t >= last
            last, cnt = t, cnt + 1
        cap.release()
        v.add(cnt > 0 and ok_pos and last > 0, f"{name}: readable by the validation runner (OpenCV)", f"{cnt} frames read, timestamps increasing up to {last:.2f} s" if cnt else "OpenCV cannot read it")
    except ImportError:
        v.add(None, f"{name}: runner readability", "OpenCV not installed: not checked")
    return side


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--expect-seconds", type=float, default=0.0, help="requested recording length (checks the total)")
    ap.add_argument("--camera-env", default=None, help="env var holding the camera URL: its password/URL must not appear anywhere in the output files")
    ap.add_argument("--require-rtsp", action="store_true", help="FAIL unless every segment came from an RTSP camera (not a file)")
    ap.add_argument("--extra-log", action="append", default=[], help="additional text/log files to scan for credentials")
    a = ap.parse_args()
    v = Verdict()
    mkvs = sorted(a.folder.rglob("*.mkv"))
    if not mkvs:
        raise SystemExit(f"no .mkv recordings under {a.folder}")
    now = time.time()
    sides = [check_segment(v, m, now) for m in mkvs]
    ok_sides = [s for s in sides if s]
    kinds = {s.get("source_kind") for s in ok_sides}
    real = kinds == {"rtsp"}
    total = sum(float(s.get("duration_s", 0)) for s in ok_sides)
    v.add(True if kinds == {"rtsp"} else (False if a.require_rtsp else None), "source",
          "RTSP network camera" if kinds == {"rtsp"} else f"{sorted(map(str, kinds))}: NOT a real-camera recording (a file/other source)")
    if a.expect_seconds and not real:
        v.add(None, "total recorded", f"not checked: the source was not an RTSP camera ({total:.0f} s of wall-clock time)")
    elif a.expect_seconds:
        lo = 0.85 * a.expect_seconds
        v.add(total >= lo, "total recorded", f"{total:.0f} s in {len(mkvs)} segment(s) vs {a.expect_seconds:.0f} s requested (>= {lo:.0f} s expected)")
    if len(ok_sides) > 1:
        starts = sorted((parse_utc(s["segment_start_utc"]), parse_utc(s["segment_end_utc"])) for s in ok_sides if "segment_start_utc" in s)
        gaps = [(b[0] - a_[1]).total_seconds() for a_, b in zip(starts, starts[1:])]
        big = [g for g in gaps if g > 2.0]
        v.add(None if big else True, "gaps between segments", f"{len(big)} gap(s) over 2 s (largest {max(big):.0f} s): a stream drop/reconnect" if big else "none over 2 s")
    # credentials
    needles = secrets_from_env(a.camera_env)
    if a.camera_env and not needles:
        v.add(None, "credentials", f"environment variable {a.camera_env} is not set here: only the user:password@ pattern was searched")
    text_files = [p for p in a.folder.rglob("*") if p.suffix.lower() in (".json", ".log", ".txt")] + [Path(x) for x in a.extra_log]
    leaks = []
    for p in text_files:
        if p.exists() and (hit := file_contains(p, needles, _USERINFO)):
            leaks.append(f"{p.name}: {hit}")
    for m in mkvs:
        if hit := file_contains(m, needles):                        # raw bytes of the video container (tags, metadata)
            leaks.append(f"{m.name}: {hit}")
    v.add(not leaks, "credentials", f"none found in {len(text_files)} text files and {len(mkvs)} videos" if not leaks else "; ".join(leaks))
    w = max(len(n) for _, n, _ in v.rows)
    for s, n, d in v.rows:
        print(f"[{s}] {n:<{w}}  {d}")
    print("\nRESULT:", "FAILED" if v.failed else "all checks passed" + (" (see WARN lines)" if any(s == "WARN" for s, _, _ in v.rows) else ""))
    if kinds != {"rtsp"}:
        print("NOTE: this recording did not come from an RTSP camera, so it is not real-camera evidence.")
    sys.exit(1 if v.failed else 0)


if __name__ == "__main__":
    main()
