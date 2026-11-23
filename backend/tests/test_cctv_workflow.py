"""Tests for the first-test workflow tools (verify a recording, cut a clip) and the tuning/independent split.
Sources are generated files, not cameras: see docs/REAL_CCTV_VALIDATION.md for what that does and does not prove."""
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from test_cctv import count_frames, make_video, run_recorder
from tools import cctv_clip, cctv_meta, cctv_validate

BACKEND = Path(__file__).resolve().parent.parent


def record(tmp_path, seconds=3, **kw):
    src = tmp_path / "src.mkv"
    make_video(src, seconds=seconds, size=(320, 240))
    run_recorder(str(src), tmp_path / "rec", seconds=2.5, **kw)
    return src, tmp_path / "rec" / "test-cam"


def verify(folder, *extra, env=None):
    e = {**os.environ, **(env or {})}
    return subprocess.run([sys.executable, "-m", "tools.cctv_verify_recording", str(folder), *extra], cwd=BACKEND, env=e, capture_output=True, text=True, timeout=120)


def test_verifier_passes_a_good_file_recording_but_says_it_is_not_a_camera(tmp_path):
    _, folder = record(tmp_path)
    r = verify(folder)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout and "NOT a real-camera recording" in r.stdout
    assert "not real-camera evidence" in r.stdout


def test_verifier_with_require_rtsp_fails_a_file_recording(tmp_path):
    _, folder = record(tmp_path)
    r = verify(folder, "--require-rtsp")
    assert r.returncode == 1 and "[FAIL] source" in r.stdout


def test_verifier_detects_missing_sidecar_and_truncated_video(tmp_path):
    _, folder = record(tmp_path)
    mkvs = sorted(folder.glob("*.mkv"))
    mkvs[0].with_suffix(".json").unlink()
    r = verify(folder)
    assert r.returncode == 1 and "sidecar" in r.stdout and "missing" in r.stdout
    bad = folder / "test-cam_20260101T000000Z_99.mkv"
    bad.write_bytes(b"not a video")
    bad.with_suffix(".json").write_text(json.dumps({"camera_id": "x"}))
    r2 = verify(folder)
    assert r2.returncode == 1 and "[FAIL]" in r2.stdout


def test_verifier_finds_a_leaked_password_in_a_sidecar_or_a_video(tmp_path):
    _, folder = record(tmp_path)
    side = sorted(folder.glob("*.json"))[0]
    d = json.loads(side.read_text())
    d["note"] = "opened rtsp://admin:hunter2pw@10.0.0.5/stream1"
    side.write_text(json.dumps(d))
    r = verify(folder, "--camera-env", "CCTV_VER_URL", env={"CCTV_VER_URL": "rtsp://admin:hunter2pw@10.0.0.5/stream1"})
    assert r.returncode == 1 and "[FAIL] credentials" in r.stdout and "hunter2pw" not in r.stdout
    d.pop("note")
    side.write_text(json.dumps(d))
    mkv = sorted(folder.glob("*.mkv"))[0]
    mkv.write_bytes(mkv.read_bytes() + b"hunter2pw")                  # a password inside the video bytes
    r2 = verify(folder, "--camera-env", "CCTV_VER_URL", env={"CCTV_VER_URL": "rtsp://admin:hunter2pw@10.0.0.5/stream1"})
    assert "[FAIL] credentials" in r2.stdout


def test_verifier_duration_checks_apply_to_rtsp_sidecars_but_not_to_file_sources(tmp_path):
    _, folder = record(tmp_path)
    r = verify(folder, "--expect-seconds", "600")                      # file source: wall-clock checks do not apply
    assert r.returncode == 0 and "not applicable" in r.stdout and "not checked" in r.stdout
    for side in folder.glob("*.json"):                                 # pretend the same files came from an RTSP camera
        d = json.loads(side.read_text())
        d["source_kind"] = "rtsp"
        d["duration_s"] = d["media_span_s"]                            # a healthy camera: footage length == time recorded
        side.write_text(json.dumps(d))
    assert verify(folder).returncode == 0
    short = verify(folder, "--expect-seconds", "600")
    assert short.returncode == 1 and "[FAIL] total recorded" in short.stdout
    side = sorted(folder.glob("*.json"))[0]
    d = json.loads(side.read_text())
    d["duration_s"] = d["media_span_s"] + 30                           # recorded 30 s longer than the footage it produced: stalls
    side.write_text(json.dumps(d))
    stall = verify(folder)
    assert stall.returncode == 1 and "[FAIL]" in stall.stdout and "wall-clock" in stall.stdout


def test_recorder_output_is_clean_of_credentials_when_the_source_is_a_file(tmp_path):
    _, folder = record(tmp_path)
    r = verify(folder, "--camera-env", "CCTV_VER_URL", env={"CCTV_VER_URL": "rtsp://admin:hunter2pw@10.0.0.5/stream1"})
    assert r.returncode == 0 and "none found" in r.stdout


def test_clip_cut_keeps_quality_starts_on_a_keyframe_and_computes_event_time(tmp_path, capsys):
    src = tmp_path / "rec.mkv"
    make_video(src, seconds=10, fps=10, size=(160, 120), gop=10)
    out = tmp_path / "clip.mkv"
    info = cctv_clip.cut(src, 3.5, 8.0, out)
    assert info["actual_start_s"] == pytest.approx(3.0, abs=0.15)        # last keyframe at or before 3.5
    n = count_frames(out)
    assert 40 <= n <= 60 and out.exists()
    with pytest.raises(SystemExit, match="not overwriting"):
        cctv_clip.cut(src, 3.5, 8.0, out)
    with pytest.raises(SystemExit, match="no video"):
        cctv_clip.cut(src, 50, 60, tmp_path / "none.mkv")
    assert not (tmp_path / "none.mkv").exists()


