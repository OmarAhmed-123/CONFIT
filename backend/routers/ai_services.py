"""
CONFIT AI Services API Router
============================
REST API endpoints for all AI services.

Endpoints:
- /stylist/* - Virtual Stylist
- /recommendations/* - Outfit Recommendations
- /visual-search/* - Visual Search
- /wardrobe/* - Wardrobe Intelligence
- /tryon/* - Virtual Try-On
"""

import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    Depends,
    BackgroundTasks,
)
from fastapi.responses import Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Services"])


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────

class StylistRequest(BaseModel):
    """Virtual stylist request."""
    text: str = Field(..., description="Natural language styling request")
    user_id: Optional[str] = Field(None, description="User ID for personalization")
    budget_min: Optional[float] = Field(None, description="Minimum budget")
    budget_max: Optional[float] = Field(None, description="Maximum budget")
    occasion: Optional[str] = Field(None, description="Occasion type hint")


class OutfitRecommendationRequest(BaseModel):
    """Outfit recommendation request."""
    user_id: Optional[str] = Field(None, description="User ID")
    occasion: Optional[str] = Field(None, description="Occasion type")
    budget_min: Optional[float] = Field(None, description="Minimum budget")
    budget_max: Optional[float] = Field(None, description="Maximum budget")
    seed_items: Optional[List[str]] = Field(None, description="Seed item IDs")
    limit: int = Field(5, ge=1, le=20, description="Number of recommendations")


class VisualSearchRequest(BaseModel):
    """Visual search request."""
    text_query: Optional[str] = Field(None, description="Text search query")
    category: Optional[str] = Field(None, description="Category filter")
    min_price: Optional[float] = Field(None, description="Minimum price")
    max_price: Optional[float] = Field(None, description="Maximum price")
    limit: int = Field(20, ge=1, le=100, description="Number of results")


class WardrobeAnalysisRequest(BaseModel):
    """Wardrobe analysis request."""
    user_id: str = Field(..., description="User ID")
    generate_stats: bool = Field(True, description="Generate wardrobe statistics")
    detect_gaps: bool = Field(True, description="Detect wardrobe gaps")


class TryOnRequest(BaseModel):
    """Virtual try-on request metadata."""
    garment_type: Optional[str] = Field(None, description="Garment type hint")
    adjust_lighting: bool = Field(True, description="Adjust lighting")
    refine_edges: bool = Field(True, description="Refine edges")
    output_format: str = Field("PNG", description="Output image format")


# ─────────────────────────────────────────────────────────────────────────────
# Virtual Stylist Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/stylist/analyze", response_model=Dict[str, Any])
async def analyze_styling_request(request: StylistRequest):
    """
    Analyze natural language styling request.
    
    Returns:
        - Detected occasion
        - Extracted budget
        - Style analysis
        - Outfit suggestions
    """
    from services.ai_services import VirtualStylistService
    from services.ai_services.virtual_stylist import StylistRequest as InternalRequest
    
    try:
        service = VirtualStylistService()
        
        internal_request = InternalRequest(
            text=request.text,
            user_id=request.user_id,
        )
        
        result = await service.infer(internal_request)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        data = result.data
        
        return {
            "success": True,
            "occasion": {
                "type": data.occasion.occasion_type.value,
                "confidence": data.occasion.confidence,
                "formality_level": data.occasion.formality_level,
                "time_of_day": data.occasion.time_of_day,
                "weather": data.occasion.weather,
            },
            "budget": {
                "min": data.budget.min_budget,
                "max": data.budget.max_budget,
                "currency": data.budget.currency,
            },
            "style_analysis": data.style_analysis,
            "outfit_suggestions": [
                {
                    "items": suggestion.items,
                    "total_price": suggestion.total_price,
                    "style_match_score": suggestion.style_match_score,
                    "occasion_match_score": suggestion.occasion_match_score,
                    "explanation": suggestion.explanation,
                    "styling_tips": suggestion.styling_tips,
                }
                for suggestion in data.outfit_suggestions
            ],
            "confidence": data.confidence,
            "reasoning": data.reasoning,
            "processing_time_ms": result.processing_time_ms,
        }
        
    except Exception as e:
        logger.error(f"Stylist analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stylist/occasions", response_model=List[str])
async def get_occasion_types():
    """Get list of supported occasion types."""
    from services.ai_services.virtual_stylist import OccasionType
    return [occasion.value for occasion in OccasionType]


