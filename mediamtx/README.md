# MediaMTX (streaming infrastructure, separate from the backend)

**What the backend actually needs:** nothing from this folder. Each camera in the backend is configured with
its own RTSP host/port/path/credentials (Camera Management), and the backend's reader opens that URL. Real
cameras are read directly. MediaMTX is used here to (a) publish recorded video as simulated cameras for
multi-camera tests (`loadtest/publish_rtsp.py`) and (b) optionally as the ingest server for RTMP-push cameras
(backend setting `INGEST_RTSP_BASE`, default `rtsp://127.0.0.1:8554`, unchanged).

Contract between the two services: RTSP over TCP on `rtsp://127.0.0.1:8554/<path>`. Register a simulated
camera in the backend with host `127.0.0.1`, port `8554`, path `cam1` (and so on).

## Setup
1. Download the MediaMTX release for Windows (amd64) from https://github.com/bluenviron/mediamtx/releases
   and put `mediamtx.exe` in `mediamtx/bin/` (`bin/` is git-ignored).
2. The executable must be allowed to run by your Windows security policy. **On the development machine it was
   blocked by an Application Control policy**, so it has not been run (see the Stage 8 report).

## Start / stop
```
mediamtx\start.ps1      # background, localhost only, log in mediamtx\mediamtx.log
mediamtx\stop.ps1
cd backend; python -m falldet.serve    # the backend, separately
python loadtest\publish_rtsp.py --cams 4 --fps 15
```
Stop everything in reverse order: publishers (Ctrl+C), backend, MediaMTX.

Config: `mediamtx.yml` (localhost bound, RTSP only, no auth: test use only; add authentication before exposing it).
