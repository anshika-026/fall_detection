# Fall-engine diagnosis: why 22 of 30 URFD falls never reached POSSIBLE

Everything here was measured on the 30 UR Fall sequences (camera 0 RGB, 5 fps, yolov8n-pose, default settings)
and the 16 ADL sequences available locally. **All of it is diagnostic or tuning work on those same sequences.
Nothing in this document is independent accuracy.** Original baseline files (`docs/eval/urfd_falls_*.json`) are unchanged.

Reproduce: `python -m tools.pose_cache` (runs the model once, caches per-frame output), `python -m tools.diagnose_urfd`,
`python -m tools.diagnose_table`, `python -m tools.replay_eval --out ...` (all in `backend/`).
Because the model output is cached, every engine version below sees the **same detections and track ids**: differences
come from the engine only. The replay of the unmodified engine reproduced the recorded baseline exactly (same 8 detected, same 22 missed).

## 1. What must be true for POSSIBLE (original engine)

| # | Gate | Exact condition |
|---|---|---|
| G1 | person | ByteTrack returned a box **with a track id**, detector conf >= 0.4 (`conf`) and engine `min_person_conf` >= 0.4 |
| G2 | lying | this frame is lying: >= 2 of 3 votes (torso angle >= 55, box width/height >= 1.0, keypoint extent <= 0.45 standing height; extent only with head+ankle visible), or, with < 2 votes available, box aspect >= 1.5 |
| G3 | reference | a standing height for this **track** was learned from an upright frame |
| G4 | was upright | within the last 4 s a frame was lying==False with extent >= 0.6 standing height |
| G5 | descent | hip drop >= 0.30 standing heights at >= 0.5 heights/s inside 1.5 s, or torso rotation >= 45 deg at >= 60 deg/s plus half the drop |

Then CONFIRMED needs the person to stay lying and still for 3 s (4.5 s if partly visible); RECOVERED needs 2 s upright, etc.

## 2. Findings

Earlier hypothesis ("no standing reference was learned in ~11/30") was **wrong**: the reference was learned in the first frame
for every main track. It was missing only in 3 sequences, and only because the tracker changed the person's id (new id = new history).

The 22 misses have **three different causes** (+ one that remains):

**A. The lying person is invisible to the engine (11 sequences).** In most clips the person falls towards the camera and ends
on the floor at the bottom edge of the frame, with the box cut off. Evidence from viewing the frames and the cache:
- after the fall the detector returns either nothing at conf 0.4, or a wide box (aspect 1.4-3.8, 3-12 keypoints) with **no track id**
  (ByteTrack needs two consecutive matching detections for a new track and the box changes abruptly at a fall; when it outputs nothing
  for a frame, ultralytics returns raw detections without ids). The engine ignored id-less boxes, so it never saw the lying posture.
- some of these boxes also have confidence 0.16-0.33, below both thresholds; others are single boxes with no keypoints at all.
- mid-fall frames (torso 60-90 deg but box taller than wide) correctly get only 1 of 3 lying votes: they are not yet lying.

**B. Falls from a chair or towards the camera have a small hip drop in the image (8 sequences).** The person starts seated
(fall-02, 06, 14, 16, 18, 22, 24, 26) or falls along the camera axis (fall-11). Hip image-y moved 0.04-0.32 standing heights
(threshold 0.30) and 0.12-0.73 heights/s. The head moves 0.52-0.72 heights in 1.2-1.4 s in the same sequences.

**C. History lost at a track-id change (3 sequences + part of B).** fall-23/26/29: lying frames existed but the new id had no standing
reference (G3) or no upright lookback (G4). Adoption of history across an id change only existed for tracks already in an alert state.

**D. Not recoverable with these settings (fall-21):** one low-confidence detection after the fall; nothing usable.

CONFIRMED was never reachable on this dataset: in every clip **at most 2.2 s of footage remains after the first POSSIBLE**
(median ~0.6 s), shorter than the 3 s confirmation window. 0 confirmed is a property of the clips, not a measured engine weakness.

## 3. Sequence-wise table (the 22 baseline misses)

P = reached POSSIBLE. S1 = id handling (Stage 1). S2 = S1 + head-drop signal (Stage 2, default detector settings).
S3 = S2 with detector `conf` and engine `min_person_conf` both 0.15 (tuning experiment, not a default).

