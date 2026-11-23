"""Per-sequence evidence table for the sequences the engine did not reach POSSIBLE on (or all, with --all).
Replays cached pose output through the engine (see tools.diagnose_urfd) and adds the facts needed to tell
the causes apart: lost/untracked person frames, torso-angle vs lying-vote disagreement, frame-edge crop,
seated start, and the best descent measured against the thresholds.   DIAGNOSTIC ONLY.

  python -m tools.diagnose_table [--all] [--weights yolov8n-pose.pt] [--md out.md] [--set k=v ...]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from falldet.fall_analysis.config import from_settings  # noqa: E402
from falldet.fall_analysis.engine import CameraFallEngine  # noqa: E402
from tools.diagnose_urfd import diagnose  # noqa: E402
from tools.pose_cache import cache_dir, load  # noqa: E402


def facts(name: str, cfg, weights: str, tag: str = "") -> dict:
    d = load(name, weights, tag)
    W, H = d["frame_wh"]
    r = diagnose(name, cfg, weights, tag)
    rows = r["rows"]
    no_id = sum(1 for x in rows if x.get("usable") == 0 and x.get("people", 0) > 0)
    no_person = sum(1 for x in rows if x.get("people") == 0)
    torso_hi = [x for x in rows if x.get("torso") is not None and x["torso"] >= cfg.lying_torso_angle]
    torso_hi_not_lying = [x for x in torso_hi if not x["lying"]]
    # last frames: where is the person and is the box cut by the bottom edge?
    cut_bottom = 0
    for fr in d["frames"]:
        for p in fr["people"]:
            if p["bbox"][3] >= H - 3:
                cut_bottom += 1
                break
    # seated start: first usable row has torso ~vertical but box aspect and extent smaller than standing? use
    # ratio of first-frame hip height to later-standing; simplest robust proxy: the ext ratio / box height vs max box height
    first = next((x for x in rows if x.get("id") is not None), None)
    hmax = max((x["box"][1] for x in rows if x.get("box")), default=0)
    seated = bool(first and first["box"][1] < 0.8 * hmax) if first else False
    ids = r["main_track_ids"]
    return {"name": name, "frames": r["analysed_frames"], "person": r["frames_with_person"], "no_track_id_frames": no_id,
            "no_person_frames": no_person, "torso>=55": len(torso_hi), "torso>=55_not_lying": len(torso_hi_not_lying),
            "not_lying_examples": [(x["ts"], x["aspect"], x["ext"]) for x in torso_hi_not_lying[:3]],
            "frames_box_cut_bottom": cut_bottom, "ids": ids, "id_changes": r["id_changes"],
            "ref_at": r["reference_learned_at"], "lying_frames": r["frames_lying"], "deepest": r["deepest_gate"],
            "blocked_by": (r["closest_attempt"] or {}).get("blocked_by"), "closest": r["closest_attempt"],
            "possible": r["possible"], "events": r["events"], "first_box_h": first["box"][1] if first else None, "max_box_h": hmax}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--weights", default="yolov8n-pose.pt")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--md", default="")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    cfg = from_settings({k: v for k, v in (s.split("=", 1) for s in a.set)}, "medium")
    names = sorted(p.stem for p in cache_dir(a.weights, tag=a.tag).glob("fall-*.pkl"))
    lines = ["| seq | frames | person | no track-id | torso>=55 but not lying | box cut at bottom | ids | closest gate | detail |", "|---|---|---|---|---|---|---|---|---|"]
    for n in names:
        f = facts(n, cfg, a.weights, a.tag)
        if f["possible"] and not a.all:
            continue
        c = f["closest"] or {}
        detail = {k: c[k] for k in ("lying", "max_drop", "lookback_frames", "stand_h") if k in c}
        lines.append(f"| {n} | {f['frames']} | {f['person']} | {f['no_track_id_frames']} | {f['torso>=55_not_lying']}/{f['torso>=55']} {f['not_lying_examples']} | "
                     f"{f['frames_box_cut_bottom']} | {f['ids']} | {f['blocked_by'] or 'POSSIBLE'} | {detail} first_box_h={f['first_box_h']}/max={f['max_box_h']} |")
    out = "\n".join(lines)
    print(out)
    if a.md:
        Path(a.md).write_text(out + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
