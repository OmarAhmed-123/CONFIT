"""
CONFIT Backend — Smart Closet Planner Service
=============================================
Weekly outfit planning engine integrating wardrobe, style DNA, weather, and calendar.
"""

import os
import logging
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import json
import asyncio
import random

from sqlalchemy import select, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.closet_planner_models import (
    ClosetPlan,
    DailyOutfit,
    OutfitHistory,
    PlannerPreferences,
    ClosetPlanDTO,
    ClosetPlanCreateDTO,
    DailyOutfitDTO,
    DailyOutfitUpdateDTO,
    OutfitSwapDTO,
    OutfitSuggestionRequestDTO,
    OutfitSuggestionDTO,
    OutfitItemDTO,
    OutfitStatus,
    DeviationType,
    PlannerPreferencesDTO,
    PlannerPreferencesUpdateDTO,
    WeeklyPlanSummaryDTO,
    OutfitHistoryDTO,
    WeatherDataDTO,
    CalendarEventDTO,
    AlternativeOutfitDTO,
)
from database.models import WardrobeItem, Outfit, User
from services.weather_service import WeatherService
from services.calendar_service import CalendarService

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# OUTFIT PLANNING CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# Category groups for outfit composition
OUTFIT_CATEGORIES = {
    "tops": ["shirt", "blouse", "t-shirt", "sweater", "cardigan", "jacket", "blazer", "coat"],
    "bottoms": ["pants", "jeans", "shorts", "skirt", "trousers"],
    "dresses": ["dress", "jumpsuit", "romper"],
    "shoes": ["shoes", "sneakers", "boots", "heels", "flats", "sandals"],
    "accessories": ["bag", "belt", "hat", "scarf", "jewelry", "watch", "sunglasses"],
}

# Essential categories for a complete outfit
ESSENTIAL_CATEGORIES = ["tops", "bottoms", "shoes"]
ALTERNATIVE_ESSENTIAL = ["dresses"]  # Can replace tops + bottoms

# Occasion to category preferences
OCCASION_PREFERENCES = {
    "work": {
        "prefer": ["blazer", "dress_shirt", "chinos", "dress", "heels", "oxfords"],
        "avoid": ["t-shirt", "shorts", "flip_flops", "sneakers"],
    },
    "formal": {
        "prefer": ["suit", "dress", "heels", "oxfords", "tie"],
        "avoid": ["jeans", "t-shirt", "sneakers", "shorts"],
    },
    "casual": {
        "prefer": ["jeans", "t-shirt", "sneakers", "casual_shirt"],
        "avoid": ["suit", "tie", "heels"],
    },
    "date_night": {
        "prefer": ["dress", "nice_shirt", "heels", "blouse"],
        "avoid": ["sweatpants", "flip_flops"],
    },
    "party": {
        "prefer": ["dress", "heels", "statement_piece", "blazer"],
        "avoid": ["work_clothes", "casual"],
    },
    "athletic": {
        "prefer": ["activewear", "sneakers", "sports_top", "leggings"],
        "avoid": ["jeans", "dress", "heels"],
    },
    "everyday": {
        "prefer": [],
        "avoid": [],
    },
}

# Style DNA to outfit matching
STYLE_PREFERENCES = {
    "classic": {"prefer": ["blazer", "dress_shirt", "chinos"], "avoid": ["distressed", "graphic_tee"]},
    "trendy": {"prefer": ["statement_piece", "trendy_item"], "avoid": ["outdated"]},
    "minimalist": {"prefer": ["solid_colors", "clean_lines"], "avoid": ["patterns", "bold_colors"]},
    "maximalist": {"prefer": ["patterns", "bold_colors", "layers"], "avoid": ["plain"]},
    "feminine": {"prefer": ["dress", "skirt", "blouse", "floral"], "avoid": ["oversized"]},
    "masculine": {"prefer": ["structured", "blazer", "pants"], "avoid": ["floral", "ruffles"]},
    "edgy": {"prefer": ["leather", "black", "distressed"], "avoid": ["preppy"]},
    "bohemian": {"prefer": ["flowy", "floral", "ethnic_prints"], "avoid": ["structured", "formal"]},
    "streetwear": {"prefer": ["hoodie", "sneakers", "oversized"], "avoid": ["formal", "heels"]},
    "luxury": {"prefer": ["designer", "quality_fabric", "elegant"], "avoid": ["cheap", "casual"]},
}


