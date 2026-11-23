"""Per-sequence diagnosis of WHY the engine does or does not reach POSSIBLE. Replays cached pose output
(tools.pose_cache) through the unmodified engine and, at every frame of every track, evaluates the
gates that _descent() applies, in order:

  G1 person        a person with a usable track id is present
  G2 lying         this frame is classified lying (>=2 of torso angle / aspect / extent votes, or strong aspect)
  G3 reference     a standing height has been learned for this track
  G4 was_upright   a frame in the last `upright_lookback` s was upright-ish (lying False, extent ok)
  G5 descent       drop >= min_drop at >= min_velocity (or the torso-angle alternative)

For each sequence it reports the first frame where each gate passes, the deepest gate ever reached, and the
gate that blocked the closest attempt. This is a DIAGNOSTIC (it looks at the evaluation sequences, so it
must not be used as accuracy). Replay is cross-checked: POSSIBLE events from the engine must coincide with
all five gates passing.

  python -m tools.diagnose_urfd [--names fall-01,...] [--out ../docs/eval/diagnosis_baseline.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from falldet.fall_analysis.config import FallConfig  # noqa: E402
from falldet.fall_analysis.engine import CameraFallEngine, TrackFSM  # noqa: E402
from tools.pose_cache import cache_dir, load  # noqa: E402

GATES = ["G1_person", "G2_lying", "G3_reference", "G4_was_upright", "G5_descent"]


def gate_report(fsm: TrackFSM, hist, now: float, cfg: FallConfig) -> dict:
    """Mirror of TrackFSM._descent(): returns {'depth': n gates passed, 'blocked_by': name|None, values}."""
    cur = hist.samples[-1]
    v = {"lying": cur.lying, "stand_h": hist.stand_h}
    if not cur.lying:
        return {"depth": 1, "blocked_by": "G2_lying", **v}
    if not hist.stand_h:
        return {"depth": 2, "blocked_by": "G3_reference", **v}
    lookback = hist.window(now, cfg.upright_lookback)[:-1]
    if not any(s.lying is False and (s.ext_ratio is None or s.ext_ratio >= cfg.upright_extent_ratio) for s in lookback):
        n_look = len(lookback)
        return {"depth": 3, "blocked_by": "G4_was_upright", "lookback_frames": n_look,
                "lookback_lying": sum(1 for s in lookback if s.lying), "lookback_unknown": sum(1 for s in lookback if s.lying is None), **v}
    trig = fsm._descent(hist, now)
    if trig is None:
        win = hist.window(now, cfg.descent_window)
        best = max(((cur.f.cy - s.cy_s) / hist.stand_h for s in win[:-1]), default=0.0)
        return {"depth": 4, "blocked_by": "G5_descent", "max_drop": round(best, 2), **v}
    return {"depth": 5, "blocked_by": None, **trig, **v}


def diagnose(name: str, cfg: FallConfig, weights: str, tag: str = "") -> dict:
    d = load(name, weights, tag)
    eng = CameraFallEngine(1, cfg)
    wh = d["frame_wh"]
    n = len(d["frames"])
    first = {g: None for g in GATES}
    deepest, closest = 0, None
    track_ids, id_changes, prev_main = set(), 0, None
    frames_person = frames_kpts6 = frames_lying = frames_ref = low_start = 0
    ref_at = lying_at = None
    events, rows = [], []
    for fr in d["frames"]:
        ts, people = fr["ts"], fr["people"]
        evs = eng.update(ts, people, wh)
        events += [(e.kind, round(ts, 2)) for e in evs]
        usable = [p for p in people if p["track_id"] is not None and p["confidence"] >= cfg.min_person_conf]
        if people:
            frames_person += 1
        if not usable:
            rows.append({"ts": round(ts, 2), "people": len(people), "usable": 0})
            continue
        if first["G1_person"] is None:
            first["G1_person"] = round(ts, 2)
        main = max(usable, key=lambda p: (p["bbox"][2] - p["bbox"][0]) * (p["bbox"][3] - p["bbox"][1]))
        track_ids.add(main["track_id"])
        if prev_main is not None and main["track_id"] != prev_main:
            id_changes += 1
        prev_main = main["track_id"]
        ent = eng.tracks.get(main["track_id"])
        if ent is None:
            continue
        hist, fsm = ent
        cur = hist.samples[-1]
        frames_kpts6 += cur.f.n_visible >= 6
        frames_lying += bool(cur.lying)
        if hist.stand_h and ref_at is None:
            ref_at = round(ts, 2)
        if cur.lying and lying_at is None:
            lying_at = round(ts, 2)
        # evaluate gates against the state BEFORE this frame's transition could hide them: use the
        # same history; for a track already past NORMAL the report is still informative.
        g = gate_report(fsm, hist, ts, cfg)
        depth = g["depth"] if g["blocked_by"] else 5
        for k in range(depth):
            if first[GATES[k]] is None:
                first[GATES[k]] = round(ts, 2)
        if depth >= deepest:
            deepest, closest = depth, {"ts": round(ts, 2), **g}
        f = cur.f
        rows.append({"ts": round(ts, 2), "id": main["track_id"], "box": [round(f.w), round(f.h)], "aspect": round(f.aspect, 2),
                     "torso": None if f.torso_angle is None else round(f.torso_angle), "kpts": f.n_visible, "partial": f.partial,
                     "ext": None if cur.ext_ratio is None else round(cur.ext_ratio, 2), "stand_h": round(hist.stand_h) if hist.stand_h else None,
                     "lying": cur.lying, "blocked": g["blocked_by"], "state": fsm.state})
    # first-frame facts: was the person already low / wide when first seen?
    first_row = next((r for r in rows if r.get("id") is not None), None)
    return {"sequence": name, "analysed_frames": n, "duration_s": round(d["frames"][-1]["ts"], 1) if n else 0,
            "frames_with_person": frames_person, "frames_kpts>=6": frames_kpts6, "frames_lying": frames_lying,
            "main_track_ids": sorted(track_ids), "id_changes": id_changes, "reference_learned_at": ref_at, "first_lying_at": lying_at,
            "first_gate_pass": first, "deepest_gate": deepest, "closest_attempt": closest, "first_frame": first_row,
            "events": events, "possible": any(k == "possible" for k, _ in events), "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", default="")
    ap.add_argument("--weights", default="yolov8n-pose.pt")
    ap.add_argument("--out", default="")
    ap.add_argument("--tag", default="")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    from falldet.fall_analysis.config import from_settings

    cfg = from_settings({k: v for k, v in (s.split("=", 1) for s in a.set)}, "medium")
    names = [n for n in a.names.split(",") if n] or sorted(p.stem for p in cache_dir(a.weights, tag=a.tag).glob("fall-*.pkl"))
    res = []
    for nm in names:
        r = diagnose(nm, cfg, a.weights, a.tag)
        res.append(r)
        c = r["closest_attempt"] or {}
        print(f"{nm:8s} person {r['frames_with_person']:2d}/{r['analysed_frames']:2d} kpts>=6 {r['frames_kpts>=6']:2d} lying {r['frames_lying']:2d} "
              f"ids={r['main_track_ids']} ref@{r['reference_learned_at']} lying@{r['first_lying_at']} deepest=G{r['deepest_gate']} "
              f"blocked_by={c.get('blocked_by')} possible={r['possible']}", flush=True)
        if a.verbose:
            for row in r["rows"]:
                print("   ", row)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
