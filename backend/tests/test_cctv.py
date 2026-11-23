"""Tests for the recording utility and the validation metadata/scoring.

The recorder tests use a generated local video FILE as the "camera": they check segmenting, reconnect after the
source ends, no-overwrite, sidecars, playable output and credential scrubbing. They are not a test against a real
RTSP camera (none was available) and say nothing about detection."""
import json
import logging
import threading
from fractions import Fraction

import av
import numpy as np
import pytest

from tools import cctv_meta, cctv_record


def make_video(path, seconds=4, fps=10, size=(160, 120), gop=10):
    out = av.open(str(path), "w", format="matroska")
    vs = out.add_stream("libx264", rate=fps)
    vs.width, vs.height, vs.pix_fmt = size[0], size[1], "yuv420p"
    vs.options = {"g": str(gop), "preset": "ultrafast"}
    for i in range(seconds * fps):
        img = np.full((size[1], size[0], 3), (i * 5) % 255, dtype=np.uint8)
        f = av.VideoFrame.from_ndarray(img, format="bgr24")
        f.pts, f.time_base = i, Fraction(1, fps)
        for p in vs.encode(f):
            out.mux(p)
    for p in vs.encode(None):
        out.mux(p)
    out.close()


def count_frames(path):
    with av.open(str(path)) as c:
        return sum(1 for _ in c.decode(video=0))


# ------------------------------------------------------------------ credentials / paths
def test_scrub_masks_password_and_raw_url():
    url = "rtsp://admin:s3cret@10.0.0.5:554/stream1"
    out = cctv_record.scrub(f"Error opening {url}: timeout; also rtsp://u:pw@h/x", url)
    assert "s3cret" not in out and "pw@" not in out and "<url>" in out


def test_unique_path_never_overwrites(tmp_path):
    a = cctv_record.unique_path(tmp_path, "cam_x", ".mkv")
    a.write_bytes(b"1")
    b = cctv_record.unique_path(tmp_path, "cam_x", ".mkv")
    assert a != b and not b.exists() and "_dup1" in b.name


def test_config_file_with_a_url_is_rejected(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"cameras": [{"id": "a", "url": "rtsp://u:p@h/x"}]}))
    args = type("A", (), {"camera": None, "db_camera": None, "config": str(cfg)})()
    with pytest.raises(SystemExit, match="must not contain a URL"):
        cctv_record.resolve_cameras(args)


def test_camera_url_comes_from_the_environment_and_bad_ids_are_rejected(monkeypatch):
    monkeypatch.setenv("CCTV_TEST_URL", "rtsp://u:p@h/x")
    ok = type("A", (), {"camera": ["office-1=CCTV_TEST_URL"], "db_camera": None, "config": None})()
    assert cctv_record.resolve_cameras(ok) == {"office-1": "rtsp://u:p@h/x"}
    bad = type("A", (), {"camera": ["../evil=CCTV_TEST_URL"], "db_camera": None, "config": None})()
    with pytest.raises(SystemExit):
        cctv_record.resolve_cameras(bad)
    missing = type("A", (), {"camera": ["a=NO_SUCH_VAR_X"], "db_camera": None, "config": None})()
    with pytest.raises(SystemExit, match="gave no URL"):
        cctv_record.resolve_cameras(missing)


# ------------------------------------------------------------------ recorder on a file source
def run_recorder(url, out, seconds, segment_s=300.0, mode=None):
    stop = threading.Event()
    r = cctv_record.CameraRecorder("test-cam", url, out, seconds, segment_s, mode or {"reencode": False}, stop, 0.0)
    r.start()
    r.join(timeout=seconds + 20)
    stop.set()
    return r


def test_recorder_writes_playable_segment_with_sidecar_and_reconnects_after_source_ends(tmp_path):
    src = tmp_path / "src.mkv"
    make_video(src, seconds=3)
    r = run_recorder(str(src), tmp_path / "rec", seconds=5)
    files = sorted((tmp_path / "rec" / "test-cam").glob("*.mkv"))
    assert len(files) >= 2, "source ended (a dropped stream): the recorder must reconnect and start a new segment"
    assert r.reconnects >= 1
    for f in files:
        assert count_frames(f) > 0                                   # everything recorded so far is playable
        side = json.loads(f.with_suffix(".json").read_text())
        assert side["camera_id"] == "test-cam" and side["ended_by"] in ("disconnect", "duration", "rotate", "stop")
        assert "rtsp" not in json.dumps(side) and str(src) not in json.dumps(side)


