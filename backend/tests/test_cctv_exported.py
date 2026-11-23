"""Tests for the exported-footage workflow: inspecting exported files, cutting them with a human-supplied time basis,
the source_kind label, ignored-file warnings and the report banner. Sources are generated files, not a real export from the
camera owner, and not a camera."""
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
import pytest

from test_cctv import make_video
from tools import cctv_clip, cctv_inspect, cctv_meta, cctv_validate

BACKEND = Path(__file__).resolve().parent.parent


def make(path, fmt, codec, secs=6, fps=15, size=(320, 240), **opt):
    out = av.open(str(path), "w", format=fmt)
    vs = out.add_stream(codec, rate=fps)
    vs.width, vs.height, vs.pix_fmt = size[0], size[1], ("yuvj420p" if codec == "mjpeg" else "yuv420p")
    vs.options = {k: str(v) for k, v in opt.items()}
    for i in range(secs * fps):
        f = av.VideoFrame.from_ndarray(np.full((size[1], size[0], 3), (i * 7) % 255, np.uint8), format="bgr24")
        f.pts, f.time_base = i, Fraction(1, fps)
        for p in vs.encode(f):
            out.mux(p)
    for p in vs.encode(None):
        out.mux(p)
    out.close()
    return path


# ------------------------------------------------------------------ inspect
@pytest.mark.parametrize("name,fmt,codec", [("a.mp4", "mp4", "libx264"), ("b.avi", "avi", "libx264"), ("c.avi", "avi", "mjpeg"),
                                           ("d.mov", "mov", "libx264"), ("e.ts", "mpegts", "libx264")])
def test_common_export_formats_are_ready(tmp_path, name, fmt, codec):
    f = make(tmp_path / name, fmt, codec, g=15) if codec != "mjpeg" else make(tmp_path / name, fmt, codec)
    r = cctv_inspect.inspect_file(f)
    assert r["verdict"] in ("READY", "USABLE WITH WARNINGS") and not r["issues"], r
    assert r["source_kind"] == "exported_file" and len(r["sha256"]) == 64
    assert r["measured_fps"] == pytest.approx(15, rel=0.1) and r["opencv_frames"] == r["frames_decoded"] == 90


def test_raw_stream_without_timestamps_is_unusable_with_the_fix_to_ask_for(tmp_path):
    f = make(tmp_path / "raw.h264", "h264", "libx264", g=15)
    r = cctv_inspect.inspect_file(f)
    assert r["verdict"] == "UNUSABLE" and any("without container timestamps" in m and "MP4 or AVI" in m for m in r["issues"])


def test_garbage_and_proprietary_files_are_reported_not_crashed_on(tmp_path):
    (tmp_path / "x.mp4").write_bytes(b"this is not a video" * 100)
    (tmp_path / "y.dav").write_bytes(b"\x00" * 2048)
    for n in ("x.mp4", "y.dav"):
        r = cctv_inspect.inspect_file(tmp_path / n)
        assert r["verdict"] == "UNUSABLE" and r["issues"]
    assert "proprietary DVR format" in " ".join(cctv_inspect.inspect_file(tmp_path / "y.dav")["issues"])


def test_low_fps_is_warned(tmp_path):
    f = make(tmp_path / "slow.mp4", "mp4", "libx264", secs=20, fps=2, g=2)
    r = cctv_inspect.inspect_file(f)
    assert r["verdict"] == "USABLE WITH WARNINGS" and any("below the 5 fps" in m for m in r["warnings"])


