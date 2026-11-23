# Real-CCTV validation workflow

Goal: measure the existing fall engine on footage from **your own cameras**, with ground truth written by people.
The tools never change the engine. Footage, recordings and caches are personal data: they are git-ignored.
**All commands are run from the `backend/` folder in PowerShell** (paths below are relative to it).

## 0. What you must supply
- RTSP access to an office camera (URL with credentials) **or** the camera already added in the backend. The machine that runs the
  recorder must be able to reach it (same LAN/VLAN, or VPN). The preflight tells you whether it can.
- **Consent** from every person who will be filmed, and a note of how long footage is kept. Staged falls need mats and supervision.
- People to perform the scenarios and one person to write the labels.
- A few hours of ordinary footage from the same camera (the false-alarm measurement needs it).

## 1. Folder layout: tuning and independent footage are kept apart
```
validation/
  tuning/        footage you MAY use to look at results and adjust settings
    <scenario>/  clip.mkv + clip.meta.json
  independent/   held-out footage: record it, label it, and DO NOT tune on it
    <scenario>/
  recordings/    raw recorder output (before cutting into clips)
    office_exported/   video files EXPORTED by the camera owner / a recorder (see "Exported footage" below)
  cache/         pose-model output cache (rebuildable)
  results/       reports
```
Scenarios (same names in both): `normal_office_activity`, `fall_standing`, `fall_from_chair`, `fall_forward`, `fall_backward`,
`fall_sideways`, `sitting_standing`, `bending_down`, `intentional_lying_down`, `recovery_after_fall`.
Rules: a clip lives in exactly one split (the runner refuses to run if the same footage is in both). `cctv_validate` defaults to
`independent/` and labels every report `tuning` or `independent`. If you change any setting after seeing results on a clip, that
clip is tuning footage from then on (move it). Record a separate day or camera for the independent set.

## Exported footage (while live camera access is pending): FILE / EXPORTED FOOTAGE
Use this when the camera owner can export video files but live RTSP access is not (yet) available. It measures **detection quality on files**.
It does **not** show that the live RTSP connection works and it is **not** physical-camera validation; every report says so.
All commands from `backend/`. `<X>` = your own file names. Never edit or rename the exported originals; the tools only read them.

1. **Copy** the owner's exported files into `..\validation\recordings\office_exported\` (keep the original file names; one copy, untouched).
2. **Check every file is usable** (read-only; also writes a SHA-256 inventory so you can prove the files did not change):
   ```powershell
   python -m tools.cctv_inspect ..\validation\recordings\office_exported --inventory ..\validation\results\office_exported_inventory.json
   ```
   `READY` = fine. `USABLE WITH WARNINGS` = read the warnings (low fps, gaps from motion-triggered recording, long keyframe spacing). `UNUSABLE` = ask the
   owner to re-export (the message says what: usually **MP4 or AVI, H.264, with timestamps**; raw `.h264`/`.264` streams and proprietary `.dav` files cannot be used).
3. **Find the times** by playing the file (VLC or Windows media player). `--start/--end/--event-at` below are seconds from the **first frame** (what the player shows as 0:00).
   Read the **wall-clock time of the first frame** from the picture's time overlay or the export name, with its time zone (India = `+05:30`).
4. **Cut a clip** around each event (no re-encoding; keep at least 20 s after a staged fall, and the whole normal stretch for normal activity):
   ```powershell
   python -m tools.cctv_clip ..\validation\recordings\office_exported\<X>.mp4 --start 125 --end 190 --event-at 152.5 --source-start 2026-12-01T10:30:00+05:30 --out ..\validation\independent\fall_standing\office_fall01.mkv
   ```
   It prints the `event_time_s` for the label. `--source-start` is optional (without it the clip has no wall-clock times and you must type them into the label yourself).
5. **Label (a person, not the detector)**: the clip is automatically marked `source_kind: exported_file`.
   ```powershell
   python -m tools.cctv_meta new ..\validation\independent\fall_standing\office_fall01.mkv --scenario fall_standing --camera-id office-1 --annotator AB
   ```
   Edit the `.meta.json`: set `event_time_s` for falls; check `recording_start/end` (a `+05:30` offset is accepted). Put clips for tuning in `tuning/`, held-out ones in `independent/`.
6. **Check the labels**: `python -m tools.cctv_meta check ..\validation\tuning ..\validation\independent` (also warns about files the runner would silently ignore).
7. **Validate**: `python -m tools.cctv_validate --footage ..\validation\independent --out ..\validation\results\exported_indep_run1.json --md ..\validation\results\exported_indep_run1.md`.
   The report records, per configuration: fall clips with POSSIBLE / CONFIRMED / missed, false alerts (and per normal hour), confirmation latency, per-frame latency; its top lines
   state that this is FILE / EXPORTED FOOTAGE, that live RTSP connectivity was NOT tested and that physical-camera live validation was NOT done.

What the owner needs to provide: see `docs/REAL_CCTV_VALIDATION.md`, section "Exported footage".

