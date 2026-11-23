"""API + integration tests: engine -> incident manager -> database -> API, on an
isolated database. All incidents here come from running the real engine on
synthetic skeletons; nothing is inserted by hand."""
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient
from synth import FRAME, GROUND, H, Timeline, lerp, lying_kw, stand_kw

from falldet.core import settings_store
from falldet.event_manager import incidents
from falldet.event_manager.manager import IncidentManager
from falldet.fall_analysis.config import FallConfig
from falldet.fall_analysis.engine import CameraFallEngine
from falldet.main import app

FRAME_IMG = np.zeros((FRAME[1], FRAME[0], 3), dtype=np.uint8)


@pytest.fixture()
def client(clean_db):
    from falldet.api import routes_auth

    routes_auth._attempts.clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_client(client):
    r = client.post("/api/auth/setup", json={"email": "ops@example.com", "password": "correct-horse"})
    assert r.status_code == 200, r.text
    client.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return client


def run_fall(manager: IncidentManager, camera_id=1, hold=6.0, recover=False, cfg=None):
    """Plays a fall through a real engine and records the events like the runtime does."""
    tl = Timeline().hold(4, **stand_kw())
    tl.run(0.5, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.06 * H, lt / 0.5), torso_deg=lerp(2, 88, lt / 0.5)))
    tl.hold(hold, **lying_kw())
    if recover:
        tl.run(2.0, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.06 * H, GROUND - 0.5 * H, lt / 2), torso_deg=lerp(88, 2, lt / 2)))
        tl.hold(12, **stand_kw())
    eng = CameraFallEngine(camera_id, cfg or FallConfig(auto_resolve_seconds=8.0))
    base = time.time() - tl.t - 5
    for ts, people in tl.frames:
        for ev in eng.update(base + ts, people, FRAME):
            manager.handle(ev, ev.fsm, FRAME_IMG)
    return eng


def test_everything_requires_sign_in(client):
    for path in ("/api/cameras", "/api/dashboard", "/api/analytics", "/api/incidents", "/api/settings", "/api/system"):
        assert client.get(path).status_code == 401, path
    assert client.get("/health").json() == {"ok": True}


def test_first_run_setup_then_login(client):
    assert client.get("/api/auth/status").json() == {"setup_required": True}
    assert client.post("/api/auth/setup", json={"email": "a@b.co", "password": "short"}).status_code == 422
    r = client.post("/api/auth/setup", json={"email": "A@B.co", "password": "long-enough-pw"})
    assert r.status_code == 200
    assert client.post("/api/auth/setup", json={"email": "x@y.co", "password": "long-enough-pw"}).status_code == 409
    assert client.get("/api/auth/status").json() == {"setup_required": False}
    assert client.post("/api/auth/login", json={"email": "a@b.co", "password": "wrong-password"}).status_code == 401
    ok = client.post("/api/auth/login", json={"email": "a@b.co", "password": "long-enough-pw"})
    assert ok.status_code == 200
    tok = ok.json()["token"]
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()["email"] == "a@b.co"
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {tok}"})
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_empty_system_reports_zeros_not_fake_data(auth_client):
    d = auth_client.get("/api/dashboard").json()
    assert d["summary"]["total"] == 0 and d["summary"]["active"] == 0 and d["summary"]["resolved"] == 0
    assert d["recent_activity"] == [] and d["active_incidents"] == [] and d["cameras"]["total"] == 0
    a = auth_client.get("/api/analytics?days=7").json()
    assert a["total_falls"] == 0 and a["by_camera"] == [] and a["history"] == []
    assert len(a["daily"]) == 7 and all(x["falls"] == 0 for x in a["daily"])
    assert len(a["by_hour"]) == 24 and all(x["falls"] == 0 for x in a["by_hour"])
    assert a["confidence"]["avg"] is None