# ─────────────────────────────────────────────────────────────────────────────
# CLOSET PLANNER SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class ClosetPlannerService:
    """
    Main service for Smart Closet Planner.
    Generates weekly outfit plans based on:
    - User's wardrobe
    - Style DNA preferences
    - Weather forecast
    - Calendar events
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.weather_service = WeatherService(session)
        self.calendar_service = CalendarService(session)
    
    async def close(self):
        """Close service connections."""
        await self.weather_service.close()
        await self.calendar_service.close()
    
    # ─────────────────────────────────────────────────────────────────────────
    # PLAN MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_or_create_preferences(
        self,
        user_id: UUID,
    ) -> PlannerPreferences:
        """Get or create planner preferences for user."""
        query = select(PlannerPreferences).where(
            PlannerPreferences.user_id == str(user_id)
        )
        result = await self.session.execute(query)
        prefs = result.scalar_one_or_none()
        
        if not prefs:
            prefs = PlannerPreferences(
                user_id=str(user_id),
                location={"city": "New York", "country": "US"},
            )
            self.session.add(prefs)
            await self.session.commit()
            await self.session.refresh(prefs)
        
        return prefs
    
    async def update_preferences(
        self,
        user_id: UUID,
        update_data: PlannerPreferencesUpdateDTO,
    ) -> PlannerPreferences:
        """Update planner preferences."""
        prefs = await self.get_or_create_preferences(user_id)
        
        if update_data.planning_day is not None:
            prefs.planning_day = update_data.planning_day
        if update_data.planning_time is not None:
            prefs.planning_time = datetime.strptime(update_data.planning_time, "%H:%M").time()
        if update_data.auto_generate is not None:
            prefs.auto_generate = update_data.auto_generate
        if update_data.location is not None:
            prefs.location = update_data.location
        if update_data.temperature_unit is not None:
            prefs.temperature_unit = update_data.temperature_unit
        if update_data.weather_sensitivity is not None:
            prefs.weather_sensitivity = update_data.weather_sensitivity
        if update_data.calendar_providers is not None:
            prefs.calendar_providers = update_data.calendar_providers
        if update_data.prefer_favorite_items is not None:
            prefs.prefer_favorite_items = update_data.prefer_favorite_items
        if update_data.avoid_recently_worn is not None:
            prefs.avoid_recently_worn = update_data.avoid_recently_worn
        if update_data.recently_worn_days is not None:
            prefs.recently_worn_days = update_data.recently_worn_days
        if update_data.max_item_frequency is not None:
            prefs.max_item_frequency = update_data.max_item_frequency
        if update_data.occasion_priorities is not None:
            prefs.occasion_priorities = update_data.occasion_priorities
        if update_data.notify_new_plan is not None:
            prefs.notify_new_plan = update_data.notify_new_plan
        if update_data.notify_daily is not None:
            prefs.notify_daily = update_data.notify_daily
        if update_data.notify_daily_time is not None:
            prefs.notify_daily_time = datetime.strptime(update_data.notify_daily_time, "%H:%M").time()
        
        prefs.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(prefs)
        
        return prefs
    
    async def get_current_plan(
        self,
        user_id: UUID,
    ) -> Optional[ClosetPlanDTO]:
        """Get the current week's plan."""
        today = date.today()
        week_start = self._get_week_start(today)
        
        query = select(ClosetPlan).options(
            selectinload(ClosetPlan.daily_outfits)
        ).where(
            ClosetPlan.user_id == str(user_id),
            ClosetPlan.week_start_date <= today,
            ClosetPlan.week_end_date >= today,
            ClosetPlan.is_active == True,
        )
        
        result = await self.session.execute(query)
        plan = result.scalar_one_or_none()
        
        if plan:
            return self._plan_to_dto(plan)
        
        return None
    
    async def get_plan(
        self,
        user_id: UUID,
        plan_id: UUID,
    ) -> Optional[ClosetPlanDTO]:
        """Get a specific plan by ID."""
        query = select(ClosetPlan).options(
            selectinload(ClosetPlan.daily_outfits)
        ).where(
            ClosetPlan.id == str(plan_id),
            ClosetPlan.user_id == str(user_id),
        )
        
        result = await self.session.execute(query)
        plan = result.scalar_one_or_none()
        
        if plan:
            return self._plan_to_dto(plan)
        
        return None
    
    async def generate_weekly_plan(
        self,
        user_id: UUID,
        request: ClosetPlanCreateDTO,
    ) -> ClosetPlanDTO:
        """
        Generate a weekly outfit plan.
        
        This is the main planning algorithm that:
        1. Fetches user's wardrobe items
        2. Gets style DNA preferences
        3. Fetches weather forecast
        4. Gets calendar events
        5. Generates outfit suggestions for each day
        """
        # Determine week to plan
        if request.week_start_date:
            week_start = self._get_week_start(request.week_start_date)
        else:
            # Default to next week
            week_start = self._get_week_start(date.today() + timedelta(days=7))
        
        week_end = week_start + timedelta(days=6)
        
        # Check for existing plan
        if not request.force_regenerate:
            existing = await self._get_plan_for_week(user_id, week_start)
            if existing:
                return self._plan_to_dto(existing)
        
        # Get user preferences
        prefs = await self.get_or_create_preferences(user_id)
        
        # Fetch context data
        wardrobe_items = await self._get_wardrobe_items(user_id)
        style_dna = await self._get_style_dna(user_id)
        weather_forecast = await self.weather_service.get_week_forecast(
            week_start, prefs.location or {}
        )
        calendar_events = await self.calendar_service.get_events_for_week(
            user_id, week_start
        )
        
        # Get recently worn items to avoid
        recently_worn = await self._get_recently_worn_items(
            user_id, prefs.recently_worn_days or 7
        )
        
        # Create plan
        plan = ClosetPlan(
            user_id=str(user_id),
            week_start_date=week_start,
            week_end_date=week_end,
            plan_name=request.plan_name,
            is_active=True,
            generation_context={
                "style_dna": style_dna,
                "weather_forecast": [w.model_dump() for w in weather_forecast],
                "calendar_events": {str(k): [e.model_dump() for e in v] for k, v in calendar_events.items()},
                "preferences": {
                    "prefer_favorite_items": prefs.prefer_favorite_items,
                    "avoid_recently_worn": prefs.avoid_recently_worn,
                    "max_item_frequency": prefs.max_item_frequency,
                },
            },
        )
        
        self.session.add(plan)
        await self.session.flush()
        
        # Generate daily outfits
        daily_outfits = []
        item_usage = {}  # Track item usage frequency
        
        for i in range(7):
            current_date = week_start + timedelta(days=i)
            day_weather = weather_forecast[i] if i < len(weather_forecast) else None
            day_events = calendar_events.get(current_date, [])
            
            # Determine primary occasion
            primary_occasion = self._determine_occasion(day_events)
            
            # Generate outfit
            outfit_data, items = await self._generate_outfit(
                user_id=user_id,
                target_date=current_date,
                wardrobe_items=wardrobe_items,
                style_dna=style_dna,
                weather=day_weather,
                events=day_events,
                occasion=primary_occasion,
                recently_worn=recently_worn if prefs.avoid_recently_worn else set(),
                item_usage=item_usage,
                max_frequency=prefs.max_item_frequency or 2,
                prefer_favorites=prefs.prefer_favorite_items or True,
            )
            
            # Generate alternatives
            alternatives = await self._generate_alternatives(
                user_id=user_id,
                target_date=current_date,
                wardrobe_items=wardrobe_items,
                style_dna=style_dna,
                weather=day_weather,
                events=day_events,
                occasion=primary_occasion,
                exclude_items=[item["id"] for item in items],
                count=2,
            )
            
            # Calculate scores
            style_score = self._calculate_style_match(outfit_data, style_dna)
            weather_score = self._calculate_weather_match(outfit_data, day_weather)
            occasion_score = self._calculate_occasion_match(outfit_data, primary_occasion)
            overall_score = (style_score + weather_score + occasion_score) / 3
            
            daily_outfit = DailyOutfit(
                plan_id=plan.id,
                user_id=str(user_id),
                plan_date=current_date,
                day_of_week=current_date.weekday(),
                outfit_data=outfit_data,
                weather_data=day_weather.model_dump() if day_weather else None,
                calendar_events=[e.model_dump() for e in day_events],
                primary_occasion=primary_occasion,
                occasion_confidence=0.8 if day_events else 0.5,
                alternative_outfits=[a.model_dump() for a in alternatives],
                status=OutfitStatus.PLANNED.value,
                style_match_score=Decimal(str(style_score)),
                weather_match_score=Decimal(str(weather_score)),
                occasion_match_score=Decimal(str(occasion_score)),
                overall_score=Decimal(str(overall_score)),
            )
            
            self.session.add(daily_outfit)
            daily_outfits.append(daily_outfit)
            
            # Update item usage
            for item in items:
                item_id = item["id"]
                item_usage[item_id] = item_usage.get(item_id, 0) + 1
        
        plan.total_outfits = len(daily_outfits)
        plan.days_planned = len([d for d in daily_outfits if d.outfit_data])
        
        await self.session.commit()
        await self.session.refresh(plan)
        
        return self._plan_to_dto(plan)
    
    async def update_daily_outfit(
        self,
        user_id: UUID,
        daily_outfit_id: UUID,
        update_data: DailyOutfitUpdateDTO,
    ) -> Optional[DailyOutfitDTO]:
        """Update a daily outfit."""
        query = select(DailyOutfit).where(
            DailyOutfit.id == str(daily_outfit_id),
            DailyOutfit.user_id == str(user_id),
        )
        
        result = await self.session.execute(query)
        daily = result.scalar_one_or_none()
        
        if not daily:
            return None
        
        if update_data.outfit_data is not None:
            daily.outfit_data = update_data.outfit_data
            daily.status = OutfitStatus.MODIFIED.value
        
        if update_data.status is not None:
            daily.status = update_data.status.value
            if update_data.status == OutfitStatus.WORN:
                daily.worn_at = datetime.now(timezone.utc)
        
        if update_data.user_rating is not None:
            daily.user_rating = update_data.user_rating
        
        if update_data.user_notes is not None:
            daily.user_notes = update_data.user_notes
        
        if update_data.primary_occasion is not None:
            daily.primary_occasion = update_data.primary_occasion
        
        daily.updated_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        await self.session.refresh(daily)
        
        return self._daily_to_dto(daily)
    
    async def swap_outfits(
        self,
        user_id: UUID,
        plan_id: UUID,
        swap_data: OutfitSwapDTO,
    ) -> Tuple[Optional[DailyOutfitDTO], Optional[DailyOutfitDTO]]:
        """Swap outfits between two days."""
        # Get both daily outfits
        query = select(DailyOutfit).where(
            DailyOutfit.plan_id == str(plan_id),
            DailyOutfit.user_id == str(user_id),
            DailyOutfit.plan_date.in_([swap_data.source_date, swap_data.target_date]),
        )
        
        result = await self.session.execute(query)
        outfits = {d.plan_date: d for d in result.scalars().all()}
        
        source = outfits.get(swap_data.source_date)
        target = outfits.get(swap_data.target_date)
        
        if not source or not target:
            return None, None
        
        # Swap outfit data
        source.outfit_data, target.outfit_data = target.outfit_data, source.outfit_data
        source.weather_data, target.weather_data = target.weather_data, source.weather_data
        source.alternative_outfits, target.alternative_outfits = target.alternative_outfits, source.alternative_outfits
        
        source.status = OutfitStatus.MODIFIED.value
        target.status = OutfitStatus.MODIFIED.value
        source.updated_at = datetime.now(timezone.utc)
        target.updated_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        
        return self._daily_to_dto(source), self._daily_to_dto(target)
    
    async def record_outfit_worn(
        self,
        user_id: UUID,
        daily_outfit_id: UUID,
        actual_outfit: Optional[Dict[str, Any]] = None,
        satisfaction: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Optional[OutfitHistoryDTO]:
        """Record that an outfit was worn (for learning)."""
        query = select(DailyOutfit).where(
            DailyOutfit.id == str(daily_outfit_id),
            DailyOutfit.user_id == str(user_id),
        )
        
        result = await self.session.execute(query)
        daily = result.scalar_one_or_none()
        
        if not daily:
            return None
        
        # Determine deviation
        deviation_type = DeviationType.NONE
        if actual_outfit:
            deviation_type = self._calculate_deviation(daily.outfit_data, actual_outfit)
        
        # Create history entry
        history = OutfitHistory(
            user_id=str(user_id),
            daily_outfit_id=str(daily_outfit_id),
            plan_id=daily.plan_id,
            worn_date=daily.plan_date,
            planned_outfit=daily.outfit_data,
            actual_outfit=actual_outfit,
            deviation_type=deviation_type.value if deviation_type != DeviationType.NONE else None,
            satisfaction_score=satisfaction,
            notes=notes,
        )
        
        self.session.add(history)
        
        # Update daily status
        daily.status = OutfitStatus.WORN.value
        daily.worn_at = datetime.now(timezone.utc)
        if satisfaction:
            daily.user_rating = satisfaction
        
        await self.session.commit()
        await self.session.refresh(history)
        
        return OutfitHistoryDTO(
            id=str(history.id),
            user_id=str(history.user_id),
            worn_date=history.worn_date,
            planned_outfit=history.planned_outfit,
            actual_outfit=history.actual_outfit,
            deviation_type=history.deviation_type,
            satisfaction_score=history.satisfaction_score,
            would_wear_again=history.would_wear_again,
            notes=history.notes,
            created_at=history.created_at,
        )
    
    async def get_suggestions_for_day(
        self,
        user_id: UUID,
        request: OutfitSuggestionRequestDTO,
    ) -> List[OutfitSuggestionDTO]:
        """Get outfit suggestions for a specific day."""
        prefs = await self.get_or_create_preferences(user_id)
        
        wardrobe_items = await self._get_wardrobe_items(user_id)
        style_dna = await self._get_style_dna(user_id)
        
        weather = request.weather_override
        if not weather:
            weather = await self.weather_service.get_weather_for_date(
                request.date, prefs.location or {}
            )
        
        events = request.events_override
        if not events:
            events = await self.calendar_service.get_events_for_date(user_id, request.date)
        
        occasion = request.occasion or self._determine_occasion(events)
        recently_worn = await self._get_recently_worn_items(user_id, 7)
        
        suggestions = []
        
        for _ in range(5):  # Generate 5 suggestions
            outfit_data, items = await self._generate_outfit(
                user_id=user_id,
                target_date=request.date,
                wardrobe_items=wardrobe_items,
                style_dna=style_dna,
                weather=weather,
                events=events,
                occasion=occasion,
                recently_worn=recently_worn,
                item_usage={},
                max_frequency=10,  # Allow more flexibility for suggestions
                prefer_favorites=True,
                excluded_ids=request.excluded_item_ids,
                preferred_ids=request.preferred_item_ids,
            )
            
            style_score = self._calculate_style_match(outfit_data, style_dna)
            weather_score = self._calculate_weather_match(outfit_data, weather)
            occasion_score = self._calculate_occasion_match(outfit_data, occasion)
            overall = (style_score + weather_score + occasion_score) / 3
            
            suggestions.append(OutfitSuggestionDTO(
                outfit_data=outfit_data,
                items=[OutfitItemDTO(**item) for item in items],
                occasion=occasion,
                confidence=overall,
                style_match_score=style_score,
                weather_match_score=weather_score,
                occasion_match_score=occasion_score,
                overall_score=overall,
                reasoning=self._generate_reasoning(style_score, weather_score, occasion_score),
            ))
        
        # Sort by overall score
        suggestions.sort(key=lambda x: x.overall_score, reverse=True)
        
        return suggestions
    
    async def get_weekly_summary(
        self,
        user_id: UUID,
        plan_id: UUID,
    ) -> Optional[WeeklyPlanSummaryDTO]:
        """Get summary statistics for a weekly plan."""
        plan = await self.get_plan(user_id, plan_id)
        if not plan:
            return None
        
        daily_outfits = plan.daily_outfits
        
        ratings = [d.user_rating for d in daily_outfits if d.user_rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        
        occasions = {}
        for d in daily_outfits:
            occ = d.primary_occasion or "everyday"
            occasions[occ] = occasions.get(occ, 0) + 1
        
        top_occasions = [
            {"occasion": k, "count": v}
            for k, v in sorted(occasions.items(), key=lambda x: x[1], reverse=True)[:3]
        ]
        
        return WeeklyPlanSummaryDTO(
            plan_id=plan.id,
            week_start=plan.week_start_date,
            week_end=plan.week_end_date,
            total_days=7,
            days_planned=len([d for d in daily_outfits if d.outfit_data]),
            days_worn=len([d for d in daily_outfits if d.status == OutfitStatus.WORN.value]),
            days_skipped=len([d for d in daily_outfits if d.status == OutfitStatus.SKIPPED.value]),
            average_rating=avg_rating,
            top_occasions=top_occasions,
            weather_summary={},
            style_diversity_score=self._calculate_diversity_score(daily_outfits),
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # OUTFIT GENERATION
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _generate_outfit(
        self,
        user_id: UUID,
        target_date: date,
        wardrobe_items: List[Dict[str, Any]],
        style_dna: Dict[str, Any],
        weather: Optional[WeatherDataDTO],
        events: List[CalendarEventDTO],
        occasion: str,
        recently_worn: set,
        item_usage: Dict[str, int],
        max_frequency: int,
        prefer_favorites: bool,
        excluded_ids: List[str] = None,
        preferred_ids: List[str] = None,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Generate an outfit for a specific day.
        
        Returns:
            Tuple of (outfit_data dict, items list)
        """
        excluded_ids = excluded_ids or []
        preferred_ids = preferred_ids or []
        
        # Filter available items
        available_items = self._filter_available_items(
            items=wardrobe_items,
            recently_worn=recently_worn,
            item_usage=item_usage,
            max_frequency=max_frequency,
            excluded_ids=excluded_ids,
        )
        
        # Score items for this context
        scored_items = []
        for item in available_items:
            score = self._score_item(
                item=item,
                style_dna=style_dna,
                weather=weather,
                occasion=occasion,
                prefer_favorites=prefer_favorites,
                preferred_ids=preferred_ids,
            )
            scored_items.append((item, score))
        
        # Sort by score
        scored_items.sort(key=lambda x: x[1], reverse=True)
        
        # Select items for outfit composition
        selected_items = []
        categories_covered = set()
        
        # First, try to get essential items
        for category_group in ESSENTIAL_CATEGORIES:
            category_items = [
                (item, score) for item, score in scored_items
                if self._get_category_group(item.get("category", "")) == category_group
                and category_group not in categories_covered
            ]
            
            if category_items:
                best_item = category_items[0][0]
                selected_items.append(best_item)
                categories_covered.add(category_group)
        
        # Check if we need dress instead
        if "tops" not in categories_covered and "bottoms" not in categories_covered:
            dress_items = [
                (item, score) for item, score in scored_items
                if self._get_category_group(item.get("category", "")) == "dresses"
            ]
            if dress_items:
                selected_items.append(dress_items[0][0])
                categories_covered.add("dresses")
                categories_covered.add("tops")
                categories_covered.add("bottoms")
        
        # Add shoes
        if "shoes" not in categories_covered:
            shoe_items = [
                (item, score) for item, score in scored_items
                if self._get_category_group(item.get("category", "")) == "shoes"
            ]
            if shoe_items:
                selected_items.append(shoe_items[0][0])
                categories_covered.add("shoes")
        
        # Add accessories
        accessory_items = [
            (item, score) for item, score in scored_items
            if self._get_category_group(item.get("category", "")) == "accessories"
        ]
        # Add 1-2 accessories
        for item, _ in accessory_items[:2]:
            selected_items.append(item)
        
        # Build outfit data
        outfit_data = {
            "title": self._generate_outfit_title(selected_items, occasion),
            "occasion": occasion,
            "items": selected_items,
            "total_price": sum(item.get("price", 0) for item in selected_items),
        }
        
        return outfit_data, selected_items
    
    async def _generate_alternatives(
        self,
        user_id: UUID,
        target_date: date,
        wardrobe_items: List[Dict[str, Any]],
        style_dna: Dict[str, Any],
        weather: Optional[WeatherDataDTO],
        events: List[CalendarEventDTO],
        occasion: str,
        exclude_items: List[str],
        count: int = 2,
    ) -> List[AlternativeOutfitDTO]:
        """Generate alternative outfit options."""
        alternatives = []
        
        for i in range(count):
            outfit_data, items = await self._generate_outfit(
                user_id=user_id,
                target_date=target_date,
                wardrobe_items=wardrobe_items,
                style_dna=style_dna,
                weather=weather,
                events=events,
                occasion=occasion,
                recently_worn=set(),
                item_usage={},
                max_frequency=10,
                prefer_favorites=False,
                excluded_ids=exclude_items,
            )
            
            alternatives.append(AlternativeOutfitDTO(
                outfit_data=outfit_data,
                reason=f"Alternative {i+1}",
                score=0.7,
            ))
            
            # Add to excluded for next iteration
            exclude_items.extend([item["id"] for item in items])
        
        return alternatives
    
    def _filter_available_items(
        self,
        items: List[Dict[str, Any]],
        recently_worn: set,
        item_usage: Dict[str, int],
        max_frequency: int,
        excluded_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """Filter items based on availability constraints."""
        available = []
        
        for item in items:
            item_id = item.get("id", "")
            
            # Skip excluded
            if item_id in excluded_ids:
                continue
            
            # Skip recently worn
            if item_id in recently_worn:
                continue
            
            # Check frequency
            if item_usage.get(item_id, 0) >= max_frequency:
                continue
            
            available.append(item)
        
        return available
    
    def _score_item(
        self,
        item: Dict[str, Any],
        style_dna: Dict[str, Any],
        weather: Optional[WeatherDataDTO],
        occasion: str,
        prefer_favorites: bool,
        preferred_ids: List[str],
    ) -> float:
        """Score an item for the given context."""
        score = 0.5  # Base score
        
        item_id = item.get("id", "")
        category = item.get("category", "").lower()
        color = item.get("color", "").lower() if item.get("color") else ""
        tags = [t.lower() for t in item.get("tags", [])]
        is_favorite = item.get("is_favorite", False)
        
        # Preferred items boost
        if item_id in preferred_ids:
            score += 0.3
        
        # Favorite boost
        if prefer_favorites and is_favorite:
            score += 0.2
        
        # Style DNA match
        primary_style = style_dna.get("primary_style", "")
        if primary_style:
            style_prefs = STYLE_PREFERENCES.get(primary_style.lower(), {})
            for pref in style_prefs.get("prefer", []):
                if pref in category or pref in tags:
                    score += 0.15
            for avoid in style_prefs.get("avoid", []):
                if avoid in category or avoid in tags:
                    score -= 0.15
        
        # Color preference
        preferred_colors = style_dna.get("color_preferences", {}).get("primary", [])
        if color in [c.lower() for c in preferred_colors]:
            score += 0.1
        
        # Occasion match
        occ_prefs = OCCASION_PREFERENCES.get(occasion, {})
        for pref in occ_prefs.get("prefer", []):
            if pref in category or pref in tags:
                score += 0.1
        for avoid in occ_prefs.get("avoid", []):
            if avoid in category or avoid in tags:
                score -= 0.2
        
        # Weather match
        if weather:
            weather_rules = self.weather_service.get_weather_outfit_rules(weather)
            for avoid in weather_rules.get("avoid", []):
                if avoid in category or avoid in tags:
                    score -= 0.15
            for pref in weather_rules.get("prefer", []):
                if pref in category or pref in tags:
                    score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _get_category_group(self, category: str) -> str:
        """Get the category group for an item."""
        category_lower = category.lower()
        
        for group, categories in OUTFIT_CATEGORIES.items():
            if any(cat in category_lower for cat in categories):
                return group
        
        return "accessories"
    
    def _determine_occasion(self, events: List[CalendarEventDTO]) -> str:
        """Determine primary occasion from events."""
        if not events:
            return "everyday"
        
        # Find most important event
        most_important = max(events, key=lambda e: e.importance or 5)
        
        return self.calendar_service.get_occasion_for_event(most_important)
    
    def _calculate_style_match(
        self,
        outfit_data: Dict[str, Any],
        style_dna: Dict[str, Any],
    ) -> float:
        """Calculate style match score."""
        if not style_dna:
            return 0.5
        
        score = 0.5
        primary_style = style_dna.get("primary_style", "").lower()
        
        if not primary_style:
            return 0.5
        
        style_prefs = STYLE_PREFERENCES.get(primary_style, {})
        items = outfit_data.get("items", [])
        
        for item in items:
            category = item.get("category", "").lower()
            tags = [t.lower() for t in item.get("tags", [])]
            
            for pref in style_prefs.get("prefer", []):
                if pref in category or pref in tags:
                    score += 0.1
            
            for avoid in style_prefs.get("avoid", []):
                if avoid in category or avoid in tags:
                    score -= 0.15
        
        return max(0.0, min(1.0, score))
    
    def _calculate_weather_match(
        self,
        outfit_data: Dict[str, Any],
        weather: Optional[WeatherDataDTO],
    ) -> float:
        """Calculate weather match score."""
        if not weather:
            return 0.5
        
        return self.weather_service.calculate_weather_match_score(outfit_data, weather)
    
    def _calculate_occasion_match(
        self,
        outfit_data: Dict[str, Any],
        occasion: str,
    ) -> float:
        """Calculate occasion match score."""
        if not occasion:
            return 0.5
        
        score = 0.5
        occ_prefs = OCCASION_PREFERENCES.get(occasion, {})
        items = outfit_data.get("items", [])
        
        for item in items:
            category = item.get("category", "").lower()
            tags = [t.lower() for t in item.get("tags", [])]
            
            for pref in occ_prefs.get("prefer", []):
                if pref in category or pref in tags:
                    score += 0.1
            
            for avoid in occ_prefs.get("avoid", []):
                if avoid in category or avoid in tags:
                    score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _calculate_diversity_score(
        self,
        daily_outfits: List[DailyOutfitDTO],
    ) -> float:
        """Calculate style diversity score for the week."""
        if not daily_outfits:
            return 0.0
        
        all_items = []
        for daily in daily_outfits:
            items = daily.outfit.get("items", [])
            all_items.extend([i.get("id") for i in items])
        
        if not all_items:
            return 0.0
        
        unique_items = set(all_items)
        diversity = len(unique_items) / len(all_items)
        
        return round(diversity, 2)
    
    def _calculate_deviation(
        self,
        planned: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> DeviationType:
        """Calculate deviation between planned and actual outfit."""
        planned_items = {i.get("id") for i in planned.get("items", [])}
        actual_items = {i.get("id") for i in actual.get("items", [])}
        
        if planned_items == actual_items:
            return DeviationType.NONE
        
        overlap = len(planned_items & actual_items)
        total = max(len(planned_items), len(actual_items))
        
        if total == 0:
            return DeviationType.NONE
        
        similarity = overlap / total
        
        if similarity >= 0.7:
            return DeviationType.MINOR
        elif similarity >= 0.3:
            return DeviationType.MAJOR
        else:
            return DeviationType.COMPLETELY_DIFFERENT
    
    def _generate_outfit_title(
        self,
        items: List[Dict[str, Any]],
        occasion: str,
    ) -> str:
        """Generate a title for the outfit."""
        occasion_titles = {
            "work": "Work Ready",
            "formal": "Elegant Evening",
            "casual": "Casual Chic",
            "date_night": "Date Night Look",
            "party": "Party Ready",
            "athletic": "Active Style",
            "everyday": "Everyday Essential",
        }
        
        base = occasion_titles.get(occasion, "Styled Look")
        
        # Add color if dominant
        colors = [i.get("color") for i in items if i.get("color")]
        if colors:
            most_common = max(set(colors), key=colors.count)
            return f"{most_common.title()} {base}"
        
        return base
    
    def _generate_reasoning(
        self,
        style_score: float,
        weather_score: float,
        occasion_score: float,
    ) -> str:
        """Generate reasoning text for the suggestion."""
        reasons = []
        
        if style_score >= 0.7:
            reasons.append("Matches your style preferences")
        if weather_score >= 0.7:
            reasons.append("Perfect for the weather")
        if occasion_score >= 0.7:
            reasons.append("Great for the occasion")
        
        if not reasons:
            reasons.append("A balanced outfit choice")
        
        return ". ".join(reasons) + "."
    
    # ─────────────────────────────────────────────────────────────────────────
    # DATA FETCHING
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _get_wardrobe_items(
        self,
        user_id: UUID,
    ) -> List[Dict[str, Any]]:
        """Get user's wardrobe items."""
        query = select(WardrobeItem).where(
            WardrobeItem.owner_user_id == str(user_id),
        )
        
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        return [
            {
                "id": str(item.id),
                "name": item.name,
                "brand": item.brand,
                "category": item.category,
                "color": item.color,
                "size": item.size,
                "price": float(item.price) if item.price else None,
                "image_url": item.image_url,
                "tags": item.tags or [],
                "is_favorite": item.tags.get("favorite", False) if item.tags else False,
            }
            for item in items
        ]
    
    async def _get_style_dna(
        self,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """Get user's style DNA profile."""
        try:
            from services.style_dna_service import StyleDNAService
            
            service = StyleDNAService(self.session)
            profile = await service._get_profile(user_id)
            
            if profile:
                return {
                    "primary_style": str(profile.primary_style) if profile.primary_style else None,
                    "secondary_styles": [str(s) for s in profile.secondary_styles] if profile.secondary_styles else [],
                    "color_preferences": profile.color_preferences or {},
                    "fit_preference": str(profile.fit_preference) if profile.fit_preference else None,
                    "occasion_preferences": profile.occasion_preferences or {},
                    "budget_level": str(profile.budget_level) if profile.budget_level else None,
                }
        except Exception as e:
            logger.warning(f"Failed to get style DNA: {e}")
        
        return {}
    
    async def _get_recently_worn_items(
        self,
        user_id: UUID,
        days: int,
    ) -> set:
        """Get items worn recently."""
        cutoff = date.today() - timedelta(days=days)
        
        query = select(OutfitHistory).where(
            OutfitHistory.user_id == str(user_id),
            OutfitHistory.worn_date >= cutoff,
        )
        
        result = await self.session.execute(query)
        history = result.scalars().all()
        
        recently_worn = set()
        for h in history:
            outfit = h.actual_outfit or h.planned_outfit
            if outfit:
                for item in outfit.get("items", []):
                    recently_worn.add(item.get("id"))
        
        return recently_worn
    
    async def _get_plan_for_week(
        self,
        user_id: UUID,
        week_start: date,
    ) -> Optional[ClosetPlan]:
        """Get existing plan for a specific week."""
        query = select(ClosetPlan).options(
            selectinload(ClosetPlan.daily_outfits)
        ).where(
            ClosetPlan.user_id == str(user_id),
            ClosetPlan.week_start_date == week_start,
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    def _get_week_start(self, d: date) -> date:
        """Get the start of the week (Sunday) for a date."""
        return d - timedelta(days=(d.weekday() + 1) % 7)
    
    # ─────────────────────────────────────────────────────────────────────────
    # DTO CONVERSION
    # ─────────────────────────────────────────────────────────────────────────
    
    def _plan_to_dto(self, plan: ClosetPlan) -> ClosetPlanDTO:
        """Convert plan to DTO."""
        daily_dtos = [self._daily_to_dto(d) for d in plan.daily_outfits]
        
        return ClosetPlanDTO(
            id=str(plan.id),
            user_id=str(plan.user_id),
            week_start_date=plan.week_start_date,
            week_end_date=plan.week_end_date,
            plan_name=plan.plan_name,
            is_active=plan.is_active,
            is_template=plan.is_template,
            generation_context=plan.generation_context or {},
            total_outfits=plan.total_outfits or 0,
            days_planned=plan.days_planned or 0,
            daily_outfits=daily_dtos,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )
    
    def _daily_to_dto(self, daily: DailyOutfit) -> DailyOutfitDTO:
        """Convert daily outfit to DTO."""
        items = []
        outfit_data = daily.outfit_data or {}
        for item in outfit_data.get("items", []):
            items.append(OutfitItemDTO(
                id=item.get("id", ""),
                name=item.get("name", ""),
                category=item.get("category", ""),
                color=item.get("color"),
                image_url=item.get("image_url"),
                brand=item.get("brand"),
                price=item.get("price"),
            ))
        
        weather = None
        if daily.weather_data:
            weather = WeatherDataDTO(**daily.weather_data)
        
        events = []
        if daily.calendar_events:
            for e in daily.calendar_events:
                events.append(CalendarEventDTO(
                    id=e.get("id", ""),
                    title=e.get("title", ""),
                    time=e.get("time"),
                    end_time=e.get("end_time"),
                    type=e.get("type"),
                    location=e.get("location"),
                    dress_code=e.get("dress_code"),
                    importance=e.get("importance", 5),
                ))
        
        alternatives = []
        if daily.alternative_outfits:
            for a in daily.alternative_outfits:
                alternatives.append(AlternativeOutfitDTO(
                    outfit_data=a.get("outfit_data", {}),
                    reason=a.get("reason"),
                    score=a.get("score"),
                ))
        
        return DailyOutfitDTO(
            id=str(daily.id),
            plan_id=str(daily.plan_id),
            plan_date=daily.plan_date,
            day_of_week=daily.day_of_week,
            day_name=DAY_NAMES[daily.day_of_week],
            outfit=outfit_data,
            items=items,
            weather=weather,
            events=events,
            primary_occasion=daily.primary_occasion,
            occasion_confidence=float(daily.occasion_confidence) if daily.occasion_confidence else 0.0,
            alternatives=alternatives,
            status=daily.status,
            worn_at=daily.worn_at,
            user_rating=daily.user_rating,
            user_notes=daily.user_notes,
            style_match_score=float(daily.style_match_score) if daily.style_match_score else None,
            weather_match_score=float(daily.weather_match_score) if daily.weather_match_score else None,
            occasion_match_score=float(daily.occasion_match_score) if daily.occasion_match_score else None,
            overall_score=float(daily.overall_score) if daily.overall_score else None,
            created_at=daily.created_at,
            updated_at=daily.updated_at,
        )