| Seq | Baseline blocker | Cause (evidence) | S1 | S2 | S3 |
|---|---|---|---|---|---|
| fall-01 | G2 | falls towards camera; lying at bottom edge; detections id-less / below 0.4 | - | - | P |
| fall-02 | G5 | seated start; hip drop 0.21; id 1 -> 3 | - | P | P |
| fall-05 | G2 | lying at bottom edge, id-less | P | P | P |
| fall-06 | G5 | seated start; hip drop 0.17; id 1 -> 2 | - | P | P |
| fall-11 | G5 | falls along camera axis; hip drop 0.32 at 0.23/s | - | P | P |
| fall-13 | G2 | lost at bottom edge; id 1 -> 2 | P | P | P |
| fall-14 | G5 | seated start; hip drop 0.18 | - | P | P |
| fall-15 | G2 | towards camera; ends cropped at bottom; id-less | P | P | P |
| fall-16 | G5 | seated start; hip drop 0.22 | - | P | P |
| fall-17 | G2 | mid-fall seen, then nothing at conf 0.4; at 0.15 only one box (conf 0.25, aspect 2.1, **0 keypoints**) | - | - | P (bare box) |
| fall-18 | G5 | seated start; hip drop 0.04; box cut at bottom | - | P | P |
| fall-19 | G2 | only boxes of conf 0.16-0.39 after the fall (9 of 17 frames) | - | - | P |
| fall-21 | G2 | mid-fall boxes only (aspect 0.5-0.7), nothing after; no lying frame at any confidence | - | - | - |
| fall-22 | G5 | seated start; hip drop 0.04; id 1 -> 2 | P | P | P |
| fall-23 | G3 | id change, no reference on new id | P | P | P |
| fall-24 | G5 | seated start; box cut at bottom | P | P | P |
| fall-25 | G2 | one box at conf 0.56 with 6 keypoints but no id, then nothing; at 0.15 one more box (conf 0.27, **0 keypoints**) | - | - | P (bare box) |
| fall-26 | G3 | seated start; id change | P | P | P |
| fall-27 | G2 | nothing after the fall at 0.4; at 0.15 one box (conf 0.19, aspect 2.5, **0 keypoints**) | - | - | P (bare box) |
| fall-28 | G2 | lying at bottom edge, id-less | P | P | P |
| fall-29 | G3 | id change | P | P | P |
| fall-30 | G2 | only low-conf boxes (aspect 1.6-3.3) after the fall | - | - | P |

**Caveat on the S3 column:** fall-17, 25 and 27 reach POSSIBLE only because a single bare box (0 keypoints, conf 0.19-0.27) is wide enough to count as lying by aspect alone. That is thin evidence and the most likely kind of detection to produce false alarms on real footage, so the S3 count (29/30) should not be trusted as much as S1/S2.

(fall-22 and fall-24 were fixed by Stage 1; I did not isolate which part of the id handling mattered. Raw per-frame evidence:
`docs/eval/diagnosis_baseline.json`, `diagnosis_table_baseline.md`, `diagnosis_conf015.json`.)

## 4. State-machine review
- Gate G1 coupled the engine to the tracker's id assignment; the tracker breaks exactly when a fall happens. Fixed (Stage 1).
- History was tied to the id and only survived an id change during an alert. Fixed for any person lost < 3 s (Stage 1).
- The hip-only descent measure assumes a camera that sees the vertical drop. Added a head-drop alternative (Stage 2).
- Not changed, but a limitation: a person who goes out of view after falling (POSSIBLE then lost) is parked as an orphan and is
  never confirmed; it closes as "dismissed" after 120 s. Escalating "lost while POSSIBLE at the bottom edge" would catch more falls
  but also people walking out of frame towards the camera; it needs real footage to judge.
- RECOVERED / RESOLVED were not exercised by any URFD clip.
- Missing keypoints: handled by the aspect-only rule (aspect >= 1.5) and torso-length reference already present; no change.

## 5. Changes (small, no new model)
| Stage | Change | Files |
|---|---|---|
| 1 | Detections without a tracker id are matched to the nearest person seen < 3 s ago (confident box first), else get an engine id. A new tracker id inherits history of any person lost < 3 s (alerts preferred). No new thresholds. | `fall_analysis/engine.py` |
| 2 | Second descent signal: top of the person drops >= 0.45 standing heights at >= 0.30 heights/s. New settings `min_top_drop`, `min_top_velocity` (scaled by sensitivity, validated, shown in Settings > advanced). The lying gate and the stay-down confirmation are unchanged. | `engine.py`, `config.py`, `core/settings_store.py`, `frontend/src/settings/SettingsPage.jsx` |
| 3 (not adopted as default) | detector `conf` and `min_person_conf` 0.15: tested only. Both are existing Settings values; defaults unchanged. | none |

