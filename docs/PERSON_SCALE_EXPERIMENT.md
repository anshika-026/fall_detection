# Smaller-person experiment on adult footage

**Status (2026-11-23): PREPARED BUT NOT MEASURED.** The 400 scaled copies are built and the measurement code is tested, but **the pose model could not run**: from 11:12 Windows Smart App Control blocked PyTorch's `torch_python.dll`, so no detection, keypoint, stability, timing or fall-event numbers exist yet. No result in this file should be quoted as a finding. The paragraphs below describe the design, what is known, what is not, and how to finish the run.

This experiment uses **adult** footage only. It is **not child validation** and must never be described as such.

## 1. What was done
| Item | Detail |
|---|---|
| Source footage | the GMDCSA-24 *tuning* split (80 clips; adults; hard links to the untouched originals). The independent split was not used. Originals re-checked after the copies were made: 168 files, **0 changed**. |
| Copies | 5 scales x 80 clips = **400 copies**, all complete, in `validation/experiments/person_scale/scale_<s>/tuning/<scenario>/` (about 17 GB, git-ignored, regenerable). Scales: **1.0 (control), 0.75, 0.5, 0.35, 0.25**. |
| Transform | each frame is shrunk by the scale (INTER_AREA) and pasted in the **centre** of a canvas of the **original size** filled with YOLO's letterbox grey (114). So frame size, fps, frame count and timeline are unchanged and the person simply looks smaller, like standing further away. Written **losslessly (FFV1 AVI)** so no extra compression is added. Scale 1.0 goes through the same pipeline with no shrink (control). |
| Labels | each copy has the original label file plus a note "SCALED ADULT COPY ... (not child footage)" and a `scale_experiment` block (scale, source clip, frame size, fps, frames). Event times are unchanged. |
| Provenance | `validation/experiments/person_scale/manifest_scale_<s>.json` per scale. |
| Tool | `backend/tools/scale_experiment.py` (`make`, `measure`); tested by `backend/tests/test_scale_experiment.py` on synthetic data (2 tests pass). |
| Detector and engine | **unchanged**: the existing `tools/cctv_validate.py` pipeline (YOLOv8n-Pose, ByteTrack, confidence 0.4, 640 px, 5 analysed fps, shipped engine settings, 3 s confirmation). Nothing in `engine.py` or the detector was modified. |

Apparent person size at each scale (before any measurement): the person's height in the 640-px model input is the scale times its height at 1.0. For a person about 60% of the frame height at 1.0, that is roughly 290, 215, 145, 100 and 70 px at scales 1.0, 0.75, 0.5, 0.35 and 0.25 for a 720p frame. `measure` records the real medians.

## 2. Why the run did not finish
At 11:11 the copies were finished and the timed pose runs started; each failed within seconds with
`OSError: [WinError 4551] An Application Control policy has blocked this file. Error loading ...\torch\lib\torch_python.dll`.
The Windows Code Integrity log (`Microsoft-Windows-CodeIntegrity/Operational`) shows **Smart App Control** blocking `python.exe` from loading libraries from 11:12:29 onwards (events 3033, 3077, 3089, 3118); some of the blocked events concern an SMC Python environment, so this is not specific to this project. PyTorch had loaded normally earlier the same day (the backend started at 10:04 and ran the pose model until about 10:32, and on Saturday); the block is therefore **first observed** at 11:12, not proven to start then, because no process imported PyTorch between about 10:32 and 11:12. **The same DLL was also blocked once before (2026-11-15 18:41) and later worked again**, so the block is intermittent; the cause of the change was not established. I did **not** try to bypass, disable or work around the policy, and I do not recommend that without whoever owns this machine's security policy deciding it.
Consequences right now: the dashboard answers (HTTP 200) but **live fall detection is not running** because the pose model cannot load. The backend keeps retrying and will recover on its own if torch becomes loadable.

