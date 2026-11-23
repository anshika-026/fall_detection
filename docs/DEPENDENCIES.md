# Dependencies, models and data

## Python (backend/requirements.txt)
Pinned to the versions the tests and measurements were run with (Python 3.12.10, Windows 11). They are the
same pins SMC uses, or newer patch levels, so one environment can serve both. Nothing from SMC's face /
Re-ID / expression / licensing stack is required.

| Package | Role | Note |
|---|---|---|
| fastapi, starlette, uvicorn, pydantic | API + websockets | |
| numpy, opencv-python, av | frames, JPEG, H.264 clips | |
| torch, torchvision | inference | CPU build used for all measurements here; no GPU on the development machine |
| ultralytics | `yolov8n-pose` + built-in ByteTrack (`bytetrack.yaml`) | **AGPL-3.0.** SMC already depends on it; get legal advice before distributing this product commercially |
| lap | ByteTrack assignment | needed by ultralytics' tracker |
| httpx | alert webhook | |
| psutil | CPU/memory in `/api/system` | |

`supervision` is **not** used (SMC's `sv.ByteTrack` is deprecated and removed upstream in 0.31).

## Frontend (frontend/package.json)
React 19, react-router 7, Vite 8, Tailwind 4, recharts 3, lucide-react: the same versions as SMC's frontend.

## Model weights
| File | Source | SHA-256 (as tested) |
|---|---|---|
| `backend/models/yolov8n-pose.pt` (6.8 MB, COCO-17 keypoints) | `github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n-pose.pt` | `c6fa93dd1ee4a2c18c900a45c1d864a1c6f7aba75d84f91648a30b7fb641d212` |

`python -m tools.fetch_models` downloads and verifies it. Larger pose models (`yolov8s-pose.pt`, `yolov8m-pose.pt`)
can be selected with `POSE_MODEL`; they are slower and have not been benchmarked here unless stated in docs/EVALUATION.md.

## Datasets (tests only; never shipped, gitignored)
| Dataset | Use | Licence (read on the source page) |
|---|---|---|
| UR Fall Detection Dataset (Kwolek & Kepski, Univ. of Rzeszow): 30 falls + 40 ADL sequences, Kinect RGB/depth + accelerometer | `tools/eval_urfd.py`, camera 0 RGB only | **CC BY-NC-SA 4.0, non-commercial academic use** (stated on https://fenix.ur.edu.pl/mkepski/ds/uf.html). Cite: Kwolek & Kepski, *Computer Methods and Programs in Biomedicine* 117(3), 2014. |
| CAUCAFall (Mendeley Data, DOI 10.17632/7w7fccy7ky) | **not used.** Licence could not be confirmed from the Mendeley page; third-party mirrors disagree (CC BY 4.0 vs non-commercial). Verify before use. | unverified |

Labels: URFD gives **sequence-level** labels (fall / activity of daily living) only, not per-frame ones.

## Deferred: MMAction2 (ST-GCN, PoseC3D)
Not integrated, by decision. Findings that stand for a later phase: MMAction2 documents NTU-60 pretrained
skeleton models; NTU-60 has a "falling down" class (from the dataset definition; confirm the label list before
relying on it); MMAction2 1.x needs `mmengine` + compiled `mmcv` ops, which are very likely to conflict with
torch 2.14 / Python 3.12 / numpy 2.5 and were **not** installed or tested here; the models are trained on acted
indoor Kinect-style data, not CCTV, so they would need fine-tuning on your own footage. If pursued, run training
in a separate environment and export the model to plain PyTorch/ONNX; feed it from `pose_worker`'s consumer
registry so no second inference pass is needed.
