"""
OpenWeatherMap integration service.
Fetches current weather and historical/forecast weather for date ranges.
"""

import httpx
import json
from datetime import date, datetime, timezone
from typing import List, Dict, Any, Optional
from app.config import settings


class WeatherAPIError(Exception):
    pass


class OpenWeatherService:

    BASE_URL = "https://api.openweathermap.org"
    ONECALL_URL = f"{BASE_URL}/data/3.0/onecall"
    HISTORY_URL = f"{BASE_URL}/data/3.0/onecall/timemachine"
    CURRENT_URL = f"{BASE_URL}/data/2.5/weather"

    async def get_current_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch live current weather for coordinates."""
        params = {
            "lat": lat,
            "lon": lon,
            "appid": settings.OPENWEATHER_API_KEY,
            "units": "metric",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.CURRENT_URL, params=params)
            if resp.status_code == 404:
                raise WeatherAPIError("Location not found by weather provider.")
            if resp.status_code == 401:
                raise WeatherAPIError("Invalid OpenWeatherMap API key.")
            resp.raise_for_status()
            return resp.json()

    async def get_forecast(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch 8-day forecast via One Call API 3.0."""
        params = {
            "lat": lat,
            "lon": lon,
            "appid": settings.OPENWEATHER_API_KEY,
            "units": "metric",
            "exclude": "minutely,hourly,alerts",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.ONECALL_URL, params=params)
            if resp.status_code == 401:
                raise WeatherAPIError("Invalid OpenWeatherMap API key.")
            resp.raise_for_status()
            return resp.json()

    async def get_historical(self, lat: float, lon: float, target_date: date) -> Dict[str, Any]:
        """Fetch historical weather for a specific date via One Call Timemachine."""
        dt = int(datetime(target_date.year, target_date.month, target_date.day, 12, 0, tzinfo=timezone.utc).timestamp())
        params = {
            "lat": lat,
            "lon": lon,
            "dt": dt,
            "appid": settings.OPENWEATHER_API_KEY,
            "units": "metric",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.HISTORY_URL, params=params)
            if resp.status_code == 401:
                raise WeatherAPIError("Invalid OpenWeatherMap API key.")
            resp.raise_for_status()
            return resp.json()

    def parse_current_weather(self, data: Dict[str, Any], location_data: Dict) -> Dict[str, Any]:
        """Normalize current weather API response."""
        main = data.get("main", {})
        wind = data.get("wind", {})
        weather = data.get("weather", [{}])[0]
        sys = data.get("sys", {})
        return {
            "temp_celsius": main.get("temp"),
            "temp_fahrenheit": round(main.get("temp", 0) * 9 / 5 + 32, 2),
            "feels_like_celsius": main.get("feels_like"),
            "humidity": main.get("humidity"),
            "pressure": main.get("pressure"),
            "wind_speed": wind.get("speed"),
            "wind_direction": wind.get("deg", 0),
            "visibility": data.get("visibility", 0),
            "cloud_cover": data.get("clouds", {}).get("all", 0),
            "weather_main": weather.get("main"),
            "weather_description": weather.get("description"),
            "weather_icon": weather.get("icon"),
            "sunrise": datetime.fromtimestamp(sys.get("sunrise", 0), tz=timezone.utc),
            "sunset": datetime.fromtimestamp(sys.get("sunset", 0), tz=timezone.utc),
            "recorded_at": datetime.fromtimestamp(data.get("dt", 0), tz=timezone.utc),
        }

    def parse_daily_record(self, day_data: Dict[str, Any], query_id, record_date: date) -> Dict[str, Any]:
        """Parse a daily entry from One Call API response."""
        temp = day_data.get("temp", {})
        weather = day_data.get("weather", [{}])[0]
        return {
            "query_id": query_id,
            "record_date": record_date,
            "temp_min": temp.get("min") if isinstance(temp, dict) else None,
            "temp_max": temp.get("max") if isinstance(temp, dict) else None,
            "temp_avg": temp.get("day") if isinstance(temp, dict) else (day_data.get("temp") if not isinstance(temp, dict) else None),
            "feels_like": day_data.get("feels_like", {}).get("day") if isinstance(day_data.get("feels_like"), dict) else day_data.get("feels_like"),
            "humidity": day_data.get("humidity"),
            "pressure": day_data.get("pressure"),
            "wind_speed": day_data.get("wind_speed"),
            "wind_direction": day_data.get("wind_deg"),
            "visibility": day_data.get("visibility"),
            "uv_index": day_data.get("uvi"),
            "cloud_cover": day_data.get("clouds"),
            "precipitation": day_data.get("rain", 0) or day_data.get("precipitation", 0),
            "snow": day_data.get("snow", 0),
            "weather_main": weather.get("main"),
            "weather_description": weather.get("description"),
            "weather_icon": weather.get("icon"),
            "sunrise": datetime.fromtimestamp(day_data["sunrise"], tz=timezone.utc) if day_data.get("sunrise") else None,
            "sunset": datetime.fromtimestamp(day_data["sunset"], tz=timezone.utc) if day_data.get("sunset") else None,
            "raw_data": json.dumps(day_data),
        }


weather_service = OpenWeatherService()
