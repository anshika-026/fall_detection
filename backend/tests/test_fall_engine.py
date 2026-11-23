"""Scenario tests for the rule-based fall engine on synthetic skeletons.

These prove the LOGIC (each activity yields the intended state sequence). They are
not accuracy measurements: see tests/eval_videos.py and docs/EVALUATION.md for
results on recorded video.
"""
import numpy as np
from synth import FRAME, GROUND, H, Timeline, lerp, lying_kw, pose, person, stand_kw

from falldet.fall_analysis.config import FallConfig, from_settings
from falldet.fall_analysis.engine import CameraFallEngine


def play(tl: Timeline, engine: CameraFallEngine | None = None, cfg: FallConfig | None = None):
    eng = engine or CameraFallEngine(1, cfg or FallConfig(auto_resolve_seconds=8.0))
    events = []
    for ts, people in tl.frames:
        events += eng.update(ts, people, FRAME)
    return eng, events


def kinds(events):
    return [e.kind for e in events]


def walking(tl, seconds, x0=300.0, speed=240.0):
    return tl.run(seconds, lambda lt: dict(cx=x0 + speed * lt, hip_y=GROUND - 0.5 * H, torso_deg=2.0))


def fall(tl, duration=0.5, x=600.0):
    """Upright -> lying in `duration` s (hip drops, torso rotates)."""
    return tl.run(duration, lambda lt: dict(cx=x, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.06 * H, lt / duration),
                                           torso_deg=lerp(2, 88, lt / duration), legs="straight"))


def test_walking_never_alerts():
    tl = Timeline()
    walking(tl, 12)
    _, ev = play(tl)
    assert ev == []


def test_sitting_down_on_chair_does_not_alert():
    tl = Timeline().hold(3, **stand_kw())
    tl.run(1.2, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.3 * H, lt / 1.2), torso_deg=5, legs="sit"))
    tl.hold(6, cx=600, hip_y=GROUND - 0.3 * H, torso_deg=5, legs="sit")
    _, ev = play(tl)
    assert ev == []


def test_standing_up_does_not_alert():
    tl = Timeline().hold(3, cx=600, hip_y=GROUND - 0.3 * H, torso_deg=5, legs="sit")
    tl.run(1.2, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.3 * H, GROUND - 0.5 * H, lt / 1.2), torso_deg=5, legs="straight"))
    tl.hold(3, **stand_kw())
    _, ev = play(tl)
    assert ev == []


def test_bending_over_does_not_alert():
    tl = Timeline().hold(3, **stand_kw())
    tl.run(1.0, lambda lt: dict(cx=600, hip_y=GROUND - 0.5 * H, torso_deg=lerp(2, 85, lt), legs="down"))
    tl.hold(4, cx=600, hip_y=GROUND - 0.5 * H, torso_deg=85, legs="down")
    tl.run(1.0, lambda lt: dict(cx=600, hip_y=GROUND - 0.5 * H, torso_deg=lerp(85, 2, lt), legs="down"))
    tl.hold(2, **stand_kw())
    _, ev = play(tl)
    assert ev == []


def test_kneeling_does_not_alert():
    tl = Timeline().hold(3, **stand_kw())
    tl.run(1.0, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.27 * H, lt), torso_deg=5, legs="kneel"))
    tl.hold(8, cx=600, hip_y=GROUND - 0.27 * H, torso_deg=5, legs="kneel")
    _, ev = play(tl)
    assert ev == []


def _slow_lie_down():
    tl = Timeline().hold(3, **stand_kw())
    tl.run(5.0, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.06 * H, lt / 5), torso_deg=lerp(2, 88, lt / 5)))
    tl.hold(15, **lying_kw())
    return tl


def test_slow_lying_down_is_ignored_when_the_floor_rule_is_switched_off():
    _, ev = play(_slow_lie_down(), cfg=FallConfig(auto_resolve_seconds=8.0, floor_lie_seconds=0))
    assert "confirmed" not in kinds(ev)             # only a rapid descent counts (the original design)


def test_person_who_stays_on_the_floor_is_alerted_even_without_a_seen_fall():
    # Slow lie-down, or first seen on the floor, or the tracker lost them mid-fall: still a person on the floor.
    _, ev = play(_slow_lie_down())
    assert kinds(ev) == ["possible", "confirmed"]
    assert ev[0].metrics["signal"] == "lying"


def test_person_first_seen_lying_on_the_floor_is_alerted():
    tl = Timeline().hold(12, **lying_kw())
    _, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed"]


