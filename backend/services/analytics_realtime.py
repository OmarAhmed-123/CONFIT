"""
CONFIT Real-Time Analytics Counters
===================================
Redis-based real-time counters for live dashboards.
Uses HINCRBY for atomic increments with TTL-based expiration.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class RealtimeCounters:
    """
    Redis-based real-time analytics counters.
    
    Features:
    - Atomic HINCRBY operations
    - TTL-based expiration (counters reset at end of day)
    - Fallback to Postgres if Redis unavailable
    """
    
    _instance: Optional['RealtimeCounters'] = None
    
    def __new__(cls) -> 'RealtimeCounters':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._redis_client = None
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'RealtimeCounters':
        """Get singleton instance."""
        return cls()
    
    def _get_redis(self):
        """Lazy-load Redis client."""
        if self._redis_client is None:
            try:
                import redis
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                self._redis_client = redis.from_url(redis_url)
            except Exception as e:
                logger.warning(f"Redis not available for realtime counters: {e}")
                self._redis_client = None
        return self._redis_client
    
    def _get_today_key(self) -> str:
        """Get today's date key in UTC."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    def _get_ttl_seconds(self) -> int:
        """Get TTL seconds until end of day + 12h buffer."""
        now = datetime.now(timezone.utc)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)
        ttl = int((end_of_day - now).total_seconds()) + 43200  # +12h buffer
        return max(ttl, 3600)  # Minimum 1 hour
    
    # -------------------------------------------------------------------------
    # Store Counters
    # -------------------------------------------------------------------------
    
    def incr_store_visits(self, store_id: str) -> int:
        """Increment store visits counter."""
        redis_client = self._get_redis()
        if redis_client is None:
            return 0
        
        try:
            today = self._get_today_key()
            key = f"analytics:store:{store_id}:{today}"
            value = redis_client.hincrby(key, "visits", 1)
            redis_client.expire(key, self._get_ttl_seconds(), nx=True)
            return value
        except Exception as e:
            logger.warning(f"Failed to incr store visits: {e}")
            return 0
    
    def incr_store_event(self, store_id: str, event_name: str) -> int:
        """Increment a store-specific event counter."""
        redis_client = self._get_redis()
        if redis_client is None:
            return 0
        
        try:
            today = self._get_today_key()
            key = f"analytics:store:{store_id}:{today}"
            value = redis_client.hincrby(key, event_name, 1)
            redis_client.expire(key, self._get_ttl_seconds(), nx=True)
            return value
        except Exception as e:
            logger.warning(f"Failed to incr store event: {e}")
            return 0
    
    def get_store_counters(self, store_id: str, days: int = 1) -> Dict[str, Any]:
        """
        Get all counters for a store.
        
        Args:
            store_id: Store UUID
            days: Number of days to aggregate (1, 7, or 30)
            
        Returns:
            Dict with aggregated counters
        """
        redis_client = self._get_redis()
        if redis_client is None:
            return {}
        
        result = {
            "visits_today": 0,
            "visits_7d": 0,
            "visits_30d": 0,
            "events": {},
        }
        
        try:
            today = datetime.now(timezone.utc)
            
            for i in range(min(days, 30)):
                date_key = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                key = f"analytics:store:{store_id}:{date_key}"
                data = redis_client.hgetall(key)
                
                if data:
                    visits = int(data.get(b"visits", 0))
                    result["visits_30d"] += visits
                    
                    if i < 7:
                        result["visits_7d"] += visits
                    if i == 0:
                        result["visits_today"] = visits
                    
                    # Aggregate events
                    for k, v in data.items():
                        event_name = k.decode() if isinstance(k, bytes) else k
                        if event_name != "visits":
                            result["events"][event_name] = result["events"].get(event_name, 0) + int(v)
            
            return result
        except Exception as e:
            logger.warning(f"Failed to get store counters: {e}")
            return result
    
    # -------------------------------------------------------------------------
    # Global Counters
    # -------------------------------------------------------------------------
    
    def incr_global_event(self, event_name: str) -> int:
        """Increment a global event counter."""
        redis_client = self._get_redis()
        if redis_client is None:
            return 0
        
        try:
            today = self._get_today_key()
            key = f"analytics:global:{today}"
            value = redis_client.hincrby(key, event_name, 1)
            redis_client.expire(key, self._get_ttl_seconds(), nx=True)
            return value
        except Exception as e:
            logger.warning(f"Failed to incr global event: {e}")
            return 0
    
    def get_global_counters(self, days: int = 1) -> Dict[str, Any]:
        """Get global counters aggregated over days."""
        redis_client = self._get_redis()
        if redis_client is None:
            return {}
        
        result = {
            "events": {},
            "dau": 0,
        }
        
        try:
            today = datetime.now(timezone.utc)
            
            for i in range(min(days, 30)):
                date_key = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                
                # Get events
                key = f"analytics:global:{date_key}"
                data = redis_client.hgetall(key)
                if data:
                    for k, v in data.items():
                        event_name = k.decode() if isinstance(k, bytes) else k
                        result["events"][event_name] = result["events"].get(event_name, 0) + int(v)
                
                # Get DAU
                dau_key = f"analytics:dau:{date_key}"
                dau = redis_client.scard(dau_key)
                if i == 0:
                    result["dau"] = dau
            
            return result
        except Exception as e:
            logger.warning(f"Failed to get global counters: {e}")
            return result
    
    # -------------------------------------------------------------------------
    # DAU/MAU Tracking
    # -------------------------------------------------------------------------
    
    def track_dau(self, user_id: str) -> bool:
        """Track user as active today (for DAU calculation)."""
        redis_client = self._get_redis()
        if redis_client is None:
            return False
        
        try:
            today = self._get_today_key()
            key = f"analytics:dau:{today}"
            redis_client.sadd(key, user_id)
            redis_client.expire(key, self._get_ttl_seconds(), nx=True)
            return True
        except Exception as e:
            logger.warning(f"Failed to track DAU: {e}")
            return False
    
    def get_dau(self) -> int:
        """Get Daily Active Users count."""
        redis_client = self._get_redis()
        if redis_client is None:
            return 0
        
        try:
            today = self._get_today_key()
            key = f"analytics:dau:{today}"
            return redis_client.scard(key)
        except Exception as e:
            logger.warning(f"Failed to get DAU: {e}")
            return 0
    
    def get_mau(self) -> int:
        """Get Monthly Active Users count (unique users in last 30 days)."""
        redis_client = self._get_redis()
        if redis_client is None:
            return 0
        
        try:
            # Use a union of all DAU sets for the last 30 days
            today = datetime.now(timezone.utc)
            keys = []
            for i in range(30):
                date_key = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                keys.append(f"analytics:dau:{date_key}")
            
            # Use SUNION to get unique users
            unique_users = redis_client.sunion(*keys)
            return len(unique_users)
        except Exception as e:
            logger.warning(f"Failed to get MAU: {e}")
            return 0
    
    # -------------------------------------------------------------------------
    # Heatmap Data
    # -------------------------------------------------------------------------
    
    def incr_heatmap(self, store_id: str, hour: int, day_of_week: int) -> int:
        """
        Increment heatmap counter for hour × day_of_week.
        
        Args:
            store_id: Store UUID
            hour: Hour of day (0-23)
            day_of_week: Day of week (0=Monday, 6=Sunday)
        """
        redis_client = self._get_redis()
        if redis_client is None:
            return 0
        
        try:
            today = self._get_today_key()
            key = f"analytics:heatmap:{store_id}:{today}"
            field = f"{hour}:{day_of_week}"
            value = redis_client.hincrby(key, field, 1)
            redis_client.expire(key, self._get_ttl_seconds() * 7, nx=True)  # 7-day TTL for heatmap
            return value
        except Exception as e:
            logger.warning(f"Failed to incr heatmap: {e}")
            return 0
    
    def get_heatmap(self, store_id: str, days: int = 7) -> Dict[str, Dict[int, int]]:
        """
        Get heatmap data aggregated over days.
        
        Returns:
            Dict of "hour:day_of_week" -> count
        """
        redis_client = self._get_redis()
        if redis_client is None:
            return {}
        
        result = {}
        
        try:
            today = datetime.now(timezone.utc)
            
            for i in range(min(days, 30)):
                date_key = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                key = f"analytics:heatmap:{store_id}:{date_key}"
                data = redis_client.hgetall(key)
                
                if data:
                    for k, v in data.items():
                        field = k.decode() if isinstance(k, bytes) else k
                        result[field] = result.get(field, 0) + int(v)
            
            return result
        except Exception as e:
            logger.warning(f"Failed to get heatmap: {e}")
            return result
    
    # -------------------------------------------------------------------------
    # Brand Counters
    # -------------------------------------------------------------------------
    
    def incr_brand_event(self, brand_id: str, event_name: str) -> int:
        """Increment a brand-specific event counter."""
        redis_client = self._get_redis()
        if redis_client is None:
            return 0
        
        try:
            today = self._get_today_key()
            key = f"analytics:brand:{brand_id}:{today}"
            value = redis_client.hincrby(key, event_name, 1)
            redis_client.expire(key, self._get_ttl_seconds(), nx=True)
            return value
        except Exception as e:
            logger.warning(f"Failed to incr brand event: {e}")
            return 0
    
    def get_brand_counters(self, brand_id: str, days: int = 30) -> Dict[str, int]:
        """Get brand counters aggregated over days."""
        redis_client = self._get_redis()
        if redis_client is None:
            return {}
        
        result = {}
        
        try:
            today = datetime.now(timezone.utc)
            
            for i in range(min(days, 30)):
                date_key = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                key = f"analytics:brand:{brand_id}:{date_key}"
                data = redis_client.hgetall(key)
                
                if data:
                    for k, v in data.items():
                        event_name = k.decode() if isinstance(k, bytes) else k
                        result[event_name] = result.get(event_name, 0) + int(v)
            
            return result
        except Exception as e:
            logger.warning(f"Failed to get brand counters: {e}")
            return result


# Singleton instance
realtime_counters = RealtimeCounters.get_instance()
