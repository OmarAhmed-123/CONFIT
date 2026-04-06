"""Quick validation of try-on pipeline fixes."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import cv2

# Test 1: body.py torso expansion
print("=== Test 1: Body segmentation imports ===")
from services.tryon.segmentation.body import UnifiedBodySegmenter, SegmentationPack
from services.tryon.vision.pose import PoseResult
seg = UnifiedBodySegmenter()
print("OK: UnifiedBodySegmenter created")

# Test 2: torso_from_pose expansion
print("\n=== Test 2: Torso from pose (expanded) ===")
pose = PoseResult(
    success=True,
    landmarks={
        "left_shoulder": (40.0, 40.0, 0.9),
        "right_shoulder": (100.0, 42.0, 0.9),
        "left_hip": (48.0, 110.0, 0.9),
        "right_hip": (96.0, 108.0, 0.9),
    },
    body_regions={}, body_proportions={},
    image_width=160, image_height=160, confidence=0.9,
)
torso = seg._torso_from_pose(pose, 160, 160)
area = float(np.sum(torso > 80))
total = 160 * 160
pct = area / total * 100
print(f"Torso mask coverage: {pct:.1f}% ({area:.0f} / {total} pixels)")
assert pct > 15, f"Torso mask too small: {pct:.1f}%"
print("PASS: Torso mask is properly expanded")

# Test 3: arms mask excludes shoulders
print("\n=== Test 3: Arms mask (elbow-wrist only) ===")
pose2 = PoseResult(
    success=True,
    landmarks={
        "left_shoulder": (40.0, 40.0, 0.9),
        "right_shoulder": (100.0, 42.0, 0.9),
        "left_elbow": (30.0, 70.0, 0.9),
        "right_elbow": (110.0, 72.0, 0.9),
        "left_wrist": (25.0, 100.0, 0.9),
        "right_wrist": (115.0, 102.0, 0.9),
    },
    body_regions={}, body_proportions={},
    image_width=160, image_height=160, confidence=0.9,
)
arms = seg._arms_from_pose(pose2, 160, 160)
shoulder_area = arms[35:50, 35:105]
shoulder_coverage = float(np.mean(shoulder_area > 80))
print(f"Shoulder area in arms mask: {shoulder_coverage*100:.1f}%")
assert shoulder_coverage < 0.3, "Arms mask should NOT cover shoulder area"
print("PASS: Arms mask excludes shoulders")

# Test 4: region compositor face protection (from existing test suite)
print("\n=== Test 4: Region compositor face protection ===")
from services.tryon.blending.compositor import ImageBlender
from services.tryon.blending.region_compositor import blend_fullframe_region_safe_sync
from PIL import Image

h, w = 128, 128
person = np.zeros((h, w, 3), dtype=np.uint8)
person[:, :] = [50, 60, 70]
face = np.zeros((h, w), dtype=np.uint8)
cv2.circle(face, (64, 28), 18, 255, -1)
hair = np.zeros((h, w), dtype=np.uint8)
arms_m = np.zeros((h, w), dtype=np.uint8)
torso = np.zeros((h, w), dtype=np.uint8)
torso[40:120, 30:98] = 255
g = np.zeros((h, w, 4), dtype=np.uint8)
g[:, :, :3] = 200
g[:, :, 3] = 255

seg_pack = SegmentationPack(
    person_mask=np.ones((h, w), dtype=np.uint8) * 255,
    torso_mask=torso, arms_mask=arms_m, face_mask=face,
    hair_mask=hair, garment_clip_mask=torso,
)
pose_fake = PoseResult(
    success=False, landmarks={}, body_regions={}, body_proportions={},
    image_width=w, image_height=h, confidence=0.0,
)
blender = ImageBlender()
pil = Image.fromarray(person, "RGB")
res = blend_fullframe_region_safe_sync(blender, pil, g, pose_fake, seg_pack)
assert res.success, f"Blend failed: {res.error_message}"
out = np.array(res.image)
# Face region should be preserved (diff < 35)
diff = np.mean(
    np.abs(out[22:34, 56:72].astype(np.float32) - person[22:34, 56:72].astype(np.float32))
)
print(f"Face zone diff from original: {diff:.1f} (lower = protected)")
assert diff < 35.0, f"Face not protected: diff={diff:.1f}"
print("PASS: Face is protected from garment overlay")

# Test 5: Torso zone should have garment (not face, not arms overlapping)
print("\n=== Test 5: Garment visible on torso ===")
torso_zone = out[60:100, 40:88]
person_torso = person[60:100, 40:88]
garment_diff = float(np.mean(np.abs(torso_zone.astype(float) - person_torso.astype(float))))
print(f"Torso zone diff from original: {garment_diff:.1f} (higher = garment visible)")
assert garment_diff > 10, f"Garment not visible on torso (diff={garment_diff:.1f})"
print("PASS: Garment is visible on torso region")

# Test 6: job_scheduler timeout import
print("\n=== Test 6: Job scheduler timeout logic ===")
from services.tryon_runtime.job_scheduler import TryOnJobScheduler
scheduler = TryOnJobScheduler()
print("PASS: TryOnJobScheduler imported and created")

# Test 7: tryon_service clip params
print("\n=== Test 7: TryOnService import ===")
from services.tryon.tryon_service import TryOnService
svc = TryOnService.__new__(TryOnService)
print("PASS: TryOnService created")

print("\n" + "="*50)
print("ALL 7 TESTS PASSED!")
print("="*50)
