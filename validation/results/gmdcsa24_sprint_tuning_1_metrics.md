# GMDCSA-24 event-level metrics: gmdcsa24_sprint_tuning_1

Footage role: **tuning**. Clips scored: 80. Detector: yolov8n-pose.pt at 5.0 analysed fps. Scoring window: event -2.0 s to event + tolerance + 10.0 s.

**PUBLIC DATASET (not our cameras).** Home-style scenes, 4 subjects in total. These numbers describe how the rules behave on this dataset only; they are not validation on the office CCTV and not evidence of real-world safety.

**TUNING set (Subjects 1 and 2): not independent evidence.**

Evaluation unit: one clip = one event opportunity; frames are never counted as events. POSSIBLE (amber) and CONFIRMED (red) are reported separately; a POSSIBLE alert is never counted as a confirmed fall. Definitions are in the header of `tools/gmdcsa_eval.py`.

## POSSIBLE alerts

| config | fall clips | TP | FN | recall | false alerts (normal clips) | false alerts (fall clips) | precision | F1 | normal clips with a false alert | specificity (clip) | false alerts / normal clip | false alerts / normal min | latency median s [min..max] (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| legacy | 41 | 35 | 6 | 85.4% | 8 | 0 | 81.4% | 83.3% | 8/39 | 79.5% | 0.205 | 1.37 | 0.82 [0.41..3.22] (35) |
| fixed | 41 | 37 | 4 | 90.2% | 11 | 0 | 77.1% | 83.1% | 10/39 | 74.4% | 0.282 | 1.884 | 0.82 [-0.28..3.22] (37) |
| fixed_floor_off | 41 | 35 | 6 | 85.4% | 2 | 0 | 94.6% | 89.7% | 2/39 | 94.9% | 0.051 | 0.342 | 0.82 [0.41..2.33] (35) |

## CONFIRMED alerts

| config | fall clips | TP | FN | recall | false alerts (normal clips) | false alerts (fall clips) | precision | F1 | normal clips with a false alert | specificity (clip) | false alerts / normal clip | false alerts / normal min | latency median s [min..max] (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| legacy | 41 | 11 | 30 | 26.8% | 1 | 0 | 91.7% | 41.5% | 1/39 | 97.4% | 0.026 | 0.171 | 3.93 [3.52..6.4] (11) |
| fixed | 41 | 12 | 29 | 29.3% | 4 | 0 | 75.0% | 42.1% | 4/39 | 89.7% | 0.103 | 0.685 | 3.97 [3.52..6.4] (12) |
| fixed_floor_off | 41 | 10 | 31 | 24.4% | 0 | 0 | 100.0% | 39.2% | 0/39 | 100.0% | 0.0 | 0.0 | 3.87 [3.52..5.52] (10) |

CONFIRMED needs the person to stay down about 3 s after the fall. Many dataset clips end before that:

| config | CONFIRMED recall, all fall clips | CONFIRMED-reachable clips (>= 4.0 s after onset) | TP among them | recall among them |
|---|---|---|---|---|
| legacy | 26.8% | 18 | 7 | 38.9% |
| fixed | 29.3% | 18 | 8 | 44.4% |
| fixed_floor_off | 24.4% | 18 | 6 | 33.3% |

## legacy: by scenario

| group | fall clips | POSSIBLE detected | CONFIRMED detected | normal clips | normal with false POSSIBLE | normal with false CONFIRMED |
|---|---|---|---|---|---|---|
| fall_backward | 14 | 10 | 3 | 0 | 0 | 0 |
| fall_forward | 11 | 11 | 4 | 0 | 0 | 0 |
| fall_sideways | 16 | 14 | 4 | 0 | 0 | 0 |
| intentional_lying_down | 0 | 0 | 0 | 7 | 3 | 0 |
| normal_office_activity | 0 | 0 | 0 | 29 | 5 | 1 |
| sitting_standing | 0 | 0 | 0 | 3 | 0 | 0 |

## legacy: by fall direction

| group | fall clips | POSSIBLE detected | CONFIRMED detected | normal clips | normal with false POSSIBLE | normal with false CONFIRMED |
|---|---|---|---|---|---|---|
| BW | 14 | 10 | 3 | 0 | 0 | 0 |
| FW | 11 | 11 | 4 | 0 | 0 | 0 |
| SW | 16 | 14 | 4 | 0 | 0 | 0 |

## legacy: by subject

| group | fall clips | POSSIBLE detected | CONFIRMED detected | normal clips | normal with false POSSIBLE | normal with false CONFIRMED |
|---|---|---|---|---|---|---|
| subject 1 | 16 | 14 | 2 | 16 | 4 | 1 |
| subject 2 | 25 | 21 | 9 | 23 | 4 | 0 |

## legacy: by tag

| group | fall clips | POSSIBLE detected | CONFIRMED detected | normal clips | normal with false POSSIBLE | normal with false CONFIRMED |
|---|---|---|---|---|---|---|
| bed | 5 | 4 | 2 | 17 | 5 | 1 |
| day | 36 | 31 | 10 | 29 | 6 | 1 |
| from_chair | 6 | 6 | 0 | 7 | 0 | 0 |
| left_side | 7 | 6 | 0 | 3 | 2 | 0 |
| night | 5 | 4 | 1 | 10 | 2 | 0 |
| partly_visible | 6 | 4 | 0 | 0 | 0 | 0 |
| right_side | 9 | 9 | 3 | 1 | 1 | 0 |

## legacy: missed falls (no POSSIBLE in the window)

- `fall_backward/gmdcsa24_s1_fall_13.mp4` onset 0.4 s of 4.2 s, people seen in 22/22 analysed frames, 2 track id(s), events none, tags ['partly_visible', 'day']. Standing position to falling. Backward fall. Full body (head) is not visible | classes: Falling (BW)[0.4 to 4.0]; Standing[0.0 to 0.3]
- `fall_backward/gmdcsa24_s1_fall_14.mp4` onset 0.3 s of 5.6 s, people seen in 29/29 analysed frames, 2 track id(s), events none, tags ['partly_visible', 'day']. Standing position to falling. Backward fall. Full body (both ankles) is not visible | classes: Falling (BW)[0.3 to 5.0]; Standing[0.0 to 0.2]
- `fall_backward/gmdcsa24_s2_fall_08.mp4` onset 3.2 s of 6.0 s, people seen in 30/31 analysed frames, 3 track id(s), events none, tags ['day']. Reading a newspaper in the sitting position on the ground then falling backward | classes: Falling (BW)[3.2 to 6.0]; Reading[0.0 to 2.1]; Sitting[0.0 to 3.0]
- `fall_backward/gmdcsa24_s2_fall_12.mp4` onset 6.9 s of 12.2 s, people seen in 43/62 analysed frames, 2 track id(s), events none, tags ['night']. Drinking water from the water bottle then falling backwards | classes: Falling (BW)[6.9 to 12.0]; Drinking[3.5 to 5.3]; Standing[3.6 to 6.9]; Walking[0.0 to 3.6
- `fall_sideways/gmdcsa24_s2_fall_05.mp4` onset 0.8 s of 4.4 s, people seen in 23/23 analysed frames, 2 track id(s), events none, tags ['left_side', 'day']. Left side fall (face hidden by hand) | classes: Falling (SW)[0.8 to 4.0]; Standing[0.0 to 0.7]
- `fall_sideways/gmdcsa24_s2_fall_15.mp4` onset 7.7 s of 11.6 s, people seen in 59/59 analysed frames, 1 track id(s), events none, tags ['bed', 'day']. Writing while sitting on the bed; then falling on the ground | classes: Falling (SW)[7.7 to 11.0]; Sitting[0.0 to 7.7]; Writing[0.0 to 4.6]

## legacy: clips with false alerts

- `intentional_lying_down/gmdcsa24_s1_adl_01.mp4` (intentional_lying_down, 8.2 s): events [['possible', 5.82]], tags ['bed', 'right_side', 'day']. Sitting on the bed to sleeping right side on the bed. Face towards camera | classes: Sitting[0.0 to 1.0]; Sleeping[2.0 to 8.0]
- `intentional_lying_down/gmdcsa24_s1_adl_02.mp4` (intentional_lying_down, 6.6 s): events [['possible', 5.42]], tags ['bed', 'left_side', 'day']. Sitting on the bed to sleeping left side on the bed. Face towards the camera | classes: Sitting[0.0 to 0.5]; Sleeping[1.5 to 6.0]
- `intentional_lying_down/gmdcsa24_s1_adl_03.mp4` (intentional_lying_down, 6.6 s): events [['possible', 5.22]], tags ['bed', 'left_side', 'day']. Sitting on the bed to sleeping left side on the bed. Face towards the ceiling | classes: Sitting[0.0 to 0.5]; Sleeping[1.0 to 6.0]
- `normal_office_activity/gmdcsa24_s1_adl_06.mp4` (normal_office_activity, 12.0 s): events [['possible', 7.41], ['confirmed', 10.42]], tags ['bed', 'day']. Sitting on the bed (front view) to reading the book while supporting towards the wall. Side view | classes: Reading[3.0 to 12.0]; Sitting[0.0 to 2.0]
- `normal_office_activity/gmdcsa24_s2_adl_09.mp4` (normal_office_activity, 10.8 s): events [['possible', 4.22], ['dismissed', 5.42]], tags ['bed', 'day']. Standing up from a sitting position on the bed and then sitting on the ground, Sitting[0 to 0.5; 3.7 to 10] | classes: Standing[0.5 to 1.3]; Walking[0.5 to 3.1]
- `normal_office_activity/gmdcsa24_s2_adl_13.mp4` (normal_office_activity, 4.8 s): events [['possible', 1.01], ['dismissed', 2.21]], tags ['day']. Sitting on the ground and reading a book | classes: Reading[1.0 to 4.0]; Sitting[1.0 to 4.0]; Standing[0.0 to 0.5]
- `normal_office_activity/gmdcsa24_s2_adl_19.mp4` (normal_office_activity, 11.2 s): events [['possible', 10.22]], tags ['night']. Sitting on the ground and writing in a notebook | classes: Sitting[1.0 to 11.0]; Walking[0.0 to 0.6]; Writing[5.0 to 11.0]
- `normal_office_activity/gmdcsa24_s2_adl_22.mp4` (normal_office_activity, 12.0 s): events [['possible', 8.02], ['dismissed', 11.63]], tags ['night']. Exercising (Push-up) and sitting | classes: Exercising[1.9 to 8.3]; Sitting[9.5 to 10.5]

## fixed: missed falls (no POSSIBLE in the window)

- `fall_backward/gmdcsa24_s1_fall_14.mp4` onset 0.3 s of 5.6 s, people seen in 29/29 analysed frames, 2 track id(s), events none, tags ['partly_visible', 'day']. Standing position to falling. Backward fall. Full body (both ankles) is not visible | classes: Falling (BW)[0.3 to 5.0]; Standing[0.0 to 0.2]
- `fall_backward/gmdcsa24_s2_fall_08.mp4` onset 3.2 s of 6.0 s, people seen in 30/31 analysed frames, 3 track id(s), events none, tags ['day']. Reading a newspaper in the sitting position on the ground then falling backward | classes: Falling (BW)[3.2 to 6.0]; Reading[0.0 to 2.1]; Sitting[0.0 to 3.0]
- `fall_backward/gmdcsa24_s2_fall_12.mp4` onset 6.9 s of 12.2 s, people seen in 43/62 analysed frames, 2 track id(s), events none, tags ['night']. Drinking water from the water bottle then falling backwards | classes: Falling (BW)[6.9 to 12.0]; Drinking[3.5 to 5.3]; Standing[3.6 to 6.9]; Walking[0.0 to 3.6
- `fall_sideways/gmdcsa24_s2_fall_05.mp4` onset 0.8 s of 4.4 s, people seen in 23/23 analysed frames, 2 track id(s), events none, tags ['left_side', 'day']. Left side fall (face hidden by hand) | classes: Falling (SW)[0.8 to 4.0]; Standing[0.0 to 0.7]

## fixed: clips with false alerts

- `intentional_lying_down/gmdcsa24_s1_adl_01.mp4` (intentional_lying_down, 8.2 s): events [['possible', 4.83], ['confirmed', 8.02]], tags ['bed', 'right_side', 'day']. Sitting on the bed to sleeping right side on the bed. Face towards camera | classes: Sitting[0.0 to 1.0]; Sleeping[2.0 to 8.0]
- `intentional_lying_down/gmdcsa24_s1_adl_02.mp4` (intentional_lying_down, 6.6 s): events [['possible', 4.82]], tags ['bed', 'left_side', 'day']. Sitting on the bed to sleeping left side on the bed. Face towards the camera | classes: Sitting[0.0 to 0.5]; Sleeping[1.5 to 6.0]
- `intentional_lying_down/gmdcsa24_s1_adl_03.mp4` (intentional_lying_down, 6.6 s): events [['possible', 4.42]], tags ['bed', 'left_side', 'day']. Sitting on the bed to sleeping left side on the bed. Face towards the ceiling | classes: Sitting[0.0 to 0.5]; Sleeping[1.0 to 6.0]
- `intentional_lying_down/gmdcsa24_s2_adl_12.mp4` (intentional_lying_down, 7.4 s): events [['possible', 7.02]], tags ['bed', 'day']. Going to bed and sleeping (belly facing downwards) | classes: Sleeping[3.0 to 7.0]; Standing[0.0 to 0.1]
- `intentional_lying_down/gmdcsa24_s2_adl_16.mp4` (intentional_lying_down, 11.4 s): events [['possible', 3.22], ['possible', 7.82], ['dismissed', 8.83], ['confirmed', 10.83]], tags ['night']. Reading a newspaper; throwing the newspaper; and sleeping | classes: Reading[0.0 to 5.8]; Sleeping[9.0 to 11.0]
- `normal_office_activity/gmdcsa24_s1_adl_06.mp4` (normal_office_activity, 12.0 s): events [['possible', 6.61], ['confirmed', 9.62]], tags ['bed', 'day']. Sitting on the bed (front view) to reading the book while supporting towards the wall. Side view | classes: Reading[3.0 to 12.0]; Sitting[0.0 to 2.0]
- `normal_office_activity/gmdcsa24_s2_adl_09.mp4` (normal_office_activity, 10.8 s): events [['possible', 4.22], ['dismissed', 5.42]], tags ['bed', 'day']. Standing up from a sitting position on the bed and then sitting on the ground, Sitting[0 to 0.5; 3.7 to 10] | classes: Standing[0.5 to 1.3]; Walking[0.5 to 3.1]
- `normal_office_activity/gmdcsa24_s2_adl_13.mp4` (normal_office_activity, 4.8 s): events [['possible', 1.01], ['dismissed', 2.21]], tags ['day']. Sitting on the ground and reading a book | classes: Reading[1.0 to 4.0]; Sitting[1.0 to 4.0]; Standing[0.0 to 0.5]
- `normal_office_activity/gmdcsa24_s2_adl_19.mp4` (normal_office_activity, 11.2 s): events [['possible', 9.42]], tags ['night']. Sitting on the ground and writing in a notebook | classes: Sitting[1.0 to 11.0]; Walking[0.0 to 0.6]; Writing[5.0 to 11.0]
- `normal_office_activity/gmdcsa24_s2_adl_22.mp4` (normal_office_activity, 12.0 s): events [['possible', 7.62], ['confirmed', 10.62]], tags ['night']. Exercising (Push-up) and sitting | classes: Exercising[1.9 to 8.3]; Sitting[9.5 to 10.5]

## fixed_floor_off: missed falls (no POSSIBLE in the window)

- `fall_backward/gmdcsa24_s1_fall_14.mp4` onset 0.3 s of 5.6 s, people seen in 29/29 analysed frames, 2 track id(s), events none, tags ['partly_visible', 'day']. Standing position to falling. Backward fall. Full body (both ankles) is not visible | classes: Falling (BW)[0.3 to 5.0]; Standing[0.0 to 0.2]
- `fall_backward/gmdcsa24_s2_fall_08.mp4` onset 3.2 s of 6.0 s, people seen in 30/31 analysed frames, 3 track id(s), events none, tags ['day']. Reading a newspaper in the sitting position on the ground then falling backward | classes: Falling (BW)[3.2 to 6.0]; Reading[0.0 to 2.1]; Sitting[0.0 to 3.0]
- `fall_backward/gmdcsa24_s2_fall_11.mp4` onset 5.9 s of 10.4 s, people seen in 46/53 analysed frames, 2 track id(s), events none, tags ['bed', 'night']. Falling from bed to ground | classes: Falling (BW[5.9 to 10.0]; Walking[0.0 to 1.3]
- `fall_backward/gmdcsa24_s2_fall_12.mp4` onset 6.9 s of 12.2 s, people seen in 43/62 analysed frames, 2 track id(s), events none, tags ['night']. Drinking water from the water bottle then falling backwards | classes: Falling (BW)[6.9 to 12.0]; Drinking[3.5 to 5.3]; Standing[3.6 to 6.9]; Walking[0.0 to 3.6
- `fall_forward/gmdcsa24_s2_fall_03.mp4` onset 0.0 s of 7.0 s, people seen in 36/36 analysed frames, 2 track id(s), events none, tags ['bed', 'day']. Forward fall on the bed | classes: Falling (FW)[0.0 to 7.0]
- `fall_sideways/gmdcsa24_s2_fall_05.mp4` onset 0.8 s of 4.4 s, people seen in 23/23 analysed frames, 2 track id(s), events none, tags ['left_side', 'day']. Left side fall (face hidden by hand) | classes: Falling (SW)[0.8 to 4.0]; Standing[0.0 to 0.7]

## fixed_floor_off: clips with false alerts

- `normal_office_activity/gmdcsa24_s2_adl_09.mp4` (normal_office_activity, 10.8 s): events [['possible', 4.22], ['dismissed', 5.42]], tags ['bed', 'day']. Standing up from a sitting position on the bed and then sitting on the ground, Sitting[0 to 0.5; 3.7 to 10] | classes: Standing[0.5 to 1.3]; Walking[0.5 to 3.1]
- `normal_office_activity/gmdcsa24_s2_adl_13.mp4` (normal_office_activity, 4.8 s): events [['possible', 1.01], ['dismissed', 2.21]], tags ['day']. Sitting on the ground and reading a book | classes: Reading[1.0 to 4.0]; Sitting[1.0 to 4.0]; Standing[0.0 to 0.5]

