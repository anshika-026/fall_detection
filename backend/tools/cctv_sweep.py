"""Find which cameras in a list are WORKING, safely: one at a time, ONE login attempt each, and it STOPS at the first rejected login.

  python -m tools.cctv_sweep --cameras ..\\validation\\cameras_office.json
  python -m tools.cctv_sweep --cameras ..\\validation\\cameras_office.json --only "Main Hall 1,Lobby" --json ..\\validation\\results\\sweep1.json

The password is typed at a hidden prompt (getpass): it is never on the command line, in the cameras file, in output or in the JSON.
The cameras file lists names / host / port / path only:
  {"user": "admin", "host": "10.0.0.5", "path": "/video/live?channel=1&subtype=0",
   "cameras": [{"name": "Lobby", "port": 554}, {"name": "Hall", "port": 91, "path": "/other?x=1"}]}

For each camera, in order:
  1. TCP reachability (5 s).
  2. Protocol detection WITHOUT any login: plain RTSP (rtsp://) or RTSP over TLS (rtsps://) or "not RTSP". Credentials are only ever sent to a port that
     answered a real RTSP request, using the scheme it answered with (so a plain-rtsp URL in a spreadsheet is corrected automatically).
  3. ONE authenticated attempt: open, decode frames for a few seconds, report codec / size / measured fps.
Results: WORKING, OPENED-NO-FRAMES, LOGIN-REJECTED, STREAM-PATH-WRONG, NOT-RTSP, UNREACHABLE, OPEN-FAILED, NOT-TRIED.
A 401 stops the sweep (the same account is probably wrong for the rest; trying seven cameras would risk locking it); --keep-going overrides that. Nothing is recorded.
"""
from __future__ import annotations

import argparse
import getpass
import json
import re
import socket
import ssl
import sys
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.cctv_preflight import FAIL, OK, Report, classify_open_error, probe_stream  # noqa: E402
from tools.cctv_record import scrub  # noqa: E402

CR, LF = chr(13), chr(10)


def _options(host: str, port: int, scheme: str) -> bytes:
    return (f"OPTIONS {scheme}://{host}:{port}/ RTSP/1.0" + CR + LF + "CSeq: 1" + CR + LF + CR + LF).encode()


def detect_protocol(host: str, port: int, timeout: float = 6.0) -> tuple[str, str]:
    """-> (protocol, note); protocol in rtsp | rtsps | not_rtsp | unreachable. Sends no credentials."""
    try:
        s = socket.create_connection((host, port), timeout=5)
    except socket.timeout:
        return "unreachable", "no answer in 5 s (offline, or a firewall / another network)"
    except ConnectionRefusedError:
        return "unreachable", "connection refused (nothing listens on that port)"
    except OSError as e:
        return "unreachable", str(e.strerror or e)[:60]
    note = ""
    try:
        s.settimeout(timeout)
        s.sendall(_options(host, port, "rtsp"))
        d = s.recv(200)
        if d.startswith(b"RTSP/"):
            return "rtsp", "plain RTSP"
        note = "plain RTSP request: " + ("reply was not RTSP" if d else "closed without reply")
    except socket.timeout:
        note = "no reply to a plain RTSP request"
    except OSError:
        note = "reset by a plain RTSP request"
    finally:
        s.close()
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE        # we only learn what protocol it speaks; the certificate is not trusted for anything
    try:
        with socket.create_connection((host, port), timeout=5) as raw, ctx.wrap_socket(raw) as t:
            t.settimeout(timeout)
            t.sendall(_options(host, port, "rtsps"))
            d = t.recv(200)
            if d.startswith(b"RTSP/"):
                return "rtsps", "RTSP over TLS"
            return "not_rtsp", note + "; TLS ok but " + ("the reply was not RTSP" if d else "no reply to an RTSP request")
    except (ssl.SSLError, OSError):
        return "not_rtsp", note + "; not TLS either"
    except socket.timeout:
        return "not_rtsp", note + "; TLS ok but no reply"


def check_camera(cam: dict, user: str, password: str, probe_seconds: float) -> dict:
    """One camera. Exactly one authenticated attempt, and only if the port answered RTSP."""
    host, port, path = cam["host"], int(cam["port"]), cam["path"]
    r = {"name": cam["name"], "host": f"{host}:{port}", "result": "", "detail": "", "protocol": None, "codec": None, "size": None, "fps": None}
    proto, note = detect_protocol(host, port)
    r["protocol"] = proto
    if proto == "unreachable":
        r.update(result="UNREACHABLE", detail=note)
        return r
    if proto == "not_rtsp":
        r.update(result="NOT-RTSP", detail=note + ". No login was sent.")
        return r
    url = f"{proto}://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}{path}"
    rep = Report()
    try:
        probe_stream(rep, url, "rtsp", probe_seconds)
    except Exception as e:                                           # never let one camera stop the sweep with a traceback that could echo the URL
        r.update(result="OPEN-FAILED", detail=scrub(f"{type(e).__name__}: {e}", url, password)[:120])
        return r
    c = {x.name: x for x in rep.checks}
    r["codec"], r["fps"] = rep.info.get("codec"), rep.info.get("fps_measured")
    if rep.info.get("width"):
        r["size"] = f"{rep.info['width']}x{rep.info['height']}"
    opened = c.get("RTSP open")
    if opened is None or opened.status == FAIL:
        text = scrub(opened.detail if opened else "no result", url, password)
        low = text.lower()
        if "rejected the login" in low or "403" in low or "refused access" in low:
            r.update(result="LOGIN-REJECTED", detail="the camera answered but rejected the login (wrong user/password, no RTSP permission, or locked)")
        elif "no stream at that path" in low:
            r.update(result="STREAM-PATH-WRONG", detail="the login was accepted but the stream path does not exist on this camera")
        else:
            r.update(result="OPEN-FAILED", detail=text.split("  [FFmpeg")[0][:120])
        return r
    dec = c.get("decoding")
    if dec is not None and dec.status == OK:
        r.update(result="WORKING", detail=f"{r['codec']} {r['size']} at {r['fps']} fps, frames decoded")
    else:
        r.update(result="OPENED-NO-FRAMES", detail=scrub((dec.detail if dec else "no frames decoded"), url, password)[:120])
    return r


