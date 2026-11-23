# Resumption checklist: pose model and person-scale experiment

Status when written (2026-11-23, about 11:20): the pose model cannot load because Windows Smart App Control blocks PyTorch. **Nothing in this checklist has been run.** It exists so work can resume safely, step by step, once a security administrator has resolved the block. It does not describe, and must not be used for, any way around the policy.

## A. Verified current state (read-only checks at 11:17-11:20)
| Item | Finding |
|---|---|
| Backend | running (process started 11:13, listening on 127.0.0.1:8830); dashboard answers HTTP 200 |
| Camera video | camera 6 is streaming (about 22-26 fps read, about 11 fps published) |
| Pose inference | **failing**: 6 failures in a row in `validation/results/backend_20261123_111318.err.log`, each `WinError 4551` (Application Control blocked `torch_python.dll`); the backend keeps retrying |
| PyTorch import | **blocked** (`import torch` and `import ultralytics` both fail with `WinError 4551`) |
| Model file | `backend/models/yolov8n-pose.pt` is present (6,832,633 bytes); it was **not** loaded, because PyTorch cannot be imported |
| Smart App Control | registry `VerifiedAndReputablePolicyState` = **1**, which I read as *Enforcement* (0 = Off, 2 = Evaluation); please confirm in Windows Security -> App & browser control |
| Blocked files (last 2 h) | `...\Python312\Lib\site-packages\torch\lib\torch_python.dll` (unsigned, 20,270,080 bytes, last written 2026-09-14, package torch 2.14.0) and `...\SMC\backend\.venv\Lib\site-packages\onnx\onnx_cpp2py_export.pyd` |
| When it started | **first observed at 11:12** on 2026-11-23. The last time the pose model is known to have run was Monday ~10:32 (backend started 10:04; `pose analysis` lines of 65-99 ms per frame, ~6,400 inferences). **No process imported PyTorch between about 10:32 and 11:12**, so the block may have begun at any time in that window. |
| Earlier occurrence | the **same file** `torch_python.dll` was blocked before: **2026-11-15 18:41**. It then loaded normally again (Saturday 21 Nov and Monday morning ran the pose model). Other earlier blocks: `pip.exe` (11-14), files under `Desktop\FALL...` (11-19), an SMC `onnx_cpp2py_export.pyd` (11-21 14:28). So Smart App Control's decision about this unsigned file is **intermittent** |
| What did NOT change | no Code Integrity policy refresh or state-change events today (the last policy activation was at boot on Saturday 21 Nov 11:25, after which PyTorch ran fine); no reboot since then; the DLL itself is unchanged (written 2026-09-14); two Windows updates (KB5132056, KB5132057) were installed on Saturday morning, **before** the successful Saturday afternoon run |
| Event log | `Microsoft-Windows-CodeIntegrity/Operational`, events 3033, 3077, 3089, 3118 ("Smart App Control Block"); the backend's retries keep adding events |
| Experiment data | 5 scales x 80 = 400 copies, **no** partial `.part.avi` files, **0** pose caches, **no** result files; `validation/experiments` is now **20 GB** |
| Experiment logs | `validation/results/person_scale_run.log`, `person_scale_<s>.log` (the five failed attempts, all `WinError 4551`), `person_scale_make_<s>.log` |
| Dataset originals | 168 files checked, **0 changed or missing** (SHA-256 against the manifest) |
| Code | `engine.py`, `config.py`, `track_history.py`, `settings_store.py`, `cctv_validate.py`, `cctv_meta.py`, `gmdcsa_eval.py` are byte-identical to the frozen record in `validation/datasets/gmdcsa24/frozen_config.json`; `min_person_conf` 0.4, `confirm_seconds` 3.0 |
| Git | the repository root is the **home folder**; this project's files show as untracked (`??`), nothing is committed, 228 entries are changed or untracked in total. All of this work exists only on disk |

