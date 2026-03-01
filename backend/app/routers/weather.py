"""
Weather CRUD router.

Endpoints:
  POST   /weather                  – Simple weather lookup (Nominatim + OpenWeather)
  POST   /weather/current          – Get live current weather (cached, full detail)
  POST   /weather/queries          – CREATE  a date-range query and fetch data
  GET    /weather/queries          – READ    all stored queries
  GET    /weather/queries/{id}     – READ    a single query with records
  PATCH  /weather/queries/{id}     – UPDATE  query metadata
  DELETE /weather/queries/{id}     – DELETE  a query and all records
  PATCH  /weather/records/{id}     – UPDATE  an individual weather record
  DELETE /weather/records/{id}     – DELETE  an individual weather record
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.weather import Location, WeatherQuery, WeatherRecord, QueryStatus, CurrentWeatherCache
from app.schemas.weather import (
    CurrentWeatherOut,
    LocationCreate,
    LocationOut,
    SimpleWeatherRequest,
    SimpleWeatherResponse,
    WeatherQueryCreate,
    WeatherQueryOut,
    WeatherQuerySummary,
    WeatherQueryUpdate,
    WeatherRecordOut,
    WeatherRecordUpdate,
    MessageResponse,
    YouTubeEmbedData,
)
from app.services.geocoding_service import geocoding_service, GeocodingError
from app.services.weather_service import weather_service, WeatherAPIError, RateLimitError
from app.services.youtube_service import youtube_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/weather", tags=["Weather"])


# ────────────────────────────────────────────────────────────────────────────
# Helper: get-or-create location
# ────────────────────────────────────────────────────────────────────────────

async def _resolve_or_create_location(
    raw_input: str, db: AsyncSession
) -> Location:
    """Geocode a location string via Nominatim and persist it (or re-use existing)."""
    try:
        geo_data = await geocoding_service.resolve_location(raw_input)
    except GeocodingError as exc:
        # Nominatim returned no results → 404 Not Found
        raise HTTPException(status_code=404, detail=str(exc))

    # Re-use existing location if lat/lon match within ~1km tolerance
    result = await db.execute(
        select(Location).where(
            func.abs(Location.latitude - geo_data["latitude"]) < 0.01,
            func.abs(Location.longitude - geo_data["longitude"]) < 0.01,
        )
    )
    existing = result.scalars().first()
    if existing:
        return existing

    location = Location(**geo_data)
    db.add(location)
    await db.flush()
    return location


# ────────────────────────────────────────────────────────────────────────────
# Helper: fetch weather data for a date range
# ────────────────────────────────────────────────────────────────────────────

async def _fetch_weather_for_range(
    query: WeatherQuery,
    location: Location,
    db: AsyncSession,
) -> None:
    """
    Fetch weather records from OpenWeatherMap for query.date_from → query.date_to.
    Intelligently routes to forecast vs historical depending on dates.

    Caching:  Checks if a weather record already exists in the DB for the same
    location and date (from any previous query within cache TTL).  If found, the
    cached record is cloned instead of making a new API call.

    Rate-limit: Catches 429 errors gracefully and logs them.
    """
    today = date.today()
    records_to_add: List[WeatherRecord] = []
    error_dates: List[str] = []
    cache_cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.WEATHER_CACHE_TTL_MINUTES)

    current_date = query.date_from
    while current_date <= query.date_to:
        try:
            # ── Check DB cache for this location + date ───────────────────
            existing_result = await db.execute(
                select(WeatherRecord)
                .join(WeatherQuery, WeatherRecord.query_id == WeatherQuery.id)
                .join(Location, WeatherQuery.location_id == Location.id)
                .where(
                    func.abs(Location.latitude - location.latitude) < 0.01,
                    func.abs(Location.longitude - location.longitude) < 0.01,
                    WeatherRecord.record_date == current_date,
                    WeatherRecord.created_at >= cache_cutoff,
                )
                .order_by(WeatherRecord.created_at.desc())
            )
            cached_record = existing_result.scalars().first()

            if cached_record:
                logger.info(
                    "Cache HIT for date %s at (%.4f, %.4f) – cloning record",
                    current_date, location.latitude, location.longitude,
                )
                # Clone cached record for this query
                rec_data = {
                    "query_id": query.id,
                    "record_date": cached_record.record_date,
                    "temp_min": cached_record.temp_min,
                    "temp_max": cached_record.temp_max,
                    "temp_avg": cached_record.temp_avg,
                    "feels_like": cached_record.feels_like,
                    "humidity": cached_record.humidity,
                    "pressure": cached_record.pressure,
                    "wind_speed": cached_record.wind_speed,
                    "wind_direction": cached_record.wind_direction,
                    "visibility": cached_record.visibility,
                    "uv_index": cached_record.uv_index,
                    "cloud_cover": cached_record.cloud_cover,
                    "precipitation": cached_record.precipitation,
                    "snow": cached_record.snow,
                    "weather_main": cached_record.weather_main,
                    "weather_description": cached_record.weather_description,
                    "weather_icon": cached_record.weather_icon,
                    "sunrise": cached_record.sunrise,
                    "sunset": cached_record.sunset,
                    "raw_data": cached_record.raw_data,
                }
                record = WeatherRecord(**rec_data)
                records_to_add.append(record)
                current_date += timedelta(days=1)
                continue

            # ── Cache MISS – call API ─────────────────────────────────────
            delta_days = (current_date - today).days

            if -5 <= delta_days <= 7:
                # Use One Call 3.0 forecast (covers ±5 days roughly)
                forecast = await weather_service.get_forecast(location.latitude, location.longitude)
                daily = forecast.get("daily", [])
                matched = next(
                    (
                        d for d in daily
                        if date.fromtimestamp(d["dt"]) == current_date
                    ),
                    None,
                )
                if matched:
                    rec_data = weather_service.parse_daily_record(
                        matched, query.id, current_date
                    )
                else:
                    # Use current data for today
                    raw = await weather_service.get_current_weather(
                        location.latitude, location.longitude
                    )
                    parsed = weather_service.parse_current_weather(raw, {})
                    rec_data = {
                        "query_id": query.id,
                        "record_date": current_date,
                        "temp_avg": parsed["temp_celsius"],
                        "feels_like": parsed["feels_like_celsius"],
                        "humidity": parsed["humidity"],
                        "pressure": parsed["pressure"],
                        "wind_speed": parsed["wind_speed"],
                        "wind_direction": parsed["wind_direction"],
                        "visibility": parsed["visibility"],
                        "cloud_cover": parsed["cloud_cover"],
                        "weather_main": parsed["weather_main"],
                        "weather_description": parsed["weather_description"],
                        "weather_icon": parsed["weather_icon"],
                        "sunrise": parsed["sunrise"],
                        "sunset": parsed["sunset"],
                        "raw_data": json.dumps(raw),
                    }
            else:
                # Historical via timemachine
                raw = await weather_service.get_historical(
                    location.latitude, location.longitude, current_date
                )
                # historical response has data array
                day_data = raw.get("data", [raw])[0] if raw.get("data") else raw
                rec_data = weather_service.parse_daily_record(
                    day_data, query.id, current_date
                )

            record = WeatherRecord(**rec_data)
            records_to_add.append(record)

        except RateLimitError as exc:
            logger.error("Rate limit hit while fetching date %s: %s", current_date, exc)
            error_dates.append(f"{current_date} (rate limited)")
            # Stop fetching more dates to avoid hammering the API
            break
        except WeatherAPIError:
            error_dates.append(str(current_date))
        except Exception:
            error_dates.append(str(current_date))

        current_date += timedelta(days=1)

    db.add_all(records_to_add)
    query.status = QueryStatus.SUCCESS if records_to_add else QueryStatus.FAILED
    await db.flush()


# ────────────────────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=SimpleWeatherResponse,
    summary="Simple weather lookup – Nominatim geocoding + OpenWeather data",
)
async def simple_weather_lookup(
    payload: SimpleWeatherRequest,
    debug: bool = Query(False, description="Include full raw API response in the reply"),
    db: AsyncSession = Depends(get_db),
):
    """
    **Simple weather endpoint.**

    1. Validates the location via Nominatim (OpenStreetMap) – no API key needed.
    2. Checks the DB cache – if a recent result (< 10 min) exists, returns it
       without calling OpenWeather, saving API quota.
    3. On cache miss, calls OpenWeather Current Weather API.
    4. Returns a clean, minimal JSON response.

    Request body::

        { "location": "Kochi" }

    Response::

        {
            "location": "Kochi, Kerala, India",
            "latitude": 9.9312,
            "longitude": 76.2673,
            "temperature": 30,
            "humidity": 75,
            "weather_description": "Cloudy"
        }
    """
    # Step 1 – Geocode with Nominatim (raises 404 if not found)
    location = await _resolve_or_create_location(payload.location, db)

    # Step 2 – Check DB cache for recent weather at these coordinates
    cache_cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=settings.WEATHER_CACHE_TTL_MINUTES
    )
    cache_result = await db.execute(
        select(CurrentWeatherCache).where(
            func.abs(CurrentWeatherCache.latitude - location.latitude) < 0.01,
            func.abs(CurrentWeatherCache.longitude - location.longitude) < 0.01,
            CurrentWeatherCache.cached_at >= cache_cutoff,
        ).order_by(CurrentWeatherCache.cached_at.desc())
    )
    cached = cache_result.scalars().first()

    if cached:
        logger.info(
            "Cache HIT for '%s' (%.4f, %.4f) – skipping API call",
            payload.location, location.latitude, location.longitude,
        )
        yt_data = YouTubeEmbedData(**youtube_service.build_search_url(location.resolved_name))
        logger.debug("[debug=%s] YouTube search URL: %s", debug, yt_data.search_url)
        return SimpleWeatherResponse(
            location=location.resolved_name,
            latitude=location.latitude,
            longitude=location.longitude,
            temperature=cached.temp_celsius,
            feels_like=cached.feels_like_celsius,
            humidity=cached.humidity,
            pressure=cached.pressure,
            wind_speed=cached.wind_speed,
            weather_description=cached.weather_description or "",
            weather_main=cached.weather_main,
            weather_icon=cached.weather_icon,
            recorded_at=cached.recorded_at.isoformat() if cached.recorded_at else None,
            youtube=yt_data,
            debug_raw_json=json.loads(cached.raw_json) if debug and cached.raw_json else None,
        )

    # Step 3 – Cache MISS → call OpenWeather
    logger.info(
        "Cache MISS for '%s' (%.4f, %.4f) – calling OpenWeather API",
        payload.location, location.latitude, location.longitude,
    )
    try:
        raw = await weather_service.get_current_weather(
            location.latitude, location.longitude
        )
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except WeatherAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    parsed = weather_service.parse_current_weather(raw, {})

    # Step 4 – Persist to cache so subsequent calls are free
    cache_entry = CurrentWeatherCache(
        latitude=location.latitude,
        longitude=location.longitude,
        temp_celsius=parsed["temp_celsius"],
        temp_fahrenheit=parsed["temp_fahrenheit"],
        feels_like_celsius=parsed["feels_like_celsius"],
        humidity=parsed["humidity"],
        pressure=parsed["pressure"],
        wind_speed=parsed["wind_speed"],
        wind_direction=parsed["wind_direction"],
        visibility=parsed["visibility"],
        cloud_cover=parsed["cloud_cover"],
        weather_main=parsed["weather_main"],
        weather_description=parsed["weather_description"],
        weather_icon=parsed["weather_icon"],
        sunrise=parsed["sunrise"],
        sunset=parsed["sunset"],
        recorded_at=parsed["recorded_at"],
        raw_json=json.dumps(raw),
    )
    db.add(cache_entry)
    await db.flush()

    yt_data = YouTubeEmbedData(**youtube_service.build_search_url(location.resolved_name))
    logger.debug("[debug=%s] YouTube search URL: %s", debug, yt_data.search_url)
    if debug:
        logger.info("[debug] Full Raw JSON for '%s': %s", payload.location, json.dumps(raw))
    return SimpleWeatherResponse(
        location=location.resolved_name,
        latitude=location.latitude,
        longitude=location.longitude,
        temperature=parsed["temp_celsius"],
        feels_like=parsed["feels_like_celsius"],
        humidity=parsed["humidity"],
        pressure=parsed["pressure"],
        wind_speed=parsed["wind_speed"],
        weather_description=parsed["weather_description"] or "",
        weather_main=parsed["weather_main"],
        weather_icon=parsed["weather_icon"],
        recorded_at=parsed["recorded_at"].isoformat() if parsed.get("recorded_at") else None,
        youtube=yt_data,
        debug_raw_json=raw if debug else None,
    )


@router.post(
    "/current",
    response_model=CurrentWeatherOut,
    summary="Get live current weather for any location",
)
async def get_current_weather(
    payload: LocationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns real-time weather for the supplied location.
    Uses DB cache: if a result for the same coordinates is less than
    WEATHER_CACHE_TTL_MINUTES old (default 10 min), the cached version
    is returned without calling the external API.
    """
    location = await _resolve_or_create_location(payload.raw_input, db)
    loc_out = LocationOut.model_validate(location)

    # ── Check DB cache first ──────────────────────────────────────────────
    cache_cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.WEATHER_CACHE_TTL_MINUTES)
    cache_result = await db.execute(
        select(CurrentWeatherCache).where(
            func.abs(CurrentWeatherCache.latitude - location.latitude) < 0.01,
            func.abs(CurrentWeatherCache.longitude - location.longitude) < 0.01,
            CurrentWeatherCache.cached_at >= cache_cutoff,
        ).order_by(CurrentWeatherCache.cached_at.desc())
    )
    cached = cache_result.scalars().first()

    if cached:
        logger.info(
            "Cache HIT for (%.4f, %.4f) – returning cached weather (age: %s)",
            location.latitude, location.longitude,
            datetime.now(timezone.utc) - cached.cached_at,
        )
        return CurrentWeatherOut(
            location=loc_out,
            recorded_at=cached.recorded_at or cached.cached_at,
            temp_celsius=cached.temp_celsius,
            temp_fahrenheit=cached.temp_fahrenheit,
            feels_like_celsius=cached.feels_like_celsius,
            humidity=cached.humidity,
            pressure=cached.pressure,
            wind_speed=cached.wind_speed,
            wind_direction=cached.wind_direction,
            visibility=cached.visibility,
            cloud_cover=cached.cloud_cover,
            weather_main=cached.weather_main,
            weather_description=cached.weather_description,
            weather_icon=cached.weather_icon,
            sunrise=cached.sunrise,
            sunset=cached.sunset,
        )

    # ── Cache MISS – call the API ─────────────────────────────────────────
    logger.info("Cache MISS for (%.4f, %.4f) – calling OpenWeatherMap API", location.latitude, location.longitude)
    try:
        raw = await weather_service.get_current_weather(location.latitude, location.longitude)
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except WeatherAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    parsed = weather_service.parse_current_weather(raw, {})

    # ── Store in cache ────────────────────────────────────────────────────
    cache_entry = CurrentWeatherCache(
        latitude=location.latitude,
        longitude=location.longitude,
        temp_celsius=parsed["temp_celsius"],
        temp_fahrenheit=parsed["temp_fahrenheit"],
        feels_like_celsius=parsed["feels_like_celsius"],
        humidity=parsed["humidity"],
        pressure=parsed["pressure"],
        wind_speed=parsed["wind_speed"],
        wind_direction=parsed["wind_direction"],
        visibility=parsed["visibility"],
        cloud_cover=parsed["cloud_cover"],
        weather_main=parsed["weather_main"],
        weather_description=parsed["weather_description"],
        weather_icon=parsed["weather_icon"],
        sunrise=parsed["sunrise"],
        sunset=parsed["sunset"],
        recorded_at=parsed["recorded_at"],
        raw_json=json.dumps(raw),
    )
    db.add(cache_entry)
    await db.flush()

    return CurrentWeatherOut(location=loc_out, **parsed)


