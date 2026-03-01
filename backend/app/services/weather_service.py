"""
OpenWeatherMap integration service.
Fetches current weather and historical/forecast weather for date ranges.
Includes rate-limit (429) protection and graceful error handling.
"""

import httpx
import json
import logging
from datetime import date, datetime, timezone
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class WeatherAPIError(Exception):
    pass


class RateLimitError(WeatherAPIError):
    """Raised when the API returns 429 Too Many Requests."""
    pass


class OpenWeatherService:

    BASE_URL = "https://api.openweathermap.org"
    ONECALL_URL = f"{BASE_URL}/data/3.0/onecall"
    HISTORY_URL = f"{BASE_URL}/data/3.0/onecall/timemachine"
    CURRENT_URL = f"{BASE_URL}/data/2.5/weather"
    # Free-tier 5-day / 3-hour forecast (fallback when 3.0 returns 401)
    FORECAST_FREE_URL = f"{BASE_URL}/data/2.5/forecast"

    # ── Key helpers ────────────────────────────────────────────────────────────

    def _masked_key(self) -> str:
        """Return first 4 chars + asterisks – safe to write to logs."""
        key = settings.OPENWEATHER_API_KEY
        if not key:
            return "(not set)"
        return key[:4] + "*" * max(0, len(key) - 4)

    async def validate_api_key(self) -> dict:
        """
        Smoke-test the API key with a cheap current-weather call.
        Returns a status dict with 'valid' (bool) and 'reason' (str).
        Called once at application startup so operators see key issues
        immediately in the logs rather than on the first user request.
        """
        if not settings.OPENWEATHER_API_KEY:
            return {
                "valid": False,
                "masked_key": "(not set)",
                "reason": "OPENWEATHER_API_KEY is missing from the environment.",
            }
        params = {"q": "London", "appid": settings.OPENWEATHER_API_KEY, "units": "metric"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self.CURRENT_URL, params=params)
            if resp.status_code == 200:
                return {"valid": True, "masked_key": self._masked_key(),
                        "reason": "Key accepted by OpenWeatherMap."}
            if resp.status_code == 401:
                return {
                    "valid": False,
                    "masked_key": self._masked_key(),
                    "reason": (
                        "Key rejected (HTTP 401). Possible causes: "
                        "(1) key not yet activated – new keys can take ~2 hours; "
                        "(2) key copied incorrectly; "
                        "(3) account suspended."
                    ),
                }
            if resp.status_code == 429:
                return {"valid": True, "masked_key": self._masked_key(),
                        "reason": "Rate-limited (HTTP 429) – key works but quota is exhausted."}
            return {"valid": False, "masked_key": self._masked_key(),
                    "reason": f"Unexpected HTTP {resp.status_code} from OpenWeatherMap."}
        except httpx.TimeoutException:
            return {"valid": False, "masked_key": self._masked_key(),
                    "reason": "Connection to OpenWeatherMap timed out during key validation."}
        except Exception as exc:  # noqa: BLE001
            return {"valid": False, "masked_key": self._masked_key(),
                    "reason": f"Connection error during key validation: {exc}"}

    def _check_rate_limit(self, resp: httpx.Response) -> None:
        """Check for 429 rate limit and raise a clear error."""
        if resp.status_code == 429:
            logger.error(
                "OpenWeatherMap rate limit exceeded (429). "
                "Daily free-tier limit is 1,000 calls/day. "
                "Response: %s", resp.text
            )
            raise RateLimitError(
                "Weather API rate limit exceeded. "
                "Please wait a few minutes and try again. "
                "The free tier allows 1,000 calls/day (~41/hour)."
            )

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
            self._check_rate_limit(resp)
            if resp.status_code == 404:
                raise WeatherAPIError("Location not found by weather provider.")
            if resp.status_code == 401:
                raise WeatherAPIError(
                    f"OpenWeatherMap rejected the API key ({self._masked_key()}). "
                    "New keys take ~2 hours to activate. "
                    "Verify the key at openweathermap.org/api_keys."
                )
            resp.raise_for_status()
            data = resp.json()
            logger.debug(
                "[WeatherAPI] /data/2.5/weather (%.4f, %.4f) HTTP %d | "
                "temp=%.1f°C humidity=%d%% desc=%s",
                lat, lon, resp.status_code,
                data.get("main", {}).get("temp", float("nan")),
                data.get("main", {}).get("humidity", 0),
                data.get("weather", [{}])[0].get("description", "n/a"),
            )
            logger.debug("[WeatherAPI] Full current weather JSON: %s", resp.text)
            return data

    async def get_forecast(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Fetch forecast data.

        Tries One Call 3.0 first (paid subscription required).
        On 401 (free-tier key), automatically falls back to the
        free-tier ``data/2.5/forecast`` endpoint and returns data
        normalised to the same One Call ``{"daily": [...]}`` shape.
        """
        params = {
            "lat": lat,
            "lon": lon,
            "appid": settings.OPENWEATHER_API_KEY,
            "units": "metric",
            "exclude": "minutely,hourly,alerts",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.ONECALL_URL, params=params)
            self._check_rate_limit(resp)
            if resp.status_code == 401:
                logger.warning(
                    "One Call 3.0 returned 401 for key %s – this endpoint "
                    "requires a paid subscription. Falling back to free-tier "
                    "data/2.5/forecast.",
                    self._masked_key(),
                )
                return await self._get_forecast_free_tier(lat, lon)
            resp.raise_for_status()
            return resp.json()

    async def _get_forecast_free_tier(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Fetch 5-day / 3-hour forecast from the free-tier endpoint and
        aggregate it into daily blocks that match the One Call 3.0
        ``daily`` list format expected by ``parse_daily_record``.
        """
        from collections import defaultdict
        params = {
            "lat": lat,
            "lon": lon,
            "appid": settings.OPENWEATHER_API_KEY,
            "units": "metric",
            "cnt": 40,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.FORECAST_FREE_URL, params=params)
            self._check_rate_limit(resp)
            if resp.status_code == 401:
                raise WeatherAPIError(
                    f"OpenWeatherMap rejected the API key ({self._masked_key()}). "
                    "New keys take ~2 hours to activate. "
                    "Verify the key at openweathermap.org/api_keys."
                )
            resp.raise_for_status()
            data = resp.json()
            logger.debug(
                "[WeatherAPI] /data/2.5/forecast (%.4f, %.4f) HTTP %d | entries=%d",
                lat, lon, resp.status_code, len(data.get("list", [])),
            )
            logger.debug("[WeatherAPI] Full forecast JSON: %s", resp.text)

        # Group 3-hourly entries by calendar date
        days: dict = defaultdict(list)
        for entry in data.get("list", []):
            d = date.fromtimestamp(entry["dt"])
            days[d].append(entry)

        daily_blocks = []
        for d, entries in sorted(days.items()):
            temps = [e["main"]["temp"] for e in entries]
            humidity_vals = [e["main"]["humidity"] for e in entries]
            pressure_vals = [e["main"]["pressure"] for e in entries]
            wind_speeds = [e.get("wind", {}).get("speed", 0) for e in entries]
            # Pick the entry closest to midday for description / icon
            midday = min(
                entries,
                key=lambda e: abs(datetime.fromtimestamp(e["dt"]).hour - 12),
            )
            weather = midday.get("weather", [{}])[0]
            daily_blocks.append({
                "dt": midday["dt"],
                "temp": {
                    "min": min(temps),
                    "max": max(temps),
                    "day": round(sum(temps) / len(temps), 2),
                },
                "feels_like": {
                    "day": midday["main"].get("feels_like", midday["main"]["temp"]),
                },
                "pressure": round(sum(pressure_vals) / len(pressure_vals), 1),
                "humidity": round(sum(humidity_vals) / len(humidity_vals)),
                "wind_speed": round(sum(wind_speeds) / len(wind_speeds), 2),
                "wind_deg": midday.get("wind", {}).get("deg", 0),
                "clouds": midday.get("clouds", {}).get("all", 0),
                "uvi": 0,   # not available in 2.5/forecast
                "weather": [weather],
                "rain": midday.get("rain", {}).get("3h", 0),
                "pop": midday.get("pop", 0),
            })

        logger.info(
            "Free-tier forecast returned %d daily blocks for (%.4f, %.4f)",
            len(daily_blocks), lat, lon,
        )
        return {"daily": daily_blocks}

    async def get_historical(self, lat: float, lon: float, target_date: date) -> Dict[str, Any]:
        """
        Fetch historical weather for a specific date via One Call Timemachine.
        NOTE: This endpoint requires a paid One Call 3.0 subscription.
        Free-tier keys will receive HTTP 401 here.
        """
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
            self._check_rate_limit(resp)
            if resp.status_code == 401:
                raise WeatherAPIError(
                    f"Historical weather (One Call 3.0 Timemachine) requires a paid "
                    f"OpenWeatherMap subscription. Key {self._masked_key()} has free-tier access only. "
                    "Use a date within the next 5 days for free-tier forecast data instead."
                )
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
