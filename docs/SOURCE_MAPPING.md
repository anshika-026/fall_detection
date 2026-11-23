# Source-to-destination mapping (SMC → Fall Detection)

Source: `C:\Users\lenovo\Desktop\SMC` (origin `github.com/anshika-026/SMC`, branch `feature/visitor-history-dates`).
SMC was only **read**; nothing in it was changed. Destination paths are relative to this folder.

## Backend

| SMC source (`backend/app/`) | Destination (`backend/falldet/`) | How | What changed and why |
|---|---|---|---|
| `rtsp_reader.py` | `camera/rtsp_reader.py` | **Copied unchanged** | Reader process, reconnect backoff, timeouts. No SMC imports. |
| `stream_source.py` | `camera/stream_source.py` | **Copied**, 2 lines | `from app import config` → `from falldet import config`. |
| `clips.py` | `camera/clips.py` | **Copied**, constants only | `VISITOR_*` env names → `FALLDET_*`; clip window 5 s+5 s → 8 s+8 s for fall evidence. |
| `resilience.py` | `core/resilience.py` | **Copied**, 1 line | import path only. |
| `db.py` | `core/db.py` | **Copied**, 1 line | import path only. |
| `person_detection.py` | `detection/pose_worker.py` | **Adapted** | Same worker architecture; pose model returning keypoints; one pass instead of a separate person pass. See "Why adaptation" below. |
| `camera_stream.py` | `camera/camera_stream.py` | **Adapted** | Reader supervision, watchdog, subscribers and JPEG fan-out kept; face, footfall, staff, visitor and analytics-switch code removed; frames go to `pose_worker` + clip buffer. |
| `camera_db.py` | `camera/camera_db.py` | **Adapted** | Same redaction rules and `is_streamable`; columns replaced (`fall_detection_enabled`, `sensitivity`); no sites table. |
| `alerts.py`, `alerts_routes.py`, `evidence.py` | `event_manager/` (`incidents.py`, `manager.py`) | **Pattern only, rewritten** | Dedupe key, acknowledge/resolve and clip-evidence ideas kept; own table, own lifecycle (possible/confirmed/recovered/resolved/dismissed). |
| `config.py`, `logging_setup.py` | `config.py`, `core/logging_setup.py` | **Adapted** | Same env helpers and reader/watchdog constants; everything SMC-specific dropped; own ports and paths. |
| `auth.py` | `auth.py` | **Rewritten (smaller)** | Own users/sessions/scrypt; no licences, SSO or client portal. |
| `main.py` (cameras, `/ws/live`, `/ws/detections`) | `main.py`, `api/routes_*.py` | **Pattern only, rewritten** | Same endpoint shapes and websocket re-auth logic. |

## Frontend

| SMC source (`frontend/src/`) | Destination (`frontend/src/`) | How |
|---|---|---|
| `components/{KpiPanel, DataTable, Modal, PageHeader, Tabs, ToggleSwitch, ErrorBoundary}.jsx`, `lib/visibleInterval.js`, `postcss.config.js` | same names | **Copied** (KpiPanel: one comment) |
| `index.css` | `index.css` | **Copied**, unused animation removed, extra button/alert classes added |
| `hooks/useLiveCameraFeed.js` | `hooks/useLiveFeed.js` | **Adapted**: boxes coloured by fall state, skeleton, detection status |
| `components/LiveCameraTile.jsx` | `live_monitoring/CameraTile.jsx` | **Adapted** |
| `pages/CameraManagement.jsx` | `cameras/Cameras.jsx` | **Adapted** (kept RTSP form, test stream; dropped footfall/gate/attendance) |
| `pages/Dashboard.jsx`, `pages/Alerts.jsx` | `dashboard/Dashboard.jsx`, `components/IncidentDrawer.jsx` | **Layout reference**, rewritten |
| `layouts/*`, `context/AuthContext.jsx`, `api/client.js` | `layouts/AppShell.jsx`, `context/AuthContext.jsx`, `api/client.js` | **Rewritten (smaller)** |

Not taken: every other SMC page and component (attendance, face recognition/training, people, visitors, footfall, staff count, workforce, intrusion/zones, licences, SMC Connect, SSO, `src/data/*` mock data).

## New files (no SMC equivalent)

`fall_analysis/{engine,config}.py`, `pose_estimation/keypoints.py`, `tracking/track_history.py`, `event_manager/{incidents,manager,hub}.py`,
`core/{schema,settings_store}.py`, `runtime.py`, `api/routes_*.py`, `tools/{eval_urfd,debug_sequence,fetch_models}.py`, the analytics page and settings page, all tests.

## Why `person_detection.py` was adapted instead of reused as is

1. It hard-codes `yolov8n.pt` and returns only boxes. Fall analysis needs the 17 keypoints, which only a pose model produces.
2. A pose model also detects and tracks people. So the adapted worker **replaces** the person pass: exactly one inference per processed frame per camera. Running SMC's person detector *and* a pose model would be the "second pipeline" to avoid.
3. What is preserved on purpose: one model instance per camera (ultralytics keeps ByteTrack state with the model, so track ids can't mix across cameras), skip-if-busy instead of queueing, backoff and model reload on failure, consumers registered by name with their own rate.
4. Because this module must be independent, SMC can't be imported at run time; the file is therefore a modified copy rather than a dependency.

## Shared vs separately installed dependencies

| | |
|---|---|
| **Same environment works** (same pins as SMC) | python 3.12, fastapi, uvicorn, pydantic, numpy, opencv-python, torch/torchvision, ultralytics, lap, scipy, av, psutil, httpx |
| **Not needed here** | insightface, onnxruntime, torchreid, transformers, scikit-learn, tensorflow, PyJWT, supervision |
| **Own install** | `frontend/` (its own `node_modules`), `backend/models/yolov8n-pose.pt` |
| **Own runtime state** | `backend/data/falldet.db`, `backend/data/evidence/`, `backend/logs/`, ports 8830 / 5190 |
