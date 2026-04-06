"""
CONFIT AI Services - Base Classes
=================================
Foundation classes for all AI services.

Features:
- Async model loading
- GPU/CPU device management
- Inference pipeline abstraction
- Batch processing support
- Model caching
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Generic
import threading
from contextlib import asynccontextmanager

import numpy as np

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class DeviceType(Enum):
    """Device types for inference."""
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"  # Apple Silicon


@dataclass
class ModelConfig:
    """Configuration for AI model."""
    name: str
    version: str = "1.0.0"
    device: DeviceType = DeviceType.CPU
    batch_size: int = 1
    max_sequence_length: int = 512
    precision: str = "float32"  # float16, float32, bfloat16
    cache_dir: Optional[Path] = None
    
    # Model-specific settings
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def get_device_str(self) -> str:
        """Get device string for PyTorch."""
        return self.device.value


@dataclass
class InferenceResult(Generic[R]):
    """Result from model inference."""
    success: bool
    data: Optional[R] = None
    error: Optional[str] = None
    confidence: float = 0.0
    processing_time_ms: float = 0.0
    model_name: str = ""
    model_version: str = "1.0.0"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelCache:
    """
    Thread-safe model cache for lazy loading.
    
    Prevents redundant model loading across requests.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._models = {}
                    cls._instance._model_locks = {}
        return cls._instance
    
    def get(self, model_name: str) -> Optional[Any]:
        """Get cached model."""
        return self._models.get(model_name)
    
    def set(self, model_name: str, model: Any) -> None:
        """Cache a model."""
        self._models[model_name] = model
    
    def contains(self, model_name: str) -> bool:
        """Check if model is cached."""
        return model_name in self._models
    
    def get_lock(self, model_name: str) -> threading.Lock:
        """Get lock for model loading."""
        if model_name not in self._model_locks:
            self._model_locks[model_name] = threading.Lock()
        return self._model_locks[model_name]
    
    def clear(self, model_name: Optional[str] = None) -> None:
        """Clear model(s) from cache."""
        if model_name:
            self._models.pop(model_name, None)
        else:
            self._models.clear()