## B. Security administrator action required (information to hand over)
The decision belongs to whoever owns this machine's security policy. Useful facts: Smart App Control is in enforcement mode; the blocked PyTorch library is unsigned; PyTorch loaded normally until 11:12 today; an SMC component was blocked at the same time; the log events are listed above. Possible outcomes the administrator may choose between (not for us to decide or to carry out): allow this Python environment under an approved policy, provide an approved or signed build of the libraries, or provide a different approved machine. **Do not disable Smart App Control, add exclusions, or move or rename files to get around it.** Record who resolved it, what changed, and when.

*Note on the paragraph above (added 2026-11-23, after further checks):* "PyTorch loaded normally until 11:12 today" is imprecise. The pose model is known to have run until about 10:32 (see B.3); the block was **first noticed** at about 11:12 and is **not shown to have begun then**. Sections B.1 to B.5 separate what Windows recorded from what is interpreted and what is still unknown.

### B.1 Directly recorded Windows event details
Source: Windows log `Microsoft-Windows-CodeIntegrity/Operational`, read on 2026-11-23 (read-only).
| Item | Recorded value |
|---|---|
| Blocked file | `C:\Users\lenovo\AppData\Local\Programs\Python\Python312\Lib\site-packages\torch\lib\torch_python.dll` (a library required by PyTorch) |
| Process that tried to load it | `C:\Users\lenovo\AppData\Local\Programs\Python\Python312\python.exe` |
| First records of the 23 Nov block | event 3033 and event 3118 ("Smart App Control Block Details") at **11:12:12** on 2026-11-23; events 3077 and 3089 follow in the same period |
| Event 3033 fields (23 Nov 11:12:12) | `RequestedPolicy` = 2; `ValidatedPolicy` = 1; `Status` = 3236495362 (0xC0E90002). The meaning of these numbers is **not interpreted** here |
| Event 3118 fields (23 Nov 11:12:12) | `SHA256FlatHash` = the fingerprint in B.2; `DefenderCalled` = true; `DefenderCloudCallRequested` = true; `DefenderMadeCloudCall` = true; `TTLValid` = false; `EADefenderTrustCached` = false; `CachedDefenderTrust` = 122235; `CachedDefenderTrustExpiryTime` = 0; `DefenderDisabled` = false; `IsUnfriendlyFile` = false; `DefenderTrust` = -16777216; `DefenderCloudHTTPCode` = 0xc8000000; `DefenderStatusCode` = 0x0. The numeric result fields (`DefenderTrust`, `CachedDefenderTrust`, `DefenderCloudHTTPCode`) are **not decoded** here |
| Earlier record of the same file | event 3033 at **2026-11-15 18:41:23**: same file, same process, same `RequestedPolicy` (2), `ValidatedPolicy` (1) and `Status` (3236495362) as on 23 Nov. **The 15 Nov event 3118 detail record was not read**, so it is not verified whether it also shows `TTLValid` = false or a cloud call |
| Smart App Control mode | registry `VerifiedAndReputablePolicyState` = 1, read as Enforcement (0 = Off, 2 = Evaluation); not yet confirmed in Windows Security |
| Other file blocked in the same period | `C:\Users\lenovo\Desktop\SMC\backend\.venv\Lib\site-packages\onnx\onnx_cpp2py_export.pyd` (an SMC component) |
| Earlier blocking events for this file on 23 Nov | none recorded before 11:12:12 (checked at about 11:20) |

### B.2 File hashes and timestamps (read from the file without loading it)
| Item | Value |
|---|---|
| SHA-256 of `torch_python.dll` | `68C8C60F013FF1E760F13B1B02AFEE23D4BE9C52AD7A85FC3CF66D90A5D73A30` |
| Where it was checked | **identical** in the event 3118 record (11:12:12) and in a read-only hash of the file on disk made afterwards on 2026-11-23 |
| Size / last written | 20,270,080 bytes; 2026-09-14 15:05:45 |
| Digital signature | Authenticode status `NotSigned`; no downloaded-from-internet mark (`Zone.Identifier`) |
| Package versions | torch 2.14.0 (2.14.0+cpu as recorded on 2026-11-21), ultralytics 8.4.151, Python 3.12.10, OpenCV 5.0.0: the same as recorded before the freeze |
| Python install | no file in `site-packages` modified in the 4 days before the check; no executable-type file (exe, dll, pyd, sys, msi, bat, cmd, ps1, vbs) created or changed in the Python install since 2026-11-20; `python.exe` last written 2025-04-08, signature Valid; `torch\lib` holds 9 DLLs, 7 unsigned, newest written 2026-09-14 |
| Project files | the only executable-type file created or changed in the project since 2026-11-20 is `run_fall_detection.ps1` (last written 2026-11-21 14:29, before the successful runs of 21 and 23 Nov) |

