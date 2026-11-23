from __future__ import annotations

import logging
import time
from typing import Literal

import cv2
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from falldet import auth, runtime as rt
from falldet.camera import camera_db, camera_stream, rtsp_reader, stream_source

log = logging.getLogger("api.cameras")
router = APIRouter(prefix="/api/cameras", tags=["cameras"], dependencies=[auth.require_user])


class CameraIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    site: str = Field(default="", max_length=100)
    protocol: Literal["rtsp", "rtsps", "rtmp"] = "rtsp"
    host: str = Field(default="", max_length=255)
    port: int = Field(default=554, ge=1, le=65535)
    user: str = Field(default="", max_length=100)
    password: str = Field(default="", max_length=200)
    stream_path: str = Field(default="", max_length=300)
    source_url: str = Field(default="", max_length=600)       # RTMP link
    live_feed_enabled: bool = True
    fall_detection_enabled: bool = True
    sensitivity: Literal["", "low", "medium", "high"] = ""


class CameraUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    site: str | None = Field(default=None, max_length=100)
    protocol: Literal["rtsp", "rtsps", "rtmp"] | None = None
    host: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    user: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, max_length=200)    # None = keep the stored password
    stream_path: str | None = Field(default=None, max_length=300)
    source_url: str | None = Field(default=None, max_length=600)
    live_feed_enabled: bool | None = None
    fall_detection_enabled: bool | None = None
    sensitivity: Literal["", "low", "medium", "high"] | None = None


_CONNECTION_FIELDS = {"protocol", "host", "port", "user", "password", "stream_path", "source_url", "live_feed_enabled"}


def _validate(fields: dict, protocol: str, host: str, source_url: str) -> dict:
    if protocol == "rtmp":
        try:
            fields["source_url"] = stream_source.validate_rtmp_url(source_url)
        except stream_source.SourceError as e:
            raise HTTPException(status_code=422, detail=str(e)) from None
        h, p = stream_source.rtmp_host_port(fields["source_url"])
        fields["host"], fields["port"] = h, p
    else:
        if not host.strip():
            raise HTTPException(status_code=422, detail="Enter the camera's IP address or host name.")
        fields["source_url"] = ""
    return fields


def connection_status(cam: dict, runtime_info: dict) -> str:
    """online | connecting | offline | idle | disabled | not_configured (for the UI badge)."""
    if not cam["is_configured"]:
        return "not_configured"
    if not cam["live_feed_enabled"]:
        return "disabled"
    st = runtime_info.get("stream")
    if st is None:
        return "idle"          # configured, but nothing is streaming it (detection off and nobody watching)
    if st["state"] == "RUNNING" and st["last_frame_at"] and time.time() - st["last_frame_at"] < 15:
        return "online"
    if st["state"] in ("CONNECTING", "RECONNECTING", "STALLED"):
        return "connecting"
    if st["state"] in ("IDLE", "STOPPED"):
        return "idle"
    return "offline"


def _decorate(cam: dict) -> dict:
    info = rt.runtime.camera_runtime(cam["id"])
    cam["runtime"] = info
    cam["connection"] = connection_status(cam, info)
    return cam


@router.get("")
def list_cameras():
    return [_decorate(c) for c in camera_db.list_cameras()]


@router.post("")
def create_camera(payload: CameraIn):
    fields = _validate(payload.model_dump(exclude={"name"}), payload.protocol, payload.host, payload.source_url)
    cid = camera_db.add_camera(payload.name, **fields)
    log.info("camera %s added (%s)", cid, payload.protocol)
    rt.runtime.sync()
    return _decorate(camera_db.get_camera(cid))


class StreamTestIn(BaseModel):
    protocol: Literal["rtsp", "rtsps", "rtmp"] = "rtsp"
    host: str = ""
    port: int = 554
    user: str = ""
    password: str = ""
    stream_path: str = ""
    source_url: str = ""
    camera_id: int | None = None     # reuse a saved camera's stored password when not re-entered


@router.post("/test-stream")
def test_stream(p: StreamTestIn):
    """Opens the stream once and returns a still JPEG (so the form can show that the link works).
    Runs in the threadpool, so a slow camera never blocks others. The address is never echoed back."""
    cam = p.model_dump()
    if p.camera_id is not None:
        saved = camera_db.get_camera_connection(p.camera_id)
        if saved and not p.password:
            cam["password"] = saved.get("password", "")
    if p.protocol == "rtmp":
        try:
            url = stream_source.validate_rtmp_url(p.source_url)
        except stream_source.SourceError as e:
            raise HTTPException(status_code=422, detail=str(e)) from None
    else:
        if not p.host.strip():
            raise HTTPException(status_code=422, detail="Enter the camera's IP address or host name.")
        url = stream_source.build_rtsp_url(cam)
    cap = rtsp_reader.open_capture(url, 8.0, 8.0)
    try:
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Couldn't connect. Check the address, port, username and password.")
        ok, frame = cap.read()
        if not ok or frame is None:
            raise HTTPException(status_code=400, detail="Connected, but the camera sent no video. Check the stream path.")
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    finally:
        cap.release()
    return Response(content=buf.tobytes(), media_type="image/jpeg")


@router.get("/{camera_id}")
def get_camera(camera_id: int):
    cam = camera_db.get_camera(camera_id)
    if cam is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return _decorate(cam)


@router.put("/{camera_id}")
def update_camera(camera_id: int, payload: CameraUpdate):
    existing = camera_db.get_camera_connection(camera_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    fields = payload.model_dump(exclude_unset=True)
    if fields.get("password") is None:
        fields.pop("password", None)
    protocol = fields.get("protocol") or stream_source.protocol_of(existing)
    if _CONNECTION_FIELDS & set(fields) - {"live_feed_enabled"}:
        _validate(fields, protocol, fields.get("host", existing.get("host", "")),
                  fields.get("source_url", existing.get("source_url", "")))
    camera_db.update_camera(camera_id, **fields)
    log.info("camera %s updated: %s", camera_id, sorted(k for k in fields if k != "password"))
    rt.runtime.camera_changed(camera_id, connection_changed=bool(_CONNECTION_FIELDS & set(fields)))
    return _decorate(camera_db.get_camera(camera_id))


@router.delete("/{camera_id}")
def delete_camera(camera_id: int):
    if camera_db.get_camera(camera_id) is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    camera_db.delete_camera(camera_id)
    rt.runtime.camera_deleted(camera_id)
    log.info("camera %s deleted", camera_id)
    return {"ok": True}


@router.get("/{camera_id}/snapshot")
def camera_snapshot(camera_id: int):
    if camera_db.get_camera(camera_id) is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    data = camera_stream.grab_still(camera_id)
    if not data:
        raise HTTPException(status_code=503, detail="No picture from this camera right now.")
    return Response(content=data, media_type="image/jpeg")
