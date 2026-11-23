"""Synthetic COCO-17 skeleton generator for engine tests.

This is TEST INPUT, not data shown anywhere in the product. It produces plausible
keypoints for a person of standing height H (pixels) so each scenario can be
described by a hip trajectory + torso angle + leg posture over time.
"""
from __future__ import annotations

import math

import numpy as np

GROUND = 700.0
H = 300.0          # standing height in px
FRAME = (1280, 720)


def pose(cx: float, hip_y: float, torso_deg: float, legs: str = "straight", h: float = H,
         hide_legs: bool = False, conf: float = 0.9, lean_sign: float = 1.0):
    """Keypoints (17,3) + bbox for one person. torso_deg: 0 upright .. 90 horizontal."""
    th = math.radians(torso_deg) * lean_sign
    u = np.array([math.sin(th), -math.cos(th)])          # hip -> shoulders
    hip = np.array([cx, hip_y])
    sho = hip + u * 0.30 * h
    head = hip + u * 0.46 * h
    side = np.array([math.cos(th), math.sin(th)]) * 0.07 * h
    if legs == "straight":
        d = -u
        knee_v, ank_v = d * 0.25 * h, d * 0.50 * h
    elif legs == "sit":          # thighs forward, shins down
        knee_v, ank_v = np.array([0.22 * h, 0.0]), np.array([0.22 * h, 0.25 * h])
    elif legs == "kneel":        # thighs down, shins back along the floor
        knee_v, ank_v = np.array([0.0, 0.25 * h]), np.array([-0.25 * h, 0.25 * h])
    else:                        # "down": legs straight down regardless of torso (bending over)
        knee_v, ank_v = np.array([0.0, 0.25 * h]), np.array([0.0, 0.50 * h])
    kp = np.zeros((17, 3))
    kp[0] = [*head, conf]
    kp[1] = [*(head + [-0.02 * h, -0.02 * h]), conf]
    kp[2] = [*(head + [0.02 * h, -0.02 * h]), conf]
    kp[3] = [*(head + [-0.05 * h, 0]), conf]
    kp[4] = [*(head + [0.05 * h, 0]), conf]
    kp[5] = [*(sho - side), conf]
    kp[6] = [*(sho + side), conf]
    kp[7] = [*(sho - side + [0, 0.12 * h]), conf]
    kp[8] = [*(sho + side + [0, 0.12 * h]), conf]
    kp[9] = [*(sho - side + [0, 0.24 * h]), conf]
    kp[10] = [*(sho + side + [0, 0.24 * h]), conf]
    kp[11] = [*(hip - side * 0.6), conf]
    kp[12] = [*(hip + side * 0.6), conf]
    kp[13] = [*(hip - side * 0.6 + knee_v), conf]
    kp[14] = [*(hip + side * 0.6 + knee_v), conf]
    kp[15] = [*(hip - side * 0.6 + ank_v), conf]
    kp[16] = [*(hip + side * 0.6 + ank_v), conf]
    if hide_legs:
        kp[13:, 2] = 0.0
    vis = kp[kp[:, 2] > 0.3, :2]
    pad = 0.04 * h
    bbox = (float(vis[:, 0].min() - pad), float(vis[:, 1].min() - pad),
            float(vis[:, 0].max() + pad), float(vis[:, 1].max() + pad))
    return kp, bbox


def person(tid: int, ts: float, *a, **k) -> dict:
    kp, bbox = pose(*a, **k)
    return {"track_id": tid, "bbox": bbox, "confidence": 0.9, "keypoints": kp}


def lerp(a, b, t):
    t = min(1.0, max(0.0, t))
    return a + (b - a) * t


class Timeline:
    """Builds a list of (ts, [people]) at a fixed fps from segment functions."""

    def __init__(self, fps: float = 5.0):
        self.dt = 1.0 / fps
        self.t = 0.0
        self.frames: list[tuple[float, list[dict]]] = []

    def run(self, seconds: float, fn, tid: int = 1):
        """fn(local_t) -> kwargs for pose(); local_t in [0, seconds]."""
        n = max(1, int(round(seconds / self.dt)))
        for i in range(n):
            lt = (i + 1) * self.dt
            self.t += self.dt
            args = fn(lt)
            self.frames.append((self.t, [person(tid, self.t, **args)]))
        return self

    def hold(self, seconds: float, **kw):
        return self.run(seconds, lambda lt: kw)


def stand_kw(cx: float = 600.0):
    return dict(cx=cx, hip_y=GROUND - 0.5 * H, torso_deg=2.0, legs="straight")


LYING_HIP_Y = GROUND - 0.06 * H


def lying_kw(cx: float = 600.0):
    return dict(cx=cx, hip_y=LYING_HIP_Y, torso_deg=88.0, legs="straight")
