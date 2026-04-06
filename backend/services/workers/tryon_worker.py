"""
CONFIT Backend — Try-On Worker
==============================
Celery tasks for virtual try-on processing.

Tasks:
- process_tryon: Main try-on processing
- process_rotation: 360° frame generation
- health_check: Worker health status
"""

import logging
import asyncio
import time
from typing import Any, Dict, Optional
from datetime import datetime

from services.workers.celery_app import app
from models.tryon_models import TryOnRequest, TryOnResponse, QualityMetrics

logger = logging.getLogger(__name__)


# ===========================================
# Main Try-On Task
# ===========================================

@app.task(
    bind=True,
    name='services.workers.tryon_worker.process_tryon',
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def process_tryon(self, request_data: dict) -> Dict[str, Any]:
    """
    Process virtual try-on request.
    
    This is the main async task for try-on processing.
    It handles:
    - Image preprocessing
    - Pose detection
    - Segmentation
    - Neural synthesis
    - Quality validation
    
    Args:
        request_data: TryOnRequest as dict
        
    Returns:
        TryOnResponse as dict
    """
    task_id = self.request.id
    start_time = time.time()
    
    logger.info(f"[{task_id}] Starting try-on processing")
    
    try:
        # Validate request
        request = TryOnRequest(**request_data)
        
        # Run async orchestrator
        result = _run_async_orchestrator(request, task_id)
        
        processing_time = (time.time() - start_time) * 1000
        result['processingTimeMs'] = processing_time
        
        logger.info(f"[{task_id}] Completed in {processing_time:.0f}ms")
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[{task_id}] Failed: {error_msg}", exc_info=True)
        
        # Check for recoverable errors
        if _is_recoverable_error(error_msg):
            # Update request for retry
            request_data = _prepare_retry(request_data, error_msg)
            
            # Retry with backoff
            raise self.retry(
                exc=e,
                countdown=min(10 * (2 ** self.request.retries), 60)
            )
        
        # Return error response
        return {
            'success': False,
            'error': error_msg,
            'taskId': task_id,
        }


def _run_async_orchestrator(request: TryOnRequest, task_id: str) -> Dict[str, Any]:
    """
    Run the same MCP try-on pipeline as HTTP (FASHN → Gateway → Advanced → HF → Local).
    """
    from services.mcp.orchestrator import TryOnOrchestrator
    from models.tryon_models import TryOnResponse

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        orch = TryOnOrchestrator.get_instance()
        opts: Dict[str, Any] = {}
        if request.options:
            opts["fit_type"] = request.options.fitType
            opts["quality_threshold"] = request.options.qualityThreshold
            opts["validate"] = request.options.enableValidation
            opts["return_validation_details"] = request.options.returnValidationDetails
        if getattr(request, "garmentCategory", None):
            opts["garment_category"] = request.garmentCategory

        async def _run():
            return await orch.process(
                user_image_base64=request.userImageBase64,
                garment_image_url=request.garmentImageUrl,
                garment_name=request.garmentName,
                options=opts or None,
            )

        result = loop.run_until_complete(asyncio.wait_for(_run(), timeout=240.0))

        msg = (
            "Virtual try-on completed!"
            if result.success
            else (result.error_message or "Processing failed")
        )
        return TryOnResponse(
            success=result.success,
            resultImage=result.result_image,
            message=msg,
            error=result.error_message if not result.success else None,
            qualityScore=result.quality_score,
            poseDetected=result.pose_detected,
            garmentCategory=result.garment_category,
            processingTimeMs=result.processing_time_ms,
            warnings=result.warnings or [],
        ).model_dump()

    except asyncio.TimeoutError:
        raise Exception("Processing timed out after 4 minutes")
    finally:
        loop.close()


def _is_recoverable_error(error_msg: str) -> bool:
    """
    Check if error is recoverable with retry.
    """
    recoverable_patterns = [
        'out of memory',
        'cuda error',
        'gpu',
        'timeout',
        'connection reset',
        'temporary',
    ]
    
    error_lower = error_msg.lower()
    return any(pattern in error_lower for pattern in recoverable_patterns)


def _prepare_retry(request_data: dict, error_msg: str) -> dict:
    """
    Prepare request for retry with adjusted parameters.
    """
    options = request_data.get('options', {})
    
    # Reduce resolution for OOM errors
    if 'memory' in error_msg.lower():
        options['resolution'] = 'medium'
        options['quality_threshold'] = 0.5
    
    request_data['options'] = options
    return request_data


# ===========================================
# Rotation Task
# ===========================================

@app.task(
    bind=True,
    name='services.workers.tryon_worker.process_rotation',
    max_retries=2,
)
def process_rotation(self, source_image: str, frame_count: int = 36) -> Dict[str, Any]:
    """
    Generate 360° rotation frames from try-on result.
    
    Args:
        source_image: Base64-encoded source image
        frame_count: Number of frames to generate
        
    Returns:
        Dict with frames array
    """
    task_id = self.request.id
    
    logger.info(f"[{task_id}] Generating {frame_count} rotation frames")
    
    try:
        from services.rotation_service import RotationService
        
        service = RotationService()
        
        # Run async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            frames = loop.run_until_complete(
                service.generate_frames(source_image, frame_count)
            )
        finally:
            loop.close()
        
        return {
            'success': True,
            'frames': frames,
            'frameCount': len(frames),
        }
        
    except Exception as e:
        logger.error(f"[{task_id}] Rotation failed: {e}")
        return {
            'success': False,
            'error': str(e),
        }


