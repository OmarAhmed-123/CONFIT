"""
CONFIT Backend — Style DNA Service
==================================
Unique style fingerprint generation using embeddings and behavioral analysis.
"""

import os
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import json
import asyncio

import numpy as np
from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from models.style_dna_models import (
    StyleDNAProfile,
    StyleVector,
    StylePreference,
    StyleSignal,
    StyleEvolutionHistory,
    StyleCluster,
    UserClusterAssignment,
    StyleSimilarityCache,
    StyleQuizResponse,
    StyleCategory,
    BudgetLevel,
    FitPreference,
    StyleSignalSource,
    StyleDNAResponseDTO,
    StyleDNACreateDTO,
    StyleDNADashboardDTO,
    StyleSimilarityDTO,
    StyleClusterDTO,
    UserClusterAssignmentDTO,
    StyleEvolutionDTO,
    StyleQuizSubmissionDTO,
    StyleQuizResultDTO,
    ColorPreferencesDTO,
    FitPreferencesDTO,
    OccasionPreferencesDTO,
    BrandAffinityDTO,
    BudgetRangeDTO,
    PatternPreferencesDTO,
    FabricPreferencesDTO,
    SilhouettePreferencesDTO,
    SignalSummaryDTO,
    StyleAnalysisResultDTO,
)
from database.models import User, WardrobeItem, Order, OrderItem, Product, Brand

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# EMBEDDING SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class StyleEmbeddingEngine:
    """
    Generates style embeddings from various data sources.
    Uses sentence-transformers for consistent vector representations.
    """
    
    VECTOR_DIMENSIONS = 384  # all-MiniLM-L6-v2 dimensions
    
    # Style attribute weights for embedding composition
    ATTRIBUTE_WEIGHTS = {
        "wardrobe": 0.30,
        "liked_outfits": 0.25,
        "purchases": 0.20,
        "style_quiz": 0.15,
        "browsing": 0.10,
    }
    
    # Style category to text mapping for embedding
    STYLE_DESCRIPTIONS = {
        StyleCategory.CLASSIC: "timeless elegant sophisticated traditional refined polished",
        StyleCategory.TRENDY: "fashionable modern current stylish contemporary fresh latest",
        StyleCategory.MINIMALIST: "clean simple sleek understated neutral essential pared-down",
        StyleCategory.MAXIMALIST: "bold eclectic vibrant expressive dramatic artistic layered",
        StyleCategory.FEMININE: "soft delicate graceful romantic elegant pretty charming",
        StyleCategory.MASCULINE: "structured sharp tailored strong confident powerful sleek",
        StyleCategory.EDGY: "rebellious bold unconventional daring dark alternative street",
        StyleCategory.ROMANTIC: "dreamy whimsical soft floral vintage delicate ethereal",
        StyleCategory.BOHEMIAN: "free-spirited artistic eclectic natural relaxed vintage hippie",
        StyleCategory.PREPPY: "polished classic refined collegiate traditional neat smart",
        StyleCategory.SPORTY: "athletic active casual comfortable functional dynamic energetic",
        StyleCategory.AVANT_GARDE: "experimental innovative artistic unconventional avant-garde unique",
        StyleCategory.STREETWEAR: "urban casual cool trendy relaxed contemporary street-style",
        StyleCategory.VINTAGE: "retro nostalgic classic antique timeless old-school heritage",
        StyleCategory.LUXURY: "premium high-end designer expensive exclusive opulent refined",
        StyleCategory.CASUAL: "relaxed comfortable everyday simple easy effortless laid-back",
    }
    
    def __init__(self):
        self._model = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the embedding model."""
        if self._initialized:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            # Loading transformer models is CPU-heavy; keep event loop responsive.
            self._model = await asyncio.to_thread(SentenceTransformer, 'all-MiniLM-L6-v2')
            self._initialized = True
            logger.info("Style embedding model initialized successfully")
        except Exception as e:
            logger.warning(f"Could not load sentence-transformers model: {e}")
            # Fallback to random embeddings for development
            self._initialized = True
    
    def generate_style_text(self, style_data: Dict[str, Any]) -> str:
        """
        Convert style data to text for embedding generation.
        Creates a rich textual representation of user's style.
        """
        parts = []
        
        # Primary style
        primary = style_data.get("primary_style")
        if primary:
            parts.append(self.STYLE_DESCRIPTIONS.get(primary, str(primary)))
        
        # Secondary styles
        for style in style_data.get("secondary_styles", []):
            parts.append(self.STYLE_DESCRIPTIONS.get(style, str(style)))
        
        # Color preferences
        colors = style_data.get("color_preferences", {})
        if colors.get("primary"):
            parts.append(f"favorite colors: {' '.join(colors['primary'][:5])}")
        if colors.get("undertone"):
            parts.append(f"{colors['undertone']} undertone")
        
        # Fit preference
        fit = style_data.get("fit_preference", "regular")
        parts.append(f"{fit} fit")
        
        # Occasion preferences
        occasions = style_data.get("occasion_preferences", {})
        top_occasions = sorted(occasions.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_occasions:
            parts.append(f"wears for: {', '.join(o[0] for o in top_occasions)}")
        
        # Brand affinity
        brands = style_data.get("brand_affinity", [])
        if brands:
            brand_names = [b.get("brand_name", b.get("brand_id", "")) for b in brands[:3]]
            parts.append(f"brands: {', '.join(brand_names)}")
        
        # Budget level
        budget = style_data.get("budget_level", "moderate")
        parts.append(f"{budget} budget")
        
        # Pattern preferences
        patterns = style_data.get("pattern_preferences", {})
        if patterns.get("preferred"):
            parts.append(f"patterns: {', '.join(patterns['preferred'][:3])}")
        
        # Fabric preferences
        fabrics = style_data.get("fabric_preferences", {})
        if fabrics.get("preferred"):
            parts.append(f"fabrics: {', '.join(fabrics['preferred'][:3])}")
        
        return " ".join(parts)
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector from text."""
        await self.initialize()
        
        if self._model is not None:
            try:
                embedding = await asyncio.to_thread(
                    self._model.encode,
                    text,
                    convert_to_numpy=True,
                )
                return embedding.tolist()
            except Exception as e:
                logger.error(f"Error generating embedding: {e}")
        
        # Fallback: deterministic pseudo-embedding based on text hash
        return self._generate_fallback_embedding(text)
    
    def _generate_fallback_embedding(self, text: str) -> List[float]:
        """Generate deterministic fallback embedding."""
        # Create a hash-based pseudo-embedding
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Use hash to seed random generator for reproducibility
        np.random.seed(int(text_hash[:8], 16))
        
        # Generate normalized random vector
        vec = np.random.randn(self.VECTOR_DIMENSIONS)
        vec = vec / np.linalg.norm(vec)
        
        return vec.tolist()
    
    def combine_embeddings(
        self,
        embeddings: List[Tuple[List[float], float]]
    ) -> List[float]:
        """
        Combine multiple embeddings with weights.
        
        Args:
            embeddings: List of (embedding, weight) tuples
        
        Returns:
            Combined normalized embedding
        """
        if not embeddings:
            return [0.0] * self.VECTOR_DIMENSIONS
        
        # Convert to numpy arrays
        vectors = [np.array(e) * w for e, w in embeddings]
        
        # Weighted sum
        combined = np.sum(vectors, axis=0)
        
        # Normalize
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm
        
        return combined.tolist()
    
    def cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(v1, v2) / (norm1 * norm2))


