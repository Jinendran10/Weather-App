"""
SQLAlchemy ORM models for the weather application.
"""

import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Date,
    Boolean, Text, ForeignKey, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class QueryStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Location(Base):
    """Stores validated and geocoded locations."""
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    raw_input = Column(String(500), nullable=False, comment="Original user-provided location string")
    resolved_name = Column(String(500), nullable=False, comment="Human-readable resolved location name")
    country = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    city = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    place_id = Column(String(500), nullable=True, comment="Google Places ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    weather_queries = relationship("WeatherQuery", back_populates="location", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Location id={self.id} name='{self.resolved_name}'>"


class WeatherQuery(Base):
    """
    Core entity storing a user weather query with:
    - location reference
    - date range
    - cached weather results
    """
    __tablename__ = "weather_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    date_from = Column(Date, nullable=False, comment="Start of requested date range")
    date_to = Column(Date, nullable=False, comment="End of requested date range")
    label = Column(String(300), nullable=True, comment="Optional user-defined label for this query")
    status = Column(SAEnum(QueryStatus), default=QueryStatus.PENDING, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    location = relationship("Location", back_populates="weather_queries")
    weather_records = relationship("WeatherRecord", back_populates="query", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WeatherQuery id={self.id} from={self.date_from} to={self.date_to}>"


class WeatherRecord(Base):
    """
    Stores daily weather data points for a given query.
    One WeatherQuery can produce many WeatherRecords (one per day).
    """
    __tablename__ = "weather_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    query_id = Column(UUID(as_uuid=True), ForeignKey("weather_queries.id", ondelete="CASCADE"), nullable=False)
    record_date = Column(Date, nullable=False, index=True)

    # Temperature (Celsius)
    temp_min = Column(Float, nullable=True)
    temp_max = Column(Float, nullable=True)
    temp_avg = Column(Float, nullable=True)
    feels_like = Column(Float, nullable=True)

    # Atmospheric conditions
    humidity = Column(Integer, nullable=True, comment="Percentage 0-100")
    pressure = Column(Float, nullable=True, comment="hPa")
    wind_speed = Column(Float, nullable=True, comment="m/s")
    wind_direction = Column(Integer, nullable=True, comment="Degrees 0-360")
    visibility = Column(Integer, nullable=True, comment="Meters")
    uv_index = Column(Float, nullable=True)
    cloud_cover = Column(Integer, nullable=True, comment="Percentage 0-100")

    # Precipitation
    precipitation = Column(Float, nullable=True, comment="mm")
    snow = Column(Float, nullable=True, comment="mm")

    # Description
    weather_main = Column(String(100), nullable=True, comment="e.g. Rain, Clear")
    weather_description = Column(String(300), nullable=True)
    weather_icon = Column(String(50), nullable=True)

    # Astronomy
    sunrise = Column(DateTime(timezone=True), nullable=True)
    sunset = Column(DateTime(timezone=True), nullable=True)

    # Raw JSON payload from provider
    raw_data = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    query = relationship("WeatherQuery", back_populates="weather_records")

    def __repr__(self):
        return f"<WeatherRecord id={self.id} date={self.record_date} temp_avg={self.temp_avg}°C>"
