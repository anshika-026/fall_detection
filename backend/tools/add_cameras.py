"""Add the cameras listed in a cameras file (names / host / port / path, NO password) to the Fall Detection app's own database.

  python -m tools.add_cameras --cameras ..\\validation\\cameras_office.json --enable "Main Hall 1"
  python -m tools.add_cameras --cameras ..\\validation\\cameras_office.json --password-env CAM_PW --enable "Main Hall 1" --dry-run

The password is typed at a hidden prompt (or read from an environment variable) and written ONLY into the app's database, as the
app's Camera Management form would (stored as typed in backend/data, which is git-ignored; see docs/LIMITATIONS.md). It is never printed.
Safe by design:
  * a camera whose NAME already exists is skipped, never overwritten or duplicated;
  * only the cameras named in --enable get live view + fall detection switched ON. The others are added switched OFF so that a
    laptop is not asked to decode and analyse seven 1080p streams at once; switch them on one at a time in Camera Management;
  * --dry-run shows what would be added and changes nothing.
The running backend notices new cameras within a few seconds (it re-reads the camera list every 5 s); no restart is needed.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from falldet.camera import camera_db  # noqa: E402
from falldet.core import schema  # noqa: E402
from tools.cctv_sweep import load_cameras  # noqa: E402


def plan(cams: list[dict], user: str, existing_names: set[str], enable: set[str], protocol: str) -> list[dict]:
    rows = []
    for c in cams:
        on = c["name"] in enable
        rows.append({"name": c["name"], "action": "skip (name already exists)" if c["name"] in existing_names else "add",
                     "fields": {"protocol": protocol, "host": c["host"], "port": int(c["port"]), "user": user, "stream_path": c["path"],
                                "live_feed_enabled": on, "fall_detection_enabled": on}})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cameras", type=Path, required=True)
    ap.add_argument("--enable", default="", help="comma list of camera names to switch ON (live view + fall detection); the rest are added OFF")
    ap.add_argument("--protocol", default="rtsps", choices=("rtsp", "rtsps"))
    ap.add_argument("--password-env", default=None, help="read the password from this environment variable instead of the hidden prompt")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cams, user = load_cameras(a.cameras)
    enable = {x.strip() for x in a.enable.split(",") if x.strip()}
    if missing := enable - {c["name"] for c in cams}:
        raise SystemExit(f"--enable names not in the cameras file: {sorted(missing)}")
    schema.init_db()
    existing = {c["name"] for c in camera_db.list_cameras()}
    rows = plan(cams, user, existing, enable, a.protocol)
    password = ""
    if not a.dry_run and any(r["action"] == "add" for r in rows):
        password = os.environ.get(a.password_env, "") if a.password_env else getpass.getpass(f"Password for '{user}' (hidden; stored only in the app's database): ")
        if not password:
            raise SystemExit("no password entered")
    print(f"{'camera':<20} {'host:port':<24} {'protocol':<7} {'live+detect':<12} action")
    added = 0
    for r in rows:
        f = r["fields"]
        print(f"{r['name']:<20} {f['host'] + ':' + str(f['port']):<24} {f['protocol']:<7} {'ON' if f['live_feed_enabled'] else 'off':<12} {r['action'] if not a.dry_run else 'would ' + r['action']}")
        if r["action"] == "add" and not a.dry_run:
            camera_db.add_camera(r["name"], password=password, **f)
            added += 1
    print(f"\n{added} camera(s) added." if not a.dry_run else "\ndry run: nothing was changed.")
    if added:
        print("The running backend picks them up within ~5 seconds. Only the cameras marked ON are streamed and analysed.")


if __name__ == "__main__":
    main()
