# Adult and child fall detection: research findings (no code or data changed)

Status: **research only.** Nothing was downloaded, no dataset was added, no detection code or setting was changed (confidence stays 0.4, confirmation stays 3 s).
Date of the web checks: 2026-11-23. Method: three research agents read dataset pages, papers, READMEs, LICENSE files and the GitHub API; the pipeline section was done by reading this repository.
Limits of this research: some pages were read through a summariser (quotes are "as returned"), a few sites blocked automated reading (ScienceDirect, Roboflow, a UBFC portal), and **no download link was tested**.
Licence notes below are a reading of public pages, **not legal advice**; a person must confirm any licence before the data or code is used.

## 1. Headline conclusions
1. **No publicly downloadable video dataset of child falls with documented ages and a usable licence was found.** Child fall data exist only in papers (toddlers 13-30 months; a childcare-centre study of 12-36 months) and are withheld or not yet released.
2. **None of the six datasets named in the task documents child participants.** CAUCAFall documents ages (23-40, adults). FallVision documents 22-27. UP-Fall documents 18-24. GMDCSA-24, Le2i and URFD document no ages. So none may be called child-specific or child-inclusive.
3. Therefore **child-fall reliability cannot be validated from public data today.** Public adult data can only protect the adult baseline (regression gate). Child evidence needs consented footage obtained from the authors of existing studies or recorded under our own ethics process.
4. **A caveat on our earlier GMDCSA-24 work:** the paper's Ethics Statement says "three human actors" took part while the data has four subject folders. Our tuning (Subjects 1-2) vs independent (Subjects 3-4) split assumes each folder is a different person. If one actor appears in two folders, the two sets may share a person (participant leakage). We must not guess identities from faces; this needs a written answer from the authors. Until then, treat the GMDCSA independent results as *possibly* participant-contaminated.
5. **Our pipeline normalises by each person's own height, which helps with smaller people**, but several adult-tuned thresholds and the new wide-box and floor rules are likely to produce **false alarms on children who crawl, sit or play on the floor.** That is an expectation to test, not a measured result.
6. **Licence concern that applies to our project today:** Ultralytics (YOLOv8) is AGPL-3.0; commercial deployment needs AGPL compliance or an Ultralytics enterprise licence. URFD is non-commercial.

