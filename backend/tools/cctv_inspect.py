"""Read-only readiness check for EXPORTED / FILE footage (e.g. clips the camera owner exports from a recorder).

  python -m tools.cctv_inspect ..\\validation\\recordings\\office_exported
  python -m tools.cctv_inspect ..\\validation\\recordings\\office_exported\\export1.mp4 --inventory ..\\validation\\results\\office_exported_inventory.json

For every video file it checks whether the validation pipeline can really use it: readable by PyAV (cutting) AND OpenCV (the
validation runner), container timestamps present and increasing, frame rate measured from the timestamps (not trusted from the
header), variable frame rate, duration agreement between PyAV, OpenCV and the container, codec, resolution, keyframe spacing
(where a cut can start). Verdicts: READY / USABLE WITH WARNINGS / UNUSABLE, each with what to ask the owner to re-export.
It never writes to, moves or changes the footage. --inventory writes a JSON record (SHA-256, size, format, verdict; never overwrites).
Everything here is FILE / EXPORTED FOOTAGE: it says nothing about live RTSP connectivity or about the physical camera's live stream.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SUFFIXES = (".mp4", ".mkv", ".avi", ".mov", ".ts", ".mpg", ".mpeg", ".m4v", ".flv", ".wmv", ".webm", ".264", ".h264", ".265", ".h265", ".dav")
SUPPORTED_CODECS = {"h264", "hevc", "mjpeg", "mpeg4", "mpeg2video", "vp8", "vp9"}
RAW_SUFFIXES = (".264", ".h264", ".265", ".h265")


def sha256(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while data := fh.read(chunk):
            h.update(data)
    return h.hexdigest()


def inspect_file(path: Path, with_hash: bool = True) -> dict:
    """Facts + verdict for one file. Never raises for a bad file: the problem is reported."""
    import av

    r = {"file": path.name, "size_mb": round(path.stat().st_size / 1e6, 2), "source_kind": "exported_file", "issues": [], "warnings": []}
    iss, warn = r["issues"], r["warnings"]
    if path.suffix.lower() == ".dav":
        iss.append("proprietary DVR format (.dav): re-export as MP4 or AVI (H.264) from the recorder's own player/export menu")
    try:
        inp = av.open(str(path))
    except Exception as e:
        iss.append(f"cannot be opened ({type(e).__name__}: {str(e)[:80]}): re-export as MP4 or AVI (H.264)")
        r["verdict"] = "UNUSABLE"
        return r
    try:
        if not inp.streams.video:
            iss.append("no video stream")
            r["verdict"] = "UNUSABLE"
            return r
        vs = inp.streams.video[0]
        cc = vs.codec_context
        r.update({"container": inp.format.name, "codec": cc.name, "width": cc.width, "height": cc.height,
                  "audio_streams": len(inp.streams.audio), "nominal_fps": float(vs.average_rate) if vs.average_rate else None,
                  "container_duration_s": round(inp.duration / 1e6, 2) if inp.duration else None})
        if cc.name not in SUPPORTED_CODECS:
            iss.append(f"codec {cc.name} is not supported by the pipeline: re-export as H.264")
        if min(cc.width, cc.height) < 360:
            warn.append(f"small picture ({cc.width}x{cc.height}): the pose model works poorly on very small people; use the main stream, not a sub-stream")
        pts, keys, n, bad_order, no_pts = [], [], 0, 0, 0
        try:
            for fr in inp.decode(vs):
                n += 1
                if fr.pts is None:
                    no_pts += 1
                    continue
                t = float(fr.pts * vs.time_base)
                if pts and t < pts[-1] - 1e-6:
                    bad_order += 1
                pts.append(t)
                if fr.key_frame:
                    keys.append(t)
        except Exception as e:
            iss.append(f"decoding stops with an error after {n} frames ({str(e)[:60]}): the file is damaged or truncated")
        r["frames_decoded"] = n
        if n == 0:
            iss.append("no frame could be decoded")
            r["verdict"] = "UNUSABLE"
            return r
        if path.suffix.lower() in RAW_SUFFIXES or no_pts > 0.5 * n or len(pts) < 2:
            iss.append("raw video stream without container timestamps: frame times would be guessed, so event times would be wrong. Re-export as MP4 or AVI")
        else:
            span = pts[-1] - pts[0]
            fps = (len(pts) - 1) / span if span > 0 else 0.0
            r["measured_fps"] = round(fps, 2)
            r["decoded_span_s"] = round(span, 2)
            if bad_order > 2:
                warn.append(f"{bad_order} out-of-order frame timestamps (B-frame ordering or a damaged index)")
            gaps = [b - a for a, b in zip(sorted(pts), sorted(pts)[1:])]
            if gaps:
                med = sorted(gaps)[len(gaps) // 2]
                big = sum(g > 3 * med and g > 0.5 for g in gaps)
                vfr = (max(gaps) - min(gaps)) > 0.5 * med and med > 0
                r["largest_gap_s"] = round(max(gaps), 2)
                if big:
                    warn.append(f"{big} gap(s) over 0.5 s in the footage (motion-triggered recording or lost frames): events in a gap cannot be seen; only continuous stretches are valid for confirmation")
                elif vfr and fps and fps < 5:
                    warn.append(f"frame rate is low and varies ({fps:.1f} fps measured)")
            if fps and fps < 5:
                warn.append(f"only {fps:.1f} fps: below the 5 fps analysis rate; a fast fall may be missed")
            if r["nominal_fps"] and fps and abs(fps - r["nominal_fps"]) / r["nominal_fps"] > 0.2:
                warn.append(f"header says {r['nominal_fps']:.1f} fps but the timestamps give {fps:.1f}: variable frame rate; trust the timestamps")
            if len(keys) >= 2:
                kg = sorted(b - a for a, b in zip(keys, keys[1:]))[len(keys) // 2 - 1 if len(keys) > 2 else 0]
                r["keyframe_interval_s"] = round(kg, 2)
                if kg > 4:
                    warn.append(f"keyframes about {kg:.1f} s apart: a cut can start up to that much before the time you ask for")
            elif span > 6:
                warn.append("fewer than 2 keyframes found: cutting may not work; re-export with regular keyframes")
    finally:
        inp.close()
    # what the validation runner will actually use: OpenCV
    try:
        import cv2

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            iss.append("OpenCV (used by the validation runner) cannot open it: re-export as MP4 (H.264)")
        else:
            c, last, mono = 0, -1.0, True
            while cap.grab():
                t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                if t > 0:
                    mono &= t >= last - 1e-6
                    last = t
                c += 1
            cap.release()
            r["opencv_frames"] = c
            r["opencv_span_s"] = round(last, 2) if last > 0 else None
            if c == 0:
                iss.append("OpenCV reads no frames: re-export as MP4 (H.264)")
            elif abs(c - r["frames_decoded"]) > max(2, 0.02 * r["frames_decoded"]):
                warn.append(f"PyAV decodes {r['frames_decoded']} frames but OpenCV {c}: the runner sees a different number of frames")
            if r.get("decoded_span_s") and r["opencv_span_s"] and abs(r["opencv_span_s"] - r["decoded_span_s"]) > max(1.0, 0.05 * r["decoded_span_s"]):
                warn.append(f"duration disagrees (container timestamps {r['decoded_span_s']} s, OpenCV {r['opencv_span_s']} s): event times could be off")
    except ImportError:
        warn.append("OpenCV is not installed: the runner's reader was not checked")
    if with_hash:
        r["sha256"] = sha256(path)
    r["verdict"] = "UNUSABLE" if iss else ("USABLE WITH WARNINGS" if warn else "READY")
    return r


def render(r: dict) -> str:
    L = [f"[{r['verdict']}] {r['file']}  ({r.get('container', '?')}, {r.get('codec', '?')}, {r.get('width', '?')}x{r.get('height', '?')}, "
         f"{r.get('measured_fps', '?')} fps measured, {r.get('decoded_span_s', r.get('container_duration_s', '?'))} s, {r['size_mb']} MB)"]
    L += [f"      PROBLEM: {m}" for m in r["issues"]] + [f"      warning: {m}" for m in r["warnings"]]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", type=Path, help="an exported video file or a folder of them")
    ap.add_argument("--inventory", type=Path, default=None, help="write a JSON inventory (SHA-256 etc.); refuses to overwrite")
    ap.add_argument("--no-hash", action="store_true", help="skip SHA-256 (faster for very large exports)")
    a = ap.parse_args()
    if not a.path.exists():
        raise SystemExit(f"{a.path} does not exist")
    files = [a.path] if a.path.is_file() else sorted(p for p in a.path.rglob("*") if p.is_file() and p.suffix.lower() in SUFFIXES)
    if a.inventory and a.inventory.exists():
        raise SystemExit(f"{a.inventory} already exists: not overwriting")
    if not files:
        raise SystemExit(f"no video files found under {a.path} (looked for {', '.join(SUFFIXES)})")
    print("FILE / EXPORTED FOOTAGE check (read-only). This says nothing about live RTSP or the physical camera.\n")
    rows = []
    for f in files:
        rows.append(inspect_file(f, not a.no_hash))
        print(render(rows[-1]))
    counts = {v: sum(r["verdict"] == v for r in rows) for v in ("READY", "USABLE WITH WARNINGS", "UNUSABLE")}
    print(f"\n{len(rows)} file(s): {counts['READY']} ready, {counts['USABLE WITH WARNINGS']} usable with warnings, {counts['UNUSABLE']} unusable")
    print("Wall-clock time is NOT known for exported files: take it from the picture's time overlay or the export name, and pass it to cctv_clip --source-start.")
    if a.inventory:
        a.inventory.parent.mkdir(parents=True, exist_ok=True)
        a.inventory.write_text(json.dumps({"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "classification": "FILE / EXPORTED FOOTAGE",
                                           "files": rows}, indent=2), encoding="utf-8")
        print("inventory written:", a.inventory)
    sys.exit(1 if counts["UNUSABLE"] else 0)


if __name__ == "__main__":
    main()
