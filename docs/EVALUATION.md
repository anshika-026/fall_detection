# Evaluation of the fall engine (measured results only)

Every number below was produced by `backend/tools/eval_urfd.py` and is stored in `docs/eval/*.json` / `*.log`.
No accuracy, precision, recall, F1 or similar metric has been computed, because the dataset has only
sequence-level labels and the sample is tiny. Counts are given as counts.

## 1. Dataset and method

- **Dataset:** UR Fall Detection (Kwolek & Kepski, Univ. of Rzeszow), camera 0 RGB, licence CC BY-NC-SA 4.0
  (non-commercial academic use). Stored under `datasets/` (git-ignored, not redistributed).
- **Sequences used:** 30 fall sequences (`fall-01` … `fall-30`); 16 of the 40 activity-of-daily-living (ADL)
  sequences (the rest were not downloaded successfully).
- **Labels:** sequence-level only (file name: `fall-*` / `adl-*`). There are no per-frame labels, so
  detection *timing* accuracy cannot be measured.
- **Chain tested:** real `yolov8n-pose` (or s/m) + ultralytics ByteTrack → `CameraFallEngine` → events.
  Frames are sub-sampled from 30 fps to 5 fps (the live default), detector confidence 0.4, imgsz 640,
  sensitivity "medium", confirm time 3.0 s.
- **Outcomes per fall sequence:** *missed* (no POSSIBLE event), *possible only*, *confirmed*.
  Per ADL sequence: *false possible*, *false confirmed*.

### POSSIBLE vs CONFIRMED
- **POSSIBLE** = a rapid descent ending in a lying posture was seen. Not alert-worthy by itself.
- **CONFIRMED** = the person then stayed down and still for `confirm_seconds` (3 s; 4.5 s if partly visible).
  Only CONFIRMED raises an alert.
- The URFD clips are 2–7 s long at the analysed rate (10–36 analysed frames) and mostly end shortly after the
  person reaches the floor, so **a clip cannot contain a 3 s confirmation window**. 0 confirmations in the
  no-hold runs is therefore expected and says nothing about confirmation quality.

## 2. Pose-model comparison (30 falls, default settings, no hold-last)

| Model | Possible | Confirmed | Missed | Mean inference | p95 inference | Run time |
|---|---:|---:|---:|---:|---:|---:|
| yolov8n-pose | 8 | 0 | 22 | 204 ms | 347 ms | 2.3 min |
| yolov8s-pose | 9 | 0 | 21 | 479 ms | 944 ms | 4.6 min |
| yolov8m-pose | 8 | 0 | 22 | 1770 ms | 3896 ms | 15.9 min |

Files: `urfd_falls_yolov8{n,s,m}.json`. Inference = wall time of one `model.track()` call, CPU only, on a machine
that was under memory pressure (up to ~92 % used), so absolute timings are pessimistic and not a benchmark.
Differences of 1 sequence out of 30 are within noise.

**Why yolov8n-pose was kept:** a 9× larger inference cost (m) and 2.3× (s) bought no meaningful gain
(8 / 9 / 8 detected). The comparison is the measured evidence; no larger model is justified on this data.

## 3. Other runs (all yolov8n-pose)

| Run (file) | Engine state | Result |
|---|---|---|
| `urfd_falls_default` | first untuned engine | 30 falls: 9 possible, 0 confirmed, 21 missed |
| `urfd_falls_v2` | after changes made while looking at these same 30 sequences | 8 possible, 0 confirmed, 22 missed |
| `urfd_falls_v2_hold6` | v2, last frame frozen for 6 s | 5 confirmed, 3 possible only, 22 missed |
| `urfd_adl_v2` | v2, 16 ADL sequences | 0 false confirmed, 0 false possible |

- v2 was **tuned on the evaluation sequences**. It is reported only to show that those changes did not
  improve the real-video result (9 → 8). It must not be quoted as accuracy. The untuned figure is `default`.
- **Hold-last is an emulation, not footage.** Freezing the last frame guarantees a person who is "still";
  it demonstrates that the confirm logic can fire on real pose output (3.0–4.6 s after POSSIBLE) but is
  not evidence that real falls are confirmed. Real recovery (getting up) was never exercised on real video.
- The ADL result (0/16) is weak evidence: 16 short clips, and which of them contain hard cases
  (sitting down fast, lying down deliberately) was not audited.

## 4. Misses and their likely causes

About 22 of 30 falls never reach POSSIBLE with any of the three models. In nearly all missed sequences the
detector *did* find a person in almost every analysed frame (e.g. fall-02 19/19, fall-06 17/17,
fall-14 11/11, fall-22 10/10 frames with a person, from `urfd_falls_yolov8n.json`). So the person is
detected; the engine does not conclude "fall". Because the larger models miss the same ones, pose quality is
not the main limit. Hypotheses from earlier per-sequence diagnosis (not proven for every sequence):
1. **No standing reference learned** (~11/30): the engine measures drops in units of the person's standing
   height, and clips that start with the person already low, close to the camera or cropped never provide it.
2. **Lying posture never voted** (~14/30): at floor level and a shallow camera angle, torso angle and
   keypoint extent degrade, legs are hidden or the person is partly outside the frame.
3. Clips are very short, so the descent window and the "was upright within 4 s" rule have little context.
4. Camera 0 in URFD is a low, floor-parallel view; real CCTV is usually higher and angled down. The
   engine's assumptions may fit that better or worse; that is unknown until tested.

## 5. What has and has not been validated

Validated (measured):
- The pipeline runs end to end on real pose/tracker output and real video frames.
- Engine logic on synthetic skeletons (26 scenario tests, in `backend/tests/`; these test the logic against
  scripted motion, not real people).
- No false confirmed/possible on 16 ADL clips.
- Inference cost of three pose models on this CPU.

Not validated:
- Fall detection accuracy on any real or CCTV footage. **The system is not production-ready.**
- Confirmation, recovery and resolution on real footage.
- False-alarm rate over hours of normal activity (beds, sofas, exercise, crouching, objects, multiple people).
- Performance with a GPU, other camera heights/angles, night/IR, H.265 or real cameras.
- Any recall/precision figure: none exists.

## 6. Next evaluation steps
Run the engine on recorded footage from the actual cameras with someone staging falls and normal activities
(labelled per event, with timestamps), measure false alarms per camera-hour on ordinary footage, and only then
tune thresholds, on one set of footage and measure on another.
