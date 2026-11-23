"""
stream_source.py

Which protocol a camera is read over (RTSP or RTMP), and everything about its
source address that must not depend on a database or a running stream:
validation, building the URL the reader opens, and a redacted form that is safe
to show or log.

RTMP cameras are read by exactly the same decoder as RTSP cameras
(rtsp_reader.py: one FFmpeg-backed capture per camera, newest frame kept in
shared memory), so playback in the browser and every AI consumer (person
detection, face recognition, tracking, footfall, staff count, visitors) share
that single decode. That is why there is no separate HLS relay here: a second
FFmpeg process decoding the same stream just for the browser would double the
CPU cost and would show video without SMC's AI overlay.

An RTMP address is a secret (the stream key is part of the path), so it is kept
in the database column `source_url`, never returned by the camera API and never
logged; only `redact_source()` output leaves the backend.
"""

from __future__ import annotations

import re
import secrets
from urllib.parse import quote, urlsplit

# rtsp       - SMC pulls from the camera (host/port/user/password/path)
# rtmp       - SMC pulls from an RTMP link (source_url)
# rtmp_push  - the camera publishes to SMC's ingest server with a generated key
PROTOCOLS = ("rtsp", "rtsps", "rtmp", "rtmp_push")   # rtsps = RTSP over TLS (many IP cameras only accept this)
PUSH_PROTOCOL = "rtmp_push"
# Non-secret marker stored as a push camera's host, so every existing "is this
# camera configured" check (which looks for a host) treats it as configured.
PUSH_HOST = "rtmp-push"
# secrets.token_urlsafe(24): 192 random bits, 32 URL/path-safe characters.
STREAM_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{32}$")
DEFAULT_PROTOCOL = "rtsp"
RTMP_SCHEMES = ("rtmp", "rtmps")
DEFAULT_RTMP_PORT = 1935
MAX_URL_LENGTH = 2048

# Whitespace/control characters, quotes, angle brackets, backticks and
# backslashes never belong in a stream address (they would only ever come from a
# paste mistake). The URL is handed to FFmpeg as one argument - never through a
# shell - but an obviously mangled address should be rejected up front.
_BAD_CHARS = re.compile(r"[\s\x00-\x1f\x7f\"'<>`\\]")


class SourceError(ValueError):
    """A source address or protocol that cannot be used. The message is safe to
    show to the user: it never contains the address that was entered."""


def normalize_protocol(value: str | None) -> str:
    """'rtsp' / 'rtmp' (any case); empty or None means the default, RTSP."""
    if value is None or not str(value).strip():
        return DEFAULT_PROTOCOL
    p = str(value).strip().lower()
    if p not in PROTOCOLS:
        raise SourceError(f"Unsupported camera protocol. Use one of: {', '.join(PROTOCOLS)}.")
    return p


def protocol_of(cam: dict | None) -> str:
    """The protocol of a camera row; rows from before the column existed are RTSP."""
    if not cam:
        return DEFAULT_PROTOCOL
    p = str(cam.get("protocol") or DEFAULT_PROTOCOL).strip().lower()
    return p if p in PROTOCOLS else DEFAULT_PROTOCOL


def validate_rtmp_url(url: str | None) -> str:
    """The RTMP address as it will be stored, or SourceError."""
    url = (url or "").strip()
    if not url:
        raise SourceError("Enter the RTMP link, for example rtmp://host/app/stream-key.")
    if len(url) > MAX_URL_LENGTH:
        raise SourceError("The RTMP link is too long.")
    if _BAD_CHARS.search(url):
        raise SourceError("The RTMP link contains spaces or characters that are not allowed.")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise SourceError("The RTMP link is not a valid address (check the port number).") from None
    if parts.scheme.lower() not in RTMP_SCHEMES:
        raise SourceError("The link must start with rtmp:// (or rtmps://).")
    if not parts.hostname:
        raise SourceError("The RTMP link has no server address after rtmp://.")
    if port is not None and not (1 <= port <= 65535):
        raise SourceError("The RTMP port must be between 1 and 65535.")
    if not parts.path.strip("/"):
        raise SourceError("The RTMP link needs the application name after the address, "
                          "for example rtmp://host/live/stream-key.")
    return url


