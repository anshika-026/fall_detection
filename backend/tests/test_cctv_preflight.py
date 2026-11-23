"""Preflight tests. Network behaviour is tested against a tiny fake RTSP server on localhost that answers like a camera
that rejects a login (401) or has no such stream path (404): this checks that FFmpeg's real error text is classified
correctly. It is NOT a real camera and says nothing about real-camera compatibility."""
import json
import re
import socket
import socketserver
import threading
from types import SimpleNamespace

import pytest

from tools import cctv_preflight as pf
from test_cctv import make_video


def args(tmp_path, env_name=None, **kw):
    base = dict(camera=[f"cam-1={env_name}"] if env_name else None, db_camera=None, config=None, out=str(tmp_path / "out"),
                probe_seconds=3.0, min_free_gb=0.0, json="")
    base.update(kw)
    return SimpleNamespace(**base)


def by_name(rep):
    return {c.name: c for c in rep.checks}


class FakeCamera(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve(describe_status: str):
    class H(socketserver.StreamRequestHandler):
        def handle(self):
            try:
                while True:
                    lines = []
                    while True:
                        ln = self.rfile.readline()
                        if not ln:
                            return
                        if ln in (b"\r\n", b"\n"):
                            break
                        lines.append(ln.decode(errors="replace").strip())
                    if not lines:
                        return
                    method = lines[0].split()[0]
                    cseq = next((l.split(":")[1].strip() for l in lines if l.lower().startswith("cseq")), "1")
                    if method == "OPTIONS":
                        self.wfile.write(f"RTSP/1.0 200 OK\r\nCSeq: {cseq}\r\nPublic: OPTIONS, DESCRIBE, SETUP, PLAY\r\n\r\n".encode())
                    else:
                        extra = 'WWW-Authenticate: Basic realm="cam"\r\n' if describe_status.startswith("401") else ""
                        self.wfile.write(f"RTSP/1.0 {describe_status}\r\nCSeq: {cseq}\r\n{extra}\r\n".encode())
            except OSError:
                return
    srv = FakeCamera(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_error_text_classification():
    assert "login" in pf.classify_open_error("Server returned 401 Unauthorized (authorization failed)")[0]
    assert "no stream" in pf.classify_open_error("Server returned 404 Not Found")[0]
    assert "no answer" in pf.classify_open_error("Connection timed out")[0]
    assert "nothing accepts" in pf.classify_open_error("Connection refused")[0]
    assert "does not resolve" in pf.classify_open_error("Name or service not known")[0]
    assert "no network route" in pf.classify_open_error("Network is unreachable")[0]
    assert "not supported" in pf.classify_open_error("Protocol not found")[0]


@pytest.mark.parametrize("status,expect", [("401 Unauthorized", "rejected the login"), ("404 Not Found", "no stream")])
def test_fake_camera_errors_are_explained_and_password_never_printed(tmp_path, monkeypatch, status, expect):
    srv = serve(status)
    try:
        monkeypatch.setenv("CCTV_PF_URL", f"rtsp://admin:hunter2pw@127.0.0.1:{srv.server_address[1]}/stream1")
        rep = pf.run(args(tmp_path, "CCTV_PF_URL"))
        c = by_name(rep)
        assert c["TCP connect"].status == pf.OK                       # reachable
        assert c["RTSP open"].status == pf.FAIL and expect in c["RTSP open"].detail
        assert rep.failed
        text = pf.render(rep, "--camera cam-1=CCTV_PF_URL") + json.dumps([x.__dict__ for x in rep.checks]) + json.dumps(rep.info)
        assert "hunter2pw" not in text
    finally:
        srv.shutdown()


def test_closed_port_is_reported_as_unreachable(tmp_path, monkeypatch):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    monkeypatch.setenv("CCTV_PF_URL", f"rtsp://u:pw@127.0.0.1:{port}/x")
    rep = pf.run(args(tmp_path, "CCTV_PF_URL"))
    c = by_name(rep)
    assert c["TCP connect"].status == pf.FAIL and "nothing accepts" in c["TCP connect"].detail
    assert "RTSP open" not in c                                       # does not go on to open a stream it cannot reach


def test_unresolvable_host_fails_at_dns(tmp_path, monkeypatch):
    monkeypatch.setenv("CCTV_PF_URL", "rtsp://u:pw@no-such-host.invalid:554/x")
    c = by_name(pf.run(args(tmp_path, "CCTV_PF_URL")))
    assert c["DNS"].status == pf.FAIL and "TCP connect" not in c


def test_file_source_passes_but_is_labelled_not_a_camera(tmp_path, monkeypatch):
    vid = tmp_path / "v.mkv"
    make_video(vid, seconds=4, fps=10, size=(640, 480), gop=10)
    monkeypatch.setenv("CCTV_PF_URL", str(vid))
    rep = pf.run(args(tmp_path, "CCTV_PF_URL"))
    c = by_name(rep)
    assert not rep.failed and rep.info["source_kind"] == "file"
    assert "NOT A CAMERA" in c["camera input"].detail
    assert c["codec"].status == pf.OK and c["decoding"].status == pf.OK and c["frame rate"].status == pf.OK
    assert rep.info["width"] == 640 and rep.info["fps_measured"] == pytest.approx(10, rel=0.15)
    out = pf.render(rep, "--camera cam-1=CCTV_PF_URL")
    assert "says nothing about a real camera" in out and "Next, a 60-second" not in out


def test_one_camera_per_run_and_missing_input(tmp_path, monkeypatch):
    monkeypatch.setenv("A_URL", "x.mkv")
    monkeypatch.setenv("B_URL", "y.mkv")
    two = pf.run(SimpleNamespace(camera=["a=A_URL", "b=B_URL"], db_camera=None, config=None, out=str(tmp_path / "o"), probe_seconds=2, min_free_gb=0, json=""))
    assert two.failed and "one camera per run" in by_name(two)["camera input"].hint
    none = pf.run(SimpleNamespace(camera=None, db_camera=None, config=None, out=str(tmp_path / "o2"), probe_seconds=2, min_free_gb=0, json=""))
    assert none.failed


def test_unwritable_recording_folder_and_low_disk_are_failures(tmp_path):
    blocker = tmp_path / "file_not_dir"
    blocker.write_text("x")
    rep = pf.Report()
    pf.check_output_and_disk(rep, blocker / "sub", 2.0)
    assert by_name(rep)["recording folder"].status == pf.FAIL
    rep2 = pf.Report()
    pf.check_output_and_disk(rep2, tmp_path / "ok", 10_000_000.0)       # demands ~10 PB free
    assert by_name(rep2)["disk space"].status == pf.FAIL


def test_memory_reading_works_on_this_system():
    total, avail = pf.memory_gb()
    assert total is None or (total > 0 and 0 <= avail <= total)
