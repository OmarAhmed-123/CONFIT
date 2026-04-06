"""
CONFIT Backend — Calendar Integration Service
=============================================
Calendar API integration for outfit planning.
Supports Google Calendar, Apple Calendar, and Outlook.
"""

import os
import logging
from datetime import datetime, timezone, timedelta, date, time
from typing import Any, Dict, List, Optional
from uuid import UUID
import json
import asyncio

import httpx
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.closet_planner_models import (
    CalendarEventsCache,
    CalendarEventDTO,
    CalendarProvider,
    CalendarSyncRequestDTO,
    EventType,
)
from database.models import UUIDType

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# EVENT TYPE MAPPING
# ─────────────────────────────────────────────────────────────────────────────

# Keywords to detect event types from titles
EVENT_TYPE_KEYWORDS = {
    EventType.MEETING: ["meeting", "call", "conference", "sync", "standup", "review", "discussion"],
    EventType.WORK: ["work", "office", "shift", "presentation", "deadline", "project"],
    EventType.PARTY: ["party", "celebration", "birthday", "anniversary", "club", "night out"],
    EventType.DINNER: ["dinner", "lunch", "brunch", "restaurant", "cafe", "food"],
    EventType.DATE: ["date", "romantic", "valentine"],
    EventType.FORMAL: ["wedding", "gala", "formal", "black tie", "ceremony", "award"],
    EventType.ATHLETIC: ["gym", "workout", "yoga", "run", "sports", "game", "training"],
    EventType.TRAVEL: ["flight", "travel", "airport", "trip", "vacation"],
    EventType.SPECIAL_EVENT: ["concert", "theater", "show", "exhibition", "festival"],
}

# Event type to occasion mapping
EVENT_TYPE_TO_OCCASION = {
    EventType.MEETING: "work",
    EventType.WORK: "work",
    EventType.PARTY: "party",
    EventType.DINNER: "casual",
    EventType.DATE: "date_night",
    EventType.FORMAL: "formal",
    EventType.ATHLETIC: "athletic",
    EventType.TRAVEL: "casual",
    EventType.SPECIAL_EVENT: "special_event",
    EventType.CASUAL: "casual",
    EventType.OTHER: "everyday",
}

# Dress code detection keywords
DRESS_CODE_KEYWORDS = {
    "black_tie": ["black tie", "formal attire", "tuxedo"],
    "formal": ["formal", "business formal", "suit required"],
    "business_casual": ["business casual", "smart casual"],
    "casual": ["casual", "relaxed", "informal"],
    "cocktail": ["cocktail", "cocktail attire"],
    "smart": ["smart", "dressy", "semi-formal"],
    "athletic": ["athletic", "sportswear", "activewear", "gym clothes"],
}


