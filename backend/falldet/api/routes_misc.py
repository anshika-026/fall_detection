"""Dashboard, analytics, settings and system status."""
from __future__ import annotations

import os
import time

import psutil
from fastapi import APIRouter, Body, HTTPException, Query

from falldet import auth, config, runtime as rt
from falldet.api.routes_cameras import connection_status
from falldet.camera import camera_db, camera_stream
from falldet.core import resilience, settings_store
from falldet.detection import pose_worker
from falldet.event_manager import incidents
from falldet.event_manager.hub import hub

router = APIRouter(prefix="/api", tags=["dashboard"], dependencies=[auth.require_user])
public = APIRouter(tags=["health"])
_started = time.time()


@router.get("/dashboard")
def dashboard(recent: int = Query(15, ge=1, le=50)):
    cams = camera_db.list_cameras()
    conn: dict[str, int] = {}
    for c in cams:
        s = connection_status(c, rt.runtime.camera_runtime(c["id"]))
        conn[s] = conn.get(s, 0) + 1
    active = incidents.list_incidents("active", limit=10)["items"]
    return {"summary": incidents.summary(),
            "active_incidents": active,
            "recent_activity": incidents.recent_activity(recent),
            "cameras": {"total": len(cams), "detecting": sum(1 for c in cams if c["fall_detection_enabled"] and c["live"]),
                        "by_connection": conn}}


@router.get("/analytics")
def analytics(days: int = Query(30, ge=1, le=365), camera_id: int | None = None):
    return incidents.analytics(days, camera_id)


# --- settings ------------------------------------------------------------------------------
@router.get("/settings")
def get_settings():
    return {g: settings_store.get(g) for g in settings_store.DEFAULTS} | {"defaults": settings_store.DEFAULTS}


@router.put("/settings/{group}")
def put_settings(group: str, data: dict = Body(...)):
    if group not in settings_store.DEFAULTS:
        raise HTTPException(status_code=404, detail="Unknown settings group")
    try:
        saved = settings_store.update(group, data)
    except settings_store.SettingsError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    rt.runtime.sync()      # engines pick the new thresholds up now, not at the next 5 s tick
    return saved


@router.post("/settings/{group}/reset")
def reset_settings(group: str):
    if group not in settings_store.DEFAULTS:
        raise HTTPException(status_code=404, detail="Unknown settings group")
    saved = settings_store.reset(group)
    rt.runtime.sync()
    return saved


# --- system ------------------------------------------------------------------------------------
@router.get("/system")
def system():
    p = psutil.Process(os.getpid())
    return {"uptime_seconds": round(time.time() - _started), "pid": p.pid,
            "process_cpu_percent": p.cpu_percent(interval=None), "process_rss_mb": round(p.memory_info().rss / 1e6, 1),
            "system_cpu_percent": psutil.cpu_percent(interval=None), "system_memory_percent": psutil.virtual_memory().percent,
            "model": config.POSE_MODEL, "device": config.POSE_DEVICE or "auto",
            "detection": pose_worker.service.status(), "streams": camera_stream.all_status(),
            "health": resilience.all_health(), "ws_subscribers": hub.subscribers}


@public.get("/health")
def health():
    return {"ok": True}


@public.get("/ready")
def ready():
    from falldet.core import db

    ok, why = db.check(config.DB_PATH)
    if not ok:
        raise HTTPException(status_code=503, detail=why)
    return {"ok": True}
