# GMDCSA-24 event-level metrics: gmdcsa24_final_independent

Footage role: **independent**. Clips scored: 79. Detector: yolov8n-pose.pt at 5.0 analysed fps. Scoring window: event -2.0 s to event + tolerance + 10.0 s.

**PUBLIC DATASET (not our cameras).** Home-style scenes, 4 subjects in total. These numbers describe how the rules behave on this dataset only; they are not validation on the office CCTV and not evidence of real-world safety.

**Independent evaluation covers only two held-out subjects (Subjects 3 and 4); the dataset has four subjects in total.**

Evaluation unit: one clip = one event opportunity; frames are never counted as events. POSSIBLE (amber) and CONFIRMED (red) are reported separately; a POSSIBLE alert is never counted as a confirmed fall. Definitions are in the header of `tools/gmdcsa_eval.py`.

## POSSIBLE alerts

| config | fall clips | TP | FN | recall | false alerts (normal clips) | false alerts (fall clips) | precision | F1 | normal clips with a false alert | specificity (clip) | false alerts / normal clip | false alerts / normal min | latency median s [min..max] (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| legacy | 37 | 25 | 12 | 67.6% | 3 | 0 | 89.3% | 76.9% | 3/42 | 92.9% | 0.071 | 0.466 | 1.11 [0.21..4.52] (25) |
| tuned | 37 | 26 | 11 | 70.3% | 9 | 0 | 74.3% | 72.2% | 9/42 | 78.6% | 0.214 | 1.398 | 1.11 [0.21..3.7] (26) |
| tuned_floor_off | 37 | 23 | 14 | 62.2% | 2 | 0 | 92.0% | 74.2% | 2/42 | 95.2% | 0.048 | 0.311 | 1.02 [0.21..2.52] (23) |

## CONFIRMED alerts

| config | fall clips | TP | FN | recall | false alerts (normal clips) | false alerts (fall clips) | precision | F1 | normal clips with a false alert | specificity (clip) | false alerts / normal clip | false alerts / normal min | latency median s [min..max] (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| legacy | 37 | 8 | 29 | 21.6% | 1 | 0 | 88.9% | 34.8% | 1/42 | 97.6% | 0.024 | 0.155 | 3.98 [3.23..5.02] (8) |
| tuned | 37 | 8 | 29 | 21.6% | 1 | 0 | 88.9% | 34.8% | 1/42 | 97.6% | 0.024 | 0.155 | 3.98 [3.23..5.02] (8) |
| tuned_floor_off | 37 | 8 | 29 | 21.6% | 0 | 0 | 100.0% | 35.6% | 0/42 | 100.0% | 0.0 | 0.0 | 3.98 [3.23..5.02] (8) |

CONFIRMED needs the person to stay down about 3 s after the fall. Many dataset clips end before that:

| config | CONFIRMED recall, all fall clips | CONFIRMED-reachable clips (>= 4.0 s after onset) | TP among them | recall among them |
|---|---|---|---|---|
| legacy | 21.6% | 16 | 5 | 31.2% |
| tuned | 21.6% | 16 | 5 | 31.2% |
| tuned_floor_off | 21.6% | 16 | 5 | 31.2% |

## legacy: by scenario

| group | fall clips | POSSIBLE detected | CONFIRMED detected | normal clips | normal with false POSSIBLE | normal with false CONFIRMED |
|---|---|---|---|---|---|---|
| fall_backward | 14 | 9 | 3 | 0 | 0 | 0 |
| fall_forward | 11 | 8 | 3 | 0 | 0 | 0 |
| fall_sideways | 12 | 8 | 2 | 0 | 0 | 0 |
| intentional_lying_down | 0 | 0 | 0 | 7 | 1 | 1 |
| normal_office_activity | 0 | 0 | 0 | 29 | 1 | 0 |
| sitting_standing | 0 | 0 | 0 | 6 | 1 | 0 |

## legacy: by fall direction

| group | fall clips | POSSIBLE detected | CONFIRMED detected | normal clips | normal with false POSSIBLE | normal with false CONFIRMED |
|---|---|---|---|---|---|---|
| BW | 14 | 9 | 3 | 0 | 0 | 0 |
| FW | 11 | 8 | 3 | 0 | 0 | 0 |
| SW | 12 | 8 | 2 | 0 | 0 | 0 |

## legacy: by subject

| group | fall clips | POSSIBLE detected | CONFIRMED detected | normal clips | normal with false POSSIBLE | normal with false CONFIRMED |
|---|---|---|---|---|---|---|
| subject 3 | 21 | 15 | 6 | 22 | 1 | 0 |
| subject 4 | 16 | 10 | 2 | 20 | 2 | 1 |

## legacy: by tag

| group | fall clips | POSSIBLE detected | CONFIRMED detected | normal clips | normal with false POSSIBLE | normal with false CONFIRMED |
|---|---|---|---|---|---|---|
| bed | 15 | 8 | 1 | 20 | 2 | 1 |
| day | 25 | 16 | 4 | 22 | 1 | 0 |
| floor | 19 | 13 | 5 | 13 | 1 | 0 |
| from_chair | 1 | 0 | 0 | 2 | 0 | 0 |
| left_side | 1 | 0 | 0 | 0 | 0 | 0 |
| lights_off | 6 | 5 | 2 | 12 | 2 | 1 |
| night | 6 | 4 | 2 | 8 | 0 | 0 |
| right_side | 1 | 1 | 1 | 0 | 0 | 0 |

## legacy: missed falls (no POSSIBLE in the window)

- `fall_backward/gmdcsa24_s3_fall_06.mp4` onset 0.0 s of 5.4 s, people seen in 6/28 analysed frames, 2 track id(s), events none, tags ['floor', 'day']. Falling (backward) on the floor from the sitting position | classes: Falling (BW)[0.0 to 5.0]
- `fall_backward/gmdcsa24_s3_fall_09.mp4` onset 3.3 s of 6.0 s, people seen in 26/31 analysed frames, 3 track id(s), events none, tags ['day']. Reading the book while sitting on the ground; then falling backward | classes: Falling (BW)[3.3 to 6.0]; Reading[0.0 to 3.3]; Sitting[0.0 to 3.4]
- `fall_backward/gmdcsa24_s3_fall_13.mp4` onset 1.4 s of 4.0 s, people seen in 21/21 analysed frames, 2 track id(s), events none, tags ['floor', 'day']. Writing something in a notebook while sitting position on the floor; then falling backward | classes: Falling (BW)[1.4 to 4.0]; Sitting[0.0 to 1.4]; Writing[0.0
- `fall_backward/gmdcsa24_s4_fall_08.mp4` onset 2.3 s of 6.2 s, people seen in 15/32 analysed frames, 1 track id(s), events none, tags ['bed', 'lights_off']. Falling backward on the bed from sitting on the bed | classes: Falling (BW)[2.3 to 6.0]; Sitting[0.0 to 2.2]
- `fall_backward/gmdcsa24_s4_fall_09.mp4` onset 2.3 s of 6.0 s, people seen in 31/31 analysed frames, 1 track id(s), events none, tags ['bed', 'day']. Falling backward on the bed from sitting on the bed | classes: Falling (BW)[2.3 to 6.0]; Sitting[0.0 to 2.0]
- `fall_forward/gmdcsa24_s3_fall_10.mp4` onset 1.7 s of 4.2 s, people seen in 22/22 analysed frames, 2 track id(s), events none, tags ['bed', 'day']. Falling forward on the bed | classes: Falling (FW)[1.7 to 4.0]
- `fall_forward/gmdcsa24_s4_fall_10.mp4` onset 2.2 s of 5.0 s, people seen in 14/26 analysed frames, 1 track id(s), events none, tags ['from_chair', 'day']. Reading a book while sitting on the chair then falling (FW) on the ground | classes: Falling (FW)[2.2 to 5.0]; Reading[0.0 to 2.1]; Sitting[0.0 to 2.1]
- `fall_forward/gmdcsa24_s4_fall_12.mp4` onset 1.5 s of 4.4 s, people seen in 23/23 analysed frames, 1 track id(s), events none, tags ['bed', 'floor', 'day']. Falling (FW)to the floor from sitting on the bed | classes: Falling (FW)[1.5 to 4.0]; Sitting[0.0 to 1.3]
- `fall_sideways/gmdcsa24_s3_fall_16.mp4` onset 1.8 s of 6.0 s, people seen in 15/31 analysed frames, 2 track id(s), events none, tags ['left_side', 'floor', 'night']. Walking and then falling left side on the floor | classes: Falling (SW)[1.8 to 7.0]; Walking[0.0 to 1.7]
- `fall_sideways/gmdcsa24_s3_fall_18.mp4` onset 4.2 s of 11.8 s, people seen in 25/60 analysed frames, 1 track id(s), events none, tags ['bed', 'floor', 'night']. Sitting on the bed; then falling on the floor | classes: Falling (SW)[4.2 to 11.0]; Sitting[0.0 to 3.2]
- `fall_sideways/gmdcsa24_s4_fall_02.mp4` onset 1.5 s of 2.8 s, people seen in 12/15 analysed frames, 1 track id(s), events none, tags ['bed', 'floor', 'day']. Falling (LS) from the bed to the floor | classes: Falling (SW)[1.5 to 2.0]; Sleeping[0.0 to 1.4]
- `fall_sideways/gmdcsa24_s4_fall_17.mp4` onset 2.8 s of 6.8 s, people seen in 35/35 analysed frames, 2 track id(s), events none, tags ['bed', 'day']. Falling (LS) on the bed from sitting on the bed | classes: Falling (SW)[2.8 to 6.0]; Sitting[0.0 to 2.6]

## legacy: clips with false alerts

- `intentional_lying_down/gmdcsa24_s4_adl_10.mp4` (intentional_lying_down, 12.6 s): events [['possible', 8.4], ['confirmed', 11.62]], tags ['bed', 'lights_off']. Walking then sleeping on the bed after removing the goggles | classes: Sleeping[4.3 to 12.0]; Walking[0.0 to 1.4]
- `normal_office_activity/gmdcsa24_s4_adl_05.mp4` (normal_office_activity, 7.2 s): events [['possible', 5.02]], tags ['lights_off']. Doing exercise (push-up); view 1 | classes: Exercising[2.6 to 7.0]; Walking[0.0 to 1.9]
- `sitting_standing/gmdcsa24_s3_adl_04.mp4` (sitting_standing, 10.0 s): events [['possible', 1.2], ['dismissed', 3.01]], tags ['bed', 'floor', 'day']. Picking a book from the floor and putting it on the bed; sitting on the bed | classes: Sitting[9.2 to 10.0]

## tuned: missed falls (no POSSIBLE in the window)

- `fall_backward/gmdcsa24_s3_fall_06.mp4` onset 0.0 s of 5.4 s, people seen in 6/28 analysed frames, 2 track id(s), events none, tags ['floor', 'day']. Falling (backward) on the floor from the sitting position | classes: Falling (BW)[0.0 to 5.0]
- `fall_backward/gmdcsa24_s3_fall_09.mp4` onset 3.3 s of 6.0 s, people seen in 26/31 analysed frames, 3 track id(s), events none, tags ['day']. Reading the book while sitting on the ground; then falling backward | classes: Falling (BW)[3.3 to 6.0]; Reading[0.0 to 3.3]; Sitting[0.0 to 3.4]
- `fall_backward/gmdcsa24_s3_fall_13.mp4` onset 1.4 s of 4.0 s, people seen in 21/21 analysed frames, 2 track id(s), events none, tags ['floor', 'day']. Writing something in a notebook while sitting position on the floor; then falling backward | classes: Falling (BW)[1.4 to 4.0]; Sitting[0.0 to 1.4]; Writing[0.0
- `fall_backward/gmdcsa24_s4_fall_08.mp4` onset 2.3 s of 6.2 s, people seen in 15/32 analysed frames, 1 track id(s), events none, tags ['bed', 'lights_off']. Falling backward on the bed from sitting on the bed | classes: Falling (BW)[2.3 to 6.0]; Sitting[0.0 to 2.2]
- `fall_backward/gmdcsa24_s4_fall_09.mp4` onset 2.3 s of 6.0 s, people seen in 31/31 analysed frames, 1 track id(s), events none, tags ['bed', 'day']. Falling backward on the bed from sitting on the bed | classes: Falling (BW)[2.3 to 6.0]; Sitting[0.0 to 2.0]
- `fall_forward/gmdcsa24_s3_fall_10.mp4` onset 1.7 s of 4.2 s, people seen in 22/22 analysed frames, 2 track id(s), events none, tags ['bed', 'day']. Falling forward on the bed | classes: Falling (FW)[1.7 to 4.0]
- `fall_forward/gmdcsa24_s4_fall_10.mp4` onset 2.2 s of 5.0 s, people seen in 14/26 analysed frames, 1 track id(s), events none, tags ['from_chair', 'day']. Reading a book while sitting on the chair then falling (FW) on the ground | classes: Falling (FW)[2.2 to 5.0]; Reading[0.0 to 2.1]; Sitting[0.0 to 2.1]
- `fall_forward/gmdcsa24_s4_fall_12.mp4` onset 1.5 s of 4.4 s, people seen in 23/23 analysed frames, 1 track id(s), events none, tags ['bed', 'floor', 'day']. Falling (FW)to the floor from sitting on the bed | classes: Falling (FW)[1.5 to 4.0]; Sitting[0.0 to 1.3]
- `fall_sideways/gmdcsa24_s3_fall_16.mp4` onset 1.8 s of 6.0 s, people seen in 15/31 analysed frames, 2 track id(s), events none, tags ['left_side', 'floor', 'night']. Walking and then falling left side on the floor | classes: Falling (SW)[1.8 to 7.0]; Walking[0.0 to 1.7]
- `fall_sideways/gmdcsa24_s3_fall_18.mp4` onset 4.2 s of 11.8 s, people seen in 25/60 analysed frames, 1 track id(s), events none, tags ['bed', 'floor', 'night']. Sitting on the bed; then falling on the floor | classes: Falling (SW)[4.2 to 11.0]; Sitting[0.0 to 3.2]
- `fall_sideways/gmdcsa24_s4_fall_02.mp4` onset 1.5 s of 2.8 s, people seen in 12/15 analysed frames, 1 track id(s), events none, tags ['bed', 'floor', 'day']. Falling (LS) from the bed to the floor | classes: Falling (SW)[1.5 to 2.0]; Sleeping[0.0 to 1.4]

## tuned: clips with false alerts

- `intentional_lying_down/gmdcsa24_s3_adl_03.mp4` (intentional_lying_down, 9.8 s): events [['possible', 3.22], ['dismissed', 6.21]], tags ['bed', 'day']. Getting up from the sleeping position from the bed; Putting a mask on the face; then walking | classes: Sitting[3.0 to 7.4]; Sleeping[0.0 to 1.0]; Standing[7.6 
- `intentional_lying_down/gmdcsa24_s3_adl_08.mp4` (intentional_lying_down, 4.8 s): events [['possible', 4.82]], tags ['floor', 'day']. Sitting to sleeping on the floor | classes: Sitting[0.0 to 0.8]; Sleeping[0.8 to 4.0]
- `intentional_lying_down/gmdcsa24_s3_adl_09.mp4` (intentional_lying_down, 7.6 s): events [['possible', 3.42], ['confirmed', 6.61]], tags ['floor', 'day']. Sleeping on the floor to sitting and then standing | classes: Sitting[2.5 to 6.0]; Sleeping[0.0 to 2.2]; Standing[6.2 to 7.0]
- `intentional_lying_down/gmdcsa24_s4_adl_10.mp4` (intentional_lying_down, 12.6 s): events [['possible', 10.62]], tags ['bed', 'lights_off']. Walking then sleeping on the bed after removing the goggles | classes: Sleeping[4.3 to 12.0]; Walking[0.0 to 1.4]
- `intentional_lying_down/gmdcsa24_s4_adl_15.mp4` (intentional_lying_down, 5.2 s): events [['possible', 4.62]], tags ['bed', 'day']. Sitting to sleeping on the bed | classes: Sitting[0.0 to 0.5]; Sleeping[1.6 to 5.0]
- `intentional_lying_down/gmdcsa24_s4_adl_16.mp4` (intentional_lying_down, 7.0 s): events [['possible', 6.4]], tags ['bed', 'day']. Sitting on the bed; removing the goggles; then sleeping | classes: Sitting[0.5 to 2.8]; Sleeping[2.9 to 7.0]
- `normal_office_activity/gmdcsa24_s4_adl_05.mp4` (normal_office_activity, 7.2 s): events [['possible', 5.02]], tags ['lights_off']. Doing exercise (push-up); view 1 | classes: Exercising[2.6 to 7.0]; Walking[0.0 to 1.9]
- `normal_office_activity/gmdcsa24_s4_adl_06.mp4` (normal_office_activity, 6.4 s): events [['possible', 6.21]], tags ['lights_off']. Doing exercise (push-up); view 2 | classes: Exercising[1.4 to 6.0]; Walking[0.0 to 1.0]
- `sitting_standing/gmdcsa24_s3_adl_04.mp4` (sitting_standing, 10.0 s): events [['possible', 1.2], ['dismissed', 3.01]], tags ['bed', 'floor', 'day']. Picking a book from the floor and putting it on the bed; sitting on the bed | classes: Sitting[9.2 to 10.0]

## tuned_floor_off: missed falls (no POSSIBLE in the window)

- `fall_backward/gmdcsa24_s3_fall_06.mp4` onset 0.0 s of 5.4 s, people seen in 6/28 analysed frames, 2 track id(s), events none, tags ['floor', 'day']. Falling (backward) on the floor from the sitting position | classes: Falling (BW)[0.0 to 5.0]
- `fall_backward/gmdcsa24_s3_fall_09.mp4` onset 3.3 s of 6.0 s, people seen in 26/31 analysed frames, 3 track id(s), events none, tags ['day']. Reading the book while sitting on the ground; then falling backward | classes: Falling (BW)[3.3 to 6.0]; Reading[0.0 to 3.3]; Sitting[0.0 to 3.4]
- `fall_backward/gmdcsa24_s3_fall_13.mp4` onset 1.4 s of 4.0 s, people seen in 21/21 analysed frames, 2 track id(s), events none, tags ['floor', 'day']. Writing something in a notebook while sitting position on the floor; then falling backward | classes: Falling (BW)[1.4 to 4.0]; Sitting[0.0 to 1.4]; Writing[0.0
- `fall_backward/gmdcsa24_s4_fall_08.mp4` onset 2.3 s of 6.2 s, people seen in 15/32 analysed frames, 1 track id(s), events none, tags ['bed', 'lights_off']. Falling backward on the bed from sitting on the bed | classes: Falling (BW)[2.3 to 6.0]; Sitting[0.0 to 2.2]
- `fall_backward/gmdcsa24_s4_fall_09.mp4` onset 2.3 s of 6.0 s, people seen in 31/31 analysed frames, 1 track id(s), events none, tags ['bed', 'day']. Falling backward on the bed from sitting on the bed | classes: Falling (BW)[2.3 to 6.0]; Sitting[0.0 to 2.0]
- `fall_forward/gmdcsa24_s3_fall_10.mp4` onset 1.7 s of 4.2 s, people seen in 22/22 analysed frames, 2 track id(s), events none, tags ['bed', 'day']. Falling forward on the bed | classes: Falling (FW)[1.7 to 4.0]
- `fall_forward/gmdcsa24_s4_fall_10.mp4` onset 2.2 s of 5.0 s, people seen in 14/26 analysed frames, 1 track id(s), events none, tags ['from_chair', 'day']. Reading a book while sitting on the chair then falling (FW) on the ground | classes: Falling (FW)[2.2 to 5.0]; Reading[0.0 to 2.1]; Sitting[0.0 to 2.1]
- `fall_forward/gmdcsa24_s4_fall_12.mp4` onset 1.5 s of 4.4 s, people seen in 23/23 analysed frames, 1 track id(s), events none, tags ['bed', 'floor', 'day']. Falling (FW)to the floor from sitting on the bed | classes: Falling (FW)[1.5 to 4.0]; Sitting[0.0 to 1.3]
- `fall_sideways/gmdcsa24_s3_fall_16.mp4` onset 1.8 s of 6.0 s, people seen in 15/31 analysed frames, 2 track id(s), events none, tags ['left_side', 'floor', 'night']. Walking and then falling left side on the floor | classes: Falling (SW)[1.8 to 7.0]; Walking[0.0 to 1.7]
- `fall_sideways/gmdcsa24_s3_fall_18.mp4` onset 4.2 s of 11.8 s, people seen in 25/60 analysed frames, 1 track id(s), events none, tags ['bed', 'floor', 'night']. Sitting on the bed; then falling on the floor | classes: Falling (SW)[4.2 to 11.0]; Sitting[0.0 to 3.2]
- `fall_sideways/gmdcsa24_s4_fall_02.mp4` onset 1.5 s of 2.8 s, people seen in 12/15 analysed frames, 1 track id(s), events none, tags ['bed', 'floor', 'day']. Falling (LS) from the bed to the floor | classes: Falling (SW)[1.5 to 2.0]; Sleeping[0.0 to 1.4]
- `fall_sideways/gmdcsa24_s4_fall_05.mp4` onset 2.7 s of 7.2 s, people seen in 37/37 analysed frames, 2 track id(s), events none, tags ['bed', 'lights_off']. Falling (RS) on the bed from sitting on the bed | classes: Falling (SW)[2.7 to 7.0]; Sitting[0.0 to 2.4]
- `fall_sideways/gmdcsa24_s4_fall_13.mp4` onset 0.3 s of 4.8 s, people seen in 25/25 analysed frames, 2 track id(s), events none, tags ['bed', 'day']. Falling (sideways) on the bed from sitting on the bed | classes: Falling (SW)[0.3 to 5.0]
- `fall_sideways/gmdcsa24_s4_fall_17.mp4` onset 2.8 s of 6.8 s, people seen in 35/35 analysed frames, 2 track id(s), events none, tags ['bed', 'day']. Falling (LS) on the bed from sitting on the bed | classes: Falling (SW)[2.8 to 6.0]; Sitting[0.0 to 2.6]

## tuned_floor_off: clips with false alerts

- `normal_office_activity/gmdcsa24_s4_adl_05.mp4` (normal_office_activity, 7.2 s): events [['possible', 5.02]], tags ['lights_off']. Doing exercise (push-up); view 1 | classes: Exercising[2.6 to 7.0]; Walking[0.0 to 1.9]
- `sitting_standing/gmdcsa24_s3_adl_04.mp4` (sitting_standing, 10.0 s): events [['possible', 1.2], ['dismissed', 3.01]], tags ['bed', 'floor', 'day']. Picking a book from the floor and putting it on the bed; sitting on the bed | classes: Sitting[9.2 to 10.0]

