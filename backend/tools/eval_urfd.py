"""Offline evaluation of the full detection chain on the UR Fall Detection dataset
(Kwolek & Kepski, University of Rzeszow; CC BY-NC-SA 4.0, non-commercial academic use).

  real yolov8n-pose + ultralytics ByteTrack  ->  CameraFallEngine  ->  events

Only camera 0 RGB (parallel to the floor) is used; sequence labels come from the
file names (fall-XX = a fall, adl-XX = activities of daily living). The dataset has
SEQUENCE-level labels, not per-frame ones, so this measures:
  - fall sequences : was a fall CONFIRMED (and when, relative to the sequence)?
  - ADL sequences  : was a fall wrongly CONFIRMED (false alarm) or only POSSIBLE?

IMPORTANT limits (also written to docs/EVALUATION.md): this is a public lab dataset
with acted falls, not CCTV footage; sequences are only a few seconds long; and any
threshold tuned on these sequences must not be reported as accuracy on them.

Run (from backend/):  python -m tools.eval_urfd --zips ../datasets/urfd/zips --out ../docs/eval/urfd_default.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import zipfile
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from falldet.fall_analysis.config import FallConfig, from_settings  # noqa: E402
from falldet.fall_analysis.engine import CameraFallEngine  # noqa: E402

SRC_FPS = 30.0
_INFER_MS: list[float] = []     # per-frame model.track() wall time (ms), whole run
_MEMBER = re.compile(r"^[\w.-]+/([\w.-]+\.png)$")


def extract(zip_path: Path, dest: Path) -> list[Path]:
    """Extracts only flat PNG members into `dest` (a fresh directory), by basename,
    so a malicious archive cannot write elsewhere."""
    dest.mkdir(parents=True, exist_ok=True)
    out = []
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            m = _MEMBER.match(name)
            if not m:
                continue
            target = dest / m.group(1)
            if not target.exists():
                target.write_bytes(z.read(name))
            out.append(target)
    return sorted(out)


def run_sequence(frames: list[Path], cfg: FallConfig, fps: float, hold_last: float, weights: str, imgsz: int, conf: float = 0.4):
    from ultralytics import YOLO

    model = YOLO(weights)                         # fresh model = fresh tracker per sequence
    eng = CameraFallEngine(1, cfg)
    step = max(1, round(SRC_FPS / fps))
    events, people_frames, n = [], 0, 0
    global _INFER_MS
    last_people, last_ts, wh = [], 0.0, None
    for i in range(0, len(frames), step):
        img = cv2.imread(str(frames[i]))
        if img is None:
            continue
        h, w = img.shape[:2]
        wh = (w, h)
        t_inf = time.perf_counter()
        res = model.track(img, persist=True, tracker="bytetrack.yaml", conf=conf, imgsz=imgsz, verbose=False)[0]
        _INFER_MS.append((time.perf_counter() - t_inf) * 1000)
        people = []
        if res.boxes is not None and len(res.boxes):
            ids = res.boxes.id.cpu().numpy().astype(int) if res.boxes.id is not None else [None] * len(res.boxes)
            kp = res.keypoints.data.cpu().numpy()
            for j in range(len(res.boxes)):
                people.append({"track_id": None if ids[j] is None else int(ids[j]), "bbox": res.boxes.xyxy[j].cpu().numpy().tolist(),
                               "confidence": float(res.boxes.conf[j]), "keypoints": kp[j]})
        n += 1
        people_frames += bool(people)
        ts = i / SRC_FPS
        events += eng.update(ts, people, wh)
        last_people, last_ts = people, ts
    if hold_last > 0 and last_people:             # optional: freeze the last frame (person stays down)
        t = last_ts
        while t < last_ts + hold_last:
            t += 1.0 / fps
            events += eng.update(t, last_people, wh)
    return events, n, people_frames


def summarise(name: str, label: str, events, n_frames: int, people_frames: int, duration: float):
    ks = [e.kind for e in events]
    conf = [e for e in events if e.kind == "confirmed"]
    pos = [e for e in events if e.kind == "possible"]
    return {"sequence": name, "label": label, "analysed_frames": n_frames, "frames_with_person": people_frames,
            "duration_s": round(duration, 1), "events": ks,
            "first_possible_s": round(pos[0].ts, 2) if pos else None,
            "first_confirmed_s": round(conf[0].ts, 2) if conf else None,
            "confirmed": len(conf), "possible": len(pos)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", required=True)
    ap.add_argument("--work", default=None, help="folder for extracted frames (default: <zips>/../extracted)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=5.0, help="analysis rate (the live default is 5)")
    ap.add_argument("--hold-last", type=float, default=0.0, help="seconds to freeze the last frame (sequence ends while the person is down)")
    ap.add_argument("--weights", default=str(Path(__file__).resolve().parent.parent / "models" / "yolov8n-pose.pt"))
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--conf", type=float, default=0.4, help="detector confidence (live default 0.4)")
    ap.add_argument("--only", default="", help="comma list of name prefixes, e.g. fall-01,adl-02")
    ap.add_argument("--set", action="append", default=[], help="override a FallConfig value: key=value")
    ap.add_argument("--sensitivity", default="medium")
    a = ap.parse_args()

    overrides = {k: v for k, v in (s.split("=", 1) for s in a.set)}
    cfg = from_settings(overrides, a.sensitivity)
    zips = Path(a.zips)
    work = Path(a.work) if a.work else zips.parent / "extracted"
    wanted = tuple(x for x in a.only.split(",") if x)
    results = []
    t0 = time.time()
    for zp in sorted(zips.glob("*-cam0-rgb.zip")):
        name = zp.name.replace("-cam0-rgb.zip", "")
        if wanted and not name.startswith(wanted):
            continue
        try:
            zipfile.ZipFile(zp).testzip()
        except Exception as e:
            print(f"SKIP {name}: incomplete archive ({type(e).__name__})")
            continue
        frames = extract(zp, work / name)
        if not frames:
            print(f"SKIP {name}: no frames")
            continue
        label = "fall" if name.startswith("fall") else "adl"
        events, n, pf = run_sequence(frames, cfg, a.fps, a.hold_last, a.weights, a.imgsz, a.conf)
        r = summarise(name, label, events, n, pf, len(frames) / SRC_FPS)
        results.append(r)
        print(f"{name:8s} {label:4s} frames={len(frames):4d} person_frames={pf:3d}/{n:3d} events={r['events']}", flush=True)

    falls = [r for r in results if r["label"] == "fall"]
    adls = [r for r in results if r["label"] == "adl"]
    summary = {
        "config": {"fps": a.fps, "hold_last_s": a.hold_last, "sensitivity": a.sensitivity, "overrides": overrides, "imgsz": a.imgsz, "conf": a.conf,
                   "weights": Path(a.weights).name, "confirm_seconds": cfg.confirm_seconds},
        "fall_sequences": len(falls), "falls_confirmed": sum(r["confirmed"] > 0 for r in falls),
        "falls_possible_only": sum(r["confirmed"] == 0 and r["possible"] > 0 for r in falls),
        "falls_missed": sum(r["possible"] == 0 for r in falls),
        "adl_sequences": len(adls), "adl_false_confirmed": sum(r["confirmed"] > 0 for r in adls),
        "adl_false_possible": sum(r["possible"] > 0 for r in adls),
        "minutes": round((time.time() - t0) / 60, 1),
        "mean_inference_ms": round(float(np.mean(_INFER_MS)), 1) if _INFER_MS else None,
        "p95_inference_ms": round(float(np.percentile(_INFER_MS, 95)), 1) if _INFER_MS else None,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"summary": summary, "sequences": results}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
