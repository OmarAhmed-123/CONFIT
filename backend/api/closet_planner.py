"""
CONFIT Backend - Closet Planner API Routes
==========================================
Smart Closet Planner endpoints for weekly outfit planning.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks

from api.deps import get_current_user
from core.security.rbac import AuthContext
from services.closet_planner_service import ClosetPlannerService
from models.closet_planner_models import (
    ClosetPlanDTO,
    ClosetPlanCreateDTO,
    DailyOutfitDTO,
    DailyOutfitUpdateDTO,
    OutfitSwapDTO,
    OutfitSuggestionRequestDTO,
    OutfitSuggestionDTO,
    PlannerPreferencesDTO,
    PlannerPreferencesUpdateDTO,
    WeeklyPlanSummaryDTO,
    OutfitHistoryDTO,
    CalendarEventDTO,
    CalendarSyncRequestDTO,
    WeatherForecastDTO,
)


router = APIRouter(prefix="/planner", tags=["Closet Planner"])


# ─────────────────────────────────────────────────────────────────────────────
# DEPENDENCIES
# ─────────────────────────────────────────────────────────────────────────────

async def get_planner_service() -> ClosetPlannerService:
    """Get closet planner service instance."""
    from database.session import get_async_session
    async for session in get_async_session():
        service = ClosetPlannerService(session)
        try:
            yield service
        finally:
            await service.close()


# ─────────────────────────────────────────────────────────────────────────────
# PREFERENCES
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/preferences",
    response_model=PlannerPreferencesDTO,
    summary="Get planner preferences",
)
async def get_preferences(
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """Get user's planner preferences."""
    prefs = await planner_service.get_or_create_preferences(
        user_id=UUID(current_user.user_id)
    )
    
    return PlannerPreferencesDTO(
        planning_day=prefs.planning_day or 0,
        planning_time=prefs.planning_time.strftime("%H:%M") if prefs.planning_time else "20:00",
        auto_generate=prefs.auto_generate if prefs.auto_generate is not None else True,
        location=prefs.location or {},
        temperature_unit=prefs.temperature_unit or "celsius",
        weather_sensitivity=prefs.weather_sensitivity or {},
        calendar_providers=prefs.calendar_providers or [],
        prefer_favorite_items=prefs.prefer_favorite_items if prefs.prefer_favorite_items is not None else True,
        avoid_recently_worn=prefs.avoid_recently_worn if prefs.avoid_recently_worn is not None else True,
        recently_worn_days=prefs.recently_worn_days or 7,
        max_item_frequency=prefs.max_item_frequency or 2,
        occasion_priorities=prefs.occasion_priorities or {},
        notify_new_plan=prefs.notify_new_plan if prefs.notify_new_plan is not None else True,
        notify_daily=prefs.notify_daily if prefs.notify_daily is not None else True,
        notify_daily_time=prefs.notify_daily_time.strftime("%H:%M") if prefs.notify_daily_time else "07:00",
    )