def test_lying_down_then_getting_up_quickly_does_not_alert():
    tl = Timeline().hold(3, **stand_kw())
    tl.run(1.5, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.06 * H, lt / 1.5), torso_deg=lerp(2, 88, lt / 1.5)))
    tl.hold(2, **lying_kw())                          # on the floor for less than the 4 s the floor rule needs
    tl.run(1.5, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.06 * H, GROUND - 0.5 * H, lt / 1.5), torso_deg=lerp(88, 2, lt / 1.5)))
    tl.hold(3, **stand_kw())
    _, ev = play(tl)
    assert "confirmed" not in kinds(ev)


def test_sudden_fall_goes_possible_then_confirmed():
    tl = Timeline().hold(4, **stand_kw())
    fall(tl)
    tl.hold(6, **lying_kw())
    eng, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed"]
    assert ev[0].confidence > 0
    assert ev[1].ts - ev[0].ts >= 2.9          # confirmation waited ~confirm_seconds
    assert eng.snapshot()[0]["state"] == "CONFIRMED"


def test_remaining_on_ground_stays_confirmed_without_duplicates():
    tl = Timeline().hold(4, **stand_kw())
    fall(tl)
    tl.hold(60, **lying_kw())
    eng, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed"]
    assert eng.snapshot()[0]["state"] == "CONFIRMED"


def test_full_lifecycle_confirmed_recovered_resolved():
    tl = Timeline().hold(4, **stand_kw())
    fall(tl)
    tl.hold(5, **lying_kw())
    tl.run(2.0, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.06 * H, GROUND - 0.5 * H, lt / 2), torso_deg=lerp(88, 2, lt / 2)))
    tl.hold(12, **stand_kw())
    eng, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed", "recovered", "resolved"]
    assert eng.snapshot()[0]["state"] in ("RESOLVED", "NORMAL")


def test_getting_up_quickly_after_a_fall_is_dismissed():
    tl = Timeline().hold(4, **stand_kw())
    fall(tl)
    tl.hold(1.0, **lying_kw())
    tl.run(1.0, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.06 * H, GROUND - 0.5 * H, lt), torso_deg=lerp(88, 2, lt)))
    tl.hold(5, **stand_kw())
    _, ev = play(tl)
    assert kinds(ev) == ["possible", "dismissed"]


def test_burpee_like_exercise_never_confirms():
    tl = Timeline().hold(4, **stand_kw())
    for _ in range(3):
        fall(tl, 0.5)
        tl.hold(0.6, **lying_kw())
        tl.run(0.6, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.06 * H, GROUND - 0.5 * H, lt / 0.6), torso_deg=lerp(88, 2, lt / 0.6)))
        tl.hold(1.0, **stand_kw())
    _, ev = play(tl)
    assert "confirmed" not in kinds(ev)


def test_person_first_seen_lying_is_not_a_fall_when_the_floor_rule_is_off():
    tl = Timeline().hold(20, **lying_kw())
    _, ev = play(tl, cfg=FallConfig(auto_resolve_seconds=8.0, floor_lie_seconds=0))
    assert ev == []


def test_partly_visible_fall_needs_longer_but_confirms():
    tl = Timeline().hold(4, **stand_kw())
    tl.run(0.5, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.06 * H, lt / 0.5),
                                torso_deg=lerp(2, 88, lt / 0.5), hide_legs=True))
    tl.hold(8, hide_legs=True, **lying_kw())
    _, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed"]
    assert ev[1].ts - ev[0].ts >= 4.4          # 3 s x 1.5 partial factor
    assert ev[1].metrics["partial"] is True


def test_multiple_people_only_the_faller_alerts():
    tl = Timeline()
    for ts_i in range(int(4 / tl.dt)):
        tl.t += tl.dt
        tl.frames.append((tl.t, [person(1, tl.t, **stand_kw(400)), person(2, tl.t, cx=900 + 40 * tl.t, hip_y=GROUND - 0.5 * H, torso_deg=2)]))
    for i in range(int(0.5 / tl.dt)):
        tl.t += tl.dt
        k = (i + 1) * tl.dt / 0.5
        tl.frames.append((tl.t, [person(1, tl.t, cx=400, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.06 * H, k), torso_deg=lerp(2, 88, k)),
                                 person(2, tl.t, cx=1000, hip_y=GROUND - 0.5 * H, torso_deg=2)]))
    for i in range(int(6 / tl.dt)):
        tl.t += tl.dt
        tl.frames.append((tl.t, [person(1, tl.t, **lying_kw(400)), person(2, tl.t, cx=1000 + 20 * i * tl.dt, hip_y=GROUND - 0.5 * H, torso_deg=2)]))
    eng, ev = play(tl)
    assert {e.track_id for e in ev} == {1}
    assert kinds(ev) == ["possible", "confirmed"]
    states = {s["track_id"]: s["state"] for s in eng.snapshot()}
    assert states == {1: "CONFIRMED", 2: "NORMAL"}