## 2. Dataset comparison (the six requested)
| | CAUCAFall | Le2i | URFD | GMDCSA-24 | FallVision |
|---|---|---|---|---|---|
| Source | https://data.mendeley.com/datasets/7w7fccy7ky (v5, 2025-03-18); paper https://pmc.ncbi.nlm.nih.gov/articles/PMC9508401 | https://imvia.ube.fr/?p=346 (page says "Dowload the data (waiting for new link)"); possibly https://search-data.ubfc.fr/imvia/FR-13002091000019-2024-04-09_Fall-Detection-Dataset.html (blocked, unverified) | https://fenix.ur.edu.pl/mkepski/ds/uf.html | Zenodo https://zenodo.org/records/12921216 (v2.0); GitHub https://github.com/ekramalam/GMDCSA24-A-Dataset-for-Human-Fall-Detection-in-Videos | Harvard Dataverse doi:10.7910/DVN/75QPKK; paper https://pmc.ncbi.nlm.nih.gov/articles/PMC11950752/ |
| GitHub repo | none found | none from authors (third-party mirrors exist) | none from authors | yes | none found |
| Videos? | yes (.avi + images) | yes in principle (191 videos); download unverified | yes (MP4 per camera) + RGB/depth sequences + accelerometer | yes (mp4, H264) | yes (raw + landmark-overlay videos) + per-frame keypoint CSVs |
| Children? | **no**; ages 23-40, 10 subjects | not stated | not stated | not stated | **no**; 22-27, 58 participants, ~6-7% female |
| Fall / non-fall | forward, backward, lateral L/R, from sitting / walking, hopping, picking up, sitting, kneeling | falls and ADL in four scenes (split not reliably documented: 143+48 or 143+79) | 30 falls / 40 ADL | 79 falls / 81 ADL by the CSVs (the paper's abstract swaps them); FW/BW/SW; sleeping, push-ups as fall-like | fall vs no-fall from bed / chair / standing |
| Camera | 1 HIKVISION IR, fixed high corner, reported 1080x960 @ 23 fps, home | 1 camera, 320x240 @ 25 fps; home, coffee room, office, lecture room | 2 Kinects (falls), 1 (ADL); cam1 ceiling; video resolution not stated | 1 fixed 720p webcam 30 fps; clips 1280x720 or 640x480; 3 rooms | webcams/phones, 720p-1080p, >=30 fps; 6 viewpoints incl. floor and ceiling |
| Annotation | per-frame .txt, silhouette box, nofall/fall (20,002 frames) | per-frame body boxes + fall frame ranges | per-depth-frame posture label (-1 / 0 / 1) | CSV: time ranges in seconds per class | no boxes or fall times found; YOLOv7-pose keypoints per frame; labels by file name |
| Size | not stated | not stated | not stated | 1.1 GB (Zenodo zip; the paper says 1.95 GB) | 11,732 videos; Dataverse lists 60 .rar files of 1-2.6 GB each (tens of GB) |
| Licence | CC BY 4.0 on Mendeley (the paper says "public domain"; a site-wide footer reserves text-and-data-mining/AI-training rights: ambiguous) | **not stated** on the official page | **CC BY-NC-SA 4.0, non-commercial academic use**; commercial: contact authors | CC BY 4.0 (Zenodo); MIT on GitHub | **conflict:** CC0 on Dataverse vs article CC BY-NC 4.0 and "academic, research or instructional use" wording; file access request flagged |
| Participant-level split possible? | yes (10 subject folders) | not documented (scene-level only) | not documented | folders documented, but 4 folders vs 3 actors (see 1.4) | not confirmed (no subject id seen in file names) |
| Suited for | adult tuning / independent test | low-resolution adult tuning; licence unknown | adult tuning / test, non-commercial | adult tuning / test (what we used) | adult pre-training/tuning only; domain mismatch (young adults on mats) |

## 3. Child-specific availability and gaps
| Resource | What it is | Children documented? | Public? |
|---|---|---|---|
| Toddler falls, Sensors 2024 (https://pmc.ncbi.nlm.nih.gov/articles/PMC11479333/, doi:10.3390/s24196451) | parent-supplied home surveillance videos, 230 videos (paper inconsistent on participant counts) | yes: **13-30 months** | **no**: "Guardians ... have requested that the dataset not be made publicly available." |
| Child head injury from falls, Sensors 2023 (https://pmc.ncbi.nlm.nih.gov/articles/PMC10534444) | 200 daily videos, 500 + 300 clips | yes: 13-30 months | no ("Not applicable") |
| Pediatric Fall Biomechanics (NIJ; https://www.ojp.gov/library/publications/biomechanical-characterization-video-recorded-short-distance-falls-children) | 3,255 video-recorded falls, licensed childcare centre | yes: **12-36 months** | **not yet** ("will be available online once project manuscripts ... are published"); consent/format not stated |
| NTU RGB+D 120 (https://rose1.ntu.edu.sg/dataset/actionRecognition/) | 114,480 videos, 2.3 TB, class "falling down" | **contradictory**: page says "No children ... included"; paper says ages "from 10 to 57" | restricted: academic only, institutional email + supervisor + approval |
| HUST-FALL (IEEE DataPort doi:10.21227/x8ey-wc90) | 50 GB of videos collected from other datasets and online platforms | not documented (one example labelled "Toddler" in a different action) | login required; CC BY 4.0 stated but source videos' own terms unknown |
| Roboflow Universe "child fall" sets | **images**, user-uploaded | not verified | provenance, ages, consent unknown; do not treat as validated |
| UP-Fall, Multiple Cameras Fall, Kinetics | adult (UP-Fall 18-24) / one subject / web video | no | n/a |

Gaps: nothing covers ages 3-17; the only documented child data are toddlers (13-36 months), whose movement (crawling, toddling) differs strongly from school-age children. "Child-representative" must always be stated with the actual ages.

## 4. GitHub implementations
| Repo | Own-code licence | Upstream issues | Last push / stars | Pose | Temporal model | Datasets / evaluation | Value to us |
|---|---|---|---|---|---|---|---|
| Datyth/cross-dataset-fall-detection | **none (all rights reserved)** | CTR-GCN adaptation is **CC BY-NC 4.0**; MMPose/RTMPose licences unverified | 2026-11-17 / 2 | RTMDet-m + RTMPose-m, COCO-17, one person | CTR-GCN, 64-frame windows, stride 32 at 15 fps | Le2i, URFD, CAUCAFall, GMDCSA-24; leave-one-dataset-out, 3 seeds, source-only thresholds; fall F1 and AP | **idea only**: evaluation protocol, loaders and manifest design. Its normalisation is global (image centre / max side), weaker than ours. |
| GajuuzZ/Human-Falling-Detect-Tracks | **none** | bundles AlphaPose SPPE; weights trained on hand-labelled Le2i | 2021-10-02 / 868 | AlphaPose FastPose | two-stream ST-GCN, 30 frames, 7 classes (incl. sit down / stand up) | Le2i only, no evaluation code | **reference only**: per-pose min/max scaling, motion input, hard-negative classes |
| cwlroda/falldetection_openpifpaf | **none** | vendored OpenPifPaf 0.11.9, compiled .so, Python 3.7 | 2025-09-12 / 435 | OpenPifPaf | rules in `core.FallDetector` (not inspected) + centroid tracker | URFD only, no negatives tested | **architecture reference only** (closest to ours) |
| stinefe/IKT213_project_group_14 | MIT | uses Ultralytics (AGPL-3.0) | 2026-11-18 / very low | YOLO11 pose | Random Forest on 30-frame hand-crafted windows + ~2 s persistence, 3 s upright to recover | Le2i; whole Office room held out (F1 0.72 there, own numbers) | MIT: features and room-level split logic can be adapted; small unreviewed student project |
| PYSKL | Apache-2.0 | NTU-trained weights have their own terms | 2026-02-19 / 1,271 | n/a | ST-GCN, CTR-GCN, PoseC3D | no fall dataset; "not currently maintained" | usable code if a learned classifier is ever wanted |
| OpenMMLab MMAction2 | Apache-2.0 | heavy (compiled ops) | 2026-03-18 / 5,203 | MMPose | PoseC3D, ST-GCN family | generic | maintained framework, heavy |
Dismissed: RuturajKhandwe/skeleton-based-fall-detection (no dataset named, no model in repo), an empty repo, and several 0-star unlicensed repos.

**Rule for all of the above:** do not copy code or weights from a repo without a licence or with a non-commercial upstream. Reuse *ideas* (protocols, feature lists) only. The only copy-compatible code found is MIT/Apache (stinefe, PYSKL, MMAction2), and only if it is actually needed.

## 5. Licence and commercial-use concerns
- **Ultralytics YOLOv8 is AGPL-3.0** (our current dependency, also used by stinefe): closed-source commercial deployment needs AGPL compliance or an enterprise licence.
- **URFD:** CC BY-NC-SA 4.0, non-commercial academic use only; commercial use needs the authors' permission.
- **FallVision:** CC0 vs "academic/research/instructional" wording is unresolved; ask the authors.
- **Le2i:** licence unknown; assume non-commercial until the owner answers.
- **CAUCAFall:** CC BY 4.0 on Mendeley, but conflicting statements ("public domain", site-wide AI-training reservation); ask if used for training.
- **GMDCSA-24:** CC BY 4.0 (Zenodo) / MIT (GitHub); attribution required.
- **NTU RGB+D:** academic only, approval required, redistribution and commercial use prohibited.
- Any footage of children needs its own consent and safeguarding route; no public source documents consent that would carry over to a new use.

## 6. Our pipeline: what it does with smaller people
Verified by reading the code (files and functions); nothing was run on child footage.
| Question | Finding | Where |
|---|---|---|
| Does YOLOv8n-Pose give usable keypoints for smaller people? | **Unknown, untested.** Detector conf 0.4, input 640 px, joints need confidence >= 0.4. Smaller or more distant people have fewer reliable joints, which lowers `n_visible`, sets `partial` (longer confirmation, 4.5 s) and removes the torso angle. No child or small-person footage has been evaluated. | `pose_estimation/keypoints.py: extract_features`; `detection/pose_worker.py: _run`; `tools/cctv_validate.py: build_pose` |
| Are body measurements normalised? | **Yes, per person.** Distances are in units of the person's own standing height, learned from upright frames (box height, or torso length / 0.30 when legs are hidden), with a body-length fallback when none is known. This removes absolute size. | `engine.py: _standing_height, classify, _ref_height`; `tracking/track_history.py: observe_upright, body_length` |
| Do hip-drop / head-drop depend on adult proportions? | **Partly.** `TORSO_FRACTION = 0.30` is an adult-typical constant used when the legs are hidden. Thresholds (`min_drop` 0.30, `min_velocity` 0.5, `min_top_drop` 0.45, `lying_extent_ratio` 0.45, `upright_extent_ratio` 0.6) were set and checked on adult data only. Children's different proportions (generally a larger head relative to the body) could shift hip and head drop magnitudes; this is general anatomy, not measured here. | `engine.py:88`, `_descent`; `fall_analysis/config.py` |
| Child-typical activity | **Expected false-alarm risk, to be tested:** crawling, playing or sitting on the floor produces a wide, low box. The wide-box rule (1.2) and the 4 s floor rule (both added recently) would classify that as lying. Sitting down fast or jumping can look like a hip drop. | `engine.py: classify, _floor_lie, _descent` |
| Is tracking stable with several small people? | **Not evidenced.** ByteTrack defaults (`track_buffer` 30, `match_thresh` 0.8, IoU-based) at 5 analysed frames per second; small boxes move more relative to their size between frames, so IoU matching is fragile. Even adults show frequent id changes in our live log. The engine re-attaches ids by IoU or centre distance relative to box size, so with several children close together **a POSSIBLE/CONFIRMED state could be inherited by the wrong child.** | ultralytics `cfg/trackers/bytetrack.yaml`; `engine.py: _assign_missing_ids, _nearest_recent_track, _adopt_orphan` |
| Can our validation tools process new datasets? | **Mostly yes.** `cctv_validate` reads mp4/avi/mkv/mov, keeps tuning vs independent roles by folder name (a nested `child_representative/tuning` works), and scores per clip from a `.meta.json`. The label file already accepts a free-form `dataset` block (used for tags), and `gmdcsa_eval` already breaks results down by tag. Missing: per-dataset importers (CAUCAFall per-frame labels, Le2i frame annotations), scenarios for child-typical normal activity (`SCENARIOS` is a fixed list), participant/session ids, and a participant-level split check (the existing guard compares file content, not people). URFD image sequences are handled by the older `eval_urfd.py` / `pose_cache.py`. | `tools/cctv_meta.py: SCENARIOS, validate`; `tools/cctv_validate.py: role_of, shared_between_roles`; `tools/gmdcsa_eval.py: attach_meta, strata` |

## 7. Integration plan (proposal, needs approval)
Layout: keep the existing convention `validation/{tuning,independent}/<scenario>/` and `validation/datasets/<name>/` (manifest, inventory, licence record). Add only what is missing:
```
validation/datasets/DATA_SOURCES.md      licence, URL, access date, checksum policy per dataset
validation/datasets/<name>/manifest.json  split, mapping rules, exclusions, SHA-256 of every original (already the GMDCSA pattern)
validation/child_representative/{tuning,independent}/<scenario>/   created ONLY if consented child footage is ever obtained
docs/CHILD_FALL_VALIDATION.md             the final workflow and results (written when there is something to report)
```
Raw data stays outside the repository (for example `C:\Users\lenovo\Datasets\<name>`), with a `<name>_download.json` record (source, commit or version, per-file checksum result). `.gitignore` already excludes validation footage and caches.

Workflow, mapped to existing tools:
1. **Acquire:** per-file verified download (the GMDCSA fetcher pattern); check size before any large download.
2. **Licence and provenance:** one row per dataset in `DATA_SOURCES.md`; manifest with SHA-256; no use until a person has read the licence.
3. **Inspect:** `cctv_inspect` plus a small-person diagnostic (median person height in pixels, share of frames with enough joints).
4. **Pose extraction:** `cctv_validate.build_pose` cache, unchanged model and settings (0.4 / 640 / 5 fps).
5. **Labels:** written by a person or taken verbatim from the dataset's own annotations; never from the detector.
6. **Tuning:** tuning split only, by participant and session; every change recorded; adult baseline re-run after each change.
7. **Independent evaluation:** once, with a frozen configuration and code hashes.
8. **Adult vs child regression:** results broken down by a `population` tag; **a configuration is accepted only if the adult results (URFD 30 sequences, GMDCSA tuning and independent) do not get worse.**

Safety rules carried into the plan: no identifiable child footage without authorisation and safeguarding; prefer consented, anonymised data; no staged dangerous falls; no age inference from faces and no facial recognition; participant- and session-level splits; no child-reliability claim without independent child-representative evaluation.

## 8. Files that would change (later; none now)
- New: `tools/caucafall_import.py` (CAUCAFall), a `le2i_import.py` only if the data and licence are confirmed, `validation/datasets/DATA_SOURCES.md`, `docs/CHILD_FALL_VALIDATION.md`.
- `tools/cctv_meta.py`: add child-typical normal scenarios (crawling, playing on the floor, running or jumping, sitting on the floor) and optional `population`, `participant_id`, `session_id` checks.
- `tools/gmdcsa_eval.py`: generalise to a dataset-neutral evaluator with by-population and leave-one-participant-out views.
- `tools/cctv_validate.py`: record per-clip person size and joint visibility in the report; a participant-level leakage guard.
- Tests for each of the above.
- **Not changed unless evidence demands it:** `engine.py`, `config.py`, `keypoints.py`, the model, confidence 0.4, confirmation 3 s.
- First low-risk experiment that needs **no child data**: rescale existing adult clips to smaller apparent sizes and measure the loss of joints and of detection. This quantifies the small-person problem, but it simulates distance, not child proportions or behaviour.

## 9. Recommended acquisition order
1. **GMDCSA-24:** already held. Ask the authors how its four folders map to three actors, and re-label its independent results as possibly contaminated until answered.
2. **CAUCAFall:** CC BY 4.0, ten adult subjects in per-subject folders (clean participant split), videos plus per-frame labels. Check size first. Adult regression and independent test only.
3. **URFD:** already used (30 sequences); non-commercial; keep as the baseline.
4. **Le2i:** only after the owner confirms the licence and a working download.
5. **FallVision:** low priority (tens of GB, young adults on mats, licence conflict, no subject ids confirmed).
6. **Child data (the real gap):** write to the authors of the toddler studies and the NIJ childcare project about restricted access, ages, consent and a data-use agreement; in parallel decide whether to record our own consented footage under an ethics process. Roboflow sets and HUST-FALL are not acceptable evidence until their provenance and consent are documented.

## 10. Genuinely usable vs research references
**Usable now (subject to a human licence check):** GMDCSA-24 (CC BY 4.0, adult), CAUCAFall (CC BY 4.0, adult), URFD (non-commercial research only), our own validation tooling, MIT/Apache code (stinefe, PYSKL, MMAction2) if ever needed.
**Research references only:** Datyth (no licence, non-commercial upstream), GajuuzZ (no licence, AlphaPose), cwlroda (no licence, vendored library), NTU RGB+D (restricted, contradictory on children), FallVision (licence conflict, adults, very large), Le2i (licence and download unverified), toddler and NIJ child data (not public), Roboflow child sets (provenance unknown, images), HUST-FALL (login, mixed provenance, unverified), UP-Fall / Multiple Cameras Fall / Kinetics (not child data).

## 11. What could not be verified
Actual availability of any download link; Le2i participants, split and licence; FallVision subject ids in archives; whether file-access requests on Dataverse are enforced; the toddler studies' authors' willingness to share; the NIJ knowledgebase release status and consent terms; rules inside `cwlroda/.../core/`; upstream licences of AlphaPose, OpenPifPaf and OpenMMLab weights; exact download sizes for CAUCAFall and URFD.
