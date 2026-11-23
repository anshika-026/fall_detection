import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Isolated state for the whole test session: set BEFORE falldet is imported, because
# falldet.config reads the environment at import. Tests never touch backend/data.
_TMP = tempfile.mkdtemp(prefix="falldet-test-")
atexit.register(shutil.rmtree, _TMP, ignore_errors=True)
os.environ.update({"DATA_DIR": _TMP, "DB_PATH": str(Path(_TMP) / "test.db"), "EVIDENCE_DIR": str(Path(_TMP) / "evidence"),
                   "LOG_TO_FILE": "0", "RUN_DETECTION": "0", "PASSWORD_MIN_LENGTH": "8"})

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402


@pytest.fixture()
def clean_db():
    """A fresh database for tests that need one."""
    from falldet import config
    from falldet.core import schema, settings_store

    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(str(config.DB_PATH) + suffix)
        except FileNotFoundError:
            pass
    schema.init_db()
    settings_store.invalidate()
    yield
