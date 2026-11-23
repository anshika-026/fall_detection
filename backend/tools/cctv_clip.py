"""Cut a clip out of a recording WITHOUT re-encoding (ffmpeg is not required).

  python -m tools.cctv_clip ..\\validation\\recordings\\office-1\\office-1_20261201T101500Z_03.mkv ^
        --start 125 --end 190 --event-at 152.5 --out ..\\validation\\independent\\fall_standing\\office1_fall01.mkv

--start/--end/--event-at are seconds from the FIRST FRAME of the source file (what a media player shows as 0:00). Packets are copied, so the clip begins at the
last keyframe at or before --start (the tool prints the real start). With --event-at it prints the value to use as
`event_time_s` in the clip's metadata (event time relative to the CLIP start). Keep >= 20 s after a staged fall.
The clip's recording times are written to a sidecar (<clip>.json) so `cctv_meta new` can pre-fill them; that is recording fact,
not ground truth. An existing --out is never overwritten.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import av


RAW_SUFFIXES = (".264", ".h264", ".265", ".h265")


def cut(src: Path, start: float, end: float, out: Path) -> dict:
    """Times are seconds from the FIRST FRAME of `src` (what a media player shows as 0:00), whatever the container's own
    timestamp origin is (MPEG-TS, FLV and some exports start at a non-zero value)."""
    if out.exists():
        raise SystemExit(f"{out} already exists: not overwriting")
    if end <= start:
        raise SystemExit("--end must be after --start")
    if src.suffix.lower() in RAW_SUFFIXES:
        raise SystemExit(f"{src.name} is a raw video stream without timestamps and cannot be cut reliably: ask for an MP4 or AVI (H.264) export")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        inp = av.open(str(src))
    except Exception as e:
        raise SystemExit(f"{src.name} cannot be opened ({type(e).__name__}): ask for an MP4 or AVI (H.264) export") from None
    if not inp.streams.video:
        inp.close()
        raise SystemExit(f"{src.name} has no video stream")
    vs = inp.streams.video[0]
    origin = float(vs.start_time * vs.time_base) if vs.start_time is not None else (inp.start_time / 1e6 if inp.start_time else 0.0)
    start, end = start + origin, end + origin
    try:
        try:
            inp.seek(int(start / vs.time_base), stream=vs, backward=True, any_frame=False)
        except Exception as e:
            raise SystemExit(f"{src.name} cannot be seeked ({type(e).__name__}): ask for an MP4 or AVI (H.264) export") from None
        outc = av.open(str(out), "w", format="matroska")
        ovs = outc.add_stream_from_template(vs)
        base = first = last = None
        n = 0
        try:
            for pkt in inp.demux(vs):
                if pkt.dts is None or pkt.size == 0:
                    continue
                t = float(pkt.pts * vs.time_base) if pkt.pts is not None else float(pkt.dts * vs.time_base)
                if base is None:
                    if not pkt.is_keyframe:
                        continue                                    # a clip must start on a keyframe to be playable
                    base, first = pkt.dts, t
                if t > end:
                    break
                pkt.dts -= base
                pkt.pts = None if pkt.pts is None else pkt.pts - base
                pkt.stream = ovs
                outc.mux(pkt)
                last, n = t, n + 1
        finally:
            outc.close()
    finally:
        inp.close()
    if not n or last < start:                      # nothing inside [start, end]: a backward seek past the end lands on the last keyframe
        out.unlink(missing_ok=True)
        raise SystemExit("no video between --start and --end (is the time inside the recording?)")
    return {"actual_start_s": first - origin, "actual_end_s": last - origin, "packets": n, "origin_s": origin}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path)
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--event-at", type=float, default=None, help="staged-event time, seconds from the recording start")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--source-start", default=None,
                    help="EXPORTED footage only: wall-clock time of the source file's first frame, ISO-8601 with its offset "
                         "(e.g. 2026-12-01T10:15:00+05:30, read from the picture's time overlay); stored in the clip sidecar as UTC")
    a = ap.parse_args()
    if not a.src.is_file():
        raise SystemExit(f"{a.src} not found")
    src_start = None
    if a.source_start:
        try:
            src_start = datetime.fromisoformat(a.source_start.replace("Z", "+00:00"))
        except ValueError:
            raise SystemExit("--source-start must be ISO-8601, e.g. 2026-12-01T10:15:00+05:30 or 2026-12-01T04:45:00Z") from None
        if src_start.tzinfo is None:
            raise SystemExit("--source-start needs a time zone (+05:30 or Z): an exported file's local time is ambiguous without it")
    side_src = a.src.with_suffix(".json")
    if src_start and side_src.exists():
        raise SystemExit(f"{a.src.name} already has a recorder sidecar with its own times: do not pass --source-start")
    info = cut(a.src, a.start, a.end, a.out)
    side = {}
    try:
        if side_src.exists():
            s = json.loads(side_src.read_text(encoding="utf-8"))
            t0 = datetime.fromisoformat(s["segment_start_utc"].replace("Z", "+00:00"))
            kind = {"rtsp": "rtsp_recording", "file": "file_test"}.get(s.get("source_kind"), s.get("source_kind"))
            side = {"camera_id": s.get("camera_id"), "cut_from": a.src.name, "source_kind": kind}
        else:
            # not made by cctv_record: exported / file footage; its wall-clock time is only known if the human supplies it
            t0 = src_start
            side = {"cut_from": a.src.name, "source_kind": "exported_file"}
            if src_start:
                side["time_basis"] = "human-supplied --source-start (from the picture overlay / export name), converted to UTC"
        if t0 is not None:
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            side["segment_start_utc"] = (t0.astimezone(timezone.utc) + timedelta(seconds=info["actual_start_s"])).strftime(fmt)
            side["segment_end_utc"] = (t0.astimezone(timezone.utc) + timedelta(seconds=info["actual_end_s"])).strftime(fmt)
        a.out.with_suffix(".json").write_text(json.dumps(side, indent=2), encoding="utf-8")
    except (KeyError, ValueError):
        side = {}
    print(f"clip written: {a.out}  ({info['actual_end_s'] - info['actual_start_s']:.1f} s, starts at {info['actual_start_s']:.2f} s in the recording)")
    if a.event_at is not None:
        rel = a.event_at - info["actual_start_s"]
        if rel < 0 or a.event_at > info["actual_end_s"]:
            print("WARNING: --event-at is outside the clip")
        print(f"event_time_s for the metadata: {rel:.1f}   (leaves {info['actual_end_s'] - a.event_at:.1f} s of footage after the event; want >= 20)")
    if side:
        print("clip sidecar written (" + side.get("source_kind", "?") + (", with recording times" if "segment_start_utc" in side else ", no wall-clock times: pass --source-start for exported files") + "); `cctv_meta new` will pre-fill it")


if __name__ == "__main__":
    main()