# ─────────────────────────────────────────────────────────────────────────────
# Outfit Recommendation Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/recommendations/outfits", response_model=Dict[str, Any])
async def get_outfit_recommendations(request: OutfitRecommendationRequest):
    """
    Get personalized outfit recommendations.
    
    Returns:
        - List of outfit recommendations with scores
        - User style vector
    """
    from services.ai_services import OutfitRecommendationEngine
    from services.ai_services.outfit_recommendation import (
        RecommendationRequest,
        RecommendationType,
    )
    
    try:
        service = OutfitRecommendationEngine()
        
        budget = None
        if request.budget_min is not None or request.budget_max is not None:
            budget = (request.budget_min or 0, request.budget_max or 10000)
        
        internal_request = RecommendationRequest(
            user_id=request.user_id,
            occasion=request.occasion,
            budget=budget,
            seed_items=request.seed_items,
            limit=request.limit,
            recommendation_type=RecommendationType.OUTFIT_COMPLETE,
        )
        
        result = await service.infer(internal_request)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        data = result.data
        
        return {
            "success": True,
            "recommendations": [
                {
                    "items": [item.to_dict() for item in rec.items],
                    "total_price": rec.total_price,
                    "compatibility_score": rec.compatibility_score,
                    "style_match_score": rec.style_match_score,
                    "personalization_score": rec.personalization_score,
                    "trend_score": rec.trend_score,
                    "explanation": rec.explanation,
                }
                for rec in data.recommendations
            ],
            "user_style_vector": data.user_style_vector.to_dict() if data.user_style_vector else None,
            "processing_time_ms": result.processing_time_ms,
        }
        
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/similar-users/{user_id}", response_model=List[Dict[str, Any]])
async def get_similar_users(user_id: str, limit: int = 10):
    """Get similar users for collaborative filtering."""
    from services.ai_services import OutfitRecommendationEngine
    
    try:
        service = OutfitRecommendationEngine()
        await service.ensure_loaded()
        
        similar = service.get_similar_users(user_id, limit)
        
        return [
            {"user_id": uid, "similarity": score}
            for uid, score in similar
        ]
        
    except Exception as e:
        logger.error(f"Similar users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Visual Search Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/visual-search/image", response_model=Dict[str, Any])
async def search_by_image(
    image: UploadFile = File(..., description="Query image"),
    category: Optional[str] = Form(None),
    min_price: Optional[float] = Form(None),
    max_price: Optional[float] = Form(None),
    limit: int = Form(20),
):
    """
    Search for similar products using an image.
    
    Returns:
        - List of similar products with similarity scores
        - Detected attributes from query image
    """
    from services.ai_services import VisualSearchAIService
    from services.ai_services.visual_search import VisualSearchRequest as InternalRequest
    
    try:
        # Read image
        image_bytes = await image.read()
        
        # Build filters
        filters = {}
        if category:
            filters["category"] = category
        if min_price is not None:
            filters["min_price"] = min_price
        if max_price is not None:
            filters["max_price"] = max_price
        
        service = VisualSearchAIService()
        
        internal_request = InternalRequest(
            image_bytes=image_bytes,
            filters=filters,
            limit=limit,
            return_attributes=True,
        )
        
        result = await service.infer(internal_request)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        data = result.data
        
        return {
            "success": True,
            "results": [
                {
                    "item_id": r.item_id,
                    "similarity_score": r.similarity_score,
                    "image_url": r.image_url,
                    "metadata": r.metadata,
                }
                for r in data.results
            ],
            "detected_attributes": {
                "category": data.detected_attributes.category if data.detected_attributes else None,
                "colors": data.detected_attributes.colors if data.detected_attributes else [],
                "patterns": data.detected_attributes.patterns if data.detected_attributes else [],
                "styles": data.detected_attributes.styles if data.detected_attributes else [],
            } if data.detected_attributes else None,
            "processing_time_ms": result.processing_time_ms,
        }
        
    except Exception as e:
        logger.error(f"Visual search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/visual-search/text", response_model=Dict[str, Any])
async def search_by_text(request: VisualSearchRequest):
    """
    Search for products using text query.
    
    Returns:
        - List of matching products with relevance scores
    """
    from services.ai_services import VisualSearchAIService
    from services.ai_services.visual_search import VisualSearchRequest as InternalRequest
    
    try:
        # Build filters
        filters = {}
        if request.category:
            filters["category"] = request.category
        if request.min_price is not None:
            filters["min_price"] = request.min_price
        if request.max_price is not None:
            filters["max_price"] = request.max_price
        
        service = VisualSearchAIService()
        
        internal_request = InternalRequest(
            text_query=request.text_query,
            filters=filters,
            limit=request.limit,
        )
        
        result = await service.infer(internal_request)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        data = result.data
        
        return {
            "success": True,
            "query": request.text_query,
            "results": [
                {
                    "item_id": r.item_id,
                    "similarity_score": r.similarity_score,
                    "image_url": r.image_url,
                    "metadata": r.metadata,
                }
                for r in data.results
            ],
            "processing_time_ms": result.processing_time_ms,
        }
        
    except Exception as e:
        logger.error(f"Text search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/visual-search/index/add", response_model=Dict[str, Any])