Stage 2 thresholds were chosen after looking at the head-drop values of these sequences (0.52-0.72 heights): **this is tuning on the evaluation data.**
Tools added: `tools/pose_cache.py`, `diagnose_urfd.py`, `diagnose_table.py`, `replay_eval.py`. Tests: 6 new engine tests (id-less lying
person, new id at fall start, chair fall by head drop, slow lowering from a chair does not alert, far-away id-less box is a new person,
weak duplicate box does not steal an incident); engine tests 26 -> 32, full suite 47 -> 53 passed.

## 6. Before and after (30 falls, 16 ADL; same cached detections)

| Run | POSSIBLE | CONFIRMED (real subsequent frames) | Missed | ADL false POSSIBLE | ADL false CONFIRMED |
|---|---:|---:|---:|---:|---:|
| Baseline (recorded, unchanged) | 8 | 0 | 22 | 0 | 0 |
| Stage 1 | 17 | 0 | 13 | 0 | 0 |
| Stage 2 (**current defaults**) | 23 | 0 | 7 | 0 | 0 |
| Stage 2 + conf 0.15 / min_person_conf 0.15 (not default) | 29 | 0 | 1 | 0 | 0 |

CONFIRMED diagnostic (real frames, **confirm_seconds shortened to 1.0** because clips end < 2.2 s after POSSIBLE; tests the confirm logic only):
Stage 2: 4 confirmed (fall-06, 10, 11, 12); with conf 0.15: 4 confirmed (same); **0 false POSSIBLE/CONFIRMED on the 16 ADL** in both.
With the shipped 3 s the confirmation of real footage remains untested. No hold-last was used anywhere in this document.

Regressions: none among the 8 baseline detections (same event lists). During development one config (conf 0.15) lost fall-10's
confirmation; cause found (a weak duplicate box stole the alert track's identity), fixed, test added.

Cost: the model and its settings are unchanged, so inference is unchanged (measured earlier: mean 204 ms, p95 347 ms for yolov8n, CPU, under memory
pressure). Engine cost measured in replay: 0.35-0.53 ms mean, ~1.0 ms p95 per analysed frame (~0.2 % of inference). Inference timing during the new
cache builds was taken while other jobs ran and is not reported.

## 7. False-positive risks (not measured on real footage)
- Id matching can merge two different people who cross within 3 s: the second inherits the first's reference and history.
- The head-drop signal fires for any fast head drop that ends "lying": a person diving onto a bed/sofa, a stunt, a crouch-to-lie. The lying votes and the
  3 s stay-down check remain the guards; slow deliberate lowering is tested not to alert.
- Lower detector confidence (Stage 3) admits more spurious boxes (coats, chairs, reflections). Wide low-confidence boxes can look "lying" by aspect alone.
- 16 ADL clips are weak negative evidence (no audit of how many contain hard cases such as fast sitting or deliberate lying).

## 8. Remaining limitations
- Only 7 -> 1 clips still miss, but 23 of 30 detections at the default settings come from a rule set whose Stage 2 thresholds were set while looking at these clips.
- Confirmation, recovery and resolution are not validated on real footage. Nothing here estimates real-world accuracy.
- URFD camera 0 is low and floor-parallel and its falls end at the frame edge; real CCTV differs.
- fall-21: no usable detection after the fall at any tested confidence.

## 9. Recommended next experiment
Record or collect footage from the real cameras (staged falls from standing and from a chair, plus a few hours of normal activity incl. sitting, lying on a
sofa, crouching, exercising). Freeze Stage 2 as is. Run the cache + replay pipeline on it with detector conf 0.4 and again with 0.15/0.15, and count
(a) staged falls reaching POSSIBLE/CONFIRMED with the real 3 s window and (b) false POSSIBLE/CONFIRMED per camera-hour. Decide the confidence setting from (b) on
that footage, not from URFD. If a second public dataset with a compatible licence is wanted, use it only as a held-out set, untouched while tuning.
