"""Runtime and pose-worker tests: camera isolation, skip-when-busy, failure backoff,
and keeping engines/streams in step with the camera table."""
import threading
import time

import numpy as np
import pytest
from synth import FRAME, GROUND, H, Timeline, lerp, lying_kw, stand_kw

from falldet.camera import camera_db, camera_stream, clips
from falldet.core import settings_store
from falldet.detection import pose_worker
from falldet.event_manager import incidents
from falldet.runtime import Runtime

IMG = np.zeros((FRAME[1], FRAME[0], 3), dtype=np.uint8)


class FakeStream:
    def __init__(self):
        self.subscribed, self.unsubscribed = [], []

    def subscribe(self, q, width=None, wants_frames=True):
        self.subscribed.append((q, wants_frames))

    def status(self):
        return {"state": "RUNNING", "last_frame_at": time.time(), "detail": None}

    def unsubscribe(self, q):
        self.unsubscribed.append(q)


@pytest.fixture()
def rt(clean_db, monkeypatch):
    streams: dict[int, FakeStream] = {}
    monkeypatch.setattr(camera_stream, "get_stream", lambda cid: streams.setdefault(cid, FakeStream()))
    monkeypatch.setattr(camera_stream, "existing_stream", lambda cid: streams.get(cid))
    monkeypatch.setattr(camera_stream, "remove_stream", lambda cid, timeout=20.0: streams.pop(cid, None))
    r = Runtime()
    r.streams = streams
    yield r
    clips.recorder.want("falldet", [])


def add_cam(name, **kw):
    return camera_db.add_camera(name, host="10.0.0.1", **kw)


def fall_frames():
    tl = Timeline().hold(4, **stand_kw())
    tl.run(0.5, lambda lt: dict(cx=600, hip_y=lerp(GROUND - 0.5 * H, GROUND - 0.06 * H, lt / 0.5), torso_deg=lerp(2, 88, lt / 0.5)))
    tl.hold(6, **lying_kw())
    return tl.frames


def walk_frames(n):
    tl = Timeline()
    tl.run(n * tl.dt, lambda lt: dict(cx=300 + 200 * lt, hip_y=GROUND - 0.5 * H, torso_deg=2))
    return tl.frames


def test_sync_creates_and_removes_engines_with_cameras(rt):
    a, b = add_cam("A"), add_cam("B", fall_detection_enabled=False)
    rt.sync()
    assert set(rt.engines) == {a}                                   # B has detection off
    assert [wq for _, wq in rt.streams[a].subscribed] == [False]    # keep-alive: no frames encoded for it
    assert b not in rt.streams
    assert clips.recorder.is_wanted(a) and not clips.recorder.is_wanted(b)
    camera_db.update_camera(b, fall_detection_enabled=True)
    camera_db.update_camera(a, fall_detection_enabled=False)
    rt.sync()
    assert set(rt.engines) == {b}
    assert len(rt.streams[a].unsubscribed) == 1                     # A's keep-alive released
    camera_db.update_camera(b, live_feed_enabled=False)             # feed off = nothing runs at all
    rt.sync()
    assert rt.engines == {}


def test_wants_is_zero_for_cameras_without_detection(rt):
    a, b = add_cam("A"), add_cam("B", fall_detection_enabled=False)
    rt.sync()
    assert rt.wants(a) == settings_store.get("processing")["detect_fps"]
    assert rt.wants(b) == 0 and rt.wants(999) == 0


def test_two_cameras_with_the_same_track_id_stay_isolated(rt):
    a, b = add_cam("Ward A"), add_cam("Ward B")
    rt.sync()
    base = time.time() - 30
    from synth import person
    fa, fb = fall_frames(), walk_frames(len(fall_frames()))
    for (ts, pa), (_, pb) in zip(fa, fb):
        rt.deliver(a, IMG, pa, base + ts)          # camera A: person with track id 1 falls
        rt.deliver(b, IMG, pb, base + ts)          # camera B: a different person, ALSO track id 1, walks
    items = incidents.list_incidents()["items"]
    assert [i["camera_id"] for i in items] == [a] and items[0]["state"] == "confirmed"
    assert items[0]["camera_name"] == "Ward A"
    assert {p["state"] for p in rt.live[a].people} == {"CONFIRMED"}
    assert {p["state"] for p in rt.live[b].people} == {"NORMAL"}
    assert rt.camera_runtime(a)["worst_state"] == "CONFIRMED" and rt.camera_runtime(b)["worst_state"] == "NORMAL"
    assert rt.live[a].people[0]["keypoints"] is not None and len(rt.live[a].people[0]["keypoints"]) == 17


