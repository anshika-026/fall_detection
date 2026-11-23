"""Persistent settings, in three groups, stored as JSON in the settings table:

  detection   sensitivity preset + every FallConfig threshold override
  alerts      what happens when a fall is confirmed
  processing  how much work the detector may do (fps, input size, device)

get() always returns defaults merged with what was saved, validated, so a bad or
missing value can never break detection. A small in-process cache with a version
counter lets the running workers notice a change without touching the database
on every frame."""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict

from falldet import config
from falldet.core import db
from falldet.fall_analysis.config import SENSITIVITY, FallConfig

DEFAULTS = {
    "detection": {"sensitivity": "medium", **{k: v for k, v in asdict(FallConfig()).items()}},
    "alerts": {
        "enabled": True,
        "min_confidence": 0.5,          # a confirmed fall below this is stored but does not raise an alert
        "webhook_url": "",              # POSTed a JSON body when a fall is confirmed ("" = off)
        "save_snapshot": True,
        "save_clip": True,
        "sound": True,                  # the dashboard beeps for a new confirmed fall
    },
    "processing": {
        "detect_fps": 5.0,              # pose inference rate per camera (frames are skipped when busy anyway)
        "imgsz": 640,
        "conf": 0.4,                    # detector confidence
    },
}

# (min, max) for numeric values; anything else is rejected
LIMITS = {
    "detection": {"kpt_conf": (0.05, 0.95), "min_person_conf": (0.05, 0.95), "lying_torso_angle": (30, 85),
                  "lying_aspect": (0.5, 3.0), "lying_aspect_strong": (1.0, 4.0), "lying_extent_ratio": (0.1, 0.9), "recovery_torso_angle": (10, 80),
                  "recovery_extent_ratio": (0.2, 1.0), "descent_window": (0.5, 5.0), "min_drop": (0.05, 1.0),
                  "min_velocity": (0.1, 5.0), "min_top_drop": (0.1, 1.5), "min_top_velocity": (0.05, 5.0), "min_angle_swing": (10, 120), "min_angle_rate": (10, 400),
                  "floor_lie_seconds": (0.0, 60.0), "lying_aspect_override": (0.0, 4.0), "floor_lie_min_fraction": (0.3, 1.0), "floor_lie_max_gap_s": (0.2, 1000.0), "upright_lookback": (1.0, 15.0), "upright_extent_ratio": (0.3, 1.0), "confirm_seconds": (0.5, 60.0),
                  "partial_confirm_factor": (1.0, 4.0), "max_motion_rate": (0.05, 3.0), "dismiss_seconds": (0.2, 10.0),
                  "possible_timeout": (2.0, 120.0), "recovery_seconds": (0.5, 30.0), "relapse_seconds": (0.5, 30.0),
                  "auto_resolve_seconds": (5.0, 3600.0), "rearm_seconds": (0.5, 60.0), "track_ttl": (1.0, 60.0),
                  "orphan_after": (0.3, 10.0), "orphan_timeout": (5.0, 900.0), "history_seconds": (3.0, 30.0)},
    "alerts": {"min_confidence": (0.0, 1.0)},
    "processing": {"detect_fps": (0.5, 15.0), "imgsz": (160, 1280), "conf": (0.1, 0.9)},
}

_lock = threading.Lock()
_cache: dict[str, dict] = {}
_version = 0


class SettingsError(ValueError):
    pass


def _clean(group: str, data: dict) -> dict:
    base = DEFAULTS[group]
    out = {}
    for k, v in data.items():
        if k not in base:
            raise SettingsError(f"Unknown setting '{k}' in '{group}'.")
        default = base[k]
        if k == "sensitivity":
            if v not in SENSITIVITY:
                raise SettingsError(f"sensitivity must be one of {sorted(SENSITIVITY)}.")
            out[k] = v
        elif isinstance(default, bool):
            if not isinstance(v, bool):
                raise SettingsError(f"'{k}' must be true or false.")
            out[k] = v
        elif isinstance(default, str):
            if not isinstance(v, str):
                raise SettingsError(f"'{k}' must be text.")
            if k == "webhook_url" and v and not v.lower().startswith(("http://", "https://")):
                raise SettingsError("Webhook URL must start with http:// or https://.")
            out[k] = v.strip()
        else:
            try:
                num = float(v)
            except (TypeError, ValueError):
                raise SettingsError(f"'{k}' must be a number.") from None
            lo, hi = LIMITS.get(group, {}).get(k, (None, None))
            if lo is not None and not (lo <= num <= hi):
                raise SettingsError(f"'{k}' must be between {lo} and {hi}.")
            out[k] = int(num) if isinstance(default, int) else num
    return out


def get(group: str) -> dict:
    with _lock:
        if group in _cache:
            return dict(_cache[group])
    with db.connect(config.DB_PATH) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (group,)).fetchone()
    merged = dict(DEFAULTS[group])
    if row:
        try:
            saved = json.loads(row[0])
            merged.update({k: v for k, v in saved.items() if k in merged})
        except (ValueError, TypeError):
            pass
    with _lock:
        _cache[group] = merged
    return dict(merged)


def update(group: str, data: dict) -> dict:
    global _version
    if group not in DEFAULTS:
        raise SettingsError("Unknown settings group.")
    clean = _clean(group, data)
    merged = {**get(group), **clean}
    with db.connect(config.DB_PATH) as conn:
        conn.execute("INSERT INTO settings(key, value, updated_at) VALUES(?,?,?) "
                     "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                     (group, json.dumps(merged), time.time()))
    with _lock:
        _cache[group] = merged
        _version += 1
    return dict(merged)


def reset(group: str) -> dict:
    global _version
    with db.connect(config.DB_PATH) as conn:
        conn.execute("DELETE FROM settings WHERE key = ?", (group,))
    with _lock:
        _cache.pop(group, None)
        _version += 1
    return get(group)


def version() -> int:
    return _version


def invalidate() -> None:
    global _version
    with _lock:
        _cache.clear()
        _version += 1


def fall_config(camera_sensitivity: str = "") -> FallConfig:
    """The FallConfig the engines should run with (global detection settings, with
    the camera's own sensitivity override applied if it has one)."""
    from falldet.fall_analysis.config import from_settings

    d = get("detection")
    return from_settings({k: v for k, v in d.items() if k != "sensitivity"}, camera_sensitivity or d["sensitivity"])
