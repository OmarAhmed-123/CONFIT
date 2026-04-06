"""
Neural Model Manager
====================
Manages loading, selection, and fallback between neural try-on models.

Provides a unified interface for:
- Auto-selection of best available model
- Model loading with device detection
- Fallback to classical CV when neural models unavailable
- Model caching and memory management
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from enum import Enum

from PIL import Image
import numpy as np

from . import NeuralTryOnModel, NeuralTryOnResult, NeuralModelType

logger = logging.getLogger(__name__)


@dataclass
class ModelStatus:
    """Status of a neural model."""
    model_type: NeuralModelType
    available: bool
    loaded: bool
    device: str
    error_message: Optional[str] = None
    last_inference_ms: float = 0.0


class NeuralModelManager:
    """
    Manager for neural try-on models.
    
    Handles:
    - Model discovery and availability checking
    - Lazy loading with memory management
    - Automatic device selection (CUDA > MPS > CPU)
    - Fallback chain when models fail
    """
    
    def __init__(self, auto_load: bool = False, prefer_fp16: bool = True):
        """
        Initialize model manager.
        
        Args:
            auto_load: Automatically load best available model on init
            prefer_fp16: Prefer FP16 inference for speed
        """
        self._models: Dict[NeuralModelType, NeuralTryOnModel] = {}
        self._statuses: Dict[NeuralModelType, ModelStatus] = {}
        self._prefer_fp16 = prefer_fp16
        self._current_model: Optional[NeuralModelType] = None
        
        # Initialize status for all model types
        for model_type in NeuralModelType:
            if model_type != NeuralModelType.AUTO:
                self._statuses[model_type] = ModelStatus(
                    model_type=model_type,
                    available=False,
                    loaded=False,
                    device="cpu",
                )
        
        # Check availability
        self._check_model_availability()
        
        if auto_load:
            self.load_best_available()
    
    def _check_model_availability(self) -> None:
        """Check which models are available (dependencies installed)."""
        # Check IDM-VTON
        try:
            import torch
            import diffusers
            self._statuses[NeuralModelType.IDM_VTON] = ModelStatus(
                model_type=NeuralModelType.IDM_VTON,
                available=True,
                loaded=False,
                device=self._get_best_device(),
            )
            logger.info("IDM-VTON dependencies available")
        except ImportError:
            self._statuses[NeuralModelType.IDM_VTON] = ModelStatus(
                model_type=NeuralModelType.IDM_VTON,
                available=False,
                loaded=False,
                device="cpu",
                error_message="Requires: pip install torch diffusers transformers accelerate",
            )
        
        # OOTDiffusion - placeholder
        self._statuses[NeuralModelType.OOT_DIFFUSION] = ModelStatus(
            model_type=NeuralModelType.OOT_DIFFUSION,
            available=False,
            loaded=False,
            device="cpu",
            error_message="OOTDiffusion not yet implemented",
        )
        
        # GP-VTON - placeholder
        self._statuses[NeuralModelType.GP_VTON] = ModelStatus(
            model_type=NeuralModelType.GP_VTON,
            available=False,
            loaded=False,
            device="cpu",
            error_message="GP-VTON not yet implemented",
        )
    
    def _get_best_device(self) -> str:
        """Get best available device for inference."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"
    
    def get_available_models(self) -> List[NeuralModelType]:
        """Get list of models with dependencies available."""
        return [
            model_type for model_type, status in self._statuses.items()
            if status.available
        ]
    
    def get_loaded_models(self) -> List[NeuralModelType]:
        """Get list of currently loaded models."""
        return [
            model_type for model_type, status in self._statuses.items()
            if status.loaded
        ]
    
    def get_best_available(self) -> Optional[NeuralModelType]:
        """Get best available model type (priority: IDM-VTON > OOT > GP-VTON)."""
        priority = [
            NeuralModelType.IDM_VTON,
            NeuralModelType.OOT_DIFFUSION,
            NeuralModelType.GP_VTON,
        ]
        
        for model_type in priority:
            if self._statuses.get(model_type, ModelStatus(model_type, False, False, "cpu")).available:
                return model_type
        
        return None
    
    def load_model(
        self,
        model_type: NeuralModelType,
        device: str = "auto",
    ) -> bool:
        """
        Load a specific model.
        
        Args:
            model_type: Model to load
            device: Target device
            
        Returns:
            True if loaded successfully
        """
        if model_type == NeuralModelType.AUTO:
            model_type = self.get_best_available()
            if model_type is None:
                logger.warning("No neural models available")
                return False
        
        status = self._statuses.get(model_type)
        if status is None or not status.available:
            logger.warning(f"Model {model_type} not available")
            return False
        
        if status.loaded and model_type in self._models:
            logger.info(f"Model {model_type} already loaded")
            return True
        
        # Create and load model
        try:
            model = self._create_model(model_type)
            if model is None:
                return False
            
            success = model.load_model(device)
            if success:
                self._models[model_type] = model
                self._statuses[model_type] = ModelStatus(
                    model_type=model_type,
                    available=True,
                    loaded=True,
                    device=model._device if hasattr(model, '_device') else device,
                )
                self._current_model = model_type
                logger.info(f"Model {model_type} loaded successfully")
                return True
            else:
                self._statuses[model_type] = ModelStatus(
                    model_type=model_type,
                    available=True,
                    loaded=False,
                    device="cpu",
                    error_message="Failed to load model weights",
                )
                return False
                
        except Exception as e:
            logger.error(f"Failed to load {model_type}: {e}")
            self._statuses[model_type] = ModelStatus(
                model_type=model_type,
                available=True,
                loaded=False,
                device="cpu",
                error_message=str(e),
            )
            return False
    
    def load_best_available(self) -> Optional[NeuralModelType]:
        """Load the best available model.
        
        Returns:
            Model type that was loaded, or None if none available
        """
        best = self.get_best_available()
        if best is None:
            return None
        
        if self.load_model(best):
            return best
        return None
    
    def _create_model(self, model_type: NeuralModelType) -> Optional[NeuralTryOnModel]:
        """Create model instance."""
        if model_type == NeuralModelType.IDM_VTON:
            from .idm_vton import IDMVTONModel
            return IDMVTONModel(use_fp16=self._prefer_fp16)
        
        # Placeholder for other models
        logger.warning(f"Model {model_type} not yet implemented")
        return None
    
    def unload_model(self, model_type: NeuralModelType) -> None:
        """Unload a specific model from memory."""
        if model_type in self._models:
            self._models[model_type].unload_model()
            del self._models[model_type]
            
            status = self._statuses.get(model_type)
            if status:
                self._statuses[model_type] = ModelStatus(
                    model_type=model_type,
                    available=True,
                    loaded=False,
                    device="cpu",
                )
            
            if self._current_model == model_type:
                self._current_model = None
            
            logger.info(f"Model {model_type} unloaded")
    
    def unload_all(self) -> None:
        """Unload all models from memory."""
        for model_type in list(self._models.keys()):
            self.unload_model(model_type)
    
    def infer(
        self,
        person_image: Image.Image,
        garment_image: Image.Image,
        model_type: NeuralModelType = NeuralModelType.AUTO,
        **kwargs,
    ) -> NeuralTryOnResult:
        """
        Run inference with specified or best available model.
        
        Args:
            person_image: Person image
            garment_image: Garment image
            model_type: Model to use (AUTO selects best)
            **kwargs: Additional inference parameters
            
        Returns:
            NeuralTryOnResult
        """
        # Select model
        if model_type == NeuralModelType.AUTO:
            model_type = self._current_model or self.get_best_available()
        
        if model_type is None:
            return NeuralTryOnResult(
                success=False,
                error_message="No neural models available. Install torch and diffusers.",
                model_used="none",
            )
        
        # Load if not loaded
        if model_type not in self._models or not self._models[model_type].is_loaded():
            if not self.load_model(model_type):
                return NeuralTryOnResult(
                    success=False,
                    error_message=f"Failed to load {model_type}",
                    model_used=str(model_type),
                )
        
        # Run inference
        model = self._models[model_type]
        result = model.infer(person_image, garment_image, **kwargs)
        
        # Update status
        if result.success:
            status = self._statuses.get(model_type)
            if status:
                self._statuses[model_type] = ModelStatus(
                    model_type=model_type,
                    available=True,
                    loaded=True,
                    device=status.device,
                    last_inference_ms=result.inference_time_ms,
                )
        
        return result
    
    def get_status(self, model_type: NeuralModelType = NeuralModelType.AUTO) -> Dict[str, Any]:
        """Get status of specified model or all models."""
        if model_type == NeuralModelType.AUTO:
            return {
                str(mt): {
                    "available": s.available,
                    "loaded": s.loaded,
                    "device": s.device,
                    "error": s.error_message,
                    "last_inference_ms": s.last_inference_ms,
                }
                for mt, s in self._statuses.items()
            }
        
        status = self._statuses.get(model_type)
        if status is None:
            return {"error": f"Unknown model type: {model_type}"}
        
        return {
            "available": status.available,
            "loaded": status.loaded,
            "device": status.device,
            "error": status.error_message,
            "last_inference_ms": status.last_inference_ms,
        }
    
    def get_current_model(self) -> Optional[NeuralModelType]:
        """Get currently active model type."""
        return self._current_model
    
    def is_neural_available(self) -> bool:
        """Check if any neural model is available."""
        return len(self.get_available_models()) > 0


# Singleton instance
_manager: Optional[NeuralModelManager] = None


def get_neural_manager() -> NeuralModelManager:
    """Get singleton NeuralModelManager instance."""
    global _manager
    if _manager is None:
        auto_load = os.getenv("TRYON_NEURAL_AUTO_LOAD", "0").lower() in ("1", "true", "yes")
        prefer_fp16 = os.getenv("TRYON_NEURAL_FP16", "1").lower() in ("1", "true", "yes")
        _manager = NeuralModelManager(auto_load=auto_load, prefer_fp16=prefer_fp16)
    return _manager


def infer_neural_tryon(
    person_image: Image.Image,
    garment_image: Image.Image,
    **kwargs,
) -> NeuralTryOnResult:
    """
    Convenience function for neural try-on inference.
    
    Uses singleton manager for model caching.
    """
    return get_neural_manager().infer(person_image, garment_image, **kwargs)