class AIServiceBase(ABC):
    """
    Abstract base class for AI services.
    
    Provides:
    - Device management (GPU/CPU)
    - Model lifecycle
    - Async inference
    - Batch processing
    - Metrics collection
    """
    
    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig(name=self.__class__.__name__)
        self._model = None
        self._device = None
        self._cache = ModelCache()
        self._is_loaded = False
        self._load_lock = asyncio.Lock()
        
        # Metrics
        self._inference_count = 0
        self._total_inference_time = 0.0
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return model name for caching."""
        pass
    
    @abstractmethod
    async def load_model(self) -> None:
        """Load model into memory."""
        pass
    
    @abstractmethod
    async def _infer(self, input_data: T) -> R:
        """Core inference logic."""
        pass
    
    async def ensure_loaded(self) -> None:
        """Ensure model is loaded (lazy loading)."""
        if self._is_loaded:
            return
        
        async with self._load_lock:
            if self._is_loaded:
                return
            
            # Check cache first
            cached = self._cache.get(self.model_name)
            if cached is not None:
                self._model = cached
                self._is_loaded = True
                logger.info(f"Loaded {self.model_name} from cache")
                return
            
            # Load model
            await self.load_model()
            
            # Cache it
            if self._model is not None:
                self._cache.set(self.model_name, self._model)
            
            self._is_loaded = True
            logger.info(f"Loaded {self.model_name} successfully")
    
    async def infer(
        self,
        input_data: T,
        confidence_threshold: float = 0.0
    ) -> InferenceResult[R]:
        """
        Run inference on input data.
        
        Args:
            input_data: Input for the model
            confidence_threshold: Minimum confidence to return result
            
        Returns:
            InferenceResult with output data
        """
        start_time = time.perf_counter()
        
        try:
            await self.ensure_loaded()
            
            result = await self._infer(input_data)
            
            processing_time = (time.perf_counter() - start_time) * 1000
            
            # Update metrics
            self._inference_count += 1
            self._total_inference_time += processing_time
            
            return InferenceResult(
                success=True,
                data=result,
                processing_time_ms=processing_time,
                model_name=self.model_name,
                model_version=self.config.version,
            )
            
        except Exception as e:
            processing_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Inference error in {self.model_name}: {e}")
            
            return InferenceResult(
                success=False,
                error=str(e),
                processing_time_ms=processing_time,
                model_name=self.model_name,
            )
    
    async def batch_infer(
        self,
        inputs: List[T],
        batch_size: Optional[int] = None
    ) -> List[InferenceResult[R]]:
        """
        Run batch inference.
        
        Args:
            inputs: List of inputs
            batch_size: Override default batch size
            
        Returns:
            List of InferenceResults
        """
        batch_size = batch_size or self.config.batch_size
        results = []
        
        for i in range(0, len(inputs), batch_size):
            batch = inputs[i:i + batch_size]
            batch_results = await asyncio.gather(*[
                self.infer(inp) for inp in batch
            ])
            results.extend(batch_results)
        
        return results
    
    def _get_device(self) -> str:
        """Get best available device."""
        try:
            import torch
            
            if self.config.device != DeviceType.CPU:
                if torch.cuda.is_available() and self.config.device == DeviceType.CUDA:
                    return "cuda"
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    return "mps"
            
            return "cpu"
            
        except ImportError:
            return "cpu"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        avg_time = (
            self._total_inference_time / self._inference_count
            if self._inference_count > 0 else 0
        )
        
        return {
            "model_name": self.model_name,
            "inference_count": self._inference_count,
            "total_inference_time_ms": self._total_inference_time,
            "average_inference_time_ms": avg_time,
            "is_loaded": self._is_loaded,
            "device": self._get_device(),
        }
    
    async def unload(self) -> None:
        """Unload model from memory."""
        self._model = None
        self._is_loaded = False
        self._cache.clear(self.model_name)
        logger.info(f"Unloaded {self.model_name}")


class InferencePipeline:
    """
    Chain multiple AI services into a pipeline.
    
    Example:
        pipeline = InferencePipeline([
            wardrobe_intelligence,  # Detect clothing
            style_analyzer,         # Analyze style
            recommendation_engine, # Get recommendations
        ])
        
        result = await pipeline.run(image_bytes)
    """
    
    def __init__(
        self,
        services: List[AIServiceBase],
        pass_results: bool = True
    ):
        """
        Initialize pipeline.
        
        Args:
            services: List of AI services to chain
            pass_results: Pass previous results to next service
        """
        self.services = services
        self.pass_results = pass_results
    
    async def run(
        self,
        initial_input: Any,
        **kwargs
    ) -> List[InferenceResult]:
        """
        Run the full pipeline.
        
        Args:
            initial_input: Input for first service
            **kwargs: Additional arguments
            
        Returns:
            List of results from each stage
        """
        results = []
        current_input = initial_input
        
        for i, service in enumerate(self.services):
            if i > 0 and self.pass_results and results:
                # Pass previous results as context
                result = await service.infer(
                    current_input,
                    previous_results=results,
                    **kwargs
                )
            else:
                result = await service.infer(current_input, **kwargs)
            
            results.append(result)
            
            # Use this result as input for next stage
            if result.success and result.data is not None:
                current_input = result.data
        
        return results
    
    async def run_parallel(
        self,
        input_data: Any
    ) -> List[InferenceResult]:
        """
        Run all services in parallel on same input.
        
        Args:
            input_data: Input for all services
            
        Returns:
            List of results from each service
        """
        return await asyncio.gather(*[
            service.infer(input_data)
            for service in self.services
        ])


@asynccontextmanager
async def gpu_context():
    """Context manager for GPU operations."""
    try:
        import torch
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        yield
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
    except ImportError:
        yield


def get_device_info() -> Dict[str, Any]:
    """Get information about available devices."""
    info = {
        "cpu": True,
        "cuda": False,
        "mps": False,
        "cuda_devices": [],
    }
    
    try:
        import torch
        
        info["cuda"] = torch.cuda.is_available()
        
        if info["cuda"]:
            info["cuda_devices"] = [
                {
                    "name": torch.cuda.get_device_name(i),
                    "memory_total_gb": torch.cuda.get_device_properties(i).total_memory / 1e9,
                }
                for i in range(torch.cuda.device_count())
            ]
        
        if hasattr(torch.backends, 'mps'):
            info["mps"] = torch.backends.mps.is_available()
            
    except ImportError:
        pass
    
    return info