def sweep(cams: list[dict], user: str, password: str, probe_seconds: float = 5.0, pause: float = 3.0, only: set[str] | None = None, log=print,
          stop_on_reject: bool = True) -> list[dict]:
    results, stopped = [], False
    todo = [c for c in cams if not only or c["name"] in only]
    for i, cam in enumerate(todo):
        if stopped:
            results.append({"name": cam["name"], "host": f"{cam['host']}:{cam['port']}", "result": "NOT-TRIED", "detail": "sweep stopped after a rejected login", "protocol": None, "codec": None, "size": None, "fps": None})
            continue
        res = check_camera(cam, user, password, probe_seconds)
        results.append(res)
        log(f"{res['name']:<20} {res['host']:<24} {res['result']:<17} {res['detail']}")
        if res["result"] == "LOGIN-REJECTED" and not stop_on_reject:
            log("  -> --keep-going: continuing (each rejected login counts toward a lockout on that camera)")
        if res["result"] == "LOGIN-REJECTED" and stop_on_reject:
            stopped = True
            log("  -> stopping: the login was rejected. Not trying the other cameras (to avoid locking the account). Fix the account first.")
        elif i < len(todo) - 1:
            time.sleep(pause)                                         # a pause between cameras, never after the last one
    return results


def load_cameras(path: Path) -> tuple[list[dict], str]:
    d = json.loads(path.read_text(encoding="utf-8"))

    def has_secret(node) -> bool:
        """A key that names a secret, or a value that looks like a URL with credentials (user:pw@host). Free-text notes are fine."""
        if isinstance(node, dict):
            return any(re.search(r"pass|pwd|secret|token", str(k), re.I) and not str(k).startswith("_") or has_secret(v) for k, v in node.items())
        if isinstance(node, list):
            return any(has_secret(v) for v in node)
        return isinstance(node, str) and bool(re.search(r"://[^/\s:@]+:[^/\s@]+@", node))

    if has_secret(d):
        raise SystemExit("the cameras file must not contain a password or a URL with credentials")
    cams = []
    for c in d.get("cameras", []):
        cams.append({"name": c["name"], "host": c.get("host", d.get("host")), "port": c.get("port", d.get("port")), "path": c.get("path", d.get("path", ""))})
        if not cams[-1]["host"] or not cams[-1]["port"]:
            raise SystemExit(f"camera '{c['name']}' needs a host and a port")
    if not cams:
        raise SystemExit("no cameras in the file")
    return cams, d.get("user", "admin")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cameras", type=Path, required=True)
    ap.add_argument("--user", default=None, help="overrides the user in the file")
    ap.add_argument("--only", default="", help="comma list of camera names to test")
    ap.add_argument("--probe-seconds", type=float, default=5.0)
    ap.add_argument("--pause", type=float, default=3.0, help="seconds between cameras")
    ap.add_argument("--password-env", default=None, help="read the password from this environment variable instead of the hidden prompt (non-interactive use)")
    ap.add_argument("--keep-going", action="store_true", help="do NOT stop at the first rejected login (only if different cameras use different accounts)")
    ap.add_argument("--json", type=Path, default=None, help="write the results (no password, no URL); never overwrites")
    a = ap.parse_args()
    cams, user = load_cameras(a.cameras)
    user = a.user or user
    if a.json and a.json.exists():
        raise SystemExit(f"{a.json} already exists: not overwriting")
    only = {x.strip() for x in a.only.split(",") if x.strip()} or None
    if only and (missing := only - {c["name"] for c in cams}):
        raise SystemExit(f"unknown camera name(s): {sorted(missing)}")
    import os

    password = os.environ.get(a.password_env, "") if a.password_env else getpass.getpass(f"Password for '{user}' (hidden, one login attempt per camera): ")
    if not password:
        raise SystemExit("no password entered")
    print(f"\n{'camera':<20} {'host:port':<24} {'result':<17} detail")
    results = sweep(cams, user, password, a.probe_seconds, a.pause, only, stop_on_reject=not a.keep_going)
    ok = [r["name"] for r in results if r["result"] == "WORKING"]
    print(f"\nWORKING: {', '.join(ok) if ok else 'none'}")
    print("Nothing was recorded. Working cameras can now be preflighted and recorded one at a time.")
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps({"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "user": user, "results": results}, indent=2), encoding="utf-8")
        print("results written:", a.json)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
