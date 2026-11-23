"""The camera loader: adds from a names-only file, never overwrites, enables only the cameras asked for, never prints the password."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from falldet.camera import camera_db
from tools import add_cameras

BACKEND = Path(__file__).resolve().parent.parent
PW = "Ld@9:r/#1?%x"


def cams_file(tmp_path):
    f = tmp_path / "cams.json"
    f.write_text(json.dumps({"user": "admin", "host": "10.0.0.5", "path": "/video/live?channel=1&subtype=0",
                             "cameras": [{"name": "Hall", "port": 91}, {"name": "Lobby", "port": 554}, {"name": "Exit", "port": 31}]}))
    return f


def run(tmp_path, *extra):
    import os

    env = {**os.environ, "CAM_PW_TEST": PW}
    return subprocess.run([sys.executable, "-m", "tools.add_cameras", "--cameras", str(cams_file(tmp_path)), "--password-env", "CAM_PW_TEST", *extra],
                          cwd=BACKEND, env=env, capture_output=True, text=True, timeout=60)


def test_plan_marks_existing_names_as_skipped_and_enables_only_the_requested_ones():
    cams = [{"name": "A", "host": "h", "port": 1, "path": "/p"}, {"name": "B", "host": "h", "port": 2, "path": "/p"}]
    rows = add_cameras.plan(cams, "u", {"B"}, {"A"}, "rtsps")
    assert rows[0]["action"] == "add" and rows[0]["fields"]["live_feed_enabled"] and rows[0]["fields"]["protocol"] == "rtsps"
    assert rows[1]["action"].startswith("skip")


def test_dry_run_changes_nothing_and_a_real_run_adds_once(tmp_path, monkeypatch, clean_db):
    monkeypatch.setenv("CAM_PW_TEST", PW)
    from falldet.core import schema

    schema.init_db()
    monkeypatch.setattr(sys, "argv", ["x", "--cameras", str(cams_file(tmp_path)), "--password-env", "CAM_PW_TEST", "--enable", "Hall", "--dry-run"])
    add_cameras.main()
    assert camera_db.list_cameras() == []
    monkeypatch.setattr(sys, "argv", ["x", "--cameras", str(cams_file(tmp_path)), "--password-env", "CAM_PW_TEST", "--enable", "Hall"])
    add_cameras.main()
    by = {c["name"]: c for c in camera_db.list_cameras()}
    assert set(by) == {"Hall", "Lobby", "Exit"}
    assert by["Hall"]["live_feed_enabled"] and by["Hall"]["fall_detection_enabled"]
    assert not by["Lobby"]["live_feed_enabled"] and not by["Lobby"]["fall_detection_enabled"] and not by["Exit"]["fall_detection_enabled"]
    assert by["Hall"]["protocol"] == "rtsps" and by["Hall"]["port"] == 91
    add_cameras.main()                                                    # second run: nothing is duplicated or overwritten
    assert len(camera_db.list_cameras()) == 3


def test_password_is_stored_for_streaming_but_never_printed(tmp_path, monkeypatch, clean_db, capsys):
    monkeypatch.setenv("CAM_PW_TEST", PW)
    from falldet.core import schema

    schema.init_db()
    monkeypatch.setattr(sys, "argv", ["x", "--cameras", str(cams_file(tmp_path)), "--password-env", "CAM_PW_TEST", "--enable", "Hall"])
    add_cameras.main()
    out = capsys.readouterr().out
    assert PW not in out and "%40" not in out
    assert camera_db.get_camera_connection(next(c["id"] for c in camera_db.list_cameras() if c["name"] == "Hall"))["password"] == PW


def test_unknown_enable_name_is_rejected(tmp_path, monkeypatch, clean_db):
    monkeypatch.setattr(sys, "argv", ["x", "--cameras", str(cams_file(tmp_path)), "--enable", "Nope"])
    with pytest.raises(SystemExit, match="not in the cameras file"):
        add_cameras.main()