def test_camera_crud_and_secrets_never_returned(auth_client):
    assert auth_client.post("/api/cameras", json={"name": "Lobby"}).status_code == 422          # RTSP needs a host
    r = auth_client.post("/api/cameras", json={"name": "Lobby", "host": "10.0.0.5", "user": "admin", "password": "s3cret",
                                               "stream_path": "/h264", "fall_detection_enabled": True})
    assert r.status_code == 200, r.text
    cam = r.json()
    assert "password" not in cam and cam["password_set"] is True and cam["fall_detection_enabled"] is True
    assert "s3cret" not in r.text
    cid = cam["id"]
    u = auth_client.put(f"/api/cameras/{cid}", json={"name": "Lobby 2", "fall_detection_enabled": False})
    assert u.json()["name"] == "Lobby 2" and u.json()["fall_detection_enabled"] is False
    from falldet.camera import camera_db
    assert camera_db.get_camera_connection(cid)["password"] == "s3cret"      # untouched by an edit that omitted it
    assert auth_client.put(f"/api/cameras/{cid}", json={"port": 70000}).status_code == 422
    assert auth_client.put("/api/cameras/9999", json={"name": "x"}).status_code == 404
    assert len(auth_client.get("/api/cameras").json()) == 1
    assert auth_client.get("/api/cameras").json()[0]["connection"] in ("idle", "offline", "connecting", "online")
    assert auth_client.delete(f"/api/cameras/{cid}").json() == {"ok": True}
    assert auth_client.get("/api/cameras").json() == []


def test_rtmp_camera_requires_valid_link(auth_client):
    assert auth_client.post("/api/cameras", json={"name": "R", "protocol": "rtmp", "source_url": "http://x"}).status_code == 422
    ok = auth_client.post("/api/cameras", json={"name": "R", "protocol": "rtmp", "source_url": "rtmp://10.0.0.9/live/abc123key"})
    assert ok.status_code == 200
    assert "abc123key" not in ok.text and ok.json()["source_url_set"] is True


def test_fall_lifecycle_through_to_dashboard_and_analytics(auth_client):
    auth_client.post("/api/cameras", json={"name": "Ward A", "host": "10.0.0.5"})
    mgr = IncidentManager(lambda cid: "Ward A")
    run_fall(mgr, camera_id=1, recover=True)
    inc = auth_client.get("/api/incidents").json()
    assert inc["total"] == 1
    item = inc["items"][0]
    assert item["state"] == "resolved" and item["resolved_by"] == "system" and item["confirmed_at"] is not None
    kinds = [e["kind"] for e in auth_client.get(f"/api/incidents/{item['id']}").json()["events"]]
    assert kinds == ["possible", "confirmed", "recovered", "resolved"]
    assert auth_client.get(f"/api/incidents/{item['id']}/snapshot").status_code == 200

    s = auth_client.get("/api/dashboard").json()["summary"]
    assert (s["total"], s["active"], s["resolved"]) == (1, 0, 1)
    a = auth_client.get("/api/analytics?days=7").json()
    assert a["total_falls"] == 1 and a["by_camera"][0]["camera_name"] == "Ward A" and a["by_camera"][0]["falls"] == 1
    assert sum(x["falls"] for x in a["daily"]) == 1 and sum(x["falls"] for x in a["by_hour"]) == 1
    assert a["confidence"]["avg"] is not None and sum(b["falls"] for b in a["confidence"]["distribution"]) == 1
    assert len(a["history"]) == 1


def test_active_alert_ack_resolve_and_no_double_count(auth_client):
    mgr = IncidentManager(lambda cid: "Ward A")
    eng = run_fall(mgr, hold=8)                       # still on the floor: CONFIRMED
    items = auth_client.get("/api/incidents?state=active").json()["items"]
    assert len(items) == 1 and items[0]["state"] == "confirmed"
    iid = items[0]["id"]
    s = auth_client.get("/api/dashboard").json()["summary"]
    assert (s["total"], s["active"], s["unacknowledged"]) == (1, 1, 1)

    assert auth_client.post(f"/api/incidents/{iid}/acknowledge").json() == {"ok": True}
    assert auth_client.post(f"/api/incidents/{iid}/acknowledge").json() == {"ok": False}      # already acknowledged
    assert auth_client.post(f"/api/incidents/{iid}/resolve", json={"reason": "  "}).status_code == 422
    assert auth_client.post(f"/api/incidents/{iid}/resolve", json={"reason": "Checked, person is fine"}).json() == {"ok": True}
    assert auth_client.post(f"/api/incidents/{iid}/resolve", json={"reason": "again"}).json() == {"ok": False}
    done = auth_client.get(f"/api/incidents/{iid}").json()
    assert done["state"] == "resolved" and done["resolved_by"] == "ops@example.com"

    # a late engine event for the already-closed incident must not reopen or duplicate it
    assert incidents.transition(iid, "recovered", time.time()) is False
    assert incidents.transition(iid, "confirmed", time.time()) is False
    s = auth_client.get("/api/dashboard").json()["summary"]
    assert (s["total"], s["active"], s["resolved"]) == (1, 0, 1)
    assert auth_client.get("/api/incidents").json()["total"] == 1


