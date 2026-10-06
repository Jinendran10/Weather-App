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

# ─── YouTube integration ──────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.routers.integrations.geocoding_service.resolve_location", new_callable=AsyncMock)
async def test_youtube_for_location(mock_geo, client):
    # The YouTube integration builds a search URL locally (no API key, no embed),
    # so only geocoding needs mocking.
    mock_geo.return_value = MOCK_GEO

    response = await client.get(
        "/api/v1/integrations/youtube/location",
        params={"location": "Tokyo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["location"] == "Tokyo, Japan"
    assert data["youtube"]["query"] == "Tokyo, Japan travel guide"
    assert data["youtube"]["search_url"] == (
        "https://www.youtube.com/results?search_query=Tokyo%2C+Japan+travel+guide"
    )


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