def test_inspect_cli_never_modifies_the_footage_and_refuses_to_overwrite_an_inventory(tmp_path):
    f = make(tmp_path / "e1.mp4", "mp4", "libx264", g=15)
    before = (f.stat().st_size, f.stat().st_mtime_ns, cctv_inspect.sha256(f))
    inv = tmp_path / "res" / "inv.json"
    r = subprocess.run([sys.executable, "-m", "tools.cctv_inspect", str(tmp_path), "--inventory", str(inv)], cwd=BACKEND, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and "FILE / EXPORTED FOOTAGE" in r.stdout and "says nothing about live RTSP" in r.stdout
    assert (f.stat().st_size, f.stat().st_mtime_ns, cctv_inspect.sha256(f)) == before
    d = json.loads(inv.read_text())
    assert d["classification"] == "FILE / EXPORTED FOOTAGE" and d["files"][0]["sha256"] == before[2]
    r2 = subprocess.run([sys.executable, "-m", "tools.cctv_inspect", str(tmp_path), "--inventory", str(inv)], cwd=BACKEND, capture_output=True, text=True, timeout=120)
    assert r2.returncode != 0 and "not overwriting" in (r2.stdout + r2.stderr)


# ------------------------------------------------------------------ clip (exported source)
def test_cut_times_are_measured_from_the_first_frame_even_when_the_container_starts_late(tmp_path):
    src = make(tmp_path / "late.ts", "mpegts", "libx264", secs=10, g=15)
    with av.open(str(src)) as c:
        origin = float(c.streams.video[0].start_time * c.streams.video[0].time_base)
    info = cctv_clip.cut(src, 3.0, 6.0, tmp_path / "c.mkv")
    assert info["origin_s"] == pytest.approx(origin)
    assert 1.5 <= info["actual_start_s"] <= 3.5 and info["actual_end_s"] <= 6.2     # relative to the first frame, not the raw timestamps


def test_raw_and_unopenable_sources_are_a_clean_error_not_a_traceback(tmp_path):
    raw = make(tmp_path / "r.h264", "h264", "libx264", g=15)
    with pytest.raises(SystemExit, match="raw video stream"):
        cctv_clip.cut(raw, 1, 3, tmp_path / "o.mkv")
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"nope" * 200)
    with pytest.raises(SystemExit, match="cannot be opened"):
        cctv_clip.cut(bad, 1, 3, tmp_path / "o2.mkv")
    assert not (tmp_path / "o.mkv").exists() and not (tmp_path / "o2.mkv").exists()


def run_clip(src, out, *extra):
    return subprocess.run([sys.executable, "-m", "tools.cctv_clip", str(src), "--start", "1", "--end", "5", "--out", str(out), *extra],
                          cwd=BACKEND, capture_output=True, text=True, timeout=120)


def test_exported_clip_sidecar_converts_a_local_time_with_offset_to_utc_and_is_marked_exported(tmp_path):
    src = make(tmp_path / "export.mp4", "mp4", "libx264", secs=10, g=15)
    out = tmp_path / "independent" / "normal_office_activity" / "clip.mkv"
    r = run_clip(src, out, "--source-start", "2026-12-01T10:30:00+05:30")
    assert r.returncode == 0, r.stdout + r.stderr
    side = json.loads(out.with_suffix(".json").read_text())
    assert side["source_kind"] == "exported_file" and side["cut_from"] == "export.mp4"
    assert side["segment_start_utc"].startswith("2026-12-01T05:00:") and side["segment_start_utc"].endswith("Z")   # 10:30 IST = 05:00 UTC
    p = cctv_meta._new(out, "normal_office_activity", "office-1", "ab")
    meta = json.loads(p.read_text())
    assert meta["source_kind"] == "exported_file" and meta["recording_start"] == side["segment_start_utc"]


def test_source_start_without_time_zone_or_with_a_recorder_sidecar_is_refused(tmp_path):
    src = make(tmp_path / "export.mp4", "mp4", "libx264", secs=10, g=15)
    r = run_clip(src, tmp_path / "c1.mkv", "--source-start", "2026-12-01T10:30:00")
    assert r.returncode != 0 and "time zone" in (r.stdout + r.stderr)
    src.with_suffix(".json").write_text(json.dumps({"segment_start_utc": "2026-12-01T00:00:00Z", "camera_id": "x", "source_kind": "rtsp"}))
    r2 = run_clip(src, tmp_path / "c2.mkv", "--source-start", "2026-12-01T10:30:00Z")
    assert r2.returncode != 0 and "recorder sidecar" in (r2.stdout + r2.stderr)


