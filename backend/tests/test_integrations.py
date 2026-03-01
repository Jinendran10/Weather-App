"""
Test suite for 3rd-party integrations and export endpoints.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch
from datetime import date


MOCK_GEO = {
    "raw_input": "Tokyo",
    "resolved_name": "Tokyo, Japan",
    "country": "Japan",
    "state": None,
    "city": "Tokyo",
    "latitude": 35.6762,
    "longitude": 139.6503,
    "place_id": "99887766",
}

MOCK_VIDEOS = [
    {
        "video_id": "abc123",
        "title": "Tokyo Travel Guide",
        "description": "Explore Tokyo",
        "thumbnail_url": "https://img.youtube.com/vi/abc123/hqdefault.jpg",
        "channel_title": "Travel Channel",
        "published_at": "2024-01-01T00:00:00Z",
        "youtube_url": "https://www.youtube.com/watch?v=abc123",
    }
]


# ─── YouTube integration ──────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.routers.integrations.geocoding_service.resolve_location", new_callable=AsyncMock)
@patch("app.routers.integrations.youtube_service.search_location_videos", new_callable=AsyncMock)
async def test_youtube_for_location(mock_videos, mock_geo, client):
    mock_geo.return_value = MOCK_GEO
    mock_videos.return_value = MOCK_VIDEOS

    response = await client.get(
        "/api/v1/integrations/youtube/location",
        params={"location": "Tokyo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["location"] == "Tokyo, Japan"
    assert len(data["videos"]) == 1
    assert data["videos"][0]["video_id"] == "abc123"


# ─── Maps integration ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.routers.integrations.geocoding_service.resolve_location", new_callable=AsyncMock)
async def test_maps_for_location(mock_geo, client):
    mock_geo.return_value = MOCK_GEO

    response = await client.get(
        "/api/v1/integrations/maps/location",
        params={"location": "Tokyo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["latitude"] == 35.6762
    assert data["longitude"] == 139.6503
    assert "maps_embed_url" in data
    assert "static_map_url" in data


# ─── Export endpoint ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_empty_returns_404(client):
    response = await client.post(
        "/api/v1/export",
        json={"format": "csv", "query_ids": ["00000000-0000-0000-0000-000000000000"]},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_invalid_format(client):
    response = await client.post(
        "/api/v1/export",
        json={"format": "xml"},
    )
    assert response.status_code == 422