def test_deleting_a_camera_drops_its_state(rt):
    a = add_cam("A")
    rt.sync()
    for ts, p in fall_frames()[:30]:
        rt.deliver(a, IMG, p, time.time() - 20 + ts)
    assert a in rt.live
    camera_db.delete_camera(a)
    rt.camera_deleted(a)
    assert a not in rt.engines and a not in rt.live and a not in rt.engine_locks


def test_settings_change_reaches_running_engines(rt):
    a = add_cam("A")
    rt.sync()
    assert rt.engines[a].cfg.confirm_seconds == 3.0
    settings_store.update("detection", {"confirm_seconds": 7})
    rt.sync()
    assert rt.engines[a].cfg.confirm_seconds == 7
    camera_db.update_camera(a, sensitivity="high")
    settings_store.update("detection", {"confirm_seconds": 8})     # bump version
    rt.sync()
    assert rt.engines[a].cfg.min_drop < 0.30                       # per-camera override applied


# ---- pose worker -----------------------------------------------------------------------

class _FakeRes:
    class _T:
        def __init__(self, a): self.a = np.asarray(a)
        def cpu(self): return self
        def numpy(self): return self.a
    def __init__(self, n=2, with_ids=True):
        self.boxes = type("B", (), {})()
        self.boxes.__len__ = lambda s: n
        self.boxes = _Boxes(n, with_ids)
        self.keypoints = type("K", (), {"data": self._T(np.full((n, 17, 3), 0.9))})()


class _Boxes:
    def __init__(self, n, with_ids):
        self.n = n
        self.id = _FakeRes._T([7 + i for i in range(n)]) if with_ids else None
        self.xyxy = _FakeRes._T([[10 * i, 10, 100 + 10 * i, 300] for i in range(n)])
        self.conf = _FakeRes._T([0.9] * n)
    def __len__(self): return self.n


def test_people_conversion_keeps_ids_boxes_and_keypoints():
    people = pose_worker.PoseDetectionService._people(_FakeRes(2))
    assert [p["track_id"] for p in people] == [7, 8]
    assert people[0]["keypoints"].shape == (17, 3) and people[1]["bbox"][0] == 10.0
    assert pose_worker.PoseDetectionService._people(_FakeRes(1, with_ids=False))[0]["track_id"] is None


def test_worker_skips_frames_while_busy_instead_of_queueing(monkeypatch):
    svc = pose_worker.PoseDetectionService()
    svc.register("t", lambda cid: 1000.0, lambda *a: None)         # asks for far more than it can get
    runs, gate = [], threading.Event()

    def slow_run(cam, frame, ts, wanted):
        runs.append(ts)
        gate.wait(2)

    monkeypatch.setattr(svc, "_run", slow_run)
    for _ in range(50):
        svc.feed(1, IMG)
        time.sleep(0.002)
    assert len(runs) == 1                                           # one in flight, the rest skipped
    assert svc._cams[1].frames_skipped_busy > 30
    gate.set()
    time.sleep(0.1)
    svc.shutdown()


def test_worker_isolates_cameras_and_pauses_a_failing_one(monkeypatch):
    svc = pose_worker.PoseDetectionService()
    svc.register("t", lambda cid: 1000.0, lambda *a: None)
    calls = {1: 0, 2: 0}

    class Boom:
        def track(self, *a, **k):
            raise RuntimeError("model exploded")

    class Fine:
        def __init__(self, cid): self.cid = cid
        def track(self, *a, **k):
            calls[self.cid] += 1
            return [_FakeRes(1)]

    svc.feed(1, IMG); svc.feed(2, IMG)
    c1, c2 = svc._cams[1], svc._cams[2]
    assert c1 is not c2 and c1.executor is not c2.executor          # per-camera model/tracker/executor
    c1.model, c2.model = Boom(), Fine(2)
    for _ in range(3):
        c1.last_run = c2.last_run = 0
        svc.feed(1, IMG); svc.feed(2, IMG)
        for c in (c1, c2):
            if c.future is not None:
                c.future.result(timeout=5)
    assert calls[2] >= 2                                            # camera 2 kept analysing
    # camera 1: one real failure, then paused on a backoff (the later feeds were refused, not retried)
    assert c1.health.consecutive_failures == 1
    assert not c1.health.allow()
    st = {x["camera_id"]: x for x in svc.status()}
    assert st[1]["failed"] is True and st[1]["state"] == "DEGRADED"
    assert st[2]["failed"] is False and st[2]["state"] == "RUNNING"
    svc.remove_camera(1)
    assert 1 not in svc._cams and 2 in svc._cams
    svc.shutdown()
