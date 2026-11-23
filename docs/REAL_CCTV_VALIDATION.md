# Real-CCTV validation

## Preparation status (read this first)
**The tools are ready for a first real-camera test. No real camera has been connected and no real footage has been recorded or evaluated.**
Everything marked "verified" below was verified on generated video files or a local fake RTSP server, which test the tools and say
nothing about real cameras. This document contains **no detection results, false-alarm rates or latencies from real cameras**, and none
are implied. The 30-clip URFD figures in `EVALUATION.md` / `FALL_DIAGNOSIS.md` are a different thing (public lab dataset, tuned on).

| Area | State |
|---|---|
| Camera preflight (`tools/cctv_preflight.py`) | built, tested on files + a fake RTSP server; **not yet run on a real camera** |
| Recorder (`tools/cctv_record.py`) | built, tested on files; **not yet run on a real camera** |
| Recording verifier (`tools/cctv_verify_recording.py`) | built, tested; real-camera rules (`--require-rtsp`, wall-clock check) **not yet exercised on real recordings** |
| Clip cutter (`tools/cctv_clip.py`), labels (`tools/cctv_meta.py`) | built, tested on generated video |
| Validation runner (`tools/cctv_validate.py`) | built; run end to end with the real pose model on file-based clips only |
| Tuning / independent footage split | in place and enforced by the runner |
| Footage | none: `validation/tuning/` and `validation/independent/` are empty |

## 1. Methodology
1. **Preflight one camera**, then record a **60-second test** and verify it. Only then record the real footage (one camera at a time first).
2. **Record** with `cctv_record` (RTSP, remux by default). **Cut** clips with `cctv_clip` into `validation/<split>/<scenario>/`.
3. **Two splits**: `tuning/` (may be looked at and used to adjust settings) and `independent/` (held out: never tuned on). A clip lives in
   exactly one split (content-compared; the runner refuses overlap). Reports are labelled `tuning` or `independent`; tuning results carry a banner
   "NOT independent validation".
4. **Label by a person.** `<clip>.meta.json`: camera id, recording start/end (UTC), scenario, approximate event time (seconds from the clip start)
   + tolerance, expected event `fall`/`none` (must match the scenario). Clips without valid metadata are skipped; labels are never derived from the detector.
5. **Replay** through the unchanged chain (yolov8n-pose + ByteTrack -> `CameraFallEngine`), one fresh engine per clip, 5 fps analysis, detector
   confidence 0.4 and the 3 s confirmation by default. Confirmation uses the clip's own following frames; no hold-last.
6. **Scoring** (windows fixed in `tools/cctv_meta.py` before any footage): detected if POSSIBLE/CONFIRMED occurs in
   `[event_time - 2 s, event_time + tolerance + 10 s]`; missed otherwise; confirmation latency = first in-window CONFIRMED minus the labelled event time; all
   other alerts in fall clips, and all alerts in normal clips, are false alerts (POSSIBLE and CONFIRMED separately, and per normal hour). One staged event per clip.
7. **Performance**: mean/p95 inference and engine ms, mean frame latency and single-stream maximum fps, tracked ids per clip.

## 2. Exact commands (PowerShell, from `backend/`)
Camera preflight (never records; run once per camera):
```powershell
$env:CCTV_URL_OFFICE1 = "rtsp://user:pass@192.168.1.20:554/stream1"
python -m tools.cctv_preflight --camera office-1=CCTV_URL_OFFICE1          # or: --db-camera office-1=3
```
First 60-second test, then its verification:
```powershell
python -m tools.cctv_record --camera office-1=CCTV_URL_OFFICE1 --duration 60 --out ..\validation\recordings\first_test
python -m tools.cctv_verify_recording ..\validation\recordings\first_test --expect-seconds 60 --camera-env CCTV_URL_OFFICE1 --require-rtsp
```
Label a recorded clip (after cutting it with `cctv_clip`, which prints the `event_time_s` to use):
```powershell
python -m tools.cctv_meta new ..\validation\independent\fall_standing\clip1.mkv --scenario fall_standing --camera-id office-1 --annotator AB
python -m tools.cctv_meta check ..\validation\tuning ..\validation\independent
```
Run validation:
```powershell
python -m tools.cctv_validate --footage ..\validation\independent --out ..\validation\results\indep_run1.json --md ..\validation\results\indep_run1.md
python -m tools.cctv_validate --footage ..\validation\tuning --out ..\validation\results\tuning_run1.json --configs default,conf015
```
Full step-by-step (recording, cutting, folder rules): `validation/README.md`.

