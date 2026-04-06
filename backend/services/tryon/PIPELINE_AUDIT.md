# CONFIT Try-On Pipeline Audit (Pre-Refactor)

This audit records structural gaps that caused floating, misaligned, or sticker-like garments in the previous flow.

## Confirmed Failure Modes

1. **Overlay-style fallback placement existed**
   - The blending layer still had a region-center placement path via `ImageBlender._calculate_position()` in `services/tryon/blending/compositor.py`.
   - This allowed center-biased placement when consumers used non-fullframe blend flows.

2. **No mandatory neck-anchor contract**
   - Previous destination quad logic in `TryOnService` used shoulder/hip heuristics, but did not enforce a strict body anchor contract (`neck_anchor` as root for placement).
   - This left room for drift in off-angle/partial visibility cases.

3. **No explicit depth model stage**
   - Warping used perspective/strip mesh operations but lacked a dedicated depth-estimation output driving vertical compression and perspective parameters as a named stage.

4. **Scaling logic partially body-aware, but not canonical**
   - Scaling used shoulder/torso heuristics, but did not consistently implement one strict formula:
     - `scale_factor = torso_width / garment_reference_width`
   - This could still over/undershoot depending on fallback paths.

## Why These Produced "Floating" Artifacts

- Center fallback and non-anchored paths can decouple garment from clavicle/neck reference.
- Missing depth stage can flatten or stretch torso mapping on perspective-heavy photos.
- Non-canonical scaling allows garment area mismatch with true torso footprint.

## Refactor Goals Implemented

- Introduce reusable `PoseService` and `PoseMap` artifact (`pose_map.json` payload).
- Enforce neck-anchor placement and body coordinate system.
- Add explicit depth/perspective estimation and mesh warp deformation.
- Use canonical torso-width scaling with ratio guards.
- Keep segmentation/occlusion protections so hands can appear above garment and face remains untouched.
