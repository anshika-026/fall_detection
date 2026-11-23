"""Console + rotating-file logging (own log files; never SMC's)."""
from __future__ import annotations

import logging
import logging.handlers
import sys

from falldet import config

_done = False


def setup() -> None:
    global _done
    if _done:
        return
    _done = True
    root = logging.getLogger()
    root.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    if config.LOG_TO_FILE:
        try:
            config.LOG_DIR.mkdir(parents=True, exist_ok=True)
            fh = logging.handlers.RotatingFileHandler(
                config.LOG_DIR / "falldet.log", maxBytes=config.LOG_FILE_MAX_BYTES,
                backupCount=config.LOG_BACKUP_COUNT, encoding="utf-8")
            fh.setFormatter(fmt)
            root.addHandler(fh)
        except OSError:
            logging.getLogger("logging_setup").exception("file logging unavailable; console only")