## 3. What preflight and verification check
**Preflight** (one camera per run): dependencies and decoders; recording folder write test and free disk; available memory; DNS and TCP reachability from this
machine (distinguishes unresolvable name, refused port, timeout/other-network, no route); RTSP login (401), stream path (404), timeouts, unsupported
protocol, each with the likely cause; video stream present; codec (H.264/H.265/MJPEG supported, others FAIL); resolution; real frame decoding; measured fps
over the probe window; keyframe interval (affects where clips start); timestamp order; bitrate and disk use per hour. Passwords are never printed or saved.
**Verification of a recording**: playable, monotonic timestamps, sidecar complete, UTC start matches the file name, footage length matches the sidecar's media span and
(RTSP only) the time spent recording, readable by the runner's OpenCV decoder, no camera password/URL in sidecars, logs or video bytes, and which kind of source produced it.

## 4. Verified on file sources and a fake server (not real-camera tests)
| Check | Result |
|---|---|
| Test suite | 116 passed (63 new across the CCTV tools; 18 of them for the exported-footage workflow) |
| Preflight on a video file | passes and prints "LOCAL FILE, NOT A CAMERA"; says the result is about the tools only |
| Preflight vs a fake RTSP server answering 401 / 404 | explained as "rejected the login" / "no stream at that path"; password never in output |
| Preflight vs closed port / unresolvable host | reported as unreachable / DNS failure; does not try to open the stream |
| Dry run of the whole first-test sequence with a file as the "camera" (preflight, 60 s record, verify, cut clip, pre-filled label, validate with the real model) | every step ran; the verifier flagged "not a real-camera recording" and skipped the wall-clock checks; no credentials found |
| Bug found by the dry run | the duration check compared a file's wall-clock time with its video length; now applies to RTSP sources only, and the sidecar records the media span |
| Bug found by tests | `cctv_clip` copied the last frames when the requested range was beyond the recording; now an error |
| Bug found by tests | preflight read "Protocol not found" as an HTTP 404; fixed |
| Recorder CPU, remux, file source, 60 s | about 2 % of one core |
| Model speed on this machine during the dry run | 588 ms/frame (1.7 fps) with only ~1.9 GB RAM free, versus 204 ms measured earlier on a quieter machine: capacity numbers must be re-measured on an idle machine |

**Not verified until a real camera is used:** reachability and login against a real camera, vendor URL paths, H.265 cameras, reconnect after a real network drop,
frame timing and loss on a real network (the wall-clock check), several cameras at once, memory over hours, and everything about detection quality.

## 4b. Localhost RTSP rehearsal (simulator on port 8555): not a real-camera test
MediaMTX cannot run on this machine (an Application Control policy blocks `mediamtx.exe`; it was not bypassed), so `loadtest/local_rtsp_server.py` serves a looping H.264
file over real RTSP/TCP on `127.0.0.1:8555` with a throwaway login. It rehearses the exact first-test commands over an actual RTSP connection. **It is a simulator on loopback.**
```powershell
$env:LOCAL_RTSP_PASS = "any-throwaway-text"
python ..\loadtest\local_rtsp_server.py --video <an H.264 file> --port 8555 --path stream1 --user tester --password-env LOCAL_RTSP_PASS     # window 1, leave running
$env:CCTV_URL_OFFICE1 = "rtsp://tester:any-throwaway-text@127.0.0.1:8555/stream1"                                                          # window 2
python -m tools.cctv_preflight --camera office-1=CCTV_URL_OFFICE1
python -m tools.cctv_record --camera office-1=CCTV_URL_OFFICE1 --duration 60 --out ..\validation\recordings\first_test_localhost_sim
python -m tools.cctv_verify_recording ..\validation\recordings\first_test_localhost_sim --expect-seconds 60 --camera-env CCTV_URL_OFFICE1 --require-rtsp
```
Result of this rehearsal (video: a short clip made from URFD frames, 640x480 H.264 30 fps): preflight all OK (RTSP open, H.264, decoding, fps, keyframe 1 s);
recording 1 segment, 0 reconnects, 1768 packets, about 2.6 % of one core; verifier all checks passed, including the RTSP-only checks (footage 58.9 s = time recorded 58.9 s,
`source_kind: rtsp`) and no password in sidecars, logs or video bytes. Wrong password and wrong path are reported as "rejected the login" / "no stream at that path" (tests).
What this proves: the tools work over RTSP/TCP with authentication. What it does not: that a physical camera is reachable, its URL path, its codec/keyframe settings, or
network behaviour. `--require-rtsp` passing here is expected because the simulator is an RTSP server; the physical-camera proof (a time-stamped paper held up in front of the
camera) is a step only the real test can satisfy. Files: `validation/recordings/first_test_localhost_sim/` (simulated; not for validation) and `validation/results/first_test_localhost_sim_recorder.log`.