def test_recorder_rotates_segments_at_keyframes(tmp_path):
    src = tmp_path / "src.mkv"
    make_video(src, seconds=4, fps=10, gop=10)                      # 4 keyframes
    run_recorder(str(src), tmp_path / "rec", seconds=2, segment_s=0.0)
    files = sorted((tmp_path / "rec" / "test-cam").glob("*.mkv"))
    assert len(files) >= 3
    assert sum(count_frames(f) for f in files[:4]) > 0


def test_recorder_does_not_overwrite_existing_recordings(tmp_path):
    src = tmp_path / "src.mkv"
    make_video(src, seconds=2)
    out = tmp_path / "rec"
    (out / "test-cam").mkdir(parents=True)
    before = {}
    run_recorder(str(src), out, seconds=1)
    for f in (out / "test-cam").glob("*.mkv"):
        before[f.name] = f.stat().st_size
    run_recorder(str(src), out, seconds=1)
    for name, size in before.items():
        assert (out / "test-cam" / name).stat().st_size == size


def test_recorder_reencode_mode_scales_and_limits_fps(tmp_path):
    src = tmp_path / "src.mkv"
    make_video(src, seconds=3, fps=10, size=(160, 120))
    run_recorder(str(src), tmp_path / "rec", seconds=1.5, mode={"reencode": True, "width": 80, "height": 60, "fps": 5})
    files = sorted((tmp_path / "rec" / "test-cam").glob("*.mkv"))
    assert files
    with av.open(str(files[0])) as c:
        v = c.streams.video[0]
        assert (v.codec_context.width, v.codec_context.height) == (80, 60)
    assert count_frames(files[0]) > 0


def test_unreachable_source_does_not_crash_and_never_logs_the_password(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="cctv_record")
    run_recorder("rtsp://admin:topsecret@127.0.0.1:9/none", tmp_path / "rec", seconds=1)
    assert "topsecret" not in caplog.text


# ------------------------------------------------------------------ metadata / scoring
def good_fall(**kw):
    m = {"schema_version": 1, "camera_id": "c", "recording_start": "2026-12-01T10:00:00Z", "recording_end": "2026-12-01T10:01:00Z",
         "scenario": "fall_standing", "expected_event": "fall", "event_time_s": 30.0, "event_time_tolerance_s": 2.0}
    m.update(kw)
    return m


def test_metadata_validation_rejects_missing_or_inconsistent_ground_truth():
    cctv_meta.validate(good_fall(), "fall_standing")
    for bad in (good_fall(event_time_s=None), good_fall(scenario="nope"), good_fall(expected_event="none"),
                good_fall(recording_end="2026-12-01T09:00:00Z"), good_fall(schema_version=2), good_fall(camera_id="")):
        with pytest.raises(cctv_meta.MetaError):
            cctv_meta.validate(bad)
    with pytest.raises(cctv_meta.MetaError, match="folder"):
        cctv_meta.validate(good_fall(), "fall_forward")


def test_a_clip_without_a_metadata_file_is_refused(tmp_path):
    clip = tmp_path / "x.mkv"
    clip.write_bytes(b"")
    with pytest.raises(cctv_meta.MetaError, match="no metadata"):
        cctv_meta.load_clip(clip)


def test_new_template_does_not_validate_until_a_person_fills_it_in(tmp_path):
    clip = tmp_path / "fall_standing" / "a.mkv"
    clip.parent.mkdir()
    clip.write_bytes(b"")
    p = cctv_meta._new(clip, "fall_standing", "office-1", "ab")
    with pytest.raises(cctv_meta.MetaError):
        cctv_meta.load_clip(clip, "fall_standing")
    with pytest.raises(SystemExit):
        cctv_meta._new(clip, "fall_standing", "office-1", "ab")       # never overwrites labels
    assert p.name == "a.meta.json"


