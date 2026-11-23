# Child fall detection: datasets, pose models and options

Status: **research only.** Nothing was downloaded, no model or dataset was installed, no code, setting or test was changed. YOLOv8n-Pose, confidence 0.4 and the 3 s confirmation are untouched; the adult baseline (URFD, GMDCSA-24) is untouched; GMDCSA-24 was not downloaded again.
Date of the web checks: 2026-11-23. This builds on `docs/CHILD_FALL_RESEARCH.md` (first round; do not repeat its content).
How it was made: two research agents read dataset pages, papers, READMEs, licence files, the Hugging Face model card and file listings, and the GitHub/Dataverse APIs; the pipeline section was done by reading this repository.
Limits: pages were read through a summariser (quotes are "as returned"), several pages could not be read (Springer, Leuphana pubdata, Roboflow, Figshare, a Northeastern page with a certificate error, the Hugging Face licence file returned 401), **no download link was tested, no access form was submitted**, and licence readings are not legal advice. A person must confirm every licence before use.

## 0. Bottom line
1. **The four named resources are not child fall data.** ChildLens (children 3-5, egocentric, no falls) and PInSoRo (children about 6, seated tabletop play, no falls) are child *activity* data. IKAR contains falls but of **adult volunteers** (7 volunteers, ages not stated). ChildPose is a **pose model**, not a dataset.
2. **There is still no public video dataset of child falls from fixed cameras.** The strongest one, a childcare-centre study (3,255 recorded falls, ages 12 to under 36 months, three fixed 1080p cameras per room), is not released.
3. **ChildPose is CC BY-NC 4.0 and may not go into a commercial product.** No permissive child-pose model with public weights was found. The commercial route is to build one ourselves from consented footage on a permissive backbone, or to negotiate a licence with the ChildPose authors.
4. **An alternative pose estimator can feed our fall engine without changing it**, provided it outputs a person box plus 17 COCO keypoints in image pixels. ChildPose does (it needs boxes from our detector). But it is GPU-oriented, new, and its licence makes even an internal experiment a grey area (section 2.2).
5. Better keypoints do not automatically mean better fall detection. That has to be measured downstream.