@router.patch(
    "/preferences",
    response_model=PlannerPreferencesDTO,
    summary="Update planner preferences",
)
async def update_preferences(
    update_data: PlannerPreferencesUpdateDTO,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """Update user's planner preferences."""
    prefs = await planner_service.update_preferences(
        user_id=UUID(current_user.user_id),
        update_data=update_data,
    )
    
    return PlannerPreferencesDTO(
        planning_day=prefs.planning_day or 0,
        planning_time=prefs.planning_time.strftime("%H:%M") if prefs.planning_time else "20:00",
        auto_generate=prefs.auto_generate if prefs.auto_generate is not None else True,
        location=prefs.location or {},
        temperature_unit=prefs.temperature_unit or "celsius",
        weather_sensitivity=prefs.weather_sensitivity or {},
        calendar_providers=prefs.calendar_providers or [],
        prefer_favorite_items=prefs.prefer_favorite_items if prefs.prefer_favorite_items is not None else True,
        avoid_recently_worn=prefs.avoid_recently_worn if prefs.avoid_recently_worn is not None else True,
        recently_worn_days=prefs.recently_worn_days or 7,
        max_item_frequency=prefs.max_item_frequency or 2,
        occasion_priorities=prefs.occasion_priorities or {},
        notify_new_plan=prefs.notify_new_plan if prefs.notify_new_plan is not None else True,
        notify_daily=prefs.notify_daily if prefs.notify_daily is not None else True,
        notify_daily_time=prefs.notify_daily_time.strftime("%H:%M") if prefs.notify_daily_time else "07:00",
    )


# ─────────────────────────────────────────────────────────────────────────────
# PLANS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/current",
    response_model=Optional[ClosetPlanDTO],
    summary="Get current week's plan",
)
async def get_current_plan(
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """Get the current week's outfit plan."""
    return await planner_service.get_current_plan(
        user_id=UUID(current_user.user_id)
    )


@router.get(
    "/{plan_id}",
    response_model=ClosetPlanDTO,
    summary="Get specific plan",
)
async def get_plan(
    plan_id: str,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """Get a specific outfit plan by ID."""
    plan = await planner_service.get_plan(
        user_id=UUID(current_user.user_id),
        plan_id=UUID(plan_id),
    )
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    return plan


@router.post(
    "",
    response_model=ClosetPlanDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Generate weekly plan",
)
async def generate_plan(
    request: ClosetPlanCreateDTO,
    background_tasks: BackgroundTasks,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """
    Generate a new weekly outfit plan.
    
    The system considers:
    - User's wardrobe items
    - Style DNA preferences
    - Weather forecast
    - Calendar events
    """
    return await planner_service.generate_weekly_plan(
        user_id=UUID(current_user.user_id),
        request=request,
    )


@router.get(
    "/{plan_id}/summary",
    response_model=WeeklyPlanSummaryDTO,
    summary="Get plan summary",
)
async def get_plan_summary(
    plan_id: str,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """Get summary statistics for a weekly plan."""
    summary = await planner_service.get_weekly_summary(
        user_id=UUID(current_user.user_id),
        plan_id=UUID(plan_id),
    )
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# DAILY OUTFITS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/daily/{daily_outfit_id}",
    response_model=DailyOutfitDTO,
    summary="Get daily outfit",
)
async def get_daily_outfit(
    daily_outfit_id: str,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """Get a specific daily outfit."""
    # Get through plan query
    plan = await planner_service.get_current_plan(
        user_id=UUID(current_user.user_id)
    )
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current plan found"
        )
    
    for daily in plan.daily_outfits:
        if daily.id == daily_outfit_id:
            return daily
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Daily outfit not found"
    )


@router.patch(
    "/daily/{daily_outfit_id}",
    response_model=DailyOutfitDTO,
    summary="Update daily outfit",
)
async def update_daily_outfit(
    daily_outfit_id: str,
    update_data: DailyOutfitUpdateDTO,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """Update a daily outfit (modify outfit, mark as worn, add rating)."""
    daily = await planner_service.update_daily_outfit(
        user_id=UUID(current_user.user_id),
        daily_outfit_id=UUID(daily_outfit_id),
        update_data=update_data,
    )
    
    if not daily:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily outfit not found"
        )
    
    return daily


@router.post(
    "/daily/{daily_outfit_id}/worn",
    response_model=OutfitHistoryDTO,
    summary="Record outfit worn",
)
async def record_outfit_worn(
    daily_outfit_id: str,
    actual_outfit: Optional[dict] = None,
    satisfaction: Optional[int] = Query(None, ge=1, le=5),
    notes: Optional[str] = None,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """Record that an outfit was worn (for learning and history)."""
    history = await planner_service.record_outfit_worn(
        user_id=UUID(current_user.user_id),
        daily_outfit_id=UUID(daily_outfit_id),
        actual_outfit=actual_outfit,
        satisfaction=satisfaction,
        notes=notes,
    )
    
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily outfit not found"
        )
    
    return history


@router.post(
    "/{plan_id}/swap",
    response_model=List[DailyOutfitDTO],
    summary="Swap outfits between days",
)
async def swap_outfits(
    plan_id: str,
    swap_data: OutfitSwapDTO,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """Swap outfits between two days in a plan."""
    source, target = await planner_service.swap_outfits(
        user_id=UUID(current_user.user_id),
        plan_id=UUID(plan_id),
        swap_data=swap_data,
    )
    
    if not source or not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find outfits to swap"
        )
    
    return [source, target]


# ─────────────────────────────────────────────────────────────────────────────
# SUGGESTIONS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/suggestions",
    response_model=List[OutfitSuggestionDTO],
    summary="Get outfit suggestions for a day",
)
async def get_suggestions(
    request: OutfitSuggestionRequestDTO,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """
    Get AI-powered outfit suggestions for a specific day.
    
    Returns multiple outfit options ranked by:
    - Style match score
    - Weather match score
    - Occasion match score
    """
    return await planner_service.get_suggestions_for_day(
        user_id=UUID(current_user.user_id),
        request=request,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CALENDAR INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/calendar/sync",
    response_model=List[CalendarEventDTO],
    summary="Sync calendar events",
)
async def sync_calendar(
    request: CalendarSyncRequestDTO,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """
    Sync calendar events from external provider.
    
    Supports Google Calendar, Outlook, and Apple Calendar.
    Requires OAuth access token for the provider.
    """
    # Note: In production, access token would come from OAuth flow
    access_token = None  # TODO: Get from user's connected accounts
    
    events = await planner_service.calendar_service.sync_events(
        user_id=UUID(current_user.user_id),
        request=request,
        access_token=access_token,
    )
    
    return events


@router.get(
    "/calendar/events",
    response_model=List[CalendarEventDTO],
    summary="Get calendar events",
)
async def get_calendar_events(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """Get cached calendar events for a date range."""
    from datetime import timedelta
    
    start = start_date or date.today()
    end = end_date or start + timedelta(days=7)
    
    return await planner_service.calendar_service._get_cached_events(
        user_id=UUID(current_user.user_id),
        start_date=start,
        end_date=end,
    )


@router.post(
    "/calendar/events",
    response_model=CalendarEventDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Add manual calendar event",
)
async def add_calendar_event(
    event: CalendarEventDTO,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """Add a manual calendar event for planning context."""
    return await planner_service.calendar_service.add_manual_event(
        user_id=UUID(current_user.user_id),
        event=event,
    )


@router.delete(
    "/calendar/events/{event_id}",
    summary="Delete calendar event",
)
async def delete_calendar_event(
    event_id: str,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """Delete a calendar event."""
    removed = await planner_service.calendar_service.remove_event(
        user_id=UUID(current_user.user_id),
        event_id=event_id,
    )
    
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    return {"message": "Event deleted"}


# ─────────────────────────────────────────────────────────────────────────────
# WEATHER
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/weather",
    response_model=WeatherForecastDTO,
    summary="Get weather forecast",
)
async def get_weather(
    start_date: Optional[date] = None,
    current_user: AuthContext = Depends(get_current_user),
    planner_service: ClosetPlannerService = Depends(get_planner_service),
):
    """Get weather forecast for planning."""
    from datetime import timedelta
    
    prefs = await planner_service.get_or_create_preferences(
        user_id=UUID(current_user.user_id)
    )
    
    start = start_date or date.today()
    forecasts = await planner_service.weather_service.get_week_forecast(
        start_date=start,
        location=prefs.location or {},
    )
    
    return WeatherForecastDTO(
        location=prefs.location.get("city", "Unknown") if prefs.location else "Unknown",
        forecasts=[f.model_dump() for f in forecasts],
        fetched_at=date.today(),
        source="openweathermap",
    )