def test_exported_clip_without_a_time_basis_still_gets_a_source_kind_but_no_invented_times(tmp_path):
    src = make(tmp_path / "export.mp4", "mp4", "libx264", secs=10, g=15)
    out = tmp_path / "c.mkv"
    assert run_clip(src, out).returncode == 0
    side = json.loads(out.with_suffix(".json").read_text())
    assert side["source_kind"] == "exported_file" and "segment_start_utc" not in side
    meta = json.loads(cctv_meta._new(out, "normal_office_activity", "c", "").read_text())
    assert meta["recording_start"].startswith("FILL-IN") and meta["source_kind"] == "exported_file"


# ------------------------------------------------------------------ meta
def good(**kw):
    m = {"schema_version": 1, "camera_id": "c", "recording_start": "2026-12-01T10:00:00+05:30", "recording_end": "2026-12-01T10:01:00+05:30",
         "scenario": "normal_office_activity", "expected_event": "none"}
    m.update(kw)
    return m


def test_source_kind_is_optional_but_validated_and_time_zone_offsets_are_accepted():
    cctv_meta.validate(good())
    for k in cctv_meta.SOURCE_KINDS:
        cctv_meta.validate(good(source_kind=k))
    with pytest.raises(cctv_meta.MetaError, match="unknown source_kind"):
        cctv_meta.validate(good(source_kind="live camera"))


def test_new_label_takes_an_explicit_source_kind_and_check_warns_about_ignored_files(tmp_path):
    root = tmp_path / "independent"
    (root / "normal_office_activity").mkdir(parents=True)
    clip = root / "normal_office_activity" / "a.mkv"
    make_video(clip, seconds=1, size=(160, 120))
    meta = json.loads(cctv_meta._new(clip, "normal_office_activity", "c", "", "simulator").read_text())
    assert meta["source_kind"] == "simulator"
    with pytest.raises(SystemExit):
        cctv_meta._new(clip, "normal_office_activity", "c", "", "made-up")
    (root / "normal_office_activity" / "export.ts").write_bytes(b"x")
    (root / "normal_office_activity" / "notes.txt").write_text("hi")
    assert [p.name for p in cctv_meta.ignored_files(root)] == ["export.ts"]
    r = subprocess.run([sys.executable, "-m", "tools.cctv_meta", "check", str(root)], cwd=BACKEND, capture_output=True, text=True, timeout=60)
    assert "WARNING" in r.stdout and "export.ts" in r.stdout and "NOT be validated" in r.stdout


# ------------------------------------------------------------------ report banner
def report(kinds):
    cfg = {"name": "default", "detector_conf": 0.4, "engine_overrides": {}, "sensitivity": "medium",
           "summary": {"fall_clips": 0, "falls_possible": 0, "falls_confirmed": 0, "falls_missed": 0, "confirm_latency_s": {"n": 0, "median": None, "min": None, "max": None},
                       "normal_clips": 1, "normal_hours": 0.1, "false_possible_total": 0, "false_confirmed_total": 0, "false_confirmed_per_normal_hour": 0.0,
                       "false_possible_per_normal_hour": 0.0, "total_footage_hours": 0.1},
           "performance": {"mean_frame_latency_ms": 100.0, "single_stream_max_fps": 10.0}, "by_scenario": {}, "clips": []}
    return {"run": "r", "footage_role": "independent", "clips_scored": 1, "skipped": [], "configs": [cfg], "source_kinds": kinds}


def test_report_banner_separates_exported_footage_from_live_rtsp_and_the_physical_camera():
    md = cctv_validate.to_markdown(report({"exported_file": 2}))
    assert "FILE / EXPORTED FOOTAGE" in md and "Live RTSP connectivity: NOT tested" in md and "Physical-camera live validation: NOT done" in md
    live = cctv_validate.to_markdown(report({"rtsp_recording": 3}))
    assert "FILE / EXPORTED FOOTAGE" not in live and "recorded by cctv_record from RTSP" in live
    sim = cctv_validate.to_markdown(report({"simulator": 1}))
    assert "SIMULATOR" in sim
    mixed = cctv_validate.to_markdown(report({"exported_file": 1, "unspecified": 1}))
    assert "unspecified" in mixed


def test_summarise_sources_counts_every_kind():
    rows = [{"source_kind": "exported_file"}, {"source_kind": "exported_file"}, {"source_kind": "unspecified"}]
    assert cctv_validate.summarise_sources(rows) == {"exported_file": 2, "unspecified": 1}
