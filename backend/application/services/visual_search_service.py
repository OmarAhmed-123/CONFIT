"""
CONFIT Backend - Visual Search Application Service
===================================================
AI-powered visual search with attribute detection.
"""

import os
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities import VisualSearchSession, VisualSearchResult
from domain.base import VisualSearchStatus
from infrastructure.elasticsearch import ElasticsearchService, get_elasticsearch_client
from database.models import VisualSearchSession as VisualSearchSessionModel


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DTOs
# ─────────────────────────────────────────────────────────────────────────────

class VisualSearchRequestDTO(BaseModel):
    """Visual search request."""
    image_url: str
    category_filter: Optional[str] = None
    color_filter: Optional[str] = None
    style_filter: Optional[List[str]] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    limit: int = 20


class DetectedAttributesDTO(BaseModel):
    """Detected attributes from image."""
    category: Optional[str] = None
    category_confidence: float = 0.0
    color: Optional[str] = None
    color_hex: Optional[str] = None
    color_confidence: float = 0.0
    style_tags: List[str] = []
    style_confidence: float = 0.0
    pattern: Optional[str] = None
    pattern_confidence: float = 0.0
    material: Optional[str] = None
    material_confidence: float = 0.0
    occasion_tags: List[str] = []
    season_tags: List[str] = []
    brand: Optional[str] = None
    brand_confidence: float = 0.0
    attributes: Dict[str, Any] = {}


class SearchResultDTO(BaseModel):
    """Visual search result item."""
    product_id: str
    name: str
    slug: str
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    image_url: Optional[str] = None
    price: float
    currency: str = "USD"
    similarity_score: float
    match_attributes: Dict[str, Any] = {}


