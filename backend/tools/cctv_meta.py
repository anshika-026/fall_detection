"""Ground-truth metadata for recorded validation footage, and the scoring rules.

Ground truth is written BY A PERSON (who staged / watched the clip), never produced by the detector.
One `<clip>.meta.json` sits beside each clip in validation/footage/<scenario>/ :

  {
    "schema_version": 1,
    "camera_id": "office-1",
    "source_kind": "exported_file",               # optional: exported_file | rtsp_recording | file_test | simulator
    "recording_start": "2026-12-01T10:15:00Z",   # ISO-8601; a time zone offset (+05:30) is accepted and compared in UTC
    "recording_end":   "2026-12-01T10:16:10Z",
    "scenario": "fall_from_chair",                # one of SCENARIOS
    "expected_event": "fall",                     # "fall" | "none" (must agree with the scenario)
    "event_time_s": 31.5,                         # seconds from the START OF THE CLIP when the person hits the floor (fall only)
    "event_time_tolerance_s": 2.0,                # how unsure that timestamp is
    "expected_recovery": false,                   # optional, recovery_after_fall: the person gets up
    "annotator": "initials",
    "notes": ""
  }

Commands:
  python -m tools.cctv_meta new <clip> --scenario fall_standing --camera-id office-1    write a template (event time left blank)
  python -m tools.cctv_meta check <footage_dir>                                          validate every clip's metadata
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = 1
VIDEO_EXT = (".mkv", ".mp4", ".avi", ".mov")
# Where the footage came from. Optional in the metadata (older labels have none and are reported as "unspecified").
#   exported_file   a file exported by the camera owner / a recorder (NOT recorded by cctv_record): FILE / EXPORTED FOOTAGE
#   rtsp_recording  recorded by cctv_record from a live RTSP camera
#   file_test       a recording made by cctv_record from a local file (tool test only)
#   simulator       made from the localhost RTSP simulator (tool test only)
#   public_dataset  a clip from a public research dataset (e.g. GMDCSA-24): no wall-clock recording time exists, so recording_start/end are optional
SOURCE_KINDS = ("exported_file", "rtsp_recording", "file_test", "simulator", "public_dataset")
_KIND_FROM_SIDECAR = {"rtsp": "rtsp_recording", "file": "file_test", "exported_file": "exported_file", "rtsp_recording": "rtsp_recording",
                      "file_test": "file_test", "simulator": "simulator"}

# scenario folder -> expected event type
SCENARIOS = {
    "normal_office_activity": "none",
    "fall_standing": "fall",          # staged fall from standing
    "fall_from_chair": "fall",
    "fall_forward": "fall",
    "fall_backward": "fall",
    "fall_sideways": "fall",
    "sitting_standing": "none",
    "bending_down": "none",
    "intentional_lying_down": "none",
    "recovery_after_fall": "fall",    # fall, then the person gets up
}

# A detection counts for a staged fall when POSSIBLE/CONFIRMED appears inside
# [event_time - PRE_S, event_time + tolerance + POST_S]. Stated up-front, fixed before looking at results.
PRE_S = 2.0
POST_S = 10.0


class MetaError(ValueError):
    pass


def meta_path(clip: Path) -> Path:
    return clip.with_suffix("").with_suffix(".meta.json") if clip.suffix in VIDEO_EXT else clip.with_name(clip.name + ".meta.json")


def _ts(value, field: str) -> datetime:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise MetaError(f"'{field}' is not an ISO-8601 time: {value!r}") from None


def validate(meta: dict, folder_scenario: str | None = None) -> dict:
    """Returns the metadata, or raises MetaError saying what is wrong. Never fills in ground truth."""
    if not isinstance(meta, dict):
        raise MetaError("metadata must be a JSON object")
    if meta.get("schema_version") != SCHEMA_VERSION:
        raise MetaError(f"schema_version must be {SCHEMA_VERSION}")
    public = meta.get("source_kind") == "public_dataset"      # a public dataset has no recording clock: do not invent one
    for k in ("camera_id", "recording_start", "recording_end", "scenario", "expected_event"):
        if public and k in ("recording_start", "recording_end"):
            continue
        if meta.get(k) in (None, ""):
            raise MetaError(f"'{k}' is required")
    sc = meta["scenario"]
    if sc not in SCENARIOS:
        raise MetaError(f"unknown scenario '{sc}' (allowed: {', '.join(SCENARIOS)})")
    if folder_scenario and folder_scenario != sc:
        raise MetaError(f"scenario '{sc}' does not match the folder '{folder_scenario}'")
    if meta["expected_event"] != SCENARIOS[sc]:
        raise MetaError(f"scenario '{sc}' expects expected_event '{SCENARIOS[sc]}', not '{meta['expected_event']}'")
    if not (public and not meta.get("recording_start") and not meta.get("recording_end")) \
            and _ts(meta["recording_end"], "recording_end") <= _ts(meta["recording_start"], "recording_start"):
        raise MetaError("recording_end must be after recording_start")
    if "source_kind" in meta and meta["source_kind"] not in SOURCE_KINDS:
        raise MetaError(f"unknown source_kind '{meta['source_kind']}' (allowed: {', '.join(SOURCE_KINDS)})")
    if meta["expected_event"] == "fall":
        t = meta.get("event_time_s")
        if not isinstance(t, (int, float)) or isinstance(t, bool) or t < 0:
            raise MetaError("'event_time_s' (seconds from the start of the clip) is required for a fall")
        tol = meta.get("event_time_tolerance_s", 2.0)
        if not isinstance(tol, (int, float)) or tol < 0:
            raise MetaError("'event_time_tolerance_s' must be >= 0")
    return meta


def load_clip(clip: Path, folder_scenario: str | None = None) -> dict:
    p = meta_path(clip)
    if not p.exists():
        raise MetaError(f"no metadata file {p.name} (ground truth must be supplied by a person)")
    try:
        meta = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        raise MetaError(f"{p.name}: not valid JSON ({e})") from None
    return validate(meta, folder_scenario)


def find_clips(footage: Path) -> list[Path]:
    return sorted(p for sc in SCENARIOS if (footage / sc).is_dir() for p in (footage / sc).iterdir() if p.suffix.lower() in VIDEO_EXT)


def ignored_files(footage: Path) -> list[Path]:
    """Files in the scenario folders that the runner will NOT use (not a supported clip, not a label or sidecar): silently
    skipping them would hide footage the owner thinks is being validated."""
    quiet = (".json", ".gitkeep", ".txt", ".md")
    return sorted(p for sc in SCENARIOS if (footage / sc).is_dir() for p in (footage / sc).iterdir()
                  if p.is_file() and p.suffix.lower() not in VIDEO_EXT and p.suffix.lower() not in quiet and p.name != ".gitkeep")


# ----------------------------------------------------------------------------------------- scoring
@dataclass
class ClipScore:
    expected: str
    detected_possible: bool = False
    detected_confirmed: bool = False
    first_possible_s: float | None = None          # seconds from clip start
    first_confirmed_s: float | None = None
    confirm_latency_s: float | None = None         # first in-window CONFIRMED minus event_time_s
    false_possible: int = 0                        # POSSIBLE outside the fall window (or any, in a 'none' clip)
    false_confirmed: int = 0
    missed: bool = False                           # fall clip with no POSSIBLE inside the window


def score_clip(meta: dict, events: list[tuple[str, float]]) -> ClipScore:
    """events: [(kind, seconds_from_clip_start)] from the engine. Ground truth only from `meta`."""
    s = ClipScore(expected=meta["expected_event"])
    if meta["expected_event"] == "none":
        s.false_possible = sum(k == "possible" for k, _ in events)
        s.false_confirmed = sum(k == "confirmed" for k, _ in events)
        return s
    t0 = float(meta["event_time_s"])
    lo, hi = t0 - PRE_S, t0 + float(meta.get("event_time_tolerance_s", 2.0)) + POST_S
    for kind, ts in events:
        inside = lo <= ts <= hi
        if kind == "possible":
            if inside:
                s.detected_possible = True
                s.first_possible_s = ts if s.first_possible_s is None else s.first_possible_s
            else:
                s.false_possible += 1
        elif kind == "confirmed":
            if inside:
                s.detected_confirmed = True
                if s.first_confirmed_s is None:
                    s.first_confirmed_s = ts
                    s.confirm_latency_s = round(ts - t0, 2)
            else:
                s.false_confirmed += 1
    s.missed = not s.detected_possible
    return s


# ----------------------------------------------------------------------------------------- CLI
def _new(clip: Path, scenario: str, camera_id: str, annotator: str, source_kind: str | None = None) -> Path:
    if scenario not in SCENARIOS:
        raise SystemExit(f"unknown scenario; choose from {', '.join(SCENARIOS)}")
    if not clip.is_file():
        raise SystemExit(f"{clip} does not exist (the path is relative to where you run the command; from backend/ use ../validation/independent/<scenario>/<clip>)")
    if clip.suffix.lower() not in VIDEO_EXT:
        raise SystemExit(f"{clip.name}: not a video file ({', '.join(VIDEO_EXT)})")
    p = meta_path(clip)
    if p.exists():
        raise SystemExit(f"{p} already exists: not overwriting")
    exp = SCENARIOS[scenario]
    start, end = "FILL-IN (UTC, e.g. 2026-12-01T10:15:00Z)", "FILL-IN"
    side = clip.with_suffix(".json")                       # the recorder's sidecar: recording FACTS (times), not ground truth
    kind = source_kind
    if side.exists():
        try:
            sd = json.loads(side.read_text(encoding="utf-8"))
            start, end = sd.get("segment_start_utc", start), sd.get("segment_end_utc", end)
            kind = kind or _KIND_FROM_SIDECAR.get(str(sd.get("source_kind")))
        except ValueError:
            pass
    if source_kind and source_kind not in SOURCE_KINDS:
        raise SystemExit(f"unknown source kind; choose from {', '.join(SOURCE_KINDS)}")
    # No sidecar and no explicit kind: a video the recorder did not make is an exported / file footage by definition.
    kind = kind or "exported_file"
    tpl = {"schema_version": SCHEMA_VERSION, "camera_id": camera_id, "source_kind": kind, "recording_start": start,
           "recording_end": end, "scenario": scenario, "expected_event": exp, "annotator": annotator, "notes": ""}
    if exp == "fall":
        tpl.update({"event_time_s": None, "event_time_tolerance_s": 2.0})
        if scenario == "recovery_after_fall":
            tpl["expected_recovery"] = True
    p.write_text(json.dumps(tpl, indent=2), encoding="utf-8")
    return p


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("clip", type=Path)
    n.add_argument("--scenario", required=True)
    n.add_argument("--camera-id", required=True)
    n.add_argument("--annotator", default="")
    n.add_argument("--source-kind", choices=SOURCE_KINDS, default=None,
                   help="where the footage came from (default: from the clip's sidecar, else exported_file)")
    c = sub.add_parser("check")
    c.add_argument("footage", type=Path, nargs="+", help="footage folder(s), e.g. ../validation/tuning ../validation/independent")
    a = ap.parse_args()
    if a.cmd == "new":
        print("wrote", _new(a.clip, a.scenario, a.camera_id, a.annotator, a.source_kind), "- fill in the times; it will not validate until you do")
        return
    bad = total = 0
    kinds: dict[str, int] = {}
    for root in a.footage:
        if not root.is_dir():
            raise SystemExit(f"{root} is not a folder")
        for clip in find_clips(root):
            total += 1
            try:
                meta = load_clip(clip, clip.parent.name)
                k = meta.get("source_kind", "unspecified")
                kinds[k] = kinds.get(k, 0) + 1
                print("ok     ", clip.relative_to(root), f"[{k}]")
            except MetaError as e:
                bad += 1
                print("INVALID", clip.relative_to(root), "-", e)
        for p in ignored_files(root):
            print("WARNING", p.relative_to(root), "- not a supported clip (use .mkv/.mp4/.avi/.mov; cut it with cctv_clip): it will NOT be validated")
    print(f"{total} clips, {bad} invalid; sources: {kinds or 'none'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