## 4c. Exported footage workflow (physical-camera login pending): FILE / EXPORTED FOOTAGE
Status of the physical camera: it is reachable and speaks RTSP over TLS, but the login returned 401, so no authenticated stream has been opened and no frame decoded. While the camera
owner arranges access (view-only account, RTSP permission, source-IP authorisation, or an approved LAN/VPN/NVR route), detection quality can be measured on **video files the owner exports**.
The step-by-step commands are in `validation/README.md`, section "Exported footage". Files are copied, untouched, into `validation/recordings/office_exported/`.

**Three different questions, three different kinds of evidence. Never mix them:**

| Question | Evidence that answers it | Status now |
|---|---|---|
| How well does the engine detect falls / avoid false alerts on office-camera footage? | exported files, cut, human-labelled, run through `cctv_validate` (**FILE / EXPORTED FOOTAGE**) | workflow ready; **no exported footage received, no results** |
| Can our tools connect to this camera over live RTSP and record it? | `cctv_preflight`, then `cctv_record` + `cctv_verify_recording --require-rtsp` | **NOT TESTED** (login 401) |
| Is a recording genuinely the live stream of the physical office camera? | the two above plus a time-marker held in front of the camera | **NOT DONE** |

How the tooling keeps them apart: every clip label carries `source_kind` (`exported_file`, `rtsp_recording`, `file_test`, `simulator`); `cctv_clip` marks cuts from a file that `cctv_record` did not make as
`exported_file`; and every validation report opens with a statement per source kind. For exported footage it says: *detection quality on exported video files only; live RTSP connectivity NOT tested; physical-camera
live validation NOT done.* Labels without a `source_kind` are reported as "unspecified".

**What the camera owner needs to provide**
- Video exports from the office camera or its recorder, one file per period, **MP4 or AVI, H.264 (H.265 also works), with the picture's time overlay visible** and the original resolution and frame rate (main stream, not a thumbnail sub-stream; 5 fps or more).
  Not usable: raw `.h264`/`.264` streams, proprietary `.dav` (re-export as MP4/AVI), clips under 360 px high.
- For each file: the **wall-clock time of its first frame with the time zone**, and the camera name.
- **Normal office activity:** at least 2-3 hours in total (the false-alert denominator): walking, desks, carrying things, several people, sitting and standing, bending, someone lying on a sofa or mat on purpose.
- **Staged falls** (consent, mats, supervision): falls from standing and from a chair, forward / backward / sideways, and one with the person getting up. Each with the **exact time** the person reaches the floor (to the second) and **20+ seconds of footage after it**.
  Keep a note of who staged each one. Record a second day or camera for the held-out (`independent/`) set; it must not be used to adjust any setting.
- Written consent for recording and storing the footage, and a retention period. Footage stays on this machine and is git-ignored.

**What has been verified (files generated by the tools; no real export has been received)**

| Check | Result |
|---|---|
| Formats | mp4, avi (H.264, MJPEG, MPEG-4), mov, ts, H.265 mp4 decode in both PyAV and OpenCV and can be cut; raw `.h264` has no timestamps (OpenCV guessed 25 fps for a 15 fps file, so event times would be wrong): now refused with the fix to ask for |
| `cctv_inspect` | READY / USABLE WITH WARNINGS / UNUSABLE per file (readability, timestamps, fps measured from timestamps, gaps, keyframes, PyAV vs OpenCV agreement), SHA-256 inventory; never modifies the files |
| Cut times | measured from the first frame (container timestamp origin removed); a local time with a UTC offset (+05:30) is converted to UTC; a time without a time zone is refused |
| Labels / report | `source_kind` validated; unsupported files in a scenario folder produce a warning instead of being silently skipped; the report banner changes with the source kind |
| Dry run with a generated mp4 as the "export" (inspect, cut with `--source-start`, label, check, validate with the real model) | every step ran and the report carried the FILE / EXPORTED FOOTAGE statement. The clip's label was an arbitrary placeholder, so its numbers are not results and are not reported |

## 4d. Physical-camera sweep (REAL PHYSICAL CAMERAS, 2026-11-19): all seven cameras connect and decode
Tool: `backend/tools/cctv_sweep.py` (one login attempt per camera; stops at the first rejected login; password via hidden prompt or environment variable, never printed or saved).
Credentials used: the account from the owner's camera sheet (not recorded anywhere in the project). Host `144.79.198.46`, path `/video/live?channel=1&subtype=0`, all over **RTSP over TLS (`rtsps://`)**.