# ─────────────────────────────────────────────────────────────────────────────
# STYLE DNA SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class StyleDNAService:
    """
    Main service for Style DNA feature.
    Handles profile creation, analysis, and recommendations.
    """
    
    CACHE_TTL = 3600  # 1 hour
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.embedding_engine = StyleEmbeddingEngine()
    
    # ─────────────────────────────────────────────────────────────────────────
    # PROFILE MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_or_create_profile(
        self,
        user_id: UUID,
    ) -> StyleDNAProfile:
        """Get existing profile or create a new one."""
        profile = await self._get_profile(user_id)
        
        if not profile:
            profile = await self._create_profile(user_id)
        
        return profile
    
    async def _get_profile(self, user_id: UUID) -> Optional[StyleDNAProfile]:
        """Get style DNA profile by user ID."""
        query = select(StyleDNAProfile).where(StyleDNAProfile.user_id == str(user_id))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def _create_profile(self, user_id: UUID) -> StyleDNAProfile:
        """Create a new style DNA profile."""
        profile = StyleDNAProfile(
            user_id=str(user_id),
            primary_style=StyleCategory.CASUAL,
            secondary_styles=[],
            style_confidence=Decimal("0.0"),
            color_preferences={
                "primary": [],
                "secondary": [],
                "avoided": [],
                "undertone": None,
                "palette_type": None,
            },
            fit_preference=FitPreference.REGULAR,
            brand_affinity=[],
            budget_level=BudgetLevel.MODERATE,
            profile_completeness=Decimal("0.0"),
        )
        
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        
        logger.info(f"Created new Style DNA profile for user {user_id}")
        
        return profile
    
    async def update_profile(
        self,
        user_id: UUID,
        update_data: StyleDNACreateDTO,
    ) -> StyleDNAProfile:
        """Update style DNA profile with new data."""
        profile = await self.get_or_create_profile(user_id)
        
        # Track changes for evolution history
        changes = []
        
        if update_data.primary_style and update_data.primary_style != profile.primary_style:
            changes.append({
                "change_type": "primary_style",
                "previous_value": {"style": str(profile.primary_style)},
                "new_value": {"style": str(update_data.primary_style)},
            })
            profile.primary_style = update_data.primary_style
        
        if update_data.secondary_styles:
            profile.secondary_styles = update_data.secondary_styles
        
        if update_data.color_preferences:
            profile.color_preferences = update_data.color_preferences.model_dump()
        
        if update_data.fit_preference:
            profile.fit_preference = update_data.fit_preference
        
        if update_data.fit_preferences:
            profile.fit_preferences = update_data.fit_preferences.model_dump()
        
        if update_data.occasion_preferences:
            profile.occasion_preferences = update_data.occasion_preferences.model_dump()
        
        if update_data.brand_affinity:
            profile.brand_affinity = [b.model_dump() for b in update_data.brand_affinity]
        
        if update_data.budget_level:
            profile.budget_level = update_data.budget_level
        
        if update_data.budget_range:
            profile.budget_range = update_data.budget_range.model_dump()
        
        if update_data.pattern_preferences:
            profile.pattern_preferences = update_data.pattern_preferences.model_dump()
        
        if update_data.fabric_preferences:
            profile.fabric_preferences = update_data.fabric_preferences.model_dump()
        
        if update_data.silhouette_preferences:
            profile.silhouette_preferences = update_data.silhouette_preferences.model_dump()
        
        # Record evolution
        for change in changes:
            await self._record_evolution(
                user_id=user_id,
                change_type=change["change_type"],
                previous_value=change["previous_value"],
                new_value=change["new_value"],
                trigger_source="manual_update",
            )
        
        # Recalculate profile completeness
        profile.profile_completeness = Decimal(str(await self._calculate_completeness(profile)))
        profile.profile_version += 1
        profile.updated_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        await self.session.refresh(profile)
        
        return profile
    
    async def _calculate_completeness(self, profile: StyleDNAProfile) -> float:
        """Calculate profile completeness percentage."""
        score = 0.0
        
        # Primary style (20%)
        if profile.primary_style:
            score += 0.20
        
        # Style vector (20%)
        if profile.style_vector is not None:
            score += 0.20
        
        # Color preferences (15%)
        colors = profile.color_preferences or {}
        if colors.get("primary") and len(colors["primary"]) > 0:
            score += 0.15
        
        # Brand affinity (15%)
        brands = profile.brand_affinity or []
        if len(brands) > 0:
            score += 0.15
        
        # Occasion preferences (10%)
        if profile.occasion_preferences:
            score += 0.10
        
        # Budget level (10%)
        if profile.budget_level:
            score += 0.10
        
        # Fit preference (5%)
        if profile.fit_preference:
            score += 0.05
        
        # Pattern preferences (5%)
        patterns = profile.pattern_preferences or {}
        if patterns.get("preferred") and len(patterns["preferred"]) > 0:
            score += 0.05
        
        return score * 100
    
    # ─────────────────────────────────────────────────────────────────────────
    # STYLE ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def analyze_user_style(
        self,
        user_id: UUID,
        force_refresh: bool = False,
    ) -> StyleAnalysisResultDTO:
        """
        Perform comprehensive style analysis for a user.
        
        Analyzes:
        - Wardrobe items
        - Liked outfits
        - Purchase history
        - Style quiz answers
        - Browsing behavior
        """
        profile = await self.get_or_create_profile(user_id)
        
        # Check if we need to refresh
        last_analyzed = profile.signal_summary.get("last_analyzed")
        if not force_refresh and last_analyzed:
            last_time = datetime.fromisoformat(last_analyzed.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - last_time < timedelta(hours=24):
                # Return cached analysis
                return await self._build_analysis_result(profile)
        
        # Analyze each data source
        wardrobe_data = await self._analyze_wardrobe(user_id)
        purchase_data = await self._analyze_purchases(user_id)
        quiz_data = await self._analyze_quiz(user_id)
        browsing_data = await self._analyze_browsing(user_id)
        
        # Combine all signals
        all_signals = []
        all_signals.extend(wardrobe_data.get("signals", []))
        all_signals.extend(purchase_data.get("signals", []))
        all_signals.extend(quiz_data.get("signals", []))
        all_signals.extend(browsing_data.get("signals", []))
        
        # Generate style embedding
        style_text = self.embedding_engine.generate_style_text({
            "primary_style": profile.primary_style,
            "secondary_styles": profile.secondary_styles,
            "color_preferences": profile.color_preferences,
            "fit_preference": profile.fit_preference,
            "occasion_preferences": profile.occasion_preferences,
            "brand_affinity": profile.brand_affinity,
            "budget_level": profile.budget_level,
            "pattern_preferences": profile.pattern_preferences,
            "fabric_preferences": profile.fabric_preferences,
        })
        
        style_vector = await self.embedding_engine.generate_embedding(style_text)
        
        # Update profile with analysis results
        profile.style_vector = style_vector
        profile.style_confidence = Decimal(str(self._calculate_confidence(all_signals)))
        profile.signal_summary = {
            "wardrobe_items": wardrobe_data.get("count", 0),
            "liked_outfits": 0,  # TODO: implement liked outfits
            "purchases": purchase_data.get("count", 0),
            "quiz_answers": quiz_data.get("count", 0),
            "browsing_events": browsing_data.get("count", 0),
            "last_analyzed": datetime.now(timezone.utc).isoformat(),
        }
        
        # Determine primary style from signals
        detected_styles = await self._detect_primary_style(all_signals)
        if detected_styles.get("primary"):
            if profile.primary_style != detected_styles["primary"]:
                await self._record_evolution(
                    user_id=user_id,
                    change_type="primary_style_detected",
                    previous_value={"style": str(profile.primary_style)},
                    new_value={"style": str(detected_styles["primary"])},
                    trigger_source="style_analysis",
                )
            profile.primary_style = detected_styles["primary"]
            profile.secondary_styles = detected_styles.get("secondary", [])
        
        # Update color preferences from analysis
        color_prefs = await self._analyze_color_preferences(all_signals)
        if color_prefs:
            profile.color_preferences = color_prefs
        
        # Update brand affinity from analysis
        brand_prefs = await self._analyze_brand_affinity(all_signals)
        if brand_prefs:
            profile.brand_affinity = brand_prefs
        
        # Update budget level from analysis
        budget_level = await self._analyze_budget_level(all_signals)
        if budget_level:
            profile.budget_level = budget_level
        
        # Update profile completeness
        profile.profile_completeness = Decimal(str(await self._calculate_completeness(profile)))
        profile.updated_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        await self.session.refresh(profile)
        
        # Store historical vector
        await self._store_style_vector(user_id, style_vector, "full_analysis")
        
        # Assign to cluster
        await self._assign_to_cluster(user_id, style_vector)
        
        return await self._build_analysis_result(profile)
    
    async def _analyze_wardrobe(self, user_id: UUID) -> Dict[str, Any]:
        """Analyze wardrobe items for style signals."""
        query = select(WardrobeItem).where(
            WardrobeItem.owner_user_id == str(user_id),
            WardrobeItem.is_active == True,
        )
        
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        signals = []
        colors = {}
        brands = {}
        categories = {}
        styles = {}
        
        for item in items:
            # Color signals
            if item.color:
                colors[item.color] = colors.get(item.color, 0) + 1
            
            # Brand signals
            if item.brand:
                brands[item.brand] = brands.get(item.brand, 0) + 1
            
            # Category signals
            if item.category:
                categories[item.category] = categories.get(item.category, 0) + 1
            
            # Style tags
            if item.tags:
                for tag in item.tags:
                    if tag.get("type") == "style":
                        style_name = tag.get("value")
                        styles[style_name] = styles.get(style_name, 0) + 1
            
            # Create signal
            signals.append({
                "signal_type": "wardrobe_item",
                "signal_category": "possession",
                "entity_type": "wardrobe_item",
                "entity_id": item.id,
                "signal_data": {
                    "color": item.color,
                    "brand": item.brand,
                    "category": item.category,
                    "price": float(item.price) if item.price else None,
                },
                "base_weight": 0.8,
            })
        
        return {
            "count": len(items),
            "signals": signals,
            "colors": colors,
            "brands": brands,
            "categories": categories,
            "styles": styles,
        }
    
    async def _analyze_purchases(self, user_id: UUID) -> Dict[str, Any]:
        """Analyze purchase history for style signals."""
        query = (
            select(OrderItem, Product)
            .join(Product, Product.id == OrderItem.product_id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.user_id == str(user_id),
                Order.status.in_(["completed", "delivered"]),
            )
            .order_by(Order.created_at.desc())
            .limit(50)
        )
        
        result = await self.session.execute(query)
        purchases = result.all()
        
        signals = []
        brands = {}
        categories = {}
        price_points = []
        
        for item, product in purchases:
            # Brand signals
            if product.brand_id:
                brands[product.brand_id] = brands.get(product.brand_id, 0) + 1
            
            # Category signals
            if product.category:
                categories[product.category] = categories.get(product.category, 0) + 1
            
            # Price tracking
            if item.price:
                price_points.append(float(item.price))
            
            # Create signal
            signals.append({
                "signal_type": "purchase",
                "signal_category": "transaction",
                "entity_type": "product",
                "entity_id": product.id,
                "signal_data": {
                    "brand_id": product.brand_id,
                    "category": product.category,
                    "color": product.color,
                    "price": float(item.price) if item.price else None,
                },
                "base_weight": 1.0,  # Purchases have highest weight
            })
        
        return {
            "count": len(purchases),
            "signals": signals,
            "brands": brands,
            "categories": categories,
            "price_points": price_points,
        }
    
    async def _analyze_quiz(self, user_id: UUID) -> Dict[str, Any]:
        """Analyze style quiz responses."""
        query = select(StyleQuizResponse).where(
            StyleQuizResponse.user_id == str(user_id)
        )
        
        result = await self.session.execute(query)
        responses = result.scalars().all()
        
        signals = []
        answer_count = 0
        
        for response in responses:
            for answer in response.responses:
                answer_count += 1
                
                signals.append({
                    "signal_type": "quiz_answer",
                    "signal_category": "explicit",
                    "entity_type": "quiz_question",
                    "entity_id": answer.get("question_id"),
                    "signal_data": answer,
                    "base_weight": 0.9,  # Explicit preferences are strong signals
                })
        
        return {
            "count": answer_count,
            "signals": signals,
        }
    
    async def _analyze_browsing(self, user_id: UUID) -> Dict[str, Any]:
        """Analyze browsing behavior for style signals."""
        query = select(StyleSignal).where(
            StyleSignal.user_id == str(user_id),
            StyleSignal.signal_type == "browsing",
            StyleSignal.created_at >= datetime.now(timezone.utc) - timedelta(days=30),
        )
        
        result = await self.session.execute(query)
        signals = result.scalars().all()
        
        browsing_signals = []
        
        for signal in signals:
            browsing_signals.append({
                "signal_type": "browsing_event",
                "signal_category": "behavioral",
                "entity_type": signal.entity_type,
                "entity_id": signal.entity_id,
                "signal_data": signal.signal_data,
                "base_weight": float(signal.base_weight) * 0.5,  # Decay browsing signals
            })
        
        return {
            "count": len(signals),
            "signals": browsing_signals,
        }
    
    def _calculate_confidence(self, signals: List[Dict]) -> float:
        """Calculate confidence score based on signal quantity and quality."""
        if not signals:
            return 0.0
        
        total_weight = sum(s.get("base_weight", 0.5) for s in signals)
        
        # Normalize based on expected signal count
        expected_signals = 50  # Minimum for high confidence
        signal_ratio = min(len(signals) / expected_signals, 1.0)
        
        # Weighted confidence
        confidence = (signal_ratio * 0.5) + (min(total_weight / 30, 1.0) * 0.5)
        
        return min(confidence, 1.0)
    
    async def _detect_primary_style(
        self,
        signals: List[Dict],
    ) -> Dict[str, Any]:
        """Detect primary and secondary styles from signals."""
        style_scores = {}
        
        for signal in signals:
            data = signal.get("signal_data", {})
            
            # Check for explicit style selections
            if "style" in data:
                style = data["style"]
                style_scores[style] = style_scores.get(style, 0) + signal.get("base_weight", 0.5)
            
            # Infer from category
            category = data.get("category", "")
            if category:
                inferred_styles = self._infer_style_from_category(category)
                for style, weight in inferred_styles.items():
                    style_scores[style] = style_scores.get(style, 0) + weight * signal.get("base_weight", 0.5)
        
        if not style_scores:
            return {"primary": StyleCategory.CASUAL, "secondary": []}
        
        # Sort by score
        sorted_styles = sorted(style_scores.items(), key=lambda x: x[1], reverse=True)
        
        primary = sorted_styles[0][0] if sorted_styles else StyleCategory.CASUAL
        
        # Convert string to enum if needed
        if isinstance(primary, str):
            try:
                primary = StyleCategory(primary.lower())
            except ValueError:
                primary = StyleCategory.CASUAL
        
        secondary = []
        for style, score in sorted_styles[1:4]:
            if isinstance(style, str):
                try:
                    secondary.append(StyleCategory(style.lower()))
                except ValueError:
                    pass
            else:
                secondary.append(style)
        
        return {
            "primary": primary,
            "secondary": secondary[:3],
        }
    
    def _infer_style_from_category(self, category: str) -> Dict[str, float]:
        """Infer style preferences from product category."""
        category_style_map = {
            "suits": {"classic": 0.9, "formal": 0.8},
            "t-shirts": {"casual": 0.8, "streetwear": 0.6},
            "dresses": {"feminine": 0.7, "romantic": 0.5},
            "jeans": {"casual": 0.8, "streetwear": 0.5},
            "blazers": {"classic": 0.7, "preppy": 0.6},
            "sneakers": {"streetwear": 0.8, "sporty": 0.6},
            "heels": {"feminine": 0.7, "luxury": 0.5},
            "boots": {"edgy": 0.7, "casual": 0.5},
            "activewear": {"sporty": 0.9, "casual": 0.4},
            "vintage": {"vintage": 0.9, "bohemian": 0.5},
        }
        
        return category_style_map.get(category.lower(), {})
    
    async def _analyze_color_preferences(
        self,
        signals: List[Dict],
    ) -> Optional[Dict[str, Any]]:
        """Analyze color preferences from signals."""
        color_counts = {}
        
        for signal in signals:
            data = signal.get("signal_data", {})
            color = data.get("color")
            
            if color:
                color_counts[color] = color_counts.get(color, 0) + signal.get("base_weight", 0.5)
        
        if not color_counts:
            return None
        
        # Sort by frequency
        sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
        
        primary = [c[0] for c in sorted_colors[:5]]
        secondary = [c[0] for c in sorted_colors[5:10]]
        
        return {
            "primary": primary,
            "secondary": secondary,
            "avoided": [],
            "undertone": self._detect_undertone(primary),
            "palette_type": self._detect_palette_type(primary),
        }
    
    def _detect_undertone(self, colors: List[str]) -> Optional[str]:
        """Detect skin undertone preference from colors."""
        warm_colors = {"red", "orange", "yellow", "coral", "peach", "cream", "gold", "brown"}
        cool_colors = {"blue", "purple", "green", "pink", "silver", "gray", "navy"}
        
        warm_count = sum(1 for c in colors if c.lower() in warm_colors)
        cool_count = sum(1 for c in colors if c.lower() in cool_colors)
        
        if warm_count > cool_count * 1.5:
            return "warm"
        elif cool_count > warm_count * 1.5:
            return "cool"
        else:
            return "neutral"
    
    def _detect_palette_type(self, colors: List[str]) -> str:
        """Detect color palette type."""
        neutral_colors = {"black", "white", "gray", "navy", "beige", "brown"}
        
        neutral_count = sum(1 for c in colors if c.lower() in neutral_colors)
        
        if neutral_count >= len(colors) * 0.7:
            return "neutral"
        elif neutral_count >= len(colors) * 0.4:
            return "mixed"
        else:
            return "colorful"
    
    async def _analyze_brand_affinity(
        self,
        signals: List[Dict],
    ) -> List[Dict[str, Any]]:
        """Analyze brand affinity from signals."""
        brand_scores = {}
        
        for signal in signals:
            data = signal.get("signal_data", {})
            brand_id = data.get("brand_id") or data.get("brand")
            
            if brand_id:
                weight = signal.get("base_weight", 0.5)
                brand_scores[brand_id] = brand_scores.get(brand_id, 0) + weight
        
        if not brand_scores:
            return []
        
        # Normalize scores
        max_score = max(brand_scores.values())
        
        affinities = []
        for brand_id, score in sorted(brand_scores.items(), key=lambda x: x[1], reverse=True)[:10]:
            affinities.append({
                "brand_id": brand_id,
                "affinity_score": min(score / max_score, 1.0),
            })
        
        return affinities
    
    async def _analyze_budget_level(
        self,
        signals: List[Dict],
    ) -> Optional[BudgetLevel]:
        """Analyze budget level from price signals."""
        prices = []
        
        for signal in signals:
            data = signal.get("signal_data", {})
            price = data.get("price")
            
            if price and price > 0:
                prices.append(price)
        
        if not prices:
            return None
        
        avg_price = sum(prices) / len(prices)
        
        if avg_price < 50:
            return BudgetLevel.BUDGET_CONSCIOUS
        elif avg_price < 150:
            return BudgetLevel.MODERATE
        elif avg_price < 500:
            return BudgetLevel.PREMIUM
        elif avg_price < 1500:
            return BudgetLevel.LUXURY
        else:
            return BudgetLevel.ULTRA_LUXURY
    
    async def _build_analysis_result(
        self,
        profile: StyleDNAProfile,
    ) -> StyleAnalysisResultDTO:
        """Build complete analysis result DTO."""
        # Get cluster assignment
        cluster_assignment = await self._get_cluster_assignment(UUID(profile.user_id))
        
        # Get similar users
        similar_users = await self._find_similar_users(UUID(profile.user_id))
        
        # Get evolution history
        evolution = await self._get_evolution_history(UUID(profile.user_id))
        
        return StyleAnalysisResultDTO(
            profile=self._profile_to_dto(profile),
            cluster_assignment=cluster_assignment,
            similar_users=similar_users,
            style_evolution=evolution,
            recommendations=await self._generate_style_recommendations(profile),
        )
    
    def _profile_to_dto(self, profile: StyleDNAProfile) -> StyleDNAResponseDTO:
        """Convert profile to DTO."""
        return StyleDNAResponseDTO(
            id=str(profile.id),
            user_id=str(profile.user_id),
            primary_style=profile.primary_style,
            secondary_styles=list(profile.secondary_styles or []),
            style_confidence=float(profile.style_confidence),
            color_preferences=ColorPreferencesDTO(**(profile.color_preferences or {})),
            fit_preference=profile.fit_preference,
            fit_preferences=FitPreferencesDTO(**(profile.fit_preferences or {})),
            occasion_preferences=OccasionPreferencesDTO(**(profile.occasion_preferences or {})),
            brand_affinity=[BrandAffinityDTO(**b) for b in (profile.brand_affinity or [])],
            budget_level=profile.budget_level,
            budget_range=BudgetRangeDTO(**(profile.budget_range or {})),
            pattern_preferences=PatternPreferencesDTO(**(profile.pattern_preferences or {})),
            fabric_preferences=FabricPreferencesDTO(**(profile.fabric_preferences or {})),
            silhouette_preferences=SilhouettePreferencesDTO(**(profile.silhouette_preferences or {})),
            signal_summary=SignalSummaryDTO(**(profile.signal_summary or {})),
            profile_completeness=float(profile.profile_completeness),
            profile_version=profile.profile_version,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # SIMILARITY & CLUSTERING
    # ─────────────────────────────────────────────────────────────────────────
    
    async def find_similar_users(
        self,
        user_id: UUID,
        limit: int = 10,
        min_similarity: float = 0.7,
    ) -> List[StyleSimilarityDTO]:
        """Find users with similar style DNA."""
        return await self._find_similar_users(user_id, limit, min_similarity)
    
    async def _find_similar_users(
        self,
        user_id: UUID,
        limit: int = 10,
        min_similarity: float = 0.7,
    ) -> List[StyleSimilarityDTO]:
        """Internal method to find similar users."""
        # Get user's profile
        profile = await self._get_profile(user_id)
        
        if not profile or not profile.style_vector:
            return []
        
        user_vector = profile.style_vector
        
        # Find similar profiles using vector similarity
        # Using raw SQL for pgvector operations
        query = """
            SELECT 
                user_id,
                1 - (style_vector <=> :vector) as similarity,
                primary_style,
                secondary_styles,
                brand_affinity,
                color_preferences
            FROM style_dna_profiles
            WHERE user_id != :user_id
              AND style_vector IS NOT NULL
              AND 1 - (style_vector <=> :vector) >= :min_similarity
            ORDER BY similarity DESC
            LIMIT :limit
        """
        
        result = await self.session.execute(
            query,
            {
                "user_id": str(user_id),
                "vector": str(user_vector),
                "min_similarity": min_similarity,
                "limit": limit,
            }
        )
        
        similar_users = []
        for row in result:
            similar_users.append(StyleSimilarityDTO(
                user_id=row.user_id,
                similarity=float(row.similarity),
                shared_styles=list(row.secondary_styles or []),
                shared_brands=[b.get("brand_id") for b in (row.brand_affinity or [])],
                shared_colors=[c for c in (row.color_preferences or {}).get("primary", [])],
            ))
        
        return similar_users
    
    async def _assign_to_cluster(
        self,
        user_id: UUID,
        style_vector: List[float],
    ) -> Optional[UserClusterAssignment]:
        """Assign user to the most similar style cluster."""
        # Find nearest cluster
        query = """
            SELECT 
                id,
                cluster_name,
                1 - (centroid_vector <=> :vector) as distance
            FROM style_clusters
            WHERE is_active = TRUE
            ORDER BY distance ASC
            LIMIT 1
        """
        
        result = await self.session.execute(
            query,
            {"vector": str(style_vector)}
        )
        
        row = result.fetchone()
        
        if not row:
            return None
        
        cluster_id = row.id
        distance = float(row.distance)
        
        # Deactivate previous assignments
        await self.session.execute(
            update(UserClusterAssignment)
            .where(
                UserClusterAssignment.user_id == str(user_id),
                UserClusterAssignment.is_current == True,
            )
            .values(is_current=False, valid_until=datetime.now(timezone.utc))
        )
        
        # Create new assignment
        assignment = UserClusterAssignment(
            user_id=str(user_id),
            cluster_id=cluster_id,
            distance_to_centroid=Decimal(str(1 - distance)),
            assignment_confidence=Decimal(str(distance)),
            is_current=True,
        )
        
        self.session.add(assignment)
        await self.session.commit()
        
        return assignment
    
    async def _get_cluster_assignment(
        self,
        user_id: UUID,
    ) -> Optional[UserClusterAssignmentDTO]:
        """Get user's current cluster assignment."""
        query = (
            select(UserClusterAssignment, StyleCluster)
            .join(StyleCluster, StyleCluster.id == UserClusterAssignment.cluster_id)
            .where(
                UserClusterAssignment.user_id == str(user_id),
                UserClusterAssignment.is_current == True,
            )
        )
        
        result = await self.session.execute(query)
        row = result.fetchone()
        
        if not row:
            return None
        
        assignment, cluster = row
        
        return UserClusterAssignmentDTO(
            cluster=StyleClusterDTO(
                id=str(cluster.id),
                cluster_name=cluster.cluster_name,
                cluster_description=cluster.cluster_description,
                dominant_styles=list(cluster.dominant_styles or []),
                dominant_colors=list(cluster.dominant_colors or []),
                cluster_size=cluster.cluster_size,
            ),
            distance_to_centroid=float(assignment.distance_to_centroid),
            assignment_confidence=float(assignment.assignment_confidence),
            secondary_clusters=list(assignment.secondary_clusters or []),
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # EVOLUTION TRACKING
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _record_evolution(
        self,
        user_id: UUID,
        change_type: str,
        previous_value: Optional[Dict],
        new_value: Dict,
        trigger_source: str,
    ) -> StyleEvolutionHistory:
        """Record a style evolution event."""
        evolution = StyleEvolutionHistory(
            user_id=str(user_id),
            change_type=change_type,
            previous_value=previous_value,
            new_value=new_value,
            trigger_source=trigger_source,
        )
        
        self.session.add(evolution)
        await self.session.flush()
        
        return evolution
    
    async def _get_evolution_history(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> List[StyleEvolutionDTO]:
        """Get style evolution history for a user."""
        query = (
            select(StyleEvolutionHistory)
            .where(StyleEvolutionHistory.user_id == str(user_id))
            .order_by(StyleEvolutionHistory.created_at.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        events = result.scalars().all()
        
        return [
            StyleEvolutionDTO(
                id=str(e.id),
                user_id=str(e.user_id),
                change_type=e.change_type,
                previous_value=e.previous_value,
                new_value=e.new_value,
                drift_magnitude=float(e.drift_magnitude) if e.drift_magnitude else None,
                trigger_source=e.trigger_source,
                created_at=e.created_at,
            )
            for e in events
        ]
    
    async def _store_style_vector(
        self,
        user_id: UUID,
        vector: List[float],
        reason: str,
    ) -> StyleVector:
        """Store a historical style vector."""
        style_vector = StyleVector(
            user_id=str(user_id),
            vector=vector,
            vector_type="full_profile",
            snapshot_reason=reason,
        )
        
        self.session.add(style_vector)
        await self.session.flush()
        
        return style_vector
    
    # ─────────────────────────────────────────────────────────────────────────
    # STYLE QUIZ
    # ─────────────────────────────────────────────────────────────────────────
    
    async def submit_style_quiz(
        self,
        user_id: UUID,
        submission: StyleQuizSubmissionDTO,
    ) -> StyleQuizResultDTO:
        """Process style quiz submission and update profile."""
        # Store quiz response
        quiz_response = StyleQuizResponse(
            user_id=str(user_id),
            quiz_type=submission.quiz_type,
            responses=[a.model_dump() for a in submission.answers],
            duration_seconds=submission.duration_seconds,
        )
        
        # Compute styles from answers
        computed_styles = await self._compute_styles_from_quiz(submission.answers)
        computed_colors = await self._compute_colors_from_quiz(submission.answers)
        computed_fit = await self._compute_fit_from_quiz(submission.answers)
        
        quiz_response.computed_styles = computed_styles
        quiz_response.computed_colors = computed_colors
        quiz_response.computed_fit = computed_fit
        
        self.session.add(quiz_response)
        
        # Update profile
        profile = await self.get_or_create_profile(user_id)
        
        if computed_styles.get("primary"):
            profile.primary_style = computed_styles["primary"]
            profile.secondary_styles = computed_styles.get("secondary", [])
        
        if computed_colors:
            profile.color_preferences = computed_colors
        
        if computed_fit:
            profile.fit_preference = computed_fit.get("default", FitPreference.REGULAR)
            profile.fit_preferences = computed_fit
        
        profile.profile_completeness = Decimal(str(await self._calculate_completeness(profile)))
        profile.updated_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        
        return StyleQuizResultDTO(
            computed_styles=computed_styles.get("scores", {}),
            computed_colors=computed_colors,
            computed_fit=computed_fit,
            confidence=float(profile.style_confidence),
            profile_updated=True,
        )
    
    async def _compute_styles_from_quiz(
        self,
        answers: List[Any],
    ) -> Dict[str, Any]:
        """Compute style preferences from quiz answers."""
        style_scores = {}
        
        for answer in answers:
            selected = answer.selected_options + answer.image_selections
            
            for option in selected:
                # Map quiz options to style categories
                style_map = {
                    "classic": StyleCategory.CLASSIC,
                    "trendy": StyleCategory.TRENDY,
                    "minimalist": StyleCategory.MINIMALIST,
                    "maximalist": StyleCategory.MAXIMALIST,
                    "feminine": StyleCategory.FEMININE,
                    "masculine": StyleCategory.MASCULINE,
                    "edgy": StyleCategory.EDGY,
                    "romantic": StyleCategory.ROMANTIC,
                    "bohemian": StyleCategory.BOHEMIAN,
                    "preppy": StyleCategory.PREPPY,
                    "sporty": StyleCategory.SPORTY,
                    "streetwear": StyleCategory.STREETWEAR,
                    "vintage": StyleCategory.VINTAGE,
                    "luxury": StyleCategory.LUXURY,
                    "casual": StyleCategory.CASUAL,
                }
                
                if option.lower() in style_map:
                    style = style_map[option.lower()]
                    style_scores[style] = style_scores.get(style, 0) + 1
        
        if not style_scores:
            return {"primary": StyleCategory.CASUAL, "secondary": [], "scores": {}}
        
        sorted_styles = sorted(style_scores.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "primary": sorted_styles[0][0],
            "secondary": [s[0] for s in sorted_styles[1:4]],
            "scores": {str(k): v for k, v in style_scores.items()},
        }
    
    async def _compute_colors_from_quiz(
        self,
        answers: List[Any],
    ) -> Dict[str, Any]:
        """Compute color preferences from quiz answers."""
        colors = []
        
        for answer in answers:
            selected = answer.selected_options + answer.image_selections
            colors.extend([c for c in selected if c.lower() in [
                "black", "white", "gray", "navy", "blue", "red", "green",
                "yellow", "orange", "pink", "purple", "brown", "beige",
            ]])
        
        return {
            "primary": list(set(colors))[:5],
            "secondary": [],
            "avoided": [],
            "undertone": self._detect_undertone(colors[:5]),
            "palette_type": self._detect_palette_type(colors[:5]),
        }
    
    async def _compute_fit_from_quiz(
        self,
        answers: List[Any],
    ) -> Dict[str, str]:
        """Compute fit preferences from quiz answers."""
        fit_counts = {}
        
        for answer in answers:
            for option in answer.selected_options:
                if option.lower() in ["tight", "slim", "regular", "relaxed", "oversized", "loose"]:
                    fit_counts[option.lower()] = fit_counts.get(option.lower(), 0) + 1
        
        if not fit_counts:
            return {"default": "regular"}
        
        most_common = max(fit_counts.items(), key=lambda x: x[1])[0]
        
        return {
            "default": most_common,
            "tops": most_common,
            "bottoms": most_common,
            "dresses": most_common,
            "outerwear": most_common,
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # SIGNAL MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    async def record_signal(
        self,
        user_id: UUID,
        signal_type: str,
        signal_category: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        signal_data: Optional[Dict] = None,
        base_weight: float = 0.5,
        context: Optional[Dict] = None,
    ) -> StyleSignal:
        """Record a style signal for analysis."""
        signal = StyleSignal(
            user_id=str(user_id),
            signal_type=signal_type,
            signal_category=signal_category,
            entity_type=entity_type,
            entity_id=entity_id,
            signal_data=signal_data or {},
            base_weight=Decimal(str(base_weight)),
            computed_weight=Decimal(str(base_weight)),
            context=context or {},
        )
        
        self.session.add(signal)
        await self.session.commit()
        
        return signal
    
    async def process_pending_signals(
        self,
        batch_size: int = 100,
    ) -> int:
        """Process pending style signals."""
        query = (
            select(StyleSignal)
            .where(StyleSignal.is_processed == False)
            .limit(batch_size)
        )
        
        result = await self.session.execute(query)
        signals = result.scalars().all()
        
        processed_count = 0
        
        for signal in signals:
            # Apply decay
            age_days = (datetime.now(timezone.utc) - signal.created_at).days
            decay = max(0.1, 1.0 - (age_days * 0.01))  # 1% decay per day
            signal.decay_factor = Decimal(str(decay))
            signal.computed_weight = signal.base_weight * signal.decay_factor
            signal.is_processed = True
            signal.processed_at = datetime.now(timezone.utc)
            processed_count += 1
        
        await self.session.commit()
        
        return processed_count
    
    # ─────────────────────────────────────────────────────────────────────────
    # RECOMMENDATIONS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _generate_style_recommendations(
        self,
        profile: StyleDNAProfile,
    ) -> Dict[str, Any]:
        """Generate style improvement recommendations."""
        recommendations = {
            "missing_essentials": [],
            "style_evolution": [],
            "color_suggestions": [],
            "brand_discoveries": [],
        }
        
        # Check for missing wardrobe essentials
        if profile.signal_summary.get("wardrobe_items", 0) < 10:
            recommendations["missing_essentials"].append({
                "type": "wardrobe_size",
                "message": "Add more items to your wardrobe for better style analysis",
                "priority": "high",
            })
        
        # Suggest style evolution
        if profile.style_confidence < Decimal("0.5"):
            recommendations["style_evolution"].append({
                "type": "style_quiz",
                "message": "Complete the style quiz to refine your style profile",
                "priority": "medium",
            })
        
        # Color suggestions based on undertone
        if profile.color_preferences.get("undertone"):
            undertone = profile.color_preferences["undertone"]
            if undertone == "warm":
                recommendations["color_suggestions"].append({
                    "colors": ["coral", "peach", "gold", "olive", "cream"],
                    "reason": "These colors complement your warm undertone",
                })
            elif undertone == "cool":
                recommendations["color_suggestions"].append({
                    "colors": ["navy", "silver", "lavender", "rose", "emerald"],
                    "reason": "These colors complement your cool undertone",
                })
        
        # Brand discoveries
        if len(profile.brand_affinity or []) < 3:
            recommendations["brand_discoveries"].append({
                "message": "Explore more brands to discover your favorites",
                "priority": "low",
            })
        
        return recommendations
    
    # ─────────────────────────────────────────────────────────────────────────
    # DASHBOARD DATA
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_dashboard_data(
        self,
        user_id: UUID,
    ) -> StyleDNADashboardDTO:
        """Get complete dashboard data for Style DNA visualization."""
        profile = await self.get_or_create_profile(user_id)
        
        # Ensure profile is analyzed
        if not profile.style_vector:
            await self.analyze_user_style(user_id)
            profile = await self._get_profile(user_id)
        
        # Build style map data
        style_map = self._build_style_map(profile)
        
        # Build color wheel data
        color_wheel = self._build_color_wheel(profile)
        
        # Build brand universe
        brand_universe = self._build_brand_universe(profile)
        
        # Get evolution timeline
        evolution_timeline = await self._get_evolution_history(user_id, 10)
        
        # Generate insights
        style_insights = await self._generate_insights(profile)
        
        # Completeness breakdown
        completeness_breakdown = self._get_completeness_breakdown(profile)
        
        # Get recommendations
        recommendations = await self._generate_style_recommendations(profile)
        
        return StyleDNADashboardDTO(
            profile=self._profile_to_dto(profile),
            style_map=style_map,
            color_wheel=color_wheel,
            brand_universe=brand_universe,
            evolution_timeline=evolution_timeline,
            style_insights=style_insights,
            completeness_breakdown=completeness_breakdown,
            recommendations=recommendations,
        )
    
    def _build_style_map(self, profile: StyleDNAProfile) -> Dict[str, Any]:
        """Build style map visualization data."""
        style_dimensions = [
            ("classic", "trendy"),
            ("minimalist", "maximalist"),
            ("feminine", "masculine"),
            ("edgy", "romantic"),
        ]
        
        return {
            "dimensions": style_dimensions,
            "position": {
                "x": 0.5 if profile.primary_style == StyleCategory.CLASSIC else 0.5,
                "y": 0.5,
            },
            "primary_style": str(profile.primary_style) if profile.primary_style else None,
            "secondary_styles": [str(s) for s in (profile.secondary_styles or [])],
            "confidence": float(profile.style_confidence),
        }
    
    def _build_color_wheel(self, profile: StyleDNAProfile) -> Dict[str, Any]:
        """Build color wheel visualization data."""
        colors = profile.color_preferences or {}
        
        return {
            "primary": colors.get("primary", []),
            "secondary": colors.get("secondary", []),
            "avoided": colors.get("avoided", []),
            "undertone": colors.get("undertone"),
            "palette_type": colors.get("palette_type"),
            "recommended": self._get_recommended_colors(colors.get("undertone")),
        }
    
    def _get_recommended_colors(self, undertone: Optional[str]) -> List[str]:
        """Get recommended colors based on undertone."""
        if undertone == "warm":
            return ["coral", "peach", "gold", "olive", "cream", "rust", "terracotta"]
        elif undertone == "cool":
            return ["navy", "silver", "lavender", "rose", "emerald", "icicle", "powder"]
        else:
            return ["black", "white", "gray", "navy", "beige"]
    
    def _build_brand_universe(self, profile: StyleDNAProfile) -> List[Dict[str, Any]]:
        """Build brand universe visualization data."""
        brands = profile.brand_affinity or []
        
        return [
            {
                "brand_id": b.get("brand_id"),
                "affinity_score": b.get("affinity_score", 0.5),
                "position": {
                    "angle": i * (360 / max(len(brands), 1)),
                    "distance": 1 - b.get("affinity_score", 0.5),
                },
            }
            for i, b in enumerate(brands[:10])
        ]
    
    async def _generate_insights(
        self,
        profile: StyleDNAProfile,
    ) -> List[Dict[str, Any]]:
        """Generate style insights for the user."""
        insights = []
        
        # Style confidence insight
        if profile.style_confidence > Decimal("0.8"):
            insights.append({
                "type": "confidence",
                "title": "Style Confidence High",
                "message": "Your style profile is well-defined and consistent.",
                "icon": "star",
            })
        elif profile.style_confidence < Decimal("0.3"):
            insights.append({
                "type": "confidence",
                "title": "Discover Your Style",
                "message": "Complete your profile to unlock personalized recommendations.",
                "icon": "compass",
            })
        
        # Wardrobe diversity insight
        categories = profile.signal_summary.get("wardrobe_items", 0)
        if categories > 20:
            insights.append({
                "type": "wardrobe",
                "title": "Diverse Wardrobe",
                "message": "You have a well-rounded wardrobe with many options.",
                "icon": "shirt",
            })
        
        # Style evolution insight
        if profile.profile_version > 5:
            insights.append({
                "type": "evolution",
                "title": "Style Evolution",
                "message": "Your style has evolved over time. Keep exploring!",
                "icon": "trending",
            })
        
        return insights
    
    def _get_completeness_breakdown(
        self,
        profile: StyleDNAProfile,
    ) -> Dict[str, float]:
        """Get breakdown of profile completeness."""
        return {
            "style_defined": 20.0 if profile.primary_style else 0.0,
            "vector_generated": 20.0 if profile.style_vector else 0.0,
            "colors_selected": 15.0 if profile.color_preferences.get("primary") else 0.0,
            "brands_added": 15.0 if profile.brand_affinity else 0.0,
            "occasions_set": 10.0 if profile.occasion_preferences else 0.0,
            "budget_defined": 10.0 if profile.budget_level else 0.0,
            "fit_preference": 5.0 if profile.fit_preference else 0.0,
            "patterns_set": 5.0 if profile.pattern_preferences.get("preferred") else 0.0,
        }


# ─────────────────────────────────────────────────────────────────────────────
# STYLE CLUSTERING SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class StyleClusteringService:
    """
    Service for clustering users based on style similarity.
    Uses K-means or hierarchical clustering on style vectors.
    """
    
    NUM_CLUSTERS = 8
    MIN_CLUSTER_SIZE = 100
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def update_clusters(self) -> Dict[str, Any]:
        """
        Update style clusters based on current user vectors.
        Runs periodically to keep clusters up-to-date.
        """
        # Get all active style vectors
        query = """
            SELECT user_id, style_vector
            FROM style_dna_profiles
            WHERE style_vector IS NOT NULL
              AND is_active = TRUE
        """
        
        result = await self.session.execute(text(query))
        vectors = result.fetchall()
        
        if len(vectors) < self.MIN_CLUSTER_SIZE:
            logger.info("Not enough users for clustering")
            return {"clusters_updated": 0, "users_assigned": 0}
        
        # Convert to numpy array
        user_ids = [v.user_id for v in vectors]
        vector_matrix = np.array([list(v.style_vector) for v in vectors])
        
        # Perform clustering
        try:
            from sklearn.cluster import KMeans
            
            kmeans = KMeans(
                n_clusters=min(self.NUM_CLUSTERS, len(vectors) // 50),
                random_state=42,
                n_init=10,
            )
            
            labels = kmeans.fit_predict(vector_matrix)
            centroids = kmeans.cluster_centers_
            
        except ImportError:
            logger.warning("sklearn not available, skipping clustering")
            return {"clusters_updated": 0, "users_assigned": 0}
        
        # Update cluster centroids in database
        cluster_ids = {}
        
        for i, centroid in enumerate(centroids):
            # Find or create cluster
            cluster_query = select(StyleCluster).where(
                StyleCluster.cluster_name == f"cluster_{i}"
            )
            cluster_result = await self.session.execute(cluster_query)
            cluster = cluster_result.scalar_one_or_none()
            
            if not cluster:
                cluster = StyleCluster(
                    cluster_name=f"Style Cluster {i+1}",
                    cluster_description=f"Auto-generated style cluster {i+1}",
                    centroid_vector=centroid.tolist(),
                    version=1,
                )
                self.session.add(cluster)
                await self.session.flush()
            else:
                cluster.centroid_vector = centroid.tolist()
                cluster.version += 1
                cluster.updated_at = datetime.now(timezone.utc)
            
            cluster_ids[i] = cluster.id
        
        await self.session.commit()
        
        # Assign users to clusters
        assignments = 0
        for idx, (user_id, label) in enumerate(zip(user_ids, labels)):
            cluster_id = cluster_ids[label]
            
            # Update or create assignment
            existing = await self.session.execute(
                select(UserClusterAssignment).where(
                    UserClusterAssignment.user_id == user_id,
                    UserClusterAssignment.is_current == True,
                )
            )
            existing_assignment = existing.scalar_one_or_none()
            
            if existing_assignment:
                existing_assignment.is_current = False
                existing_assignment.valid_until = datetime.now(timezone.utc)
            
            distance = np.linalg.norm(vector_matrix[idx] - centroids[label])
            
            new_assignment = UserClusterAssignment(
                user_id=user_id,
                cluster_id=cluster_id,
                distance_to_centroid=Decimal(str(distance)),
                assignment_confidence=Decimal(str(1 - min(distance, 1))),
                is_current=True,
            )
            self.session.add(new_assignment)
            assignments += 1
        
        await self.session.commit()
        
        logger.info(f"Updated {len(cluster_ids)} clusters, assigned {assignments} users")
        
        return {
            "clusters_updated": len(cluster_ids),
            "users_assigned": assignments,
        }


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_style_dna_service(session: AsyncSession) -> StyleDNAService:
    """Factory function to create StyleDNAService."""
    return StyleDNAService(session)


def get_style_clustering_service(session: AsyncSession) -> StyleClusteringService:
    """Factory function to create StyleClusteringService."""
    return StyleClusteringService(session)