## 1. Child fall datasets (do the videos contain children falling?)
| Resource | Contains | Ages | Falls | Camera | Resolution / fps | Annotations | Access | Licence | Consent stated | CCTV fall use |
|---|---|---|---|---|---|---|---|---|---|---|
| **NIJ "Pediatric Fall Biomechanics"** (Bertocci et al., Univ. Louisville; paper https://pmc.ncbi.nlm.nih.gov/articles/PMC9124183/) | childcare-centre video, 3,255 recorded falls | 12 to <36 months (mean 19.4; 31-35 children) | **yes** | 15 fixed cameras (3 per space; 4 classrooms + playground) | Lorex 1080p, 30 fps | fall, child and head-biomechanics descriptors, stills | **not public** ("will be available online once project manuscripts ... are published"; "not publicly available ... on-going analysis"; on request to the corresponding author once published) | not stated | yes: IRB #16.1030, "Legal guardians provided informed consent" | **best match in design, unavailable** |
| **Toddler falls, Sensors 2024** (https://pmc.ncbi.nlm.nih.gov/articles/PMC11479333/) | parent-supplied home surveillance clips (230 videos; counts inconsistent) | 13-30 months | yes | home surveillance (model not named) | 30 fps | not stated | **withheld**: "Guardians ... have requested that the dataset not be made publicly available." | n/a | yes | unavailable |
| Sensors 2023 child head-injury paper | 200 daily videos | 13-30 months | yes | home | not stated | not stated | not public ("Not applicable") | n/a | not stated | unavailable |
| Roboflow Universe "Child Fall Detection" and similar | **images**, user-uploaded | not stated | unverified | unknown | unknown | boxes (classes like fall / not fall) | public, but page could not be read | "CC BY 4.0" in a search snippet, unverified | not stated | **do not use** until provenance, ages and consent are documented |
| **IKAR Fall Detection Dataset** (https://agh.rodbuk.pl/dataset.xhtml?persistentId=doi%3A10.58032%2FAGH%2FA1NZPE) | **adult** staged falls on protective mats: trips 92, slips 64, faintings 65, blackouts 57 = 278 videos | "7 volunteer participants"; **ages not stated, none documented as children** | yes (adult) | mobile devices; viewpoint not stated | not stated | tight bounding boxes (Labelbox) | open; a guestbook (name, account) appears on download; file-access-request flag set | **CC BY 4.0** | not stated on the record (readme not read) | adult only; four fall types, no stated normal-activity class |

## 2. Child activity datasets (children moving, but **not** falls)
| Resource | Ages / n | Camera | Res / fps | Annotations | Access | Licence | Consent / ethics | Use for us |
|---|---|---|---|---|---|---|---|---|
| **ChildLens** (https://fis.leuphana.de/en/datasets/childlens-an-egocentric-video-dataset-for-activity-analysis-in-ch/; paper doi 10.3758/s13428-026-02982-6; data at Keeper doi 10.17617/4.fe, the Leuphana page's doi ...4.fc was reported as removed) | 3-5 years, 62 children, 109 h at home (54 h annotated) | **egocentric**, chest-level, 140-degree lens in a vest | not stated | 5 location and 14 activity classes (temporal labels); no keypoints | **by request** (login via Keeper or contact ra@eva.mpg.de) | not stated; Leuphana page: "All rights are reserved, including those for text and data mining, AI training, and similar technologies" | not stated on readable pages | none for CCTV falls; at most background/negative footage if the licence ever allows |
| **PInSoRo** (https://freeplay-sandbox.github.io/; paper https://pmc.ncbi.nlm.nih.gov/articles/PMC6195299/; Zenodo 10.5281/zenodo.1043507) | 120 children, mean age 6.4 (SD 1.3); no range stated | two RealSense face cameras + one Kinect overview, children seated at a touchscreen | 960x540 @ 30 | social-behaviour labels + 15-point 2D skeleton (upper body) | **academics only**; raw video no longer distributed (ethics policy change); anonymised version without video on Zenodo (~7.2 GB) | dataset licence not stated ("Creative Commons licensed" in the paper for one version); commercial not stated | written parental consent for sharing; university ethics approval | none: seated, tabletop |
| **Multiview child motor-development dataset** (GigaScience 2023, https://pmc.ncbi.nlm.nih.gov/articles/PMC10220505/; GigaDB doi 10.5524/102382) | 20-71 months (groups 20-35, 36-53, 54-71); children 339 in the abstract vs 399 in the methods | 3 simultaneous views (front, left, right), Sony RX100 | 1920x1080 @ 30 | OpenPose BODY_25 skeletons (x, y, confidence); developmental-test behaviours | **public** (GitHub and GigaDB) | code MIT; article CC BY 4.0; **dataset licence not stated** (check GigaDB) | IRB 4-2021-0845; text says consent waived yet "all caregivers gave written informed consent" (contradictory); face blurring not mentioned | **best public child-motion set**: indoor, multi-view, 1080p, skeletons; no falls; the skeletons are OpenPose output, not human labels |
| ToddlerAct (arXiv 2409.00349; https://github.com/ipl-uw/ToddlerAct) | under 3 years; 495 videos (snippet) | not stated | not stated | action labels | **not released** (repo shows no data) | not stated | not stated | none yet |
| InfActPrimitive (https://github.com/ostadabbas/Video-Based-Infant-Action-Recognition) | infants; ages not stated | not stated | not stated | 2D/3D skeletons (Google Drive) | download under a **non-commercial** condition | non-commercial | not stated | no (infants, no falls) |
| Kindergarten-monitoring YOLO (https://zenodo.org/records/20208893) | not stated | not stated | not stated | boxes "child"/"adult" | only the paper PDF is listed | CC BY 4.0 on the record | not stated | no data to use |
| Child action subset of Kinetics-600 (arXiv 2212.09027) | web video | n/a | n/a | n/a | no confirmed release | Kinetics terms | none | no |

## 3. Child / infant pose models and pose datasets
### 3.1 ChildPose (investigated in detail)
- **Where:** code and weights at **https://github.com/PediaMedAI/ChildPose** (the `jiaka1chen/ChildPose` link you gave returns 404; a mirror may point to it, unverified) and https://huggingface.co/PediaMedAI/ChildPose (gated, "auto" approval). Paper: "ChildPose: Foundation for Children Pose Modeling" (Chen, Shen, Li, Dong, Cao), listed for NeurIPS 2026; **no arXiv or DOI, and the project page's paper link is a placeholder**. Repo created 2026-11-06, last push 2026-11-13, 3 commits, 0 stars: **very new, no track record.**
- **What it is:** a streaming pediatric pose model that adds memory-augmented temporal attention over adjacent-frame features and an auxiliary age-prediction objective (training only) to pretrained pose encoders. Backbones: HRNet-W48 (102.5M parameters, 288x384 input), HRFormer-B (82.1M), ViTPose-B (108.2M, 256x192), Sapiens-0.3B / 0.6B / 1B.
- **Input:** per-frame **person boxes** [x1, y1, x2, y2] in pixels (enlarged 10% before cropping), RGB frames. "ChildPose does not detect or track children": **a separate detector and tracker are required.** (Our YOLO + ByteTrack could supply them.)
- **Output:** **COCO-17** 2D keypoints in image pixels (17x2) plus per-keypoint scores (17,) from the heatmap peak, an overall score and the crop box; `None` if the child is not visible. No 3D.
- **Temporal handling:** uses a memory of adjacent frames; trained on **8-frame windows at 5 fps** (our analysis rate is also 5 fps). `fps` modes: "interleave" (default, every frame), "downsample" (about 5 fps), "sequential"; `use_memory=False` gives independent per-frame prediction. It does not track.
- **Hardware and integration:** PyTorch >= 2.0, numpy, pillow, safetensors, huggingface_hub, opencv (only for the video script); Python >= 3.9; **no MMPose/MMCV compiled dependency** (backbones are re-implemented), so installation looks easy. CUDA optional but **no minimum hardware and no CPU benchmark is stated**. The project page claims about 164 FPS on one L40S GPU at FP16 and 1.1 ms for the memory module, apparently for ViTPose-B (not confirmed). My inference, not stated by the authors: a 100M-parameter model per person crop will be far heavier than YOLOv8n-pose and should be treated as GPU-only until measured; our laptop has no GPU.
- **Training data and ages:** 5,943 clips (25.6 h), six sources (public ChildPlay, InfAct, Kinder-Gator, a Kinetics-600 child subset; private InfantPose and Children Gait Video, 110 subjects aged 3-17). Age labels exist for only 49.9% of windows; among those: infant (<1) 18.5%, toddler (1-2) 5.3%, preschool (3-5) 12.4%, child (6-9) 55.2%, **teenager (10-17) 0.1%**, adult 8.6%. The model card gives no age range. So "children" here means mostly infants to age 9; teenagers are essentially absent.
- **Accuracy:** ViTPose-B + ChildPose 0.8956 AP on its own private-heavy test split (0.8761 when trained on public data only, against 0.8673 for a fine-tuned ViTPose-B). Adult results are not stated. These numbers cannot be compared with YOLOv8n-pose unless both are run on the same labelled footage.
- **Ethics:** originating studies report IRB approval and parent/guardian consent; private recordings de-identified; the full dataset and training code are not released.
- **LICENCE (verified in LICENSE, README, model card and third-party notices):** **CC BY-NC 4.0 for code and weights.** The model card adds a Responsible Use Policy: *non-commercial research use only*, with parental or guardian consent for video; prohibited: re-identification, **covert surveillance**, standalone clinical diagnosis; "not a medical device". Upstream: Sapiens CC BY-NC 4.0 (Meta), ViTPose-B Apache-2.0, HRNet-W48 and HRFormer-B MIT; yet "checkpoints follow the strictest upstream backbone terms" and the training data (ChildPlay, CGV CC BY-NC 4.0; InfAct non-commercial; Kinetics terms) are non-commercial, so **even the ViTPose-B checkpoint is non-commercial**. The Sapiens-bootstrapped labels carry the same taint. A commercial licence from the authors is the only route and is unverified.
- **Do not integrate its code or weights into the product.** An *internal research comparison* (experiment B in section 7) is a grey area: the licence allows non-commercial research, but an experiment run by a company to decide a commercial product's design may not count, and the Responsible Use Policy restricts surveillance use. **Get the authors' written permission or legal advice before even downloading the weights.** The gated Hugging Face terms (not readable) may add conditions.

### 3.2 Alternatives to ChildPose (licensing)
| Item | Maker | Ages | Keypoints | Licence | Weights public | Footage public | Commercially usable? |
|---|---|---|---|---|---|---|---|
| SyRIP / FiDIP (https://github.com/ostadabbas/Infant-Pose-Estimation) | Northeastern ACLab | infants; not stated | COCO-style | code: "non-commertial purpose only"; data licence not stated; extra data needs a password via contact | yes (Google Drive) | images from the web (snippet) | **no** |
| AggPose infant dataset (arXiv 2205.05277) | university group | not verified | 21 | "Commercial usage ... is prohibited" (snippet) | not verified | not verified | **no** |
| MINI-RGBD (Fraunhofer IOSB) | Hesse et al. | synthetic infants (no real child) | 25 joints | licence terms not read; "research purposes" | n/a | synthetic, no consent issue | unverified |
| AGORA (MPI-IS) | MPI-IS | 257 child scans among 4,240 synthetic | SMPL-X / SMIL | registration; commercial via MPI | n/a | synthetic | only with a commercial licence |
| Roboflow "infant-pose-estimation" set | unnamed | not stated | not verified | "CC BY 4.0" (snippet) | n/a | unknown provenance, 1,701 images | possibly, but **unvetted** |
| Helsinki/Pisa infant movement data (Zenodo 10.5281/zenodo.14269867) | trial groups | corrected age in days | 2D/3D time series | **CC BY 4.0 (verified)** | trained "Kinetic Age" models | no raw images | data only; not an image pose model |
| ViTPose / HRNet (backbones) | ViTAE / HRNet | adult-dominated | COCO-17 | code Apache-2.0 / MIT; **weights licence not stated** | yes | n/a | the plausible base for our own fine-tune, after a licence check |
| MMPose / RTMPose | OpenMMLab | adult-dominated | COCO-17 and more | code Apache-2.0; weights' licence and the terms of some training datasets (AI Challenger, Halpe, MPII) not checked | yes | n/a | **legal question** |
| MediaPipe Pose | Google | not stated | 33 | code Apache-2.0; model terms not read | yes | n/a | likely, unverified; no child accuracy claim |
| Ultralytics YOLO-pose (our current) | Ultralytics | adult-dominated | COCO-17 | **AGPL-3.0**, or paid Enterprise licence | yes | n/a | **needs AGPL compliance or an Enterprise licence** |
| Commercial SDKs with documented child support | - | - | - | **none found** | - | - | vendor enquiries needed |
**Conclusion:** no permissive child-pose model with public weights exists that I could find. Realistic commercial routes: (a) ask the ChildPose authors for a commercial licence; (b) collect and annotate our own consented child footage and fine-tune a permissive backbone (ViTPose/HRNet) after checking the weights' licence; (c) accept YOLOv8n-pose's adult-trained behaviour and measure it on child footage first.

## 4. GitHub repositories (child-relevant)
| Repo | What | Licence | Status | Use |
|---|---|---|---|---|
| PediaMedAI/ChildPose | child pose model (section 3.1) | CC BY-NC 4.0 | created 2026-11-06, 0 stars | research reference; **not for product** |
| ostadabbas/Infant-Pose-Estimation | SyRIP, FiDIP | "non-commertial purpose only" | 67 stars, last push 2024-07 | research reference |
| ostadabbas/Video-Based-Infant-Action-Recognition | InfActPrimitive skeletons | non-commercial download terms | n/a | research reference |
| ipl-uw/ToddlerAct | toddler action recognition | not stated | no data released | reference only |
| GigaScience multiview child repo (URL not captured; linked from the article) | skeletons of 20-71-month-olds | code MIT | public | worth a closer look once permitted |
Earlier round (adult fall repositories, none with a usable licence except MIT/Apache ones): see `docs/CHILD_FALL_RESEARCH.md`.

## 5. Access and licence restrictions, consent, privacy
| Resource | How to get it | Restrictions and flags |
|---|---|---|
| NIJ childcare falls | write to Prof. Gina Bertocci (Univ. of Louisville) / NIJ after manuscripts appear | not public; toddlers; guardian consent; ask about licence, de-identification, permitted purposes |
| Toddler Sensors 2024 | contact the corresponding author | guardians asked for **no public release**; any access needs a data-use agreement and likely re-consent |
| ChildLens | login via Keeper doi 10.17617/4.fe or ra@eva.mpg.de | "All rights are reserved ... AI training"; consent and licence not found; egocentric footage of children in homes: privacy-sensitive |
| PInSoRo | contact address on the site's get-dataset page, subject "[PInSoRO]" | academics only; no raw video; parental consent for sharing was obtained for the research community, not for commercial use |
| IKAR | download from RODBUK (guestbook) | CC BY 4.0 (attribution); readme with ages, consent and camera details not read |
| GigaScience multiview | GitHub / GigaDB doi 10.5524/102382 | data licence not stated; consent text contradictory; faces may be visible (blurring not mentioned): **check before download** |
| ChildPose weights | gated Hugging Face page | CC BY-NC 4.0 + Responsible Use Policy; guardian consent for video; no covert surveillance |
| SyRIP / AggPose / InfActPrimitive | web page or Drive; password or contact for parts | non-commercial |
General rules for this project: no restricted or identifiable child footage without written authorisation; no download of any of the above until a person has read the licence and, where relevant, obtained consent for **our** purpose; no facial recognition and no age inference from faces; split by participant and recording session; no staging of dangerous falls.

## 6. Commercial suitability (our product)
- **Usable commercially, subject to a human licence check:** IKAR (CC BY 4.0, but adult falls); GMDCSA-24 and CAUCAFall (CC BY 4.0, adults); Helsinki/Pisa Zenodo data (CC BY 4.0, not images).
- **Not usable commercially (or unknown, so treat as no):** ChildPose and every model initialised from Sapiens or trained on NC data; SyRIP, AggPose, InfActPrimitive; ChildLens ("all rights reserved"); PInSoRo (academic only); NIJ and toddler data (not released); Roboflow child sets (provenance unknown).
- **Existing concern on our side:** Ultralytics YOLOv8 is AGPL-3.0; a closed commercial product needs AGPL compliance or an Enterprise licence.
- Nothing child-specific found is both public and commercially clean. Child capability will need data we collect, or data licensed from its owners.

## 7. Compatibility with our pipeline (verified by reading the code)
| Part | Where | What it takes / gives |
|---|---|---|
| Pose inference entry (live) | `falldet/detection/pose_worker.py: PoseDetectionService._run` | `cam.model.track(frame, persist=True, tracker="bytetrack.yaml", conf=0.4, imgsz=640)` on one Ultralytics YOLO object; detection and ByteTrack are one call |
| Pose entry (offline) | `tools/cctv_validate.py: build_pose` (also `tools/pose_cache.py`, `tools/debug_sequence.py`) | same call, writes a pickle cache per clip |
| Keypoint representation | `falldet/pose_estimation/keypoints.py` | COCO-17 order (nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles); array (17, 3) = x, y in **original image pixels**, confidence |
| Tracking input / output | `pose_worker.PoseDetectionService._people`; `engine.CameraFallEngine.update` | each person: `{"track_id": int or None, "bbox": [x1,y1,x2,y2] px, "confidence": detector score, "keypoints": (17,3)}`; ids from ByteTrack |
| Temporal history | `falldet/tracking/track_history.py: TrackHistory, Sample` | per-id window of `PoseFeatures` from `extract_features(ts, bbox, keypoints, frame_wh, kpt_conf)`; uses **only the box and keypoints**, nothing model-specific |
| Fall engine input | `falldet/fall_analysis/engine.py: CameraFallEngine.update(ts, people, frame_wh)` | the list above; people with `track_id=None` are given ids by `_assign_missing_ids`; `confidence < 0.4` is skipped; joints below `kpt_conf` 0.4 are ignored |
| Validation runner | `tools/cctv_validate.py: get_pose, replay, run_config` | `replay` runs the unchanged engine on cache frames `{"i","ts","people"}`; `get_pose` looks for `<cache>/<weights stem>_conf<conf>_fps<fps>_sz<imgsz>/<scenario>__<clip>.pkl` with a matching clip fingerprint |

**Can another estimator feed the engine without changing it? Yes, with conditions:**
1. It must output a person box and 17 COCO-order keypoints (x, y, confidence) in image pixels. **ChildPose does** (COCO-17, pixels), and needs boxes, which YOLO + ByteTrack already provide. A hybrid (YOLO supplies boxes and ids, a second model supplies keypoints) fits the engine as is.
2. **Confidence scales are not interchangeable.** The engine's `kpt_conf = 0.4` and `min_person_conf = 0.4` were set for YOLO's scores; ChildPose scores are heatmap peaks. Keypoint visibility must be reported at several thresholds and the engine's threshold must **not** be changed to chase a number.
3. The box quality for children still comes from YOLO's person detector, whose behaviour on children is unmeasured; ChildPose cannot rescue a child that YOLO never boxes.
4. Offline, **no engine change is needed:** a second estimator could write caches in the same pickle format into a differently named cache folder and be replayed by the unchanged runner (`build_pose` itself is YOLO-only, so a clean pluggable builder would be a small tool change later). Live, `pose_worker._run` would need a second stage; not recommended before the offline results.
5. Compute: ChildPose is a heavy per-person model; our live camera runs on a laptop CPU, so live use is unlikely. Offline comparison is feasible.

## 8. Experiment proposal (isolated; **do not run before approval and licence clearance**)
**A.** Current YOLOv8n-Pose (existing caches or a fresh run with the shipped settings).
**B.** ChildPose keypoints on **the same boxes and ids and the same frames (5 fps)** as A, so only the keypoint source differs. Run only if its authors or counsel confirm that this internal research use is allowed; otherwise skip B and use this design for any other candidate model.
Measurements (all per clip and per camera view, reported separately, **no accuracy claim without a human-labelled keypoint subset**):
- person-box availability: frames with a box, track continuity, id changes per person;
- keypoint visibility at thresholds 0.3 / 0.4 / 0.5, per joint, and especially frames where shoulders or hips (needed by the engine) are missing;
- missing-keypoint rate and `partial` frames;
- temporal stability: frame-to-frame jitter of shoulder and hip points for a still person, normalised by person height;
- processing time per frame on the same machine (CPU, and GPU if any);
- behaviour at several image scales (original, 0.75, 0.5, 0.35: simulates distance, not child proportions) and across viewpoints (GigaScience front/left/right if cleared; CAUCAFall high corner; GMDCSA fixed camera);
- a small set of human-labelled keypoint frames (for example 100-200, adults and, only with consent, children) to give any accuracy statement a basis.
**Downstream check:** replay both keypoint sources through the **unchanged engine** on the adult validation sets and compare alerts; improved keypoints are accepted only if the adult baseline does not get worse. Better keypoint metrics are never reported as better fall detection.
Isolation: separate cache folder, separate report, no change to `engine.py`, `config.py`, the live backend, thresholds or the 0.4 / 3 s settings.

## 9. Recommended order
1. **Permissions first (no code):** ask the ChildPose authors whether an internal research comparison is permitted and whether a commercial licence exists; check GigaDB's licence and whether raw video is blurred; ask the NIJ PI about release timing; (still open from round 1) ask the GMDCSA authors how four folders map to three actors.
2. Quantify the small-person problem with **adult footage rescaled to small sizes** (no child data, no licence issue).
3. If cleared: use the **GigaScience multiview children set** only for keypoint-visibility and stability comparisons (it has no falls and no human-labelled keypoints).
4. Decide the target ages (toddlers, school-age, both): the public child data cluster at under 6, while ChildPose has almost no teenagers.
5. Plan **our own consented child footage** (ethics approval, guardian consent, anonymisation, no dangerous falls): normal child activity from the real camera viewpoints first (crawling, running, jumping, sitting and playing on the floor), because false alarms on these are the likeliest problem.
6. Choose the pose route with evidence: YOLO unchanged, fine-tune a permissive backbone on our consented data, or a commercial licence for ChildPose.
7. Only then, a pluggable estimator in `pose_worker._run` and `build_pose`, engine unchanged, adult regression gate in place.

## 10. Still missing to validate child falls
- Fixed-camera child fall videos with documented ages (none public; NIJ and toddler data unavailable).
- Child normal-activity negatives from CCTV-like viewpoints (crawling, running, jumping, floor play).
- Human-labelled child keypoints on our camera views.
- Participant- and session-level independent split, and at least one independent child-representative evaluation.
- Consent, ethics approval and a safeguarding procedure for any child footage.
- A commercially usable child-capable pose model, or a licence for one.
- A measurement of YOLO's person-box recall on children.
- Resolution of the open licence questions: ChildPose (commercial/internal research), GigaDB data licence, FallVision, Le2i, Ultralytics AGPL.
- Until these exist, **no claim of child-fall reliability can be made.**

## 11. What could not be verified
ChildPose paper full text (no arXiv/DOI), its adult benchmarks, its normalisation constants and README detector, which backbone the 164 FPS refers to, any CPU speed, the gated Hugging Face terms (LICENSE raw file returned 401), the `jiaka1chen` URL (404) and the Asp1rinn mirror; ChildLens resolution, fps, consent and licence; IKAR's readme (camera, resolution, ages, consent); PInSoRo age range and dataset licence; GigaDB licence and blurring; ToddlerAct availability; weights licences of RTMPose, ViTPose and MediaPipe; SyRIP data licence; MINI-RGBD licence text; commercial SDKs with documented child accuracy.
