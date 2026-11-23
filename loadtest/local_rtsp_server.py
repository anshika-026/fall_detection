"""A tiny RTSP test server for localhost: serves a looping H.264 video file as `rtsp://127.0.0.1:<port>/<path>`.

  python loadtest/local_rtsp_server.py --video some_h264.mkv --port 8555 --path stream1 --user tester --password-env LOCAL_RTSP_PASS

It exists so the CCTV tools (preflight, recorder, verifier) can be run over a REAL RTSP connection when MediaMTX cannot be started
on this machine (an Application Control policy blocks the downloaded .exe). It is a TEST SIMULATOR, not a camera: a recording made from it
proves the tools work over RTSP/TCP, not that any physical camera is compatible. Never expose it beyond localhost.

Supported: RTSP over TCP (interleaved RTP), H.264 (mp4 or Annex B source), Basic authentication (optional), several clients, real-time pacing,
looping. Not supported: UDP, H.265, audio, seeking. The password is read from an environment variable and never printed.
"""
from __future__ import annotations

import argparse
import base64
import os
import socket
import struct
import threading
import time

import av

MTU = 1400


def split_annexb(data: bytes) -> list[bytes]:
    nals, i, n = [], 0, len(data)
    starts = []
    while i < n - 3:
        if data[i] == 0 and data[i + 1] == 0 and (data[i + 2] == 1 or (data[i + 2] == 0 and i + 3 < n and data[i + 3] == 1)):
            j = i + (3 if data[i + 2] == 1 else 4)
            starts.append((i, j))
            i = j
        else:
            i += 1
    for k, (_, j) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else n
        nals.append(data[j:end])
    return [x for x in nals if x]


def split_avcc(data: bytes, size: int) -> list[bytes]:
    out, i = [], 0
    while i + size <= len(data):
        ln = int.from_bytes(data[i:i + size], "big")
        i += size
        out.append(data[i:i + ln])
        i += ln
    return out


class Source:
    """The video file as lists of NAL units per access unit (loaded once)."""

    def __init__(self, path: str):
        c = av.open(path)
        vs = c.streams.video[0]
        if vs.codec_context.name != "h264":
            raise SystemExit(f"{path}: video is {vs.codec_context.name}; this test server only serves H.264")
        self.fps = float(vs.average_rate or 15)
        extra = bytes(vs.codec_context.extradata or b"")
        self.sps = self.pps = None
        self.avcc_size = 0
        if extra[:1] == b"\x01":                                  # avcC (mp4 / matroska)
            self.avcc_size = (extra[4] & 3) + 1
            n_sps = extra[5] & 31
            p = 6
            for _ in range(n_sps):
                ln = int.from_bytes(extra[p:p + 2], "big")
                self.sps = self.sps or extra[p + 2:p + 2 + ln]
                p += 2 + ln
            n_pps = extra[p]
            p += 1
            for _ in range(n_pps):
                ln = int.from_bytes(extra[p:p + 2], "big")
                self.pps = self.pps or extra[p + 2:p + 2 + ln]
                p += 2 + ln
        elif extra:
            for nal in split_annexb(extra):
                if nal[0] & 31 == 7:
                    self.sps = nal
                elif nal[0] & 31 == 8:
                    self.pps = nal
        self.units: list[tuple[list[bytes], bool]] = []
        for pkt in c.demux(vs):
            if pkt.size == 0:
                continue
            raw = bytes(pkt)
            nals = split_avcc(raw, self.avcc_size) if self.avcc_size else split_annexb(raw)
            for nal in nals:
                t = nal[0] & 31
                if t == 7 and not self.sps:
                    self.sps = nal
                if t == 8 and not self.pps:
                    self.pps = nal
            self.units.append(([n for n in nals if n and (n[0] & 31) not in (7, 8, 9)], any(n[0] & 31 == 5 for n in nals)))
        c.close()
        if not self.sps or not self.pps or not self.units:
            raise SystemExit("could not read SPS/PPS or frames from the video")

    def sdp(self) -> str:
        return ("v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=local test stream\r\nc=IN IP4 0.0.0.0\r\nt=0 0\r\n"
                "m=video 0 RTP/AVP 96\r\na=rtpmap:96 H264/90000\r\n"
                f"a=fmtp:96 packetization-mode=1;profile-level-id={self.sps[1:4].hex()};"
                f"sprop-parameter-sets={base64.b64encode(self.sps).decode()},{base64.b64encode(self.pps).decode()}\r\n"
                "a=control:track1\r\n")


