"""
CONFIT AI Services
==================
Production-ready AI microservices for fashion intelligence.

Services:
- VirtualStylistService: NLP-based outfit recommendations
- OutfitRecommendationEngine: Collaborative filtering & style vectors
- VisualSearchService: CLIP-based image similarity
- WardrobeIntelligenceService: Clothing detection & analysis
- TryOnAIService: Virtual try-on with segmentation

Architecture:
- Async inference pipelines
- GPU-accelerated processing
- Model caching & lazy loading
- Batch processing support
"""

from .base import (
    AIServiceBase,
    InferenceResult,
    ModelConfig,
    InferencePipeline,
)
from .virtual_stylist import VirtualStylistService
from .outfit_recommendation import OutfitRecommendationEngine
from .visual_search import VisualSearchAIService
from .wardrobe_intelligence import WardrobeIntelligenceService
from .tryon_ai import TryOnAIService

__all__ = [
    # Base classes
    'AIServiceBase',
    'InferenceResult',
    'ModelConfig',
    'InferencePipeline',
    # Services
    'VirtualStylistService',
    'OutfitRecommendationEngine',
    'VisualSearchAIService',
    'WardrobeIntelligenceService',
    'TryOnAIService',
]
