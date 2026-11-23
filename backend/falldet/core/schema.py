"""The module's own SQLite schema (falldet.db). Nothing here touches SMC's database."""
from __future__ import annotations

import logging

from falldet import config
from falldet.core import db

log = logging.getLogger("schema")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cameras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    site TEXT NOT NULL DEFAULT '',
    host TEXT DEFAULT '',
    port INTEGER DEFAULT 554,
    user TEXT DEFAULT '',
    password TEXT DEFAULT '',
    stream_path TEXT DEFAULT '',
    protocol TEXT DEFAULT 'rtsp',
    source_url TEXT DEFAULT '',
    rtmp_stream_key TEXT,
    live_feed_enabled INTEGER DEFAULT 1,
    fall_detection_enabled INTEGER DEFAULT 1,
    sensitivity TEXT DEFAULT '',          -- '' = use the global setting
    created_at REAL DEFAULT (strftime('%s','now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_cameras_stream_key ON cameras(rtmp_stream_key) WHERE rtmp_stream_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT DEFAULT '',
    password_hash TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at REAL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL
);

-- One row per fall incident. state: possible | confirmed | recovered | resolved | dismissed.
-- A "fall incident" for statistics means confirmed_at IS NOT NULL (dismissed ones were
-- never confirmed; they are kept so false positives can be measured).
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id INTEGER NOT NULL,
    camera_name TEXT DEFAULT '',
    track_id INTEGER,
    state TEXT NOT NULL,
    started_at REAL NOT NULL,
    confirmed_at REAL,
    recovered_at REAL,
    resolved_at REAL,
    resolved_by TEXT,
    resolve_reason TEXT,
    acknowledged_at REAL,
    acknowledged_by TEXT,
    confidence REAL DEFAULT 0,
    peak_confidence REAL DEFAULT 0,
    metrics TEXT DEFAULT '{}',
    snapshot_path TEXT,
    clip_path TEXT,
    clip_status TEXT
);
CREATE INDEX IF NOT EXISTS ix_incidents_camera ON incidents(camera_id, started_at);
CREATE INDEX IF NOT EXISTS ix_incidents_confirmed ON incidents(confirmed_at);
CREATE INDEX IF NOT EXISTS ix_incidents_state ON incidents(state);

CREATE TABLE IF NOT EXISTS incident_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    confidence REAL DEFAULT 0,
    details TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_incident_events ON incident_events(incident_id, ts);
"""


def init_db(path=None) -> None:
    with db.connect(path or config.DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
    log.info("database ready at %s", path or config.DB_PATH)
