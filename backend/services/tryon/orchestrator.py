"""
CONFIT Backend — Try-On Orchestrator
====================================
Coordinates the entire virtual try-on pipeline.

Pipeline stages:
1. Preprocessing and validation
2. Pose detection and body analysis
3. Segmentation (person, clothing regions)
4. Garment warping and alignment
5. Neural synthesis
6. Post-processing and quality validation
"""

import io
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
from enum import Enum

import numpy as np
from PIL import Image

from models.tryon_models import TryOnRequest, TryOnResponse, QualityMetrics
from utils.image_utils import validate_base64_image, decode_base64_image
from utils.gpu_utils import GPUManager

logger = logging.getLogger(__name__)


class TryOnStage(Enum):
    """Pipeline stages for progress tracking."""
    PREPROCESSING = "preprocessing"
    POSE_DETECTION = "pose_detection"
    SEGMENTATION = "segmentation"
    GARMENT_PROCESSING = "garment_processing"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    COMPLETE = "complete"
    FAILED = "failed"


class TryOnValidationError(Exception):
    """Raised when try-on validation fails."""
    pass


@dataclass
class TryOnContext:
    """
    Holds all intermediate data during try-on processing.
    Enables stage-by-stage processing with context preservation.
    """
    # Input data
    user_image: bytes
    garment_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    garment_image: Optional[bytes] = None
    garment_3d_url: Optional[str] = None
    garment_metadata: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    
    # Populated during processing
    image_shape: Optional[Tuple[int, int]] = None
    pose_keypoints: Optional[Dict] = None
    pose_score: float = 0.0
    segmentation_masks: Optional[Dict] = None
    body_measurements: Optional[Dict] = None
    warped_garment: Optional[bytes] = None
    raw_result: Optional[bytes] = None
    final_result: Optional[bytes] = None
    quality_metrics: Optional[QualityMetrics] = None
    
    # Visual realism data
    pose_alignment: Optional[Any] = None  # PoseAlignmentScore
    fit_confidence: Optional[Any] = None  # FitConfidenceScore
    lighting_analysis: Optional[Any] = None  # LightingAnalysis
    depth_consistency: Optional[Any] = None  # DepthConsistencyResult
    
    # AI Brain data
    size_prediction: Optional[Dict] = None
    brain_fit_suggestion: Optional[Dict] = None
    
    # Privacy data
    image_id: Optional[str] = None
    
    # Processing metadata
    current_stage: TryOnStage = TryOnStage.PREPROCESSING
    processing_time_ms: float = 0.0
    warnings: list = field(default_factory=list)
    error: Optional[str] = None


