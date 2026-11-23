# Validation run gmdcsa24_sprint_tuning_2

**TUNING footage: results here are NOT independent validation.**

- **PUBLIC DATASET footage (not our cameras):** home-style scenes from a research dataset. These results say how the rules behave on that dataset only. They are NOT validation on the office CCTV and NOT evidence of real-world safety. (80 clips)

Clips scored: 80; skipped (no/invalid metadata): 0. Counts only: these are not accuracy figures.


| config | fall clips | POSSIBLE | CONFIRMED | missed | median confirm latency (s) | normal hours | false POSSIBLE | false CONFIRMED | false CONFIRMED / normal hour | mean frame latency (ms) | max fps (1 stream) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fixed (conf 0.4) | 41 | 37 | 12 | 4 | 3.97 | 0.097 | 11 | 4 | 41.1 | 318.7 | 3.14 |
| asp12 (conf 0.4) | 41 | 38 | 12 | 3 | 3.97 | 0.097 | 11 | 5 | 51.37 | 318.9 | 3.14 |
| top40 (conf 0.4) | 41 | 38 | 13 | 3 | 4.02 | 0.097 | 12 | 4 | 41.1 | 318.9 | 3.14 |
| top35 (conf 0.4) | 41 | 39 | 13 | 2 | 4.02 | 0.097 | 13 | 4 | 41.1 | 318.8 | 3.14 |
| asp12_top35 (conf 0.4) | 41 | 40 | 13 | 1 | 4.02 | 0.097 | 13 | 5 | 51.37 | 318.8 | 3.14 |
| asp12_top35_floor_off (conf 0.4) | 41 | 38 | 11 | 3 | 3.93 | 0.097 | 4 | 0 | 0.0 | 318.9 | 3.14 |

## fixed: by scenario

| scenario | clips | POSSIBLE | CONFIRMED | missed | false POSSIBLE | false CONFIRMED |
|---|---|---|---|---|---|---|
| fall_backward | 14 | 11 | 4 | 3 | 0 | 0 |
| fall_forward | 11 | 11 | 4 | 0 | 0 | 0 |
| fall_sideways | 16 | 15 | 4 | 1 | 0 | 0 |
| intentional_lying_down | 7 | 0 | 0 | 0 | 6 | 2 |
| normal_office_activity | 29 | 0 | 0 | 0 | 5 | 2 |
| sitting_standing | 3 | 0 | 0 | 0 | 0 | 0 |

### fixed: per clip

| clip | expected | event t (s) | events | missed | latency (s) |
|---|---|---|---|---|---|
| fall_backward/gmdcsa24_s1_fall_11.mp4 | fall | 1.0 | possible@2.21 | False | None |
| fall_backward/gmdcsa24_s1_fall_12.mp4 | fall | 1.9 | possible@3.22 | False | None |
| fall_backward/gmdcsa24_s1_fall_13.mp4 | fall | 0.4 | possible@1.62 | False | None |
| fall_backward/gmdcsa24_s1_fall_14.mp4 | fall | 0.3 | - | True | None |
| fall_backward/gmdcsa24_s2_fall_04.mp4 | fall | 3.3 | possible@5.63, confirmed@8.82 | False | 5.52 |
| fall_backward/gmdcsa24_s2_fall_06.mp4 | fall | 2.1 | possible@3.62 | False | None |
| fall_backward/gmdcsa24_s2_fall_08.mp4 | fall | 3.2 | - | True | None |
| fall_backward/gmdcsa24_s2_fall_09.mp4 | fall | 1.8 | possible@2.42 | False | None |
| fall_backward/gmdcsa24_s2_fall_10.mp4 | fall | 2.0 | possible@3.22 | False | None |
| fall_backward/gmdcsa24_s2_fall_11.mp4 | fall | 5.9 | possible@5.62, confirmed@10.22 | False | 4.32 |
| fall_backward/gmdcsa24_s2_fall_12.mp4 | fall | 6.9 | - | True | None |
| fall_backward/gmdcsa24_s2_fall_13.mp4 | fall | 2.5 | possible@4.21 | False | None |
| fall_backward/gmdcsa24_s2_fall_14.mp4 | fall | 3.4 | possible@5.02, confirmed@8.22 | False | 4.82 |
| fall_backward/gmdcsa24_s2_fall_25.mp4 | fall | 3.0 | possible@3.81, confirmed@7.02 | False | 4.02 |
| fall_forward/gmdcsa24_s1_fall_08.mp4 | fall | 0.8 | possible@1.44 | False | None |
| fall_forward/gmdcsa24_s1_fall_09.mp4 | fall | 0.7 | possible@2.21 | False | None |
| fall_forward/gmdcsa24_s1_fall_10.mp4 | fall | 0.7 | possible@1.62, dismissed@3.02 | False | None |
| fall_forward/gmdcsa24_s2_fall_03.mp4 | fall | 0.0 | possible@3.22, confirmed@6.4 | False | 6.4 |
| fall_forward/gmdcsa24_s2_fall_07.mp4 | fall | 2.0 | possible@2.82 | False | None |
| fall_forward/gmdcsa24_s2_fall_16.mp4 | fall | 0.8 | possible@1.6 | False | None |
| fall_forward/gmdcsa24_s2_fall_17.mp4 | fall | 2.5 | possible@3.22, confirmed@6.43 | False | 3.93 |
| fall_forward/gmdcsa24_s2_fall_18.mp4 | fall | 9.8 | possible@10.82 | False | None |
| fall_forward/gmdcsa24_s2_fall_19.mp4 | fall | 8.2 | possible@8.82, confirmed@11.82 | False | 3.62 |
| fall_forward/gmdcsa24_s2_fall_20.mp4 | fall | 7.9 | possible@8.61 | False | None |
| fall_forward/gmdcsa24_s2_fall_22.mp4 | fall | 1.3 | possible@2.02, confirmed@5.02 | False | 3.72 |
| fall_sideways/gmdcsa24_s1_fall_01.mp4 | fall | 3.4 | possible@4.22 | False | None |
| fall_sideways/gmdcsa24_s1_fall_02.mp4 | fall | 1.9 | possible@2.42 | False | None |
| fall_sideways/gmdcsa24_s1_fall_03.mp4 | fall | 2.5 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s1_fall_04.mp4 | fall | 2.3 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s1_fall_05.mp4 | fall | 1.8 | possible@2.42, confirmed@5.42 | False | 3.62 |
| fall_sideways/gmdcsa24_s1_fall_06.mp4 | fall | 2.2 | possible@2.61 | False | None |
| fall_sideways/gmdcsa24_s1_fall_07.mp4 | fall | 1.1 | possible@1.62, confirmed@4.62 | False | 3.52 |
| fall_sideways/gmdcsa24_s1_fall_15.mp4 | fall | 1.8 | possible@3.02 | False | None |
| fall_sideways/gmdcsa24_s1_fall_16.mp4 | fall | 2.8 | possible@3.63 | False | None |
| fall_sideways/gmdcsa24_s2_fall_01.mp4 | fall | 1.4 | possible@2.61 | False | None |
| fall_sideways/gmdcsa24_s2_fall_02.mp4 | fall | 2.7 | possible@3.42, confirmed@8.21 | False | 5.51 |
| fall_sideways/gmdcsa24_s2_fall_05.mp4 | fall | 0.8 | - | True | None |
| fall_sideways/gmdcsa24_s2_fall_15.mp4 | fall | 7.7 | possible@9.22 | False | None |
| fall_sideways/gmdcsa24_s2_fall_21.mp4 | fall | 6.2 | possible@7.01 | False | None |
| fall_sideways/gmdcsa24_s2_fall_23.mp4 | fall | 3.6 | possible@4.4, confirmed@7.41 | False | 3.81 |
| fall_sideways/gmdcsa24_s2_fall_24.mp4 | fall | 3.3 | possible@5.22 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_01.mp4 | none | None | possible@4.83, confirmed@8.02 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_02.mp4 | none | None | possible@4.82 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_03.mp4 | none | None | possible@4.42 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_04.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_03.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_12.mp4 | none | None | possible@7.02 | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_16.mp4 | none | None | possible@3.22, possible@7.82, dismissed@8.83, confirmed@10.83 | False | None |
| normal_office_activity/gmdcsa24_s1_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_06.mp4 | none | None | possible@6.61, confirmed@9.62 | False | None |
| normal_office_activity/gmdcsa24_s1_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_08.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_09.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_10.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_11.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_12.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_13.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_01.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_02.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_04.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_08.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_09.mp4 | none | None | possible@4.22, dismissed@5.42 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_10.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_13.mp4 | none | None | possible@1.01, dismissed@2.21 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_17.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_18.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_19.mp4 | none | None | possible@9.42 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_20.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_21.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_22.mp4 | none | None | possible@7.62, confirmed@10.62 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_23.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s1_adl_16.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s2_adl_06.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s2_adl_11.mp4 | none | None | - | False | None |

