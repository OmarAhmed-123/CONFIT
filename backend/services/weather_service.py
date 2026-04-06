"""
CONFIT Backend — Weather Service
================================
Weather API integration for outfit planning.
Supports OpenWeatherMap, WeatherAPI, and fallback mock data.
"""

import os
import logging
import hashlib
from datetime import datetime, timezone, timedelta, date
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import json
import asyncio

import httpx
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.closet_planner_models import (
    WeatherCache,
    WeatherDataDTO,
    WeatherForecastDTO,
    WeatherCondition,
)
from database.models import UUIDType

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# WEATHER MAPPINGS
# ─────────────────────────────────────────────────────────────────────────────

# OpenWeatherMap condition codes to our internal conditions
OWM_CONDITION_MAP = {
    "01d": WeatherCondition.SUNNY,
    "01n": WeatherCondition.CLEAR,
    "02d": WeatherCondition.PARTLY_CLOUDY,
    "02n": WeatherCondition.PARTLY_CLOUDY,
    "03d": WeatherCondition.CLOUDY,
    "03n": WeatherCondition.CLOUDY,
    "04d": WeatherCondition.OVERCAST,
    "04n": WeatherCondition.OVERCAST,
    "09d": WeatherCondition.LIGHT_RAIN,
    "09n": WeatherCondition.LIGHT_RAIN,
    "10d": WeatherCondition.RAIN,
    "10n": WeatherCondition.RAIN,
    "11d": WeatherCondition.THUNDERSTORM,
    "11n": WeatherCondition.THUNDERSTORM,
    "13d": WeatherCondition.SNOW,
    "13n": WeatherCondition.SNOW,
    "50d": WeatherCondition.FOG,
    "50n": WeatherCondition.FOG,
}

# Weather icons mapping
WEATHER_ICONS = {
    WeatherCondition.SUNNY: "☀️",
    WeatherCondition.CLEAR: "🌙",
    WeatherCondition.PARTLY_CLOUDY: "⛅",
    WeatherCondition.CLOUDY: "☁️",
    WeatherCondition.OVERCAST: "☁️",
    WeatherCondition.LIGHT_RAIN: "🌧️",
    WeatherCondition.RAIN: "🌧️",
    WeatherCondition.HEAVY_RAIN: "⛈️",
    WeatherCondition.THUNDERSTORM: "⛈️",
    WeatherCondition.LIGHT_SNOW: "🌨️",
    WeatherCondition.SNOW: "❄️",
    WeatherCondition.HEAVY_SNOW: "❄️",
    WeatherCondition.FOG: "🌫️",
    WeatherCondition.WINDY: "💨",
}

