"""
Third-party API integrations router.
  GET /integrations/maps/{query_id}     – Google Maps data for a query's location
  GET /integrations/youtube/{query_id}  – YouTube travel videos for a query's location
  GET /integrations/maps/location       – Map data for any raw location string
  GET /integrations/youtube/location    – YouTube videos for any raw location string
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.weather import WeatherQuery, Location
from app.schemas.weather import MapDataOut, YouTubeResponse, LocationCreate
from app.services.geocoding_service import geocoding_service, GeocodingError
from app.services.maps_service import maps_service
from app.services.youtube_service import youtube_service

router = APIRouter(prefix="/integrations", tags=["3rd-Party Integrations"])


# ── Shared helpers ────────────────────────────────────────────────────────────

async def _get_location_for_query(query_id: UUID, db: AsyncSession) -> Location:
    result = await db.execute(
        select(WeatherQuery)
        .options(selectinload(WeatherQuery.location))
        .where(WeatherQuery.id == query_id)
    )
    q = result.scalars().first()
    if not q:
        raise HTTPException(status_code=404, detail="Weather query not found.")
    return q.location


async def _geocode_raw(raw_input: str) -> Location:
    try:
        geo = await geocoding_service.resolve_location(raw_input)
    except GeocodingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    # Return a temporary in-memory Location object (not saved to DB here)
    from app.models.weather import Location as Loc
    loc = Loc(**geo)
    return loc


# ── Maps endpoints ────────────────────────────────────────────────────────────

@router.get(
    "/maps/query/{query_id}",
    response_model=MapDataOut,
    summary="Get Google Maps data for a stored query's location",
)
async def maps_for_query(
    query_id: UUID,
    zoom: int = Query(12, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Returns embed URL, static map URL, and place details for the stored query's location."""
    location = await _get_location_for_query(query_id, db)
    place_details = await maps_service.get_place_details(location.place_id) if location.place_id else None
    return MapDataOut(
        location=location.resolved_name,
        latitude=location.latitude,
        longitude=location.longitude,
        place_id=location.place_id,
        formatted_address=location.resolved_name,
        maps_embed_url=maps_service.build_embed_url(location.latitude, location.longitude, zoom, location.place_id),
        static_map_url=maps_service.build_static_map_url(location.latitude, location.longitude, zoom),
        place_details=place_details,
    )


@router.get(
    "/maps/location",
    response_model=MapDataOut,
    summary="Get Google Maps data for any location string",
)
async def maps_for_location(
    location: str = Query(..., min_length=1, description="Any location string"),
    zoom: int = Query(12, ge=1, le=20),
):
    """Geocodes any location string and returns Google Maps data."""
    loc = await _geocode_raw(location)
    place_details = await maps_service.get_place_details(loc.place_id) if loc.place_id else None
    return MapDataOut(
        location=loc.resolved_name,
        latitude=loc.latitude,
        longitude=loc.longitude,
        place_id=loc.place_id,
        formatted_address=loc.resolved_name,
        maps_embed_url=maps_service.build_embed_url(loc.latitude, loc.longitude, zoom, loc.place_id),
        static_map_url=maps_service.build_static_map_url(loc.latitude, loc.longitude, zoom),
        place_details=place_details,
    )


# ── YouTube endpoints ─────────────────────────────────────────────────────────

@router.get(
    "/youtube/query/{query_id}",
    response_model=YouTubeResponse,
    summary="Get YouTube travel videos for a stored query's location",
)
async def youtube_for_query(
    query_id: UUID,
    max_results: int = Query(6, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Returns relevant YouTube videos for the stored query's location."""
    location = await _get_location_for_query(query_id, db)
    videos_raw = await youtube_service.search_location_videos(location.resolved_name, max_results)
    from app.schemas.weather import YouTubeVideo
    return YouTubeResponse(
        location=location.resolved_name,
        query_used=f"{location.resolved_name} travel weather",
        videos=[YouTubeVideo(**v) for v in videos_raw],
    )


@router.get(
    "/youtube/location",
    response_model=YouTubeResponse,
    summary="Get YouTube travel videos for any location string",
)
async def youtube_for_location(
    location: str = Query(..., min_length=1, description="Any location string"),
    max_results: int = Query(6, ge=1, le=10),
):
    """Geocodes any location string and returns relevant YouTube videos."""
    loc = await _geocode_raw(location)
    videos_raw = await youtube_service.search_location_videos(loc.resolved_name, max_results)
    from app.schemas.weather import YouTubeVideo
    return YouTubeResponse(
        location=loc.resolved_name,
        query_used=f"{loc.resolved_name} travel weather",
        videos=[YouTubeVideo(**v) for v in videos_raw],
    )