def rtmp_host_port(url: str) -> tuple[str, int]:
    """(host, port) of a validated RTMP address; host is not a secret and is what
    the camera list shows."""
    parts = urlsplit(url)
    default = 443 if parts.scheme.lower() == "rtmps" else DEFAULT_RTMP_PORT
    return parts.hostname or "", parts.port or default


def build_rtsp_url(cam: dict) -> str | None:
    host = cam.get("host")
    if not host:
        return None
    scheme = "rtsps" if str(cam.get("protocol") or "").strip().lower() == "rtsps" else "rtsp"
    port = cam.get("port") or (322 if scheme == "rtsps" else 554)
    # user and password are percent-encoded: a password containing @ : / # ? % would otherwise corrupt the address
    user = quote(cam.get("user") or "", safe="")
    password = quote(cam.get("password") or "", safe="")
    path = cam.get("stream_path") or ""
    if not path.startswith("/"):
        path = "/" + path
    auth = f"{user}:{password}@" if user or password else ""
    return f"{scheme}://{auth}{host}:{port}{path}"


def generate_stream_key() -> str:
    """A new, unguessable stream key (CSPRNG, 192 bits)."""
    return secrets.token_urlsafe(24)


def is_stream_key(value: str | None) -> bool:
    return bool(value) and bool(STREAM_KEY_RE.match(value))


def push_setup(key: str, host: str, port: int, scheme: str, app: str, full_format: str) -> dict:
    """What the camera is told: the server URL, the key, and the single URL for
    devices with one field. The ingest server accepts exactly {app}/{key}."""
    default_port = 443 if scheme == "rtmps" else 1935
    hostport = host if int(port) == default_port else f"{host}:{int(port)}"
    server = f"{scheme}://{hostport}/{app}"
    return {"server_url": server, "stream_key": key, "full_url": full_format.format(server=server, key=key)}


def ingest_path(key: str, app: str) -> str:
    return f"{app}/{key}"


def ingest_read_url(key: str, base: str, app: str, user: str, password: str) -> str:
    """Where the backend reads a pushed stream from (the ingest server's internal
    RTSP side), with its read-only account."""
    scheme, rest = base.split("://", 1)
    auth = f"{quote(user, safe='')}:{quote(password, safe='')}@" if user or password else ""
    return f"{scheme}://{auth}{rest}/{ingest_path(key, app)}"


def build_source_url(cam: dict | None) -> str | None:
    """The address the camera's reader opens: the stored RTMP link for an RTMP
    camera, the ingest server's copy of the camera's own published stream for an
    RTMP-push camera, otherwise the RTSP URL assembled from
    host/port/user/password/path (unchanged behaviour for every existing camera)."""
    if not cam:
        return None
    protocol = protocol_of(cam)
    if protocol == "rtmp":
        return (cam.get("source_url") or "").strip() or None
    if protocol == PUSH_PROTOCOL:
        key = cam.get("rtmp_stream_key") or ""
        if not is_stream_key(key):
            return None
        from falldet import config

        return ingest_read_url(key, config.INGEST_RTSP_BASE, config.RTMP_APP,
                               config.INGEST_READ_USER, config.INGEST_READ_PASSWORD)
    return build_rtsp_url(cam)


_USERINFO = re.compile(r"^([a-z][a-z0-9+.-]*://)([^:/@\s]+):([^@/\s]+)@", re.I)


def redact_source(url: str | None) -> str:
    """The address with every secret masked, for the UI and for logs:
    rtsp://user:***@host:554/path, rtmp://host:1935/app/***."""
    if not url:
        return ""
    text = _USERINFO.sub(r"\1\2:***@", url.strip())
    try:
        parts = urlsplit(text)
    except ValueError:
        return "***"
    if parts.scheme.lower() in RTMP_SCHEMES:
        segs = [s for s in parts.path.split("/") if s]
        keep = "/" + segs[0] if segs else ""
        masked = keep + ("/***" if len(segs) > 1 or parts.query else "")
        return f"{parts.scheme}://{parts.netloc}{masked}"   # netloc already has any password masked
    return text
