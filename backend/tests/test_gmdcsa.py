"""GMDCSA-24 import mapping and event-level metrics (no dataset or model needed)."""
import json

import pytest

from tools import cctv_meta, gmdcsa_eval, gmdcsa_import

HEADER = "File Name,Length (seconds),Time of Recording,Attire,Description, Classes\n"


def _csv(tmp_path, name, lines):
    p = tmp_path / name
    p.write_text(HEADER + "\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_fall_row_with_unquoted_commas_in_the_description(tmp_path):
    p = _csv(tmp_path, "Fall.csv", ["01.mp4,06, Day (Light On),Full T-shirt & Trousers, Falling from sitting on the chair to the ground. Left side Fall. Full body not visible, Falling (SW)[3.4 to 6]; Sitting[0 to 3.4]"])
    row = gmdcsa_import.parse_csv(p)[0]
    assert row["length_s"] == 6.0 and row["time_of_recording"] == "Day (Light On)"
    assert [(s["label"], s["start"], s["end"]) for s in row["segments"]] == [("Falling (SW)", 3.4, 6.0), ("Sitting", 0.0, 3.4)]
    assert row["description"].endswith("Full body not visible")
    plan = gmdcsa_import.plan_clip(1, "Fall", row)
    assert plan["include"] and plan["scenario"] == "fall_sideways" and plan["event_time_s"] == 3.4 and plan["split"] == "tuning"
    assert "from_chair" in plan["tags"] and "partly_visible" in plan["tags"]


def test_label_variants_and_the_unscorable_row_are_handled_not_guessed(tmp_path):
    p = _csv(tmp_path, "Fall.csv", [
        "07.mp4,05,Day,T-shirt,Fall backwards. Missing bracket, Falling (BW[1.0 to 5]; Standing[0 to 1.0]",
        "15.mp4,04,Day (Lights On),T-Shirt & Pant,Falling (FW) on the floor from sitting on the bed, Falling (FW); Sitting[0 to 1.7]"])
    a, b = (gmdcsa_import.plan_clip(4, "Fall", r) for r in gmdcsa_import.parse_csv(p))
    assert a["include"] and a["scenario"] == "fall_backward" and a["event_time_s"] == 1.0 and a["split"] == "independent"
    assert not b["include"] and "no time range" in b["reason"]            # left out and reported, never given an invented fall time


def test_normal_clips_map_by_their_activities(tmp_path):
    p = _csv(tmp_path, "ADL.csv", [
        "01.mp4,08,Day,T,Sitting on the bed to sleeping, Sitting[0 to 1]; Sleeping[2 to 8]",
        "02.mp4,09,Night,T,Walking then reading, Walking[0 to 4]; Reading[4 to 9]",
        "03.mp4,05,Day,T,Sits and stands, Sitting[0 to 2]; Standing[2 to 5]"])
    sc = [gmdcsa_import.plan_clip(3, "ADL", r)["scenario"] for r in gmdcsa_import.parse_csv(p)]
    assert sc == ["intentional_lying_down", "normal_office_activity", "sitting_standing"]


def test_public_dataset_label_needs_no_recording_clock_but_other_kinds_still_do():
    base = {"schema_version": 1, "camera_id": "x", "scenario": "normal_office_activity", "expected_event": "none"}
    assert cctv_meta.validate({**base, "source_kind": "public_dataset"})
    with pytest.raises(cctv_meta.MetaError):
        cctv_meta.validate({**base, "source_kind": "exported_file"})


def _row(expected, ev=None, dur=6.0, dp=False, dc=False, fp=None, fc=None, fpos=0, fconf=0, miss=False):
    return {"expected": expected, "event_time_s": ev, "duration_s": dur, "detected_possible": dp, "detected_confirmed": dc,
            "first_possible_s": fp, "first_confirmed_s": fc, "false_possible": fpos, "false_confirmed": fconf, "missed": miss}


def test_event_metrics_keep_possible_and_confirmed_apart():
    rows = [_row("fall", 2.0, 5.5, dp=True, fp=3.0),                                        # POSSIBLE only (clip too short to confirm)
            _row("fall", 1.0, 9.0, dp=True, dc=True, fp=2.0, fc=5.0),                       # both
            _row("fall", 2.0, 5.5, miss=True),                                              # missed
            _row("none", None, 60.0, fpos=1),                                               # one false POSSIBLE
            _row("none", None, 60.0)]
    p, c = gmdcsa_eval.state_metrics(rows, "possible"), gmdcsa_eval.state_metrics(rows, "confirmed")
    assert (p["TP"], p["FN"], p["false_alerts_total"]) == (2, 1, 1)
    assert p["recall"] == round(2 / 3, 3) and p["precision"] == round(2 / 3, 3)
    assert p["latency_s"]["median"] == 1.0 and p["normal_clips_with_a_false_alert"] == 1 and p["specificity_clip_level"] == 0.5
    assert (c["TP"], c["FN"], c["false_alerts_total"]) == (1, 2, 0) and c["precision"] == 1.0
    assert c["reachable"]["fall_clips"] == 1 and c["reachable"]["recall"] == 1.0           # only the 9 s clip leaves >= 4 s after onset (5.5 - 2.0 = 3.5)
    assert c["recall"] != p["recall"]                                                      # a POSSIBLE is never counted as a confirmed fall


def test_label_with_a_missing_to_is_read_as_written_and_flagged(tmp_path):
    p = _csv(tmp_path, "Fall.csv", ["09.mp4,06,Day (Lights On),Full Shirt & Pant,Falling backward on the bed from sitting on the bed, Falling (BW)[2.3 6]; Sitting[0 to 2]"])
    row = gmdcsa_import.parse_csv(p)[0]
    fall = row["segments"][0]
    assert (fall["start"], fall["end"]) == (2.3, 6.0) and "label_typo" in fall and "label_typo" not in row["segments"][1]
    assert gmdcsa_import.plan_clip(4, "Fall", row)["event_time_s"] == 2.3
