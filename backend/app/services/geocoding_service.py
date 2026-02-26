"""
Geocoding service using OpenWeatherMap's Geocoding API and Google Maps API.
Resolves any location string into (latitude, longitude, metadata).
"""

import httpx
from typing import Optional, Tuple, Dict, Any
from app.config import settings
from app.utils.validators import is_gps_coordinates, sanitize_location_input


class GeocodingError(Exception):
    """Raised when a location cannot be resolved."""
    pass


class GeocodingService:

    OWM_GEO_URL = "https://api.openweathermap.org/geo/1.0"
    GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    async def resolve_location(self, raw_input: str) -> Dict[str, Any]:
        """
        Resolve any location string to geocoded data.
        Priority:
         1. GPS coordinates (parse directly)
         2. OpenWeatherMap Geocoding API
         3. Google Maps Geocoding API (fallback)

        Returns a dict compatible with Location model creation.
        Raises GeocodingError if resolution fails.
        """
        raw_input = sanitize_location_input(raw_input)
        if not raw_input:
            raise GeocodingError("Location input cannot be empty.")

        # 1. Try direct GPS parsing
        coords = is_gps_coordinates(raw_input)
        if coords:
            lat, lon = coords
            return await self._reverse_geocode(lat, lon, raw_input)

        # 2. Try OpenWeatherMap Geocoding
        try:
            result = await self._owm_geocode(raw_input)
            if result:
                return result
        except Exception:
            pass

        # 3. Fallback to Google Maps
        if settings.GOOGLE_MAPS_API_KEY:
            try:
                result = await self._google_geocode(raw_input)
                if result:
                    return result
            except Exception:
                pass

        raise GeocodingError(
            f"Could not resolve location: '{raw_input}'. "
            "Please try a more specific location name, ZIP code, or GPS coordinates."
        )

    async def _owm_geocode(self, query: str) -> Optional[Dict[str, Any]]:
        """Forward geocoding via OpenWeatherMap."""
        params = {
            "q": query,
            "limit": 1,
            "appid": settings.OPENWEATHER_API_KEY,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.OWM_GEO_URL}/direct", params=params)
            resp.raise_for_status()
            data = resp.json()

        if not data:
            return None

        loc = data[0]
        return {
            "raw_input": query,
            "resolved_name": f"{loc.get('name', '')}, {loc.get('state', loc.get('country', ''))}".strip(", "),
            "country": loc.get("country"),
            "state": loc.get("state"),
            "city": loc.get("name"),
            "latitude": loc["lat"],
            "longitude": loc["lon"],
            "place_id": None,
        }

    async def _reverse_geocode(self, lat: float, lon: float, raw_input: str) -> Dict[str, Any]:
        """Reverse geocode GPS coordinates via OpenWeatherMap."""
        params = {
            "lat": lat,
            "lon": lon,
            "limit": 1,
            "appid": settings.OPENWEATHER_API_KEY,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.OWM_GEO_URL}/reverse", params=params)
            resp.raise_for_status()
            data = resp.json()

        if data:
            loc = data[0]
            name = f"{loc.get('name', '')}, {loc.get('country', '')}".strip(", ")
        else:
            name = f"{lat}, {lon}"

        return {
            "raw_input": raw_input,
            "resolved_name": name,
            "country": data[0].get("country") if data else None,
            "state": data[0].get("state") if data else None,
            "city": data[0].get("name") if data else None,
            "latitude": lat,
            "longitude": lon,
            "place_id": None,
        }

    async def _google_geocode(self, query: str) -> Optional[Dict[str, Any]]:
        """Geocode via Google Maps Geocoding API."""
        params = {
            "address": query,
            "key": settings.GOOGLE_MAPS_API_KEY,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self.GOOGLE_GEOCODE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "OK" or not data.get("results"):
            return None

        result = data["results"][0]
        geo = result["geometry"]["location"]
        components = {c["types"][0]: c["long_name"] for c in result.get("address_components", [])}

        return {
            "raw_input": query,
            "resolved_name": result.get("formatted_address", query),
            "country": components.get("country"),
            "state": components.get("administrative_area_level_1"),
            "city": components.get("locality") or components.get("administrative_area_level_2"),
            "latitude": geo["lat"],
            "longitude": geo["lng"],
            "place_id": result.get("place_id"),
        }


geocoding_service = GeocodingService()