## 2. One camera first: preflight
```powershell
$env:CCTV_URL_OFFICE1 = "rtsp://user:pass@192.168.1.20:554/stream1"      # stays in this PowerShell session only
python -m tools.cctv_preflight --camera office-1=CCTV_URL_OFFICE1
python -m tools.cctv_preflight --db-camera office-1=3                    # or camera #3 of the backend database
```
Checks dependencies, folder + disk, memory, then DNS and TCP reachability from this machine, the RTSP login and path, codec
(H.264 / H.265 / MJPEG), resolution, decoding of real frames, measured fps, keyframe interval and bitrate (disk per hour). It never
records. Fix every `[FAIL]`; read every `[WARN]`. Special characters in a password (`@ : / # ?`) must be percent-encoded in the URL (`@` -> `%40`).
Only when one camera passes, repeat for the next camera; do not record several cameras before each has passed.

## 3. First 60-second test recording
```powershell
python -m tools.cctv_record --camera office-1=CCTV_URL_OFFICE1 --duration 60 --out ..\validation\recordings\first_test
python -m tools.cctv_verify_recording ..\validation\recordings\first_test --expect-seconds 60 --camera-env CCTV_URL_OFFICE1 --require-rtsp
```
The verifier checks: every segment playable, timestamps monotonic, sidecar present and complete, UTC start matches the file name,
footage length matches the time recorded (real cameras only), readable by the validation runner's decoder, total length, and that the
camera password / URL appears **nowhere** in the sidecars, logs or video bytes. `--require-rtsp` fails a recording that did not come from an RTSP camera.
Redirect the recorder's console output to a file if you want it scanned too (`--extra-log file`).

## 4. Record the real footage
```powershell
python -m tools.cctv_record --camera office-1=CCTV_URL_OFFICE1 --duration 3600 --segment-seconds 300
python -m tools.cctv_record --config ..\validation\cameras.json --duration 7200     # several cameras (copy cameras.example.json first; it holds no URL)
```
Output: `validation/recordings/<camera>/<camera>_<UTC>_<nn>.mkv` + a sidecar `.json`. Remux by default (no re-encode, low CPU); `--width/--height/--fps`
re-encode to a smaller size. A dropped stream closes the segment (kept) and reconnects with backoff. Nothing is overwritten. Stop with Ctrl+C.
Record from the camera and settings that will be used in production (same angle, height, resolution, fps).

## 5. Cut clips (no ffmpeg needed)
Times are seconds from the start of the recording **file**.
```powershell
python -m tools.cctv_clip ..\validation\recordings\office-1\office-1_20261201T101500Z_03.mkv --start 125 --end 190 --event-at 152.5 `
       --out ..\validation\independent\fall_standing\office1_fall01.mkv
```
It copies packets (no quality loss), starts at the previous keyframe, prints the real start, and prints the **`event_time_s`** to put in the label
(event time relative to the clip). Keep **20+ seconds after a staged fall**: CONFIRMED needs 3 s lying still, and a clip that ends sooner can only reach POSSIBLE.
One staged event per clip. Normal-activity clips can be long.

## 6. Label (a person, never the detector)
```powershell
python -m tools.cctv_meta new ..\validation\independent\fall_standing\office1_fall01.mkv --scenario fall_standing --camera-id office-1 --annotator AB
# edit office1_fall01.meta.json: set event_time_s (from step 5); recording_start/end are pre-filled from the recording sidecar (check them)
python -m tools.cctv_meta check ..\validation\tuning ..\validation\independent
```
Fields: camera id, recording start/end (UTC), scenario, approximate event time + tolerance, expected event (`fall`/`none`, must match the scenario),
optional `expected_recovery`. A clip without a valid `.meta.json` is skipped. `metadata_template.json` shows a complete example.

## 7. Validate
```powershell
python -m tools.cctv_validate --footage ..\validation\independent --out ..\validation\results\indep_run1.json --md ..\validation\results\indep_run1.md
python -m tools.cctv_validate --footage ..\validation\tuning --out ..\validation\results\tuning_run1.json --configs default,conf015
```
Runs yolov8n-pose + ByteTrack once per clip per detector confidence (cached), replays through the unchanged engine per configuration
(`default` = what ships; `conf015` = experiment; add `--config NAME:conf=0.3,min_person_conf=0.3`). Confirmation uses the clip's own following
frames and the 3 s requirement; no hold-last. Output: POSSIBLE/CONFIRMED per fall clip, confirmation latency, missed falls, false alerts (and per normal hour),
per-frame latency and single-stream fps. Counts, not accuracy. An existing `--out` is never overwritten.

Scoring: a staged fall is detected if POSSIBLE/CONFIRMED falls in `[event_time - 2 s, event_time + tolerance + 10 s]`; every other alert in a fall clip and
every alert in a `none` clip is a false alert. The windows are fixed in `tools/cctv_meta.py`.
Compare configurations on **normal** footage first. Change a setting only if false alerts there stay acceptable, then confirm on `independent/` footage that was not used to choose it.
