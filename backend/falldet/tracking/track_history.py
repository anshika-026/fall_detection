"""Per-person pose history. One TrackHistory per (camera, track id); it lives
inside that camera's CameraFallEngine, so histories can never cross cameras."""
from __future__ import annotations

import collections
import statistics
from dataclasses import dataclass

from falldet.pose_estimation.keypoints import PoseFeatures


@dataclass
class Sample:
    f: PoseFeatures
    cy_s: float          # cy smoothed by a 3-sample median (removes single-frame keypoint jitter)
    lying: bool | None   # None = too few usable signals to tell
    upright: bool
    votes: int
    n_votes: int
    ext_ratio: float | None  # keypoint extent / standing height (None until a standing height is known)


class TrackHistory:
    def __init__(self, track_id: int, history_seconds: float):
        self.track_id = track_id
        self.history_seconds = history_seconds
        self.samples: collections.deque[Sample] = collections.deque()
        self.stand_h: float | None = None     # the person's standing height (px), learned from upright frames
        self.last_seen = 0.0
        self.first_seen = 0.0

    def add(self, s: Sample) -> None:
        if not self.samples:
            self.first_seen = s.f.ts
        self.samples.append(s)
        self.last_seen = s.f.ts
        cut = s.f.ts - self.history_seconds
        while self.samples and self.samples[0].f.ts < cut:
            self.samples.popleft()

    def smooth_cy(self, cy: float) -> float:
        recent = [x.f.cy for x in list(self.samples)[-2:]] + [cy]
        return statistics.median(recent)

    def observe_upright(self, height: float) -> None:
        """Called for unambiguously upright frames with an estimate of the person's
        standing height (px): tracked as an EMA, so walking towards/away from the
        camera is followed."""
        self.stand_h = height if self.stand_h is None else 0.8 * self.stand_h + 0.2 * height

    def body_length(self) -> float | None:
        """Longest box side seen so far (px): a stand-in for the person's height when no standing height was ever observed."""
        return max((max(s.f.w, s.f.h) for s in self.samples), default=None)

    def window(self, now: float, seconds: float) -> list[Sample]:
        return [s for s in self.samples if s.f.ts >= now - seconds]