def test_two_cameras_do_not_share_tracks_or_state():
    a, b = CameraFallEngine(1, FallConfig()), CameraFallEngine(2, FallConfig())
    tl_fall = Timeline().hold(4, **stand_kw())
    fall(tl_fall)
    tl_fall.hold(6, **lying_kw())
    tl_walk = Timeline()
    walking(tl_walk, len(tl_fall.frames) * tl_fall.dt)           # SAME track id (1) on the other camera
    evb = []
    eva = []
    for (ts, pa), (_, pb) in zip(tl_fall.frames, tl_walk.frames):
        eva += a.update(ts, pa, FRAME)
        evb += b.update(ts, pb, FRAME)
    assert kinds(eva) == ["possible", "confirmed"]
    assert evb == []
    assert b.snapshot()[0]["state"] == "NORMAL" and a.snapshot()[0]["state"] == "CONFIRMED"
    assert all(e.camera_id == 1 for e in eva)


def test_track_id_switch_while_lying_keeps_a_single_incident():
    tl = Timeline().hold(4, **stand_kw())
    fall(tl)
    tl.hold(2, **lying_kw())                      # id 1 lying, POSSIBLE
    for _ in range(3):                            # detector loses the person briefly
        tl.t += tl.dt
        tl.frames.append((tl.t, []))
    tl.run(8, lambda lt: lying_kw(), tid=7)       # re-appears as id 7, same place
    eng, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed"]
    assert ev[1].track_id == 7                    # the new id inherited the incident


def test_lost_person_while_confirmed_is_closed_as_lost():
    cfg = FallConfig(orphan_timeout=10.0)
    tl = Timeline().hold(4, **stand_kw())
    fall(tl)
    tl.hold(5, **lying_kw())
    for _ in range(int(14 / tl.dt)):
        tl.t += tl.dt
        tl.frames.append((tl.t, []))
    _, ev = play(tl, cfg=cfg)
    assert kinds(ev) == ["possible", "confirmed", "lost"]


def test_manual_resolve_while_still_down_does_not_realert():
    tl = Timeline().hold(4, **stand_kw())
    fall(tl)
    tl.hold(5, **lying_kw())
    eng, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed"]
    eng.resolve_track(1, ts=tl.t)
    more = Timeline()
    more.t = tl.t
    more.hold(30, **lying_kw())
    for ts, people in more.frames:
        ev += eng.update(ts, people, FRAME)
    assert kinds(ev) == ["possible", "confirmed"]
    assert eng.snapshot()[0]["state"] == "RESOLVED"


def test_second_fall_after_recovery_is_a_new_incident():
    tl = Timeline().hold(4, **stand_kw())
    fall(tl)
    tl.hold(5, **lying_kw())
    tl.run(2.0, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.06 * H, GROUND - 0.5 * H, lt / 2), torso_deg=lerp(88, 2, lt / 2)))
    tl.hold(12, **stand_kw())
    fall(tl)
    tl.hold(6, **lying_kw())
    _, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed", "recovered", "resolved", "possible", "confirmed"]


def test_disabled_engine_emits_nothing():
    tl = Timeline().hold(4, **stand_kw())
    fall(tl)
    tl.hold(6, **lying_kw())
    _, ev = play(tl, cfg=FallConfig(enabled=False))
    assert ev == []


def test_sensitivity_presets_scale_thresholds():
    lo, hi = from_settings({}, "low"), from_settings({}, "high")
    assert lo.min_drop > FallConfig().min_drop > hi.min_drop


def test_bad_settings_values_keep_defaults():
    cfg = from_settings({"confirm_seconds": "abc", "bogus": 1, "min_drop": "0.4"})
    assert cfg.confirm_seconds == FallConfig().confirm_seconds and cfg.min_drop == 0.4


def test_fall_is_detected_when_legs_are_never_visible():
    """A camera that never sees the ankles: the standing height comes from the torso length."""
    tl = Timeline().hold(4, hide_legs=True, **stand_kw())
    tl.run(0.5, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.06 * H, lt / 0.5),
                                torso_deg=lerp(2, 88, lt / 0.5), hide_legs=True))
    tl.hold(8, hide_legs=True, **lying_kw())
    _, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed"]


