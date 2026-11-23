"""Camera registry (SQLite). Adapted from SMC camera_db.py: same connection
policy, same password/stream-key redaction rules, same is_streamable() contract,
but the SMC-specific columns (attendance, purpose, vendor, cam_code) are replaced
by fall_detection_enabled and a per-camera sensitivity override."""
from __future__ import annotations

import sqlite3

from falldet import config
from falldet.camera import stream_source
from falldet.core import db

DB_PATH = config.DB_PATH

_COLS = ("name", "site", "host", "port", "user", "password", "stream_path", "protocol", "source_url",
         "rtmp_stream_key", "live_feed_enabled", "fall_detection_enabled", "sensitivity")


def get_connection():
    return db.connect(DB_PATH, row_factory=None)


def is_streamable(cam: dict | None) -> bool:
    """Has an address and its feed is switched on."""
    if not cam or not cam.get("live_feed_enabled", 1):
        return False
    proto = stream_source.protocol_of(cam)
    if proto == "rtmp":
        return bool(cam.get("source_url") or cam.get("source_url_set"))
    if proto == stream_source.PUSH_PROTOCOL:
        return bool(cam.get("rtmp_stream_key") or cam.get("rtmp_key_set"))
    return bool(cam.get("host"))


def wants_detection(cam: dict | None) -> bool:
    return bool(cam and is_streamable(cam) and cam.get("fall_detection_enabled", 1))


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["protocol"] = stream_source.protocol_of(d)
    d["is_configured"] = bool(d.get("host") or d.get("source_url") or d.get("rtmp_stream_key"))
    d["live"] = is_streamable(d)
    d["fall_detection_enabled"] = bool(d.get("fall_detection_enabled"))
    d["live_feed_enabled"] = bool(d.get("live_feed_enabled"))
    d.pop("password", None)                       # never sent to the frontend
    d["password_set"] = bool(row["password"])
    source = d.pop("source_url", "") or ""        # the RTMP link carries the key: only a masked form leaves
    d["source_url_set"] = bool(source)
    d["rtmp_key_set"] = bool(d.pop("rtmp_stream_key", None))
    d["source_display"] = stream_source.redact_source(source) if source else ""
    return d


def list_cameras() -> list[dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM cameras ORDER BY id").fetchall()
    return [_row_to_dict(r) for r in rows]


def get_camera(camera_id: int) -> dict | None:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_camera_connection(camera_id: int) -> dict | None:
    """Includes the password and the RTMP link: internal use only."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,)).fetchone()
    return dict(row) if row else None


def add_camera(name: str, **fields) -> int:
    vals = {"site": "", "host": "", "port": 554, "user": "", "password": "", "stream_path": "",
            "protocol": "rtsp", "source_url": "", "rtmp_stream_key": None, "live_feed_enabled": 1,
            "fall_detection_enabled": 1, "sensitivity": ""}
    vals.update({k: v for k, v in fields.items() if k in vals})
    vals["live_feed_enabled"] = int(bool(vals["live_feed_enabled"]))
    vals["fall_detection_enabled"] = int(bool(vals["fall_detection_enabled"]))
    cols = ("name", *vals.keys())
    with get_connection() as conn:
        cur = conn.execute(f"INSERT INTO cameras ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                           (name, *vals.values()))
        return cur.lastrowid


def update_camera(camera_id: int, **fields) -> None:
    fields = {k: v for k, v in fields.items() if k in _COLS}
    for k in ("live_feed_enabled", "fall_detection_enabled"):
        if k in fields:
            fields[k] = int(bool(fields[k]))
    if not fields:
        return
    columns = ", ".join(f"{k} = ?" for k in fields)
    with get_connection() as conn:
        conn.execute(f"UPDATE cameras SET {columns} WHERE id = ?", (*fields.values(), camera_id))


def get_camera_by_stream_key(key: str) -> dict | None:
    if not stream_source.is_stream_key(key):
        return None
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM cameras WHERE rtmp_stream_key = ? AND protocol = ?",
                           (key, stream_source.PUSH_PROTOCOL)).fetchone()
    return dict(row) if row else None


def set_stream_key(camera_id: int, key: str | None) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE cameras SET rtmp_stream_key = ? WHERE id = ?", (key, camera_id))


def delete_camera(camera_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
