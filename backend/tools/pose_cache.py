"""Run the real pose model + ByteTrack ONCE over extracted URFD sequences and store the per-frame
output, so the fall engine can be replayed and diagnosed without re-running the model (the engine
is pure Python; the model is the slow part). Same detector settings as tools.eval_urfd.

  python -m tools.pose_cache --names fall-01,adl-02   (default: every extracted sequence)
Output: datasets/urfd/pose_cache/<weights>/<name>.pkl  (git-ignored with the rest of datasets/)
Each file: {"fps","frame_wh","frames":[{"i","ts","people":[{track_id,bbox,confidence,keypoints}]}],"infer_ms":[...]}"""
from __future__ import annotations

import argparse
import pickle
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SRC_FPS = 30.0


def cache_dir(weights: str, base: Path | None = None, tag: str = "") -> Path:
    """`tag` separates caches made with non-default detector settings, e.g. conf0.15."""
    return (base or ROOT.parent / "datasets" / "urfd" / "pose_cache") / (Path(weights).stem + (f"_{tag}" if tag else ""))


def load(name: str, weights: str = "yolov8n-pose.pt", tag: str = "") -> dict:
    with open(cache_dir(weights, tag=tag) / f"{name}.pkl", "rb") as fh:
        return pickle.load(fh)


def build(name: str, frames: list[Path], model, fps: float, conf: float, imgsz: int) -> dict:
    out, wh, ms = [], None, []
    step = max(1, round(SRC_FPS / fps))
    for i in range(0, len(frames), step):
        img = cv2.imread(str(frames[i]))
        if img is None:
            continue
        wh = (img.shape[1], img.shape[0])
        t0 = time.perf_counter()
        r = model.track(img, persist=True, tracker="bytetrack.yaml", conf=conf, imgsz=imgsz, verbose=False)[0]
        ms.append((time.perf_counter() - t0) * 1000)
        people = []
        if r.boxes is not None and len(r.boxes):
            ids = r.boxes.id.cpu().numpy().astype(int) if r.boxes.id is not None else [None] * len(r.boxes)
            kp = r.keypoints.data.cpu().numpy()
            for j in range(len(r.boxes)):
                people.append({"track_id": None if ids[j] is None else int(ids[j]), "bbox": r.boxes.xyxy[j].cpu().numpy().tolist(),
                               "confidence": float(r.boxes.conf[j]), "keypoints": kp[j]})
        out.append({"i": i, "ts": i / SRC_FPS, "people": people})
    return {"name": name, "fps": fps, "frame_wh": wh, "frames": out, "infer_ms": ms, "n_source_frames": len(frames)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", default="")
    ap.add_argument("--weights", default=str(ROOT / "models" / "yolov8n-pose.pt"))
    ap.add_argument("--fps", type=float, default=5.0)
    ap.add_argument("--conf", type=float, default=0.4)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--tag", default="", help="cache sub-folder suffix for non-default settings (e.g. conf0.15)")
    a = ap.parse_args()
    from ultralytics import YOLO

    ext = ROOT.parent / "datasets" / "urfd" / "extracted"
    names = [n for n in a.names.split(",") if n] or sorted(p.name for p in ext.iterdir() if p.is_dir())
    dest = cache_dir(a.weights, tag=a.tag)
    dest.mkdir(parents=True, exist_ok=True)
    for n in names:
        frames = sorted((ext / n).glob("*.png"))
        if not frames:
            print("no frames:", n)
            continue
        model = YOLO(a.weights)          # fresh tracker per sequence
        d = build(n, frames, model, a.fps, a.conf, a.imgsz)
        with open(dest / f"{n}.pkl", "wb") as fh:
            pickle.dump(d, fh)
        print(f"{n}: {len(d['frames'])} frames cached", flush=True)


if __name__ == "__main__":
    main()
