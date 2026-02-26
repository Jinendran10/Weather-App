"""
Google Maps integration service.
Provides map embed URLs, static map images, and place details.
"""

import httpx
from typing import Optional, Dict, Any
from app.config import settings


class MapsService:

    PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
    STATIC_MAP_URL = "https://maps.googleapis.com/maps/api/staticmap"
    GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    def build_embed_url(
        self,
        lat: float,
        lon: float,
        zoom: int = 12,
        place_id: Optional[str] = None,
    ) -> str:
        """
        Build a Google Maps Embed API URL.
        Uses place mode if place_id available, otherwise view mode.
        """
        key = settings.GOOGLE_MAPS_API_KEY
        if not key:
            # Return OpenStreetMap embed as fallback
            return (
                f"https://www.openstreetmap.org/export/embed.html"
                f"?bbox={lon-0.1},{lat-0.1},{lon+0.1},{lat+0.1}"
                f"&layer=mapnik&marker={lat},{lon}"
            )
        if place_id:
            return (
                f"https://www.google.com/maps/embed/v1/place"
                f"?key={key}&q=place_id:{place_id}&zoom={zoom}"
            )
        return (
            f"https://www.google.com/maps/embed/v1/view"
            f"?key={key}&center={lat},{lon}&zoom={zoom}"
        )

    def build_static_map_url(
        self,
        lat: float,
        lon: float,
        zoom: int = 12,
        width: int = 600,
        height: int = 400,
    ) -> str:
        """Build a Google Static Maps API URL."""
        key = settings.GOOGLE_MAPS_API_KEY
        if not key:
            return (
                f"https://www.openstreetmap.org/export/embed.html"
                f"?bbox={lon-0.1},{lat-0.1},{lon+0.1},{lat+0.1}&layer=mapnik"
            )
        return (
            f"{self.STATIC_MAP_URL}"
            f"?center={lat},{lon}&zoom={zoom}&size={width}x{height}"
            f"&markers=color:red%7C{lat},{lon}"
            f"&maptype=roadmap&key={key}"
        )

    async def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Fetch rich place details from Google Places API."""
        if not settings.GOOGLE_MAPS_API_KEY or not place_id:
            return None
        params = {
            "place_id": place_id,
            "fields": "name,rating,formatted_phone_number,website,opening_hours,photos",
            "key": settings.GOOGLE_MAPS_API_KEY,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self.PLACE_DETAILS_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return data.get("result")
        except Exception:
            return None


maps_service = MapsService()
