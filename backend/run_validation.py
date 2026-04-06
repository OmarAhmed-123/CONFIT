"""Quick validation script for anti-sticker fixes."""
import sys
import os

# Force output to be unbuffered
os.environ['PYTHONUNBUFFERED'] = '1'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import numpy as np

# Output file for results
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'validation_results.txt')

def log(msg: str):
    """Print and write to file."""
    print(msg)
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
    sys.stdout.flush()

def main():
    # Clear output file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('')
    
    log('=' * 60)
    log('ANTI-STICKER FIXES VALIDATION')
    log('=' * 60)

    passed = 0
    failed = 0

    # Test 1: Strip mesh default
    log('\n[TEST 1] Strip mesh warp default')
    try:
        from services.tryon.warping.tps import warp_rgba_strip_mesh, warp_rgba_to_quad
        
        rgba = np.zeros((100, 80, 4), dtype=np.uint8)
        rgba[:, :, :3] = 150
        rgba[:, :, 3] = 255
        
        dst_quad = np.array([[20, 10], [100, 12], [90, 150], [30, 148]], dtype=np.float32)
        
        mesh = warp_rgba_strip_mesh(rgba, dst_quad, (120, 160), strips=16)
        flat = warp_rgba_to_quad(rgba, dst_quad, (120, 160))
        
        log(f'  Strip mesh output shape: {mesh.shape}')
        log(f'  Flat warp output shape: {flat.shape}')
        log('  PASSED')
        passed += 1
    except Exception as e:
        log(f'  FAILED: {e}')
        failed += 1

    # Test 2: Quality thresholds
    log('\n[TEST 2] Quality thresholds raised')
    try:
        from services.tryon.tryon_service import _effective_min_output_quality
        
        min_q = _effective_min_output_quality({}, 0.72)
        min_q_low = _effective_min_output_quality({}, 0.50)
        
        log(f'  Min quality (thresh=0.72): {min_q}')
        log(f'  Min quality (thresh=0.50): {min_q_low}')
        assert min_q >= 0.60, f'Min quality should be >= 0.60, got {min_q}'
        assert min_q_low >= 0.60, f'Min quality floor should be 0.60, got {min_q_low}'
        log('  PASSED')
        passed += 1
    except Exception as e:
        log(f'  FAILED: {e}')
        failed += 1

    # Test 3: Body-anchored scaling
    log('\n[TEST 3] Body-anchored garment scaling')
    try:
        from services.tryon.tryon_service import _scale_garment_rgba_to_shoulder
        from services.tryon.warping.garment import GarmentCategory
        
        rgba = np.zeros((150, 100, 4), dtype=np.uint8)
        rgba[10:140, 10:90, :3] = 128
        rgba[10:140, 10:90, 3] = 255
        
        tops = _scale_garment_rgba_to_shoulder(rgba, 90.0, GarmentCategory.TOPS, None, 120.0)
        dress = _scale_garment_rgba_to_shoulder(rgba, 90.0, GarmentCategory.DRESSES, None, 120.0)
        
        log(f'  TOPS scaled: {tops.shape}')
        log(f'  DRESS scaled: {dress.shape}')
        assert dress.shape[0] > tops.shape[0], 'Dresses should be taller'
        log('  PASSED')
        passed += 1
    except Exception as e:
        log(f'  FAILED: {e}')
        failed += 1

    # Test 4: estimate_body_angle_deg moved
    log('\n[TEST 4] estimate_body_angle_deg moved to anchoring.py')
    try:
        from services.tryon.anchoring import estimate_body_angle_deg
        from services.tryon.pose import PoseMap
        
        pm = PoseMap(
            left_shoulder=(40.0, 50.0, 0.9),
            right_shoulder=(100.0, 55.0, 0.9),
            neck=(70.0, 52.0, 0.9),
            left_hip=(45.0, 140.0, 0.8),
            right_hip=(95.0, 138.0, 0.8),
            confidence=0.85,
            image_width=160,
            image_height=200,
        )
        
        angle = estimate_body_angle_deg(pm)
        log(f'  Angle from PoseMap: {angle:.2f} degrees')
        
        # Check not in tps
        import services.tryon.warping.tps as tps
        assert not hasattr(tps, 'estimate_body_angle_deg'), 'Should not be in tps.py'
        log('  PASSED')
        passed += 1
    except Exception as e:
        log(f'  FAILED: {e}')
        failed += 1

    # Test 5: build_anchored_dst_quad
    log('\n[TEST 5] build_anchored_dst_quad with image dimensions')
    try:
        from services.tryon.anchoring import build_anchored_dst_quad, compute_body_anchors
        from services.tryon.warping.garment import GarmentCategory
        
        pm = PoseMap(
            left_shoulder=(60.0, 80.0, 0.9),
            right_shoulder=(140.0, 82.0, 0.9),
            neck=(100.0, 81.0, 0.9),
            left_hip=(70.0, 200.0, 0.8),
            right_hip=(130.0, 198.0, 0.8),
            confidence=0.85,
            image_width=200,
            image_height=300,
        )
        
        anchors = compute_body_anchors(pm)
        quad = build_anchored_dst_quad(anchors, GarmentCategory.TOPS, 200, 300)
        
        log(f'  Quad shape: {quad.shape}')
        log(f'  Quad dtype: {quad.dtype}')
        log(f'  Neck anchor: {anchors.neck_anchor}')
        log('  PASSED')
        passed += 1
    except Exception as e:
        log(f'  FAILED: {e}')
        failed += 1

    # Test 6: Enhanced segmentation
    log('\n[TEST 6] Enhanced torso detection')
    try:
        from services.tryon.segmentation.body import UnifiedBodySegmenter
        from services.tryon.vision.pose import PoseResult
        
        pose = PoseResult(
            success=True,
            landmarks={
                'left_shoulder': (40, 60, 0.9),
                'right_shoulder': (120, 62, 0.9),
                'left_hip': (50, 150, 0.8),
                'right_hip': (110, 148, 0.8),
            },
            body_regions={},
            body_proportions={},
            image_width=160,
            image_height=200,
            confidence=0.85,
        )
        
        segmenter = UnifiedBodySegmenter()
        torso = segmenter._torso_from_pose(pose, 160, 200)
        
        log(f'  Torso mask shape: {torso.shape}')
        log(f'  Torso coverage: {np.mean(torso > 80) * 100:.1f}%')
        log('  PASSED')
        passed += 1
    except Exception as e:
        log(f'  FAILED: {e}')
        failed += 1

    # Test 7: Adaptive feathering
    log('\n[TEST 7] Adaptive edge feathering')
    try:
        from services.tryon.blending.region_compositor import _feather_alpha_u8
        
        alpha = np.zeros((100, 100), dtype=np.uint8)
        alpha[20:80, 20:80] = 255
        
        feathered = _feather_alpha_u8(alpha, ksize=21)
        
        log(f'  Original alpha max: {np.max(alpha)}')
        log(f'  Feathered alpha max: {np.max(feathered)}')
        log('  PASSED')
        passed += 1
    except Exception as e:
        log(f'  FAILED: {e}')
        failed += 1

    log('\n' + '=' * 60)
    log(f'RESULTS: {passed} passed, {failed} failed')
    log('=' * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