def test_seated_person_with_hidden_legs_does_not_alert_and_is_not_a_short_reference():
    tl = Timeline().hold(3, hide_legs=True, **stand_kw())
    tl.run(1.2, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.3 * H, lt / 1.2), torso_deg=5, legs="sit", hide_legs=True))
    tl.hold(8, cx=600, hip_y=GROUND - 0.3 * H, torso_deg=5, legs="sit", hide_legs=True)
    eng, ev = play(tl)
    assert ev == []
    hist = eng.tracks[1][0]
    assert abs(hist.stand_h - H) < 0.15 * H      # still the standing height, not the seated one


def test_wide_box_alone_counts_as_lying_when_keypoints_are_too_few_to_vote():
    from falldet.fall_analysis.engine import classify
    from falldet.pose_estimation.keypoints import extract_features

    kp = np.zeros((17, 3))                                  # nothing confident
    f = extract_features(0.0, (100, 400, 420, 520), kp, FRAME)          # 320 x 120 box: aspect 2.7
    assert classify(f, 300.0, FallConfig())[0] is True
    f2 = extract_features(0.0, (100, 300, 220, 560), kp, FRAME)         # tall box: unknown, not "lying"
    assert classify(f2, 300.0, FallConfig())[0] is not True


def test_legs_hidden_does_not_make_a_standing_person_look_collapsed():
    from falldet.fall_analysis.engine import classify
    from falldet.pose_estimation.keypoints import extract_features
    from synth import pose

    kp, bbox = pose(600, GROUND - 0.5 * H, 2, hide_legs=True)
    f = extract_features(0.0, bbox, kp, FRAME)
    lying, upright, votes, n, ext = classify(f, H, FallConfig())
    assert ext is None and lying is False and upright is True


# --- diagnosis-driven additions (docs/FALL_DIAGNOSIS.md) --------------------------------------------------

def _seated(tl, seconds):
    return tl.hold(seconds, cx=600.0, hip_y=GROUND - 0.28 * H, torso_deg=5.0, legs="sit")


def test_lying_person_without_tracker_id_is_still_analysed():
    """ByteTrack gives no id right after an abrupt fall; the engine must not drop that person."""
    tl = Timeline().hold(4, **stand_kw())
    fall(tl)                                       # falls as id 1 ...
    tl.run(8, lambda lt: lying_kw(), tid=None)     # ... then only id-less detections
    eng, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed"]
    assert ev[0].track_id == 1                     # matched to the person who was just standing there


def test_new_tracker_id_at_fall_start_inherits_the_standing_reference():
    tl = Timeline().hold(4, **stand_kw())
    tl.t += 2 * tl.dt
    tl.frames += [(tl.t - tl.dt, []), (tl.t, [])]  # tracker loses the person for 2 frames
    tl.run(0.5, lambda lt: dict(cx=600.0, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.06 * H, lt / 0.5),
                                torso_deg=lerp(2, 88, lt / 0.5), legs="straight"), tid=9)
    tl.run(6, lambda lt: lying_kw(), tid=9)
    eng, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed"]


def test_fall_from_a_chair_is_detected_by_the_head_drop():
    tl = _seated(Timeline(), 4)
    tl.run(0.6, lambda lt: dict(cx=600.0, hip_y=lerp(GROUND - 0.28 * H, GROUND - 0.06 * H, lt / 0.6),
                                torso_deg=lerp(5, 88, lt / 0.6), legs="straight"))
    tl.hold(6, **lying_kw())
    eng, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed"]
    assert ev[0].metrics["signal"] == "head"       # the hips alone dropped less than min_drop


def test_slowly_lowering_oneself_from_a_chair_to_the_floor_does_not_alert_when_the_floor_rule_is_off():
    tl = _seated(Timeline(), 4)
    tl.run(4.0, lambda lt: dict(cx=600.0, hip_y=lerp(GROUND - 0.28 * H, GROUND - 0.06 * H, lt / 4.0),
                                torso_deg=lerp(5, 88, lt / 4.0), legs="straight"))
    tl.hold(8, **lying_kw())
    _, ev = play(tl, cfg=FallConfig(auto_resolve_seconds=8.0, floor_lie_seconds=0))
    assert kinds(ev) == []


def test_untracked_detection_far_from_any_recent_person_is_a_new_person_not_a_fall_when_the_floor_rule_is_off():
    tl = Timeline().hold(4, **stand_kw(cx=200.0))
    tl.t += 10 * tl.dt                              # nobody for 2 s ... then, 3 s later, someone lying elsewhere
    tl.run(8, lambda lt: lying_kw(cx=1100.0), tid=None)
    _, ev = play(tl, cfg=FallConfig(auto_resolve_seconds=8.0, floor_lie_seconds=0))
    assert kinds(ev) == []                          # never seen upright => not a fall


