# Validation run gmdcsa24_baseline_independent

Independent (held-out) footage: valid only if nothing was tuned on it.

- **PUBLIC DATASET footage (not our cameras):** home-style scenes from a research dataset. These results say how the rules behave on that dataset only. They are NOT validation on the office CCTV and NOT evidence of real-world safety. (79 clips)

Clips scored: 79; skipped (no/invalid metadata): 0. Counts only: these are not accuracy figures.


| config | fall clips | POSSIBLE | CONFIRMED | missed | median confirm latency (s) | normal hours | false POSSIBLE | false CONFIRMED | false CONFIRMED / normal hour | mean frame latency (ms) | max fps (1 stream) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| default (conf 0.4) | 37 | 25 | 8 | 12 | 3.98 | 0.107 | 3 | 1 | 9.32 | 237.3 | 4.21 |
| floor_off (conf 0.4) | 37 | 23 | 8 | 14 | 3.98 | 0.107 | 2 | 0 | 0.0 | 237.0 | 4.22 |

## default: by scenario

| scenario | clips | POSSIBLE | CONFIRMED | missed | false POSSIBLE | false CONFIRMED |
|---|---|---|---|---|---|---|
| fall_backward | 14 | 9 | 3 | 5 | 0 | 0 |
| fall_forward | 11 | 8 | 3 | 3 | 0 | 0 |
| fall_sideways | 12 | 8 | 2 | 4 | 0 | 0 |
| intentional_lying_down | 7 | 0 | 0 | 0 | 1 | 1 |
| normal_office_activity | 29 | 0 | 0 | 0 | 1 | 0 |
| sitting_standing | 6 | 0 | 0 | 0 | 1 | 0 |

### default: per clip

| clip | expected | event t (s) | events | missed | latency (s) |
|---|---|---|---|---|---|
| fall_backward/gmdcsa24_s3_fall_03.mp4 | fall | 1.5 | possible@2.62 | False | None |
| fall_backward/gmdcsa24_s3_fall_04.mp4 | fall | 1.2 | possible@3.01 | False | None |
| fall_backward/gmdcsa24_s3_fall_05.mp4 | fall | 3.2 | possible@4.22, confirmed@7.6 | False | 4.4 |
| fall_backward/gmdcsa24_s3_fall_06.mp4 | fall | 0.0 | - | True | None |
| fall_backward/gmdcsa24_s3_fall_07.mp4 | fall | 1.0 | possible@1.82, confirmed@5.04 | False | 4.04 |
| fall_backward/gmdcsa24_s3_fall_09.mp4 | fall | 3.3 | - | True | None |
| fall_backward/gmdcsa24_s3_fall_12.mp4 | fall | 1.6 | possible@2.61 | False | None |
| fall_backward/gmdcsa24_s3_fall_13.mp4 | fall | 1.4 | - | True | None |
| fall_backward/gmdcsa24_s3_fall_14.mp4 | fall | 8.1 | possible@9.42 | False | None |
| fall_backward/gmdcsa24_s3_fall_15.mp4 | fall | 1.9 | possible@5.01 | False | None |
| fall_backward/gmdcsa24_s3_fall_17.mp4 | fall | 1.4 | possible@3.2, confirmed@6.42 | False | 5.02 |
| fall_backward/gmdcsa24_s3_fall_19.mp4 | fall | 2.0 | possible@2.42 | False | None |
| fall_backward/gmdcsa24_s4_fall_08.mp4 | fall | 2.3 | - | True | None |
| fall_backward/gmdcsa24_s4_fall_09.mp4 | fall | 2.3 | - | True | None |
| fall_forward/gmdcsa24_s3_fall_01.mp4 | fall | 0.0 | possible@1.2 | False | None |
| fall_forward/gmdcsa24_s3_fall_02.mp4 | fall | 2.6 | possible@3.42 | False | None |
| fall_forward/gmdcsa24_s3_fall_10.mp4 | fall | 1.7 | - | True | None |
| fall_forward/gmdcsa24_s3_fall_11.mp4 | fall | 4.7 | possible@5.81, confirmed@8.82 | False | 4.12 |
| fall_forward/gmdcsa24_s3_fall_20.mp4 | fall | 2.3 | possible@2.8, confirmed@6.21 | False | 3.91 |
| fall_forward/gmdcsa24_s4_fall_03.mp4 | fall | 1.7 | possible@3.42, dismissed@6.21 | False | None |
| fall_forward/gmdcsa24_s4_fall_04.mp4 | fall | 1.2 | possible@1.6, confirmed@4.62 | False | 3.42 |
| fall_forward/gmdcsa24_s4_fall_10.mp4 | fall | 2.2 | - | True | None |
| fall_forward/gmdcsa24_s4_fall_11.mp4 | fall | 1.2 | possible@1.82 | False | None |
| fall_forward/gmdcsa24_s4_fall_12.mp4 | fall | 1.5 | - | True | None |
| fall_forward/gmdcsa24_s4_fall_16.mp4 | fall | 3.2 | possible@3.82 | False | None |
| fall_sideways/gmdcsa24_s3_fall_08.mp4 | fall | 0.0 | possible@0.61, confirmed@3.82 | False | 3.82 |
| fall_sideways/gmdcsa24_s3_fall_16.mp4 | fall | 1.8 | - | True | None |
| fall_sideways/gmdcsa24_s3_fall_18.mp4 | fall | 4.2 | - | True | None |
| fall_sideways/gmdcsa24_s3_fall_21.mp4 | fall | 5.4 | possible@6.8 | False | None |
| fall_sideways/gmdcsa24_s4_fall_01.mp4 | fall | 1.8 | possible@2.22 | False | None |
| fall_sideways/gmdcsa24_s4_fall_02.mp4 | fall | 1.5 | - | True | None |
| fall_sideways/gmdcsa24_s4_fall_05.mp4 | fall | 2.7 | possible@7.22 | False | None |
| fall_sideways/gmdcsa24_s4_fall_06.mp4 | fall | 1.1 | possible@3.42 | False | None |
| fall_sideways/gmdcsa24_s4_fall_07.mp4 | fall | 2.4 | possible@2.61, confirmed@5.63 | False | 3.23 |
| fall_sideways/gmdcsa24_s4_fall_13.mp4 | fall | 0.3 | possible@4.62 | False | None |
| fall_sideways/gmdcsa24_s4_fall_14.mp4 | fall | 0.8 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s4_fall_17.mp4 | fall | 2.8 | - | True | None |
| intentional_lying_down/gmdcsa24_s3_adl_03.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s3_adl_08.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s3_adl_09.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s4_adl_08.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s4_adl_10.mp4 | none | None | possible@8.4, confirmed@11.62 | False | None |
| intentional_lying_down/gmdcsa24_s4_adl_15.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s4_adl_16.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_01.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_02.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_06.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_11.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_12.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_16.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_17.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_18.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_19.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_21.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_22.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_02.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_03.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_05.mp4 | none | None | possible@5.02 | False | None |
| normal_office_activity/gmdcsa24_s4_adl_06.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_09.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_11.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_12.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_13.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_17.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_18.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_19.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_20.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s3_adl_04.mp4 | none | None | possible@1.2, dismissed@3.01 | False | None |
| sitting_standing/gmdcsa24_s3_adl_10.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s3_adl_13.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s3_adl_20.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s4_adl_01.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s4_adl_04.mp4 | none | None | - | False | None |

