"""Rule-based fall engine: per-person posture history -> temporal signals ->
state machine

    NORMAL -> POSSIBLE -> CONFIRMED -> RECOVERED -> RESOLVED

One CameraFallEngine exists per camera and owns all of that camera's track
histories, so camera A's tracks can never influence camera B's. The engine is
pure Python/numpy (no model, no I/O): it consumes {track_id, bbox, confidence,
keypoints} dicts and returns FallEvents, so it is unit-testable on synthetic or
recorded keypoints.

Why several signals and not one: a single cue (bbox aspect ratio, body angle)
fires on bending, sitting, kneeling and exercise. A fall is declared only when
ALL of these agree over time:

  1. a rapid DESCENT of the hips (drop >= min_drop standing-heights at
     >= min_velocity), or a fast torso rotation together with a partial drop;
  2. the person is LYING at the end of it (>= 2 of: torso angle, bbox aspect,
     collapsed vertical extent of the keypoints);
  3. they were UPRIGHT-ish shortly before (so someone first seen on the floor,
     or already lying, is not a "fall");
  4. they STAY down and still for confirm_seconds (so burpees, sit-ups and
     people who immediately get back up are dismissed).

Known limits are documented in docs/LIMITATIONS.md.
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field

from falldet.fall_analysis.config import FallConfig
from falldet.pose_estimation.keypoints import extract_features
from falldet.tracking.track_history import Sample, TrackHistory

log = logging.getLogger("fall_engine")

NORMAL, POSSIBLE, CONFIRMED, RECOVERED, RESOLVED = "NORMAL", "POSSIBLE", "CONFIRMED", "RECOVERED", "RESOLVED"
ACTIVE_STATES = (POSSIBLE, CONFIRMED, RECOVERED)


@dataclass
class FallEvent:
    kind: str            # possible | confirmed | recovered | relapse | resolved | dismissed | lost
    camera_id: int
    track_id: int
    ts: float
    confidence: float
    bbox: tuple[float, float, float, float]
    metrics: dict = field(default_factory=dict)
    reason: str = ""
    fsm: object = field(default=None, repr=False, compare=False)   # the person's state machine (holds incident_key)


def classify(f, stand_h: float | None, cfg: FallConfig):
    """-> (lying | None, upright, votes, n_votes, ext_ratio) for one frame."""
    # The vertical-extent vote only means something when the whole body (head to ankles) is
    # visible; with the legs hidden (desk, counter, frame edge) it would read "collapsed".
    full_body = f.head_y is not None and f.ankle_y is not None
    ext_ratio = (f.extent / stand_h) if (stand_h and full_body) else None
    votes = n = 0
    if f.torso_angle is not None:
        n += 1
        votes += f.torso_angle >= cfg.lying_torso_angle
    n += 1
    votes += f.aspect >= cfg.lying_aspect
    if ext_ratio is not None:
        n += 1
        votes += ext_ratio <= cfg.lying_extent_ratio
    lying: bool | None = None
    if n >= 2:
        lying = votes >= 2
    elif f.aspect >= cfg.lying_aspect_strong:
        lying = True      # too few keypoints to vote (a person on the floor is often poorly detected)
    if cfg.lying_aspect_override > 0 and f.aspect >= cfg.lying_aspect_override:
        lying = True      # clearly wider than tall: the torso-angle vote is unreliable seen from the front/back
    upright = (lying is False and f.aspect < cfg.lying_aspect
               and (f.torso_angle is None or f.torso_angle <= cfg.recovery_torso_angle)
               and (ext_ratio is None or ext_ratio >= cfg.recovery_extent_ratio))
    return lying, upright, int(votes), n, ext_ratio


REATTACH_S = 3.0        # a person lost this recently may be re-identified with a new / missing track id
SYNTH_ID_BASE = 10_000_000   # engine-made ids (ByteTrack gave none) start here, so they never collide with tracker ids

TORSO_FRACTION = 0.30   # shoulder-to-hip distance as a fraction of standing height (typical adult)


def _standing_height(f) -> float | None:
    """Standing height (px) if this frame is unambiguously upright, else None.
    Whole body visible: the box height. Legs hidden (desk, counter, frame edge): estimated from
    the torso length, which is the same sitting or standing, so a seated person gives a correct
    reference rather than a too-small one."""
    if f.aspect >= 0.8 or (f.torso_angle is not None and f.torso_angle >= 30):
        return None
    if f.ankle_y is not None and f.head_y is not None and f.extent >= 0.8 * f.h and not f.partial:
        return f.h
    if f.torso_len is not None and f.torso_angle is not None and f.n_visible >= 6:
        return f.torso_len / TORSO_FRACTION
    return None


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


class TrackFSM:
    def __init__(self, cfg: FallConfig):
        self.cfg = cfg
        self.state = NORMAL
        self.entered_at = 0.0
        self.not_lying_since: float | None = None
        self.upright_since: float | None = None
        self.lying_since: float | None = None
        self.confidence = 0.0
        self.trigger: dict = {}
        self.incident_key: int | None = None  # set by the caller (DB incident id)

    def _enter(self, state: str, ts: float) -> None:
        self.state = state
        self.entered_at = ts
        self.not_lying_since = self.upright_since = self.lying_since = None

    # -- signals ---------------------------------------------------------------
    def _descent(self, hist: TrackHistory, now: float) -> dict | None:
        cfg, cur = self.cfg, hist.samples[-1]
        ref = self._ref_height(hist)
        if not cur.lying or not ref:
            return None
        lookback = hist.window(now, cfg.upright_lookback)[:-1]
        if not any(s.lying is False and (s.ext_ratio is None or s.ext_ratio >= cfg.upright_extent_ratio)
                   for s in lookback):
            return None  # never seen upright recently: first seen lying, or lying for a long time
        win = hist.window(now, cfg.descent_window)
        # Fastest qualifying descent inside the window: compare the CURRENT hip height
        # (raw: smoothing lags a fast fall by a frame) with each earlier, smoothed sample.
        # Using the highest point in the window instead would measure a fast fall over the
        # time the person had been standing still before it began, and call it slow.
        max_drop = 0.0                      # largest drop from any earlier sample (for the angle signal)
        fast_drop = fast_vel = 0.0          # the fastest pair whose drop reaches min_drop
        for s in win[:-1]:
            d = (cur.f.cy - s.cy_s) / ref
            if d <= 0:
                continue
            max_drop = max(max_drop, d)
            v = d / max(cur.f.ts - s.f.ts, 0.25)
            if d >= cfg.min_drop and v > fast_vel:
                fast_drop, fast_vel = d, v
        drop, vel = (fast_drop, fast_vel) if fast_vel else (max_drop, 0.0)
        swing = rate = 0.0
        ang = [s for s in win if s.f.torso_angle is not None]
        if cur.f.torso_angle is not None and ang:
            low = min(ang, key=lambda s: s.f.torso_angle)
            swing = cur.f.torso_angle - low.f.torso_angle
            rate = swing / max(cur.f.ts - low.f.ts, 0.25)
        # Head signal: how far the top of the person fell (same fastest-qualifying-pair logic).
        top_drop = top_vel = 0.0
        for s in win[:-1]:
            d = (cur.f.bbox[1] - s.f.bbox[1]) / ref
            if d >= cfg.min_top_drop:
                v = d / max(cur.f.ts - s.f.ts, 0.25)
                if v > top_vel:
                    top_drop, top_vel = d, v
        drop_ok = drop >= cfg.min_drop and vel >= cfg.min_velocity
        top_ok = top_drop >= cfg.min_top_drop and top_vel >= cfg.min_top_velocity
        angle_ok = swing >= cfg.min_angle_swing and rate >= cfg.min_angle_rate and drop >= 0.5 * cfg.min_drop
        if not (drop_ok or angle_ok or top_ok):
            return None
        if not (drop_ok or angle_ok):
            drop, vel = top_drop, top_vel           # report the signal that fired
        return {"drop": round(drop, 3), "velocity": round(vel, 3), "angle_swing": round(swing, 1),
                "angle_rate": round(rate, 1), "signal": "drop" if drop_ok else ("angle" if angle_ok else "head")}

    def _ref_height(self, hist: TrackHistory) -> float | None:
        """Height all distances are measured in: the learned standing height, else (if allowed) the body length seen so far."""
        if hist.stand_h:
            return hist.stand_h
        return hist.body_length() if self.cfg.descent_ref_fallback else None

    def _floor_lie(self, hist: TrackHistory, now: float) -> dict | None:
        """A person who has been lying and still for `floor_lie_seconds`, without the fall itself having been seen
        (it was slow, happened before they were tracked, or the tracker lost them mid-fall). Without this a person on
        the floor is shown as a normal 'Person' forever. The usual stay-down confirmation still follows."""
        cfg = self.cfg
        if cfg.floor_lie_seconds <= 0:
            return None
        win = hist.window(now, cfg.floor_lie_seconds)
        if len(win) < 2 or win[-1].f.ts - win[0].f.ts < 0.8 * cfg.floor_lie_seconds:
            return None
        if not win[-1].lying or sum(bool(s.lying) for s in win) < cfg.floor_lie_min_fraction * len(win):
            return None      # (a sample with too few keypoints has lying=None and counts as NOT lying)
        if max(b.f.ts - a.f.ts for a, b in zip(win, win[1:])) > cfg.floor_lie_max_gap_s:
            return None      # the person was not seen for part of the window: an unobserved gap is not lying time
        if self._motion_rate(hist, now, cfg.floor_lie_seconds) > cfg.max_motion_rate:
            return None
        return {"drop": 0.0, "velocity": 0.0, "angle_swing": 0.0, "angle_rate": 0.0, "signal": "lying"}

    def _motion_rate(self, hist: TrackHistory, now: float, seconds: float) -> float:
        win = hist.window(now, seconds)
        ref = self._ref_height(hist)
        if len(win) < 2 or not ref:
            return 0.0
        path = 0.0
        for a, b in zip(win, win[1:]):
            ax, bx = (a.f.bbox[0] + a.f.bbox[2]) / 2, (b.f.bbox[0] + b.f.bbox[2]) / 2
            path += math.hypot(bx - ax, b.cy_s - a.cy_s)
        span = max(win[-1].f.ts - win[0].f.ts, 0.25)
        return path / ref / span

    def _confidence(self, cur: Sample, immobile_ratio: float) -> float:
        t = self.trigger
        drop_s = min(1.0, t.get("drop", 0.0) / (2 * self.cfg.min_drop))
        vel_s = min(1.0, t.get("velocity", 0.0) / (2 * self.cfg.min_velocity))
        trig = max(drop_s * 0.5 + vel_s * 0.5, min(1.0, t.get("angle_swing", 0.0) / 90.0) * 0.8)
        lying_s = cur.votes / max(cur.n_votes, 1)
        return round(min(1.0, 0.30 * trig + 0.25 * lying_s + 0.25 * immobile_ratio + 0.20 * cur.f.quality), 3)

    def _metrics(self, hist: TrackHistory, motion: float) -> dict:
        cur = hist.samples[-1]
        m = dict(self.trigger)
        m.update({"torso_angle": None if cur.f.torso_angle is None else round(cur.f.torso_angle, 1),
                  "aspect": round(cur.f.aspect, 2),
                  "extent_ratio": None if cur.ext_ratio is None else round(cur.ext_ratio, 2),
                  "motion_rate": round(motion, 3), "quality": round(cur.f.quality, 2), "partial": cur.f.partial})
        return m

    # -- state machine ----------------------------------------------------------
    def update(self, hist: TrackHistory, camera_id: int, now: float) -> list[FallEvent]:
        cfg, cur, out = self.cfg, hist.samples[-1], []

        def ev(kind: str, reason: str = "") -> None:
            out.append(FallEvent(kind, camera_id, hist.track_id, now, self.confidence, cur.f.bbox,
                                 self._metrics(hist, self._motion_rate(hist, now, cfg.confirm_seconds)), reason, self))

        lying, upright = bool(cur.lying), cur.upright

        if self.state == NORMAL:
            trig = self._descent(hist, now) or self._floor_lie(hist, now)
            if trig:
                self.trigger = trig
                self.confidence = self._confidence(cur, 0.0)
                self._enter(POSSIBLE, now)
                ev("possible")

        elif self.state == POSSIBLE:
            if lying:
                self.not_lying_since = None
            else:
                self.not_lying_since = self.not_lying_since or now
            if self.not_lying_since is not None and now - self.not_lying_since >= cfg.dismiss_seconds:
                self._enter(NORMAL, now)
                ev("dismissed", "got back up before confirmation")
            else:
                need = cfg.confirm_seconds * (cfg.partial_confirm_factor if cur.f.partial else 1.0)
                waited = now - self.entered_at
                motion = self._motion_rate(hist, now, min(need, max(waited, 0.5)))
                self.confidence = self._confidence(cur, min(1.0, waited / need) if motion <= cfg.max_motion_rate else 0.0)
                if waited >= need and motion <= cfg.max_motion_rate and lying:
                    self._enter(CONFIRMED, now)
                    ev("confirmed")
                elif waited >= cfg.possible_timeout:
                    self._enter(NORMAL, now)
                    ev("dismissed", "kept moving: not a fall")

        elif self.state == CONFIRMED:
            self.upright_since = (self.upright_since or now) if upright else None
            if self.upright_since is not None and now - self.upright_since >= cfg.recovery_seconds:
                self._enter(RECOVERED, now)
                ev("recovered")

        elif self.state == RECOVERED:
            self.lying_since = (self.lying_since or now) if lying else None
            if self.lying_since is not None and now - self.lying_since >= cfg.relapse_seconds:
                self._enter(CONFIRMED, now)
                ev("relapse")
            elif now - self.entered_at >= cfg.auto_resolve_seconds:
                self._enter(RESOLVED, now)
                ev("resolved", "auto: recovered and no operator action")

        elif self.state == RESOLVED:
            # Stay quiet until the person is upright again, so a person who is still
            # on the floor after an operator resolved the alert is not re-alerted.
            self.upright_since = (self.upright_since or now) if upright else None
            if self.upright_since is not None and now - self.upright_since >= cfg.rearm_seconds:
                self._enter(NORMAL, now)
            else:
                # A fresh upright -> rapid descent -> lying sequence is a NEW fall even
                # if the person never stayed upright long enough to re-arm. A person who
                # simply stays on the floor has no upright frames in the lookback, so
                # they cannot re-trigger.
                trig = self._descent(hist, now)
                if trig:
                    self.trigger = trig
                    self.confidence = self._confidence(cur, 0.0)
                    self._enter(POSSIBLE, now)
                    ev("possible")
        return out

    def resolve_externally(self, ts: float) -> None:
        if self.state in ACTIVE_STATES:
            self._enter(RESOLVED, ts)


class CameraFallEngine:
    """All fall analysis for ONE camera."""

    def __init__(self, camera_id: int, cfg: FallConfig | None = None):
        self.camera_id = camera_id
        self.cfg = cfg or FallConfig()
        self.tracks: dict[int, tuple[TrackHistory, TrackFSM]] = {}
        self.orphans: list[tuple[float, TrackHistory, TrackFSM]] = []  # (lost_at, hist, fsm)
        self.frame_wh: tuple[int, int] | None = None
        self.last_ts = 0.0
        self._next_synth = 0

    def set_config(self, cfg: FallConfig) -> None:
        self.cfg = cfg
        for hist, fsm in self.tracks.values():
            fsm.cfg = cfg
            hist.history_seconds = cfg.history_seconds
        for _, hist, fsm in self.orphans:
            fsm.cfg = cfg

    # -- main entry ---------------------------------------------------------------
    def update(self, ts: float, people: list[dict], frame_wh: tuple[int, int] | None = None) -> list[FallEvent]:
        cfg, events = self.cfg, []
        if frame_wh:
            self.frame_wh = frame_wh
        self.last_ts = ts
        seen: set[int] = set()
        people = self._assign_missing_ids(people, ts)
        present = {p.get("track_id") for p in people if p.get("track_id") is not None}
        for p in people:
            tid = p.get("track_id")
            if tid is None or p.get("confidence", 1.0) < cfg.min_person_conf or tid in seen:
                continue
            seen.add(tid)
            entry = self.tracks.get(tid)
            if entry is None:
                entry = self._adopt_orphan(tid, p["bbox"], present, ts) or (TrackHistory(tid, cfg.history_seconds), TrackFSM(cfg))
                self.tracks[tid] = entry
            hist, fsm = entry
            f = extract_features(ts, p["bbox"], p.get("keypoints"), self.frame_wh, cfg.kpt_conf)
            height = _standing_height(f)
            if height is not None:
                hist.observe_upright(height)
            lying, upright, votes, n, ext = classify(f, hist.stand_h, cfg)
            hist.add(Sample(f, hist.smooth_cy(f.cy), lying, upright, votes, n, ext))
            if cfg.enabled:
                try:
                    events += fsm.update(hist, self.camera_id, ts)
                except Exception:
                    log.exception("camera %s track %s: fall analysis failed", self.camera_id, tid)

        # tracks not seen this update
        for tid in [t for t in self.tracks if t not in seen]:
            hist, fsm = self.tracks[tid]
            gap = ts - hist.last_seen
            if fsm.state in ACTIVE_STATES and gap >= cfg.orphan_after:
                self.orphans.append((hist.last_seen, hist, fsm))
                del self.tracks[tid]
            elif gap >= cfg.track_ttl:
                del self.tracks[tid]
        # orphans never re-found
        keep = []
        for lost_at, hist, fsm in self.orphans:
            if ts - lost_at >= cfg.orphan_timeout:
                cur = hist.samples[-1]
                kind = "dismissed" if fsm.state == POSSIBLE else "lost"
                events.append(FallEvent(kind, self.camera_id, hist.track_id, ts, fsm.confidence, cur.f.bbox,
                                        fsm._metrics(hist, 0.0), "person no longer visible", fsm))
            else:
                keep.append((lost_at, hist, fsm))
        self.orphans = keep
        return events

    def _assign_missing_ids(self, people: list[dict], ts: float) -> list[dict]:
        """ByteTrack returns a person without an id when its tracker has nothing confirmed for the frame
        (typically right after a fall: the box changes abruptly and a new track needs two matching frames).
        A person lying at the frame edge would then never be analysed. Such a detection is matched to the
        recently seen track that is closest to it (continuity), else gets an engine id."""
        if all(p.get("track_id") is not None for p in people):
            return people
        used = {p["track_id"] for p in people if p.get("track_id") is not None}
        assigned: dict[int, int] = {}                  # index in `people` -> track id
        # most confident detection first: it claims the recent track, a weaker duplicate gets its own id
        for i in sorted((i for i, p in enumerate(people) if p.get("track_id") is None
                         and p.get("confidence", 1.0) >= self.cfg.min_person_conf),
                        key=lambda i: -people[i].get("confidence", 1.0)):
            tid = self._nearest_recent_track(people[i]["bbox"], used, ts)
            if tid is None:
                tid = SYNTH_ID_BASE + self._next_synth
                self._next_synth += 1
            used.add(tid)
            assigned[i] = tid
        return [{**p, "track_id": assigned[i]} if i in assigned else p for i, p in enumerate(people)]

    def _nearest_recent_track(self, bbox, used: set, ts: float) -> int | None:
        best, best_score = None, 0.0
        for tid, (hist, _) in self.tracks.items():
            if tid in used or not hist.samples or ts - hist.last_seen > REATTACH_S:
                continue
            last = hist.samples[-1].f.bbox
            score = _iou(last, bbox)
            if score <= 0:
                diag = math.hypot(last[2] - last[0], last[3] - last[1])
                dist = math.hypot((bbox[0] + bbox[2]) / 2 - (last[0] + last[2]) / 2, (bbox[1] + bbox[3]) / 2 - (last[1] + last[3]) / 2)
                score = 0.05 * (1 - dist / (2.5 * diag)) if dist < 2.5 * diag else 0.0   # a fall can move the box ~1-2 body heights
            if score > best_score:
                best, best_score = tid, score
        return best

    def _adopt_orphan(self, new_id: int, bbox, present: set, ts: float) -> tuple[TrackHistory, TrackFSM] | None:
        """ByteTrack often gives a person a NEW id after they go down (pose and box
        change abruptly). A new track that appears where an active track that is no
        longer detected last was (whether already parked as an orphan or only just
        missing) inherits its history and state, so one fall stays one incident."""
        cands = [("orphan", i, h, f) for i, (_, h, f) in enumerate(self.orphans)]
        # Any recently lost track may be re-identified, not only one with an active alert: the person's
        # standing reference and recent posture history are what the fall rules need after an id change.
        cands += [("track", tid, h, f) for tid, (h, f) in self.tracks.items()
                  if tid not in present and h.last_seen < ts
                  and (f.state in ACTIVE_STATES or ts - h.last_seen <= REATTACH_S)]
        best, best_score = None, 0.0
        for c in cands:
            last = c[2].samples[-1].f.bbox
            score = _iou(last, bbox)
            if score <= 0:
                cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
                ocx, ocy = (last[0] + last[2]) / 2, (last[1] + last[3]) / 2
                diag = math.hypot(last[2] - last[0], last[3] - last[1])
                dist = math.hypot(cx - ocx, cy - ocy)
                score = 0.05 * (1 - dist / diag) if dist < diag else 0.0
            if score <= 0:
                continue
            if c[3].state in ACTIVE_STATES:
                score += 0.3                    # an alert in progress outranks an idle track unless the idle one fits far better
            if score > best_score:
                best, best_score = c, score
        if best is None:
            return None
        kind, key, hist, fsm = best
        if kind == "orphan":
            self.orphans.pop(key)
        else:
            del self.tracks[key]
        log.info("camera %s: track %s inherits the fall state of lost track %s", self.camera_id, new_id, hist.track_id)
        hist.track_id = new_id
        return hist, fsm

    # -- operator actions / views --------------------------------------------------
    def resolve_track(self, track_id: int, ts: float | None = None) -> None:
        ts = ts or time.time()
        if track_id in self.tracks:
            self.tracks[track_id][1].resolve_externally(ts)
        for _, hist, fsm in self.orphans:
            if hist.track_id == track_id:
                fsm.resolve_externally(ts)

    def snapshot(self) -> list[dict]:
        """Live view for the overlay: every tracked person with their fall state."""
        out = []
        for tid, (hist, fsm) in self.tracks.items():
            cur = hist.samples[-1] if hist.samples else None
            if cur is None:
                continue
            out.append({"track_id": tid, "bbox": list(cur.f.bbox), "state": fsm.state,
                        "confidence": fsm.confidence if fsm.state != NORMAL else 0.0,
                        "posture": "lying" if cur.lying else ("upright" if cur.upright else "other"),
                        "incident_id": fsm.incident_key})
        return out

    def fsm_for(self, track_id: int) -> TrackFSM | None:
        if track_id in self.tracks:
            return self.tracks[track_id][1]
        for _, hist, fsm in self.orphans:
            if hist.track_id == track_id:
                return fsm
        return None
