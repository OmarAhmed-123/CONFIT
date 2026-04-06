"""
CONFIT Backend — Model Control Pipeline (MCP)
===============================================
Central coordination layer for AI model inference.

Components:
- ModelRouter: Selects optimal model based on request and availability
- CacheLayer: Redis-backed result and garment caching
- GPUScheduler: GPU memory management and batch inference
- Pipeline: Main orchestrator tying all MCP components together
- TryOnOrchestrator: Unified entry point for all try-on requests
"""

from .pipeline import ModelControlPipeline
from .orchestrator import TryOnOrchestrator
from .model_router import ModelRouter
from .cache_layer import TryOnCache
from .gpu_scheduler import GPUScheduler

__all__ = [
    "ModelControlPipeline",
    "TryOnOrchestrator",
    "ModelRouter",
    "TryOnCache",
    "GPUScheduler",
]
