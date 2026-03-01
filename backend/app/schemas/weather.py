"""
Pydantic schemas for request/response validation.
"""

from __future__ import annotations
from uuid import UUID
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator
from app.models.weather import QueryStatus


# ────────────────────────────────────────────────
# Location schemas
# ────────────────────────────────────────────────

class LocationBase(BaseModel):
    raw_input: str = Field(..., min_length=1, max_length=500, description="Location as entered by user")


class LocationCreate(LocationBase):
    pass


class LocationOut(BaseModel):
    id: UUID
    raw_input: str
    resolved_name: str
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    latitude: float
    longitude: float
    place_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ────────────────────────────────────────────────
# WeatherRecord schemas
# ────────────────────────────────────────────────

class WeatherRecordBase(BaseModel):
    record_date: date
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    temp_avg: Optional[float] = None
    feels_like: Optional[float] = None
    humidity: Optional[int] = Field(None, ge=0, le=100)
    pressure: Optional[float] = None
    wind_speed: Optional[float] = Field(None, ge=0)
    wind_direction: Optional[int] = Field(None, ge=0, le=360)
    visibility: Optional[int] = Field(None, ge=0)
    uv_index: Optional[float] = Field(None, ge=0)
    cloud_cover: Optional[int] = Field(None, ge=0, le=100)
    precipitation: Optional[float] = Field(None, ge=0)
    snow: Optional[float] = Field(None, ge=0)
    weather_main: Optional[str] = None
    weather_description: Optional[str] = None
    weather_icon: Optional[str] = None


class WeatherRecordUpdate(BaseModel):
    """Fields the user is allowed to manually correct."""
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    temp_avg: Optional[float] = None
    feels_like: Optional[float] = None
    humidity: Optional[int] = Field(None, ge=0, le=100)
    pressure: Optional[float] = None
    wind_speed: Optional[float] = Field(None, ge=0)
    wind_direction: Optional[int] = Field(None, ge=0, le=360)
    visibility: Optional[int] = Field(None, ge=0)
    uv_index: Optional[float] = Field(None, ge=0)
    cloud_cover: Optional[int] = Field(None, ge=0, le=100)
    precipitation: Optional[float] = Field(None, ge=0)
    snow: Optional[float] = Field(None, ge=0)
    weather_description: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "WeatherRecordUpdate":
        if not any(
            v is not None for v in self.model_dump().values()
        ):
            raise ValueError("At least one field must be provided for update.")
        return self


class WeatherRecordOut(WeatherRecordBase):
    id: UUID
    query_id: UUID
    sunrise: Optional[datetime] = None
    sunset: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ────────────────────────────────────────────────
# WeatherQuery schemas
# ────────────────────────────────────────────────

class WeatherQueryCreate(BaseModel):
    location: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description=(
            "Any location string: city name, ZIP code, GPS coords (lat,lon), "
            "landmark, or full address."
        ),
        examples=["New York", "10001", "48.8566,2.3522", "Eiffel Tower"],
    )
    date_from: date = Field(..., description="Start date (inclusive) in YYYY-MM-DD format")
    date_to: date = Field(..., description="End date (inclusive) in YYYY-MM-DD format")
    label: Optional[str] = Field(None, max_length=300, description="Optional user label")
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("date_from", "date_to", mode="before")
    @classmethod
    def parse_dates(cls, v):
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format.")
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "WeatherQueryCreate":
        if self.date_from > self.date_to:
            raise ValueError("date_from must be on or before date_to.")
        delta = (self.date_to - self.date_from).days
        if delta > 365:
            raise ValueError("Date range cannot exceed 365 days.")
        return self


class WeatherQueryUpdate(BaseModel):
    """Fields the user may update on an existing query."""
    label: Optional[str] = Field(None, max_length=300)
    notes: Optional[str] = Field(None, max_length=2000)
    date_from: Optional[date] = None
    date_to: Optional[date] = None

    @model_validator(mode="after")
    def validate_dates_if_present(self) -> "WeatherQueryUpdate":
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from must be on or before date_to.")
            delta = (self.date_to - self.date_from).days
            if delta > 365:
                raise ValueError("Date range cannot exceed 365 days.")
        return self


class WeatherQueryOut(BaseModel):
    id: UUID
    location: LocationOut
    date_from: date
    date_to: date
    label: Optional[str] = None
    status: QueryStatus
    notes: Optional[str] = None
    weather_records: List[WeatherRecordOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WeatherQuerySummary(BaseModel):
    """Lightweight query representation for list endpoints."""
    id: UUID
    location_name: str
    latitude: float
    longitude: float
    date_from: date
    date_to: date
    label: Optional[str] = None
    status: QueryStatus
    record_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ────────────────────────────────────────────────
# Current weather (non-persisted, live response)
# ────────────────────────────────────────────────

class CurrentWeatherOut(BaseModel):
    location: LocationOut
    recorded_at: datetime
    temp_celsius: float
    temp_fahrenheit: float
    feels_like_celsius: float
    humidity: int
    pressure: float
    wind_speed: float
    wind_direction: int
    visibility: int
    cloud_cover: int
    uv_index: Optional[float] = None
    weather_main: str
    weather_description: str
    weather_icon: str
    sunrise: datetime
    sunset: datetime


# ────────────────────────────────────────────────
# API Integration response schemas
# ────────────────────────────────────────────────

class YouTubeEmbedData(BaseModel):
    """Embed URL payload built without any API calls."""
    embed_url: str = Field(
        ...,
        description="YouTube search-playlist embed URL. Drop into an <iframe src=...>.",
        examples=["https://www.youtube.com/embed?listType=search&list=Kochi+Kerala+India+travel+guide"],
    )
    query: str = Field(..., description="Human-readable search query used to build the URL.")


class YouTubeResponse(BaseModel):
    """Response for /integrations/youtube/* endpoints."""
    location: str
    youtube: YouTubeEmbedData


class MapDataOut(BaseModel):
    location: str
    latitude: float
    longitude: float
    place_id: Optional[str] = None
    formatted_address: Optional[str] = None
    maps_embed_url: str
    static_map_url: str
    place_details: Optional[dict] = None


# ────────────────────────────────────────────────
# Export schemas
# ────────────────────────────────────────────────

class ExportRequest(BaseModel):
    query_ids: Optional[List[UUID]] = Field(
        None, description="Specific query IDs to export; omit for all records."
    )
    format: str = Field("csv", pattern="^(csv|json)$", description="Export format: 'csv' or 'json'")
    include_records: bool = Field(True, description="Include individual daily weather records")


# ────────────────────────────────────────────────
# Simple weather lookup (POST /weather)
# ────────────────────────────────────────────────

class SimpleWeatherRequest(BaseModel):
    """Request body for the simple POST /weather endpoint."""
    location: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Any location: city name, ZIP code, GPS coordinates, landmark, or address.",
        examples=["Kochi", "New York", "10001", "48.8566,2.3522"],
    )


class SimpleWeatherResponse(BaseModel):
    """Clean response for the simple POST /weather endpoint."""
    location: str = Field(..., description="Resolved human-readable location name")
    latitude: float
    longitude: float
    temperature: float = Field(..., description="Current temperature in Celsius")
    humidity: int = Field(..., description="Humidity percentage (0-100)")
    weather_description: str = Field(..., description="Short weather description")
    youtube: Optional[YouTubeEmbedData] = Field(
        None,
        description="YouTube search embed URL for travel videos about this location.",
    )


# ────────────────────────────────────────────────
# Standard API responses
# ────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    field: Optional[str] = None
