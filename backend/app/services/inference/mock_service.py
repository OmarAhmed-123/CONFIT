"""
CONFIT Backend — Mock Inference Service
=====================================
Simulated inference service for development without GPU.

Features:
- Realistic processing delays
- Fake pose detection
- Fake segmentation
- Pre-generated try-on results
- Identical API to GPU service
"""

import asyncio
import base64
import io
import logging
import os
import random
from typing import Dict, Any, Optional, List
from pathlib import Path

from services.inference.base import (
    InferenceServiceBase,
    InferenceMode,
    InferenceResult,
    PoseDetectionResult,
    SegmentationResult,
)

logger = logging.getLogger(__name__)


class MockInferenceService(InferenceServiceBase):
    """
    Mock inference service for development.
    
    Simulates realistic AI inference behavior without requiring GPU.
    All responses are generated or loaded from pre-cached data.
    
    Usage:
        service = MockInferenceService()
        result = await service.process_tryon(user_image, garment_image, garment_id)
    """
    
    def __init__(self):
        self._mode = InferenceMode.MOCK
        
        # Configuration from environment
        self.delay_min = float(os.getenv('MOCK_DELAY_MIN', '2.0'))
        self.delay_max = float(os.getenv('MOCK_DELAY_MAX', '5.0'))
        self.quality_min = float(os.getenv('MOCK_QUALITY_SCORE_MIN', '0.70'))
        self.quality_max = float(os.getenv('MOCK_QUALITY_SCORE_MAX', '0.95'))
        
        # Load mock data
        self._mock_data_dir = Path(__file__).parent.parent.parent / 'mock_services' / 'data'
        self._sample_results: List[bytes] = []
        self._garment_cache: Dict[str, bytes] = {}
        
        # Initialize sample data
        self._initialize_mock_data()
        
        logger.info(
            f"MockInferenceService initialized "
            f"(delay: {self.delay_min}-{self.delay_max}s, "
            f"quality: {self.quality_min}-{self.quality_max})"
        )
    
    @property
    def mode(self) -> InferenceMode:
        return self._mode
    
    @property
    def is_available(self) -> bool:
        """Mock service is always available."""
        return True
    
    def _initialize_mock_data(self):
        """Initialize mock data from disk or generate defaults."""
        # Create mock data directory if needed
        self._mock_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load sample results
        sample_dir = self._mock_data_dir / 'sample_results'
        if sample_dir.exists():
            for file in sample_dir.glob('*.jpg'):
                self._sample_results.append(file.read_bytes())
            logger.info(f"Loaded {len(self._sample_results)} sample results")
        
        # Load sample garments
        garment_dir = self._mock_data_dir / 'sample_garments'
        if garment_dir.exists():
            for file in garment_dir.glob('*.jpg'):
                self._garment_cache[file.stem] = file.read_bytes()
            logger.info(f"Loaded {len(self._garment_cache)} sample garments")
        
        # Generate default sample if none loaded
        if not self._sample_results:
            self._sample_results = [self._generate_default_result()]
    
    def _generate_default_result(self) -> bytes:
        """Generate a default placeholder result image."""
        from PIL import Image, ImageDraw, ImageFont
        
        # Create placeholder image
        img = Image.new('RGB', (512, 640), color=(240, 240, 245))
        draw = ImageDraw.Draw(img)
        
        # Draw placeholder text
        text = "Virtual Try-On Result\n(Mock Mode)"
        bbox = draw.textbbox((0, 0), text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (512 - text_width) // 2
        y = (640 - text_height) // 2
        
        draw.text((x, y), text, fill=(100, 100, 100))
        
        # Draw border
        draw.rectangle([10, 10, 502, 630], outline=(200, 200, 200), width=2)
        
        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue()
    
    async def process_tryon(
        self,
        user_image: str,
        garment_image: str,
        garment_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> InferenceResult:
        """
        Process virtual try-on request (simulated).
        
        Simulates:
        1. Processing delay (2-5 seconds)
        2. Pose detection
        3. Segmentation
        4. Neural synthesis
        5. Quality validation
        """
        logger.info(f"[MOCK] Processing try-on for garment: {garment_id}")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Simulate processing delay
            delay = random.uniform(self.delay_min, self.delay_max)
            await asyncio.sleep(delay)
            
            # Simulate stages
            await self._simulate_pose_detection()
            await self._simulate_segmentation()
            await self._simulate_synthesis()
            
            # Generate result
            result_image = await self._generate_mock_result(user_image, garment_id)
            
            # Calculate quality score
            quality_score = random.uniform(self.quality_min, self.quality_max)
            
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            logger.info(
                f"[MOCK] Try-on completed in {processing_time:.0f}ms "
                f"(quality: {quality_score:.2f})"
            )
            
            return InferenceResult(
                success=True,
                result_image=result_image,
                processing_time_ms=processing_time,
                quality_score=quality_score,
                pose_detected=True,
                garment_category=self._detect_garment_category(garment_id),
                metadata={
                    'mode': 'mock',
                    'simulated_delay': delay,
                }
            )
            
        except Exception as e:
            logger.error(f"[MOCK] Try-on failed: {e}")
            return InferenceResult(
                success=False,
                error=str(e),
                processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
            )
    
    async def detect_pose(self, image: str) -> PoseDetectionResult:
        """Detect pose (simulated)."""
        logger.info("[MOCK] Detecting pose")
        
        # Simulate delay
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Generate fake keypoints
        keypoints = self._generate_fake_keypoints()
        score = random.uniform(0.85, 0.98)
        
        return PoseDetectionResult(
            success=True,
            keypoints=keypoints,
            score=score,
            is_valid=score > 0.5,
            feedback=None if score > 0.7 else "Please face the camera directly"
        )
    
    async def segment_image(
        self,
        image: str,
        pose_keypoints: Optional[Dict] = None
    ) -> SegmentationResult:
        """Segment image (simulated)."""
        logger.info("[MOCK] Segmenting image")
        
        # Simulate delay
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        # Generate fake masks
        person_mask = self._generate_fake_mask()
        
        return SegmentationResult(
            success=True,
            person_mask=person_mask,
            face_mask=person_mask,  # Simplified
            upper_body_mask=person_mask,
            lower_body_mask=person_mask,
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        return {
            'status': 'healthy',
            'mode': 'mock',
            'available': True,
            'gpu_required': False,
            'sample_results_loaded': len(self._sample_results),
            'garments_cached': len(self._garment_cache),
        }
    
    # ========================================
    # Simulation Helpers
    # ========================================
    
    async def _simulate_pose_detection(self):
        """Simulate pose detection stage."""
        await asyncio.sleep(random.uniform(0.1, 0.3))
    
    async def _simulate_segmentation(self):
        """Simulate segmentation stage."""
        await asyncio.sleep(random.uniform(0.2, 0.4))
    
    async def _simulate_synthesis(self):
        """Simulate neural synthesis stage."""
        await asyncio.sleep(random.uniform(1.0, 2.0))
    
    async def _generate_mock_result(
        self,
        user_image: str,
        garment_id: str
    ) -> str:
        """
        Generate mock try-on result.
        
        In production, this would use neural networks.
        Here we return a pre-generated or composited image.
        """
        # Try to load garment-specific result
        if garment_id in self._garment_cache:
            result_bytes = self._garment_cache[garment_id]
        else:
            # Use random sample result
            result_bytes = random.choice(self._sample_results)
        
        # Encode to base64
        result_b64 = base64.b64encode(result_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{result_b64}"
    
    def _generate_fake_keypoints(self) -> Dict[str, Any]:
        """Generate realistic-looking pose keypoints."""
        # MediaPipe-style 33 keypoints
        keypoints = []
        
        # Define approximate positions for frontal pose
        base_positions = [
            # Face
            (0.5, 0.08, 'nose'),
            (0.47, 0.06, 'left_eye_inner'),
            (0.46, 0.06, 'left_eye'),
            (0.45, 0.06, 'left_eye_outer'),
            (0.53, 0.06, 'right_eye_inner'),
            (0.54, 0.06, 'right_eye'),
            (0.55, 0.06, 'right_eye_outer'),
            (0.43, 0.07, 'left_ear'),
            (0.57, 0.07, 'right_ear'),
            (0.48, 0.09, 'mouth_left'),
            (0.52, 0.09, 'mouth_right'),
            
            # Upper body
            (0.38, 0.20, 'left_shoulder'),
            (0.62, 0.20, 'right_shoulder'),
            (0.32, 0.35, 'left_elbow'),
            (0.68, 0.35, 'right_elbow'),
            (0.28, 0.48, 'left_wrist'),
            (0.72, 0.48, 'right_wrist'),
            
            # Hands (simplified)
            (0.27, 0.50, 'left_pinky'),
            (0.73, 0.50, 'right_pinky'),
            (0.26, 0.48, 'left_index'),
            (0.74, 0.48, 'right_index'),
            (0.28, 0.49, 'left_thumb'),
            (0.72, 0.49, 'right_thumb'),
            
            # Lower body
            (0.42, 0.52, 'left_hip'),
            (0.58, 0.52, 'right_hip'),
            (0.43, 0.72, 'left_knee'),
            (0.57, 0.72, 'right_knee'),
            (0.44, 0.92, 'left_ankle'),
            (0.56, 0.92, 'right_ankle'),
            
            # Feet
            (0.44, 0.94, 'left_heel'),
            (0.56, 0.94, 'right_heel'),
            (0.42, 0.96, 'left_foot_index'),
            (0.58, 0.96, 'right_foot_index'),
        ]
        
        for i, (x, y, name) in enumerate(base_positions):
            # Add small random variation
            x_var = x + random.uniform(-0.02, 0.02)
            y_var = y + random.uniform(-0.02, 0.02)
            visibility = random.uniform(0.85, 0.99)
            
            keypoints.append({
                'x': max(0, min(1, x_var)),
                'y': max(0, min(1, y_var)),
                'z': random.uniform(-0.1, 0.1),
                'visibility': visibility,
                'name': name,
            })
        
        return {
            'keypoints': keypoints,
            'num_landmarks': len(keypoints),
        }
    
    def _generate_fake_mask(self) -> str:
        """Generate a fake segmentation mask."""
        from PIL import Image, ImageDraw
        
        # Create simple person-shaped mask
        img = Image.new('L', (512, 640), color=0)
        draw = ImageDraw.Draw(img)
        
        # Draw person shape (simplified)
        # Head
        draw.ellipse([200, 20, 312, 100], fill=255)
        # Torso
        draw.polygon([
            (180, 100), (332, 100),
            (350, 350), (162, 350)
        ], fill=255)
        # Legs
        draw.rectangle([162, 350, 240, 600], fill=255)
        draw.rectangle([272, 350, 350, 600], fill=255)
        
        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        
        # Encode to base64
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _detect_garment_category(self, garment_id: str) -> str:
        """Detect garment category from ID (heuristic)."""
        garment_lower = garment_id.lower()
        
        if any(x in garment_lower for x in ['shirt', 'top', 'blouse', 'jacket', 'sweater']):
            return 'tops'
        elif any(x in garment_lower for x in ['pants', 'jeans', 'trousers', 'shorts']):
            return 'pants'
        elif any(x in garment_lower for x in ['dress', 'skirt']):
            return 'dresses'
        else:
            return 'tops'


# ========================================
# Convenience Functions
# ========================================

def get_mock_service() -> MockInferenceService:
    """Get the mock inference service instance."""
    return MockInferenceService()
