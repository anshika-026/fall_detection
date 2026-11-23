"""Smaller-person experiment on ADULT footage: how does a smaller apparent person size affect YOLOv8n-Pose?

  python -m tools.scale_experiment make    --scales 1.0,0.75,0.5,0.35,0.25
  python -m tools.scale_experiment measure --scales 1.0,0.75,0.5,0.35,0.25 --out ..\\validation\\results\\person_scale_metrics

NOT child validation. Resizing adult footage changes apparent size only; it does not give children's body proportions, movement or
behaviour (see docs/PERSON_SCALE_EXPERIMENT.md). Nothing here changes the detector settings or the fall engine.

`make`    writes lossless (FFV1) copies of the TUNING clips into validation/experiments/person_scale/scale_<s>/tuning/<scenario>/.
          Each frame is shrunk by <s> (INTER_AREA) and pasted in the CENTRE of a canvas of the ORIGINAL size filled with the YOLO letterbox
          grey (114), so the frame size, fps and timeline are unchanged and the person simply looks smaller (like standing further away).
          Scale 1.0 is the same pipeline with no shrink (the control). Labels are copied with a note; originals are only read.
`measure` compares the pose caches that tools.cctv_validate built for each scale with the 1.0 control, frame by frame, and writes
          detection, keypoint, stability and timing figures. Reference = YOLO at scale 1.0 (NOT human-labelled ground truth).
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from falldet.pose_estimation.keypoints import extract_features  # noqa: E402
from tools import cctv_meta  # noqa: E402

V = ROOT.parent / "validation"
EXP = V / "experiments" / "person_scale"
GREY = 114
CACHE_SUB = "yolov8n-pose_conf0.4_fps5.0_sz640"


def tag(s: float) -> str:
    return f"scale_{s:.2f}".replace(".", "p")


def shrink(frame: np.ndarray, s: float):
    """-> (new_frame, (sx, sy, ox, oy)) ; the mapping new_xy = old_xy * (sx, sy) + (ox, oy)."""
    h, w = frame.shape[:2]
    if s >= 0.999:
        return frame, (1.0, 1.0, 0, 0)
    nw, nh = max(8, round(w * s)), max(8, round(h * s))
    small = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.full((h, w, 3), GREY, np.uint8)
    ox, oy = (w - nw) // 2, (h - nh) // 2
    canvas[oy:oy + nh, ox:ox + nw] = small
    return canvas, (nw / w, nh / h, ox, oy)


def make(scales: list[float]) -> None:
    clips = sorted((V / "tuning").rglob("*.mp4"))
    manifest = {"purpose": "documented scaled ADULT copies; not child footage", "source": "validation/tuning (GMDCSA-24 tuning split, hard links to the untouched originals)",
                "transform": "frame shrunk by s (INTER_AREA), centred on a canvas of the original size filled with grey 114; lossless FFV1 AVI; fps and frame count unchanged",
                "scales": scales, "clips": []}
    for s in scales:
        for clip in clips:
            sc = clip.parent.name
            out_dir = EXP / tag(s) / "tuning" / sc
            out_dir.mkdir(parents=True, exist_ok=True)
            out = out_dir / (clip.stem + ".avi")
            meta_in = cctv_meta.meta_path(clip)
            if out.exists():
                continue
            cap = cv2.VideoCapture(str(clip))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            vw = cv2.VideoWriter(str(out.with_suffix(".part.avi")), cv2.VideoWriter_fourcc(*"FFV1"), fps, (w, h))
            if not vw.isOpened():
                raise SystemExit("cannot open an FFV1 writer")
            n, mapping = 0, None
            while True:
                ok, fr = cap.read()
                if not ok:
                    break
                nf, mapping = shrink(fr, s)
                vw.write(nf)
                n += 1
            vw.release()
            cap.release()
            out.with_suffix(".part.avi").replace(out)
            meta = json.loads(meta_in.read_text(encoding="utf-8"))
            meta["notes"] = f"SCALED ADULT COPY x{s} (not child footage). " + meta.get("notes", "")
            meta["scale_experiment"] = {"scale": s, "source_clip": clip.name, "frame_size": [w, h], "fps": fps, "frames": n}
            cctv_meta.meta_path(out).write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"scale {s}: done", flush=True)
    for s in scales:       # the manifest is rebuilt from what is on disk, so a re-run or a parallel run per scale stays consistent
        listed = []
        for avi in sorted((EXP / tag(s) / "tuning").rglob("*.avi")):
            m = json.loads(cctv_meta.meta_path(avi).read_text(encoding="utf-8")).get("scale_experiment", {})
            listed.append({"scale": s, "clip": f"{avi.parent.name}/{m.get('source_clip')}", "frames": m.get("frames"), "size": m.get("frame_size"), "fps": m.get("fps")})
        manifest["clips"] = listed
        (EXP / f"manifest_{tag(s)}.json").write_text(json.dumps({**manifest, "scales": [s]}, indent=2), encoding="utf-8")


# ----------------------------------------------------------------------------------------------- measure
def iou(a, b):
    ix, iy = max(0.0, min(a[2], b[2]) - max(a[0], b[0])), max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u > 0 else 0.0


def load_caches(s: float) -> dict[str, dict]:
    root = EXP / tag(s) / "cache" / CACHE_SUB
    return {p.stem: pickle.loads(p.read_bytes()) for p in sorted(root.glob("*.pkl"))}


def q(a, p):
    return None if len(a) == 0 else round(float(np.percentile(a, p)), 4)


def measure(scales: list[float]) -> dict:
    ref_all = load_caches(1.0)
    out = {"reference": "YOLOv8n-Pose at scale 1.0 on the lossless control copies (NOT human-labelled ground truth)", "scales": {}}
    kp_groups = {"head": (0, 1, 2, 3, 4), "shoulders": (5, 6), "hips": (11, 12), "ankles": (15, 16)}
    for s in scales:
        caches = ref_all if s == 1.0 else load_caches(s)
        agg = {"clips": 0, "frames": 0, "ref_person_frames": 0, "ref_persons": 0, "matched": 0, "extra_boxes": 0, "frames_any_person": 0,
               "frames_ref_any_person": 0}
        det_conf, joint_conf, visible_n, usable_torso, usable_hip, partial = [], [], [], [], [], []
        grp = {k: [] for k in kp_groups}
        err, jitter, ref_h_px, in_h_px = [], [], [], []
        infer, ids_per_clip, ids_ref_per_clip = [], [], []
        for name, ref in ref_all.items():
            cur = caches.get(name)
            if cur is None:
                continue
            agg["clips"] += 1
            W, H = ref["frame_wh"]
            by_i = {f["i"]: f for f in cur["frames"]}
            track_prev: dict[int, np.ndarray] = {}
            ids, ids_ref = set(), set()
            infer += cur["infer_ms"]
            for rf in ref["frames"]:
                agg["frames"] += 1
                cf = by_i.get(rf["i"])
                rp = [p for p in rf["people"]]
                agg["ref_person_frames"] += bool(rp)
                cp = cf["people"] if cf else []
                agg["frames_any_person"] += bool(cp)
                agg["frames_ref_any_person"] += bool(rp)
                for p in rp:
                    if p["track_id"] is not None:
                        ids_ref.add(p["track_id"])
                for p in cp:
                    if p["track_id"] is not None:
                        ids.add(p["track_id"])
                agg["ref_persons"] += len(rp)
                if not rp:
                    agg["extra_boxes"] += len(cp)
                    continue
                if s >= 0.999:
                    sx = sy = 1.0
                    ox = oy = 0
                else:
                    nw, nh = max(8, round(W * s)), max(8, round(H * s))
                    sx, sy, ox, oy = nw / W, nh / H, (W - nw) // 2, (H - nh) // 2
                used = set()
                for r in rp:
                    rb = r["bbox"]
                    mapped = [rb[0] * sx + ox, rb[1] * sy + oy, rb[2] * sx + ox, rb[3] * sy + oy]
                    ref_h = rb[3] - rb[1]
                    ref_h_px.append(ref_h)
                    in_h_px.append((mapped[3] - mapped[1]) * 640.0 / max(W, H))
                    best, bi = 0.0, None
                    for j, c in enumerate(cp):
                        if j in used:
                            continue
                        v = iou(mapped, c["bbox"])
                        if v > best:
                            best, bi = v, j
                    if bi is None or best < 0.5:
                        continue
                    used.add(bi)
                    agg["matched"] += 1
                    c = cp[bi]
                    det_conf.append(c["confidence"])
                    kp = np.asarray(c["keypoints"], float).reshape(-1, 3)
                    ok = kp[:, 2] >= 0.4
                    joint_conf.append(float(kp[:, 2].mean()))
                    visible_n.append(int(ok.sum()))
                    for k, idx in kp_groups.items():
                        grp[k].append(float(ok[list(idx)].mean()))
                    f = extract_features(cf["ts"], c["bbox"], c["keypoints"], (W, H), 0.4)
                    usable_torso.append(f.torso_angle is not None)
                    partial.append(f.partial)
                    rk = np.asarray(r["keypoints"], float).reshape(-1, 3)
                    inv = np.stack([(kp[:, 0] - ox) / sx, (kp[:, 1] - oy) / sy], 1)
                    both = ok & (rk[:, 2] >= 0.4)
                    if both.any() and ref_h > 1:
                        err += list(np.linalg.norm(inv[both] - rk[both, :2], axis=1) / ref_h)
                    # temporal jitter of the mid-shoulder / mid-hip points for the same track id
                    tid = c["track_id"]
                    pts = []
                    for idx in ((5, 6), (11, 12)):
                        sel = [i for i in idx if kp[i, 2] >= 0.4]
                        pts.append(inv[sel].mean(0) if sel else np.array([np.nan, np.nan]))
                    cur_pts = np.concatenate(pts)
                    if tid is not None and tid in track_prev and ref_h > 1:
                        d = np.abs(cur_pts - track_prev[tid])
                        d = d[~np.isnan(d)]
                        if len(d):
                            jitter.append(float(np.linalg.norm(d)) / ref_h)
                    if tid is not None:
                        track_prev[tid] = cur_pts
                agg["extra_boxes"] += len(cp) - len(used)
            ids_per_clip.append(len(ids))
            ids_ref_per_clip.append(len(ids_ref))
        m = agg["matched"]
        out["scales"][f"{s}"] = {
            "clips": agg["clips"], "analysed_frames": agg["frames"], "reference_persons": agg["ref_persons"],
            "median_person_height_in_full_frame_px_at_scale_1": q(ref_h_px, 50),
            "median_person_height_in_640_model_input_px": q(in_h_px, 50),
            "person_detection_recall_vs_scale_1": round(m / agg["ref_persons"], 4) if agg["ref_persons"] else None,
            "frames_with_any_person_share": round(agg["frames_any_person"] / agg["frames"], 4) if agg["frames"] else None,
            "extra_boxes_per_analysed_frame": round(agg["extra_boxes"] / agg["frames"], 4) if agg["frames"] else None,
            "matched_persons": m,
            "mean_detector_confidence_matched": round(float(np.mean(det_conf)), 4) if det_conf else None,
            "mean_keypoint_confidence_matched": round(float(np.mean(joint_conf)), 4) if joint_conf else None,
            "mean_visible_joints_of_17_matched": round(float(np.mean(visible_n)), 3) if visible_n else None,
            "mean_missing_joints_matched": round(17 - float(np.mean(visible_n)), 3) if visible_n else None,
            "joint_group_visible_share_matched": {k: round(float(np.mean(v)), 4) if v else None for k, v in grp.items()},
            "torso_angle_computable_share_matched": round(float(np.mean(usable_torso)), 4) if usable_torso else None,
            "partial_flag_share_matched": round(float(np.mean(partial)), 4) if partial else None,
            "keypoint_position_deviation_vs_scale_1_in_person_heights": {"median": q(err, 50), "p90": q(err, 90), "n": len(err)},
            "mid_shoulder_hip_frame_to_frame_jitter_in_person_heights": {"median": q(jitter, 50), "p90": q(jitter, 90), "n": len(jitter)},
            "track_ids_per_clip_mean": round(float(np.mean(ids_per_clip)), 3) if ids_per_clip else None,
            "track_ids_per_clip_mean_at_scale_1": round(float(np.mean(ids_ref_per_clip)), 3) if ids_ref_per_clip else None,
            "inference_ms": {"mean": round(float(np.mean(infer)), 1) if infer else None, "median": q(infer, 50), "p95": q(infer, 95), "n": len(infer)},
        }
    return out


def to_md(res: dict) -> str:
    sc = res["scales"]
    keys = list(sc)
    rows = [("person height, 640-px model input (median px)", "median_person_height_in_640_model_input_px"),
            ("person detection recall vs scale 1.0", "person_detection_recall_vs_scale_1"),
            ("frames with any person", "frames_with_any_person_share"),
            ("extra boxes per analysed frame", "extra_boxes_per_analysed_frame"),
            ("mean detector confidence (matched)", "mean_detector_confidence_matched"),
            ("mean keypoint confidence (matched)", "mean_keypoint_confidence_matched"),
            ("mean visible joints of 17 (matched)", "mean_visible_joints_of_17_matched"),
            ("mean missing joints (matched)", "mean_missing_joints_matched"),
            ("torso angle computable (matched)", "torso_angle_computable_share_matched"),
            ("partial flag (matched)", "partial_flag_share_matched"),
            ("track ids per clip (mean)", "track_ids_per_clip_mean")]
    L = ["| measure | " + " | ".join(f"x{k}" for k in keys) + " |", "|---|" + "---|" * len(keys)]
    for label, key in rows:
        L.append(f"| {label} | " + " | ".join(str(sc[k][key]) for k in keys) + " |")
    for g in ("head", "shoulders", "hips", "ankles"):
        L.append(f"| joints visible: {g} | " + " | ".join(str(sc[k]["joint_group_visible_share_matched"][g]) for k in keys) + " |")
    L.append("| keypoint deviation vs x1.0, median / p90 (person heights) | " + " | ".join(f"{sc[k]['keypoint_position_deviation_vs_scale_1_in_person_heights']['median']} / {sc[k]['keypoint_position_deviation_vs_scale_1_in_person_heights']['p90']}" for k in keys) + " |")
    L.append("| shoulder/hip frame-to-frame jitter, median / p90 (person heights) | " + " | ".join(f"{sc[k]['mid_shoulder_hip_frame_to_frame_jitter_in_person_heights']['median']} / {sc[k]['mid_shoulder_hip_frame_to_frame_jitter_in_person_heights']['p90']}" for k in keys) + " |")
    L.append("| inference ms per frame, mean / p95 | " + " | ".join(f"{sc[k]['inference_ms']['mean']} / {sc[k]['inference_ms']['p95']}" for k in keys) + " |")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("make", "measure"))
    ap.add_argument("--scales", default="1.0,0.75,0.5,0.35,0.25")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    scales = [float(x) for x in a.scales.split(",") if x]
    if a.cmd == "make":
        make(scales)
        return
    if a.out is None:
        raise SystemExit("--out is required for measure")
    js, md = a.out.with_suffix(".json"), a.out.with_suffix(".md")
    if js.exists() or md.exists():
        raise SystemExit("output exists: not overwriting")
    res = measure(scales)
    js.write_text(json.dumps(res, indent=2), encoding="utf-8")
    md.write_text(to_md(res), encoding="utf-8")
    print(to_md(res))


if __name__ == "__main__":
    main()
