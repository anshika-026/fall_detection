"""Turns the engine's FallEvents into database incidents, evidence (snapshot +
clip), alerts (webhook / dashboard) and live websocket messages.

Deduplication: the engine keeps ONE state machine per person and hands the same
machine to a replacement track id, so a fall is one incident. The incident id is
stored on that machine (fsm.incident_key). The database additionally refuses
transitions that are not valid from the incident's current state, so a late or
repeated event can never reopen or double-count an incident."""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

import cv2
import httpx

from falldet import config
from falldet.camera import clips
from falldet.core import settings_store
from falldet.event_manager import incidents
from falldet.event_manager.hub import hub
from falldet.fall_analysis.engine import FallEvent

log = logging.getLogger("incident_manager")

_STATE_FOR = {"confirmed": "confirmed", "relapse": "confirmed", "recovered": "recovered",
              "resolved": "resolved", "dismissed": "dismissed", "lost": "resolved"}


def snapshot_dir() -> Path:
    return Path(config.EVIDENCE_DIR) / "snapshots"


def clip_dir() -> Path:
    return Path(config.EVIDENCE_DIR) / "clips"


def _save_snapshot(incident_id: int, frame, bbox, label: str) -> None:
    try:
        img = frame.copy()
        x1, y1, x2, y2 = (int(v) for v in bbox)
        cv2.rectangle(img, (x1, y1), (x2, y2), (40, 40, 230), 3)
        cv2.putText(img, label, (x1, max(18, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 230), 2, cv2.LINE_AA)
        h, w = img.shape[:2]
        if w > 1280:
            img = cv2.resize(img, (1280, round(h * 1280 / w)), interpolation=cv2.INTER_AREA)
        snapshot_dir().mkdir(parents=True, exist_ok=True)
        path = snapshot_dir() / f"{incident_id}.jpg"
        if cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, 85]):
            incidents.set_snapshot(incident_id, str(path))
    except Exception:
        log.exception("incident %s: could not save snapshot", incident_id)


def _post_webhook(url: str, payload: dict) -> None:
    try:
        r = httpx.post(url, json=payload, timeout=5.0)
        if r.status_code >= 400:
            log.warning("alert webhook returned HTTP %s", r.status_code)
    except Exception as e:
        log.warning("alert webhook failed: %s", type(e).__name__)


class IncidentManager:
    def __init__(self, camera_name_of):
        self._camera_name_of = camera_name_of      # callable(camera_id) -> str

    def handle(self, ev: FallEvent, fsm, frame) -> None:
        try:
            self._handle(ev, fsm, frame)
        except Exception:
            log.exception("camera %s: could not record %s event", ev.camera_id, ev.kind)

    def _handle(self, ev: FallEvent, fsm, frame) -> None:
        alerts = settings_store.get("alerts")
        iid = fsm.incident_key
        name = self._camera_name_of(ev.camera_id)

        if ev.kind == "possible":
            iid = incidents.create(ev.camera_id, name, ev.track_id, ev.ts, ev.confidence, ev.metrics)
            fsm.incident_key = iid
            incidents.add_event(iid, ev.ts, "possible", ev.confidence, ev.metrics)
            if alerts["save_snapshot"] and frame is not None:
                _save_snapshot(iid, frame, ev.bbox, f"POSSIBLE FALL {ev.confidence:.0%}")
            log.info("camera %s track %s: possible fall (incident %s)", ev.camera_id, ev.track_id, iid)
            self._publish("incident", iid, ev)
            return

        if iid is None:      # machine restored without an incident (should not happen): open one now
            iid = incidents.create(ev.camera_id, name, ev.track_id, ev.ts, ev.confidence, ev.metrics)
            fsm.incident_key = iid

        new_state = _STATE_FOR[ev.kind]
        ok = incidents.transition(iid, new_state, ev.ts, confidence=ev.confidence if ev.kind == "confirmed" else None,
                                  track_id=ev.track_id, metrics=ev.metrics if ev.kind in ("confirmed", "dismissed") else None,
                                  by="system", reason=ev.reason or ev.kind)
        incidents.add_event(iid, ev.ts, ev.kind if ok else f"{ev.kind}_ignored", ev.confidence,
                            {**ev.metrics, "reason": ev.reason})
        if not ok:
            log.info("incident %s: %s ignored (not valid from its current state)", iid, ev.kind)
            return
        log.info("camera %s track %s: %s (incident %s)", ev.camera_id, ev.track_id, ev.kind, iid)

        if ev.kind == "confirmed":
            if alerts["save_snapshot"] and frame is not None:
                _save_snapshot(iid, frame, ev.bbox, f"FALL CONFIRMED {ev.confidence:.0%}")
            self._schedule_clip(iid, ev, alerts)
            if alerts["enabled"] and ev.confidence >= alerts["min_confidence"]:
                payload = {"event": "fall_confirmed", "incident_id": iid, "camera_id": ev.camera_id, "camera_name": name,
                           "confidence": ev.confidence, "timestamp": ev.ts}
                if alerts["webhook_url"]:
                    threading.Thread(target=_post_webhook, args=(alerts["webhook_url"], payload), daemon=True,
                                     name="alert-webhook").start()
                hub.publish({"type": "alert", **payload, "sound": bool(alerts["sound"])})
            else:
                log.info("incident %s: confidence %.2f below alert threshold %.2f (stored, not alerted)",
                         iid, ev.confidence, alerts["min_confidence"])
        self._publish("incident", iid, ev)

    def _schedule_clip(self, iid: int, ev: FallEvent, alerts: dict) -> None:
        if not alerts["save_clip"] or not clips.recorder.is_wanted(ev.camera_id):
            return
        inc = incidents.get(iid)
        t0 = inc["started_at"] if inc else ev.ts
        final = clip_dir() / str(iid) / f"fall-{iid}.mp4"
        incidents.set_clip(iid, None, "pending")

        def done(status, frames=None, error=None):
            incidents.set_clip(iid, str(final) if status == "ready" else None, "ready" if status == "ready" else "failed")
            if status != "ready":
                log.warning("incident %s: clip not saved: %s", iid, error)
            hub.publish({"type": "clip", "incident_id": iid, "status": status})

        clips.recorder.schedule(ev.camera_id, t0, final, done)

    @staticmethod
    def _publish(kind: str, iid: int, ev: FallEvent) -> None:
        hub.publish({"type": kind, "incident_id": iid, "event": ev.kind, "camera_id": ev.camera_id,
                     "track_id": ev.track_id, "confidence": ev.confidence, "timestamp": ev.ts})
