"""Publish recorded video as live RTSP cameras to a local MediaMTX, for end-to-end and
multi-camera tests of the real backend (reader process, reconnection, detection).

  python loadtest/publish_rtsp.py --cams 4 --fps 15 --seed fall-03,adl-01,fall-07

Each camera N publishes rtsp://127.0.0.1:8554/camN and loops its own playlist of
extracted UR Fall sequences (PNG frames from datasets/urfd/extracted/<name>/). Cameras
start at different offsets so they are not in lock-step. This is TEST INPUT only.
Stop with Ctrl+C (or terminate the process: that is also how a camera outage is simulated).
"""
from __future__ import annotations

import argparse
import itertools
import threading
import time
from pathlib import Path

import av
import cv2

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "datasets" / "urfd" / "extracted"


def frames_of(name: str) -> list[Path]:
    return sorted((EXTRACTED / name).glob("*.png"))


def publish(cam: int, playlist: list[str], fps: float, url: str, stop: threading.Event) -> None:
    seqs = [frames_of(n) for n in playlist]
    seqs = [s for s in seqs if s]
    if not seqs:
        print(f"cam{cam}: no frames for {playlist}")
        return
    first = cv2.imread(str(seqs[0][0]))
    h, w = first.shape[:2]
    w, h = w - w % 2, h - h % 2
    container = av.open(url, "w", format="rtsp", options={"rtsp_transport": "tcp"})
    stream = container.add_stream("libx264", rate=int(fps))
    stream.width, stream.height, stream.pix_fmt = w, h, "yuv420p"
    stream.options = {"preset": "ultrafast", "tune": "zerolatency", "g": str(int(fps) * 2)}
    period = 1.0 / fps
    nxt = time.perf_counter()
    n = 0
    print(f"cam{cam}: publishing {playlist} to {url}", flush=True)
    try:
        for seq in itertools.cycle(seqs):
            for p in seq[:: max(1, round(30 / fps))]:           # source is 30 fps
                if stop.is_set():
                    return
                img = cv2.imread(str(p))
                if img is None:
                    continue
                frame = av.VideoFrame.from_ndarray(img[:h, :w], format="bgr24")
                for packet in stream.encode(frame):
                    container.mux(packet)
                n += 1
                nxt += period
                time.sleep(max(0.0, nxt - time.perf_counter()))
    finally:
        try:
            container.close()
        except Exception:
            pass
        print(f"cam{cam}: stopped after {n} frames", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cams", type=int, default=2)
    ap.add_argument("--fps", type=float, default=15.0)
    ap.add_argument("--seed", default="fall-03,adl-01,fall-07,adl-02", help="comma list of sequence names to cycle")
    ap.add_argument("--host", default="127.0.0.1:8554")
    a = ap.parse_args()
    names = [n for n in a.seed.split(",") if n]
    stop = threading.Event()
    threads = []
    for c in range(1, a.cams + 1):
        rot = names[(c - 1) % len(names):] + names[: (c - 1) % len(names)]     # different start per camera
        t = threading.Thread(target=publish, args=(c, rot, a.fps, f"rtsp://{a.host}/cam{c}", stop), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.3)
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        stop.set()


if __name__ == "__main__":
    main()
