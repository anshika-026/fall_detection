"""Person-scale experiment: the transform and the measurements, on synthetic caches (no model, no video needed)."""
import pickle

import numpy as np

from tools import scale_experiment as se

W, H = 640, 480


def _kp(box, conf=0.9):
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2
    ys = np.linspace(y1, y2, 17)
    return np.stack([np.full(17, cx), ys, np.full(17, conf)], 1)


def _frame(i, box, conf=0.9, tid=1):
    return {"i": i, "ts": i * 0.2, "people": [{"track_id": tid, "bbox": list(box), "confidence": 0.9, "keypoints": _kp(box, conf)}]}


def _write(tmp_path, scale, frames, ms=100.0):
    folder = tmp_path / se.tag(scale) / "cache" / se.CACHE_SUB
    folder.mkdir(parents=True)
    d = {"frame_wh": (W, H), "frames": frames, "infer_ms": [ms] * len(frames)}
    (folder / "clipA.pkl").write_bytes(pickle.dumps(d))


def _mapped(box, s):
    nw, nh = round(W * s), round(H * s)
    ox, oy = (W - nw) // 2, (H - nh) // 2
    return [box[0] * nw / W + ox, box[1] * nh / H + oy, box[2] * nw / W + ox, box[3] * nh / H + oy]


def test_shrink_keeps_the_frame_size_and_centres_the_smaller_picture():
    f = np.full((H, W, 3), 200, np.uint8)
    out, (sx, sy, ox, oy) = se.shrink(f, 0.5)
    assert out.shape == f.shape and (sx, sy, ox, oy) == (0.5, 0.5, 160, 120)
    assert out[0, 0, 0] == se.GREY and out[H // 2, W // 2, 0] == 200               # grey border, picture in the middle
    same, m = se.shrink(f, 1.0)
    assert same is f and m == (1.0, 1.0, 0, 0)


def test_measure_matches_boxes_through_the_transform_and_counts_losses(tmp_path, monkeypatch):
    monkeypatch.setattr(se, "EXP", tmp_path)
    box = [200.0, 100.0, 300.0, 400.0]
    n = 6
    _write(tmp_path, 1.0, [_frame(i, box) for i in range(n)], ms=100.0)
    # at 0.5: the same person found in 4 of 6 frames, 2 frames lost; one extra box in frame 0
    frames = []
    for i in range(n):
        if i in (2, 3):
            frames.append({"i": i, "ts": i * 0.2, "people": []})
            continue
        fr = _frame(i, _mapped(box, 0.5), conf=0.6)
        if i == 0:
            fr["people"].append({"track_id": 9, "bbox": [0, 0, 20, 20], "confidence": 0.5, "keypoints": _kp([0, 0, 20, 20], 0.5)})
        frames.append(fr)
    _write(tmp_path, 0.5, frames, ms=90.0)
    res = se.measure([1.0, 0.5])["scales"]
    base, half = res["1.0"], res["0.5"]
    assert base["person_detection_recall_vs_scale_1"] == 1.0 and base["extra_boxes_per_analysed_frame"] == 0.0
    assert half["reference_persons"] == 6 and half["matched_persons"] == 4
    assert half["person_detection_recall_vs_scale_1"] == round(4 / 6, 4)
    assert half["frames_with_any_person_share"] == round(4 / 6, 4)
    assert half["extra_boxes_per_analysed_frame"] == round(1 / 6, 4)
    assert half["keypoint_position_deviation_vs_scale_1_in_person_heights"]["median"] < 0.01   # same person, positions map back exactly
    assert half["mean_keypoint_confidence_matched"] == 0.6 and base["mean_keypoint_confidence_matched"] == 0.9
    assert half["median_person_height_in_640_model_input_px"] == round(base["median_person_height_in_640_model_input_px"] * 0.5, 4)
    assert half["inference_ms"]["mean"] == 90.0
    assert "x0.5" in se.to_md(se.measure([1.0, 0.5]))