### B.3 Timeline: recorded facts versus what is not established
| Time (2026-11-23) | Fact |
|---|---|
| 10:04 | the backend process was started (log `validation/results/backend_20261123_100448.err.log`) |
| about 10:29 to 10:32 | the four last `pose analysis` log lines report 65, 78, 73 and 99 ms average per frame (3 threads), 6,371 inferences by 10:32: **PyTorch was running** |
| about 10:32 | that backend process was stopped (by us, to run the experiment) |
| 10:34 to 11:11 | the experiment's copy stage ran; reading its code, it imports OpenCV, NumPy and project code but **not PyTorch** |
| **11:12:12** | first recorded block; the first timed pose run tried to import PyTorch and failed (`WinError 4551`) |
| 11:13 | the backend was restarted with the normal script; its pose worker failed with the same error |
**Not established:** the time the block began. No process imported PyTorch between about 10:32 and 11:12, so it may have begun anywhere in that interval, or earlier and been hidden by the process that was already running. The block is **first noticed at about 11:12**, not proven to start then.

### B.4 Interpretation (NOT proven by the logs)
1. **Expired stored decision, then a fresh online check.** `TTLValid` = false, `CachedDefenderTrustExpiryTime` = 0 and `EADefenderTrustCached` = false, together with `DefenderCloudCallRequested` and `DefenderMadeCloudCall` = true, are *consistent with* Smart App Control having no valid stored trust decision for this file, asking Microsoft's online reputation service, and then blocking it. This is an interpretation of the field names; Microsoft's documentation of these fields was not consulted, and the logs do not state the reason in words.
2. **Why it appeared after the backend was stopped.** Stopping the backend ended the only process that already had PyTorch loaded; the next process that loaded the DLL needed Windows to evaluate it again. That a process that already has a library loaded keeps working is general behaviour, not something these logs show, and the block may have existed earlier.
3. **15 Nov.** Only the identical event 3033 values are verified for that date (B.1); that it shared the same cause is an assumption.