## asp12: by scenario

| scenario | clips | POSSIBLE | CONFIRMED | missed | false POSSIBLE | false CONFIRMED |
|---|---|---|---|---|---|---|
| fall_backward | 14 | 12 | 4 | 2 | 0 | 0 |
| fall_forward | 11 | 11 | 4 | 0 | 0 | 0 |
| fall_sideways | 16 | 15 | 4 | 1 | 0 | 0 |
| intentional_lying_down | 7 | 0 | 0 | 0 | 6 | 3 |
| normal_office_activity | 29 | 0 | 0 | 0 | 5 | 2 |
| sitting_standing | 3 | 0 | 0 | 0 | 0 | 0 |

### asp12: per clip

| clip | expected | event t (s) | events | missed | latency (s) |
|---|---|---|---|---|---|
| fall_backward/gmdcsa24_s1_fall_11.mp4 | fall | 1.0 | possible@2.21 | False | None |
| fall_backward/gmdcsa24_s1_fall_12.mp4 | fall | 1.9 | possible@3.22 | False | None |
| fall_backward/gmdcsa24_s1_fall_13.mp4 | fall | 0.4 | possible@1.62 | False | None |
| fall_backward/gmdcsa24_s1_fall_14.mp4 | fall | 0.3 | possible@1.81 | False | None |
| fall_backward/gmdcsa24_s2_fall_04.mp4 | fall | 3.3 | possible@5.63, confirmed@8.82 | False | 5.52 |
| fall_backward/gmdcsa24_s2_fall_06.mp4 | fall | 2.1 | possible@3.62 | False | None |
| fall_backward/gmdcsa24_s2_fall_08.mp4 | fall | 3.2 | - | True | None |
| fall_backward/gmdcsa24_s2_fall_09.mp4 | fall | 1.8 | possible@2.42 | False | None |
| fall_backward/gmdcsa24_s2_fall_10.mp4 | fall | 2.0 | possible@3.22 | False | None |
| fall_backward/gmdcsa24_s2_fall_11.mp4 | fall | 5.9 | possible@5.62, confirmed@10.22 | False | 4.32 |
| fall_backward/gmdcsa24_s2_fall_12.mp4 | fall | 6.9 | - | True | None |
| fall_backward/gmdcsa24_s2_fall_13.mp4 | fall | 2.5 | possible@4.21 | False | None |
| fall_backward/gmdcsa24_s2_fall_14.mp4 | fall | 3.4 | possible@5.02, confirmed@8.22 | False | 4.82 |
| fall_backward/gmdcsa24_s2_fall_25.mp4 | fall | 3.0 | possible@3.81, confirmed@7.02 | False | 4.02 |
| fall_forward/gmdcsa24_s1_fall_08.mp4 | fall | 0.8 | possible@1.44 | False | None |
| fall_forward/gmdcsa24_s1_fall_09.mp4 | fall | 0.7 | possible@2.21 | False | None |
| fall_forward/gmdcsa24_s1_fall_10.mp4 | fall | 0.7 | possible@1.62, dismissed@3.02 | False | None |
| fall_forward/gmdcsa24_s2_fall_03.mp4 | fall | 0.0 | possible@3.22, confirmed@6.4 | False | 6.4 |
| fall_forward/gmdcsa24_s2_fall_07.mp4 | fall | 2.0 | possible@2.82 | False | None |
| fall_forward/gmdcsa24_s2_fall_16.mp4 | fall | 0.8 | possible@1.6 | False | None |
| fall_forward/gmdcsa24_s2_fall_17.mp4 | fall | 2.5 | possible@3.22, confirmed@6.43 | False | 3.93 |
| fall_forward/gmdcsa24_s2_fall_18.mp4 | fall | 9.8 | possible@10.82 | False | None |
| fall_forward/gmdcsa24_s2_fall_19.mp4 | fall | 8.2 | possible@8.82, confirmed@11.82 | False | 3.62 |
| fall_forward/gmdcsa24_s2_fall_20.mp4 | fall | 7.9 | possible@8.61 | False | None |
| fall_forward/gmdcsa24_s2_fall_22.mp4 | fall | 1.3 | possible@2.02, confirmed@5.02 | False | 3.72 |
| fall_sideways/gmdcsa24_s1_fall_01.mp4 | fall | 3.4 | possible@4.22 | False | None |
| fall_sideways/gmdcsa24_s1_fall_02.mp4 | fall | 1.9 | possible@2.42 | False | None |
| fall_sideways/gmdcsa24_s1_fall_03.mp4 | fall | 2.5 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s1_fall_04.mp4 | fall | 2.3 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s1_fall_05.mp4 | fall | 1.8 | possible@2.42, confirmed@5.42 | False | 3.62 |
| fall_sideways/gmdcsa24_s1_fall_06.mp4 | fall | 2.2 | possible@2.61 | False | None |
| fall_sideways/gmdcsa24_s1_fall_07.mp4 | fall | 1.1 | possible@1.62, confirmed@4.62 | False | 3.52 |
| fall_sideways/gmdcsa24_s1_fall_15.mp4 | fall | 1.8 | possible@3.02 | False | None |
| fall_sideways/gmdcsa24_s1_fall_16.mp4 | fall | 2.8 | possible@3.63 | False | None |
| fall_sideways/gmdcsa24_s2_fall_01.mp4 | fall | 1.4 | possible@2.61 | False | None |
| fall_sideways/gmdcsa24_s2_fall_02.mp4 | fall | 2.7 | possible@3.42, confirmed@8.21 | False | 5.51 |
| fall_sideways/gmdcsa24_s2_fall_05.mp4 | fall | 0.8 | - | True | None |
| fall_sideways/gmdcsa24_s2_fall_15.mp4 | fall | 7.7 | possible@9.22 | False | None |
| fall_sideways/gmdcsa24_s2_fall_21.mp4 | fall | 6.2 | possible@7.01 | False | None |
| fall_sideways/gmdcsa24_s2_fall_23.mp4 | fall | 3.6 | possible@4.4, confirmed@7.41 | False | 3.81 |
| fall_sideways/gmdcsa24_s2_fall_24.mp4 | fall | 3.3 | possible@5.22 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_01.mp4 | none | None | possible@4.83, confirmed@8.02 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_02.mp4 | none | None | possible@4.82 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_03.mp4 | none | None | possible@4.42 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_04.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_03.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_12.mp4 | none | None | possible@7.02 | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_16.mp4 | none | None | possible@3.22, possible@7.82, confirmed@8.83, confirmed@10.83 | False | None |
| normal_office_activity/gmdcsa24_s1_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_06.mp4 | none | None | possible@6.61, confirmed@9.62 | False | None |
| normal_office_activity/gmdcsa24_s1_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_08.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_09.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_10.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_11.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_12.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_13.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_01.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_02.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_04.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_08.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_09.mp4 | none | None | possible@4.22, dismissed@5.42 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_10.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_13.mp4 | none | None | possible@1.01, dismissed@2.21 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_17.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_18.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_19.mp4 | none | None | possible@9.42 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_20.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_21.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_22.mp4 | none | None | possible@7.62, confirmed@10.62 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_23.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s1_adl_16.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s2_adl_06.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s2_adl_11.mp4 | none | None | - | False | None |