| Camera (owner's sheet) | Port | Result | Codec / size | fps (approximate, see note) |
|---|---|---|---|---|
| Main Hall 1 | 91 | WORKING | H.265 1920x1080 | 32 |
| Main Hall 2 | 90 | WORKING | H.265 1920x1080 | 13 |
| Lift Gate | 92 | WORKING | H.265 1920x1080 | 12 |
| Technical Section | 93 | WORKING | H.265 1920x1080 | 12 |
| Lobby | 554 | WORKING | H.265 1920x1080 | 20 |
| Entry | 94 | WORKING | H.265 1920x1080 | 11 |
| Exit | 31 | WORKING (the sheet lists it as Offline) | H.265 1920x1080 | 27 |

Notes: fps was measured over a 6 s probe from packet arrival and includes the initial burst, so treat it as a rough figure (the preflight measures over 8 s; a recording gives the real rate).
"WORKING" means an authenticated stream opened and frames decoded. It does **not** yet prove that each stream is the live view of the camera it is named after: the time-marker (liveness) test is still to do for the camera used.
Nothing has been recorded from these cameras yet. The earlier 401 with the first-supplied password means that password was not valid for these accounts; the sheet's account works.
The 1080p H.265 streams are heavier to decode than the 640x480 H.264 test files; capacity must be re-measured on this machine.

## 5. Camera access and consent required
- The RTSP URL (user, password, host, port, path) of one office camera, reachable from the machine that records. If the preflight says the address is private and
  unreachable, run the recorder on that network or over VPN. Alternatively add the camera in the backend and use `--db-camera`.
- Whether the camera exposes an H.264 stream (preferred; H.265 usually works; set the I-frame interval to 1-2 s).
- Written consent from everyone filmed, for recording, staged falls and storage; a retention period; recordings stay on this machine (git-ignored).
- Safe staging: mats, supervision, people who decide their own participation.

## 6. Results
Fall detection, false alerts, missed falls, confirmation latency, real-camera performance and the configuration comparison: **not run (no footage).**
Planned comparison: `default` (detector conf 0.4, `min_person_conf` 0.4: what ships) against `conf015` (0.15 / 0.15) and any `--config` you define. **0.15 is not a
default and is not recommended** on URFD evidence (it added detections, some from single boxes with no keypoints, and lower confidence admits more spurious
boxes). Judge it on normal-footage false alerts first (false CONFIRMED per hour, then false POSSIBLE). A setting chosen on `tuning/` footage must be tested on
`independent/` footage it was not chosen on.

## 7. Limitations
- Counts only ("k of n"); no accuracy, precision or recall percentage, because the sample will be small and the labels one person's.
- One staged event per clip; approximate event times; 5 fps analysis; volunteers fall more carefully than real people.
- A validation on one camera does not transfer to another position or angle.
- Everything inherits the engine's documented limits (`LIMITATIONS.md`).
- The 588 ms/frame above means this machine, when busy, analyses well under 5 fps for one stream: long normal footage will take longer than real time to process.

## 8. Remaining requirements for the first real camera test
1. Camera URL reachable from this machine, and consent (section 5).
2. Run the preflight; fix any FAIL; then the 60-second test and its verification (section 2). Only after both pass, record the real footage.
3. Free memory: close other programs before validation runs (the machine had about 1.9 GB free).
4. People and time for the staged scenarios and for labelling; a second day or camera for the `independent/` split.

## 9. Files
Exported-footage round added `backend/tools/cctv_inspect.py`, `backend/tests/test_cctv_exported.py`, the folder `validation/recordings/office_exported/`; changed (tools only) `cctv_meta.py` (`source_kind`, ignored-file warning), `cctv_clip.py` (first-frame time origin, `--source-start`, clean errors), `cctv_validate.py` (source-kind banner), `validation/README.md`, this document. Earlier: added `loadtest/local_rtsp_server.py` (test simulator), `backend/tests/test_rtsp_sim.py`, `backend/tools/cctv_preflight.py`, `cctv_verify_recording.py`, `cctv_clip.py`; tests `test_cctv_preflight.py`, `test_cctv_workflow.py`.
Changed (tools only): `cctv_record.py` (sidecar adds source kind, codec, media span), `cctv_meta.py` (clean errors, pre-fill from sidecar, check several folders),
`cctv_validate.py` (default to `independent/`, role label, overlap refusal), `tests/test_cctv.py` (unchanged tests). `validation/` re-organised into `tuning/` and
`independent/` (was `footage/`, empty), `validation/README.md` rewritten, `.gitignore` updated. Not touched: detection engine, default detector confidence,
the 3 s confirmation, SMC, MediaMTX.