class VisualSearchResponseDTO(BaseModel):
    """Visual search response."""
    id: str
    status: str
    image_url: str
    detected_attributes: Optional[DetectedAttributesDTO] = None
    results: List[SearchResultDTO] = []
    total_results: int = 0
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# VISUAL SEARCH SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class VisualSearchService:
    """Visual search service with AI attribute detection."""
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    SUPPORTED_CATEGORIES = [
        "tops", "bottoms", "dresses", "outerwear", "footwear",
        "accessories", "bags", "jewelry", "activewear", "swimwear"
    ]
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._search: Optional[ElasticsearchService] = None
        self._celery_app = None
    
    @property
    def celery_app(self):
        """Get Celery app for async tasks."""
        if self._celery_app is None:
            from workers.celery_app import celery_app
            self._celery_app = celery_app
        return self._celery_app
    
    async def _get_search(self) -> ElasticsearchService:
        """Get Elasticsearch service."""
        if self._search is None:
            self._search = ElasticsearchService(await get_elasticsearch_client())
        return self._search
    
    # ─────────────────────────────────────────────────────────────────────────
    # SEARCH OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def create_search(
        self,
        user_id: Optional[UUID],
        request: VisualSearchRequestDTO,
    ) -> Tuple[Optional[VisualSearchResponseDTO], Optional[str]]:
        """
        Create a new visual search session.
        
        Processing is done asynchronously via Celery.
        """
        # Validate image
        if not request.image_url.startswith(("http://", "https://", "data:")):
            return None, "Invalid image URL"
        
        # Create session
        session = VisualSearchSessionModel(
            user_id=str(user_id) if user_id else None,
            image_url=request.image_url,
            status=VisualSearchStatus.PENDING.value,
        )
        
        self.session.add(session)
        await self.session.flush()
        await self.session.refresh(session)
        
        # Queue async processing task
        task = self.celery_app.send_task(
            "workers.visual_search_tasks.process_visual_search",
            args=[str(session.id)],
            kwargs={
                "filters": {
                    "category": request.category_filter,
                    "color": request.color_filter,
                    "style_tags": request.style_filter,
                    "price_min": request.price_min,
                    "price_max": request.price_max,
                },
                "limit": request.limit,
            },
            queue="search",
        )
        
        session.task_id = task.id
        await self.session.flush()
        
        logger.info(f"Visual search session created: {session.id}")
        
        return self._to_dto(session), None
    
    async def get_search(self, session_id: UUID) -> Optional[VisualSearchResponseDTO]:
        """Get search session by ID."""
        session = await self._get_session(session_id)
        return self._to_dto(session) if session else None
    
    async def get_user_searches(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Get user's search history."""
        query = select(VisualSearchSessionModel).where(
            VisualSearchSessionModel.user_id == str(user_id)
        )
        
        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(VisualSearchSessionModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.session.execute(query)
        sessions = result.scalars().all()
        
        return {
            "items": [self._to_dto(s) for s in sessions],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # PROCESSING (Called by Celery workers)
    # ─────────────────────────────────────────────────────────────────────────
    
    async def process_search(
        self,
        session_id: UUID,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
    ) -> None:
        """
        Process visual search (called by Celery worker).
        """
        session = await self._get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return
        
        start_time = datetime.now(timezone.utc)
        session.status = VisualSearchStatus.PROCESSING.value
        session.processing_started_at = start_time
        await self.session.flush()
        
        try:
            # Step 1: Detect attributes from image
            attributes = await self._detect_attributes(session.image_url)
            
            # Store detected attributes
            session.detected_category = attributes.category
            session.detected_color = attributes.color
            session.detected_style = ", ".join(attributes.style_tags) if attributes.style_tags else None
            session.detected_pattern = attributes.pattern
            session.detected_attributes = attributes.dict()
            
            # Step 2: Search for similar products
            search_results = await self._search_similar_products(
                attributes=attributes,
                filters=filters,
                limit=limit,
            )
            
            # Step 3: Store results
            session.results = [
                {
                    "product_id": r.product_id,
                    "similarity_score": r.similarity_score,
                    "match_attributes": r.match_attributes,
                }
                for r in search_results
            ]
            
            session.status = VisualSearchStatus.COMPLETED.value
            session.processing_completed_at = datetime.now(timezone.utc)
            session.processing_time_ms = int(
                (session.processing_completed_at - start_time).total_seconds() * 1000
            )
            
            await self.session.flush()
            
            logger.info(f"Visual search completed: {session_id}")
            
        except Exception as e:
            logger.error(f"Visual search failed: {session_id} - {e}")
            session.status = VisualSearchStatus.FAILED.value
            session.error_message = str(e)
            session.processing_completed_at = datetime.now(timezone.utc)
            await self.session.flush()
    
    # ─────────────────────────────────────────────────────────────────────────
    # ATTRIBUTE DETECTION
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _detect_attributes(self, image_url: str) -> DetectedAttributesDTO:
        """
        Detect attributes from image using AI.
        
        In production, this would call:
        - Computer vision models (ResNet, EfficientNet)
        - Object detection (YOLO, Faster R-CNN)
        - Color extraction
        - Style classification
        """
        # Simulated AI detection (replace with actual model inference)
        # In production, integrate with:
        # - TensorFlow/PyTorch models
        # - Google Vision API
        # - AWS Rekognition
        # - Azure Computer Vision
        
        attributes = DetectedAttributesDTO(
            category=self._detect_category(image_url),
            category_confidence=0.92,
            color=self._detect_color(image_url),
            color_hex="#1a1a2e",
            color_confidence=0.88,
            style_tags=self._detect_style(image_url),
            style_confidence=0.85,
            pattern=self._detect_pattern(image_url),
            pattern_confidence=0.80,
            material=self._detect_material(image_url),
            material_confidence=0.75,
            occasion_tags=["casual", "everyday"],
            season_tags=["all-season"],
            attributes={
                "sleeve_length": "long",
                "neckline": "crew",
                "fit": "regular",
            }
        )
        
        return attributes
    
    def _detect_category(self, image_url: str) -> str:
        """Detect product category from image."""
        # Placeholder - in production use ML model
        return "tops"
    
    def _detect_color(self, image_url: str) -> str:
        """Detect dominant color from image."""
        # Placeholder - in production use color extraction
        return "black"
    
    def _detect_style(self, image_url: str) -> List[str]:
        """Detect style tags from image."""
        # Placeholder - in production use style classifier
        return ["minimalist", "classic"]
    
    def _detect_pattern(self, image_url: str) -> str:
        """Detect pattern from image."""
        # Placeholder
        return "solid"
    
    def _detect_material(self, image_url: str) -> str:
        """Detect material from image."""
        # Placeholder
        return "cotton"
    
    # ─────────────────────────────────────────────────────────────────────────
    # SIMILARITY SEARCH
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _search_similar_products(
        self,
        attributes: DetectedAttributesDTO,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
    ) -> List[SearchResultDTO]:
        """Search for similar products based on detected attributes."""
        search = await self._get_search()
        
        # Build search query
        search_filters = {
            "status": "active",
        }
        
        # Apply detected attributes
        if attributes.category:
            search_filters["category_id"] = attributes.category
        
        if attributes.color:
            search_filters["color"] = attributes.color
        
        if attributes.style_tags:
            search_filters["style_tags"] = attributes.style_tags
        
        # Apply user filters
        if filters:
            if filters.get("category"):
                search_filters["category_id"] = filters["category"]
            if filters.get("color"):
                search_filters["color"] = filters["color"]
            if filters.get("style_tags"):
                search_filters["style_tags"] = filters["style_tags"]
            if filters.get("price_min"):
                search_filters["price_min"] = filters["price_min"]
            if filters.get("price_max"):
                search_filters["price_max"] = filters["price_max"]
        
        # Execute search
        result = await search.search_products(
            query="",
            filters=search_filters,
            page=1,
            page_size=limit,
        )
        
        hits = result.get("hits", {}).get("hits", [])
        
        # Convert to DTOs with similarity scores
        results = []
        for i, hit in enumerate(hits):
            source = hit.get("_source", {})
            
            # Calculate similarity score based on attribute matching
            similarity = self._calculate_similarity(attributes, source)
            
            results.append(SearchResultDTO(
                product_id=source.get("id", ""),
                name=source.get("name", ""),
                slug=source.get("slug", ""),
                brand_name=source.get("brand_name"),
                category_name=source.get("category_name"),
                image_url=source.get("primary_image_url"),
                price=source.get("current_price", 0),
                currency=source.get("currency", "USD"),
                similarity_score=similarity,
                match_attributes={
                    "category_match": attributes.category == source.get("category_name"),
                    "color_match": attributes.color == source.get("color"),
                    "style_match": bool(set(attributes.style_tags) & set(source.get("style_tags", []))),
                }
            ))
        
        # Sort by similarity
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return results
    
    def _calculate_similarity(
        self,
        detected: DetectedAttributesDTO,
        product: Dict[str, Any]
    ) -> float:
        """Calculate similarity score between detected attributes and product."""
        score = 0.0
        max_score = 100.0
        
        # Category match (30 points)
        if detected.category and detected.category == product.get("category_name"):
            score += 30.0
        
        # Color match (25 points)
        if detected.color and detected.color == product.get("color"):
            score += 25.0
        
        # Style match (25 points)
        if detected.style_tags:
            product_styles = set(product.get("style_tags", []))
            detected_styles = set(detected.style_tags)
            if product_styles & detected_styles:
                score += 25.0 * len(product_styles & detected_styles) / len(detected_styles)
        
        # Pattern match (10 points)
        if detected.pattern and detected.pattern == product.get("pattern"):
            score += 10.0
        
        # Material match (10 points)
        if detected.material and detected.material == product.get("material"):
            score += 10.0
        
        return min(score / max_score, 1.0)
    
    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE METHODS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _get_session(self, session_id: UUID) -> Optional[VisualSearchSessionModel]:
        """Get search session model."""
        query = select(VisualSearchSessionModel).where(
            VisualSearchSessionModel.id == str(session_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    def _to_dto(self, model: VisualSearchSessionModel) -> VisualSearchResponseDTO:
        """Convert model to DTO."""
        detected = None
        if model.detected_attributes:
            detected = DetectedAttributesDTO(**model.detected_attributes)
        
        results = []
        if model.results:
            for r in model.results:
                results.append(SearchResultDTO(
                    product_id=r.get("product_id", ""),
                    name="",  # Would need to load product
                    slug="",
                    image_url=None,
                    price=0,
                    similarity_score=r.get("similarity_score", 0),
                    match_attributes=r.get("match_attributes", {}),
                ))
        
        return VisualSearchResponseDTO(
            id=model.id,
            status=model.status,
            image_url=model.image_url,
            detected_attributes=detected,
            results=results,
            total_results=len(results),
            processing_time_ms=model.processing_time_ms,
            error_message=model.error_message,
            created_at=model.created_at,
        )
