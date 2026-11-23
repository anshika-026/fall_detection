"""RTSP over TLS (rtsps) cameras, and passwords with special characters in a camera's address."""
from urllib.parse import unquote, urlsplit

import pytest
from test_api import auth_client, client  # noqa: F401  (fixtures)

from falldet.camera import camera_db, stream_source

PW = "Pa@ss:w/rd#1?%!&=+"


def test_rtsps_url_is_built_with_the_right_scheme_and_an_encoded_password():
    url = stream_source.build_rtsp_url({"protocol": "rtsps", "host": "10.0.0.5", "port": 91, "user": "admin", "password": PW,
                                        "stream_path": "/video/live?channel=1&subtype=0"})
    p = urlsplit(url)
    assert p.scheme == "rtsps" and p.hostname == "10.0.0.5" and p.port == 91 and p.path == "/video/live" and p.query == "channel=1&subtype=0"
    assert p.username == "admin" and unquote(p.password) == PW                       # the real password survives the round trip
    assert "@" not in p.netloc.rsplit("@", 1)[0].split(":", 1)[1]                    # no raw @ left inside the password


def test_plain_rtsp_urls_are_unchanged_for_ordinary_passwords_and_fixed_for_special_ones():
    cam = {"host": "10.0.0.5", "port": 554, "user": "admin", "password": "s3cret", "stream_path": "/stream1"}
    assert stream_source.build_rtsp_url(cam) == "rtsp://admin:s3cret@10.0.0.5:554/stream1"        # behaviour for existing cameras
    cam["password"] = "a@b"
    assert stream_source.build_rtsp_url(cam) == "rtsp://admin:a%40b@10.0.0.5:554/stream1"        # was a broken address before


def test_rtsps_default_port_and_protocol_helpers():
    assert stream_source.build_rtsp_url({"protocol": "rtsps", "host": "h", "port": 0, "stream_path": "x"}).startswith("rtsps://h:322/x")
    assert stream_source.normalize_protocol("RTSPS") == "rtsps" and stream_source.protocol_of({"protocol": "rtsps"}) == "rtsps"
    assert stream_source.build_source_url({"protocol": "rtsps", "host": "h", "port": 91, "user": "u", "password": "p", "stream_path": "/a"}) == "rtsps://u:p@h:91/a"
    assert camera_db.is_streamable({"protocol": "rtsps", "host": "h"}) and not camera_db.is_streamable({"protocol": "rtsps", "host": ""})


def test_redaction_masks_the_password_of_an_encoded_address():
    url = stream_source.build_rtsp_url({"protocol": "rtsps", "host": "h", "port": 91, "user": "admin", "password": PW, "stream_path": "/a"})
    red = stream_source.redact_source(url)
    assert PW not in red and "%40" not in red and "***" in red


def test_api_accepts_an_rtsps_camera_and_never_returns_the_password(auth_client):  # noqa: F811
    r = auth_client.post("/api/cameras", json={"name": "Main Hall 1", "protocol": "rtsps", "host": "10.0.0.5", "port": 91, "user": "admin",
                                               "password": PW, "stream_path": "/video/live?channel=1&subtype=0"})
    assert r.status_code == 200, r.text
    cam = r.json()
    assert cam["protocol"] == "rtsps" and cam["port"] == 91 and PW not in r.text
    assert PW not in auth_client.get("/api/cameras").text
    assert auth_client.post("/api/cameras", json={"name": "Bad", "protocol": "rtsps"}).status_code == 422        # still needs a host
    assert auth_client.post("/api/cameras", json={"name": "Bad2", "protocol": "ftp", "host": "h"}).status_code == 422
    stored = camera_db.get_camera_connection(cam["id"])
    assert stored["protocol"] == "rtsps" and stored["password"] == PW                              # stored as typed (documented limitation), used encoded
