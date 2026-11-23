"""Download the pose weights into backend/models/ and print their SHA-256.
   python -m tools.fetch_models [yolov8n-pose.pt ...]

Weights come from the Ultralytics assets release. Pin the checksum you verified in
your own deployment (docs/DEPENDENCIES.md lists the one this module was tested with)."""
from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

BASE = "https://github.com/ultralytics/assets/releases/download/v8.3.0/"
MODELS = Path(__file__).resolve().parent.parent / "models"
KNOWN = {"yolov8n-pose.pt": "c6fa93dd1ee4a2c18c900a45c1d864a1c6f7aba75d84f91648a30b7fb641d212"}


def main() -> int:
    names = sys.argv[1:] or ["yolov8n-pose.pt"]
    MODELS.mkdir(parents=True, exist_ok=True)
    rc = 0
    for name in names:
        if "/" in name or "\\" in name or not name.endswith(".pt"):
            print(f"refusing odd file name: {name}")
            rc = 1
            continue
        dest = MODELS / name
        if not dest.exists():
            print(f"downloading {name} ...")
            urllib.request.urlretrieve(BASE + name, dest)
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        known = KNOWN.get(name)
        status = "matches the tested file" if known == digest else ("DIFFERS from the tested file!" if known else "no pinned checksum for this model")
        print(f"{name}: sha256={digest} ({status})")
        if known and known != digest:
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
