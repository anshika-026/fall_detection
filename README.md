# Fall Detection

A standalone fall-detection system: camera streaming, pose estimation, a rule-based fall engine with a
temporal state machine, incident management, and its own dashboard. It reuses the proven camera and
YOLO/ByteTrack architecture from SMC (see [docs/SOURCE_MAPPING.md](docs/SOURCE_MAPPING.md)) but shares no
code, database, configuration, ports or authentication with it.

> **Status:** engine, backend and frontend are built and covered by automated tests. It has **not** been
> validated on real CCTV footage and must not be treated as production-ready or as a safety system.
> See [docs/EVALUATION.md](docs/EVALUATION.md) and [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## How it works

```
camera (RTSP/RTMP) ─► rtsp_reader process ─► camera_stream ─┬─► JPEG ─► /ws/live/{id} ─► browser
                                                           ├─► clip buffer (evidence)
                                                           └─► pose_worker  (1 yolov8n-pose + ByteTrack pass per camera,
                                                                              own model/tracker, skips frames when busy)
                                                                  └─► CameraFallEngine (one per camera)
                                                                         NORMAL → POSSIBLE → CONFIRMED → RECOVERED → RESOLVED
                                                                            └─► IncidentManager ─► SQLite, snapshot, clip,
                                                                                                    webhook, /ws/events, /ws/detections
```

A fall is confirmed only when several signals agree over time: a rapid hip descent (or fast torso rotation), a
lying posture at the end of it (≥2 of torso angle / box shape / collapsed body height), the person having been
upright shortly before, and staying down and still for the confirmation time. Sitting, bending, kneeling,
exercise and deliberate lying down do not satisfy all of these. Details: `backend/falldet/fall_analysis/engine.py`.

## Run it

```bash
# backend (Python 3.12) — from backend/
pip install -r requirements.txt            # install PyTorch for your hardware first (see the file header)
python -m tools.fetch_models               # downloads yolov8n-pose.pt (checksum printed)
copy .env.example .env                     # optional
python -m falldet.serve                    # http://127.0.0.1:8830  (API docs at /docs)

# frontend — from frontend/
npm install
npm run dev                                # http://localhost:5190  (proxies /api and /ws to :8830)
```

Open http://localhost:5190. The first visit asks you to create the administrator account. Then add cameras on
the **Cameras** page (use *Test* to confirm the stream works).

Tests: `cd backend && python -m pytest tests -q`.
Offline evaluation on recorded video: `python -m tools.eval_urfd --help`.

## Layout

```
backend/falldet/   camera/ detection/ pose_estimation/ tracking/ fall_analysis/ event_manager/ api/ core/
backend/tests/     engine scenarios, API + integration, runtime/worker tests
backend/tools/     evaluation harness, per-frame debugger, model fetcher
frontend/src/      dashboard/ live_monitoring/ analytics/ cameras/ settings/ (+ shared components)
docs/              SOURCE_MAPPING, DEPENDENCIES, LIMITATIONS, EVALUATION
```

Ports: backend 8830, frontend 5190 (SMC uses 8822 / 5180, MAINDV 8821).