### B.5 Still unknown
- **Why Microsoft's reputation service returned a blocking decision** for this file (the numeric result fields are not decoded here).
- Whether the decision will change again (the same file loaded normally again after 15 Nov).
- Why the outcome differs between days.
- Whether the block began before 11:12.
- Whether the SMC `onnx_cpp2py_export.pyd` block shares the cause (the pattern of events was seen at the same time; the cause is not known).
- Nothing in the checks found a change by us (package files, versions, executable-type files, the experiment's code) that would explain it; that is an absence of evidence, not a proof.

### B.6 What to hand to the administrator
File: `...\Python312\Lib\site-packages\torch\lib\torch_python.dll`, SHA-256 `68C8C60F013FF1E760F13B1B02AFEE23D4BE9C52AD7A85FC3CF66D90A5D73A30`, unsigned, torch 2.14.0; Smart App Control registry state 1 (Enforcement, to be confirmed); first noticed block 2026-11-23 about 11:12 (event 3033/3118), earlier block of the same file 2026-11-15 18:41; the pose model last ran about 10:32 that morning; the SMC file `...\onnx\onnx_cpp2py_export.pyd` was blocked in the same period; the log is `Microsoft-Windows-CodeIntegrity/Operational`.

## C. Steps once the administrator confirms the block is resolved
Stop at the first failing step and report it; do not continue past a failure.

1. **Record the confirmation** (who, when, what was changed) in the project notes.
2. **Plain import check, nothing changed:**
   `python -c "import torch; print(torch.__version__)"` and `python -c "import ultralytics; print(ultralytics.__version__)"`. Pass: both print a version.
3. **Pose-model load and one real inference** (from `backend/`; reads a frame from an existing clip, writes nothing):
   ```
   python - <<'E'
   import cv2, time
   from ultralytics import YOLO
   cap = cv2.VideoCapture("../validation/tuning/fall_sideways/gmdcsa24_s2_fall_05.mp4"); cap.set(cv2.CAP_PROP_POS_FRAMES, 10); ok, f = cap.read()
   m = YOLO("models/yolov8n-pose.pt"); t = time.time(); r = m(f, conf=0.4, imgsz=640, verbose=False)[0]
   print("persons", len(r.boxes), "keypoints", tuple(r.keypoints.data.shape), "ms", round((time.time()-t)*1000))
   E
   ```
   Pass: at least one person and a keypoint shape of `(n, 17, 3)`.
4. **Confirm live detection works again** (restarting the backend needs explicit approval): after a restart, `validation/results/backend_<stamp>.err.log` must contain **no** `WinError 4551` line, must show the once-a-minute `pose analysis N ms average` line with a rising `run` count, and the live view must show boxes and skeletons on a real person. **Detection counts as restored only when an actual inference has succeeded**, not when the dashboard merely answers.
5. **Run the full test suite** (`python -m pytest -q` in `backend/`). It was 145 passed before the new experiment tests; 2 more were added (`tests/test_scale_experiment.py`, 2 passed alone), so **147 is the expected total** (an expectation, not yet verified). Report any failure with its output.
6. **Prepare a clean machine state (approval needed to stop the backend):** `run_fall_detection.ps1 -Stop`; confirm the CPU is idle (no process above about 10%); do not touch SMC.
7. **Run the experiment** from `backend/`, one scale at a time, control first (`1p00`), exactly as in `docs/PERSON_SCALE_EXPERIMENT.md` section 4. If a scale exits non-zero or logs `4551`, stop; keep its log; do not delete it. The runner never overwrites an existing `--out`; for a retry use a new name (for example `person_scale_1p00_attempt2.json`).
8. **Verify the measurements are real and complete for all five scales:**
   - each `validation/experiments/person_scale/scale_<s>/cache/yolov8n-pose_conf0.4_fps5.0_sz640/` holds **80** `.pkl` files;
   - each `validation/results/person_scale_<s>.json` has `clips_scored` 80 and no skipped clips;
   - `person_scale_metrics.json` lists **five** scales, each with `clips` 80 and the **same** `reference_persons` (the reference is the 1.0 control), `inference_ms.n` > 0, no empty or `null` fields;
   - the control (1.0) must reproduce itself: detection recall vs scale 1.0 = 1.0 and extra boxes = 0;
   - compare the control's person-frame counts with the earlier tuning-set cache (`validation/cache/yolov8n-pose_conf0.4_fps5.0_sz640`): a large gap means the copies or the environment differ and must be investigated before anything is reported;
   - timings are comparable only because the backend was stopped; say so in the report.
9. **Preserve logs and report failures honestly:** keep every log and partial output; report a scale that failed or was cut short as "incomplete (n of 80 clips)"; never fill gaps with estimates, interpolation or numbers from another scale; label every table "adult footage, scaled, not child".
10. **Restart the backend** and repeat step 4.

## D. What the experiment actually measures (and what it does not)
**Measures** (adult clips of the GMDCSA-24 tuning split, shrunk to 1.0 / 0.75 / 0.5 / 0.35 / 0.25 of their size on a grey canvas of the original size, lossless): how the output of the unchanged YOLOv8n-Pose + ByteTrack changes as the same adult looks smaller: person-detection recall relative to the 1.0 control, extra boxes, detector and joint confidence, visible and missing joints, whether the torso angle can still be computed, keypoint position deviation and frame-to-frame jitter, track ids per clip, per-frame inference time, and (through the unchanged runner) POSSIBLE and CONFIRMED events and false alerts, reported separately.
**Does not measure:** anything about children (proportions, movement, clothing, falls); accuracy against ground truth (the reference is YOLO itself at 1.0); real distance effects (perspective, focus, noise); other cameras or rooms. **Resizing adult footage does not validate child fall detection**, and no threshold may be tuned from it.
