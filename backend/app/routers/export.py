"""
Data export router.
Supports exporting weather query data to CSV and JSON formats.
"""

import csv
import json
import os
import io
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.weather import WeatherQuery, WeatherRecord, Location
from app.schemas.weather import ExportRequest

router = APIRouter(prefix="/export", tags=["Export"])


def _build_flat_rows(queries: list) -> List[dict]:
    """Flatten queries + records into a list of dicts suitable for CSV."""
    rows = []
    for q in queries:
        for rec in q.weather_records:
            rows.append(
                {
                    "query_id": str(q.id),
                    "query_label": q.label or "",
                    "location": q.location.resolved_name,
                    "country": q.location.country or "",
                    "latitude": q.location.latitude,
                    "longitude": q.location.longitude,
                    "query_date_from": str(q.date_from),
                    "query_date_to": str(q.date_to),
                    "record_date": str(rec.record_date),
                    "temp_min_c": rec.temp_min,
                    "temp_max_c": rec.temp_max,
                    "temp_avg_c": rec.temp_avg,
                    "feels_like_c": rec.feels_like,
                    "humidity_pct": rec.humidity,
                    "pressure_hpa": rec.pressure,
                    "wind_speed_ms": rec.wind_speed,
                    "wind_direction_deg": rec.wind_direction,
                    "visibility_m": rec.visibility,
                    "uv_index": rec.uv_index,
                    "cloud_cover_pct": rec.cloud_cover,
                    "precipitation_mm": rec.precipitation,
                    "snow_mm": rec.snow,
                    "weather_main": rec.weather_main or "",
                    "weather_description": rec.weather_description or "",
                    "query_created_at": str(q.created_at),
                }
            )
        if not q.weather_records:
            # Include query row even with no records
            rows.append(
                {
                    "query_id": str(q.id),
                    "query_label": q.label or "",
                    "location": q.location.resolved_name,
                    "country": q.location.country or "",
                    "latitude": q.location.latitude,
                    "longitude": q.location.longitude,
                    "query_date_from": str(q.date_from),
                    "query_date_to": str(q.date_to),
                    "record_date": "",
                    "temp_min_c": None,
                    "temp_max_c": None,
                    "temp_avg_c": None,
                    "feels_like_c": None,
                    "humidity_pct": None,
                    "pressure_hpa": None,
                    "wind_speed_ms": None,
                    "wind_direction_deg": None,
                    "visibility_m": None,
                    "uv_index": None,
                    "cloud_cover_pct": None,
                    "precipitation_mm": None,
                    "snow_mm": None,
                    "weather_main": "",
                    "weather_description": "",
                    "query_created_at": str(q.created_at),
                }
            )
    return rows


async def _load_queries(
    db: AsyncSession, query_ids: Optional[List[UUID]] = None
) -> list:
    stmt = select(WeatherQuery).options(
        selectinload(WeatherQuery.location),
        selectinload(WeatherQuery.weather_records),
    )
    if query_ids:
        stmt = stmt.where(WeatherQuery.id.in_(query_ids))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post(
    "",
    summary="Export weather data to CSV or JSON",
    description=(
        "Export stored weather queries and their daily records. "
        "Specify `format: 'csv'` or `format: 'json'`. "
        "Optionally filter by specific `query_ids`; omit to export all records."
    ),
)
async def export_data(
    payload: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    queries = await _load_queries(db, payload.query_ids)
    if not queries:
        raise HTTPException(status_code=404, detail="No data found for the given criteria.")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"weather_export_{timestamp}"

    if payload.format == "csv":
        rows = _build_flat_rows(queries)
        if not rows:
            raise HTTPException(status_code=404, detail="No weather records to export.")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.csv"',
                "X-Record-Count": str(len(rows)),
            },
        )

    elif payload.format == "json":
        export_data = []
        for q in queries:
            entry = {
                "query_id": str(q.id),
                "label": q.label,
                "notes": q.notes,
                "status": q.status.value,
                "location": {
                    "id": str(q.location.id),
                    "raw_input": q.location.raw_input,
                    "resolved_name": q.location.resolved_name,
                    "country": q.location.country,
                    "state": q.location.state,
                    "city": q.location.city,
                    "latitude": q.location.latitude,
                    "longitude": q.location.longitude,
                },
                "date_from": str(q.date_from),
                "date_to": str(q.date_to),
                "created_at": str(q.created_at),
                "updated_at": str(q.updated_at),
            }
            if payload.include_records:
                entry["weather_records"] = [
                    {
                        "record_id": str(r.id),
                        "date": str(r.record_date),
                        "temp_min_c": r.temp_min,
                        "temp_max_c": r.temp_max,
                        "temp_avg_c": r.temp_avg,
                        "feels_like_c": r.feels_like,
                        "humidity_pct": r.humidity,
                        "pressure_hpa": r.pressure,
                        "wind_speed_ms": r.wind_speed,
                        "wind_direction_deg": r.wind_direction,
                        "visibility_m": r.visibility,
                        "uv_index": r.uv_index,
                        "cloud_cover_pct": r.cloud_cover,
                        "precipitation_mm": r.precipitation,
                        "snow_mm": r.snow,
                        "weather_main": r.weather_main,
                        "weather_description": r.weather_description,
                        "weather_icon": r.weather_icon,
                        "sunrise": str(r.sunrise) if r.sunrise else None,
                        "sunset": str(r.sunset) if r.sunset else None,
                    }
                    for r in sorted(q.weather_records, key=lambda x: x.record_date)
                ]
            export_data.append(entry)

        json_output = json.dumps(
            {"exported_at": timestamp, "total_queries": len(export_data), "data": export_data},
            indent=2,
            default=str,
        )
        return StreamingResponse(
            iter([json_output]),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.json"',
                "X-Record-Count": str(len(export_data)),
            },
        )