def test_dismissed_possible_falls_are_not_counted_as_incidents(auth_client):
    mgr = IncidentManager(lambda cid: "Cam")
    tl = Timeline().hold(4, **stand_kw())
    tl.run(0.5, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.06 * H, lt / 0.5), torso_deg=lerp(2, 88, lt / 0.5)))
    tl.hold(1.0, **lying_kw())
    tl.run(1.0, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.06 * H, GROUND - 0.5 * H, lt), torso_deg=lerp(88, 2, lt)))
    tl.hold(5, **stand_kw())
    eng = CameraFallEngine(1, FallConfig())
    for ts, people in tl.frames:
        for ev in eng.update(time.time() - 60 + ts, people, FRAME):
            mgr.handle(ev, ev.fsm, FRAME_IMG)
    assert auth_client.get("/api/incidents").json()["total"] == 0
    assert auth_client.get("/api/incidents?state=dismissed").json()["total"] == 1
    d = auth_client.get("/api/dashboard").json()
    assert d["summary"]["total"] == 0 and d["summary"]["dismissed"] == 1
    assert auth_client.get("/api/analytics?days=7").json()["dismissed_possible_falls"] == 1


def test_low_confidence_fall_is_stored_but_not_alerted(auth_client):
    from falldet.event_manager.hub import hub

    seen = []
    orig = hub.publish
    hub.publish = lambda m: (seen.append(m), orig(m))[1]
    try:
        auth_client.put("/api/settings/alerts", json={"min_confidence": 1.0})
        run_fall(IncidentManager(lambda c: "Cam"), hold=6)
    finally:
        hub.publish = orig
    assert auth_client.get("/api/incidents").json()["total"] == 1
    assert not [m for m in seen if m.get("type") == "alert"]


def test_settings_validation_persistence_and_effect(auth_client):
    s = auth_client.get("/api/settings").json()
    assert s["detection"]["confirm_seconds"] == FallConfig().confirm_seconds
    assert auth_client.put("/api/settings/detection", json={"confirm_seconds": 0}).status_code == 422
    assert auth_client.put("/api/settings/detection", json={"nope": 1}).status_code == 422
    assert auth_client.put("/api/settings/detection", json={"sensitivity": "extreme"}).status_code == 422
    assert auth_client.put("/api/settings/alerts", json={"webhook_url": "ftp://x"}).status_code == 422
    assert auth_client.put("/api/settings/detection", json={"confirm_seconds": 5, "sensitivity": "high"}).status_code == 200
    cfg = settings_store.fall_config()
    assert cfg.confirm_seconds == 5 and cfg.min_drop < FallConfig().min_drop
    assert settings_store.fall_config("low").min_drop > FallConfig().min_drop          # per-camera override wins
    settings_store.invalidate()
    assert auth_client.get("/api/settings").json()["detection"]["confirm_seconds"] == 5   # survives a cache drop
    assert auth_client.post("/api/settings/detection/reset").json()["confirm_seconds"] == FallConfig().confirm_seconds
    assert auth_client.put("/api/settings/processing", json={"detect_fps": 99}).status_code == 422


def test_evidence_files_cannot_be_read_outside_the_evidence_folder(auth_client):
    mgr = IncidentManager(lambda c: "Cam")
    run_fall(mgr, hold=6)
    iid = auth_client.get("/api/incidents").json()["items"][0]["id"]
    from falldet.core import db
    from falldet import config
    with db.connect(config.DB_PATH) as c:
        c.execute("UPDATE incidents SET snapshot_path = ? WHERE id = ?", (__file__, iid))
    assert auth_client.get(f"/api/incidents/{iid}/snapshot").status_code == 404
    assert auth_client.get("/api/incidents/9999/clip").status_code == 404


def test_websocket_requires_a_valid_token(auth_client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect) as e:
        with auth_client.websocket_connect("/ws/events?token=bogus") as ws:
            ws.receive_json()
    assert e.value.code == 4401
    tok = auth_client.headers["Authorization"].split()[1]
    with auth_client.websocket_connect(f"/ws/events?token={tok}") as ws:
        run_fall(IncidentManager(lambda c: "Cam"), hold=6)
        got = []
        for _ in range(12):
            m = ws.receive_json()
            got.append(m.get("event") or m["type"])
            if "confirmed" in got:
                break
    assert "possible" in got and "confirmed" in got


def test_login_attempts_are_throttled(client):
    client.post("/api/auth/setup", json={"email": "t@t.co", "password": "long-enough-pw"})
    codes = [client.post("/api/auth/login", json={"email": "t@t.co", "password": "bad-password"}).status_code for _ in range(12)]
    assert codes[0] == 401 and codes[-1] == 429