async def add_to_search_index(
    item_id: str = Form(...),
    image: UploadFile = File(...),
    metadata: str = Form("{}"),
):
    """Add item to visual search index."""
    from services.ai_services import VisualSearchAIService
    import json
    
    try:
        image_bytes = await image.read()
        metadata_dict = json.loads(metadata)
        
        service = VisualSearchAIService()
        await service.ensure_loaded()
        
        # Get embedding
        embedding = await service._encode_image(image_bytes)
        
        # Add to index
        service.add_item(item_id, embedding.vector, metadata_dict)
        
        return {
            "success": True,
            "item_id": item_id,
            "index_size": service.get_index_size(),
        }
        
    except Exception as e:
        logger.error(f"Index add error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Wardrobe Intelligence Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/wardrobe/analyze-image", response_model=Dict[str, Any])
async def analyze_clothing_image(
    image: UploadFile = File(..., description="Clothing image"),
    detect_style: bool = Form(True),
    extract_colors: bool = Form(True),
):
    """
    Analyze a clothing image.
    
    Returns:
        - Detected clothing items
        - Colors
        - Style tags
        - Seasons
    """
    from services.ai_services import WardrobeIntelligenceService
    from services.ai_services.wardrobe_intelligence import WardrobeAnalysisRequest as InternalRequest
    
    try:
        image_bytes = await image.read()
        
        service = WardrobeIntelligenceService()
        
        internal_request = InternalRequest(
            image_bytes=image_bytes,
            detect_clothing=True,
            extract_colors=extract_colors,
            classify_style=detect_style,
            generate_stats=False,
        )
        
        result = await service.infer(internal_request)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        data = result.data
        
        return {
            "success": True,
            "detected_items": [item.to_dict() for item in data.detected_items],
            "processing_time_ms": result.processing_time_ms,
        }
        
    except Exception as e:
        logger.error(f"Wardrobe analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wardrobe/stats", response_model=Dict[str, Any])
async def get_wardrobe_stats(request: WardrobeAnalysisRequest):
    """
    Get comprehensive wardrobe statistics.
    
    Returns:
        - Category distribution
        - Color distribution
        - Style profile
        - Gap analysis
        - Recommendations
    """
    from services.ai_services import WardrobeIntelligenceService
    from services.ai_services.wardrobe_intelligence import WardrobeAnalysisRequest as InternalRequest
    
    try:
        # Would fetch wardrobe items from database
        # Placeholder for now
        wardrobe_items = []
        
        service = WardrobeIntelligenceService()
        
        internal_request = InternalRequest(
            wardrobe_items=wardrobe_items,
            user_id=request.user_id,
            generate_stats=request.generate_stats,
            detect_gaps=request.detect_gaps,
        )
        
        result = await service.infer(internal_request)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        data = result.data
        
        return {
            "success": True,
            "wardrobe_stats": data.wardrobe_stats.to_dict() if data.wardrobe_stats else None,
            "style_profile": data.style_profile,
            "recommendations": data.recommendations,
            "processing_time_ms": result.processing_time_ms,
        }
        
    except Exception as e:
        logger.error(f"Wardrobe stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wardrobe/categories", response_model=List[str])
async def get_clothing_categories():
    """Get list of clothing categories."""
    from services.ai_services.wardrobe_intelligence import ClothingCategory
    return [cat.value for cat in ClothingCategory]


@router.get("/wardrobe/styles", response_model=List[str])
async def get_style_categories():
    """Get list of style categories."""
    from services.ai_services.wardrobe_intelligence import StyleCategory
    return [style.value for style in StyleCategory]


