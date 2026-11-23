"""The localhost RTSP simulator (loadtest/local_rtsp_server.py) and the preflight/recorder over a REAL RTSP/TCP connection.
Still a simulator on loopback: this proves the tools work over RTSP, not that any physical camera is compatible."""
import socket
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "loadtest"))
import local_rtsp_server as sim  # noqa: E402
from test_cctv import make_video, run_recorder  # noqa: E402
from tools import cctv_preflight as pf  # noqa: E402


@pytest.fixture()
def server(tmp_path):
    vid = tmp_path / "v.mkv"
    make_video(vid, seconds=4, fps=15, size=(320, 240), gop=15)
    src = sim.Source(str(vid))
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    srv.settimeout(0.3)
    stop = threading.Event()

    def loop():
        while not stop.is_set():
            try:
                c, _ = srv.accept()
            except (socket.timeout, OSError):
                continue
            sim.Handler(c, src, "stream1", "tester", "sim-pw-123", lambda *a: None).start()

    threading.Thread(target=loop, daemon=True).start()
    yield srv.getsockname()[1]
    stop.set()
    srv.close()


def args(tmp_path):
    return SimpleNamespace(camera=["office-1=CCTV_SIM_URL"], db_camera=None, config=None, out=str(tmp_path / "o"), probe_seconds=3.0, min_free_gb=0.0, json="")


def test_preflight_passes_over_real_rtsp_with_a_login_and_reports_an_rtsp_source(server, tmp_path, monkeypatch):
    monkeypatch.setenv("CCTV_SIM_URL", f"rtsp://tester:sim-pw-123@127.0.0.1:{server}/stream1")
    rep = pf.run(args(tmp_path))
    c = {x.name: x for x in rep.checks}
    assert not rep.failed, [(x.name, x.detail) for x in rep.checks if x.status == pf.FAIL]
    assert rep.info["source_kind"] == "rtsp" and "RTSP network camera" in c["camera input"].detail
    assert c["RTSP open"].status == pf.OK and c["decoding"].status == pf.OK and rep.info["codec"] == "h264"
    assert "sim-pw-123" not in pf.render(rep, "--camera office-1=CCTV_SIM_URL")


def test_wrong_password_and_wrong_path_are_explained(server, tmp_path, monkeypatch):
    monkeypatch.setenv("CCTV_SIM_URL", f"rtsp://tester:WRONG-pw@127.0.0.1:{server}/stream1")
    c = {x.name: x for x in pf.run(args(tmp_path)).checks}
    assert c["RTSP open"].status == pf.FAIL and "rejected the login" in c["RTSP open"].detail
    monkeypatch.setenv("CCTV_SIM_URL", f"rtsp://tester:sim-pw-123@127.0.0.1:{server}/nope")
    c2 = {x.name: x for x in pf.run(args(tmp_path)).checks}
    assert c2["RTSP open"].status == pf.FAIL and "no stream" in c2["RTSP open"].detail


def test_recorder_over_real_rtsp_marks_the_sidecar_rtsp_and_keeps_the_password_out(server, tmp_path):
    import json

    url = f"rtsp://tester:sim-pw-123@127.0.0.1:{server}/stream1"
    run_recorder(url, tmp_path / "rec", seconds=4)
    side = sorted((tmp_path / "rec" / "test-cam").glob("*.json"))
    assert side
    d = json.loads(side[0].read_text())
    assert d["source_kind"] == "rtsp" and d["source_codec"] == "h264" and d["media_span_s"] > 1
    assert all("sim-pw-123" not in p.read_text() for p in side)