# ===========================================
# Health Check Task
# ===========================================

@app.task(
    name='services.workers.tryon_worker.health_check',
)
def health_check() -> Dict[str, Any]:
    """
    Check worker health status.
    
    Returns:
        Dict with health status
    """
    health = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {},
    }
    
    # Check CUDA
    try:
        import torch
        
        health['checks']['cuda'] = {
            'available': torch.cuda.is_available(),
        }
        
        if torch.cuda.is_available():
            health['checks']['cuda'].update({
                'device_name': torch.cuda.get_device_name(0),
                'device_count': torch.cuda.device_count(),
                'memory_allocated_gb': torch.cuda.memory_allocated(0) / 1024**3,
                'memory_reserved_gb': torch.cuda.memory_reserved(0) / 1024**3,
                'memory_total_gb': torch.cuda.get_device_properties(0).total_memory / 1024**3,
            })
            
            # Check if GPU memory is critically low
            free_memory = (
                torch.cuda.get_device_properties(0).total_memory - 
                torch.cuda.memory_allocated(0)
            ) / 1024**3
            
            if free_memory < 2:
                health['status'] = 'degraded'
                health['checks']['cuda']['warning'] = 'Low GPU memory'
                
    except ImportError:
        health['checks']['cuda'] = {'available': False, 'error': 'PyTorch not installed'}
    except Exception as e:
        health['checks']['cuda'] = {'available': False, 'error': str(e)}
        health['status'] = 'degraded'
    
    # Check Redis
    try:
        from services.workers.celery_app import check_broker_connection
        health['checks']['redis'] = {
            'connected': check_broker_connection(),
        }
    except Exception as e:
        health['checks']['redis'] = {'connected': False, 'error': str(e)}
        health['status'] = 'degraded'
    
    # Check models
    try:
        from models.model_loader import model_loader
        
        models = ['idm_vton', 'viton_hd']
        health['checks']['models'] = {}
        
        for model_name in models:
            try:
                model = model_loader.load_tryon_model(model_name)
                health['checks']['models'][model_name] = {
                    'loaded': model is not None,
                }
            except Exception as e:
                health['checks']['models'][model_name] = {
                    'loaded': False,
                    'error': str(e),
                }
                
    except Exception as e:
        health['checks']['models'] = {'error': str(e)}
    
    return health


# ===========================================
# Preprocessing Task
# ===========================================

@app.task(
    name='services.workers.preprocessing_worker.preprocess_garment',
)
def preprocess_garment(garment_id: str, garment_image: str) -> Dict[str, Any]:
    """
    Preprocess garment for faster try-on.
    
    Generates:
    - Multiple resolution variants
    - Pre-warped versions for common poses
    - Thumbnails
    """
    logger.info(f"Preprocessing garment: {garment_id}")
    
    try:
        from services.assets.preprocessing_pipeline import GarmentPreprocessor
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            preprocessor = GarmentPreprocessor()
            result = loop.run_until_complete(
                preprocessor.preprocess_garment(garment_id, garment_image)
            )
        finally:
            loop.close()
        
        return {
            'success': True,
            'garment_id': garment_id,
            'variants': result.get('variants', {}),
        }
        
    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        return {
            'success': False,
            'error': str(e),
        }


# ===========================================
# Maintenance Tasks
# ===========================================

@app.task(
    name='services.workers.maintenance_worker.cleanup_gpu_memory',
)
def cleanup_gpu_memory() -> Dict[str, Any]:
    """
    Periodic task to cleanup GPU memory.
    """
    try:
        import torch
        
        if torch.cuda.is_available():
            before = torch.cuda.memory_allocated(0) / 1024**3
            
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            
            after = torch.cuda.memory_allocated(0) / 1024**3
            
            return {
                'success': True,
                'freed_gb': before - after,
                'current_gb': after,
            }
            
    except Exception as e:
        return {'success': False, 'error': str(e)}
    
    return {'success': True, 'message': 'CUDA not available'}


@app.task(
    name='services.workers.maintenance_worker.clear_model_cache',
)
def clear_model_cache() -> Dict[str, Any]:
    """
    Clear model cache to free memory.
    """
    try:
        from models.model_loader import model_loader
        model_loader.clear_cache()
        
        return {'success': True, 'message': 'Model cache cleared'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
