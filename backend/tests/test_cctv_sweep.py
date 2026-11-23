"""Sweep tests, on localhost only: a simulator camera (plain RTSP with a login), a fake camera that rejects every login (401), a port with
nothing listening, and a port that accepts connections but is not RTSP. Not real cameras."""
import json
import socket
import socketserver
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "loadtest"))
import local_rtsp_server as sim  # noqa: E402
from test_cctv import make_video  # noqa: E402
from test_cctv_preflight import serve as serve_401  # noqa: E402
from tools import cctv_sweep  # noqa: E402

PW = "sw33p-Pw!@#9"


@pytest.fixture()
def sim_camera(tmp_path):
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
            sim.Handler(c, src, "stream1", "admin", PW, lambda *a: None).start()

    threading.Thread(target=loop, daemon=True).start()
    yield srv.getsockname()[1]
    stop.set()
    srv.close()


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def not_rtsp_server():
    class H(socketserver.BaseRequestHandler):
        def handle(self):
            try:
                self.request.recv(100)
                self.request.sendall(b"HTTP/1.1 400 Bad Request" + bytes([13, 10, 13, 10]))
            except OSError:
                pass
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def cam(name, port, path="/stream1"):
    return {"name": name, "host": "127.0.0.1", "port": port, "path": path}


def test_detect_protocol_without_any_login(sim_camera):
    assert cctv_sweep.detect_protocol("127.0.0.1", sim_camera)[0] == "rtsp"
    assert cctv_sweep.detect_protocol("127.0.0.1", free_port())[0] == "unreachable"
    srv = not_rtsp_server()
    try:
        proto, note = cctv_sweep.detect_protocol("127.0.0.1", srv.server_address[1])
        assert proto == "not_rtsp" and "not" in note
    finally:
        srv.shutdown()


def test_working_camera_is_found_and_the_others_are_classified_without_sending_credentials(sim_camera):
    srv = not_rtsp_server()
    lines = []
    try:
        res = cctv_sweep.sweep([cam("Lobby", sim_camera), cam("Gone", free_port()), cam("Web", srv.server_address[1])], "admin", PW,
                               probe_seconds=3, pause=0, log=lines.append)
    finally:
        srv.shutdown()
    by = {r["name"]: r for r in res}
    assert by["Lobby"]["result"] == "WORKING" and by["Lobby"]["codec"] == "h264" and by["Lobby"]["size"] == "320x240"
    assert by["Gone"]["result"] == "UNREACHABLE"
    assert by["Web"]["result"] == "NOT-RTSP" and "No login was sent" in by["Web"]["detail"]
    assert PW not in json.dumps(res) and PW not in "\n".join(lines)


def test_a_rejected_login_stops_the_sweep_so_other_cameras_are_not_attempted(sim_camera):
    fake = serve_401("401 Unauthorized")
    lines = []
    try:
        res = cctv_sweep.sweep([cam("Fake", fake.server_address[1]), cam("Lobby", sim_camera), cam("Third", sim_camera)], "admin", PW,
                               probe_seconds=3, pause=0, log=lines.append)
    finally:
        fake.shutdown()
    assert [r["result"] for r in res] == ["LOGIN-REJECTED", "NOT-TRIED", "NOT-TRIED"]
    assert any("stopping" in l for l in lines) and PW not in "\n".join(lines) + json.dumps(res)


def test_wrong_stream_path_and_wrong_password_are_told_apart(sim_camera):
    path_wrong = cctv_sweep.check_camera(cam("X", sim_camera, "/nope"), "admin", PW, 3)
    assert path_wrong["result"] == "STREAM-PATH-WRONG"
    bad_pw = cctv_sweep.check_camera(cam("X", sim_camera), "admin", "wrong-password", 3)
    assert bad_pw["result"] == "LOGIN-REJECTED"
    assert "wrong-password" not in json.dumps(bad_pw)


def test_only_filter_and_cameras_file_rules(tmp_path, sim_camera):
    res = cctv_sweep.sweep([cam("A", free_port()), cam("B", sim_camera)], "admin", PW, probe_seconds=3, pause=0, only={"B"}, log=lambda *_: None)
    assert [r["name"] for r in res] == ["B"] and res[0]["result"] == "WORKING"
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"host": "h", "cameras": [{"name": "a", "port": 1}], "password": "oops"}))
    with pytest.raises(SystemExit, match="must not contain a password"):
        cctv_sweep.load_cameras(f)
    f.write_text(json.dumps({"host": "h", "cameras": [{"name": "a", "port": 1, "path": "rtsp://u:p@h/x"}]}))
    with pytest.raises(SystemExit, match="must not contain a password"):
        cctv_sweep.load_cameras(f)
    f.write_text(json.dumps({"user": "viewer", "host": "h", "path": "/p", "cameras": [{"name": "a", "port": 1}, {"name": "b", "port": 2, "path": "/q"}]}))
    cams, user = cctv_sweep.load_cameras(f)
    assert user == "viewer" and cams[0]["path"] == "/p" and cams[1]["path"] == "/q"


def test_the_real_cameras_file_has_no_credentials_and_loads():
    cams, user = cctv_sweep.load_cameras(Path(__file__).resolve().parent.parent.parent / "validation" / "cameras_office.json")
    assert len(cams) == 7 and user == "admin" and all(c["host"] and c["port"] for c in cams)
    assert "@" not in json.dumps(cams)


def test_keep_going_continues_past_a_rejected_login_only_when_asked(sim_camera):
    fake = serve_401("401 Unauthorized")
    try:
        res = cctv_sweep.sweep([cam("Fake", fake.server_address[1]), cam("Lobby", sim_camera)], "admin", PW, probe_seconds=3, pause=0,
                               log=lambda *_: None, stop_on_reject=False)
    finally:
        fake.shutdown()
    assert [r["result"] for r in res] == ["LOGIN-REJECTED", "WORKING"]