## 3. What will be measured (unchanged plan)
All measured per scale, against **YOLOv8n-Pose at scale 1.0 as the reference**, which is **not human-labelled ground truth**:
1. **Person detection:** recall of the scale-1.0 persons (box overlap >= 0.5 after mapping the box through the transform), share of frames with any person, extra boxes per frame, mean detector confidence.
2. **Keypoint confidence and visibility:** mean joint confidence, visible joints of 17 (threshold 0.4), per group (head, shoulders, hips, ankles).
3. **Missing joints and engine inputs:** mean missing joints, share of frames where a torso angle can be computed (needs shoulders and hips), share flagged `partial`.
4. **Pose stability:** keypoint position deviation from the scale-1.0 pose (in person heights, positions mapped back), frame-to-frame jitter of mid-shoulder and mid-hip, track ids per clip.
5. **Processing time:** per-frame inference time (mean, median, 95th percentile) with the live backend stopped, so nothing competes for the CPU.
6. **Fall pipeline:** the unchanged runner at each scale; POSSIBLE and CONFIRMED detections, false POSSIBLE and false CONFIRMED reported **separately** by `tools/gmdcsa_eval.py`. No threshold is changed or tuned from this.

## 4. How to finish the run (when PyTorch can load again)
Prerequisite: `python -c "import torch"` works. **Stop the Fall Detection backend first** (`run_fall_detection.ps1 -Stop`) so the timings are clean. From `backend/`:
```
for s in 1p00 0p75 0p50 0p35 0p25; do
  python -m tools.cctv_validate --footage ../validation/experiments/person_scale/scale_$s/tuning --cache ../validation/experiments/person_scale/scale_$s/cache \
     --out ../validation/results/person_scale_$s.json --md ../validation/results/person_scale_$s.md --configs default
done
python -m tools.scale_experiment measure --out ../validation/results/person_scale_metrics
python -m tools.gmdcsa_eval --report ../validation/results/person_scale_<s>.json --out ../validation/results/person_scale_<s>_metrics     # per scale
```
(The failed attempts wrote no `.json`, so the runner will not refuse to overwrite. Expect roughly 8 to 10 minutes per scale.) Restart the backend afterwards.

## 5. Limitations (stated before any number exists)
- **Resized adults are not children.** Shrinking an adult only reduces apparent size. It does not reproduce children's proportions (for example a relatively larger head), how they move (crawling, running, sitting and playing on the floor), their clothing, or how their falls look. A result here says how YOLOv8n-Pose copes with a *small adult*, nothing more.
- **Distance is simulated crudely:** the picture is shrunk about its centre; a real distant person would also sit higher in the image, have different perspective, lighting and sensor noise, and the camera would not be re-focused. The grey border is an artefact the model has not seen in real footage.
- **The reference is YOLO itself.** Differences from scale 1.0 show how much the model's output changes, not how accurate it is; there are no human-labelled boxes or keypoints.
- **One dataset, adults only, one camera model, a few rooms, short clips:** results may not carry over to the office camera.
- **The fall results (when measured) cannot be read as child-fall performance** and must not be used to tune any threshold.

## 6. Questions the finished run will answer, and what stays open
| Question | Status |
|---|---|
| Does person *detection* or *keypoint quality* become the bottleneck as people get smaller? | **Unknown until measured.** The detection-recall and joint-visibility rows separate the two. |
| Does the fall engine still receive valid inputs at smaller scales? | **Unknown.** The torso-angle-computable and `partial` rows, and the number of frames where people are found, will show it. |
| What evidence is needed before considering ChildPose? | See below. |

**Evidence needed before ChildPose is worth considering (independent of this experiment):** (1) the authors' written permission for even an internal comparison (draft A in `docs/CHILD_RESEARCH_EMAIL_DRAFTS.md`) and a clear commercial-licence route; (2) measured evidence that YOLOv8n-Pose's person boxes and keypoints actually fail on **real children** (this experiment cannot show that); (3) consented, ethically approved child footage from our camera viewpoints, including normal child activity (crawling, running, jumping, floor play); (4) a small human-labelled keypoint set so any quality claim has a ground truth; (5) a downstream replay through the unchanged engine showing no loss on the adult baseline; (6) a decision on the target ages, since ChildPose has almost no teenagers in its age-labelled data.
