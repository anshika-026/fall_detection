# Assessment: telling normal sitting from a fall, with a full, upper-body or partial view

Status: **an assessment from reading the code and from the results already measured; no code was changed and nothing new was run.** Statements marked *(code reading)* have not been tested on footage.

## 1. How the current engine treats sitting (code reading)
- **There is no "sitting" detector.** Sitting is simply "not lying". `classify()` in `backend/falldet/fall_analysis/engine.py` calls someone lying when at least 2 of up to 3 votes agree (torso angle >= 55 degrees, box width/height >= 1.0, and, only when head and ankles are both visible, collapsed vertical extent), or when the box is at least 1.2 times wider than tall (the wide-box rule), or at least 1.5 with too few joints to vote. A seated person normally has an upright torso and a narrow box, so no vote passes.
- **A fall trigger requires the person to end lying.** `_descent()` returns nothing unless the current frame is lying, so a fast sit-down (hips drop, upright torso) is rejected by the ending posture, not by its speed. Consequence: a person who slumps in a chair, faints upright, or falls and stays seated-looking is **not** detected.
- **Floor rule:** lying (80% of a 4 s window) and still, with no gaps in tracking, raises POSSIBLE. It cannot tell a floor from a bed or sofa: in the GMDCSA-24 tuning set most of its false alerts were people lying on beds, doing push-ups, or leaning back on a bed.
- **Measured sitting-like false alerts (tuning set, baseline run with the original settings):** clips of sitting down onto the ground and of sitting on the ground raised POSSIBLE alerts: `s2_adl_09` and `s2_adl_13` were dismissed within about a second, and `s2_adl_19` (sitting on the ground and writing) stayed POSSIBLE until the clip ended (raised by the floor rule). Separately, while the head-drop threshold was being tried at 0.35 (since reverted to 0.45), a seated person picking a phone up from the floor (`s1_adl_16`) and a stretching clip also raised POSSIBLE alerts; those two were **not** re-checked under the final settings. I did not find alerts from ordinary sitting on a chair in the tuning clips, but I did not specifically audit every chair clip.

## 2. What the camera sees changes what can be known
| View | What the engine can use | What it cannot know |
|---|---|---|
| **Full body** (head to ankles) | torso angle, box shape, vertical extent against standing height, head and hip drop; hip, knee and ankle positions exist in the data but the engine does not use knee or leg geometry | with a **seated** person the code treats a whole body with an upright torso as "standing" and takes the seated box height as the reference height (`_standing_height`, code reading), so distances are measured in too-small units until the person is seen standing |
| **Upper body only** (desk, counter, frame edge, close camera) | shoulders, head, torso angle if hips are visible, box shape, head drop | no ankles, so no vertical-extent vote; standing height is only a guess from torso length divided by a fixed adult fraction of 0.30; when the hips are missing the engine uses the **box centre** as the body height, and the box centre moves when legs enter or leave the view (a possible false trigger, code reading) |
| **Partial** (head and shoulders, a limb, behind an occluder) | few joints, so most features are empty; a box alone is used only if it is at least 1.5 times wider than tall | whether the person is sitting, standing or crouching; whether they fell **behind** the occluder; the body's orientation |
- The `partial` flag (shoulders or hips missing, or the box touching the frame edge) lengthens CONFIRMED from 3 s to 4.5 s. It does not make the decision more reliable; it only waits longer.
- **Measured on partly visible falls:** in the tuning baseline, 6 fall clips were tagged "partly visible" (the dataset's own description); 4 of them reached POSSIBLE and none reached CONFIRMED. That is six clips: an indication, not a rate.

## 3. What can and cannot be inferred
**Can be inferred (with enough keypoints):** a sudden head or shoulder descent relative to the person's own earlier size; torso rotation towards horizontal and staying there; stillness after it; a person who is upright and steady (sitting, standing, walking); a person who vanishes downward past an occluder.
**Cannot be inferred from partial visibility:**
- standing versus sitting when hips and legs are hidden (the head height depends on the unknown chair and body size);
- the person's true height, so a drop cannot be expressed reliably in body heights;
- that a person fell **onto the floor behind a desk or counter**: only the vanishing head is seen, which also happens when someone bends to pick something up or crouches;
- floor versus bed or sofa, and a deliberate lie-down versus a fall, without scene knowledge (zones) or timing context;
- an upright slump (fainting in a chair) because the torso stays upright.
**Honest consequence:** from an upper-body or partial view the system can raise *possible* alerts for fast head descents, but it cannot reliably separate "sat down quickly", "bent down", "crouched" and "fell" without more evidence, so partial-view results should be reported on their own and not mixed with full-body numbers.

## 4. Representative footage needed to evaluate it
Same camera types, angles, heights, lighting and distances as the real sites, with **human-written labels**, **participant and session identifiers**, and a **visibility category on every clip** (full body, upper body only, partly hidden behind an object, at the frame edge).
- **Normal sitting and transitions, every visibility category:** sitting on chairs of different types, sofas and the floor; sitting down at slow, normal and abrupt speeds; standing up; leaning back, slumping, crossing legs; bending to pick things up or tie shoes; crouching; reaching across a desk; lying on a sofa deliberately.
- **Falls, every visibility category:** from standing and from a chair or sofa onto a soft mat, forward, backward and sideways, **consented, supervised and not dangerous**; including falls that end hidden behind a desk or counter.
- **Hours of ordinary footage per site** (people working, sitting, walking), because false alerts per hour can only be measured on ordinary activity.
- **Several different people**, with the tuning and held-out sets split by participant and by day or session; the existing validation tools already keep the two apart.
- **Enough clips in each visibility-by-activity cell.** The tools report counts, not percentages; with a handful of clips per cell the result is anecdotal.
- Optional low-risk step needing no new people: replay existing adult clips with the lower half of the frame masked, or cropped, to see what the engine receives from an "upper body only" view. This simulates a view, not real furniture or occlusion, and must be labelled as such.
- Public data helps only partly: GMDCSA-24 has sitting, sitting on the floor and falls from a chair, but visibility is described only in free text for a few clips.
