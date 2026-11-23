"""COCO-17 keypoint helpers (the layout yolov8n-pose outputs) and per-frame
posture features computed from a single pose. Pure numpy, no model needed, so
the whole fall engine can be tested on synthetic or recorded keypoints."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

NOSE, L_EYE, R_EYE, L_EAR, R_EAR = 0, 1, 2, 3, 4
L_SHO, R_SHO, L_ELB, R_ELB, L_WRI, R_WRI = 5, 6, 7, 8, 9, 10
L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANK, R_ANK = 11, 12, 13, 14, 15, 16
N_KEYPOINTS = 17

SKELETON = [(5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12), (11, 12),
            (11, 13), (13, 15), (12, 14), (14, 16), (0, 1), (0, 2), (1, 3), (2, 4)]


def _mid(kp: np.ndarray, idx: tuple[int, ...], thr: float):
    """Mean (x, y) of the confident keypoints among idx, or None."""
    pts = [kp[i, :2] for i in idx if kp[i, 2] >= thr]
    if not pts:
        return None
    return np.mean(pts, axis=0)


@dataclass
class PoseFeatures:
    """Raw (pixel-space) features of one detected person in one frame."""
    ts: float
    bbox: tuple[float, float, float, float]
    w: float
    h: float
    aspect: float                 # bbox width / height
    torso_angle: float | None     # deg from vertical: 0 upright .. 90 horizontal
    cy: float                     # vertical centre-of-mass proxy (hip y, else bbox centre)
    extent: float                 # vertical extent of the confident keypoints (px)
    n_visible: int                # confident keypoints
    partial: bool                 # shoulders or hips missing, or box cut by the frame edge
    quality: float                # mean confidence of the confident keypoints, 0..1
    head_y: float | None
    ankle_y: float | None
    torso_len: float | None       # shoulder-mid to hip-mid distance (px), None if either is missing


def extract_features(ts: float, bbox, kpts, frame_wh: tuple[int, int] | None, kpt_conf: float = 0.4) -> PoseFeatures:
    x1, y1, x2, y2 = (float(v) for v in bbox)
    w, h = max(1.0, x2 - x1), max(1.0, y2 - y1)
    kp = np.asarray(kpts, dtype=float).reshape(-1, 3) if kpts is not None else np.zeros((N_KEYPOINTS, 3))
    ok = kp[:, 2] >= kpt_conf
    n_vis = int(ok.sum())
    sho = _mid(kp, (L_SHO, R_SHO), kpt_conf)
    hip = _mid(kp, (L_HIP, R_HIP), kpt_conf)
    ank = _mid(kp, (L_ANK, R_ANK), kpt_conf)
    head = _mid(kp, (NOSE,), kpt_conf)
    if head is None:
        head = _mid(kp, (L_EYE, R_EYE, L_EAR, R_EAR), kpt_conf)
    angle = None
    torso_len = None
    if sho is not None and hip is not None and float(np.hypot(*(sho - hip))) > 1.0:
        dx, dy = abs(sho[0] - hip[0]), abs(sho[1] - hip[1])
        angle = math.degrees(math.atan2(dx, dy))
        torso_len = float(np.hypot(dx, dy))
    cy = float(hip[1]) if hip is not None else (y1 + y2) / 2.0
    extent = float(kp[ok, 1].max() - kp[ok, 1].min()) if n_vis >= 4 else h
    edge = False
    if frame_wh:
        fw, fh = frame_wh
        m = 3.0
        edge = x1 <= m or y1 <= m or x2 >= fw - m or y2 >= fh - m
    partial = sho is None or hip is None or edge
    quality = float(kp[ok, 2].mean()) if n_vis else 0.0
    return PoseFeatures(ts=ts, bbox=(x1, y1, x2, y2), w=w, h=h, aspect=w / h, torso_angle=angle, cy=cy,
                        extent=extent, n_visible=n_vis, partial=partial, quality=quality,
                        head_y=None if head is None else float(head[1]),
                        ankle_y=None if ank is None else float(ank[1]), torso_len=torso_len)