## top40: by scenario

| scenario | clips | POSSIBLE | CONFIRMED | missed | false POSSIBLE | false CONFIRMED |
|---|---|---|---|---|---|---|
| fall_backward | 14 | 11 | 4 | 3 | 0 | 0 |
| fall_forward | 11 | 11 | 4 | 0 | 0 | 0 |
| fall_sideways | 16 | 16 | 5 | 0 | 0 | 0 |
| intentional_lying_down | 7 | 0 | 0 | 0 | 6 | 2 |
| normal_office_activity | 29 | 0 | 0 | 0 | 6 | 2 |
| sitting_standing | 3 | 0 | 0 | 0 | 0 | 0 |

### top40: per clip

| clip | expected | event t (s) | events | missed | latency (s) |
|---|---|---|---|---|---|
| fall_backward/gmdcsa24_s1_fall_11.mp4 | fall | 1.0 | possible@2.21 | False | None |
| fall_backward/gmdcsa24_s1_fall_12.mp4 | fall | 1.9 | possible@3.22 | False | None |
| fall_backward/gmdcsa24_s1_fall_13.mp4 | fall | 0.4 | possible@1.62 | False | None |
| fall_backward/gmdcsa24_s1_fall_14.mp4 | fall | 0.3 | - | True | None |
| fall_backward/gmdcsa24_s2_fall_04.mp4 | fall | 3.3 | possible@5.63, confirmed@8.82 | False | 5.52 |
| fall_backward/gmdcsa24_s2_fall_06.mp4 | fall | 2.1 | possible@3.62 | False | None |
| fall_backward/gmdcsa24_s2_fall_08.mp4 | fall | 3.2 | - | True | None |
| fall_backward/gmdcsa24_s2_fall_09.mp4 | fall | 1.8 | possible@2.42 | False | None |
| fall_backward/gmdcsa24_s2_fall_10.mp4 | fall | 2.0 | possible@3.22 | False | None |
| fall_backward/gmdcsa24_s2_fall_11.mp4 | fall | 5.9 | possible@5.62, confirmed@10.22 | False | 4.32 |
| fall_backward/gmdcsa24_s2_fall_12.mp4 | fall | 6.9 | - | True | None |
| fall_backward/gmdcsa24_s2_fall_13.mp4 | fall | 2.5 | possible@4.21 | False | None |
| fall_backward/gmdcsa24_s2_fall_14.mp4 | fall | 3.4 | possible@5.02, confirmed@8.22 | False | 4.82 |
| fall_backward/gmdcsa24_s2_fall_25.mp4 | fall | 3.0 | possible@3.81, confirmed@7.02 | False | 4.02 |
| fall_forward/gmdcsa24_s1_fall_08.mp4 | fall | 0.8 | possible@1.44 | False | None |
| fall_forward/gmdcsa24_s1_fall_09.mp4 | fall | 0.7 | possible@2.21 | False | None |
| fall_forward/gmdcsa24_s1_fall_10.mp4 | fall | 0.7 | possible@1.62, dismissed@3.02 | False | None |
| fall_forward/gmdcsa24_s2_fall_03.mp4 | fall | 0.0 | possible@3.22, confirmed@6.4 | False | 6.4 |
| fall_forward/gmdcsa24_s2_fall_07.mp4 | fall | 2.0 | possible@2.82 | False | None |
| fall_forward/gmdcsa24_s2_fall_16.mp4 | fall | 0.8 | possible@1.6 | False | None |
| fall_forward/gmdcsa24_s2_fall_17.mp4 | fall | 2.5 | possible@3.22, confirmed@6.43 | False | 3.93 |
| fall_forward/gmdcsa24_s2_fall_18.mp4 | fall | 9.8 | possible@10.82 | False | None |
| fall_forward/gmdcsa24_s2_fall_19.mp4 | fall | 8.2 | possible@8.82, confirmed@11.82 | False | 3.62 |
| fall_forward/gmdcsa24_s2_fall_20.mp4 | fall | 7.9 | possible@8.61 | False | None |
| fall_forward/gmdcsa24_s2_fall_22.mp4 | fall | 1.3 | possible@2.02, confirmed@5.02 | False | 3.72 |
| fall_sideways/gmdcsa24_s1_fall_01.mp4 | fall | 3.4 | possible@4.22 | False | None |
| fall_sideways/gmdcsa24_s1_fall_02.mp4 | fall | 1.9 | possible@2.42 | False | None |
| fall_sideways/gmdcsa24_s1_fall_03.mp4 | fall | 2.5 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s1_fall_04.mp4 | fall | 2.3 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s1_fall_05.mp4 | fall | 1.8 | possible@2.42, confirmed@5.42 | False | 3.62 |
| fall_sideways/gmdcsa24_s1_fall_06.mp4 | fall | 2.2 | possible@2.61 | False | None |
| fall_sideways/gmdcsa24_s1_fall_07.mp4 | fall | 1.1 | possible@1.62, confirmed@4.62 | False | 3.52 |
| fall_sideways/gmdcsa24_s1_fall_15.mp4 | fall | 1.8 | possible@2.61, confirmed@5.82 | False | 4.02 |
| fall_sideways/gmdcsa24_s1_fall_16.mp4 | fall | 2.8 | possible@3.63 | False | None |
| fall_sideways/gmdcsa24_s2_fall_01.mp4 | fall | 1.4 | possible@2.4 | False | None |
| fall_sideways/gmdcsa24_s2_fall_02.mp4 | fall | 2.7 | possible@3.42, confirmed@8.21 | False | 5.51 |
| fall_sideways/gmdcsa24_s2_fall_05.mp4 | fall | 0.8 | possible@2.21 | False | None |
| fall_sideways/gmdcsa24_s2_fall_15.mp4 | fall | 7.7 | possible@9.22 | False | None |
| fall_sideways/gmdcsa24_s2_fall_21.mp4 | fall | 6.2 | possible@7.01 | False | None |
| fall_sideways/gmdcsa24_s2_fall_23.mp4 | fall | 3.6 | possible@4.4, confirmed@7.41 | False | 3.81 |
| fall_sideways/gmdcsa24_s2_fall_24.mp4 | fall | 3.3 | possible@5.22 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_01.mp4 | none | None | possible@4.83, confirmed@8.02 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_02.mp4 | none | None | possible@4.82 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_03.mp4 | none | None | possible@4.42 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_04.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_03.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_12.mp4 | none | None | possible@7.02 | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_16.mp4 | none | None | possible@3.22, possible@7.82, dismissed@8.83, confirmed@10.83 | False | None |
| normal_office_activity/gmdcsa24_s1_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_06.mp4 | none | None | possible@6.61, confirmed@9.62 | False | None |
| normal_office_activity/gmdcsa24_s1_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_08.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_09.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_10.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_11.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_12.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_13.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_01.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_02.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_04.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_08.mp4 | none | None | possible@7.41, dismissed@10.62 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_09.mp4 | none | None | possible@4.22, dismissed@5.42 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_10.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_13.mp4 | none | None | possible@1.01, dismissed@2.21 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_17.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_18.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_19.mp4 | none | None | possible@9.42 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_20.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_21.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_22.mp4 | none | None | possible@7.62, confirmed@10.62 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_23.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s1_adl_16.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s2_adl_06.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s2_adl_11.mp4 | none | None | - | False | None |

