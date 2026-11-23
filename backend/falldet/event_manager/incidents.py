"""Incident storage, lifecycle transitions and analytics queries.

Every number the dashboard and analytics pages show is computed here by SQL over
the incidents table (real detections only). There is no seed data and no
hard-coded figures; an empty database yields zeros and empty series.

What counts as a "fall incident": a row whose confirmed_at is set. 'possible'
rows are falls under review; 'dismissed' rows were never confirmed (kept so the
false-alarm rate can be measured)."""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timedelta

from falldet import config
from falldet.core import db

ACTIVE = ("confirmed", "recovered")
OPEN_STATES = ("possible", "confirmed", "recovered")

# state -> states it may move to (guards against late/duplicate events overwriting a closed incident)
_ALLOWED_FROM = {
    "confirmed": ("possible", "recovered"),     # recovered -> confirmed is a relapse
    "recovered": ("confirmed",),
    "resolved": ("possible", "confirmed", "recovered"),
    "dismissed": ("possible",),
}


def _conn():
    return db.connect(config.DB_PATH, row_factory=sqlite3.Row)


def _row(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    try:
        d["metrics"] = json.loads(d.get("metrics") or "{}")
    except ValueError:
        d["metrics"] = {}
    d["has_snapshot"] = bool(d.pop("snapshot_path", None))
    d["has_clip"] = d.get("clip_status") == "ready"
    d.pop("clip_path", None)
    return d


# --- writes -----------------------------------------------------------------------------

def create(camera_id: int, camera_name: str, track_id: int, ts: float, confidence: float, metrics: dict) -> int:
    with _conn() as c:
        cur = c.execute("INSERT INTO incidents(camera_id, camera_name, track_id, state, started_at, confidence, "
                        "peak_confidence, metrics) VALUES(?,?,?,?,?,?,?,?)",
                        (camera_id, camera_name, track_id, "possible", ts, confidence, confidence, json.dumps(metrics)))
        return cur.lastrowid


def add_event(incident_id: int, ts: float, kind: str, confidence: float, details: dict | None = None) -> None:
    with _conn() as c:
        c.execute("INSERT INTO incident_events(incident_id, ts, kind, confidence, details) VALUES(?,?,?,?,?)",
                  (incident_id, ts, kind, confidence, json.dumps(details or {})))


def transition(incident_id: int, new_state: str, ts: float, confidence: float | None = None, track_id: int | None = None,
               metrics: dict | None = None, by: str | None = None, reason: str | None = None) -> bool:
    """Move an incident to new_state if that move is allowed from its current state.
    Returns False (and changes nothing) for a stale or duplicate transition."""
    allowed = _ALLOWED_FROM[new_state]
    sets, args = ["state = ?"], [new_state]
    if new_state == "confirmed":
        sets.append("confirmed_at = COALESCE(confirmed_at, ?)")
        args.append(ts)
    elif new_state == "recovered":
        sets.append("recovered_at = ?")
        args.append(ts)
    elif new_state == "resolved":
        sets += ["resolved_at = ?", "resolved_by = ?", "resolve_reason = ?"]
        args += [ts, by or "system", reason or ""]
    if confidence is not None:
        sets += ["confidence = ?", "peak_confidence = MAX(peak_confidence, ?)"]
        args += [confidence, confidence]
    if track_id is not None:
        sets.append("track_id = ?")
        args.append(track_id)
    if metrics is not None:
        sets.append("metrics = ?")
        args.append(json.dumps(metrics))
    with _conn() as c:
        cur = c.execute(f"UPDATE incidents SET {', '.join(sets)} WHERE id = ? AND state IN ({','.join('?' * len(allowed))})",
                        (*args, incident_id, *allowed))
        return cur.rowcount == 1


def set_snapshot(incident_id: int, path: str) -> None:
    with _conn() as c:
        c.execute("UPDATE incidents SET snapshot_path = ? WHERE id = ?", (path, incident_id))


def set_clip(incident_id: int, path: str | None, status: str) -> None:
    with _conn() as c:
        c.execute("UPDATE incidents SET clip_path = ?, clip_status = ? WHERE id = ?", (path, status, incident_id))


def acknowledge(incident_id: int, by: str) -> bool:
    with _conn() as c:
        cur = c.execute("UPDATE incidents SET acknowledged_at = ?, acknowledged_by = ? WHERE id = ? "
                        "AND acknowledged_at IS NULL AND state IN ('confirmed','recovered')", (time.time(), by, incident_id))
        return cur.rowcount == 1


def resolve(incident_id: int, by: str, reason: str) -> bool:
    return transition(incident_id, "resolved", time.time(), by=by, reason=reason)


def close_stale_on_startup() -> int:
    """After a restart no engine is tracking anyone: a 'possible' incident can never be
    confirmed, so dismiss it. Confirmed/recovered ones stay open for an operator."""
    with _conn() as c:
        cur = c.execute("UPDATE incidents SET state='dismissed' WHERE state='possible'")
        return cur.rowcount


# --- reads -------------------------------------------------------------------------------

def get(incident_id: int) -> dict | None:
    with _conn() as c:
        return _row(c.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone())


def paths(incident_id: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT snapshot_path, clip_path, clip_status FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    return dict(r) if r else None


def events(incident_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT ts, kind, confidence, details FROM incident_events WHERE incident_id = ? ORDER BY ts, id",
                         (incident_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["details"] = json.loads(d["details"] or "{}")
        except ValueError:
            d["details"] = {}
        out.append(d)
    return out


def list_incidents(state: str | None = None, camera_id: int | None = None, since: float | None = None,
                   until: float | None = None, confirmed_only: bool = True, limit: int = 100, offset: int = 0) -> dict:
    where, args = [], []
    if state == "active":
        where.append("state IN ('confirmed','recovered')")
    elif state:
        where.append("state = ?")
        args.append(state)
    if confirmed_only and state not in ("possible", "dismissed"):
        where.append("confirmed_at IS NOT NULL")
    if camera_id is not None:
        where.append("camera_id = ?")
        args.append(camera_id)
    if since is not None:
        where.append("started_at >= ?")
        args.append(since)
    if until is not None:
        where.append("started_at <= ?")
        args.append(until)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    limit = max(1, min(int(limit), 500))
    with _conn() as c:
        total = c.execute(f"SELECT COUNT(*) FROM incidents {w}", args).fetchone()[0]
        rows = c.execute(f"SELECT * FROM incidents {w} ORDER BY started_at DESC LIMIT ? OFFSET ?",
                         (*args, limit, max(0, int(offset)))).fetchall()
    return {"total": total, "items": [_row(r) for r in rows]}


def _day_start(ts: float | None = None) -> float:
    d = datetime.fromtimestamp(ts or time.time())
    return d.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def summary() -> dict:
    with _conn() as c:
        r = c.execute("""
            SELECT
              COALESCE(SUM(confirmed_at IS NOT NULL), 0)                                  AS total,
              COALESCE(SUM(state IN ('confirmed','recovered')), 0)                         AS active,
              COALESCE(SUM(state = 'resolved' AND confirmed_at IS NOT NULL), 0)            AS resolved,
              COALESCE(SUM(state = 'possible'), 0)                                         AS possible,
              COALESCE(SUM(state = 'dismissed'), 0)                                        AS dismissed,
              COALESCE(SUM(state = 'confirmed' AND acknowledged_at IS NULL), 0)            AS unacknowledged,
              COALESCE(SUM(confirmed_at >= ?), 0)                                          AS today
            FROM incidents""", (_day_start(),)).fetchone()
    return {k: int(r[k]) for k in r.keys()}


def recent_activity(limit: int = 20) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""SELECT e.id, e.ts, e.kind, e.confidence, e.incident_id, i.camera_id, i.camera_name, i.state
                            FROM incident_events e JOIN incidents i ON i.id = e.incident_id
                            ORDER BY e.ts DESC, e.id DESC LIMIT ?""", (max(1, min(limit, 100)),)).fetchall()
    return [dict(r) for r in rows]


def analytics(days: int = 30, camera_id: int | None = None) -> dict:
    """Real-data analytics over confirmed falls in the last `days` days (local time)."""
    days = max(1, min(int(days), 365))
    start = _day_start() - (days - 1) * 86400
    cam = " AND camera_id = ?" if camera_id is not None else ""
    base = (start, camera_id) if camera_id is not None else (start,)
    q = f"FROM incidents WHERE confirmed_at IS NOT NULL AND confirmed_at >= ?{cam}"
    with _conn() as c:
        total = c.execute(f"SELECT COUNT(*) {q}", base).fetchone()[0]
        by_cam = [dict(r) for r in c.execute(
            f"SELECT camera_id, camera_name, COUNT(*) AS falls, ROUND(AVG(confidence),3) AS avg_confidence {q} "
            "GROUP BY camera_id ORDER BY falls DESC", base)]
        daily_raw = {r[0]: r[1] for r in c.execute(
            f"SELECT strftime('%Y-%m-%d', confirmed_at,'unixepoch','localtime') d, COUNT(*) {q} GROUP BY d", base)}
        hourly_raw = {r[0]: r[1] for r in c.execute(
            f"SELECT CAST(strftime('%H', confirmed_at,'unixepoch','localtime') AS INTEGER) h, COUNT(*) {q} GROUP BY h", base)}
        dow_raw = {r[0]: r[1] for r in c.execute(
            f"SELECT CAST(strftime('%w', confirmed_at,'unixepoch','localtime') AS INTEGER) w, COUNT(*) {q} GROUP BY w", base)}
        conf = c.execute(f"SELECT AVG(confidence), MIN(confidence), MAX(confidence) {q}", base).fetchone()
        buckets = {"0.5-0.6": 0, "0.6-0.7": 0, "0.7-0.8": 0, "0.8-0.9": 0, "0.9-1.0": 0, "<0.5": 0}
        for (v,) in c.execute(f"SELECT confidence {q}", base):
            if v < 0.5:
                buckets["<0.5"] += 1
            else:
                lo = min(int(v * 10), 9)
                buckets[f"0.{lo}-0.{lo + 1}" if lo < 9 else "0.9-1.0"] += 1
        rt = c.execute(f"SELECT AVG(acknowledged_at - confirmed_at), AVG(resolved_at - confirmed_at) {q} "
                       "AND acknowledged_at IS NOT NULL", base).fetchone()
        dismissed = c.execute("SELECT COUNT(*) FROM incidents WHERE state='dismissed' AND started_at >= ?"
                              + cam, base).fetchone()[0]
        history = [dict(r) for r in c.execute(
            f"SELECT id, camera_id, camera_name, state, started_at, confirmed_at, recovered_at, resolved_at, "
            f"resolve_reason, confidence {q} ORDER BY confirmed_at DESC LIMIT 200", base)]
    day_list = [(datetime.fromtimestamp(start) + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    daily = [{"date": d, "falls": daily_raw.get(d, 0)} for d in day_list]
    weeks: dict[str, int] = {}
    for item in daily:
        dt = datetime.strptime(item["date"], "%Y-%m-%d")
        monday = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
        weeks[monday] = weeks.get(monday, 0) + item["falls"]
    return {
        "days": days, "camera_id": camera_id, "total_falls": total,
        "by_camera": by_cam, "daily": daily,
        "weekly": [{"week_start": k, "falls": v} for k, v in weeks.items()],
        "by_hour": [{"hour": h, "falls": hourly_raw.get(h, 0)} for h in range(24)],
        "by_weekday": [{"weekday": w, "falls": dow_raw.get(w, 0)} for w in range(7)],   # 0 = Sunday
        "confidence": {"avg": None if conf[0] is None else round(conf[0], 3),
                       "min": conf[1], "max": conf[2], "distribution": [{"bucket": k, "falls": v} for k, v in buckets.items()]},
        "avg_seconds_to_acknowledge": None if rt[0] is None else round(rt[0], 1),
        "avg_seconds_to_resolve": None if rt[1] is None else round(rt[1], 1),
        "dismissed_possible_falls": dismissed,
        "history": history,
    }
