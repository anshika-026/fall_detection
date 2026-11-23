"""Fall Detection backend configuration (environment-driven).

Adapted from SMC backend/app/config.py: same helpers and the same reader /
watchdog / retry constants that the reused camera modules expect, but with only
what this module needs. No SMC licensing, SSO, face or visitor settings.
Everything is overridable with an environment variable (or backend/.env).
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    p = BACKEND_DIR / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def _str(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    return default if raw is None else raw.strip().lower() in ("1", "true", "yes", "on")


def _path(name: str, default: Path) -> Path:
    raw = _str(name)
    return Path(raw) if raw else default


APP_ENV = _str("APP_ENV", "development").lower()
IS_PRODUCTION = APP_ENV == "production"

# 8822/5180 are SMC's, 8821 is MAINDV's: this module must never clash with them.
HOST = _str("HOST", "127.0.0.1")
PORT = _int("PORT", 8830)
CORS_ORIGINS = [o.strip() for o in _str("CORS_ORIGINS", "http://localhost:5190,http://127.0.0.1:5190").split(",") if o.strip()]

DATA_DIR = _path("DATA_DIR", BACKEND_DIR / "data")
DB_PATH = _path("DB_PATH", DATA_DIR / "falldet.db")
MODEL_DIR = _path("MODEL_DIR", BACKEND_DIR / "models")
EVIDENCE_DIR = _path("EVIDENCE_DIR", DATA_DIR / "evidence")

# --- pose model -------------------------------------------------------------
POSE_MODEL = _str("POSE_MODEL", "yolov8n-pose.pt")     # file in MODEL_DIR (auto-downloaded by ultralytics if absent)
RUN_DETECTION = _bool("RUN_DETECTION", True)          # False = API only (tests, frontend work)
POSE_DEVICE = _str("POSE_DEVICE", "")                  # "" = ultralytics default (GPU if available), "cpu", "0"
POSE_TRACKER = _str("POSE_TRACKER", "bytetrack.yaml")  # ultralytics' built-in ByteTrack config (same as SMC)
POSE_THREADS = max(1, _int("POSE_THREADS", 3))         # cores one pose inference may use; the rest stay free for decoding and streaming

# --- streaming (names kept: the reused rtsp_reader / camera modules read them)
LIVE_STREAM_FPS = _float("LIVE_STREAM_FPS", 12.0)      # frames per second handed from the camera reader to the app (live picture + analysis source)
RTSP_CONNECT_TIMEOUT = _float("RTSP_CONNECT_TIMEOUT", 20.0)
RTSP_READ_TIMEOUT = _float("RTSP_READ_TIMEOUT", 10.0)
RTSP_RECONNECT_DELAY = _float("RTSP_RECONNECT_DELAY", 2.0)
RTSP_RECONNECT_MAX_DELAY = _float("RTSP_RECONNECT_MAX_DELAY", 60.0)
RTSP_MAX_RETRIES = _int("RTSP_MAX_RETRIES", 10)
CAMERA_FRAME_TIMEOUT = _float("CAMERA_FRAME_TIMEOUT", 20.0)
CAMERA_WATCHDOG_INTERVAL = _float("CAMERA_WATCHDOG_INTERVAL", 2.0)
FEATURE_RETRY_BASE_SECONDS = _float("FEATURE_RETRY_BASE_SECONDS", 5.0)
FEATURE_RETRY_MAX_SECONDS = _float("FEATURE_RETRY_MAX_SECONDS", 300.0)
FEATURE_REBUILD_AFTER_FAILURES = _int("FEATURE_REBUILD_AFTER_FAILURES", 3)

# RTMP push ingest (only used when a camera's protocol is rtmp_push)
RTMP_APP = _str("RTMP_APP", "live").strip("/")
INGEST_RTSP_BASE = _str("INGEST_RTSP_BASE", "rtsp://127.0.0.1:8554").rstrip("/")
INGEST_READ_USER = _str("INGEST_READ_USER", "falldet-reader")
INGEST_READ_PASSWORD = _str("INGEST_READ_PASSWORD", "")

# --- auth -------------------------------------------------------------------
SESSION_TTL_SECONDS = _int("SESSION_TTL_HOURS", 12) * 3600
PASSWORD_MIN_LENGTH = _int("PASSWORD_MIN_LENGTH", 8)
ADMIN_EMAIL = _str("ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
JWT_SECRET = os.environ.get("JWT_SECRET") or secrets.token_hex(32)

# --- retention / logging ------------------------------------------------------
EVIDENCE_RETENTION_DAYS = _int("EVIDENCE_RETENTION_DAYS", 30)
LOG_LEVEL = _str("LOG_LEVEL", "INFO").upper()
LOG_DIR = _path("LOG_DIR", BACKEND_DIR / "logs")
LOG_TO_FILE = _bool("LOG_TO_FILE", True)
LOG_FILE_MAX_BYTES = _int("LOG_FILE_MAX_MB", 10) * 1024 * 1024
LOG_BACKUP_COUNT = _int("LOG_BACKUP_COUNT", 5)
