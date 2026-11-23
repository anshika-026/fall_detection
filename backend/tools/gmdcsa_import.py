"""Import the GMDCSA-24 fall dataset into the project's validation layout WITHOUT copying or changing the originals.

  python -m tools.gmdcsa_import --dataset C:\\Users\\lenovo\\Datasets\\GMDCSA24 --dry-run
  python -m tools.gmdcsa_import --dataset C:\\Users\\lenovo\\Datasets\\GMDCSA24

What it does (and nothing else):
  * reads the dataset's own CSV annotations (ADL.csv / Fall.csv per subject). The CSVs and videos are never edited;
    their SHA-256 is recorded so a later run can prove they did not change (--verify);
  * writes one <clip>.meta.json per clip, in the format tools.cctv_meta already scores, with source_kind = public_dataset;
  * puts each video in validation/tuning/<scenario>/ or validation/independent/<scenario>/ as a HARD LINK (no second copy of the
    1.1 GB; falls back to a copy only if linking is impossible, and says so);
  * writes validation/datasets/gmdcsa24/manifest.json: the split, every label mapping, every clip left out and why.

Split: by SUBJECT, fixed, no randomness. Subjects 1-2 = tuning, Subjects 3-4 = independent. Only four subjects exist, so the
independent evaluation covers two held-out people.

Ground truth is the dataset authors' CSV, never the detector. Mapping rules (fixed before any result was seen):
  fall clips   event_time_s = START of the dataset's "Falling" segment (the onset of the fall, not the landing);
               scenario from the direction in the label: (SW) sideways, (FW) forward, (BW) backward. A fall clip whose label
               has no time range cannot be scored and is listed, not guessed.
  normal clips scenario intentional_lying_down if the clip contains "Sleeping", normal_office_activity if it contains any of
               Walking/Exercising/Reading/Writing/Eating/Drinking, otherwise sitting_standing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import cctv_meta  # noqa: E402

SPLIT = {1: "tuning", 2: "tuning", 3: "independent", 4: "independent"}
DIRECTION = {"SW": "fall_sideways", "FW": "fall_forward", "BW": "fall_backward"}
ACTIVE_ADL = ("Walking", "Exercising", "Reading", "Writing", "Eating", "Drinking")
SEGMENT = re.compile(r"([A-Za-z][A-Za-z ()]*?)\s*\[\s*([\d.]+)\s*(?:to)?\s*([\d.]+)\s*\]")   # "to" optional: one label is typed [2.3 6]
FALL_LABEL = re.compile(r"^Fall(?:ing)?\b", re.I)
NAME = "gmdcsa24"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_csv(path: Path) -> list[dict]:
    """Rows of one annotation file. The description contains unquoted commas, so only the first four fields are split off."""
    rows = []
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(",", 4)
        if len(parts) < 5:
            rows.append({"file": parts[0].strip(), "parse_error": "fewer than 5 fields", "raw": line})
            continue
        name, length, when, attire, rest = (x.strip() for x in parts)
        segs = [{"label": m.group(1).strip(), "start": float(m.group(2)), "end": float(m.group(3)),
                 **({"label_typo": "the word 'to' is missing in the dataset label; range read as written"} if " to " not in m.group(0).lower() else {})}
                for m in SEGMENT.finditer(rest)]
        first = SEGMENT.search(rest)
        desc = rest[:first.start()].rstrip(" ,;") if first else rest
        try:
            length_s = float(length)
        except ValueError:
            length_s = None
        rows.append({"file": name, "length_s": length_s, "time_of_recording": when, "attire": attire, "description": desc,
                     "segments": segs, "raw": line})
    return rows


def tags_of(desc: str, when: str, partial_hint: str) -> list[str]:
    d = (desc + " " + partial_hint).lower()
    t = []
    for key, tag in (("chair", "from_chair"), ("bed", "bed"), ("sofa", "sofa"), ("not visible", "partly_visible"),
                     ("left", "left_side"), ("right", "right_side"), ("floor", "floor")):
        if key in d:
            t.append(tag)
    w = when.lower()
    t.append("night" if "night" in w else "lights_off" if "off" in w else "day")
    return t


def plan_clip(subject: int, kind: str, row: dict) -> dict:
    """-> {'include': bool, 'reason': str, 'scenario', 'event_time_s', ...} for one CSV row."""
    base = {"subject": subject, "category": kind, "file": row["file"], "split": SPLIT[subject]}
    if row.get("parse_error"):
        return {**base, "include": False, "reason": f"label not parseable: {row['parse_error']}"}
    segs = row["segments"]
    tags = tags_of(row["description"], row["time_of_recording"], "")
    base.update({"description": row["description"], "classes": segs, "time_of_recording": row["time_of_recording"], "attire": row["attire"],
                 "csv_length_s": row["length_s"], "tags": tags})
    if kind == "Fall":
        falls = [s for s in segs if FALL_LABEL.match(s["label"])]
        direction = re.search(r"\((SW|FW|BW)", row["raw"])
        if not falls:
            return {**base, "include": False, "reason": "fall clip whose label gives no time range for the fall: the fall time cannot be taken from the dataset, so it is not scored (not guessed)"}
        if not direction:
            return {**base, "include": False, "reason": "fall direction (SW/FW/BW) missing in the label"}
        return {**base, "include": True, "reason": "", "scenario": DIRECTION[direction.group(1)], "expected_event": "fall",
                "event_time_s": falls[0]["start"], "direction": direction.group(1)}
    labels = {s["label"].lower() for s in segs}
    if not segs:
        return {**base, "include": False, "reason": "normal clip with no activity segments in the label"}
    if "sleeping" in labels:
        sc = "intentional_lying_down"
    elif any(a.lower() in labels for a in ACTIVE_ADL):
        sc = "normal_office_activity"
    else:
        sc = "sitting_standing"
    return {**base, "include": True, "reason": "", "scenario": sc, "expected_event": "none", "event_time_s": None}


def collect(dataset: Path) -> list[dict]:
    plans = []
    for s in sorted(SPLIT):
        sub = dataset / f"Subject {s}"
        for kind in ("Fall", "ADL"):
            csv_path = sub / f"{kind}.csv"
            if not csv_path.is_file():
                raise SystemExit(f"missing {csv_path}")
            rows = parse_csv(csv_path)
            for r in rows:
                p = plan_clip(s, kind, r)
                video = sub / kind / r["file"]
                p["source"] = str(video)
                if p["include"] and not video.is_file():
                    p.update(include=False, reason="video file listed in the CSV is not in the dataset folder")
                plans.append(p)
            listed = {r["file"] for r in rows}
            for v in sorted((sub / kind).glob("*.mp4")):
                if v.name not in listed:
                    plans.append({"subject": s, "category": kind, "file": v.name, "split": SPLIT[s], "include": False,
                                  "reason": "video present but not listed in the CSV: no ground truth", "source": str(v)})
    return plans


def dataset_commit(dataset: Path) -> str | None:
    rec = dataset.parent / f"{dataset.name}_download.json"      # written by the per-file downloader (no .git folder in that case)
    if rec.is_file():
        try:
            return json.loads(rec.read_text(encoding="utf-8")).get("commit")
        except ValueError:
            pass
    try:
        return subprocess.run(["git", "-C", str(dataset), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20).stdout.strip() or None
    except Exception:
        return None


def link_or_copy(src: Path, dst: Path) -> str:
    if dst.exists():
        return "exists"
    try:
        os.link(src, dst)
        return "hardlink"
    except OSError:
        shutil.copy2(src, dst)
        return "copy"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--validation", type=Path, default=ROOT.parent / "validation")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true", help="re-hash the originals and compare with the recorded inventory, then exit")
    a = ap.parse_args()
    out_dir = a.validation / "datasets" / NAME
    manifest_path = out_dir / "manifest.json"

    if a.verify:
        inv = json.loads(manifest_path.read_text(encoding="utf-8"))["inventory"]
        bad = [k for k, h in inv.items() if not (a.dataset / k).is_file() or sha256(a.dataset / k) != h]
        print(f"{len(inv)} original files checked; {len(bad)} changed or missing")
        for k in bad:
            print("  CHANGED:", k)
        raise SystemExit(1 if bad else 0)

    plans = collect(a.dataset)
    inc = [p for p in plans if p["include"]]
    exc = [p for p in plans if not p["include"]]
    print(f"{len(plans)} clips in the dataset: {len(inc)} included, {len(exc)} left out")
    for p in exc:
        print(f"  LEFT OUT  Subject {p['subject']}/{p['category']}/{p['file']}: {p['reason']}")
    tab: dict[tuple, int] = {}
    for p in inc:
        k = (p["split"], p["expected_event"], p["scenario"])
        tab[k] = tab.get(k, 0) + 1
    for k in sorted(tab):
        print(f"  {k[0]:<12} {k[1]:<5} {k[2]:<24} {tab[k]}")
    if a.dry_run:
        print("dry run: nothing written")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    if manifest_path.exists():
        raise SystemExit(f"{manifest_path} already exists: not overwriting")
    inventory, how = {}, {}
    for s in sorted(SPLIT):
        for f in [a.dataset / f"Subject {s}" / "Fall.csv", a.dataset / f"Subject {s}" / "ADL.csv"]:
            inventory[str(f.relative_to(a.dataset)).replace("\\", "/")] = sha256(f)
    for p in plans:
        v = Path(p["source"])
        if v.is_file():
            inventory[str(v.relative_to(a.dataset)).replace("\\", "/")] = sha256(v)
    for p in inc:
        clip_name = f"{NAME}_s{p['subject']}_{p['category'].lower()}_{Path(p['file']).stem}.mp4"
        folder = a.validation / p["split"] / p["scenario"]
        folder.mkdir(parents=True, exist_ok=True)
        dst = folder / clip_name
        how[p["split"] + "/" + clip_name] = link_or_copy(Path(p["source"]), dst)
        meta = {"schema_version": cctv_meta.SCHEMA_VERSION, "camera_id": f"{NAME}-subject{p['subject']}", "source_kind": "public_dataset",
                "scenario": p["scenario"], "expected_event": p["expected_event"], "event_time_tolerance_s": 2.0,
                "annotator": "GMDCSA-24 dataset authors (their CSV; not the detector)",
                "notes": f"{p['description']} | classes: " + "; ".join(f"{s['label']}[{s['start']} to {s['end']}]" for s in p["classes"]),
                "dataset": {"name": "GMDCSA-24", "subject": p["subject"], "category": p["category"], "file": p["file"],
                            "time_of_recording": p["time_of_recording"], "attire": p["attire"], "tags": p["tags"], "split": p["split"]}}
        if p["expected_event"] == "fall":
            meta["event_time_s"] = p["event_time_s"]
            meta["dataset"]["direction"] = p["direction"]
        cctv_meta.validate(meta, p["scenario"])
        cctv_meta.meta_path(dst).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    manifest = {"dataset": "GMDCSA-24", "source_repo": "https://github.com/ekramalam/GMDCSA24-A-Dataset-for-Human-Fall-Detection-in-Videos",
                "citation_doi": "10.5281/zenodo.12921216", "dataset_commit": dataset_commit(a.dataset), "dataset_folder": str(a.dataset),
                "split_rule": "by subject, fixed, no randomness: Subjects 1-2 tuning, Subjects 3-4 independent (only 4 subjects exist; independent = 2 held-out people)",
                "split": {str(k): v for k, v in SPLIT.items()}, "mapping_rules": __doc__.split("Ground truth is")[1],
                "counts": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in sorted(tab.items())}, "included": len(inc), "left_out": exc,
                "placement": how, "inventory": inventory, "clips": [{k: v for k, v in p.items() if k != "raw"} for p in plans]}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"written: {manifest_path}  ({sum(1 for h in how.values() if h == 'hardlink')} hard links, {sum(1 for h in how.values() if h == 'copy')} copies)")


if __name__ == "__main__":
    main()
