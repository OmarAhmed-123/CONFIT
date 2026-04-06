"""
CONFIT Backend — Wardrobe Analytics Service
============================================
GROUP 4: Personal Wardrobe & Smart Reuse
Comprehensive analytics, tracking, and personalization.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from collections import defaultdict
from collections import Counter

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from database.session import get_db

from database.models import WardrobeItem
from models.wardrobe_analytics_models import (
    WardrobeItemUsage,
    OutfitHistory,
    WardrobeSeasonalRotation,
    WardrobeSustainabilityMetrics,
    WardrobeColorDominance,
    WardrobeStyleDominance,
    WardrobeConfidenceScore,
    CapsuleWardrobeDetection,
    DeclutterSuggestion,
    PurchaseAvoidanceSignal,
    WearLogEntry,
    OutfitHistoryCreate,
    WardrobeAnalyticsResponse,
    SustainabilityInsightsResponse,
    CapsuleWardrobeResponse,
    DeclutterSuggestionResponse,
    WardrobeConfidenceResponse,
    PurchaseAvoidanceResponse,
    SeasonalRotationResponse,
)
from services.ai_brain_service import AIBrainService

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════

SEASONS = ["spring", "summer", "fall", "winter"]

SEASONAL_TEMP_RANGES = {
    "spring": {"min": 10, "max": 20},
    "summer": {"min": 20, "max": 35},
    "fall": {"min": 5, "max": 18},
    "winter": {"min": -10, "max": 10},
}

CATEGORY_IMPORTANCE = {
    "tops": 1.0,
    "bottoms": 1.0,
    "dresses": 0.8,
    "outerwear": 0.7,
    "shoes": 0.9,
    "accessories": 0.5,
    "bags": 0.6,
}

UNUSED_THRESHOLD_DAYS = 180  # 6 months
LOW_USAGE_THRESHOLD_DAYS = 90  # 3 months
ACTIVE_THRESHOLD_DAYS = 90

# Environmental impact estimates (approximate)
CO2_PER_GARMENT_KG = 15.0  # Average CO2 to produce a garment
WATER_PER_GARMENT_L = 2700.0  # Average water to produce a garment


# ═══════════════════════════════════════════════════════════════════
# Wardrobe Analytics Service
# ═══════════════════════════════════════════════════════════════════

class WardrobeAnalyticsService:
    """
    Comprehensive wardrobe analytics and personalization service.
    
    Features:
    - Wear frequency tracking
    - Seasonal rotation management
    - Outfit history tracking
    - Unused-item alerts
    - Sustainability insights
    - AI Brain signal integration
    - Capsule wardrobe detection
    - Smart declutter suggestions
    - Wardrobe confidence scoring
    """
    
    def __init__(self, db: Session, ai_brain: AIBrainService = None):
        self._db = db
        self._ai_brain = ai_brain
    
    # ── Wear Frequency Tracking ───────────────────────────────────────
    
    def log_wear(
        self,
        user_id: str,
        item_id: str,
        occasion: str = None,
        outfit_id: str = None,
        worn_at: datetime = None,
    ) -> Dict[str, Any]:
        """
        Log a wear event for a wardrobe item.
        Updates usage statistics and triggers analytics recalculation.
        """
        worn_at = worn_at or datetime.now(timezone.utc)
        
        # Get or create usage record
        usage = self._db.query(WardrobeItemUsage).filter(
            WardrobeItemUsage.user_id == user_id,
            WardrobeItemUsage.item_id == item_id,
        ).first()
        
        if not usage:
            usage = WardrobeItemUsage(
                user_id=user_id,
                item_id=item_id,
                first_worn_at=worn_at,
            )
            self._db.add(usage)
        
        # Update wear count
        usage.wear_count += 1
        usage.last_worn_at = worn_at
        
        # Update seasonal tracking
        season = self._get_season_from_date(worn_at)
        seasons_worn = usage.seasons_worn or []
        if season not in seasons_worn:
            seasons_worn.append(season)
            usage.seasons_worn = seasons_worn
        
        # Update current season wears
        current_season = self._get_current_season()
        if season == current_season:
            usage.current_season_wears += 1
        
        # Update occasion tracking
        if occasion:
            occasions = usage.occasions_worn or {}
            occasions[occasion] = occasions.get(occasion, 0) + 1
            usage.occasions_worn = occasions
        
        # Recalculate cost per wear
        item = self._db.query(WardrobeItem).filter(WardrobeItem.id == item_id).first()
        if item and item.price:
            usage.cost_per_wear = Decimal(str(item.price)) / usage.wear_count
        
        # Update wear frequency score
        usage.wear_frequency_score = self._calculate_wear_frequency_score(usage)
        usage.analytics_updated_at = datetime.now(timezone.utc)
        
        self._db.commit()
        
        # Send signal to AI Brain
        if self._ai_brain:
            self._send_reuse_signal(user_id, item_id, usage.wear_count, occasion)
        
        logger.info(f"Logged wear for item {item_id}, total wears: {usage.wear_count}")
        
        return {
            "item_id": item_id,
            "wear_count": usage.wear_count,
            "cost_per_wear": float(usage.cost_per_wear) if usage.cost_per_wear else None,
            "wear_frequency_score": float(usage.wear_frequency_score),
        }
    
    def get_wear_frequency_stats(self, user_id: str) -> Dict[str, Any]:
        """Get wear frequency statistics for user's wardrobe."""
        usage_records = self._db.query(WardrobeItemUsage).filter(
            WardrobeItemUsage.user_id == user_id,
        ).all()
        
        if not usage_records:
            return {"avg_wears": 0, "total_wears": 0, "items_tracked": 0}
        
        total_wears = sum(r.wear_count for r in usage_records)
        avg_wears = total_wears / len(usage_records)
        
        # Find most/least worn
        most_worn = max(usage_records, key=lambda r: r.wear_count)
        least_worn = [r for r in usage_records if r.wear_count <= 1]
        
        return {
            "avg_wears": round(avg_wears, 2),
            "total_wears": total_wears,
            "items_tracked": len(usage_records),
            "most_worn_item_id": most_worn.item_id,
            "most_worn_count": most_worn.wear_count,
            "least_worn_count": len(least_worn),
        }
    
    def _calculate_wear_frequency_score(self, usage: WardrobeItemUsage) -> Decimal:
        """Calculate wear frequency score (0-100) based on usage patterns."""
        if not usage.first_worn_at:
            return Decimal("0.0")
        
        days_owned = (datetime.now(timezone.utc) - usage.first_worn_at).days
        if days_owned < 1:
            days_owned = 1
        
        # Expected wears: at least once every 30 days for good utilization
        expected_wears = max(days_owned / 30, 1)
        actual_wears = usage.wear_count
        
        # Score based on ratio
        ratio = actual_wears / expected_wears
        score = min(ratio * 50, 100)  # Cap at 100
        
        return Decimal(str(round(score, 2)))
    
    # ── Seasonal Rotation ─────────────────────────────────────────────
    
    def get_seasonal_rotation(self, user_id: str) -> Dict[str, Any]:
        """Get seasonal rotation status and recommendations."""
        current_season = self._get_current_season()
        
        # Get all items with seasonal info
        items = self._db.query(WardrobeItem).filter(
            WardrobeItem.owner_user_id == user_id,
        ).all()
        
        seasonal_rotations = self._db.query(WardrobeSeasonalRotation).filter(
            WardrobeSeasonalRotation.user_id == user_id,
        ).all()
        
        rotation_map = {r.item_id: r for r in seasonal_rotations}
        
        active_items = []
        stored_items = []
        items_to_activate = []
        items_to_store = []
        
        for item in items:
            rotation = rotation_map.get(item.id)
            season = rotation.primary_season if rotation else "all_season"
            
            item_data = {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "color": item.color,
                "image_url": item.image_url,
                "season": season,
            }
            
            if rotation and rotation.is_active:
                active_items.append(item_data)
            elif rotation:
                stored_items.append(item_data)
            else:
                # No rotation info - assume active
                active_items.append(item_data)
        
        # Determine items to activate/store based on season
        for item in stored_items:
            rotation = rotation_map.get(item["id"])
            if rotation and rotation.primary_season == current_season:
                items_to_activate.append(item)
        
        for item in active_items:
            rotation = rotation_map.get(item["id"])
            if rotation and rotation.primary_season and rotation.primary_season != "all_season":
                if rotation.primary_season != current_season:
                    items_to_store.append(item)
        
        return {
            "current_season": current_season,
            "active_items_count": len(active_items),
            "stored_items_count": len(stored_items),
            "items_to_activate": items_to_activate[:5],
            "items_to_store": items_to_store[:5],
            "weather_recommendations": self._get_weather_recommendations(current_season),
        }
    
    def set_item_season(
        self,
        user_id: str,
        item_id: str,
        primary_season: str,
        secondary_seasons: List[str] = None,
        temp_range: Dict[int, int] = None,
    ) -> WardrobeSeasonalRotation:
        """Set seasonal classification for an item."""
        rotation = self._db.query(WardrobeSeasonalRotation).filter(
            WardrobeSeasonalRotation.user_id == user_id,
            WardrobeSeasonalRotation.item_id == item_id,
        ).first()
        
        if not rotation:
            rotation = WardrobeSeasonalRotation(
                user_id=user_id,
                item_id=item_id,
            )
            self._db.add(rotation)
        
        rotation.primary_season = primary_season
        rotation.secondary_seasons = secondary_seasons or []
        
        if temp_range:
            rotation.min_temp_c = temp_range.get("min")
            rotation.max_temp_c = temp_range.get("max")
        
        self._db.commit()
        return rotation
    
    def _get_current_season(self) -> str:
        """Determine current season based on date."""
        month = datetime.now().month
        if month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "fall"
        else:
            return "winter"
    
    def _get_season_from_date(self, date: datetime) -> str:
        """Get season from a specific date."""
        month = date.month
        if month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "fall"
        else:
            return "winter"
    
    def _get_weather_recommendations(self, season: str) -> Dict[str, Any]:
        """Get weather-based styling recommendations for season."""
        recommendations = {
            "spring": {
                "fabrics": ["cotton", "linen", "light_denim"],
                "layers": "light",
                "colors": ["pastels", "florals", "neutrals"],
                "accessories": ["light_scarf", "trench_coat"],
            },
            "summer": {
                "fabrics": ["linen", "cotton", "silk", "chambray"],
                "layers": "minimal",
                "colors": ["whites", "brights", "naturals"],
                "accessories": ["sunglasses", "straw_hat", "sandals"],
            },
            "fall": {
                "fabrics": ["wool", "denim", "leather", "knits"],
                "layers": "medium",
                "colors": ["burgundy", "mustard", "brown", "olive"],
                "accessories": ["scarf", "boots", "jacket"],
            },
            "winter": {
                "fabrics": ["wool", "cashmere", "fleece", "down"],
                "layers": "heavy",
                "colors": ["navy", "black", "grey", "burgundy"],
                "accessories": ["coat", "gloves", "beanie", "boots"],
            },
        }
        return recommendations.get(season, recommendations["spring"])
    
    # ── Outfit History ─────────────────────────────────────────────────
    
    def log_outfit(
        self,
        user_id: str,
        item_ids: List[str],
        outfit_name: str = None,
        occasion: str = None,
        weather: str = None,
        temperature_c: int = None,
        is_favorite: bool = False,
        ai_generated: bool = False,
    ) -> OutfitHistory:
        """Log an outfit worn by the user."""
        season = self._get_current_season()
        
        # Get item details
        items = self._db.query(WardrobeItem).filter(
            WardrobeItem.id.in_(item_ids),
            WardrobeItem.owner_user_id == user_id,
        ).all()
        
        item_details = [{
            "id": i.id,
            "name": i.name,
            "category": i.category,
            "color": i.color,
            "image_url": i.image_url,
        } for i in items]
        
        # Calculate style score
        style_score = self._calculate_outfit_style_score(items)
        color_harmony = self._calculate_color_harmony(items)
        
        outfit = OutfitHistory(
            id=f"outfit-{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            outfit_name=outfit_name,
            item_ids=item_ids,
            item_details=item_details,
            occasion=occasion,
            weather=weather,
            temperature_c=temperature_c,
            season=season,
            is_favorite=is_favorite,
            ai_generated=ai_generated,
            style_score=Decimal(str(style_score)),
            color_harmony_score=Decimal(str(color_harmony)),
        )
        
        self._db.add(outfit)
        
        # Log wear for each item
        for item_id in item_ids:
            self.log_wear(user_id, item_id, occasion=occasion, outfit_id=outfit.id)
        
        self._db.commit()
        
        # Send signal to AI Brain
        if self._ai_brain:
            self._ai_brain.track_occasion_pattern(
                user_id=user_id,
                occasion=occasion or "casual",
                outfit_id=outfit.id,
                context={"item_count": len(item_ids), "style_score": style_score},
            )
        
        logger.info(f"Logged outfit {outfit.id} with {len(item_ids)} items")
        return outfit
    
    def get_outfit_history(
        self,
        user_id: str,
        limit: int = 20,
        occasion: str = None,
        season: str = None,
    ) -> List[Dict[str, Any]]:
        """Get outfit history for user."""
        query = self._db.query(OutfitHistory).filter(
            OutfitHistory.user_id == user_id,
        )
        
        if occasion:
            query = query.filter(OutfitHistory.occasion == occasion)
        if season:
            query = query.filter(OutfitHistory.season == season)
        
        outfits = query.order_by(OutfitHistory.worn_at.desc()).limit(limit).all()
        
        return [{
            "id": o.id,
            "name": o.outfit_name,
            "items": o.item_details,
            "occasion": o.occasion,
            "season": o.season,
            "worn_at": o.worn_at.isoformat(),
            "is_favorite": o.is_favorite,
            "style_score": float(o.style_score) if o.style_score else None,
        } for o in outfits]
    
    def _calculate_outfit_style_score(self, items: List[WardrobeItem]) -> float:
        """Calculate style score for an outfit."""
        if not items:
            return 0.0
        
        # Base score
        score = 50.0
        
        # Category completeness bonus
        categories = set(i.category for i in items)
        if "tops" in categories and "bottoms" in categories:
            score += 15
        if "shoes" in categories:
            score += 10
        if "accessories" in categories:
            score += 5
        
        # Color harmony bonus
        color_harmony = self._calculate_color_harmony(items)
        score += color_harmony * 0.2
        
        return min(score, 100.0)
    
    def _calculate_color_harmony(self, items: List[WardrobeItem]) -> float:
        """Calculate color harmony score for items."""
        colors = [i.color for i in items if i.color]
        if len(colors) < 2:
            return 100.0
        
        # Simple harmony check
        neutral_colors = {"black", "white", "grey", "navy", "beige", "brown"}
        
        non_neutral = [c for c in colors if c.lower() not in neutral_colors]
        
        # If only neutrals, high harmony
        if len(non_neutral) <= 1:
            return 95.0
        
        # If multiple non-neutrals, check for harmony
        if len(set(non_neutral)) > 2:
            return 60.0
        
        return 80.0
    
    # ── Unused Item Alerts ─────────────────────────────────────────────
    
    def get_unused_items(self, user_id: str) -> List[Dict[str, Any]]:
        """Get items that haven't been worn recently."""
        threshold = datetime.now(timezone.utc) - timedelta(days=UNUSED_THRESHOLD_DAYS)
        low_threshold = datetime.now(timezone.utc) - timedelta(days=LOW_USAGE_THRESHOLD_DAYS)
        
        # Get all items with usage data
        usage_records = self._db.query(WardrobeItemUsage).filter(
            WardrobeItemUsage.user_id == user_id,
        ).all()
        
        usage_map = {r.item_id: r for r in usage_records}
        
        # Get all wardrobe items
        items = self._db.query(WardrobeItem).filter(
            WardrobeItem.owner_user_id == user_id,
        ).all()
        
        unused = []
        for item in items:
            usage = usage_map.get(item.id)
            
            if not usage:
                # Never worn
                unused.append({
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "color": item.color,
                    "image_url": item.image_url,
                    "brand": item.brand,
                    "price": item.price,
                    "wear_count": 0,
                    "days_since_worn": None,
                    "status": "never_worn",
                    "alert_level": "high",
                })
            elif usage.last_worn_at and usage.last_worn_at < threshold:
                days_since = (datetime.now(timezone.utc) - usage.last_worn_at).days
                unused.append({
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "color": item.color,
                    "image_url": item.image_url,
                    "brand": item.brand,
                    "price": item.price,
                    "wear_count": usage.wear_count,
                    "days_since_worn": days_since,
                    "status": "unused",
                    "alert_level": "high" if days_since > 365 else "medium",
                })
            elif usage.last_worn_at and usage.last_worn_at < low_threshold:
                days_since = (datetime.now(timezone.utc) - usage.last_worn_at).days
                unused.append({
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "color": item.color,
                    "image_url": item.image_url,
                    "brand": item.brand,
                    "price": item.price,
                    "wear_count": usage.wear_count,
                    "days_since_worn": days_since,
                    "status": "low_usage",
                    "alert_level": "low",
                })
        
        return sorted(unused, key=lambda x: x.get("days_since_worn") or 999, reverse=True)
    
    # ── Sustainability Insights ─────────────────────────────────────────
    
    def calculate_sustainability_metrics(self, user_id: str) -> WardrobeSustainabilityMetrics:
        """Calculate and update sustainability metrics for user."""
        metrics = self._db.query(WardrobeSustainabilityMetrics).filter(
            WardrobeSustainabilityMetrics.user_id == user_id,
        ).first()
        
        if not metrics:
            metrics = WardrobeSustainabilityMetrics(user_id=user_id)
            self._db.add(metrics)
        
        # Get all items and usage
        items = self._db.query(WardrobeItem).filter(
            WardrobeItem.owner_user_id == user_id,
        ).all()
        
        usage_records = self._db.query(WardrobeItemUsage).filter(
            WardrobeItemUsage.user_id == user_id,
        ).all()
        
        usage_map = {r.item_id: r for r in usage_records}
        
        # Calculate metrics
        total_items = len(items)
        active_threshold = datetime.now(timezone.utc) - timedelta(days=ACTIVE_THRESHOLD_DAYS)
        unused_threshold = datetime.now(timezone.utc) - timedelta(days=UNUSED_THRESHOLD_DAYS)
        
        active_items = 0
        unused_items = 0
        total_wears = 0
        total_value = Decimal("0.0")
        
        for item in items:
            usage = usage_map.get(item.id)
            if usage:
                total_wears += usage.wear_count
                if usage.last_worn_at and usage.last_worn_at > active_threshold:
                    active_items += 1
                elif not usage.last_worn_at or usage.last_worn_at < unused_threshold:
                    unused_items += 1
            else:
                unused_items += 1
            
            if item.price:
                total_value += Decimal(str(item.price))
        
        metrics.total_items = total_items
        metrics.active_items = active_items
        metrics.unused_items = unused_items
        
        # Utilization score
        if total_items > 0:
            metrics.wardrobe_utilization_score = Decimal(str(
                round((active_items / total_items) * 100, 2)
            ))
        else:
            metrics.wardrobe_utilization_score = Decimal("0.0")
        
        # Sustainability score (based on reuse)
        avg_wears = total_wears / total_items if total_items > 0 else 0
        sustainability_base = min(avg_wears * 10, 50)  # Max 50 from wears
        utilization_bonus = float(metrics.wardrobe_utilization_score) * 0.5
        metrics.sustainability_score = Decimal(str(
            round(min(sustainability_base + utilization_bonus, 100), 2)
        ))
        
        # Environmental impact
        # Each wear saves ~1/30th of the item's production impact
        co2_saved = Decimal(str(total_wears * CO2_PER_GARMENT_KG / 30))
        water_saved = Decimal(str(total_wears * WATER_PER_GARMENT_L / 30))
        
        metrics.total_estimated_co2_kg = co2_saved
        metrics.total_water_saved_l = water_saved
        
        # Capsule score
        metrics.capsule_wardrobe_score = self._calculate_capsule_score(items)
        
        # Declutter value
        declutter_value = sum(
            Decimal(str(i.price or 0)) * Decimal("0.3")  # Estimate 30% resale
            for i in items
            if not usage_map.get(i.id) or usage_map.get(i.id).wear_count <= 2
        )
        metrics.declutter_value_estimate = declutter_value
        
        self._db.commit()
        return metrics
    
    def get_sustainability_insights(self, user_id: str) -> Dict[str, Any]:
        """Get detailed sustainability insights."""
        metrics = self.calculate_sustainability_metrics(user_id)
        
        # Generate tips
        tips = []
        if float(metrics.wardrobe_utilization_score) < 50:
            tips.append("Try wearing items you haven't used in a while")
        if metrics.unused_items > 5:
            tips.append("Consider donating or reselling unused items")
        if float(metrics.sustainability_score) > 70:
            tips.append("Great job! Your wardrobe is eco-friendly")
        
        return {
            "sustainability_score": float(metrics.sustainability_score),
            "wardrobe_utilization_score": float(metrics.wardrobe_utilization_score),
            "total_co2_saved_kg": float(metrics.total_estimated_co2_kg),
            "total_water_saved_l": float(metrics.total_water_saved_l),
            "purchases_prevented": metrics.purchases_prevented,
            "money_saved": float(metrics.money_saved),
            "active_items": metrics.active_items,
            "unused_items": metrics.unused_items,
            "sustainability_tips": tips,
        }
    
    def _calculate_capsule_score(self, items: List[WardrobeItem]) -> Decimal:
        """Calculate capsule wardrobe score."""
        if not items:
            return Decimal("0.0")
        
        # Ideal capsule: 30-40 items, good category balance
        ideal_count = 35
        item_count = len(items)
        
        # Size score
        if item_count <= ideal_count:
            size_score = min(item_count / ideal_count * 100, 100)
        else:
            # Penalty for too many items
            size_score = max(100 - (item_count - ideal_count) * 2, 50)
        
        # Category balance score
        categories = Counter(i.category for i in items)
        expected_distribution = {
            "tops": 0.25,
            "bottoms": 0.15,
            "dresses": 0.10,
            "outerwear": 0.10,
            "shoes": 0.15,
            "accessories": 0.15,
            "bags": 0.10,
        }
        
        balance_score = 100
        for cat, expected_pct in expected_distribution.items():
            actual_pct = categories.get(cat, 0) / item_count
            deviation = abs(actual_pct - expected_pct)
            balance_score -= deviation * 50
        
        balance_score = max(balance_score, 0)
        
        # Combined score
        final_score = (size_score * 0.4 + balance_score * 0.6)
        return Decimal(str(round(final_score, 2)))
    
    # ── Color & Style Dominance ─────────────────────────────────────────
    
    def analyze_color_dominance(self, user_id: str) -> List[Dict[str, Any]]:
        """Analyze color distribution in wardrobe."""
        items = self._db.query(WardrobeItem).filter(
            WardrobeItem.owner_user_id == user_id,
        ).all()
        
        color_counts = Counter(i.color for i in items if i.color)
        total = sum(color_counts.values())
        
        if total == 0:
            return []
        
        # Clear existing records
        self._db.query(WardrobeColorDominance).filter(
            WardrobeColorDominance.user_id == user_id,
        ).delete()
        
        results = []
        for color, count in color_counts.most_common():
            percentage = round((count / total) * 100, 2)
            
            # Determine harmony group
            harmony_group = self._get_color_harmony_group(color)
            
            dominance = WardrobeColorDominance(
                user_id=user_id,
                color_name=color,
                item_count=count,
                percentage=Decimal(str(percentage)),
                harmony_group=harmony_group,
                is_dominant=percentage > 20,
                is_overrepresented=percentage > 30,
            )
            self._db.add(dominance)
            
            results.append({
                "color": color,
                "count": count,
                "percentage": percentage,
                "harmony_group": harmony_group,
                "is_dominant": percentage > 20,
            })
        
        self._db.commit()
        
        # Send signal to AI Brain
        if self._ai_brain:
            self._send_color_dominance_signal(user_id, results)
        
        return results
    
    def analyze_style_dominance(self, user_id: str) -> List[Dict[str, Any]]:
        """Analyze style/category distribution in wardrobe."""
        items = self._db.query(WardrobeItem).filter(
            WardrobeItem.owner_user_id == user_id,
        ).all()
        
        category_counts = Counter(i.category for i in items)
        total = sum(category_counts.values())
        
        if total == 0:
            return []
        
        # Clear existing records
        self._db.query(WardrobeStyleDominance).filter(
            WardrobeStyleDominance.user_id == user_id,
        ).delete()
        
        # Get usage data
        usage_records = self._db.query(WardrobeItemUsage).filter(
            WardrobeItemUsage.user_id == user_id,
        ).all()
        usage_map = {r.item_id: r for r in usage_records}
        
        results = []
        for category, count in category_counts.most_common():
            percentage = round((count / total) * 100, 2)
            
            # Calculate average wear for category
            cat_items = [i for i in items if i.category == category]
            wears = [usage_map.get(i.id).wear_count for i in cat_items if usage_map.get(i.id)]
            avg_wear = sum(wears) / len(wears) if wears else 0
            
            # Find most worn in category
            most_worn_id = None
            max_wears = 0
            for item in cat_items:
                usage = usage_map.get(item.id)
                if usage and usage.wear_count > max_wears:
                    max_wears = usage.wear_count
                    most_worn_id = item.id
            
            # Check for gaps
            is_gap = percentage < 10 and CATEGORY_IMPORTANCE.get(category, 0.5) > 0.7
            gap_severity = "critical" if percentage < 5 else "moderate" if percentage < 10 else None
            
            dominance = WardrobeStyleDominance(
                user_id=user_id,
                category=category,
                item_count=count,
                percentage=Decimal(str(percentage)),
                avg_wear_count=Decimal(str(round(avg_wear, 2))),
                most_worn_item_id=most_worn_id,
                is_gap=is_gap,
                gap_severity=gap_severity,
            )
            self._db.add(dominance)
            
            results.append({
                "category": category,
                "count": count,
                "percentage": percentage,
                "avg_wears": round(avg_wear, 2),
                "is_gap": is_gap,
                "gap_severity": gap_severity,
            })
        
        self._db.commit()
        
        # Send signal to AI Brain
        if self._ai_brain:
            self._send_style_dominance_signal(user_id, results)
        
        return results
    
    def _get_color_harmony_group(self, color: str) -> str:
        """Determine color harmony group."""
        warm = {"red", "orange", "yellow", "coral", "peach", "burgundy", "rust", "terracotta"}
        cool = {"blue", "green", "purple", "teal", "navy", "emerald", "lavender", "pink"}
        neutral = {"black", "white", "grey", "beige", "brown", "cream", "tan", "charcoal"}
        
        color_lower = color.lower()
        
        if color_lower in warm:
            return "warm"
        elif color_lower in cool:
            return "cool"
        elif color_lower in neutral:
            return "neutral"
        else:
            return "accent"
    
    # ── Wardrobe Confidence Score ─────────────────────────────────────────
    
    def calculate_wardrobe_confidence(self, user_id: str) -> WardrobeConfidenceScore:
        """Calculate comprehensive wardrobe confidence score."""
        score = self._db.query(WardrobeConfidenceScore).filter(
            WardrobeConfidenceScore.user_id == user_id,
        ).first()
        
        if not score:
            score = WardrobeConfidenceScore(user_id=user_id)
            self._db.add(score)
        
        # Get items and analytics
        items = self._db.query(WardrobeItem).filter(
            WardrobeItem.owner_user_id == user_id,
        ).all()
        
        usage_records = self._db.query(WardrobeItemUsage).filter(
            WardrobeItemUsage.user_id == user_id,
        ).all()
        
        sustainability = self.calculate_sustainability_metrics(user_id)
        
        # Calculate dimension scores
        score.variety_score = self._calc_variety_score(items)
        score.versatility_score = self._calc_versatility_score(items)
        score.utilization_score = sustainability.wardrobe_utilization_score
        score.cohesion_score = self._calc_cohesion_score(items)
        score.seasonality_score = self._calc_seasonality_score(user_id)
        score.quality_score = self._calc_quality_score(items)
        
        # Calculate outfit readiness
        score.outfit_readiness = self._calc_outfit_readiness(items)
        score.occasion_coverage = self._calc_occasion_coverage(items)
        
        # Overall confidence
        dimensions = [
            float(score.variety_score),
            float(score.versatility_score),
            float(score.utilization_score),
            float(score.cohesion_score),
            float(score.seasonality_score),
            float(score.quality_score),
        ]
        score.overall_confidence = Decimal(str(round(sum(dimensions) / len(dimensions), 2)))
        
        # Generate improvements
        improvements = []
        quick_wins = []
        
        if float(score.variety_score) < 50:
            improvements.append("Add more variety across categories")
        if float(score.utilization_score) < 50:
            quick_wins.append("Wear items you haven't used recently")
        if float(score.cohesion_score) < 50:
            improvements.append("Build a more cohesive color palette")
        
        score.top_improvements = improvements[:3]
        score.quick_wins = quick_wins[:3]
        
        self._db.commit()
        return score
    
    def _calc_variety_score(self, items: List[WardrobeItem]) -> Decimal:
        """Calculate category variety score."""
        if not items:
            return Decimal("0.0")
        
        categories = set(i.category for i in items)
        expected_categories = 5  # Minimum for good variety
        
        score = min(len(categories) / expected_categories * 100, 100)
        return Decimal(str(round(score, 2)))
    
    def _calc_versatility_score(self, items: List[WardrobeItem]) -> Decimal:
        """Calculate mix-and-match versatility score."""
        if not items:
            return Decimal("0.0")
        
        # Count neutral/base items (more versatile)
        neutral_colors = {"black", "white", "grey", "navy", "beige", "brown"}
        neutral_count = sum(1 for i in items if i.color and i.color.lower() in neutral_colors)
        
        # Versatility increases with neutral items
        neutral_ratio = neutral_count / len(items)
        
        # Also consider category combinations possible
        categories = set(i.category for i in items)
        category_score = len(categories) * 10
        
        score = min(neutral_ratio * 60 + category_score, 100)
        return Decimal(str(round(score, 2)))
    
    def _calc_cohesion_score(self, items: List[WardrobeItem]) -> Decimal:
        """Calculate color/style cohesion score."""
        if not items:
            return Decimal("0.0")
        
        colors = [i.color for i in items if i.color]
        if len(colors) < 2:
            return Decimal("100.0")
        
        # Check color harmony
        color_analysis = self.analyze_color_dominance(items[0].owner_user_id if items else "")
        
        # High dominance of harmonious colors = good cohesion
        dominant_harmony_groups = set(
            c["harmony_group"] for c in color_analysis
            if c["is_dominant"]
        )
        
        # Good cohesion = 1-2 dominant harmony groups
        if len(dominant_harmony_groups) <= 2:
            return Decimal("85.0")
        elif len(dominant_harmony_groups) <= 3:
            return Decimal("70.0")
        else:
            return Decimal("50.0")
    
    def _calc_seasonality_score(self, user_id: str) -> Decimal:
        """Calculate season coverage score."""
        rotations = self._db.query(WardrobeSeasonalRotation).filter(
            WardrobeSeasonalRotation.user_id == user_id,
        ).all()
        
        if not rotations:
            return Decimal("50.0")  # Default without data
        
        seasons_covered = set(r.primary_season for r in rotations if r.primary_season)
        
        # Score based on seasons covered
        score = len(seasons_covered) / 4 * 100
        return Decimal(str(round(min(score, 100), 2)))
    
    def _calc_quality_score(self, items: List[WardrobeItem]) -> Decimal:
        """Calculate quality/investment score."""
        if not items:
            return Decimal("0.0")
        
        # Consider price as quality indicator
        prices = [i.price for i in items if i.price]
        if not prices:
            return Decimal("50.0")
        
        avg_price = sum(prices) / len(prices)
        
        # Score based on average price tiers
        if avg_price > 200:
            return Decimal("90.0")
        elif avg_price > 100:
            return Decimal("75.0")
        elif avg_price > 50:
            return Decimal("60.0")
        else:
            return Decimal("40.0")
    
    def _calc_outfit_readiness(self, items: List[WardrobeItem]) -> Decimal:
        """Calculate outfit creation readiness."""
        categories = set(i.category for i in items)
        
        # Need at least tops and bottoms or dresses
        essentials = {"tops", "bottoms"}
        has_essentials = bool(categories & essentials) or "dresses" in categories
        has_shoes = "shoes" in categories
        
        if has_essentials and has_shoes:
            return Decimal("90.0")
        elif has_essentials:
            return Decimal("60.0")
        else:
            return Decimal("30.0")
    
    def _calc_occasion_coverage(self, items: List[WardrobeItem]) -> Dict[str, int]:
        """Calculate occasion coverage percentages."""
        categories = Counter(i.category for i in items)
        
        return {
            "casual": min(100, categories.get("tops", 0) * 10 + categories.get("bottoms", 0) * 15),
            "work": min(100, categories.get("tops", 0) * 8 + categories.get("outerwear", 0) * 20),
            "formal": min(100, categories.get("dresses", 0) * 30 + categories.get("outerwear", 0) * 15),
            "active": min(100, categories.get("shoes", 0) * 10),
        }
    
    # ── Capsule Wardrobe Detection ─────────────────────────────────────────
    
    def detect_capsule_wardrobes(self, user_id: str) -> List[CapsuleWardrobeDetection]:
        """Detect and suggest capsule wardrobes."""
        items = self._db.query(WardrobeItem).filter(
            WardrobeItem.owner_user_id == user_id,
        ).all()
        
        if len(items) < 10:
            return []
        
        capsules = []
        
        # Detect work capsule
        work_items = self._detect_work_capsule(items)
        if work_items:
            capsules.append(self._create_capsule(user_id, work_items, "work", "Work Capsule"))
        
        # Detect casual capsule
        casual_items = self._detect_casual_capsule(items)
        if casual_items:
            capsules.append(self._create_capsule(user_id, casual_items, "casual", "Casual Capsule"))
        
        # Detect seasonal capsule
        current_season = self._get_current_season()
        seasonal_items = self._detect_seasonal_capsule(items, current_season)
        if seasonal_items:
            capsules.append(self._create_capsule(user_id, seasonal_items, "seasonal", f"{current_season.title()} Capsule"))
        
        return capsules
    
    def _detect_work_capsule(self, items: List[WardrobeItem]) -> List[WardrobeItem]:
        """Detect items suitable for work capsule."""
        work_categories = {"tops", "bottoms", "dresses", "outerwear", "shoes"}
        work_colors = {"black", "navy", "grey", "white", "beige", "brown"}
        
        work_items = [
            i for i in items
            if i.category in work_categories
            and (not i.color or i.color.lower() in work_colors)
        ]
        
        return work_items[:15] if len(work_items) >= 8 else []
    
    def _detect_casual_capsule(self, items: List[WardrobeItem]) -> List[WardrobeItem]:
        """Detect items suitable for casual capsule."""
        casual_items = [i for i in items if i.category in {"tops", "bottoms", "shoes", "accessories"}]
        return casual_items[:12] if len(casual_items) >= 6 else []
    
    def _detect_seasonal_capsule(self, items: List[WardrobeItem], season: str) -> List[WardrobeItem]:
        """Detect items suitable for seasonal capsule."""
        # Simplified - would integrate with seasonal rotation data
        return items[:20] if len(items) >= 10 else []
    
    def _create_capsule(
        self,
        user_id: str,
        items: List[WardrobeItem],
        capsule_type: str,
        name: str,
    ) -> CapsuleWardrobeDetection:
        """Create a capsule wardrobe record."""
        item_ids = [i.id for i in items]
        colors = list(set(i.color for i in items if i.color))
        
        capsule = CapsuleWardrobeDetection(
            id=uuid.uuid4(),
            user_id=user_id,
            capsule_name=name,
            capsule_type=capsule_type,
            item_ids=item_ids,
            item_count=len(items),
            cohesion_score=self._calc_cohesion_score(items),
            versatility_score=self._calc_versatility_score(items),
            outfit_combinations=self._estimate_outfit_combinations(items),
            dominant_colors=colors[:5],
            is_ai_suggested=True,
        )
        
        self._db.add(capsule)
        self._db.commit()
        return capsule
    
    def _estimate_outfit_combinations(self, items: List[WardrobeItem]) -> int:
        """Estimate possible outfit combinations."""
        categories = Counter(i.category for i in items)
        
        tops = categories.get("tops", 0)
        bottoms = categories.get("bottoms", 0)
        dresses = categories.get("dresses", 0)
        outerwear = categories.get("outerwear", 0)
        
        # Base combinations
        base = tops * bottoms + dresses
        # With outerwear options
        with_outer = base * (1 + outerwear * 0.5)
        
        return int(min(with_outer, 1000))
    
    # ── Smart Declutter Suggestions ─────────────────────────────────────────
    
    def generate_declutter_suggestions(self, user_id: str) -> List[DeclutterSuggestion]:
        """Generate smart declutter suggestions."""
        unused_items = self.get_unused_items(user_id)
        
        suggestions = []
        for item_data in unused_items[:10]:  # Limit to top 10
            item = self._db.query(WardrobeItem).filter(WardrobeItem.id == item_data["id"]).first()
            if not item:
                continue
            
            # Determine suggestion type
            if item_data["status"] == "never_worn":
                suggestion_type = "unused"
                reason = "This item has never been worn since being added to your wardrobe."
            elif item_data["wear_count"] <= 2:
                suggestion_type = "low_usage"
                reason = f"This item has only been worn {item_data['wear_count']} time(s)."
            else:
                suggestion_type = "unused"
                reason = f"Last worn {item_data.get('days_since_worn', 'unknown')} days ago."
            
            # Estimate resale value
            estimated_value = Decimal(str(item.price or 0)) * Decimal("0.3") if item.price else None
            
            suggestion = DeclutterSuggestion(
                id=uuid.uuid4(),
                user_id=user_id,
                item_id=item.id,
                suggestion_type=suggestion_type,
                confidence=Decimal("0.85"),
                reason=reason,
                data_points={
                    "wear_count": item_data["wear_count"],
                    "days_since_worn": item_data.get("days_since_worn"),
                },
                estimated_resale_value=estimated_value,
            )
            
            self._db.add(suggestion)
            suggestions.append(suggestion)
        
        self._db.commit()
        return suggestions
    
    # ── Purchase Avoidance Signals ─────────────────────────────────────────
    
    def check_purchase_avoidance(
        self,
        user_id: str,
        product_name: str,
        product_category: str,
        product_color: str,
        product_price: float = None,
    ) -> PurchaseAvoidanceResponse:
        """Check if user already has similar items to prevent unnecessary purchase."""
        # Find similar items in wardrobe
        similar_items = self._db.query(WardrobeItem).filter(
            WardrobeItem.owner_user_id == user_id,
            WardrobeItem.category == product_category,
        ).all()
        
        # Filter by color similarity
        color_matches = [
            i for i in similar_items
            if i.color and i.color.lower() == product_color.lower()
        ]
        
        matched_item = None
        similarity = 0.0
        
        if color_matches:
            matched_item = color_matches[0]
            similarity = 0.9
        elif similar_items:
            # Category match only
            matched_item = similar_items[0]
            similarity = 0.5
        
        # Log signal
        signal = PurchaseAvoidanceSignal(
            id=uuid.uuid4(),
            user_id=user_id,
            signal_type="duplicate_check",
            product_name=product_name,
            product_category=product_category,
            product_color=product_color,
            product_price=Decimal(str(product_price)) if product_price else None,
            matched_item_id=matched_item.id if matched_item else None,
            match_similarity=Decimal(str(similarity)) if similarity > 0 else None,
            purchase_avoided=bool(matched_item),
        )
        
        self._db.add(signal)
        
        # Update sustainability metrics
        if matched_item:
            metrics = self._db.query(WardrobeSustainabilityMetrics).filter(
                WardrobeSustainabilityMetrics.user_id == user_id,
            ).first()
            if metrics:
                metrics.purchases_prevented += 1
                if product_price:
                    metrics.money_saved += Decimal(str(product_price))
        
        self._db.commit()
        
        # Send signal to AI Brain
        if self._ai_brain:
            self._send_purchase_avoidance_signal(user_id, matched_item, product_price)
        
        return PurchaseAvoidanceResponse(
            avoided=bool(matched_item),
            matched_item_id=matched_item.id if matched_item else None,
            matched_item_name=matched_item.name if matched_item else None,
            matched_item_image=matched_item.image_url if matched_item else None,
            similarity=similarity,
            money_saved=product_price if matched_item else None,
            suggestion=f"You already have a similar {product_color} {product_category}!" if matched_item else "No similar items found.",
        )
    
    # ── AI Brain Signal Integration ─────────────────────────────────────────
    
    def _send_reuse_signal(self, user_id: str, item_id: str, wear_count: int, occasion: str):
        """Send reuse pattern signal to AI Brain."""
        if not self._ai_brain:
            return
        
        self._ai_brain.track_interaction(
            user_id=user_id,
            interaction_type="item_worn",
            entity_type="wardrobe_item",
            entity_id=item_id,
            context={
                "wear_count": wear_count,
                "occasion": occasion,
                "source": "wardrobe_analytics",
            },
        )
    
    def _send_color_dominance_signal(self, user_id: str, color_analysis: List[Dict]):
        """Send color dominance signal to AI Brain."""
        if not self._ai_brain:
            return
        
        dominant_colors = [c for c in color_analysis if c["is_dominant"]]
        
        self._ai_brain.track_style_preference(
            user_id=user_id,
            preference_type="dominant_colors",
            value=",".join(c["color"] for c in dominant_colors),
            source="wardrobe_analytics",
            confidence=0.8,
        )
    
    def _send_style_dominance_signal(self, user_id: str, style_analysis: List[Dict]):
        """Send style dominance signal to AI Brain."""
        if not self._ai_brain:
            return
        
        gaps = [s for s in style_analysis if s["is_gap"]]
        
        for gap in gaps:
            self._ai_brain.track_interaction(
                user_id=user_id,
                interaction_type="wardrobe_gap",
                entity_type="category",
                entity_id=gap["category"],
                context={
                    "severity": gap["gap_severity"],
                    "current_count": gap["count"],
                },
            )
    
    def _send_purchase_avoidance_signal(self, user_id: str, matched_item: WardrobeItem, price: float):
        """Send purchase avoidance signal to AI Brain."""
        if not self._ai_brain or not matched_item:
            return
        
        self._ai_brain.track_budget_behavior(
            user_id=user_id,
            action="purchase_avoided",
            amount=price or 0,
            context={
                "matched_item_id": matched_item.id,
                "source": "wardrobe_duplicate_check",
            },
        )
    
    # ── Comprehensive Analytics ─────────────────────────────────────────
    
    def get_full_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive wardrobe analytics."""
        # Ensure all analytics are up to date
        self.calculate_sustainability_metrics(user_id)
        self.calculate_wardrobe_confidence(user_id)
        color_analysis = self.analyze_color_dominance(user_id)
        style_analysis = self.analyze_style_dominance(user_id)
        
        # Get usage stats
        usage_stats = self.get_wear_frequency_stats(user_id)
        
        # Get unused items
        unused = self.get_unused_items(user_id)
        
        # Get seasonal rotation
        seasonal = self.get_seasonal_rotation(user_id)
        
        # Get outfit history summary
        outfit_history = self.get_outfit_history(user_id, limit=5)
        
        # Get confidence score
        confidence = self._db.query(WardrobeConfidenceScore).filter(
            WardrobeConfidenceScore.user_id == user_id,
        ).first()
        
        # Get sustainability
        sustainability = self._db.query(WardrobeSustainabilityMetrics).filter(
            WardrobeSustainabilityMetrics.user_id == user_id,
        ).first()
        
        return {
            "overview": {
                "total_items": sustainability.total_items if sustainability else 0,
                "active_items": sustainability.active_items if sustainability else 0,
                "unused_items": len(unused),
                "total_wears": usage_stats.get("total_wears", 0),
            },
            "wear_frequency": usage_stats,
            "color_distribution": color_analysis[:10],
            "category_distribution": style_analysis,
            "seasonal_rotation": seasonal,
            "recent_outfits": outfit_history,
            "confidence": {
                "overall": float(confidence.overall_confidence) if confidence else 0,
                "dimensions": {
                    "variety": float(confidence.variety_score) if confidence else 0,
                    "versatility": float(confidence.versatility_score) if confidence else 0,
                    "utilization": float(confidence.utilization_score) if confidence else 0,
                    "cohesion": float(confidence.cohesion_score) if confidence else 0,
                },
                "improvements": confidence.top_improvements if confidence else [],
            },
            "sustainability": {
                "score": float(sustainability.sustainability_score) if sustainability else 0,
                "co2_saved_kg": float(sustainability.total_estimated_co2_kg) if sustainability else 0,
                "money_saved": float(sustainability.money_saved) if sustainability else 0,
            },
            "declutter_candidates": len(unused),
        }


def get_wardrobe_analytics_service(db: Session = Depends(get_db), ai_brain: AIBrainService = None) -> WardrobeAnalyticsService:
    """Factory function for wardrobe analytics service."""
    return WardrobeAnalyticsService(db, ai_brain)