class TryOnOrchestrator:
    """
    Coordinates the entire virtual try-on pipeline.
    
    Implements the Strategy pattern for model selection and
    Template Method pattern for pipeline execution.
    
    Integrates:
    - Visual Realism Engine for pose alignment and fit confidence
    - AI Brain for signal tracking and size prediction
    - Privacy Manager for secure image handling
    
    Usage:
        orchestrator = TryOnOrchestrator()
        response = await orchestrator.process(request)
    """
    
    def __init__(self, db_session=None, ai_brain_service=None):
        self.gpu = GPUManager()
        
        # Lazy-loaded services
        self._pose_detector = None
        self._segmenter = None
        self._body_analyzer = None
        self._tryon_engine = None
        self._validator = None
        self._visual_realism = None
        self._brain_integration = None
        self._privacy_manager = None
        
        # External dependencies
        self._db_session = db_session
        self._ai_brain_service = ai_brain_service
        
        # Performance tracking
        self._stage_times: Dict[str, float] = {}
    
    @property
    def pose_detector(self):
        """Lazy load pose detector."""
        if self._pose_detector is None:
            from services.tryon.pose_detector import PoseDetector
            self._pose_detector = PoseDetector()
        return self._pose_detector
    
    @property
    def segmenter(self):
        """Lazy load segmenter."""
        if self._segmenter is None:
            from services.tryon.segmenter import BodySegmenter
            self._segmenter = BodySegmenter()
        return self._segmenter
    
    @property
    def body_analyzer(self):
        """Lazy load body analyzer."""
        if self._body_analyzer is None:
            from services.tryon.body_analyzer import BodyAnalyzer
            self._body_analyzer = BodyAnalyzer()
        return self._body_analyzer
    
    @property
    def tryon_engine(self):
        """Lazy load neural try-on engine."""
        if self._tryon_engine is None:
            from services.tryon.neural_tryon import NeuralTryOnEngine
            self._tryon_engine = NeuralTryOnEngine()
        return self._tryon_engine
    
    @property
    def validator(self):
        """Lazy load quality validator."""
        if self._validator is None:
            from services.tryon.quality_validator import QualityValidator
            self._validator = QualityValidator()
        return self._validator
    
    @property
    def visual_realism(self):
        """Lazy load visual realism engine."""
        if self._visual_realism is None:
            from services.tryon.visual_realism import VisualRealismEngine
            self._visual_realism = VisualRealismEngine()
        return self._visual_realism
    
    @property
    def brain_integration(self):
        """Lazy load AI brain integration."""
        if self._brain_integration is None and self._db_session:
            from services.tryon.brain_integration import TryOnBrainIntegration
            self._brain_integration = TryOnBrainIntegration(
                self._db_session, self._ai_brain_service
            )
        return self._brain_integration
    
    @property
    def privacy_manager(self):
        """Lazy load privacy manager."""
        if self._privacy_manager is None:
            from services.tryon.privacy_manager import PrivacyManager
            self._privacy_manager = PrivacyManager()
        return self._privacy_manager
    
    async def process(self, request: TryOnRequest) -> TryOnResponse:
        """
        Execute the full try-on pipeline.
        
        Args:
            request: Validated try-on request with user image and garment data
            
        Returns:
            TryOnResponse with result image and quality metrics
            
        Raises:
            TryOnValidationError: If validation fails at any stage
            Exception: For unexpected errors
        """
        start_time = time.time()
        
        # Initialize context
        context = TryOnContext(
            user_image=decode_base64_image(request.userImageBase64),
            garment_id=request.garmentId,
            user_id=getattr(request, 'userId', None),
            session_id=getattr(request, 'sessionId', None),
            garment_metadata=getattr(request, 'garmentMetadata', {}),
            options=self._build_options(request.options),
        )
        
        try:
            # Stage 1: Preprocessing
            await self._run_stage(
                context, 
                TryOnStage.PREPROCESSING,
                self._preprocess
            )
            
            # Stage 2: Body analysis
            await self._run_stage(
                context,
                TryOnStage.POSE_DETECTION,
                self._analyze_body
            )
            
            # Stage 3: Segmentation
            await self._run_stage(
                context,
                TryOnStage.SEGMENTATION,
                self._segment
            )
            
            # Stage 4: Garment processing
            await self._run_stage(
                context,
                TryOnStage.GARMENT_PROCESSING,
                self._process_garment
            )
            
            # Stage 5: Neural synthesis
            await self._run_stage(
                context,
                TryOnStage.SYNTHESIS,
                self._synthesize
            )
            
            # Stage 6: Validation and refinement
            await self._run_stage(
                context,
                TryOnStage.VALIDATION,
                self._validate_and_refine
            )
            
            context.current_stage = TryOnStage.COMPLETE
            context.processing_time_ms = (time.time() - start_time) * 1000
            
            # Track successful try-on with AI Brain
            if self.brain_integration and context.user_id:
                try:
                    await self.brain_integration.track_try_on_success(
                        user_id=context.user_id,
                        session_id=context.session_id or 'unknown',
                        garment_id=context.garment_id,
                        quality_score=context.quality_metrics.overallScore if context.quality_metrics else 0.5,
                        processing_time_ms=context.processing_time_ms,
                        body_measurements=context.body_measurements,
                        fit_confidence=context.fit_confidence.overall_confidence if context.fit_confidence else 0.5
                    )
                except Exception as e:
                    logger.warning(f"Failed to track try-on success: {e}")
            
            return self._build_response(context, success=True)
            
        except TryOnValidationError as e:
            logger.warning(f"Validation failed at {context.current_stage.value}: {e}")
            context.error = str(e)
            context.current_stage = TryOnStage.FAILED
            
            # Track failure with AI Brain
            if self.brain_integration and context.user_id:
                try:
                    await self.brain_integration.track_try_on_failure(
                        user_id=context.user_id,
                        session_id=context.session_id or 'unknown',
                        garment_id=context.garment_id,
                        failure_reason=str(e),
                        failure_stage=context.current_stage.value,
                        user_photo_quality=0.5
                    )
                except Exception as track_error:
                    logger.warning(f"Failed to track try-on failure: {track_error}")
            
            return self._build_response(context, success=False, error=str(e))
            
        except Exception as e:
            logger.error(f"Try-on failed: {e}", exc_info=True)
            context.error = str(e)
            context.current_stage = TryOnStage.FAILED
            raise
    
    async def _run_stage(
        self, 
        context: TryOnContext, 
        stage: TryOnStage,
        stage_fn
    ) -> None:
        """Execute a pipeline stage with timing."""
        context.current_stage = stage
        stage_start = time.time()
        
        await stage_fn(context)
        
        self._stage_times[stage.value] = (time.time() - stage_start) * 1000
        logger.debug(f"Stage {stage.value} completed in {self._stage_times[stage.value]:.1f}ms")
    
    async def _preprocess(self, ctx: TryOnContext) -> None:
        """
        Validate and preprocess user image.
        
        Checks:
        - Image format and validity
        - Resolution constraints (512-2048px)
        - Quality assessment (blur, exposure)
        """
        # Load image
        try:
            img = Image.open(io.BytesIO(ctx.user_image))
            img = img.convert('RGB')
        except Exception as e:
            raise TryOnValidationError(f"Invalid image format: {e}")
        
        # Check dimensions
        w, h = img.size
        ctx.image_shape = (h, w)
        
        if min(h, w) < 512:
            raise TryOnValidationError(
                "Image resolution too low. Minimum 512x512 required. "
                f"Current: {w}x{h}"
            )
        
        # Downsample if too large (for performance)
        if max(h, w) > 2048:
            logger.info(f"Downsampling image from {w}x{h}")
            scale = 2048 / max(h, w)
            new_size = (int(w * scale), int(h * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            ctx.image_shape = (new_size[1], new_size[0])
            
            # Update context with resized image
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=95)
            ctx.user_image = buffer.getvalue()
        
        # Quality assessment
        quality_score = self._assess_image_quality(img)
        if quality_score < 0.3:
            ctx.warnings.append("Image quality is low. Results may be affected.")
    
    def _assess_image_quality(self, img: Image.Image) -> float:
        """
        Assess image quality based on blur and exposure.
        
        Returns score 0-1 (1 = best quality)
        """
        import cv2
        
        # Convert to numpy
        img_array = np.array(img)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Blur detection (Laplacian variance)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_score = min(1.0, laplacian_var / 500)  # Normalize
        
        # Exposure check
        mean_brightness = np.mean(gray)
        exposure_score = 1.0 - abs(mean_brightness - 128) / 128
        
        return (blur_score * 0.6 + exposure_score * 0.4)
    
    async def _analyze_body(self, ctx: TryOnContext) -> None:
        """
        Detect pose and extract body measurements.
        
        Uses MediaPipe for pose detection.
        """
        # Run pose detection
        pose_result = await self.pose_detector.detect(ctx.user_image)
        
        ctx.pose_keypoints = pose_result.get('keypoints')
        ctx.pose_score = pose_result.get('score', 0)
        
        # Validate pose detection
        if not ctx.pose_keypoints or ctx.pose_score < 0.5:
            raise TryOnValidationError(
                "Could not detect body pose. Please ensure your full body is visible "
                "and you're facing the camera."
            )
        
        # Check pose quality
        pose_quality = self._check_pose_quality(ctx.pose_keypoints)
        if not pose_quality['is_valid']:
            raise TryOnValidationError(
                f"Pose quality issue: {pose_quality['feedback']}"
            )
        
        if pose_quality['warnings']:
            ctx.warnings.extend(pose_quality['warnings'])
        
        # Extract body measurements
        ctx.body_measurements = self.body_analyzer.analyze(
            ctx.pose_keypoints,
            image_shape=ctx.image_shape
        )
        
        # Analyze pose alignment for visual realism
        ctx.pose_alignment = self.visual_realism.analyze_pose_alignment(
            ctx.pose_keypoints,
            ctx.image_shape
        )
        
        # Add alignment warnings
        if ctx.pose_alignment.overall_score < 0.7:
            ctx.warnings.extend(ctx.pose_alignment.suggestions)
        
        # Get size prediction from AI Brain if available
        if self.brain_integration and ctx.user_id:
            try:
                prediction = await self.brain_integration.get_size_prediction(
                    ctx.user_id,
                    ctx.garment_id,
                    self._classify_garment(ctx.garment_id)
                )
                ctx.size_prediction = prediction.data
            except Exception as e:
                logger.warning(f"Size prediction failed: {e}")
    
    def _check_pose_quality(self, keypoints: Dict) -> Dict:
        """
        Check if pose is suitable for try-on.
        
        Returns dict with is_valid, feedback, and warnings.
        """
        warnings = []
        feedback = []
        
        # Check nose visibility (facing camera)
        nose = keypoints.get(0, {})
        if nose.get('visibility', 0) < 0.7:
            feedback.append("Please face the camera directly")
        
        # Check shoulder alignment
        left_shoulder = keypoints.get(11, {})
        right_shoulder = keypoints.get(12, {})
        
        if left_shoulder.get('visibility', 0) > 0.5 and right_shoulder.get('visibility', 0) > 0.5:
            shoulder_diff = abs(left_shoulder.get('y', 0) - right_shoulder.get('y', 0))
            if shoulder_diff > 0.1:
                feedback.append("Level your shoulders")
        
        # Check arms visible
        left_wrist = keypoints.get(15, {})
        right_wrist = keypoints.get(16, {})
        if left_wrist.get('visibility', 0) < 0.3 and right_wrist.get('visibility', 0) < 0.3:
            warnings.append("Arms not fully visible - may affect sleeve rendering")
        
        # Check distance (body size in frame)
        left_hip = keypoints.get(23, {})
        right_hip = keypoints.get(24, {})
        
        if left_hip.get('visibility', 0) > 0.5 and right_hip.get('visibility', 0) > 0.5:
            hip_width = abs(left_hip.get('x', 0) - right_hip.get('x', 0))
            if hip_width < 0.15:
                feedback.append("Move closer to the camera")
            elif hip_width > 0.6:
                feedback.append("Move back slightly")
        
        is_valid = len(feedback) == 0
        return {
            'is_valid': is_valid,
            'feedback': '. '.join(feedback) if feedback else None,
            'warnings': warnings
        }
    
    async def _segment(self, ctx: TryOnContext) -> None:
        """
        Segment person and clothing regions.
        
        Uses SAM or Self-Correction-Human-Parsing.
        """
        ctx.segmentation_masks = await self.segmenter.segment(
            ctx.user_image,
            pose_keypoints=ctx.pose_keypoints
        )
        
        # Validate segmentation
        if not ctx.segmentation_masks:
            raise TryOnValidationError("Failed to segment image. Please try a different photo.")
        
        # Check person mask coverage
        person_mask = ctx.segmentation_masks.get('person')
        if person_mask is None:
            raise TryOnValidationError("Could not detect person in image.")
    
    async def _process_garment(self, ctx: TryOnContext) -> None:
        """
        Load and warp garment to match body pose.
        """
        # Load garment image if not provided
        if ctx.garment_image is None:
            ctx.garment_image = await self._load_garment_image(ctx.garment_id)
        
        if ctx.garment_image is None:
            raise TryOnValidationError("Garment image not available")
        
        # Determine garment category
        garment_category = self._classify_garment(ctx.garment_id)
        
        # Get fabric type from metadata or default
        fabric_type = ctx.garment_metadata.get('fabric', 'cotton')
        
        # Simulate physics-based garment deformation
        deformation_result = self.visual_realism.simulate_garment_deformation(
            garment_image=ctx.garment_image,
            body_measurements=ctx.body_measurements,
            pose_keypoints=ctx.pose_keypoints,
            fabric_type=fabric_type,
            garment_category=garment_category
        )
        
        if deformation_result.success:
            ctx.warped_garment = deformation_result.warped_garment
        else:
            # Fallback to standard warping
            ctx.warped_garment = await self.tryon_engine.warp_garment(
                garment_image=ctx.garment_image,
                pose_keypoints=ctx.pose_keypoints,
                body_measurements=ctx.body_measurements,
                category=garment_category
            )
    
    async def _synthesize(self, ctx: TryOnContext) -> None:
        """
        Generate try-on result using neural model.
        """
        # Select model based on pose and quality preference
        model = self._select_model(ctx)
        
        ctx.raw_result = await self.tryon_engine.synthesize(
            person_image=ctx.user_image,
            warped_garment=ctx.warped_garment,
            pose_keypoints=ctx.pose_keypoints,
            segmentation_masks=ctx.segmentation_masks,
            model=model
        )
    
    async def _validate_and_refine(self, ctx: TryOnContext) -> None:
        """
        Validate quality and apply refinements if needed.
        """
        # Run quality validation
        ctx.quality_metrics = await self.validator.validate(
            result_image=ctx.raw_result,
            original_image=ctx.user_image,
            pose_keypoints=ctx.pose_keypoints
        )
        
        # Analyze visual realism components
        ctx.lighting_analysis = self.visual_realism.analyze_lighting_adaptation(
            ctx.raw_result,
            ctx.user_image,
            ctx.pose_keypoints
        )
        
        ctx.depth_consistency = self.visual_realism.analyze_depth_consistency(
            ctx.raw_result,
            ctx.segmentation_masks,
            ctx.pose_keypoints
        )
        
        # Calculate fit confidence score
        ctx.fit_confidence = self.visual_realism.calculate_fit_confidence(
            ctx.body_measurements,
            ctx.garment_metadata,
            ctx.pose_alignment,
            self._classify_garment(ctx.garment_id)
        )
        
        quality_threshold = ctx.options.get('quality_threshold', 0.65)
        
        # If quality is low, attempt refinement
        if ctx.quality_metrics.overallScore < quality_threshold:
            logger.info(f"Quality {ctx.quality_metrics.overallScore:.2f} below threshold, refining...")
            ctx.final_result = await self._refine_result(ctx)
        else:
            ctx.final_result = ctx.raw_result
    
    async def _refine_result(self, ctx: TryOnContext) -> bytes:
        """
        Apply post-processing refinements.
        
        Steps:
        1. Edge smoothing
        2. Color harmonization
        3. Shadow synthesis
        """
        # Edge smoothing
        refined = await self.tryon_engine.refine_edges(
            ctx.raw_result,
            ctx.segmentation_masks
        )
        
        # Color harmonization
        refined = await self.tryon_engine.harmonize_colors(
            refined,
            ctx.user_image
        )
        
        # Shadow synthesis
        refined = await self.tryon_engine.add_shadows(
            refined,
            ctx.pose_keypoints
        )
        
        return refined
    
    def _select_model(self, ctx: TryOnContext) -> str:
        """
        Select neural model based on context.
        
        Strategy:
        - Standard frontal pose: IDM-VTON (best quality)
        - Non-standard pose: GP-VTON (general pose)
        - Speed priority: VITON-HD (fast)
        """
        # Check if speed is prioritized
        if ctx.options.get('speed_priority', False):
            return 'viton-hd'
        
        # Check pose angle
        if ctx.body_measurements:
            pose_angle = ctx.body_measurements.get('pose_angle', 0)
            if abs(pose_angle) > 30:
                return 'gp-vton'
        
        return 'idm-vton'  # Default: best quality
    
    def _classify_garment(self, garment_id: str) -> str:
        """
        Classify garment category from ID.
        
        In production, this would query the product database.
        """
        # Simple heuristic based on ID
        garment_id_lower = garment_id.lower()
        
        if any(x in garment_id_lower for x in ['shirt', 'top', 'blouse', 'jacket', 'sweater']):
            return 'tops'
        elif any(x in garment_id_lower for x in ['pants', 'jeans', 'trousers', 'shorts']):
            return 'pants'
        elif any(x in garment_id_lower for x in ['dress', 'skirt']):
            return 'dresses'
        else:
            return 'tops'  # Default
    
    async def _load_garment_image(self, garment_id: str) -> Optional[bytes]:
        """
        Load garment image from storage.
        
        In production, this would:
        1. Check cache
        2. Load from S3/CDN
        3. Return None if not found
        """
        # Placeholder - implement with actual storage
        return None
    
    def _build_options(self, request_options) -> Dict[str, Any]:
        """Build options dict from request options."""
        if request_options is None:
            return {
                "fit_type": "regular",
                "quality_threshold": 0.65,
                "validate": True,
                "return_validation_details": False,
            }
        
        return {
            "fit_type": request_options.fitType,
            "quality_threshold": request_options.qualityThreshold,
            "validate": request_options.enableValidation,
            "return_validation_details": request_options.returnValidationDetails,
        }
    
    def _build_response(
        self, 
        context: TryOnContext, 
        success: bool,
        error: Optional[str] = None
    ) -> TryOnResponse:
        """Build TryOnResponse from context."""
        
        # Encode result image
        result_image = None
        if context.final_result:
            import base64
            result_image = base64.b64encode(context.final_result).decode('utf-8')
            result_image = f"data:image/jpeg;base64,{result_image}"
        
        # Build enhanced response with visual realism data
        response_data = {
            'success': success,
            'resultImage': result_image,
            'message': "Virtual try-on completed successfully!" if success else (error or "Processing failed"),
            'error': error if not success else None,
            'qualityScore': context.quality_metrics.overallScore if context.quality_metrics else 0.0,
            'poseDetected': context.pose_keypoints is not None,
            'garmentCategory': self._classify_garment(context.garment_id),
            'processingTimeMs': context.processing_time_ms,
            'warnings': context.warnings,
            'qualityMetrics': context.quality_metrics,
        }
        
        # Add visual realism scores
        if context.pose_alignment:
            response_data['poseAlignmentScore'] = context.pose_alignment.overall_score
            response_data['poseQualityLevel'] = context.pose_alignment.quality_level.value
        
        
        if context.fit_confidence:
            response_data['fitConfidence'] = context.fit_confidence.overall_confidence
            response_data['fitCategory'] = context.fit_confidence.fit_category
            response_data['sizeRecommendation'] = context.fit_confidence.size_recommendation
            response_data['fitIssues'] = context.fit_confidence.fit_issues
        
        
        if context.lighting_analysis:
            response_data['lightingScore'] = context.lighting_analysis.overall_score
        
        
        if context.depth_consistency:
            response_data['depthConsistencyScore'] = context.depth_consistency.overall_score
        
        
        if context.size_prediction:
            response_data['predictedSize'] = context.size_prediction.get('predicted_size')
            response_data['sizeConfidence'] = context.size_prediction.get('confidence')
        
        
        return TryOnResponse(**response_data)
    
    def get_stage_times(self) -> Dict[str, float]:
        """Return timing breakdown for last processed request."""
        return self._stage_times.copy()