# ─────────────────────────────────────────────────────────────────────────────
# CALENDAR SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class CalendarService:
    """
    Calendar integration service for outfit planning.
    Supports Google Calendar, Apple Calendar, and Outlook.
    """
    
    CACHE_DURATION_DAYS = 7  # Cache events for 7 days
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self._google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self._outlook_client_id = os.getenv("OUTLOOK_CLIENT_ID")
        self._outlook_client_secret = os.getenv("OUTLOOK_CLIENT_SECRET")
        self._client = httpx.AsyncClient(timeout=10.0)
    
    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()
    
    async def sync_events(
        self,
        user_id: UUID,
        request: CalendarSyncRequestDTO,
        access_token: Optional[str] = None,
    ) -> List[CalendarEventDTO]:
        """
        Sync calendar events from external provider.
        
        Args:
            user_id: User ID
            request: Sync request with provider and date range
            access_token: OAuth access token for the provider
            
        Returns:
            List of synced events
        """
        start_date = request.start_date or date.today()
        end_date = request.end_date or start_date + timedelta(days=7)
        
        # Check cache first if not forcing refresh
        if not request.force_refresh:
            cached = await self._get_cached_events(user_id, start_date, end_date)
            if cached:
                logger.debug(f"Using {len(cached)} cached events for user {user_id}")
                return cached
        
        # Fetch from provider
        events = []
        
        if request.provider == CalendarProvider.GOOGLE and access_token:
            events = await self._fetch_google_events(
                access_token, start_date, end_date
            )
        elif request.provider == CalendarProvider.OUTLOOK and access_token:
            events = await self._fetch_outlook_events(
                access_token, start_date, end_date
            )
        elif request.provider == CalendarProvider.APPLE:
            # Apple Calendar requires special handling via CalDAV
            logger.warning("Apple Calendar sync not yet implemented")
            events = []
        elif request.provider == CalendarProvider.MANUAL:
            # Manual events are stored directly
            events = await self._get_cached_events(user_id, start_date, end_date)
        
        # Cache events
        if events:
            await self._cache_events(user_id, request.provider, events)
        
        return events
    
    async def get_events_for_date(
        self,
        user_id: UUID,
        target_date: date,
    ) -> List[CalendarEventDTO]:
        """
        Get calendar events for a specific date.
        
        Args:
            user_id: User ID
            target_date: Date to get events for
            
        Returns:
            List of events on that date
        """
        return await self._get_cached_events(user_id, target_date, target_date)
    
    async def get_events_for_week(
        self,
        user_id: UUID,
        start_date: date,
    ) -> Dict[date, List[CalendarEventDTO]]:
        """
        Get calendar events for a week.
        
        Args:
            user_id: User ID
            start_date: Start date of the week
            
        Returns:
            Dict mapping dates to events
        """
        end_date = start_date + timedelta(days=6)
        events = await self._get_cached_events(user_id, start_date, end_date)
        
        # Group by date
        events_by_date = {}
        for i in range(7):
            d = start_date + timedelta(days=i)
            events_by_date[d] = []
        
        for event in events:
            if event.event_date in events_by_date:
                events_by_date[event.event_date].append(event)
        
        return events_by_date
    
    async def add_manual_event(
        self,
        user_id: UUID,
        event: CalendarEventDTO,
    ) -> CalendarEventDTO:
        """
        Add a manual calendar event.
        
        Args:
            user_id: User ID
            event: Event data
            
        Returns:
            Created event
        """
        cache_entry = CalendarEventsCache(
            user_id=str(user_id),
            external_id=f"manual_{datetime.now(timezone.utc).timestamp()}",
            provider=CalendarProvider.MANUAL.value,
            event_title=event.title,
            event_date=event.event_date if hasattr(event, 'event_date') else date.today(),
            event_time=event.time,
            event_end_time=event.end_time,
            location=event.location,
            description="",
            dress_code=event.dress_code,
            event_type=event.type,
            importance=event.importance,
            raw_event_data=event.model_dump() if hasattr(event, 'model_dump') else {},
            synced_at=datetime.now(timezone.utc),
        )
        
        self.session.add(cache_entry)
        await self.session.commit()
        await self.session.refresh(cache_entry)
        
        return self._cache_to_dto(cache_entry)
    
    async def remove_event(
        self,
        user_id: UUID,
        event_id: str,
    ) -> bool:
        """
        Remove a calendar event.
        
        Args:
            user_id: User ID
            event_id: Event ID
            
        Returns:
            True if removed, False if not found
        """
        delete_stmt = delete(CalendarEventsCache).where(
            CalendarEventsCache.id == event_id,
            CalendarEventsCache.user_id == str(user_id),
        )
        
        result = await self.session.execute(delete_stmt)
        await self.session.commit()
        
        return result.rowcount > 0
    
    async def _get_cached_events(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> List[CalendarEventDTO]:
        """Get cached events for a date range."""
        query = select(CalendarEventsCache).where(
            CalendarEventsCache.user_id == str(user_id),
            CalendarEventsCache.event_date >= start_date,
            CalendarEventsCache.event_date <= end_date,
        ).order_by(CalendarEventsCache.event_date, CalendarEventsCache.event_time)
        
        result = await self.session.execute(query)
        cached_events = result.scalars().all()
        
        return [self._cache_to_dto(e) for e in cached_events]
    
    def _cache_to_dto(self, cache: CalendarEventsCache) -> CalendarEventDTO:
        """Convert cache entry to DTO."""
        return CalendarEventDTO(
            id=str(cache.id),
            title=cache.event_title,
            time=cache.event_time.strftime("%H:%M") if cache.event_time else None,
            end_time=cache.event_end_time.strftime("%H:%M") if cache.event_end_time else None,
            type=cache.event_type,
            location=cache.location,
            dress_code=cache.dress_code,
            importance=cache.importance or 5,
        )
    
    async def _cache_events(
        self,
        user_id: UUID,
        provider: CalendarProvider,
        events: List[Dict[str, Any]],
    ) -> None:
        """Cache events from provider."""
        for event in events:
            # Check if already exists
            existing_query = select(CalendarEventsCache).where(
                CalendarEventsCache.user_id == str(user_id),
                CalendarEventsCache.external_id == event.get("external_id"),
            )
            existing = await self.session.execute(existing_query)
            existing_entry = existing.scalar_one_or_none()
            
            if existing_entry:
                # Update existing
                existing_entry.event_title = event.get("title", "")
                existing_entry.event_date = event.get("date")
                existing_entry.event_time = event.get("time")
                existing_entry.event_end_time = event.get("end_time")
                existing_entry.location = event.get("location")
                existing_entry.description = event.get("description")
                existing_entry.dress_code = event.get("dress_code")
                existing_entry.event_type = event.get("event_type")
                existing_entry.importance = event.get("importance", 5)
                existing_entry.raw_event_data = event
                existing_entry.synced_at = datetime.now(timezone.utc)
            else:
                # Create new
                cache_entry = CalendarEventsCache(
                    user_id=str(user_id),
                    external_id=event.get("external_id", ""),
                    provider=provider.value,
                    event_title=event.get("title", ""),
                    event_date=event.get("date"),
                    event_time=event.get("time"),
                    event_end_time=event.get("end_time"),
                    location=event.get("location"),
                    description=event.get("description", ""),
                    dress_code=event.get("dress_code"),
                    event_type=event.get("event_type"),
                    importance=event.get("importance", 5),
                    raw_event_data=event,
                    synced_at=datetime.now(timezone.utc),
                )
                self.session.add(cache_entry)
        
        await self.session.commit()
    
    async def _fetch_google_events(
        self,
        access_token: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """Fetch events from Google Calendar."""
        time_min = datetime.combine(start_date, time.min).isoformat() + "Z"
        time_max = datetime.combine(end_date, time.max).isoformat() + "Z"
        
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 100,
        }
        
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        
        try:
            response = await self._client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            events = []
            
            for item in data.get("items", []):
                event = self._parse_google_event(item)
                if event:
                    events.append(event)
            
            return events
        except Exception as e:
            logger.error(f"Failed to fetch Google Calendar events: {e}")
            return []
    
    def _parse_google_event(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Google Calendar event."""
        try:
            # Get start/end times
            start = item.get("start", {})
            end = item.get("end", {})
            
            # Handle all-day events
            if "date" in start:
                event_date = datetime.strptime(start["date"], "%Y-%m-%d").date()
                event_time = None
                end_time = None
            else:
                start_dt = datetime.fromisoformat(start.get("dateTime", "").replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end.get("dateTime", "").replace("Z", "+00:00"))
                event_date = start_dt.date()
                event_time = start_dt.time()
                end_time = end_dt.time()
            
            title = item.get("summary", "Untitled Event")
            
            return {
                "external_id": item.get("id", ""),
                "title": title,
                "date": event_date,
                "time": event_time,
                "end_time": end_time,
                "location": item.get("location"),
                "description": item.get("description", ""),
                "event_type": self._detect_event_type(title).value,
                "dress_code": self._detect_dress_code(title, item.get("description", "")),
                "importance": self._calculate_importance(item),
            }
        except Exception as e:
            logger.warning(f"Failed to parse Google event: {e}")
            return None
    
    async def _fetch_outlook_events(
        self,
        access_token: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """Fetch events from Outlook Calendar."""
        start_dt = datetime.combine(start_date, time.min).isoformat() + "Z"
        end_dt = datetime.combine(end_date, time.max).isoformat() + "Z"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        # Use Microsoft Graph API
        url = f"https://graph.microsoft.com/v1.0/me/calendarView?startDateTime={start_dt}&endDateTime={end_dt}"
        
        try:
            response = await self._client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            events = []
            
            for item in data.get("value", []):
                event = self._parse_outlook_event(item)
                if event:
                    events.append(event)
            
            return events
        except Exception as e:
            logger.error(f"Failed to fetch Outlook Calendar events: {e}")
            return []
    
    def _parse_outlook_event(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Outlook Calendar event."""
        try:
            start = item.get("start", {})
            end = item.get("end", {})
            
            # Parse datetime
            start_dt = datetime.fromisoformat(start.get("dateTime", "").replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.get("dateTime", "").replace("Z", "+00:00"))
            
            title = item.get("subject", "Untitled Event")
            
            return {
                "external_id": item.get("id", ""),
                "title": title,
                "date": start_dt.date(),
                "time": start_dt.time(),
                "end_time": end_dt.time(),
                "location": item.get("location", {}).get("displayName"),
                "description": item.get("bodyPreview", ""),
                "event_type": self._detect_event_type(title).value,
                "dress_code": self._detect_dress_code(title, item.get("bodyPreview", "")),
                "importance": self._calculate_importance(item),
            }
        except Exception as e:
            logger.warning(f"Failed to parse Outlook event: {e}")
            return None
    
    def _detect_event_type(self, title: str) -> EventType:
        """Detect event type from title."""
        title_lower = title.lower()
        
        for event_type, keywords in EVENT_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return event_type
        
        return EventType.OTHER
    
    def _detect_dress_code(
        self,
        title: str,
        description: str = "",
    ) -> Optional[str]:
        """Detect dress code from title and description."""
        combined = (title + " " + description).lower()
        
        for dress_code, keywords in DRESS_CODE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in combined:
                    return dress_code
        
        return None
    
    def _calculate_importance(self, event: Dict[str, Any]) -> int:
        """Calculate event importance score (1-10)."""
        importance = 5  # Default
        
        # Check for importance indicators
        title = event.get("summary", event.get("subject", "")).lower()
        description = event.get("description", event.get("bodyPreview", "")).lower()
        combined = title + " " + description
        
        # High importance keywords
        high_keywords = ["important", "critical", "mandatory", "key", "major", "ceo", "board", "client"]
        for kw in high_keywords:
            if kw in combined:
                importance += 2
                break
        
        # Meeting type importance
        if "interview" in combined:
            importance = 9
        elif "presentation" in combined or "pitch" in combined:
            importance = 8
        elif "wedding" in combined:
            importance = 9
        elif "funeral" in combined:
            importance = 9
        elif "birthday" in combined or "anniversary" in combined:
            importance = 7
        
        # Check if all-day event (often more important)
        if event.get("start", {}).get("date"):
            importance += 1
        
        # Check if has attendees (more important)
        attendees = event.get("attendees", event.get("attendees", []))
        if len(attendees) > 5:
            importance += 1
        
        return min(10, max(1, importance))
    
    def get_occasion_for_event(
        self,
        event: CalendarEventDTO,
    ) -> str:
        """
        Get the appropriate occasion for an event.
        
        Args:
            event: Calendar event
            
        Returns:
            Occasion string for outfit planning
        """
        try:
            event_type = EventType(event.type) if event.type else EventType.OTHER
            return EVENT_TYPE_TO_OCCASION.get(event_type, "everyday")
        except ValueError:
            return "everyday"
    
    def get_dress_code_requirements(
        self,
        event: CalendarEventDTO,
    ) -> Dict[str, Any]:
        """
        Get dress code requirements for an event.
        
        Args:
            event: Calendar event
            
        Returns:
            Dict with dress code requirements
        """
        requirements = {
            "formality_level": "casual",
            "avoid": [],
            "prefer": [],
            "accessories": [],
        }
        
        dress_code = event.dress_code
        
        if dress_code == "black_tie":
            requirements["formality_level"] = "formal"
            requirements["prefer"] = ["tuxedo", "evening_gown", "formal_shoes"]
            requirements["avoid"] = ["casual", "jeans", "sneakers"]
            requirements["accessories"] = ["bow_tie", "evening_bag", "jewelry"]
        elif dress_code == "formal":
            requirements["formality_level"] = "formal"
            requirements["prefer"] = ["suit", "dress", "formal_shoes"]
            requirements["avoid"] = ["casual", "jeans", "sneakers"]
        elif dress_code == "business_casual":
            requirements["formality_level"] = "smart_casual"
            requirements["prefer"] = ["blazer", "dress_shirt", "chinos", "dress"]
            requirements["avoid"] = ["t_shirt", "shorts", "flip_flops"]
        elif dress_code == "cocktail":
            requirements["formality_level"] = "semi_formal"
            requirements["prefer"] = ["cocktail_dress", "suit", "heels"]
            requirements["avoid"] = ["casual", "jeans", "flats"]
        elif dress_code == "smart":
            requirements["formality_level"] = "smart_casual"
            requirements["prefer"] = ["blazer", "nice_top", "dark_jeans", "dress"]
        elif dress_code == "athletic":
            requirements["formality_level"] = "athletic"
            requirements["prefer"] = ["activewear", "sneakers", "sports_top"]
            requirements["avoid"] = ["jeans", "dress_shoes", "jewelry"]
        
        # Adjust based on event type
        if event.type == EventType.ATHLETIC.value:
            requirements["formality_level"] = "athletic"
            requirements["prefer"] = ["activewear", "sneakers"]
        elif event.type == EventType.FORMAL.value:
            requirements["formality_level"] = "formal"
        
        return requirements
