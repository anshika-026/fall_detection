"""Fall-detection thresholds. Every value is configurable from the Settings page
(stored in the database, see falldet.settings_store). All time comparisons are in
SECONDS and all distances in units of the person's own standing height, so the
engine does not depend on frame rate or on camera resolution / zoom."""
from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass
class FallConfig:
    enabled: bool = True
    # --- keypoint / person filtering
    kpt_conf: float = 0.4               # a keypoint below this confidence is ignored
    min_person_conf: float = 0.4        # detector confidence for a person to be analysed
    # --- posture ("lying") votes: >= 2 of the available votes must agree
    lying_torso_angle: float = 55.0     # deg from vertical
    lying_aspect: float = 1.0           # bbox width / height
    lying_extent_ratio: float = 0.45    # keypoint vertical extent / standing height
    lying_aspect_strong: float = 1.5    # with too few keypoints to vote, a box this wide/tall alone means lying
    lying_aspect_override: float = 1.2  # a box at least this wide/tall means lying even if the torso-angle vote disagrees (a fall seen from the
                                        # front or back squashes the torso angle). 0 = off (the original 2-of-3 votes only).
    # --- upright (used for recovery)
    recovery_torso_angle: float = 45.0
    recovery_extent_ratio: float = 0.55
    # --- trigger: a rapid descent that ends lying
    descent_window: float = 1.5         # s over which the descent is measured
    min_drop: float = 0.30              # hip drop, in standing heights
    min_velocity: float = 0.50          # standing heights per second
    min_top_drop: float = 0.45          # alternative signal: the top of the person (head) drops this far ...
    min_top_velocity: float = 0.30      # ... at this rate (standing heights/s). Hips barely move in the image for
                                        # a fall from a chair or towards the camera; the head always does.
    min_angle_swing: float = 45.0       # alternative signal: torso rotation (deg) ...
    min_angle_rate: float = 60.0        # ... at this deg/s, plus half of min_drop
    floor_lie_seconds: float = 4.0      # second way in: lying and still on the floor this long with NO fall seen (slow lie-down,
                                        # first seen on the floor, or the tracker lost the person mid-fall) => POSSIBLE. 0 = off.
    floor_lie_max_gap_s: float = 1.0    # ... and the person must be SEEN throughout: a gap longer than this between two analyses in the window
                                        # (tracking lost, nobody detected) means the floor rule does not fire. 1000 = no check (the original rule).
    floor_lie_min_fraction: float = 0.8 # the floor rule needs this share of the window classed lying (1.0 = every sample, the original rule)
    descent_ref_fallback: bool = True   # no standing height known (e.g. seen sitting on the floor): scale by the body length seen so far
                                        # instead of discarding the fall. False = the original behaviour.
    upright_lookback: float = 4.0       # must have been upright-ish this recently (s)
    upright_extent_ratio: float = 0.6   # what counts as "upright-ish" before the fall
    # --- confirmation / recovery / resolution (seconds)
    confirm_seconds: float = 3.0        # lying + still for this long => CONFIRMED
    partial_confirm_factor: float = 1.5 # longer when the person is only partly visible
    max_motion_rate: float = 0.5        # standing heights/s of hip motion still counted as "still"
    dismiss_seconds: float = 1.0        # back on their feet this long while POSSIBLE => dismissed
    possible_timeout: float = 10.0      # POSSIBLE this long without settling => dismissed
    recovery_seconds: float = 2.0       # upright this long while CONFIRMED => RECOVERED
    relapse_seconds: float = 2.0        # lying again this long while RECOVERED => back to CONFIRMED
    auto_resolve_seconds: float = 60.0  # RECOVERED -> RESOLVED automatically after this
    rearm_seconds: float = 3.0          # upright this long after RESOLVED => may alert again
    # --- tracking robustness
    track_ttl: float = 5.0              # forget an idle track after this
    orphan_after: float = 1.0           # active track unseen this long => keep as orphan
    orphan_timeout: float = 120.0       # orphan not re-found within this => closed as "lost"
    history_seconds: float = 8.0


# Sensitivity presets scale the trigger thresholds (smaller = triggers more easily).
SENSITIVITY = {"low": 1.25, "medium": 1.0, "high": 0.8}


def from_settings(data: dict | None, sensitivity: str | None = None) -> FallConfig:
    """Build a FallConfig from stored settings (unknown keys ignored, bad values
    keep the default), then apply the sensitivity preset."""
    cfg = FallConfig()
    known = {f.name: f for f in fields(FallConfig)}
    for k, v in (data or {}).items():
        f = known.get(k)
        if f is None:
            continue
        try:
            setattr(cfg, k, bool(v) if f.type in ("bool", bool) else float(v))
        except (TypeError, ValueError):
            pass
    scale = SENSITIVITY.get((sensitivity or "medium").lower(), 1.0)
    if scale != 1.0:
        cfg.min_drop *= scale
        cfg.min_velocity *= scale
        cfg.min_top_drop *= scale
        cfg.min_top_velocity *= scale
        cfg.min_angle_swing *= scale
    return cfg
