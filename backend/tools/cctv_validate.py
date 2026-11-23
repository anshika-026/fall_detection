"""Replay labelled CCTV footage through the existing detection chain and score it against HUMAN-written labels.

  python -m tools.cctv_validate --footage ../validation/footage --out ../validation/results/run1.json --md ../validation/results/run1.md
  python -m tools.cctv_validate ... --config strict:conf=0.5,min_person_conf=0.5 --configs default,conf015,strict

Chain (same as the live backend and tools.eval_urfd): yolov8n-pose + ultralytics ByteTrack -> CameraFallEngine.
Nothing here changes the engine. Rules:
  * Ground truth comes only from <clip>.meta.json files written by a person (tools.cctv_meta). A clip without a valid
    metadata file is skipped and reported, never labelled from the detector's output.
  * CONFIRMED only from the clip's own continuous subsequent frames at the configured confirm_seconds (default 3.0).
    There is no hold-last / frame freezing anywhere.
  * The model is run once per (clip, detector conf) and cached in validation/cache/ (never overwritten without --refresh);
    configurations that differ only in engine settings reuse the cache, so they see identical detections.
  * One fresh CameraFallEngine per clip (a clip is one camera session).
Scoring windows and definitions: tools/cctv_meta.py (PRE_S / POST_S), fixed before any footage is looked at.
Reported as counts. No accuracy / precision / recall percentages are computed: the clips are few and the labels are yours.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from falldet.fall_analysis.config import from_settings  # noqa: E402
from falldet.fall_analysis.engine import CameraFallEngine  # noqa: E402
from tools import cctv_meta  # noqa: E402

DEFAULT_CONFIGS = {
    "default": {"conf": 0.4, "overrides": {}},                                   # what ships
    "conf015": {"conf": 0.15, "overrides": {"min_person_conf": 0.15}},           # experiment only, NOT a default
}


def parse_config(spec: str) -> tuple[str, dict]:
    name, _, rest = spec.partition(":")
    conf, over = 0.4, {}
    for kv in filter(None, rest.split(",")):
        k, _, v = kv.partition("=")
        if k == "conf":
            conf = float(v)
        else:
            over[k] = float(v)
    return name, {"conf": conf, "overrides": over}


def role_of(footage: Path) -> str:
    """'tuning' or 'independent' from the folder the footage sits in (validation/tuning, validation/independent)."""
    parts = {x.lower() for x in footage.resolve().parts}
    return "tuning" if "tuning" in parts else "independent" if "independent" in parts else "unspecified"


def content_key(clip: Path) -> str:
    """Identity of the footage itself (size + first 2 MB), so a copy under another name is still the same clip."""
    h = hashlib.sha1(str(clip.stat().st_size).encode())
    with open(clip, "rb") as fh:
        h.update(fh.read(2_000_000))
    return h.hexdigest()


def shared_between_roles(footage: Path) -> list[str]:
    """Clips in this footage root that also exist in the sibling tuning/independent root: such footage cannot
    be called independent."""
    role = role_of(footage)
    other = {"tuning": "independent", "independent": "tuning"}.get(role)
    sibling = footage.resolve().parent / other if other else None
    if not sibling or not sibling.is_dir():
        return []
    theirs = {content_key(c) for c in cctv_meta.find_clips(sibling)}
    return [str(c.relative_to(footage)) for c in cctv_meta.find_clips(footage) if content_key(c) in theirs]


def clip_id(clip: Path) -> str:
    return f"{clip.parent.name}__{clip.stem}"


def fingerprint(clip: Path) -> str:
    st = clip.stat()
    return hashlib.sha1(f"{clip.name}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()[:12]


# ------------------------------------------------------------------------------------------ pose cache
def build_pose(clip: Path, weights: str, conf: float, imgsz: int, fps: float) -> dict:
    """Decode the clip and run pose + tracker at `fps` (by the video's own timestamps)."""
    import cv2
    from ultralytics import YOLO

    model = YOLO(weights)                                         # fresh tracker per clip
    cap = cv2.VideoCapture(str(clip))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {clip.name}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    frames, infer, wall0 = [], [], time.perf_counter()
    nxt, idx, wh = 0.0, -1, None
    while True:
        if not cap.grab():
            break
        idx += 1
        ts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if ts <= 0 and idx > 0 and src_fps:
            ts = idx / src_fps
        if ts + 1e-6 < nxt:
            continue
        ok, img = cap.retrieve()
        if not ok:
            continue
        nxt = max(nxt + 1.0 / fps, ts)
        wh = (img.shape[1], img.shape[0])
        t0 = time.perf_counter()
        r = model.track(img, persist=True, tracker="bytetrack.yaml", conf=conf, imgsz=imgsz, verbose=False)[0]
        infer.append((time.perf_counter() - t0) * 1000)
        people = []
        if r.boxes is not None and len(r.boxes):
            ids = r.boxes.id.cpu().numpy().astype(int) if r.boxes.id is not None else [None] * len(r.boxes)
            kp = r.keypoints.data.cpu().numpy()
            for j in range(len(r.boxes)):
                people.append({"track_id": None if ids[j] is None else int(ids[j]), "bbox": r.boxes.xyxy[j].cpu().numpy().tolist(),
                               "confidence": float(r.boxes.conf[j]), "keypoints": kp[j]})
        frames.append({"i": idx, "ts": ts, "people": people})
    cap.release()
    return {"clip": clip.name, "fingerprint": fingerprint(clip), "fps": fps, "conf": conf, "imgsz": imgsz, "frame_wh": wh,
            "frames": frames, "infer_ms": infer, "decode_and_infer_wall_s": round(time.perf_counter() - wall0, 2),
            "source_fps": src_fps, "duration_s": frames[-1]["ts"] if frames else 0.0}


def get_pose(clip: Path, cache_root: Path, weights: str, conf: float, imgsz: int, fps: float, refresh: bool) -> dict:
    folder = cache_root / f"{Path(weights).stem}_conf{conf}_fps{fps}_sz{imgsz}"
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / f"{clip_id(clip)}.pkl"
    if p.exists() and not refresh:
        d = pickle.loads(p.read_bytes())
        if d.get("fingerprint") == fingerprint(clip):
            return d
        print(f"  cache for {clip.name} is stale (the clip changed): rebuilding")
    d = build_pose(clip, weights, conf, imgsz, fps)
    tmp = p.with_suffix(".tmp")
    tmp.write_bytes(pickle.dumps(d))
    tmp.replace(p)
    return d


# ------------------------------------------------------------------------------------------ replay + report
def replay(pose: dict, overrides: dict, sensitivity: str = "medium"):
    cfg = from_settings(overrides, sensitivity)
    eng = CameraFallEngine(1, cfg)
    events, eng_ms, ids = [], [], set()
    for fr in pose["frames"]:
        ids.update(p["track_id"] for p in fr["people"] if p["track_id"] is not None)
        t0 = time.perf_counter()
        for e in eng.update(fr["ts"], fr["people"], pose["frame_wh"]):
            events.append((e.kind, round(fr["ts"], 2)))
        eng_ms.append((time.perf_counter() - t0) * 1000)
    return events, eng_ms, ids


def pct(a, q):
    return round(float(np.percentile(a, q)), 1) if len(a) else None


def run_config(name: str, spec: dict, clips: list[tuple[Path, dict]], cache_root: Path, a) -> dict:
    rows, all_inf, all_eng = [], [], []
    for clip, meta in clips:
        pose = get_pose(clip, cache_root, a.weights, spec["conf"], a.imgsz, a.fps, a.refresh)
        events, eng_ms, ids = replay(pose, spec["overrides"], a.sensitivity)
        sc = cctv_meta.score_clip(meta, events)
        inf = pose["infer_ms"]
        all_inf += inf
        all_eng += eng_ms
        rows.append({"clip": f"{clip.parent.name}/{clip.name}", "scenario": meta["scenario"], "camera_id": meta["camera_id"],
                     "expected": meta["expected_event"], "duration_s": round(pose["duration_s"], 1), "analysed_frames": len(pose["frames"]),
                     "frames_with_person": sum(bool(f["people"]) for f in pose["frames"]), "unique_track_ids": len(ids),
                     "source_kind": meta.get("source_kind", "unspecified"),
                     "events": events, "event_time_s": meta.get("event_time_s"), **{k: v for k, v in sc.__dict__.items() if k != "expected"},
                     "mean_inference_ms": round(float(np.mean(inf)), 1) if inf else None})
    falls = [r for r in rows if r["expected"] == "fall"]
    normals = [r for r in rows if r["expected"] == "none"]
    lat = [r["confirm_latency_s"] for r in falls if r["confirm_latency_s"] is not None]
    hours_normal = sum(r["duration_s"] for r in normals) / 3600.0
    hours_all = sum(r["duration_s"] for r in rows) / 3600.0
    by_sc = defaultdict(lambda: {"clips": 0, "possible": 0, "confirmed": 0, "missed": 0, "false_possible": 0, "false_confirmed": 0})
    for r in rows:
        b = by_sc[r["scenario"]]
        b["clips"] += 1
        b["possible"] += r["detected_possible"]
        b["confirmed"] += r["detected_confirmed"]
        b["missed"] += r["missed"]
        b["false_possible"] += r["false_possible"]
        b["false_confirmed"] += r["false_confirmed"]
    mean_lat = (float(np.mean(all_inf)) + float(np.mean(all_eng))) if all_inf else None
    return {"name": name, "detector_conf": spec["conf"], "engine_overrides": spec["overrides"], "sensitivity": a.sensitivity,
            "summary": {
                "fall_clips": len(falls), "falls_possible": sum(r["detected_possible"] for r in falls),
                "falls_confirmed": sum(r["detected_confirmed"] for r in falls), "falls_missed": sum(r["missed"] for r in falls),
                "confirm_latency_s": {"n": len(lat), "median": round(float(np.median(lat)), 2) if lat else None,
                                      "min": min(lat) if lat else None, "max": max(lat) if lat else None},
                "normal_clips": len(normals), "normal_hours": round(hours_normal, 3),
                "false_possible_total": sum(r["false_possible"] for r in rows), "false_confirmed_total": sum(r["false_confirmed"] for r in rows),
                "false_confirmed_per_normal_hour": round(sum(r["false_confirmed"] for r in normals) / hours_normal, 2) if hours_normal else None,
                "false_possible_per_normal_hour": round(sum(r["false_possible"] for r in normals) / hours_normal, 2) if hours_normal else None,
                "total_footage_hours": round(hours_all, 3)},
            "performance": {"analysed_frames": len(all_inf), "mean_inference_ms": round(float(np.mean(all_inf)), 1) if all_inf else None,
                            "p95_inference_ms": pct(all_inf, 95), "mean_engine_ms": round(float(np.mean(all_eng)), 3) if all_eng else None,
                            "p95_engine_ms": pct(all_eng, 95), "mean_frame_latency_ms": round(mean_lat, 1) if mean_lat else None,
                            "single_stream_max_fps": round(1000.0 / mean_lat, 2) if mean_lat else None, "target_analysis_fps": a.fps},
            "by_scenario": dict(by_sc), "clips": rows}


def summarise_sources(rows) -> dict:
    """{source_kind: number of clips}; clips whose label has no source_kind count as 'unspecified'."""
    out: dict[str, int] = {}
    for r in rows:
        k = r.get("source_kind", "unspecified")
        out[k] = out.get(k, 0) + 1
    return out


# What each kind of footage does and does not show. Printed at the top of every report so a file test is never read as a camera test.
SCOPE_TEXT = {
    "exported_file": "**FILE / EXPORTED FOOTAGE:** these results describe detection quality on exported video files only. "
                     "Live RTSP connectivity: NOT tested by this run. Physical-camera live validation: NOT done.",
    "rtsp_recording": "Footage recorded by cctv_record from RTSP cameras. It counts as live-camera evidence only if the recordings passed "
                      "`cctv_verify_recording --require-rtsp` and a time-marker (liveness) check in front of the physical camera.",
    "file_test": "**FILE TEST footage** (a recording made from a local file): a tool test, not camera evidence.",
    "simulator": "**SIMULATOR footage:** a tool test, not camera evidence of any kind.",
    "public_dataset": "**PUBLIC DATASET footage (not our cameras):** home-style scenes from a research dataset. These results say how the rules behave on "
                      "that dataset only. They are NOT validation on the office CCTV and NOT evidence of real-world safety.",
    "unspecified": "Source not recorded in the labels of some clips (unspecified): do not read these results as live-camera evidence.",
}


def to_markdown(report: dict) -> str:
    role = report.get("footage_role", "unspecified")
    banner = {"tuning": "**TUNING footage: results here are NOT independent validation.**",
              "independent": "Independent (held-out) footage: valid only if nothing was tuned on it.",
              "unspecified": "**Footage role unspecified.**"}[role]
    kinds = report.get("source_kinds", {})
    scope = [f"- {SCOPE_TEXT[k]} ({n} clip{'s' if n != 1 else ''})" for k, n in kinds.items() if k in SCOPE_TEXT]
    L = [f"# Validation run {report['run']}", "", banner, "", *scope, "", f"Clips scored: {report['clips_scored']}; skipped (no/invalid metadata): {len(report['skipped'])}. "
         "Counts only: these are not accuracy figures.", ""]
    for s in report["skipped"]:
        L.append(f"- SKIPPED `{s['clip']}`: {s['reason']}")
    L += ["", "| config | fall clips | POSSIBLE | CONFIRMED | missed | median confirm latency (s) | normal hours | false POSSIBLE | false CONFIRMED | false CONFIRMED / normal hour | mean frame latency (ms) | max fps (1 stream) |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in report["configs"]:
        s, p = c["summary"], c["performance"]
        L.append(f"| {c['name']} (conf {c['detector_conf']}) | {s['fall_clips']} | {s['falls_possible']} | {s['falls_confirmed']} | {s['falls_missed']} | "
                 f"{s['confirm_latency_s']['median']} | {s['normal_hours']} | {s['false_possible_total']} | {s['false_confirmed_total']} | "
                 f"{s['false_confirmed_per_normal_hour']} | {p['mean_frame_latency_ms']} | {p['single_stream_max_fps']} |")
    for c in report["configs"]:
        L += ["", f"## {c['name']}: by scenario", "", "| scenario | clips | POSSIBLE | CONFIRMED | missed | false POSSIBLE | false CONFIRMED |", "|---|---|---|---|---|---|---|"]
        for sc, b in sorted(c["by_scenario"].items()):
            L.append(f"| {sc} | {b['clips']} | {b['possible']} | {b['confirmed']} | {b['missed']} | {b['false_possible']} | {b['false_confirmed']} |")
        L += ["", f"### {c['name']}: per clip", "", "| clip | expected | event t (s) | events | missed | latency (s) |", "|---|---|---|---|---|---|"]
        for r in c["clips"]:
            L.append(f"| {r['clip']} | {r['expected']} | {r['event_time_s']} | {', '.join(f'{k}@{t}' for k, t in r['events']) or '-'} | {r['missed']} | {r['confirm_latency_s']} |")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--footage", default=str(ROOT.parent / "validation" / "independent"),
                    help="validation/independent (default: the held-out footage) or validation/tuning")
    ap.add_argument("--cache", default=str(ROOT.parent / "validation" / "cache"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--md", default="")
    ap.add_argument("--weights", default=str(ROOT / "models" / "yolov8n-pose.pt"))
    ap.add_argument("--fps", type=float, default=5.0, help="analysis rate (the live default is 5)")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--sensitivity", default="medium")
    ap.add_argument("--configs", default="default,conf015", help="comma list of config names")
    ap.add_argument("--config", action="append", default=[], help="define one: NAME:conf=0.3,min_person_conf=0.3,confirm_seconds=3")
    ap.add_argument("--refresh", action="store_true", help="re-run the model even if a cache exists")
    a = ap.parse_args()

    cfgs = dict(DEFAULT_CONFIGS)
    cfgs.update(dict(parse_config(s) for s in a.config))
    wanted = [c for c in a.configs.split(",") if c]
    unknown = [c for c in wanted if c not in cfgs]
    if unknown:
        raise SystemExit(f"unknown config(s) {unknown}; defined: {sorted(cfgs)}")
    footage = Path(a.footage)
    out = Path(a.out)
    if out.exists():
        raise SystemExit(f"{out} already exists: not overwriting (choose another --out)")
    role = role_of(footage)
    if role == "unspecified":
        print("WARNING: footage is not under validation/tuning or validation/independent: results will be labelled 'unspecified'.")
    dup = shared_between_roles(footage)
    if dup:
        raise SystemExit(f"these clips also exist in the other split ({', '.join(dup[:5])}): footage used for tuning cannot also be independent validation footage")
    ok, skipped = [], []
    for clip in cctv_meta.find_clips(footage):
        try:
            ok.append((clip, cctv_meta.load_clip(clip, clip.parent.name)))
        except cctv_meta.MetaError as e:
            skipped.append({"clip": str(clip.relative_to(footage)), "reason": str(e)})
    print(f"{len(ok)} labelled clips, {len(skipped)} skipped")
    for s in skipped:
        print("  SKIP", s["clip"], "-", s["reason"])
    if not ok:
        raise SystemExit("nothing to validate: add clips with metadata under validation/independent/<scenario>/ or validation/tuning/<scenario>/ (see validation/README.md)")
    for p in cctv_meta.ignored_files(footage):
        print(f"  WARNING {p.relative_to(footage)}: not a supported clip, NOT validated (use .mkv/.mp4/.avi/.mov; cut it with cctv_clip)")
    kinds = summarise_sources([{"source_kind": m.get("source_kind", "unspecified")} for _, m in ok])
    report = {"run": out.stem, "footage_role": role, "footage_root": str(footage), "source_kinds": kinds, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "weights": Path(a.weights).name,
              "analysis_fps": a.fps, "scoring_window": {"pre_s": cctv_meta.PRE_S, "post_s": cctv_meta.POST_S}, "clips_scored": len(ok),
              "skipped": skipped, "configs": []}
    for name in wanted:
        print(f"== config {name}: {cfgs[name]}")
        report["configs"].append(run_config(name, cfgs[name], ok, Path(a.cache), a))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = to_markdown(report)
    if a.md:
        Path(a.md).write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