## top35: by scenario

| scenario | clips | POSSIBLE | CONFIRMED | missed | false POSSIBLE | false CONFIRMED |
|---|---|---|---|---|---|---|
| fall_backward | 14 | 12 | 4 | 2 | 0 | 0 |
| fall_forward | 11 | 11 | 4 | 0 | 0 | 0 |
| fall_sideways | 16 | 16 | 5 | 0 | 0 | 0 |
| intentional_lying_down | 7 | 0 | 0 | 0 | 6 | 2 |
| normal_office_activity | 29 | 0 | 0 | 0 | 6 | 2 |
| sitting_standing | 3 | 0 | 0 | 0 | 1 | 0 |

### top35: per clip

| clip | expected | event t (s) | events | missed | latency (s) |
|---|---|---|---|---|---|
| fall_backward/gmdcsa24_s1_fall_11.mp4 | fall | 1.0 | possible@2.21 | False | None |
| fall_backward/gmdcsa24_s1_fall_12.mp4 | fall | 1.9 | possible@3.22 | False | None |
| fall_backward/gmdcsa24_s1_fall_13.mp4 | fall | 0.4 | possible@1.62 | False | None |
| fall_backward/gmdcsa24_s1_fall_14.mp4 | fall | 0.3 | - | True | None |
| fall_backward/gmdcsa24_s2_fall_04.mp4 | fall | 3.3 | possible@5.63, confirmed@8.82 | False | 5.52 |
| fall_backward/gmdcsa24_s2_fall_06.mp4 | fall | 2.1 | possible@3.62 | False | None |
| fall_backward/gmdcsa24_s2_fall_08.mp4 | fall | 3.2 | possible@3.62 | False | None |
| fall_backward/gmdcsa24_s2_fall_09.mp4 | fall | 1.8 | possible@2.42 | False | None |
| fall_backward/gmdcsa24_s2_fall_10.mp4 | fall | 2.0 | possible@2.61 | False | None |
| fall_backward/gmdcsa24_s2_fall_11.mp4 | fall | 5.9 | possible@5.62, confirmed@10.22 | False | 4.32 |
| fall_backward/gmdcsa24_s2_fall_12.mp4 | fall | 6.9 | - | True | None |
| fall_backward/gmdcsa24_s2_fall_13.mp4 | fall | 2.5 | possible@4.21 | False | None |
| fall_backward/gmdcsa24_s2_fall_14.mp4 | fall | 3.4 | possible@5.02, confirmed@8.22 | False | 4.82 |
| fall_backward/gmdcsa24_s2_fall_25.mp4 | fall | 3.0 | possible@3.81, confirmed@7.02 | False | 4.02 |
| fall_forward/gmdcsa24_s1_fall_08.mp4 | fall | 0.8 | possible@1.44 | False | None |
| fall_forward/gmdcsa24_s1_fall_09.mp4 | fall | 0.7 | possible@2.21 | False | None |
| fall_forward/gmdcsa24_s1_fall_10.mp4 | fall | 0.7 | possible@1.62, dismissed@3.02 | False | None |
| fall_forward/gmdcsa24_s2_fall_03.mp4 | fall | 0.0 | possible@3.22, confirmed@6.4 | False | 6.4 |
| fall_forward/gmdcsa24_s2_fall_07.mp4 | fall | 2.0 | possible@2.82 | False | None |
| fall_forward/gmdcsa24_s2_fall_16.mp4 | fall | 0.8 | possible@1.6 | False | None |
| fall_forward/gmdcsa24_s2_fall_17.mp4 | fall | 2.5 | possible@3.22, confirmed@6.43 | False | 3.93 |
| fall_forward/gmdcsa24_s2_fall_18.mp4 | fall | 9.8 | possible@10.82 | False | None |
| fall_forward/gmdcsa24_s2_fall_19.mp4 | fall | 8.2 | possible@8.82, confirmed@11.82 | False | 3.62 |
| fall_forward/gmdcsa24_s2_fall_20.mp4 | fall | 7.9 | possible@8.61 | False | None |
| fall_forward/gmdcsa24_s2_fall_22.mp4 | fall | 1.3 | possible@2.02, confirmed@5.02 | False | 3.72 |
| fall_sideways/gmdcsa24_s1_fall_01.mp4 | fall | 3.4 | possible@4.22 | False | None |
| fall_sideways/gmdcsa24_s1_fall_02.mp4 | fall | 1.9 | possible@2.42 | False | None |
| fall_sideways/gmdcsa24_s1_fall_03.mp4 | fall | 2.5 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s1_fall_04.mp4 | fall | 2.3 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s1_fall_05.mp4 | fall | 1.8 | possible@2.42, confirmed@5.42 | False | 3.62 |
| fall_sideways/gmdcsa24_s1_fall_06.mp4 | fall | 2.2 | possible@2.61 | False | None |
| fall_sideways/gmdcsa24_s1_fall_07.mp4 | fall | 1.1 | possible@1.62, confirmed@4.62 | False | 3.52 |
| fall_sideways/gmdcsa24_s1_fall_15.mp4 | fall | 1.8 | possible@2.61, confirmed@5.82 | False | 4.02 |
| fall_sideways/gmdcsa24_s1_fall_16.mp4 | fall | 2.8 | possible@3.42 | False | None |
| fall_sideways/gmdcsa24_s2_fall_01.mp4 | fall | 1.4 | possible@2.4 | False | None |
| fall_sideways/gmdcsa24_s2_fall_02.mp4 | fall | 2.7 | possible@3.42, confirmed@8.21 | False | 5.51 |
| fall_sideways/gmdcsa24_s2_fall_05.mp4 | fall | 0.8 | possible@2.21 | False | None |
| fall_sideways/gmdcsa24_s2_fall_15.mp4 | fall | 7.7 | possible@9.22 | False | None |
| fall_sideways/gmdcsa24_s2_fall_21.mp4 | fall | 6.2 | possible@7.01 | False | None |
| fall_sideways/gmdcsa24_s2_fall_23.mp4 | fall | 3.6 | possible@4.4, confirmed@7.41 | False | 3.81 |
| fall_sideways/gmdcsa24_s2_fall_24.mp4 | fall | 3.3 | possible@5.22 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_01.mp4 | none | None | possible@4.83, confirmed@8.02 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_02.mp4 | none | None | possible@4.82 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_03.mp4 | none | None | possible@4.42 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_04.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_03.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_12.mp4 | none | None | possible@7.02 | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_16.mp4 | none | None | possible@3.22, possible@7.82, dismissed@8.83, confirmed@10.83 | False | None |
| normal_office_activity/gmdcsa24_s1_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_06.mp4 | none | None | possible@6.61, confirmed@9.62 | False | None |
| normal_office_activity/gmdcsa24_s1_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_08.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_09.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_10.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_11.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_12.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_13.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_01.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_02.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_04.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_08.mp4 | none | None | possible@7.2, dismissed@10.62 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_09.mp4 | none | None | possible@4.22, dismissed@5.42 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_10.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_13.mp4 | none | None | possible@1.01, dismissed@2.21 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_17.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_18.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_19.mp4 | none | None | possible@9.42 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_20.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_21.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_22.mp4 | none | None | possible@7.62, confirmed@10.62 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_23.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s1_adl_16.mp4 | none | None | possible@1.22, dismissed@2.42 | False | None |
| sitting_standing/gmdcsa24_s2_adl_06.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s2_adl_11.mp4 | none | None | - | False | None |