# ─────────────────────────────────────────────────────────────────────────────
# Virtual Try-On Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/tryon/try")
async def virtual_try_on(
    person_image: UploadFile = File(..., description="Person image"),
    garment_image: UploadFile = File(..., description="Garment image"),
    garment_type: Optional[str] = Form(None),
    adjust_lighting: bool = Form(True),
    refine_edges: bool = Form(True),
    output_format: str = Form("PNG"),
):
    """
    Perform virtual try-on.
    
    Returns:
        - Output image with garment overlaid
    """
    from services.ai_services import TryOnAIService
    from services.ai_services.tryon_ai import (
        TryOnRequest as InternalRequest,
        GarmentType,
        output_to_bytes,
    )
    
    try:
        person_bytes = await person_image.read()
        garment_bytes = await garment_image.read()
        
        # Parse garment type
        g_type = None
        if garment_type:
            try:
                g_type = GarmentType(garment_type)
            except ValueError:
                pass
        
        service = TryOnAIService()
        
        internal_request = InternalRequest(
            person_image_bytes=person_bytes,
            garment_image_bytes=garment_bytes,
            garment_type=g_type,
            adjust_lighting=adjust_lighting,
            refine_edges=refine_edges,
        )
        
        result = await service.infer(internal_request)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        # Convert output to bytes
        output_bytes = output_to_bytes(result, output_format)
        
        media_type = "image/png" if output_format.upper() == "PNG" else "image/jpeg"
        
        return Response(
            content=output_bytes,
            media_type=media_type,
            headers={
                "X-Blend-Score": str(result.data.blend_score),
                "X-Realism-Score": str(result.data.realism_score),
                "X-Processing-Time-Ms": str(result.data.processing_time_ms),
            }
        )
        
    except Exception as e:
        logger.error(f"Try-on error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tryon/detect-pose", response_model=Dict[str, Any])
async def detect_body_pose(
    image: UploadFile = File(..., description="Person image"),
):
    """
    Detect body pose and landmarks.
    
    Returns:
        - Body landmarks
        - Bounding box
        - Rotation angle
    """
    from services.ai_services import TryOnAIService
    
    try:
        image_bytes = await image.read()
        
        service = TryOnAIService()
        await service.ensure_loaded()
        
        # Load image
        image_array = service._load_image(image_bytes)
        
        # Detect pose
        pose = await service._detect_pose(image_array)
        
        return {
            "success": True,
            "landmarks": [
                {
                    "part": lm.part.value,
                    "x": lm.x,
                    "y": lm.y,
                    "confidence": lm.confidence,
                    "visibility": lm.visibility,
                }
                for lm in pose.landmarks
            ],
            "bounding_box": pose.bounding_box,
            "rotation_angle": pose.rotation_angle,
            "confidence": pose.confidence,
        }
        
    except Exception as e:
        logger.error(f"Pose detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tryon/segment-garment", response_model=Dict[str, Any])
async def segment_garment(
    image: UploadFile = File(..., description="Garment image"),
    garment_type: Optional[str] = Form(None),
):
    """
    Segment garment from image.
    
    Returns:
        - Segmentation mask
        - Bounding box
        - Garment type
    """
    from services.ai_services import TryOnAIService
    from services.ai_services.tryon_ai import GarmentType
    
    try:
        image_bytes = await image.read()
        
        # Parse garment type
        g_type = None
        if garment_type:
            try:
                g_type = GarmentType(garment_type)
            except ValueError:
                pass
        
        service = TryOnAIService()
        await service.ensure_loaded()
        
        # Load image
        image_array = service._load_image(image_bytes)
        
        # Segment
        segment = await service._segment_garment(image_array, g_type)
        
        return {
            "success": True,
            "garment_type": segment.garment_type.value,
            "bounding_box": segment.mask.bounding_box,
            "confidence": segment.mask.confidence,
        }
        
    except Exception as e:
        logger.error(f"Segmentation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Service Health & Metrics
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=Dict[str, Any])
async def get_ai_services_health():
    """Get health status of all AI services."""
    from services.ai_services import (
        VirtualStylistService,
        OutfitRecommendationEngine,
        VisualSearchAIService,
        WardrobeIntelligenceService,
        TryOnAIService,
    )
    from services.ai_services.base import get_device_info
    
    services = {
        "virtual_stylist": VirtualStylistService(),
        "outfit_recommendation": OutfitRecommendationEngine(),
        "visual_search": VisualSearchAIService(),
        "wardrobe_intelligence": WardrobeIntelligenceService(),
        "tryon_ai": TryOnAIService(),
    }
    
    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_info": get_device_info(),
        "services": {},
    }
    
    for name, service in services.items():
        health["services"][name] = {
            "is_loaded": service._is_loaded,
            "metrics": service.get_metrics(),
        }
    
    return health


@router.get("/metrics", response_model=Dict[str, Any])
async def get_ai_services_metrics():
    """Get metrics from all AI services."""
    from services.ai_services import (
        VirtualStylistService,
        OutfitRecommendationEngine,
        VisualSearchAIService,
        WardrobeIntelligenceService,
        TryOnAIService,
    )
    
    services = [
        ("virtual_stylist", VirtualStylistService()),
        ("outfit_recommendation", OutfitRecommendationEngine()),
        ("visual_search", VisualSearchAIService()),
        ("wardrobe_intelligence", WardrobeIntelligenceService()),
        ("tryon_ai", TryOnAIService()),
    ]
    
    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {},
    }
    
    for name, service in services:
        metrics["services"][name] = service.get_metrics()
    
    return metrics
