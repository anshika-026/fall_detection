# Limitations of the rule-based fall engine

This is a heuristic detector over single-camera 2D pose. It is a decision-support tool; it is **not** a
certified safety device and must not be the only protection for anyone at risk.

## What it can and cannot see
1. **It needs a pose.** Everything depends on `yolov8n-pose` finding the person and their keypoints. In the
   recorded tests the nano model often **loses or degrades a person lying on the floor** (very few keypoints, or no
   detection at all), which is exactly when the fall must be confirmed. A person who is not detected cannot be
   confirmed. A larger model, a higher input size or a better camera angle helps but costs compute; this
   trade-off has to be measured on your own cameras (docs/EVALUATION.md).
2. **A standing reference is required.** Heights and speeds are measured in units of the person's own standing
   height, learned from frames where the whole body is visible and upright (full body incl. ankles). A person
   first seen sitting, lying, or only partly visible (desk, counter, frame edge) gives no reference, so **no fall is
   raised for them** until a full-body upright frame has been seen.
3. **Camera geometry.** Thresholds assume a roughly side-on / moderately elevated view. Straight-down ceiling
   cameras, falls directly towards or away from the camera, and strong fisheye distortion shrink the vertical
   displacement and distort torso angle; these views are not supported without re-tuning.
4. **Occlusion and crowds.** Furniture, doors, beds and other people hide keypoints. Overlapping people can merge
   into one box or swap ByteTrack ids. The engine hands a lost person's state to a new track that appears in the
   same place, but a swap between two people is not detectable.
5. **Track-id loss.** ByteTrack frequently re-issues an id when a person drops quickly. Recovery by position works
   for the common case; a person who is out of detection for longer than `orphan_timeout` (default 120 s) is closed
   as "no longer visible", not as resolved by a human.

## Behaviours that are *by design* not alerts
- **Falls ending seated or kneeling** (slumping against a wall, sliding down a cupboard) are not "lying", so they
  are not detected. They are indistinguishable from sitting down by these signals.
- **A slow, controlled descent** to the floor (the elderly lowering themselves, deliberate lying) stays under the
  speed threshold. A real fall that is slow, e.g. fainting while leaning on something, may do the same.
- **A person already on the floor** when first seen, or who lies down fast on purpose and stays still (jumping on to
  a sofa), looks like a fall followed by lying still, and *will* be confirmed. Without zone information (beds, mats)
  the engine cannot tell. Fast exercise that ends on the floor and stays still has the same problem.

## False-positive risks
Burpees, sit-ups, yoga floor poses, children playing, someone dropping something and crouching, a person climbing
into a vehicle or lying under one. The multi-signal rule plus the "must stay down and still for N seconds" step
removes most brief ones; the cost is a confirmation delay (`confirm_seconds`, default 3 s, ×1.5 when partly visible).

## Statistical caveats
- Thresholds are initial engineering values, not fitted to your site. Sensitivity presets scale three of them.
- Numbers from the public dataset (docs/EVALUATION.md) come from acted falls in a lab with a Kinect, not CCTV.
  They say the pipeline runs and where it breaks; they do **not** estimate real-world accuracy.
- Any threshold chosen while looking at those sequences is tuned on the test set and can't be reported as
  accuracy on it.

## Operational limits
- Camera passwords are stored in the SQLite database in clear text (as in SMC); protect the data folder.
- Single-process, in-memory sign-in throttling; one backend instance.
- A backend restart dismisses unconfirmed "possible" falls (no engine state survives a restart); confirmed
  and recovered incidents stay open for an operator.
- No GPU was available during development; capacity numbers are CPU-only and machine-specific.
- Not yet verified: weeks-long stability, behaviour on real RTSP cameras from several vendors, H.265 streams.

## Ways to improve (not done)
Per-camera calibration / floor-plane or zone masks (beds, mats), a larger pose model on the GPU, a temporal
skeleton classifier (ST-GCN / PoseC3D) fine-tuned on your own footage as a second opinion, depth/ceiling
cameras, and an audio or wearable cue for confirmation.
