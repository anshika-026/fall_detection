"""Event-level metrics and error analysis for GMDCSA-24 runs made by tools.cctv_validate (the engine is not touched here).

  python -m tools.gmdcsa_eval --report ..\\validation\\results\\gmdcsa24_baseline_tuning.json --out ..\\validation\\results\\gmdcsa24_baseline_tuning_metrics

Definitions (fixed before any result was looked at):
  evaluation unit   one CLIP is one event opportunity. A fall clip contains one labelled fall; a normal clip contains none.
                    Frames are never counted as events.
  fall event        scored for the clip's `event_time_s` = onset of the dataset's "Falling" segment.
  detected (S)      state S (POSSIBLE or CONFIRMED) first appears in [event - 2 s, event + tolerance + 10 s] (tools/cctv_meta.py).
  TP / FN           fall clips detected / not detected in that state.
  false alert (S)   every alert of state S outside the window in a fall clip, plus every alert of state S in a normal clip.
                    Counted per alert event (an engine that flickers can raise several in one clip).
  precision(S)      TP / (TP + false alerts(S)).  recall(S) = TP / fall clips.  F1 = 2PR/(P+R).
  normal clip TN    a normal clip with no alert of state S;  specificity(S) = TN / normal clips (clip level).
  latency(S)        first S time - event_time_s, in seconds. NEGATIVE = the alert came before the labelled onset (reported, not hidden).
  CONFIRMED-reachable   a fall clip with at least REACH_S = 4.0 s of footage after the labelled onset (about 1 s to be seen lying + the
                    3 s stay-down confirmation). CONFIRMED recall is shown for all fall clips AND for these only, because short clips
                    end before CONFIRMED is possible; that limit belongs to the clip, not to the detector.
A POSSIBLE alert is NEVER counted as a confirmed fall.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import cctv_meta  # noqa: E402

REACH_S = 4.0


def _div(a, b):
    return None if not b else a / b


def f1(p, r):
    return None if p is None or r is None or (p + r) == 0 else 2 * p * r / (p + r)


def rnd(x, n=3):
    return None if x is None else round(x, n)


def state_metrics(rows: list[dict], state: str) -> dict:
    """Event-level metrics for one state ('possible' | 'confirmed') over scored clips."""
    det_key, first_key = f"detected_{state}", f"first_{state}_s"
    falls = [r for r in rows if r["expected"] == "fall"]
    normals = [r for r in rows if r["expected"] == "none"]
    tp = sum(bool(r[det_key]) for r in falls)
    fp_fall_clips = sum(r[f"false_{state}"] for r in falls)
    fp_normal = sum(r[f"false_{state}"] for r in normals)
    fp = fp_fall_clips + fp_normal
    lat = [r[first_key] - r["event_time_s"] for r in falls if r[det_key] and r[first_key] is not None]
    normal_min = sum(r["duration_s"] for r in normals) / 60.0
    tn = sum(r[f"false_{state}"] == 0 for r in normals)
    p, rec = _div(tp, tp + fp), _div(tp, len(falls))
    out = {"fall_clips": len(falls), "TP": tp, "FN": len(falls) - tp, "false_alerts_total": fp,
           "false_alerts_in_normal_clips": fp_normal, "false_alerts_in_fall_clips": fp_fall_clips,
           "normal_clips": len(normals), "normal_clips_with_a_false_alert": len(normals) - tn, "TN_clips": tn,
           "recall": rnd(rec), "precision": rnd(p), "f1": rnd(f1(p, rec)), "specificity_clip_level": rnd(_div(tn, len(normals))),
           "false_alerts_per_normal_clip": rnd(_div(fp_normal, len(normals))),
           "false_alerts_per_normal_minute": rnd(_div(fp_normal, normal_min)), "normal_minutes": rnd(normal_min, 2),
           "latency_s": {"n": len(lat), "median": rnd(statistics.median(lat), 2) if lat else None,
                         "min": rnd(min(lat), 2) if lat else None, "max": rnd(max(lat), 2) if lat else None,
                         "early_alerts_before_onset": sum(x < 0 for x in lat)}}
    if state == "confirmed":
        reach = [r for r in falls if (r["duration_s"] - r["event_time_s"]) >= REACH_S]
        tp_r = sum(bool(r[det_key]) for r in reach)
        out["reachable"] = {"definition": f">= {REACH_S} s of footage after the labelled onset", "fall_clips": len(reach), "TP": tp_r,
                            "recall": rnd(_div(tp_r, len(reach)))}
    return out


def strata(rows: list[dict], key_fn) -> dict:
    groups = defaultdict(list)
    for r in rows:
        for k in key_fn(r):
            groups[k].append(r)
    out = {}
    for k, rs in sorted(groups.items()):
        falls = [r for r in rs if r["expected"] == "fall"]
        normals = [r for r in rs if r["expected"] == "none"]
        out[k] = {"fall_clips": len(falls), "possible_detected": sum(bool(r["detected_possible"]) for r in falls),
                  "confirmed_detected": sum(bool(r["detected_confirmed"]) for r in falls),
                  "normal_clips": len(normals), "normal_with_false_possible": sum(r["false_possible"] > 0 for r in normals),
                  "normal_with_false_confirmed": sum(r["false_confirmed"] > 0 for r in normals)}
    return out


def attach_meta(report: dict) -> list[dict]:
    root = Path(report["footage_root"])
    rows = []
    for r in report["config_rows"]:
        m = json.loads(cctv_meta.meta_path(root / r["clip"]).read_text(encoding="utf-8"))
        d = m.get("dataset", {})
        rows.append({**r, "subject": d.get("subject"), "tags": d.get("tags", []), "direction": d.get("direction"),
                     "category": d.get("category"), "notes": m.get("notes", "")})
    return rows


def analyse_config(report: dict, cfg: dict) -> dict:
    rep = dict(report, config_rows=cfg["clips"])
    rows = attach_meta(rep)
    return {"name": cfg["name"], "detector_conf": cfg["detector_conf"], "engine_overrides": cfg["engine_overrides"],
            "possible": state_metrics(rows, "possible"), "confirmed": state_metrics(rows, "confirmed"),
            "by_scenario": strata(rows, lambda r: [r["scenario"]]),
            "by_direction": strata([r for r in rows if r["expected"] == "fall"], lambda r: [r["direction"]]),
            "by_subject": strata(rows, lambda r: [f"subject {r['subject']}"]),
            "by_tag": strata(rows, lambda r: r["tags"]),
            "missed_falls_possible": [{k: r[k] for k in ("clip", "event_time_s", "duration_s", "events", "frames_with_person", "analysed_frames",
                                                         "unique_track_ids", "tags", "direction", "notes")} for r in rows
                                      if r["expected"] == "fall" and r["missed"]],
            "false_alert_clips": [{k: r[k] for k in ("clip", "scenario", "duration_s", "events", "tags", "notes")} for r in rows
                                  if (r["expected"] == "none" and (r["false_possible"] or r["false_confirmed"]))
                                  or (r["expected"] == "fall" and (r["false_possible"] or r["false_confirmed"]))]}


def pct(x):
    return "-" if x is None else f"{100 * x:.1f}%"


def to_markdown(report: dict, results: list[dict]) -> str:
    L = [f"# GMDCSA-24 event-level metrics: {report['run']}", "",
         f"Footage role: **{report.get('footage_role')}**. Clips scored: {report['clips_scored']}. Detector: {report['weights']} at {report['analysis_fps']} analysed fps. "
         f"Scoring window: event -{report['scoring_window']['pre_s']} s to event + tolerance + {report['scoring_window']['post_s']} s.", "",
         "**PUBLIC DATASET (not our cameras).** Home-style scenes, 4 subjects in total. These numbers describe how the rules behave on this dataset only; "
         "they are not validation on the office CCTV and not evidence of real-world safety.", ""]
    if report.get("footage_role") == "independent":
        L += ["**Independent evaluation covers only two held-out subjects (Subjects 3 and 4); the dataset has four subjects in total.**", ""]
    elif report.get("footage_role") == "tuning":
        L += ["**TUNING set (Subjects 1 and 2): not independent evidence.**", ""]
    L += ["Evaluation unit: one clip = one event opportunity; frames are never counted as events. POSSIBLE (amber) and CONFIRMED (red) are reported separately; "
          "a POSSIBLE alert is never counted as a confirmed fall. Definitions are in the header of `tools/gmdcsa_eval.py`.", ""]
    for state in ("possible", "confirmed"):
        L += [f"## {state.upper()} alerts", "",
              "| config | fall clips | TP | FN | recall | false alerts (normal clips) | false alerts (fall clips) | precision | F1 | normal clips with a false alert | specificity (clip) | false alerts / normal clip | false alerts / normal min | latency median s [min..max] (n) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for c in results:
            m = c[state]
            lt = m["latency_s"]
            L.append(f"| {c['name']} | {m['fall_clips']} | {m['TP']} | {m['FN']} | {pct(m['recall'])} | {m['false_alerts_in_normal_clips']} | {m['false_alerts_in_fall_clips']} | "
                     f"{pct(m['precision'])} | {pct(m['f1'])} | {m['normal_clips_with_a_false_alert']}/{m['normal_clips']} | {pct(m['specificity_clip_level'])} | "
                     f"{m['false_alerts_per_normal_clip']} | {m['false_alerts_per_normal_minute']} | {lt['median']} [{lt['min']}..{lt['max']}] ({lt['n']}) |")
        if state == "confirmed":
            L += ["", "CONFIRMED needs the person to stay down about 3 s after the fall. Many dataset clips end before that:", "",
                  "| config | CONFIRMED recall, all fall clips | CONFIRMED-reachable clips (>= 4.0 s after onset) | TP among them | recall among them |", "|---|---|---|---|---|"]
            for c in results:
                m = c["confirmed"]
                L.append(f"| {c['name']} | {pct(m['recall'])} | {m['reachable']['fall_clips']} | {m['reachable']['TP']} | {pct(m['reachable']['recall'])} |")
        L.append("")
    best = results[0]
    for title, key in (("by scenario", "by_scenario"), ("by fall direction", "by_direction"), ("by subject", "by_subject"), ("by tag", "by_tag")):
        L += [f"## {best['name']}: {title}", "", "| group | fall clips | POSSIBLE detected | CONFIRMED detected | normal clips | normal with false POSSIBLE | normal with false CONFIRMED |", "|---|---|---|---|---|---|---|"]
        for k, b in best[key].items():
            L.append(f"| {k} | {b['fall_clips']} | {b['possible_detected']} | {b['confirmed_detected']} | {b['normal_clips']} | {b['normal_with_false_possible']} | {b['normal_with_false_confirmed']} |")
        L.append("")
    for c in results:
        L += [f"## {c['name']}: missed falls (no POSSIBLE in the window)", ""]
        if not c["missed_falls_possible"]:
            L.append("none")
        for m in c["missed_falls_possible"]:
            L.append(f"- `{m['clip']}` onset {m['event_time_s']} s of {m['duration_s']} s, people seen in {m['frames_with_person']}/{m['analysed_frames']} analysed frames, "
                     f"{m['unique_track_ids']} track id(s), events {m['events'] or 'none'}, tags {m['tags']}. {m['notes'][:160]}")
        L += ["", f"## {c['name']}: clips with false alerts", ""]
        if not c["false_alert_clips"]:
            L.append("none")
        for m in c["false_alert_clips"]:
            L.append(f"- `{m['clip']}` ({m['scenario']}, {m['duration_s']} s): events {m['events']}, tags {m['tags']}. {m['notes'][:160]}")
        L.append("")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", type=Path, required=True, help="JSON written by tools.cctv_validate")
    ap.add_argument("--out", type=Path, required=True, help="path stem: writes <stem>.json and <stem>.md (never overwrites)")
    ap.add_argument("--configs", default="", help="comma list of config names to include (default: all in the report)")
    a = ap.parse_args()
    report = json.loads(a.report.read_text(encoding="utf-8"))
    want = [c for c in a.configs.split(",") if c]
    cfgs = [c for c in report["configs"] if not want or c["name"] in want]
    if not cfgs:
        raise SystemExit("no matching config in the report")
    js, md = a.out.with_suffix(".json"), a.out.with_suffix(".md")
    if js.exists() or md.exists():
        raise SystemExit(f"{js.name} / {md.name} already exist: not overwriting")
    results = [analyse_config(report, c) for c in cfgs]
    js.write_text(json.dumps({"source_report": str(a.report), "run": report["run"], "footage_role": report.get("footage_role"),
                              "reach_s": REACH_S, "results": results}, indent=2), encoding="utf-8")
    text = to_markdown(report, results)
    md.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
