"""Print the engine's per-frame view of one extracted URFD sequence, to understand
why it did or did not trigger.   python -m tools.debug_sequence fall-01 [--fps 5]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from falldet.fall_analysis.config import FallConfig  # noqa: E402
from falldet.fall_analysis.engine import CameraFallEngine  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
a = argparse.ArgumentParser()
a.add_argument("name")
a.add_argument("--fps", type=float, default=5.0)
a.add_argument("--conf", type=float, default=0.4)
a.add_argument("--imgsz", type=int, default=640)
a.add_argument("--work", default=str(ROOT.parent / "datasets" / "urfd" / "extracted"))
args = a.parse_args()

from ultralytics import YOLO  # noqa: E402

frames = sorted((Path(args.work) / args.name).glob("*.png"))
model = YOLO(str(ROOT / "models" / "yolov8n-pose.pt"))
eng = CameraFallEngine(1, FallConfig())
step = max(1, round(30 / args.fps))
print("t(s)  ids  box(w x h)  aspect torso ext   cy    stand_h lying upr  state")
for i in range(0, len(frames), step):
    img = cv2.imread(str(frames[i]))
    h, w = img.shape[:2]
    r = model.track(img, persist=True, tracker="bytetrack.yaml", conf=args.conf, imgsz=args.imgsz, verbose=False)[0]
    people = []
    if r.boxes is not None and len(r.boxes):
        ids = r.boxes.id.cpu().numpy().astype(int) if r.boxes.id is not None else [None] * len(r.boxes)
        kp = r.keypoints.data.cpu().numpy()
        for j in range(len(r.boxes)):
            people.append({"track_id": None if ids[j] is None else int(ids[j]), "bbox": r.boxes.xyxy[j].cpu().numpy().tolist(),
                           "confidence": float(r.boxes.conf[j]), "keypoints": kp[j]})
    ts = i / 30
    ev = eng.update(ts, people, (w, h))
    line = f"{ts:5.2f} "
    if not people:
        line += " no person detected"
    for tid, (hist, fsm) in eng.tracks.items():
        if not hist.samples or hist.samples[-1].f.ts != ts:
            continue
        s = hist.samples[-1]
        f = s.f
        line += (f" {tid!s:>3}  {f.w:4.0f}x{f.h:4.0f}  {f.aspect:5.2f} "
                 f"{'  -  ' if f.torso_angle is None else format(f.torso_angle, '5.0f')} "
                 f"{'  -  ' if s.ext_ratio is None else format(s.ext_ratio, '4.2f')} {f.cy:5.0f} "
                 f"{hist.stand_h or 0:7.0f} {str(s.lying):5s} {str(s.upright):5s} {fsm.state}"
                 f"{'  vis=' + str(f.n_visible) + (' partial' if f.partial else '')}")
    print(line + ("   EVENTS: " + ",".join(e.kind for e in ev) if ev else ""))