# Weather condition to outfit recommendations
WEATHER_OUTFIT_RULES = {
    WeatherCondition.SUNNY: {
        "avoid": ["heavy_jacket", "boots", "sweaters"],
        "prefer": ["light_fabric", "sunglasses", "hats"],
        "layer_suggestion": "light",
    },
    WeatherCondition.RAIN: {
        "avoid": ["suede", "light_colors", "canvas_shoes"],
        "prefer": ["waterproof", "dark_colors", "boots", "jacket"],
        "layer_suggestion": "medium",
    },
    WeatherCondition.SNOW: {
        "avoid": ["light_fabric", "sneakers", "light_colors"],
        "prefer": ["warm_layers", "boots", "coat", "gloves"],
        "layer_suggestion": "heavy",
    },
    WeatherCondition.CLOUDY: {
        "avoid": [],
        "prefer": ["layers", "light_jacket"],
        "layer_suggestion": "medium",
    },
    WeatherCondition.THUNDERSTORM: {
        "avoid": ["light_colors", "canvas", "delicate_fabric"],
        "prefer": ["waterproof", "hooded_jacket", "boots"],
        "layer_suggestion": "medium",
    },
    WeatherCondition.WINDY: {
        "avoid": ["loose_items", "hats_without_strap"],
        "prefer": ["fitted", "jacket", "closed_shoes"],
        "layer_suggestion": "medium",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# WEATHER SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class WeatherService:
    """
    Weather service for outfit planning.
    Supports multiple weather APIs with caching.
    """
    
    CACHE_DURATION_HOURS = 6  # Cache weather for 6 hours
    FORECAST_DAYS = 7  # Get 7-day forecast
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        self._weatherapi_key = os.getenv("WEATHERAPI_KEY")
        self._client = httpx.AsyncClient(timeout=10.0)
    
    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()
    
    def _get_location_key(self, location: Dict[str, Any]) -> str:
        """Generate a unique key for location caching."""
        if "lat" in location and "lng" in location:
            return f"{location['lat']:.2f},{location['lng']:.2f}"
        elif "city" in location:
            return location["city"].lower().replace(" ", "_")
        return "default"
    
    async def get_weather_for_date(
        self,
        target_date: date,
        location: Dict[str, Any],
        use_cache: bool = True,
    ) -> Optional[WeatherDataDTO]:
        """
        Get weather forecast for a specific date.
        
        Args:
            target_date: The date to get weather for
            location: Location dict with city or lat/lng
            use_cache: Whether to use cached data
            
        Returns:
            WeatherDataDTO or None if not available
        """
        location_key = self._get_location_key(location)
        
        # Check cache first
        if use_cache:
            cached = await self._get_cached_weather(location_key, target_date)
            if cached:
                logger.debug(f"Using cached weather for {location_key} on {target_date}")
                return cached
        
        # Fetch fresh data
        forecasts = await self._fetch_forecast(location)
        
        if forecasts:
            # Cache all forecasts
            await self._cache_forecasts(location_key, forecasts)
            
            # Return the requested date
            for forecast in forecasts:
                if forecast.get("date") == target_date:
                    return forecast.get("weather")
        
        # Fallback to mock weather
        return self._generate_mock_weather(target_date)
    
    async def get_week_forecast(
        self,
        start_date: date,
        location: Dict[str, Any],
        use_cache: bool = True,
    ) -> List[WeatherDataDTO]:
        """
        Get weather forecast for a week.
        
        Args:
            start_date: Start date of the week
            location: Location dict
            use_cache: Whether to use cached data
            
        Returns:
            List of WeatherDataDTO for each day of the week
        """
        location_key = self._get_location_key(location)
        forecasts = []
        
        end_date = start_date + timedelta(days=6)
        
        # Check if we have all cached
        if use_cache:
            all_cached = True
            for i in range(7):
                target_date = start_date + timedelta(days=i)
                cached = await self._get_cached_weather(location_key, target_date)
                if cached:
                    forecasts.append(cached)
                else:
                    all_cached = False
                    break
            
            if all_cached:
                return forecasts
        
        # Fetch fresh forecast
        api_forecasts = await self._fetch_forecast(location)
        
        if api_forecasts:
            await self._cache_forecasts(location_key, api_forecasts)
            
            # Extract the week we need
            for i in range(7):
                target_date = start_date + timedelta(days=i)
                found = False
                for f in api_forecasts:
                    if f.get("date") == target_date:
                        forecasts.append(f.get("weather"))
                        found = True
                        break
                
                if not found:
                    forecasts.append(self._generate_mock_weather(target_date))
        else:
            # Use mock weather for all days
            for i in range(7):
                target_date = start_date + timedelta(days=i)
                forecasts.append(self._generate_mock_weather(target_date))
        
        return forecasts
    
    async def _get_cached_weather(
        self,
        location_key: str,
        target_date: date,
    ) -> Optional[WeatherDataDTO]:
        """Get weather from cache if still valid."""
        query = select(WeatherCache).where(
            WeatherCache.location_key == location_key,
            WeatherCache.forecast_date == target_date,
            WeatherCache.expires_at > datetime.now(timezone.utc),
        )
        
        result = await self.session.execute(query)
        cached = result.scalar_one_or_none()
        
        if cached:
            return WeatherDataDTO(**cached.weather_data)
        
        return None
    
    async def _cache_forecasts(
        self,
        location_key: str,
        forecasts: List[Dict[str, Any]],
    ) -> None:
        """Cache forecast data."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.CACHE_DURATION_HOURS)
        
        for forecast in forecasts:
            forecast_date = forecast.get("date")
            weather_data = forecast.get("weather")
            
            if not forecast_date or not weather_data:
                continue
            
            # Delete old cache entry
            delete_stmt = delete(WeatherCache).where(
                WeatherCache.location_key == location_key,
                WeatherCache.forecast_date == forecast_date,
            )
            await self.session.execute(delete_stmt)
            
            # Create new cache entry
            cache_entry = WeatherCache(
                location_key=location_key,
                forecast_date=forecast_date,
                weather_data=weather_data.model_dump() if isinstance(weather_data, WeatherDataDTO) else weather_data,
                source="openweathermap",
                fetched_at=datetime.now(timezone.utc),
                expires_at=expires_at,
            )
            self.session.add(cache_entry)
        
        await self.session.commit()
    
    async def _fetch_forecast(
        self,
        location: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Fetch forecast from weather API."""
        # Try OpenWeatherMap first
        if self._api_key:
            try:
                return await self._fetch_openweathermap(location)
            except Exception as e:
                logger.warning(f"OpenWeatherMap API failed: {e}")
        
        # Try WeatherAPI as fallback
        if self._weatherapi_key:
            try:
                return await self._fetch_weatherapi(location)
            except Exception as e:
                logger.warning(f"WeatherAPI failed: {e}")
        
        logger.warning("No weather API available, using mock data")
        return []
    
    async def _fetch_openweathermap(
        self,
        location: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Fetch forecast from OpenWeatherMap."""
        # Build query params
        if "lat" in location and "lng" in location:
            params = {
                "lat": location["lat"],
                "lon": location["lng"],
            }
        elif "city" in location:
            params = {"q": location["city"]}
        else:
            params = {"q": "New York"}  # Default
        
        params.update({
            "appid": self._api_key,
            "units": "metric",
            "cnt": 40,  # 5 days / 3 hours = 40 data points
        })
        
        url = "https://api.openweathermap.org/data/2.5/forecast"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse into daily forecasts
        daily_data = self._parse_openweathermap_daily(data)
        
        return daily_data
    
    def _parse_openweathermap_daily(
        self,
        data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Parse OpenWeatherMap response into daily forecasts."""
        forecasts = []
        daily_groups = {}
        
        # Group by date
        for item in data.get("list", []):
            dt = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
            date_str = dt.date()
            
            if date_str not in daily_groups:
                daily_groups[date_str] = []
            daily_groups[date_str].append(item)
        
        # Process each day
        for forecast_date, items in daily_groups.items():
            if not items:
                continue
            
            # Calculate daily aggregates
            temps = [i["main"]["temp"] for i in items]
            temp_min = min(temps)
            temp_max = max(temps)
            
            # Get most common weather condition
            weather_codes = [i["weather"][0]["icon"] for i in items if i.get("weather")]
            most_common_code = max(set(weather_codes), key=weather_codes.count) if weather_codes else "01d"
            
            # Get precipitation
            rain = sum(i.get("rain", {}).get("3h", 0) for i in items)
            snow = sum(i.get("snow", {}).get("3h", 0) for i in items)
            
            # Get humidity and wind
            humidity = sum(i["main"]["humidity"] for i in items) / len(items)
            wind_speed = sum(i["wind"]["speed"] for i in items) / len(items)
            
            condition = OWM_CONDITION_MAP.get(most_common_code, WeatherCondition.CLOUDY)
            
            weather = WeatherDataDTO(
                temp_high=round(temp_max, 1),
                temp_low=round(temp_min, 1),
                condition=condition.value,
                precipitation=round(rain + snow, 1),
                humidity=round(humidity, 1),
                wind_speed=round(wind_speed, 1),
                icon=WEATHER_ICONS.get(condition, "🌡️"),
            )
            
            forecasts.append({
                "date": forecast_date,
                "weather": weather,
            })
        
        return forecasts
    
    async def _fetch_weatherapi(
        self,
        location: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Fetch forecast from WeatherAPI.com."""
        if "lat" in location and "lng" in location:
            q = f"{location['lat']},{location['lng']}"
        elif "city" in location:
            q = location["city"]
        else:
            q = "New York"
        
        params = {
            "key": self._weatherapi_key,
            "q": q,
            "days": 7,
            "aqi": "no",
            "alerts": "no",
        }
        
        url = "https://api.weatherapi.com/v1/forecast.json"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        return self._parse_weatherapi_daily(data)
    
    def _parse_weatherapi_daily(
        self,
        data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Parse WeatherAPI response into daily forecasts."""
        forecasts = []
        
        for day in data.get("forecast", {}).get("forecastday", []):
            forecast_date = datetime.strptime(day["date"], "%Y-%m-%d").date()
            day_data = day["day"]
            
            # Map condition
            condition_text = day_data["condition"]["text"].lower()
            condition = self._map_weatherapi_condition(condition_text)
            
            weather = WeatherDataDTO(
                temp_high=round(day_data["maxtemp_c"], 1),
                temp_low=round(day_data["mintemp_c"], 1),
                condition=condition.value,
                precipitation=round(day_data.get("totalprecip_mm", 0), 1),
                humidity=round(day_data.get("avghumidity", 0), 1),
                wind_speed=round(day_data.get("maxwind_kph", 0) / 3.6, 1),  # Convert to m/s
                uv_index=day_data.get("uv"),
                icon=WEATHER_ICONS.get(condition, "🌡️"),
            )
            
            forecasts.append({
                "date": forecast_date,
                "weather": weather,
            })
        
        return forecasts
    
    def _map_weatherapi_condition(self, text: str) -> WeatherCondition:
        """Map WeatherAPI condition text to our enum."""
        text = text.lower()
        
        if "sunny" in text or "clear" in text:
            return WeatherCondition.SUNNY
        elif "partly cloudy" in text:
            return WeatherCondition.PARTLY_CLOUDY
        elif "cloudy" in text or "overcast" in text:
            return WeatherCondition.CLOUDY
        elif "rain" in text:
            if "light" in text:
                return WeatherCondition.LIGHT_RAIN
            elif "heavy" in text:
                return WeatherCondition.HEAVY_RAIN
            return WeatherCondition.RAIN
        elif "snow" in text:
            if "light" in text:
                return WeatherCondition.LIGHT_SNOW
            elif "heavy" in text:
                return WeatherCondition.HEAVY_SNOW
            return WeatherCondition.SNOW
        elif "thunder" in text:
            return WeatherCondition.THUNDERSTORM
        elif "fog" in text or "mist" in text:
            return WeatherCondition.FOG
        elif "wind" in text:
            return WeatherCondition.WINDY
        
        return WeatherCondition.CLOUDY
    
    def _generate_mock_weather(self, target_date: date) -> WeatherDataDTO:
        """Generate deterministic mock weather for testing."""
        # Use date to create deterministic but varied weather
        date_hash = int(hashlib.md5(str(target_date).encode()).hexdigest()[:8], 16)
        
        # Generate temperature based on season (Northern Hemisphere)
        month = target_date.month
        if month in [12, 1, 2]:  # Winter
            base_temp = 5
            temp_range = 10
        elif month in [3, 4, 5]:  # Spring
            base_temp = 15
            temp_range = 10
        elif month in [6, 7, 8]:  # Summer
            base_temp = 28
            temp_range = 8
        else:  # Fall
            base_temp = 15
            temp_range = 12
        
        # Add some variation
        temp_high = base_temp + (date_hash % temp_range) - temp_range / 2
        temp_low = temp_high - 5 - (date_hash % 5)
        
        # Select condition based on hash
        conditions = list(WeatherCondition)
        condition_idx = date_hash % len(conditions)
        condition = conditions[condition_idx]
        
        return WeatherDataDTO(
            temp_high=round(temp_high, 1),
            temp_low=round(temp_low, 1),
            condition=condition.value,
            precipitation=round((date_hash % 30) / 10, 1) if "rain" in condition.value else 0,
            humidity=round(40 + (date_hash % 40), 1),
            wind_speed=round((date_hash % 20) / 2, 1),
            icon=WEATHER_ICONS.get(condition, "🌡️"),
        )
    
    def get_weather_outfit_rules(
        self,
        weather: WeatherDataDTO,
    ) -> Dict[str, Any]:
        """
        Get outfit recommendations based on weather.
        
        Args:
            weather: Weather data
            
        Returns:
            Dict with avoid, prefer, and layer_suggestion
        """
        try:
            condition = WeatherCondition(weather.condition)
            rules = WEATHER_OUTFIT_RULES.get(condition, {})
        except ValueError:
            rules = {}
        
        # Add temperature-based rules
        temp = weather.temp_high
        
        if temp < 10:
            rules.setdefault("prefer", []).extend(["coat", "layers", "closed_shoes"])
            rules["layer_suggestion"] = "heavy"
        elif temp < 20:
            rules.setdefault("prefer", []).extend(["light_jacket", "layers"])
            rules["layer_suggestion"] = "medium"
        else:
            rules.setdefault("prefer", []).extend(["light_fabric", "breathable"])
            rules["layer_suggestion"] = "light"
        
        # Add rain-specific rules
        if weather.precipitation > 0:
            rules.setdefault("avoid", []).extend(["suede", "canvas_shoes"])
            rules.setdefault("prefer", []).extend(["waterproof_outer"])
        
        # Add wind-specific rules
        if weather.wind_speed > 10:
            rules.setdefault("avoid", []).extend(["loose_skirts", "loose_hats"])
            rules.setdefault("prefer", []).extend(["fitted"])
        
        return rules
    
    def calculate_weather_match_score(
        self,
        outfit_data: Dict[str, Any],
        weather: WeatherDataDTO,
    ) -> float:
        """
        Calculate how well an outfit matches the weather.
        
        Args:
            outfit_data: Outfit data with items
            weather: Weather data
            
        Returns:
            Score between 0 and 1
        """
        rules = self.get_weather_outfit_rules(weather)
        score = 0.5  # Start neutral
        
        items = outfit_data.get("items", [])
        if not items:
            return 0.5
        
        avoid_list = rules.get("avoid", [])
        prefer_list = rules.get("prefer", [])
        
        for item in items:
            category = item.get("category", "").lower()
            tags = [t.lower() for t in item.get("tags", [])]
            all_attributes = [category] + tags
            
            # Check for avoided items
            for avoid in avoid_list:
                if avoid.lower() in all_attributes:
                    score -= 0.15
            
            # Check for preferred items
            for prefer in prefer_list:
                if prefer.lower() in all_attributes:
                    score += 0.1
        
        # Clamp score
        return max(0.0, min(1.0, score))