def test_weak_duplicate_untracked_box_does_not_steal_the_incident():
    """Two id-less boxes in one frame: the confident one is the person who fell; the weak one must not
    become the track that a later tracker id is matched to."""
    tl = Timeline().hold(4, **stand_kw())
    fall(tl)
    tl.hold(1, **lying_kw())                                       # id 1 POSSIBLE
    for _ in range(2):
        tl.t += tl.dt
        main = person(None, tl.t, **lying_kw())
        weak = person(None, tl.t, **lying_kw(cx=640.0))
        weak["confidence"] = 0.45
        tl.frames.append((tl.t, [weak, main]))
    tl.run(6, lambda lt: lying_kw(), tid=5)
    eng, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed"]


# ---- GMDCSA-24 tuning-set fixes (see docs/FALL_DIAGNOSIS.md, stage 3)
from types import SimpleNamespace  # noqa: E402

from falldet.fall_analysis.engine import classify  # noqa: E402


def _shape(aspect, angle):
    """Just the fields classify() reads: a person with the whole body NOT visible (no extent vote)."""
    return SimpleNamespace(head_y=None, ankle_y=None, extent=0.0, torso_angle=angle, aspect=aspect)


def test_a_clearly_wide_box_counts_as_lying_even_when_the_torso_angle_disagrees():
    # A backward fall seen from the front: the box is 1.4x wider than tall but the torso angle reads only 30 degrees.
    cfg = FallConfig()
    assert classify(_shape(1.4, 30.0), None, cfg)[0] is True
    assert classify(_shape(1.4, 30.0), None, FallConfig(lying_aspect_override=0))[0] is False     # the original 2-of-3 behaviour
    assert classify(_shape(0.4, 5.0), None, cfg)[0] is False                                      # standing is untouched
    assert classify(_shape(1.1, 30.0), None, cfg)[0] is False                                     # a box only slightly wider than tall is not enough


def test_without_a_standing_height_the_body_length_seen_so_far_is_the_reference():
    eng, _ = play(Timeline().hold(3, **stand_kw()))
    hist, fsm = next(iter(eng.tracks.values()))
    hist.stand_h = None                                           # as for someone only ever seen sitting on the floor
    assert fsm._ref_height(hist) == hist.body_length() and hist.body_length() > 0
    eng.cfg.descent_ref_fallback = False
    assert fsm._ref_height(hist) is None                          # the original behaviour: no reference, so no descent can be judged


def test_floor_rule_survives_a_brief_misclassification_flicker():
    tl = Timeline().hold(12, **lying_kw())
    _, ev = play(tl)
    assert kinds(ev) == ["possible", "confirmed"]


# ---- floor rule: missing keypoints and tracking gaps are never lying evidence
def _floor_hist(times, lying_of):
    from types import SimpleNamespace as NS

    from falldet.tracking.track_history import Sample, TrackHistory
    h = TrackHistory(1, 30.0)
    for t in times:
        f = NS(ts=t, bbox=(100, 300, 500, 380), w=400, h=80, cy=340, torso_angle=85.0, aspect=5.0)
        h.add(Sample(f, 340.0, lying_of(t), False, 2, 2, None))
    return h


def test_floor_rule_does_not_count_missing_keypoints_or_unseen_gaps_as_lying():
    from falldet.fall_analysis.engine import TrackFSM
    fsm = TrackFSM(FallConfig())
    dense = [round(i * 0.2, 2) for i in range(26)]                                   # 5 s, every 0.2 s
    assert fsm._floor_lie(_floor_hist(dense, lambda t: True), 5.0)["signal"] == "lying"
    assert fsm._floor_lie(_floor_hist(dense, lambda t: False if t == 2.0 else True), 5.0)            # one flickering frame is tolerated
    assert fsm._floor_lie(_floor_hist(dense, lambda t: None if int(round(t * 5)) % 10 < 3 else True), 5.0) is None   # 30% 'too few keypoints' is NOT lying
    gap = [1.0, 1.2] + [4.2, 4.4, 4.6, 4.8, 5.0]                                    # lying, then NOT SEEN for 3 s, then lying again
    assert fsm._floor_lie(_floor_hist(gap, lambda t: True), 5.0) is None
    assert TrackFSM(FallConfig(floor_lie_max_gap_s=1000))._floor_lie(_floor_hist(gap, lambda t: True), 5.0)   # the original rule had no such check
