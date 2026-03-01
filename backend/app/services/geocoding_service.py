"""
Geocoding service using Nominatim (OpenStreetMap).
Resolves any location string (city, ZIP, landmark, GPS coords) into
latitude, longitude, and metadata.

Nominatim is free and requires no API key – only a descriptive User-Agent
header is mandatory per the usage policy.
"""

import httpx
import logging
from typing import Optional, Dict, Any
from app.utils.validators import is_gps_coordinates, sanitize_location_input

logger = logging.getLogger(__name__)


class GeocodingError(Exception):
    """Raised when a location cannot be resolved."""
    pass


class GeocodingService:
    """Async geocoding via Nominatim (OpenStreetMap)."""

    NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
    NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

    # Nominatim requires a descriptive User-Agent (usage policy).
    HEADERS = {
        "User-Agent": "WeatherVault/1.0 (portfolio project; contact@weathervault.dev)",
        "Accept-Language": "en",
    }

    async def resolve_location(self, raw_input: str) -> Dict[str, Any]:
        """
        Resolve any user-provided location string to geocoded data.

        Strategy:
          1. If the input looks like GPS coordinates → reverse-geocode via Nominatim
          2. Otherwise → forward-search via Nominatim

        Returns a dict compatible with the Location ORM model.
        Raises GeocodingError if resolution fails.
        """
        raw_input = sanitize_location_input(raw_input)
        if not raw_input:
            raise GeocodingError("Location input cannot be empty.")

        # 1. Direct GPS coordinate detection
        coords = is_gps_coordinates(raw_input)
        if coords:
            lat, lon = coords
            return await self._reverse_geocode(lat, lon, raw_input)

        # 2. Forward geocoding via Nominatim
        result = await self._nominatim_search(raw_input)
        if result:
            return result

        raise GeocodingError(
            f"Could not resolve location: '{raw_input}'. "
            "Please try a more specific location name, ZIP code, or GPS coordinates."
        )

    # ── Forward geocoding ─────────────────────────────────────────────────

    async def _nominatim_search(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Forward-geocode a location string via Nominatim /search.
        Returns the top result formatted for our Location model, or None.
        """
        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 1,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                self.NOMINATIM_SEARCH_URL,
                params=params,
                headers=self.HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()

        if not data:
            logger.warning("Nominatim returned no results for query: %s", query)
            return None

        place = data[0]
        return self._parse_nominatim_result(place, query)

    # ── Reverse geocoding ─────────────────────────────────────────────────

    async def _reverse_geocode(
        self, lat: float, lon: float, raw_input: str
    ) -> Dict[str, Any]:
        """Reverse-geocode GPS coordinates via Nominatim /reverse."""
        params = {
            "lat": lat,
            "lon": lon,
            "format": "jsonv2",
            "addressdetails": 1,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                self.NOMINATIM_REVERSE_URL,
                params=params,
                headers=self.HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()

        if data and data.get("lat"):
            return self._parse_nominatim_result(data, raw_input)

        # Fall back to raw coordinates if reverse geocode found nothing
        return {
            "raw_input": raw_input,
            "resolved_name": f"{lat}, {lon}",
            "country": None,
            "state": None,
            "city": None,
            "latitude": lat,
            "longitude": lon,
            "place_id": None,
        }

    # ── Parsing helper ────────────────────────────────────────────────────

    @staticmethod
    def _parse_nominatim_result(place: Dict, raw_input: str) -> Dict[str, Any]:
        """
        Convert a Nominatim JSON result into a dict compatible with the
        Location ORM model.
        """
        address = place.get("address", {})

        # Build a human-readable resolved name from address components
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("hamlet")
            or address.get("municipality")
        )
        state = address.get("state")
        country = address.get("country")

        name_parts = [p for p in (city, state, country) if p]
        resolved_name = ", ".join(name_parts) if name_parts else place.get("display_name", raw_input)

        return {
            "raw_input": raw_input,
            "resolved_name": resolved_name,
            "country": country,
            "state": state,
            "city": city,
            "latitude": float(place["lat"]),
            "longitude": float(place["lon"]),
            "place_id": str(place.get("place_id")) if place.get("place_id") else None,
        }


# Module-level singleton
geocoding_service = GeocodingService()

