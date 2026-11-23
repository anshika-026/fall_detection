from __future__ import annotations

import re
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from falldet import auth, config, runtime as rt
from falldet.event_manager import incidents

router = APIRouter(prefix="/api", tags=["incidents"], dependencies=[auth.require_user])

STATES = {"possible", "confirmed", "recovered", "resolved", "dismissed", "active"}


def _who(user: dict) -> str:
    return user.get("email") or "operator"


@router.get("/incidents")
def list_incidents(state: str | None = None, camera_id: int | None = None, since: float | None = None,
                   until: float | None = None, include_unconfirmed: bool = False,
                   limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    if state is not None and state not in STATES:
        raise HTTPException(status_code=422, detail=f"state must be one of {sorted(STATES)}")
    return incidents.list_incidents(state, camera_id, since, until, confirmed_only=not include_unconfirmed,
                                    limit=limit, offset=offset)


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: int):
    inc = incidents.get(incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    inc["events"] = incidents.events(incident_id)
    return inc


@router.post("/incidents/{incident_id}/acknowledge")
def acknowledge(incident_id: int, user: dict = Depends(auth.current_user)):
    if incidents.get(incident_id) is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    ok = incidents.acknowledge(incident_id, _who(user))
    if ok:
        incidents.add_event(incident_id, time.time(), "acknowledged", 0, {"by": _who(user)})
    return {"ok": ok}


class ResolveIn(BaseModel):
    reason: str


@router.post("/incidents/{incident_id}/resolve")
def resolve(incident_id: int, payload: ResolveIn, user: dict = Depends(auth.current_user)):
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Pick a reason for resolving.")
    inc = incidents.get(incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    ok = incidents.resolve(incident_id, _who(user), reason)
    if ok:
        incidents.add_event(incident_id, time.time(), "resolved_by_operator", 0, {"by": _who(user), "reason": reason})
        # tell the engine so a person still on the floor is not alerted about again
        rt.runtime.resolve_in_engine(inc["camera_id"], inc.get("track_id"))
    return {"ok": ok}


def _safe(path_str: str | None) -> Path | None:
    """Only ever serve files inside the evidence folder."""
    if not path_str:
        return None
    p = Path(path_str).resolve()
    root = Path(config.EVIDENCE_DIR).resolve()
    return p if root in p.parents and p.is_file() else None


@router.get("/incidents/{incident_id}/snapshot")
def snapshot(incident_id: int):
    info = incidents.paths(incident_id)
    p = _safe(info and info["snapshot_path"])
    if p is None:
        raise HTTPException(status_code=404, detail="No snapshot for this incident")
    return FileResponse(p, media_type="image/jpeg")


@router.get("/incidents/{incident_id}/clip")
def clip(incident_id: int, download: bool = False):
    info = incidents.paths(incident_id)
    if info is None or info["clip_status"] is None:
        raise HTTPException(status_code=404, detail="No clip for this incident")
    if info["clip_status"] == "pending":
        raise HTTPException(status_code=409, detail="The clip is still being prepared. Try again in a few seconds.")
    p = _safe(info["clip_path"]) if info["clip_status"] == "ready" else None
    if p is None:
        raise HTTPException(status_code=404, detail="The clip is not available (no video was captured, or it expired).")
    if not download:
        return FileResponse(p, media_type="video/mp4")
    return FileResponse(p, media_type="video/mp4", filename=re.sub(r"[^A-Za-z0-9.-]+", "-", p.name),
                        content_disposition_type="attachment")