@router.post(
    "/queries",
    response_model=WeatherQueryOut,
    status_code=status.HTTP_201_CREATED,
    summary="CREATE – Submit a weather query for a location and date range",
)
async def create_weather_query(
    payload: WeatherQueryCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    **CREATE** operation.
    - Validates and geocodes the location.
    - Validates the date range (max 365 days, date_from ≤ date_to).
    - Fetches weather data from OpenWeatherMap.
    - Persists query + daily records to PostgreSQL.
    """
    location = await _resolve_or_create_location(payload.location, db)

    query = WeatherQuery(
        location_id=location.id,
        date_from=payload.date_from,
        date_to=payload.date_to,
        label=payload.label,
        notes=payload.notes,
        status=QueryStatus.PENDING,
    )
    db.add(query)
    await db.flush()

    await _fetch_weather_for_range(query, location, db)

    # Reload with relationships
    result = await db.execute(
        select(WeatherQuery)
        .options(
            selectinload(WeatherQuery.location),
            selectinload(WeatherQuery.weather_records),
        )
        .where(WeatherQuery.id == query.id)
    )
    full_query = result.scalars().first()
    return full_query


@router.get(
    "/queries",
    response_model=List[WeatherQuerySummary],
    summary="READ – List all weather queries",
)
async def list_weather_queries(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    location_search: Optional[str] = Query(None, description="Filter by location name (partial match)"),
    db: AsyncSession = Depends(get_db),
):
    """
    **READ** operation.
    Returns a paginated list of all stored weather queries with summary statistics.
    """
    stmt = (
        select(
            WeatherQuery.id,
            Location.resolved_name.label("location_name"),
            Location.latitude,
            Location.longitude,
            WeatherQuery.date_from,
            WeatherQuery.date_to,
            WeatherQuery.label,
            WeatherQuery.status,
            WeatherQuery.created_at,
            func.count(WeatherRecord.id).label("record_count"),
        )
        .join(Location, WeatherQuery.location_id == Location.id)
        .outerjoin(WeatherRecord, WeatherRecord.query_id == WeatherQuery.id)
        .group_by(WeatherQuery.id, Location.resolved_name, Location.latitude, Location.longitude)
        .order_by(WeatherQuery.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if location_search:
        stmt = stmt.where(Location.resolved_name.ilike(f"%{location_search}%"))

    result = await db.execute(stmt)
    rows = result.all()
    return [WeatherQuerySummary(**row._asdict()) for row in rows]


@router.get(
    "/queries/{query_id}",
    response_model=WeatherQueryOut,
    summary="READ – Get a single query with all daily weather records",
)
async def get_weather_query(
    query_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """**READ** operation. Returns full query detail including all daily records."""
    result = await db.execute(
        select(WeatherQuery)
        .options(
            selectinload(WeatherQuery.location),
            selectinload(WeatherQuery.weather_records),
        )
        .where(WeatherQuery.id == query_id)
    )
    query = result.scalars().first()
    if not query:
        raise HTTPException(status_code=404, detail="Weather query not found.")
    return query


@router.patch(
    "/queries/{query_id}",
    response_model=WeatherQueryOut,
    summary="UPDATE – Edit a query's label, notes, or date range",
)
async def update_weather_query(
    query_id: UUID,
    payload: WeatherQueryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    **UPDATE** operation.
    Updatable fields: `label`, `notes`, `date_from`, `date_to`.
    If the date range changes, existing records are cleared and weather data is re-fetched.
    Location cannot be changed (create a new query instead).
    """
    result = await db.execute(
        select(WeatherQuery)
        .options(selectinload(WeatherQuery.location), selectinload(WeatherQuery.weather_records))
        .where(WeatherQuery.id == query_id)
    )
    query = result.scalars().first()
    if not query:
        raise HTTPException(status_code=404, detail="Weather query not found.")

    date_changed = False
    if payload.label is not None:
        query.label = payload.label
    if payload.notes is not None:
        query.notes = payload.notes
    if payload.date_from is not None:
        query.date_from = payload.date_from
        date_changed = True
    if payload.date_to is not None:
        query.date_to = payload.date_to
        date_changed = True

    if date_changed:
        # Validate updated range
        if query.date_from > query.date_to:
            raise HTTPException(status_code=422, detail="date_from must be on or before date_to.")
        # Clear existing records and re-fetch
        for rec in query.weather_records:
            await db.delete(rec)
        await db.flush()
        query.status = QueryStatus.PENDING
        await _fetch_weather_for_range(query, query.location, db)

    await db.flush()
    result2 = await db.execute(
        select(WeatherQuery)
        .options(selectinload(WeatherQuery.location), selectinload(WeatherQuery.weather_records))
        .where(WeatherQuery.id == query_id)
    )
    return result2.scalars().first()


@router.delete(
    "/queries/{query_id}",
    response_model=MessageResponse,
    summary="DELETE – Remove a query and all its weather records",
)
async def delete_weather_query(
    query_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    **DELETE** operation.
    Cascade-deletes the query and all associated daily weather records.
    """
    result = await db.execute(select(WeatherQuery).where(WeatherQuery.id == query_id))
    query = result.scalars().first()
    if not query:
        raise HTTPException(status_code=404, detail="Weather query not found.")
    await db.delete(query)
    return MessageResponse(message="Query deleted successfully.", detail=str(query_id))


@router.patch(
    "/records/{record_id}",
    response_model=WeatherRecordOut,
    summary="UPDATE – Manually correct a single daily weather record",
)
async def update_weather_record(
    record_id: UUID,
    payload: WeatherRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    **UPDATE** operation on a specific daily record.
    Useful for correcting API data or adding manual observations.
    """
    result = await db.execute(select(WeatherRecord).where(WeatherRecord.id == record_id))
    record = result.scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="Weather record not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    await db.flush()
    return record


@router.delete(
    "/records/{record_id}",
    response_model=MessageResponse,
    summary="DELETE – Remove a single daily weather record",
)
async def delete_weather_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """**DELETE** a specific daily record without removing the parent query."""
    result = await db.execute(select(WeatherRecord).where(WeatherRecord.id == record_id))
    record = result.scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="Weather record not found.")
    await db.delete(record)
    return MessageResponse(message="Record deleted successfully.", detail=str(record_id))
