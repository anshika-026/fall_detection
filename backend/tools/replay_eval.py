"""Replay cached pose output (tools.pose_cache) through the CURRENT engine and summarise, in the same
format as tools.eval_urfd. Because the model output is cached, results isolate the engine: the same
detections and track ids feed every engine version, so differences are caused by engine changes only.

  python -m tools.replay_eval --out ../docs/eval/replay_x.json [--tag conf0.15] [--set k=v ...] [--names ...]

Confirmed = reached CONFIRMED using the sequence's own subsequent frames (no hold-last, ever).
inference ms are those measured when the cache was built (model.track wall time, CPU);
engine ms is measured here, per analysed frame.
NOTE: runs over the evaluation sequences are DIAGNOSTIC / TUNING results, not independent accuracy."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from falldet.fall_analysis.config import from_settings  # noqa: E402
from falldet.fall_analysis.engine import CameraFallEngine  # noqa: E402
from tools.pose_cache import cache_dir, load  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--weights", default="yolov8n-pose.pt")
    ap.add_argument("--tag", default="")
    ap.add_argument("--names", default="")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--sensitivity", default="medium")
    a = ap.parse_args()
    overrides = {k: v for k, v in (s.split("=", 1) for s in a.set)}
    cfg = from_settings(overrides, a.sensitivity)
    names = [n for n in a.names.split(",") if n] or sorted(p.stem for p in cache_dir(a.weights, tag=a.tag).glob("*.pkl"))
    results, eng_ms, inf_ms = [], [], []
    for n in names:
        d = load(n, a.weights, a.tag)
        eng = CameraFallEngine(1, cfg)
        events = []
        for fr in d["frames"]:
            t0 = time.perf_counter()
            events += eng.update(fr["ts"], fr["people"], d["frame_wh"])
            eng_ms.append((time.perf_counter() - t0) * 1000)
        inf_ms += d["infer_ms"]
        label = "fall" if n.startswith("fall") else "adl"
        pos = [e for e in events if e.kind == "possible"]
        con = [e for e in events if e.kind == "confirmed"]
        results.append({"sequence": n, "label": label, "analysed_frames": len(d["frames"]),
                        "duration_s": round(d["frames"][-1]["ts"], 1) if d["frames"] else 0,
                        "events": [e.kind for e in events], "first_possible_s": round(pos[0].ts, 2) if pos else None,
                        "first_confirmed_s": round(con[0].ts, 2) if con else None, "possible": len(pos), "confirmed": len(con)})
        print(f"{n:8s} {label:4s} events={results[-1]['events']}", flush=True)
    falls = [r for r in results if r["label"] == "fall"]
    adls = [r for r in results if r["label"] == "adl"]
    summary = {"config": {"overrides": overrides, "sensitivity": a.sensitivity, "weights": a.weights, "tag": a.tag, "hold_last": False},
               "fall_sequences": len(falls), "falls_confirmed": sum(r["confirmed"] > 0 for r in falls),
               "falls_possible_only": sum(r["confirmed"] == 0 and r["possible"] > 0 for r in falls),
               "falls_missed": sum(r["possible"] == 0 for r in falls),
               "adl_sequences": len(adls), "adl_false_confirmed": sum(r["confirmed"] > 0 for r in adls),
               "adl_false_possible": sum(r["possible"] > 0 for r in adls),
               "mean_inference_ms_at_cache_build": round(float(np.mean(inf_ms)), 1) if inf_ms else None,
               "p95_inference_ms_at_cache_build": round(float(np.percentile(inf_ms, 95)), 1) if inf_ms else None,
               "mean_engine_ms_per_frame": round(float(np.mean(eng_ms)), 3), "p95_engine_ms_per_frame": round(float(np.percentile(eng_ms, 95)), 3)}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"summary": summary, "sequences": results}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