def rtp_packets(nals: list[bytes], seq: int, ts: int, ssrc: int):
    """Yield (packet bytes, next_seq) for one access unit (single NAL or FU-A); marker on the last packet."""
    pieces = []
    for nal in nals:
        if len(nal) <= MTU:
            pieces.append(nal)
        else:
            ind, typ = (nal[0] & 0xE0) | 28, nal[0] & 31
            body = nal[1:]
            for k in range(0, len(body), MTU - 2):
                chunk = body[k:k + MTU - 2]
                flags = (0x80 if k == 0 else 0) | (0x40 if k + MTU - 2 >= len(body) else 0)
                pieces.append(bytes([ind, flags | typ]) + chunk)
    for i, pl in enumerate(pieces):
        marker = 0x80 if i == len(pieces) - 1 else 0
        yield struct.pack("!BBHII", 0x80, marker | 96, seq & 0xFFFF, ts & 0xFFFFFFFF, ssrc) + pl
        seq += 1


class Handler(threading.Thread):
    def __init__(self, conn: socket.socket, src: Source, path: str, user: str | None, pw: str | None, log):
        super().__init__(daemon=True)
        self.conn, self.src, self.path, self.user, self.pw, self.log = conn, src, path, user, pw, log
        self.session = f"{abs(hash(id(self))) % 10**8:08d}"
        self.playing = threading.Event()
        self.stop = threading.Event()
        self.wlock = threading.Lock()
        self.chan = 0

    def send(self, text: str) -> None:
        with self.wlock:
            self.conn.sendall(text.encode())

    def authed(self, headers: dict) -> bool:
        if not self.user:
            return True
        a = headers.get("authorization", "")
        return a.startswith("Basic ") and base64.b64decode(a[6:]).decode(errors="replace") == f"{self.user}:{self.pw}"

    def read_request(self, buf: bytearray):
        while True:
            while buf[:1] == b"$":                                    # client RTCP on an interleaved channel: discard
                if len(buf) < 4:
                    break
                ln = struct.unpack("!H", bytes(buf[2:4]))[0]
                if len(buf) < 4 + ln:
                    break
                del buf[:4 + ln]
            i = buf.find(b"\r\n\r\n")
            if i >= 0 and buf[:1] != b"$":
                head = bytes(buf[:i]).decode(errors="replace")
                del buf[:i + 4]
                lines = head.split("\r\n")
                method, url = lines[0].split()[:2]
                headers = {k.strip().lower(): v.strip() for k, v in (l.split(":", 1) for l in lines[1:] if ":" in l)}
                return method, url, headers
            data = self.conn.recv(4096)
            if not data:
                return None
            buf += data

    def run(self) -> None:
        buf = bytearray()
        try:
            while True:
                req = self.read_request(buf)
                if req is None:
                    break
                method, url, h = req
                cseq = h.get("cseq", "0")
                base = f"RTSP/1.0 %s\r\nCSeq: {cseq}\r\n"
                if method == "OPTIONS":
                    self.send(base % "200 OK" + "Public: OPTIONS, DESCRIBE, SETUP, PLAY, TEARDOWN\r\n\r\n")
                elif not self.authed(h):
                    self.log("auth rejected for %s", method)
                    self.send(base % "401 Unauthorized" + 'WWW-Authenticate: Basic realm="local-test"\r\n\r\n')
                elif method == "DESCRIBE":
                    if not url.rstrip("/").endswith("/" + self.path):
                        self.send(base % "404 Not Found" + "\r\n")
                        continue
                    body = self.src.sdp()
                    self.send(base % "200 OK" + f"Content-Base: {url.rstrip('/')}/\r\nContent-Type: application/sdp\r\nContent-Length: {len(body)}\r\n\r\n{body}")
                elif method == "SETUP":
                    t = h.get("transport", "")
                    if "TCP" not in t.upper():
                        self.send(base % "461 Unsupported Transport" + "\r\n")
                        continue
                    self.chan = int(t.split("interleaved=")[1].split("-")[0].split(";")[0]) if "interleaved=" in t else 0
                    self.send(base % "200 OK" + f"Transport: RTP/AVP/TCP;unicast;interleaved={self.chan}-{self.chan + 1}\r\nSession: {self.session};timeout=60\r\n\r\n")
                elif method == "PLAY":
                    self.send(base % "200 OK" + f"Session: {self.session}\r\nRange: npt=0.000-\r\n\r\n")
                    if not self.playing.is_set():
                        self.playing.set()
                        threading.Thread(target=self.stream, daemon=True).start()
                elif method == "TEARDOWN":
                    self.send(base % "200 OK" + f"Session: {self.session}\r\n\r\n")
                    break
                else:
                    self.send(base % "405 Method Not Allowed" + "\r\n")
        except (OSError, ValueError, IndexError):
            pass
        finally:
            self.stop.set()
            try:
                self.conn.close()
            except OSError:
                pass
            self.log("client disconnected")

    def stream(self) -> None:
        self.log("streaming started")
        src, seq, ssrc, tick = self.src, 1000, 0x1234ABCD, 0
        t0 = time.perf_counter()
        try:
            while not self.stop.is_set():
                for nals, key in src.units:
                    due = t0 + tick / src.fps
                    delay = due - time.perf_counter()
                    if delay > 0:
                        time.sleep(delay)
                    ts = int(tick * 90000 / src.fps)
                    out = ([src.sps, src.pps] if key else []) + nals
                    for p in rtp_packets(out, seq, ts, ssrc):
                        with self.wlock:
                            self.conn.sendall(b"$" + bytes([self.chan]) + struct.pack("!H", len(p)) + p)
                        seq += 1
                    tick += 1
                    if self.stop.is_set():
                        return
        except OSError:
            pass


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", required=True, help="an H.264 video file to loop")
    ap.add_argument("--port", type=int, default=8555)
    ap.add_argument("--path", default="stream1")
    ap.add_argument("--user", default=None)
    ap.add_argument("--password-env", default=None, help="env var holding the password (never printed)")
    ap.add_argument("--duration", type=float, default=0, help="stop after this many seconds (0 = until Ctrl+C)")
    a = ap.parse_args()
    pw = os.environ.get(a.password_env) if a.password_env else None
    if a.user and not pw:
        raise SystemExit("--user needs --password-env naming a set environment variable")
    src = Source(a.video)
    log = lambda m, *x: print(time.strftime("%H:%M:%S"), "rtsp-sim:", m % x, flush=True)
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", a.port))                                  # localhost only, by design
    srv.listen(8)
    srv.settimeout(0.5)
    log("serving %s fps H.264 at rtsp://127.0.0.1:%d/%s (%s) - TEST SIMULATOR, not a camera", f"{src.fps:g}", a.port, a.path, "login required" if a.user else "no login")
    t0 = time.time()
    try:
        while not a.duration or time.time() - t0 < a.duration:
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            log("client connected")
            Handler(conn, src, a.path, a.user, pw, log).start()
    except KeyboardInterrupt:
        pass
    srv.close()


if __name__ == "__main__":
    main()