def test_scoring_fall_detected_with_confirmation_latency():
    s = cctv_meta.score_clip(good_fall(), [("possible", 31.0), ("confirmed", 34.2)])
    assert s.detected_possible and s.detected_confirmed and not s.missed
    assert s.confirm_latency_s == pytest.approx(4.2) and s.false_possible == 0 and s.false_confirmed == 0


def test_scoring_missed_fall_and_events_outside_the_window_are_false_alerts():
    assert cctv_meta.score_clip(good_fall(), []).missed
    s = cctv_meta.score_clip(good_fall(), [("possible", 5.0), ("confirmed", 9.0)])      # long before the staged fall
    assert s.missed and s.false_possible == 1 and s.false_confirmed == 1
    late = cctv_meta.score_clip(good_fall(), [("possible", 30 + 2 + 10 + 1)])           # after the window
    assert late.missed and late.false_possible == 1


def test_scoring_normal_clip_counts_every_alert_as_false():
    meta = good_fall(scenario="sitting_standing", expected_event="none")
    meta.pop("event_time_s")
    s = cctv_meta.score_clip(meta, [("possible", 3.0), ("confirmed", 7.0), ("possible", 20.0)])
    assert (s.false_possible, s.false_confirmed, s.missed) == (2, 1, False)


def test_scoring_possible_only_is_not_a_confirmation():
    s = cctv_meta.score_clip(good_fall(), [("possible", 31.0), ("dismissed", 33.0)])
    assert s.detected_possible and not s.detected_confirmed and s.confirm_latency_s is None


# ------------------------------------------------------------------ validation runner (synthetic pose, no model)
def _prime_cache(clip, cache_root, timeline, conf=0.4, fps=5.0, weights="yolov8n-pose.pt", imgsz=640):
    """Writes the pose-cache file the runner would have built, from a synthetic skeleton timeline (TEST INPUT)."""
    import pickle

    from tools import cctv_validate as cv
    from synth import FRAME

    folder = cache_root / f"{cv.Path(weights).stem}_conf{conf}_fps{fps}_sz{imgsz}"
    folder.mkdir(parents=True, exist_ok=True)
    frames = [{"i": i, "ts": ts, "people": people} for i, (ts, people) in enumerate(timeline.frames)]
    d = {"clip": clip.name, "fingerprint": cv.fingerprint(clip), "fps": fps, "conf": conf, "imgsz": imgsz, "frame_wh": FRAME, "frames": frames,
         "infer_ms": [50.0] * len(frames), "source_fps": 30.0, "duration_s": frames[-1]["ts"]}
    (folder / f"{cv.clip_id(clip)}.pkl").write_bytes(pickle.dumps(d))



def _make_footage(tmp_path):
    """footage/ with a staged-fall clip, a walking clip and an UNLABELLED clip; returns (root, cache_root)."""
    from synth import GROUND, H, Timeline, lerp, lying_kw, stand_kw

    root, cache = tmp_path / "footage", tmp_path / "cache"
    for sc in ("fall_standing", "normal_office_activity"):
        (root / sc).mkdir(parents=True)
    def clip(sc, name, tl, meta):
        c = root / sc / name
        c.write_bytes(b"x" * 100)                                      # content irrelevant: the cache is primed
        if meta is not None:
            (root / sc / (c.stem + ".meta.json")).write_text(json.dumps(meta))
        _prime_cache(c, cache, tl)
        return c
    fall = Timeline().hold(4, **stand_kw())
    fall.run(0.5, lambda lt: dict(cx=600.0, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.06 * H, lt / 0.5), torso_deg=lerp(2, 88, lt / 0.5), legs="straight"))
    fall.hold(8, **lying_kw())
    walk = Timeline().run(20, lambda lt: dict(cx=300.0 + 40 * lt, hip_y=GROUND - 0.5 * H, torso_deg=2.0))
    base = {"schema_version": 1, "camera_id": "cam", "recording_start": "2026-12-01T10:00:00Z", "recording_end": "2026-12-01T10:01:00Z"}
    clip("fall_standing", "f1.mkv", fall, {**base, "scenario": "fall_standing", "expected_event": "fall", "event_time_s": 4.5, "event_time_tolerance_s": 1.0})
    clip("normal_office_activity", "n1.mkv", walk, {**base, "scenario": "normal_office_activity", "expected_event": "none"})
    clip("fall_standing", "unlabelled.mkv", fall, None)
    return root, cache


