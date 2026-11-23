"""Websockets: live JPEG feed, live detection overlay, and the incident event stream.
Each authorises with ?token= (a session token) and re-checks it periodically, so
signing out or an expired session ends the stream."""
from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from falldet import auth, runtime as rt
from falldet.camera import camera_db, camera_stream
from falldet.event_manager.hub import hub

log = logging.getLogger("api.ws")
router = APIRouter()
REAUTH_SECONDS = 30.0


async def _ok(token: str | None) -> bool:
    return await asyncio.to_thread(auth.get_session_user, token) is not None


def _drop_oldest_and_put(q: asyncio.Queue, item: bytes) -> None:
    if q.full():
        try:
            q.get_nowait()
        except asyncio.QueueEmpty:
            pass
    try:
        q.put_nowait(item)
    except asyncio.QueueFull:
        pass


@router.websocket("/ws/live/{camera_id}")
async def ws_live(ws: WebSocket, camera_id: int, token: str | None = None, w: int | None = None):
    await ws.accept()
    if not await _ok(token):
        await ws.close(code=4401)
        return
    cam = camera_db.get_camera(camera_id)
    if not cam or not cam.get("live"):
        await ws.close(code=4403, reason="Feed unavailable")
        return
    loop = asyncio.get_running_loop()
    q: asyncio.Queue = asyncio.Queue(maxsize=2)

    class Sink:
        @staticmethod
        def put_nowait(item):
            loop.call_soon_threadsafe(_drop_oldest_and_put, q, item)

    stream = camera_stream.get_stream(camera_id)
    stream.subscribe(Sink, width=max(320, min(w, 3840)) if w else None)
    next_auth = loop.time() + REAUTH_SECONDS
    try:
        while True:
            try:
                frame = await asyncio.wait_for(q.get(), timeout=REAUTH_SECONDS)
            except asyncio.TimeoutError:
                frame = None
            if loop.time() >= next_auth:
                next_auth = loop.time() + REAUTH_SECONDS
                if not await _ok(token):
                    await ws.close(code=4401)
                    return
            if frame is not None:
                await ws.send_bytes(frame)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        stream.unsubscribe(Sink)


@router.websocket("/ws/detections/{camera_id}")
async def ws_detections(ws: WebSocket, camera_id: int, token: str | None = None):
    """Boxes, fall state and keypoints for the people on one camera (about 5 per second).
    Coordinates are in the camera's full-resolution pixels; frame_w/frame_h let a
    scaled-down viewer place them."""
    await ws.accept()
    if not await _ok(token):
        await ws.close(code=4401)
        return
    loop = asyncio.get_running_loop()
    next_auth = loop.time() + REAUTH_SECONDS
    last_sent, last_sent_at = None, 0.0
    try:
        while True:
            if loop.time() >= next_auth:
                next_auth = loop.time() + REAUTH_SECONDS
                if not await _ok(token):
                    await ws.close(code=4401)
                    return
            lv = rt.runtime.live.get(camera_id)
            # Send the moment a new analysis exists (checked every 40 ms) instead of on a fixed 250 ms beat, so the skeleton
            # is never up to a quarter-second older than it has to be. A heartbeat every second keeps "stale" detection working.
            stamp = lv.updated_at if lv else None
            if stamp == last_sent and loop.time() - last_sent_at < 1.0:
                await asyncio.sleep(0.04)
                continue
            last_sent, last_sent_at = stamp, loop.time()
            info = rt.runtime.camera_runtime(camera_id)
            await ws.send_json({
                "people": lv.people if lv else [],
                "frame_w": lv.frame_wh[0] if lv and lv.frame_wh else None,
                "frame_h": lv.frame_wh[1] if lv and lv.frame_wh else None,
                "updated_at": lv.updated_at if lv else None, "server_time": time.time(),
                "detecting": info["detecting"], "worst_state": info["worst_state"],
                "inference_ms": (info["detection"] or {}).get("inference_ms"),
            })
            await asyncio.sleep(0.04)
    except (WebSocketDisconnect, RuntimeError):
        pass


@router.websocket("/ws/events")
async def ws_events(ws: WebSocket, token: str | None = None):
    """Pushes incident changes and alerts to dashboards the moment they happen."""
    await ws.accept()
    if not await _ok(token):
        await ws.close(code=4401)
        return
    q, entry = hub.subscribe()
    loop = asyncio.get_running_loop()
    next_auth = loop.time() + REAUTH_SECONDS
    try:
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=REAUTH_SECONDS)
            except asyncio.TimeoutError:
                msg = {"type": "ping", "timestamp": time.time()}
            if loop.time() >= next_auth:
                next_auth = loop.time() + REAUTH_SECONDS
                if not await _ok(token):
                    await ws.close(code=4401)
                    return
            await ws.send_json(msg)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        hub.unsubscribe(entry)