## asp12_top35: by scenario

| scenario | clips | POSSIBLE | CONFIRMED | missed | false POSSIBLE | false CONFIRMED |
|---|---|---|---|---|---|---|
| fall_backward | 14 | 13 | 4 | 1 | 0 | 0 |
| fall_forward | 11 | 11 | 4 | 0 | 0 | 0 |
| fall_sideways | 16 | 16 | 5 | 0 | 0 | 0 |
| intentional_lying_down | 7 | 0 | 0 | 0 | 6 | 3 |
| normal_office_activity | 29 | 0 | 0 | 0 | 6 | 2 |
| sitting_standing | 3 | 0 | 0 | 0 | 1 | 0 |

### asp12_top35: per clip

| clip | expected | event t (s) | events | missed | latency (s) |
|---|---|---|---|---|---|
| fall_backward/gmdcsa24_s1_fall_11.mp4 | fall | 1.0 | possible@2.21 | False | None |
| fall_backward/gmdcsa24_s1_fall_12.mp4 | fall | 1.9 | possible@3.22 | False | None |
| fall_backward/gmdcsa24_s1_fall_13.mp4 | fall | 0.4 | possible@1.62 | False | None |
| fall_backward/gmdcsa24_s1_fall_14.mp4 | fall | 0.3 | possible@1.81 | False | None |
| fall_backward/gmdcsa24_s2_fall_04.mp4 | fall | 3.3 | possible@5.63, confirmed@8.82 | False | 5.52 |
| fall_backward/gmdcsa24_s2_fall_06.mp4 | fall | 2.1 | possible@3.62 | False | None |
| fall_backward/gmdcsa24_s2_fall_08.mp4 | fall | 3.2 | possible@3.62 | False | None |
| fall_backward/gmdcsa24_s2_fall_09.mp4 | fall | 1.8 | possible@2.42 | False | None |
| fall_backward/gmdcsa24_s2_fall_10.mp4 | fall | 2.0 | possible@2.61 | False | None |
| fall_backward/gmdcsa24_s2_fall_11.mp4 | fall | 5.9 | possible@5.62, confirmed@10.22 | False | 4.32 |
| fall_backward/gmdcsa24_s2_fall_12.mp4 | fall | 6.9 | - | True | None |
| fall_backward/gmdcsa24_s2_fall_13.mp4 | fall | 2.5 | possible@4.21 | False | None |
| fall_backward/gmdcsa24_s2_fall_14.mp4 | fall | 3.4 | possible@5.02, confirmed@8.22 | False | 4.82 |
| fall_backward/gmdcsa24_s2_fall_25.mp4 | fall | 3.0 | possible@3.81, confirmed@7.02 | False | 4.02 |
| fall_forward/gmdcsa24_s1_fall_08.mp4 | fall | 0.8 | possible@1.44 | False | None |
| fall_forward/gmdcsa24_s1_fall_09.mp4 | fall | 0.7 | possible@2.21 | False | None |
| fall_forward/gmdcsa24_s1_fall_10.mp4 | fall | 0.7 | possible@1.62, dismissed@3.02 | False | None |
| fall_forward/gmdcsa24_s2_fall_03.mp4 | fall | 0.0 | possible@3.22, confirmed@6.4 | False | 6.4 |
| fall_forward/gmdcsa24_s2_fall_07.mp4 | fall | 2.0 | possible@2.82 | False | None |
| fall_forward/gmdcsa24_s2_fall_16.mp4 | fall | 0.8 | possible@1.6 | False | None |
| fall_forward/gmdcsa24_s2_fall_17.mp4 | fall | 2.5 | possible@3.22, confirmed@6.43 | False | 3.93 |
| fall_forward/gmdcsa24_s2_fall_18.mp4 | fall | 9.8 | possible@10.82 | False | None |
| fall_forward/gmdcsa24_s2_fall_19.mp4 | fall | 8.2 | possible@8.82, confirmed@11.82 | False | 3.62 |
| fall_forward/gmdcsa24_s2_fall_20.mp4 | fall | 7.9 | possible@8.61 | False | None |
| fall_forward/gmdcsa24_s2_fall_22.mp4 | fall | 1.3 | possible@2.02, confirmed@5.02 | False | 3.72 |
| fall_sideways/gmdcsa24_s1_fall_01.mp4 | fall | 3.4 | possible@4.22 | False | None |
| fall_sideways/gmdcsa24_s1_fall_02.mp4 | fall | 1.9 | possible@2.42 | False | None |
| fall_sideways/gmdcsa24_s1_fall_03.mp4 | fall | 2.5 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s1_fall_04.mp4 | fall | 2.3 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s1_fall_05.mp4 | fall | 1.8 | possible@2.42, confirmed@5.42 | False | 3.62 |
| fall_sideways/gmdcsa24_s1_fall_06.mp4 | fall | 2.2 | possible@2.61 | False | None |
| fall_sideways/gmdcsa24_s1_fall_07.mp4 | fall | 1.1 | possible@1.62, confirmed@4.62 | False | 3.52 |
| fall_sideways/gmdcsa24_s1_fall_15.mp4 | fall | 1.8 | possible@2.61, confirmed@5.82 | False | 4.02 |
| fall_sideways/gmdcsa24_s1_fall_16.mp4 | fall | 2.8 | possible@3.42 | False | None |
| fall_sideways/gmdcsa24_s2_fall_01.mp4 | fall | 1.4 | possible@2.4 | False | None |
| fall_sideways/gmdcsa24_s2_fall_02.mp4 | fall | 2.7 | possible@3.42, confirmed@8.21 | False | 5.51 |
| fall_sideways/gmdcsa24_s2_fall_05.mp4 | fall | 0.8 | possible@2.21 | False | None |
| fall_sideways/gmdcsa24_s2_fall_15.mp4 | fall | 7.7 | possible@9.22 | False | None |
| fall_sideways/gmdcsa24_s2_fall_21.mp4 | fall | 6.2 | possible@7.01 | False | None |
| fall_sideways/gmdcsa24_s2_fall_23.mp4 | fall | 3.6 | possible@4.4, confirmed@7.41 | False | 3.81 |
| fall_sideways/gmdcsa24_s2_fall_24.mp4 | fall | 3.3 | possible@5.22 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_01.mp4 | none | None | possible@4.83, confirmed@8.02 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_02.mp4 | none | None | possible@4.82 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_03.mp4 | none | None | possible@4.42 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_04.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_03.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_12.mp4 | none | None | possible@7.02 | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_16.mp4 | none | None | possible@3.22, possible@7.82, confirmed@8.83, confirmed@10.83 | False | None |
| normal_office_activity/gmdcsa24_s1_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_06.mp4 | none | None | possible@6.61, confirmed@9.62 | False | None |
| normal_office_activity/gmdcsa24_s1_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_08.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_09.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_10.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_11.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_12.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_13.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_01.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_02.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_04.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_08.mp4 | none | None | possible@7.2, dismissed@10.62 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_09.mp4 | none | None | possible@4.22, dismissed@5.42 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_10.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_13.mp4 | none | None | possible@1.01, dismissed@2.21 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_17.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_18.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_19.mp4 | none | None | possible@9.42 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_20.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_21.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_22.mp4 | none | None | possible@7.62, confirmed@10.62 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_23.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s1_adl_16.mp4 | none | None | possible@1.22, dismissed@2.42 | False | None |
| sitting_standing/gmdcsa24_s2_adl_06.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s2_adl_11.mp4 | none | None | - | False | None |