def test_clip_cli_prints_event_time_relative_to_the_clip_and_writes_a_prefill_sidecar(tmp_path):
    folder = tmp_path / "rec"
    src = tmp_path / "s.mkv"
    make_video(src, seconds=6, size=(320, 240))
    run_recorder(str(src), folder, seconds=2.5)
    rec = sorted((folder / "test-cam").glob("*.mkv"))[0]
    out = tmp_path / "independent" / "fall_standing" / "c.mkv"
    r = subprocess.run([sys.executable, "-m", "tools.cctv_clip", str(rec), "--start", "0.5", "--end", "2.5", "--event-at", "1.5", "--out", str(out)],
                       cwd=BACKEND, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "event_time_s for the metadata" in r.stdout
    side = json.loads(out.with_suffix(".json").read_text())
    assert side["segment_start_utc"].endswith("Z") and side["source_kind"] == "file_test"
    p = cctv_meta._new(out, "fall_standing", "office-1", "ab")             # pre-filled from the sidecar (facts, not labels)
    meta = json.loads(p.read_text())
    assert meta["recording_start"] == side["segment_start_utc"] and meta["event_time_s"] is None


def test_new_label_template_for_a_missing_clip_is_a_clean_error(tmp_path):
    with pytest.raises(SystemExit, match="does not exist"):
        cctv_meta._new(tmp_path / "nope.mkv", "fall_standing", "c", "")


def test_role_detection_and_the_same_footage_cannot_be_both_tuning_and_independent(tmp_path):
    tuning, indep = tmp_path / "validation" / "tuning", tmp_path / "validation" / "independent"
    for root in (tuning, indep):
        (root / "normal_office_activity").mkdir(parents=True)
    assert cctv_validate.role_of(tuning) == "tuning" and cctv_validate.role_of(indep) == "independent"
    assert cctv_validate.role_of(tmp_path) == "unspecified"
    (tuning / "normal_office_activity" / "a.mkv").write_bytes(b"A" * 5000)
    (indep / "normal_office_activity" / "copy_of_a.mkv").write_bytes(b"A" * 5000)      # same footage, other name
    (indep / "normal_office_activity" / "other.mkv").write_bytes(b"B" * 5000)
    assert cctv_validate.shared_between_roles(indep) == [str(Path("normal_office_activity") / "copy_of_a.mkv")]
    assert cctv_validate.shared_between_roles(tuning) == [str(Path("normal_office_activity") / "a.mkv")]


def _split_clip(root, name, content, scenario="normal_office_activity"):
    d = root / scenario
    d.mkdir(parents=True, exist_ok=True)
    c = d / name
    c.write_bytes(content)
    meta = {"schema_version": 1, "camera_id": "cam", "recording_start": "2026-12-01T10:00:00Z", "recording_end": "2026-12-01T10:01:00Z",
            "scenario": scenario, "expected_event": "none"}
    (d / (c.stem + ".meta.json")).write_text(json.dumps(meta))
    return c


def test_runner_refuses_when_the_same_footage_is_in_both_splits(tmp_path, monkeypatch):
    from test_cctv import _run_main

    v = tmp_path / "validation"
    _split_clip(v / "tuning", "a.mkv", b"A" * 5000)
    _split_clip(v / "independent", "same_footage_other_name.mkv", b"A" * 5000)
    with pytest.raises(SystemExit, match="cannot also be independent"):
        _run_main(monkeypatch, v / "independent", tmp_path / "cache", tmp_path / "res" / "x.json")


def test_tuning_results_are_labelled_as_not_independent(tmp_path, monkeypatch):
    from synth import GROUND, H, Timeline
    from test_cctv import _prime_cache, _run_main

    v = tmp_path / "validation"
    c = _split_clip(v / "tuning", "t.mkv", b"T" * 5000)
    _prime_cache(c, tmp_path / "cache", Timeline().run(10, lambda lt: dict(cx=300.0 + 20 * lt, hip_y=GROUND - 0.5 * H, torso_deg=2.0)))
    rep = _run_main(monkeypatch, v / "tuning", tmp_path / "cache", tmp_path / "res" / "t.json")
    assert rep["footage_role"] == "tuning"
    assert "NOT independent validation" in cctv_validate.to_markdown(rep)
    c2 = _split_clip(v / "independent", "i.mkv", b"I" * 5000)
    _prime_cache(c2, tmp_path / "cache", Timeline().run(10, lambda lt: dict(cx=300.0 + 20 * lt, hip_y=GROUND - 0.5 * H, torso_deg=2.0)))
    rep2 = _run_main(monkeypatch, v / "independent", tmp_path / "cache", tmp_path / "res" / "i.json")
    assert rep2["footage_role"] == "independent"
    assert "NOT independent" not in cctv_validate.to_markdown(rep2)


def test_default_footage_root_is_the_held_out_independent_folder():
    import inspect

    assert "independent" in inspect.getsource(cctv_validate.main).split('"--footage"')[1].split("help=")[0]