## floor_off: by scenario

| scenario | clips | POSSIBLE | CONFIRMED | missed | false POSSIBLE | false CONFIRMED |
|---|---|---|---|---|---|---|
| fall_backward | 14 | 9 | 3 | 5 | 0 | 0 |
| fall_forward | 11 | 8 | 3 | 3 | 0 | 0 |
| fall_sideways | 12 | 6 | 2 | 6 | 0 | 0 |
| intentional_lying_down | 7 | 0 | 0 | 0 | 0 | 0 |
| normal_office_activity | 29 | 0 | 0 | 0 | 1 | 0 |
| sitting_standing | 6 | 0 | 0 | 0 | 1 | 0 |

### floor_off: per clip

| clip | expected | event t (s) | events | missed | latency (s) |
|---|---|---|---|---|---|
| fall_backward/gmdcsa24_s3_fall_03.mp4 | fall | 1.5 | possible@2.62 | False | None |
| fall_backward/gmdcsa24_s3_fall_04.mp4 | fall | 1.2 | possible@3.01 | False | None |
| fall_backward/gmdcsa24_s3_fall_05.mp4 | fall | 3.2 | possible@4.22, confirmed@7.6 | False | 4.4 |
| fall_backward/gmdcsa24_s3_fall_06.mp4 | fall | 0.0 | - | True | None |
| fall_backward/gmdcsa24_s3_fall_07.mp4 | fall | 1.0 | possible@1.82, confirmed@5.04 | False | 4.04 |
| fall_backward/gmdcsa24_s3_fall_09.mp4 | fall | 3.3 | - | True | None |
| fall_backward/gmdcsa24_s3_fall_12.mp4 | fall | 1.6 | possible@2.61 | False | None |
| fall_backward/gmdcsa24_s3_fall_13.mp4 | fall | 1.4 | - | True | None |
| fall_backward/gmdcsa24_s3_fall_14.mp4 | fall | 8.1 | possible@9.42 | False | None |
| fall_backward/gmdcsa24_s3_fall_15.mp4 | fall | 1.9 | possible@5.01 | False | None |
| fall_backward/gmdcsa24_s3_fall_17.mp4 | fall | 1.4 | possible@3.2, confirmed@6.42 | False | 5.02 |
| fall_backward/gmdcsa24_s3_fall_19.mp4 | fall | 2.0 | possible@2.42 | False | None |
| fall_backward/gmdcsa24_s4_fall_08.mp4 | fall | 2.3 | - | True | None |
| fall_backward/gmdcsa24_s4_fall_09.mp4 | fall | 2.3 | - | True | None |
| fall_forward/gmdcsa24_s3_fall_01.mp4 | fall | 0.0 | possible@1.2 | False | None |
| fall_forward/gmdcsa24_s3_fall_02.mp4 | fall | 2.6 | possible@3.42 | False | None |
| fall_forward/gmdcsa24_s3_fall_10.mp4 | fall | 1.7 | - | True | None |
| fall_forward/gmdcsa24_s3_fall_11.mp4 | fall | 4.7 | possible@5.81, confirmed@8.82 | False | 4.12 |
| fall_forward/gmdcsa24_s3_fall_20.mp4 | fall | 2.3 | possible@2.8, confirmed@6.21 | False | 3.91 |
| fall_forward/gmdcsa24_s4_fall_03.mp4 | fall | 1.7 | possible@3.42, dismissed@6.21 | False | None |
| fall_forward/gmdcsa24_s4_fall_04.mp4 | fall | 1.2 | possible@1.6, confirmed@4.62 | False | 3.42 |
| fall_forward/gmdcsa24_s4_fall_10.mp4 | fall | 2.2 | - | True | None |
| fall_forward/gmdcsa24_s4_fall_11.mp4 | fall | 1.2 | possible@1.82 | False | None |
| fall_forward/gmdcsa24_s4_fall_12.mp4 | fall | 1.5 | - | True | None |
| fall_forward/gmdcsa24_s4_fall_16.mp4 | fall | 3.2 | possible@3.82 | False | None |
| fall_sideways/gmdcsa24_s3_fall_08.mp4 | fall | 0.0 | possible@0.61, confirmed@3.82 | False | 3.82 |
| fall_sideways/gmdcsa24_s3_fall_16.mp4 | fall | 1.8 | - | True | None |
| fall_sideways/gmdcsa24_s3_fall_18.mp4 | fall | 4.2 | - | True | None |
| fall_sideways/gmdcsa24_s3_fall_21.mp4 | fall | 5.4 | possible@6.8 | False | None |
| fall_sideways/gmdcsa24_s4_fall_01.mp4 | fall | 1.8 | possible@2.22 | False | None |
| fall_sideways/gmdcsa24_s4_fall_02.mp4 | fall | 1.5 | - | True | None |
| fall_sideways/gmdcsa24_s4_fall_05.mp4 | fall | 2.7 | - | True | None |
| fall_sideways/gmdcsa24_s4_fall_06.mp4 | fall | 1.1 | possible@3.42 | False | None |
| fall_sideways/gmdcsa24_s4_fall_07.mp4 | fall | 2.4 | possible@2.61, confirmed@5.63 | False | 3.23 |
| fall_sideways/gmdcsa24_s4_fall_13.mp4 | fall | 0.3 | - | True | None |
| fall_sideways/gmdcsa24_s4_fall_14.mp4 | fall | 0.8 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s4_fall_17.mp4 | fall | 2.8 | - | True | None |
| intentional_lying_down/gmdcsa24_s3_adl_03.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s3_adl_08.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s3_adl_09.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s4_adl_08.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s4_adl_10.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s4_adl_15.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s4_adl_16.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_01.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_02.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_06.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_11.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_12.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_16.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_17.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_18.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_19.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_21.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s3_adl_22.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_02.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_03.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_05.mp4 | none | None | possible@5.02 | False | None |
| normal_office_activity/gmdcsa24_s4_adl_06.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_09.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_11.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_12.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_13.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_17.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_18.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_19.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s4_adl_20.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s3_adl_04.mp4 | none | None | possible@1.2, dismissed@3.01 | False | None |
| sitting_standing/gmdcsa24_s3_adl_10.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s3_adl_13.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s3_adl_20.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s4_adl_01.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s4_adl_04.mp4 | none | None | - | False | None |