## asp12_top35_floor_off: by scenario

| scenario | clips | POSSIBLE | CONFIRMED | missed | false POSSIBLE | false CONFIRMED |
|---|---|---|---|---|---|---|
| fall_backward | 14 | 12 | 3 | 2 | 0 | 0 |
| fall_forward | 11 | 10 | 3 | 1 | 0 | 0 |
| fall_sideways | 16 | 16 | 5 | 0 | 0 | 0 |
| intentional_lying_down | 7 | 0 | 0 | 0 | 0 | 0 |
| normal_office_activity | 29 | 0 | 0 | 0 | 3 | 0 |
| sitting_standing | 3 | 0 | 0 | 0 | 1 | 0 |

### asp12_top35_floor_off: per clip

| clip | expected | event t (s) | events | missed | latency (s) |
|---|---|---|---|---|---|
| fall_backward/gmdcsa24_s1_fall_11.mp4 | fall | 1.0 | possible@2.21 | False | None |
| fall_backward/gmdcsa24_s1_fall_12.mp4 | fall | 1.9 | possible@3.22 | False | None |
| fall_backward/gmdcsa24_s1_fall_13.mp4 | fall | 0.4 | possible@1.62 | False | None |
| fall_backward/gmdcsa24_s1_fall_14.mp4 | fall | 0.3 | possible@1.81 | False | None |
| fall_backward/gmdcsa24_s2_fall_04.mp4 | fall | 3.3 | possible@5.63, confirmed@8.82 | False | 5.52 |
| fall_backward/gmdcsa24_s2_fall_06.mp4 | fall | 2.1 | possible@3.62 | False | None |
| fall_backward/gmdcsa24_s2_fall_08.mp4 | fall | 3.2 | possible@3.62 | False | None |
| fall_backward/gmdcsa24_s2_fall_09.mp4 | fall | 1.8 | possible@2.42 | False | None |
| fall_backward/gmdcsa24_s2_fall_10.mp4 | fall | 2.0 | possible@2.61 | False | None |
| fall_backward/gmdcsa24_s2_fall_11.mp4 | fall | 5.9 | - | True | None |
| fall_backward/gmdcsa24_s2_fall_12.mp4 | fall | 6.9 | - | True | None |
| fall_backward/gmdcsa24_s2_fall_13.mp4 | fall | 2.5 | possible@4.21 | False | None |
| fall_backward/gmdcsa24_s2_fall_14.mp4 | fall | 3.4 | possible@5.02, confirmed@8.22 | False | 4.82 |
| fall_backward/gmdcsa24_s2_fall_25.mp4 | fall | 3.0 | possible@3.81, confirmed@7.02 | False | 4.02 |
| fall_forward/gmdcsa24_s1_fall_08.mp4 | fall | 0.8 | possible@1.44 | False | None |
| fall_forward/gmdcsa24_s1_fall_09.mp4 | fall | 0.7 | possible@2.21 | False | None |
| fall_forward/gmdcsa24_s1_fall_10.mp4 | fall | 0.7 | possible@1.62, dismissed@3.02 | False | None |
| fall_forward/gmdcsa24_s2_fall_03.mp4 | fall | 0.0 | - | True | None |
| fall_forward/gmdcsa24_s2_fall_07.mp4 | fall | 2.0 | possible@2.82 | False | None |
| fall_forward/gmdcsa24_s2_fall_16.mp4 | fall | 0.8 | possible@1.6 | False | None |
| fall_forward/gmdcsa24_s2_fall_17.mp4 | fall | 2.5 | possible@3.22, confirmed@6.43 | False | 3.93 |
| fall_forward/gmdcsa24_s2_fall_18.mp4 | fall | 9.8 | possible@10.82 | False | None |
| fall_forward/gmdcsa24_s2_fall_19.mp4 | fall | 8.2 | possible@8.82, confirmed@11.82 | False | 3.62 |
| fall_forward/gmdcsa24_s2_fall_20.mp4 | fall | 7.9 | possible@8.61 | False | None |
| fall_forward/gmdcsa24_s2_fall_22.mp4 | fall | 1.3 | possible@2.02, confirmed@5.02 | False | 3.72 |
| fall_sideways/gmdcsa24_s1_fall_01.mp4 | fall | 3.4 | possible@4.22 | False | None |
| fall_sideways/gmdcsa24_s1_fall_02.mp4 | fall | 1.9 | possible@2.42 | False | None |
| fall_sideways/gmdcsa24_s1_fall_03.mp4 | fall | 2.5 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s1_fall_04.mp4 | fall | 2.3 | possible@3.01 | False | None |
| fall_sideways/gmdcsa24_s1_fall_05.mp4 | fall | 1.8 | possible@2.42, confirmed@5.42 | False | 3.62 |
| fall_sideways/gmdcsa24_s1_fall_06.mp4 | fall | 2.2 | possible@2.61 | False | None |
| fall_sideways/gmdcsa24_s1_fall_07.mp4 | fall | 1.1 | possible@1.62, confirmed@4.62 | False | 3.52 |
| fall_sideways/gmdcsa24_s1_fall_15.mp4 | fall | 1.8 | possible@2.61, confirmed@5.82 | False | 4.02 |
| fall_sideways/gmdcsa24_s1_fall_16.mp4 | fall | 2.8 | possible@3.42 | False | None |
| fall_sideways/gmdcsa24_s2_fall_01.mp4 | fall | 1.4 | possible@2.4 | False | None |
| fall_sideways/gmdcsa24_s2_fall_02.mp4 | fall | 2.7 | possible@3.42, confirmed@8.21 | False | 5.51 |
| fall_sideways/gmdcsa24_s2_fall_05.mp4 | fall | 0.8 | possible@2.21 | False | None |
| fall_sideways/gmdcsa24_s2_fall_15.mp4 | fall | 7.7 | possible@9.22 | False | None |
| fall_sideways/gmdcsa24_s2_fall_21.mp4 | fall | 6.2 | possible@7.01 | False | None |
| fall_sideways/gmdcsa24_s2_fall_23.mp4 | fall | 3.6 | possible@4.4, confirmed@7.41 | False | 3.81 |
| fall_sideways/gmdcsa24_s2_fall_24.mp4 | fall | 3.3 | possible@5.22 | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_01.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_02.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_03.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s1_adl_04.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_03.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_12.mp4 | none | None | - | False | None |
| intentional_lying_down/gmdcsa24_s2_adl_16.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_06.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_08.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_09.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_10.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_11.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_12.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_13.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s1_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_01.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_02.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_04.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_05.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_07.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_08.mp4 | none | None | possible@7.2, dismissed@10.62 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_09.mp4 | none | None | possible@4.22, dismissed@5.42 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_10.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_13.mp4 | none | None | possible@1.01, dismissed@2.21 | False | None |
| normal_office_activity/gmdcsa24_s2_adl_14.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_15.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_17.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_18.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_19.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_20.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_21.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_22.mp4 | none | None | - | False | None |
| normal_office_activity/gmdcsa24_s2_adl_23.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s1_adl_16.mp4 | none | None | possible@1.22, dismissed@2.42 | False | None |
| sitting_standing/gmdcsa24_s2_adl_06.mp4 | none | None | - | False | None |
| sitting_standing/gmdcsa24_s2_adl_11.mp4 | none | None | - | False | None |
