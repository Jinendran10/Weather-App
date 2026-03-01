"""
Test suite for weather CRUD endpoints.
Uses mocked external API calls so no live credentials are required.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date, datetime, timezone


# ─── Mock data ────────────────────────────────────────────────────────────────

MOCK_GEO = {
    "raw_input": "New York",
    "resolved_name": "New York, New York, United States",
    "country": "United States",
    "state": "New York",
    "city": "New York",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "place_id": "12345678",
}

MOCK_GEO_KOCHI = {
    "raw_input": "Kochi",
    "resolved_name": "Kochi, Kerala, India",
    "country": "India",
    "state": "Kerala",
    "city": "Kochi",
    "latitude": 9.9312,
    "longitude": 76.2673,
    "place_id": "87654321",
}

MOCK_CURRENT_RAW = {
    "main": {"temp": 15.0, "feels_like": 13.0, "humidity": 60, "pressure": 1013},
    "wind": {"speed": 5.0, "deg": 180},
    "weather": [{"main": "Clear", "description": "clear sky", "icon": "01d"}],
    "clouds": {"all": 10},
    "visibility": 10000,
    "sys": {"sunrise": 1700000000, "sunset": 1700040000},
    "dt": 1700010000,
}

MOCK_FORECAST_RAW = {
    "daily": [
        {
            "dt": int(datetime.now(timezone.utc).timestamp()),
            "temp": {"min": 10.0, "max": 20.0, "day": 15.0},
            "feels_like": {"day": 13.0},
            "humidity": 60,
            "pressure": 1013,
            "wind_speed": 5.0,
            "wind_deg": 180,
            "uvi": 3.0,
            "clouds": 10,
            "rain": 0,
            "snow": 0,
            "weather": [{"main": "Clear", "description": "clear sky", "icon": "01d"}],
            "sunrise": 1700000000,
            "sunset": 1700040000,
        }
    ]
}


# ─── Health check ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app" in data


# ─── CREATE query ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.routers.weather.geocoding_service.resolve_location", new_callable=AsyncMock)
@patch("app.routers.weather.weather_service.get_current_weather", new_callable=AsyncMock)
@patch("app.routers.weather.weather_service.get_forecast", new_callable=AsyncMock)
async def test_create_weather_query(
    mock_forecast, mock_current, mock_geo, client
):
    mock_geo.return_value = MOCK_GEO
    mock_forecast.return_value = MOCK_FORECAST_RAW
    mock_current.return_value = MOCK_CURRENT_RAW

    payload = {
        "location": "New York",
        "date_from": str(date.today()),
        "date_to": str(date.today()),
        "label": "Test Query",
    }
    response = await client.post("/api/v1/weather/queries", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["location"]["resolved_name"] == "New York, New York, United States"
    assert data["label"] == "Test Query"
    assert "id" in data
    return data["id"]


# ─── Validation: invalid date range ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_query_invalid_date_range(client):
    payload = {
        "location": "London",
        "date_from": "2024-12-31",
        "date_to": "2024-01-01",  # before date_from
    }
    response = await client.post("/api/v1/weather/queries", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_create_query_date_range_too_long(client):
    payload = {
        "location": "Paris",
        "date_from": "2023-01-01",
        "date_to": "2024-06-01",  # > 365 days
    }
    response = await client.post("/api/v1/weather/queries", json=payload)
    assert response.status_code == 422


# ─── READ queries ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_weather_queries(client):
    response = await client.get("/api/v1/weather/queries")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_weather_query_not_found(client):
    response = await client.get("/api/v1/weather/queries/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# ─── UPDATE query ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.routers.weather.geocoding_service.resolve_location", new_callable=AsyncMock)
@patch("app.routers.weather.weather_service.get_current_weather", new_callable=AsyncMock)
@patch("app.routers.weather.weather_service.get_forecast", new_callable=AsyncMock)
async def test_update_weather_query(mock_forecast, mock_current, mock_geo, client):
    mock_geo.return_value = MOCK_GEO
    mock_forecast.return_value = MOCK_FORECAST_RAW
    mock_current.return_value = MOCK_CURRENT_RAW

    # Create first
    create_payload = {
        "location": "New York",
        "date_from": str(date.today()),
        "date_to": str(date.today()),
    }
    create_resp = await client.post("/api/v1/weather/queries", json=create_payload)
    assert create_resp.status_code == 201
    query_id = create_resp.json()["id"]

    # Update label
    update_resp = await client.patch(
        f"/api/v1/weather/queries/{query_id}",
        json={"label": "Updated Label", "notes": "Re-tagged for testing"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["label"] == "Updated Label"


# ─── DELETE query ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.routers.weather.geocoding_service.resolve_location", new_callable=AsyncMock)
@patch("app.routers.weather.weather_service.get_current_weather", new_callable=AsyncMock)
@patch("app.routers.weather.weather_service.get_forecast", new_callable=AsyncMock)
async def test_delete_weather_query(mock_forecast, mock_current, mock_geo, client):
    mock_geo.return_value = MOCK_GEO
    mock_forecast.return_value = MOCK_FORECAST_RAW
    mock_current.return_value = MOCK_CURRENT_RAW

    # Create first
    create_payload = {
        "location": "New York",
        "date_from": str(date.today()),
        "date_to": str(date.today()),
    }
    create_resp = await client.post("/api/v1/weather/queries", json=create_payload)
    assert create_resp.status_code == 201
    query_id = create_resp.json()["id"]

    # Delete
    delete_resp = await client.delete(f"/api/v1/weather/queries/{query_id}")
    assert delete_resp.status_code == 200
    assert "deleted" in delete_resp.json()["message"].lower()

    # Confirm gone
    get_resp = await client.get(f"/api/v1/weather/queries/{query_id}")
    assert get_resp.status_code == 404


# ─── Current weather endpoint ─────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.routers.weather.geocoding_service.resolve_location", new_callable=AsyncMock)
@patch("app.routers.weather.weather_service.get_current_weather", new_callable=AsyncMock)
async def test_get_current_weather(mock_current, mock_geo, client):
    mock_geo.return_value = MOCK_GEO
    mock_current.return_value = MOCK_CURRENT_RAW

    response = await client.post(
        "/api/v1/weather/current",
        json={"raw_input": "New York"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["temp_celsius"] == 15.0
    assert data["weather_main"] == "Clear"
    assert "location" in data


# ─── Validators unit tests ────────────────────────────────────────────────────

def test_gps_coordinate_detection():
    from app.utils.validators import is_gps_coordinates
    assert is_gps_coordinates("40.7128,-74.0060") == (40.7128, -74.006)
    assert is_gps_coordinates("48.8566, 2.3522") == (48.8566, 2.3522)
    assert is_gps_coordinates("New York") is None
    assert is_gps_coordinates("10001") is None


def test_zip_code_detection():
    from app.utils.validators import is_zip_code
    assert is_zip_code("10001") is True
    assert is_zip_code("10001-1234") is True
    assert is_zip_code("EC1A 1BB") is True
    assert is_zip_code("A1A 1A1") is True
    assert is_zip_code("New York") is False


def test_sanitize_location():
    from app.utils.validators import sanitize_location_input
    result = sanitize_location_input("  New York <script>  ")
    assert "<script>" not in result
    assert "New York" in result


# ─── Simple POST /weather endpoint ───────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.routers.weather.geocoding_service.resolve_location", new_callable=AsyncMock)
@patch("app.routers.weather.weather_service.get_current_weather", new_callable=AsyncMock)
async def test_simple_weather_lookup(mock_current, mock_geo, client):
    """Test the simple POST /weather endpoint (Nominatim + OpenWeather)."""
    mock_geo.return_value = MOCK_GEO_KOCHI
    mock_current.return_value = MOCK_CURRENT_RAW

    response = await client.post(
        "/api/v1/weather",
        json={"location": "Kochi"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    # Verify the response shape matches the spec
    assert data["location"] == "Kochi, Kerala, India"
    assert data["latitude"] == 9.9312
    assert data["longitude"] == 76.2673
    assert data["temperature"] == 15.0
    assert data["humidity"] == 60
    assert data["weather_description"] == "clear sky"


@pytest.mark.asyncio
@patch("app.routers.weather.geocoding_service.resolve_location", new_callable=AsyncMock)
@patch("app.routers.weather.weather_service.get_current_weather", new_callable=AsyncMock)
async def test_simple_weather_lookup_uses_cache(mock_current, mock_geo, client):
    """Second call to the same location should hit the DB cache and NOT call OpenWeather again."""
    mock_geo.return_value = MOCK_GEO_KOCHI
    mock_current.return_value = MOCK_CURRENT_RAW

    # First call – populates cache
    resp1 = await client.post("/api/v1/weather", json={"location": "Kochi"})
    assert resp1.status_code == 200

    # Second call – should use cache (mock_current should NOT be called again)
    mock_current.reset_mock()
    resp2 = await client.post("/api/v1/weather", json={"location": "Kochi"})
    assert resp2.status_code == 200
    assert resp2.json()["location"] == "Kochi, Kerala, India"
    # The weather API should NOT have been called for the cached request
    mock_current.assert_not_called()


@pytest.mark.asyncio
async def test_simple_weather_lookup_empty_location(client):
    """Empty location should fail validation."""
    response = await client.post("/api/v1/weather", json={"location": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("app.routers.weather.geocoding_service.resolve_location", new_callable=AsyncMock)
async def test_simple_weather_lookup_unknown_location(mock_geo, client):
    """When Nominatim can't find a location, the API should return 404."""
    from app.services.geocoding_service import GeocodingError
    mock_geo.side_effect = GeocodingError("Could not resolve location: 'xyznoplace'.")

    response = await client.post("/api/v1/weather", json={"location": "xyznoplace"})
    assert response.status_code == 404
    assert "resolve" in response.json()["detail"].lower()


@pytest.mark.asyncio
@patch("app.routers.weather.geocoding_service.resolve_location", new_callable=AsyncMock)
@patch("app.routers.weather.weather_service.get_current_weather", new_callable=AsyncMock)
async def test_simple_weather_rate_limit_handling(mock_current, mock_geo, client):
    """When OpenWeather returns 429, the endpoint should return a 429 with a message."""
    from app.services.weather_service import RateLimitError
    mock_geo.return_value = MOCK_GEO
    mock_current.side_effect = RateLimitError("Rate limit exceeded.")

    response = await client.post("/api/v1/weather", json={"location": "New York"})
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()