def _run_main(monkeypatch, root, cache, out, *extra):
    from tools import cctv_validate as cv

    monkeypatch.setattr(cv.sys, "argv", ["x", "--footage", str(root), "--cache", str(cache), "--out", str(out), "--configs", "default", *extra])
    cv.main()
    return json.loads(out.read_text())


def test_runner_scores_against_human_labels_uses_real_subsequent_frames_and_skips_unlabelled(tmp_path, monkeypatch):
    root, cache = _make_footage(tmp_path)
    rep = _run_main(monkeypatch, root, cache, tmp_path / "res" / "r.json")
    assert rep["clips_scored"] == 2 and len(rep["skipped"]) == 1 and "unlabelled.mkv" in rep["skipped"][0]["clip"]
    assert "no metadata" in rep["skipped"][0]["reason"]
    c = rep["configs"][0]
    s = c["summary"]
    assert (s["fall_clips"], s["falls_possible"], s["falls_confirmed"], s["falls_missed"]) == (1, 1, 1, 0)
    fall = next(r for r in c["clips"] if r["expected"] == "fall")
    assert [k for k, _ in fall["events"]] == ["possible", "confirmed"]
    assert fall["confirm_latency_s"] >= 3.0                           # the 3 s window was waited out on real frames
    assert s["false_possible_total"] == 0 and s["false_confirmed_total"] == 0 and s["normal_clips"] == 1
    assert c["performance"]["mean_inference_ms"] == 50.0 and c["performance"]["single_stream_max_fps"] > 0


def test_runner_confirmation_needs_the_footage_to_continue(tmp_path, monkeypatch):
    """A clip that ends 1 s after the fall can reach POSSIBLE but never CONFIRMED: nothing is extended or frozen."""
    from synth import GROUND, H, Timeline, lerp, lying_kw, stand_kw

    root, cache = _make_footage(tmp_path)
    short = Timeline().hold(4, **stand_kw())
    short.run(0.5, lambda lt: dict(cx=600.0, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.06 * H, lt / 0.5), torso_deg=lerp(2, 88, lt / 0.5), legs="straight"))
    short.hold(1, **lying_kw())
    _prime_cache(root / "fall_standing" / "f1.mkv", cache, short)
    rep = _run_main(monkeypatch, root, cache, tmp_path / "res" / "r2.json")
    fall = next(r for r in rep["configs"][0]["clips"] if r["expected"] == "fall")
    assert fall["detected_possible"] and not fall["detected_confirmed"]


def test_runner_refuses_to_overwrite_a_results_file_and_to_run_with_no_labelled_clips(tmp_path, monkeypatch):
    root, cache = _make_footage(tmp_path)
    out = tmp_path / "res" / "r.json"
    _run_main(monkeypatch, root, cache, out)
    with pytest.raises(SystemExit, match="not overwriting"):
        _run_main(monkeypatch, root, cache, out)
    empty = tmp_path / "empty"
    (empty / "fall_standing").mkdir(parents=True)
    with pytest.raises(SystemExit, match="nothing to validate"):
        _run_main(monkeypatch, empty, cache, tmp_path / "res" / "r3.json")


def test_config_parsing_separates_detector_conf_from_engine_overrides():
    from tools import cctv_validate as cv

    assert cv.parse_config("strict:conf=0.5,min_person_conf=0.5,confirm_seconds=3") == ("strict", {"conf": 0.5, "overrides": {"min_person_conf": 0.5, "confirm_seconds": 3.0}})
    assert cv.DEFAULT_CONFIGS["default"]["conf"] == 0.4 and cv.DEFAULT_CONFIGS["default"]["overrides"] == {}
