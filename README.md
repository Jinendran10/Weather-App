# WeatherVault

> **Production-grade weather intelligence platform** — Full CRUD persistence, real-time data, multi-API integration, and data export. Built with FastAPI, PostgreSQL, and React.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Features](#features)
5. [Database Schema](#database-schema)
6. [API Reference](#api-reference)
7. [Request & Response Examples](#request--response-examples)
8. [Error Handling](#error-handling)
9. [Environment Configuration](#environment-configuration)
10. [Getting Started](#getting-started)
11. [Docker Deployment](#docker-deployment)
12. [Running Tests](#running-tests)
13. [Project Structure](#project-structure)
14. [Scalability Considerations](#scalability-considerations)

---

## Overview

WeatherVault is a **full-stack SaaS-style weather application** demonstrating enterprise-level backend patterns:

- **RESTful API** with versioned endpoints (`/api/v1/`)
- **Full CRUD** with PostgreSQL persistence via async SQLAlchemy
- **Multi-provider geocoding** — resolves any location input (city names, ZIP codes, GPS coordinates, landmarks)
- **Third-party API integrations** — OpenWeatherMap, Google Maps Embed, YouTube Data API v3
- **Data export** — streaming CSV and JSON downloads
- **Input validation** — Pydantic v2 schemas with custom validators for date ranges and location sanitization
- **Structured error handling** — consistent JSON error payloads across all endpoints
- **React SPA frontend** — live weather dashboard, CRUD history interface, interactive Leaflet maps, Recharts visualizations

---

## Architecture

```
+------------------------------------------------------------------+
|                        CLIENT LAYER                              |
|   React SPA (Vite + Tailwind CSS)                                |
|   [ Home (Live) ]  [ History (CRUD) ]  [ QueryDetail (Charts) ] |
+---------------------------+--------------------------------------+
                            | HTTP/REST  /api/v1/*
+---------------------------v--------------------------------------+
|                        API LAYER                                 |
|   FastAPI (Python 3.12, Uvicorn ASGI)                           |
|   [ /weather CRUD ]  [ /export CSV/JSON ]  [ /integrations ]   |
|                                                                  |
|   SERVICE LAYER                                                  |
|   GeocodingService | OpenWeatherService | MapsService           |
|   YouTubeService   | Validators                                  |
+---------------------------+--------------------------------------+
                            | async SQLAlchemy ORM
+---------------------------v--------------------------------------+
|   PostgreSQL 16                                                  |
|   [ locations ] ---< [ weather_queries ] ---< [ weather_records]|
+------------------------------------------------------------------+
                            |
+---------------------------v--------------------------------------+
|   EXTERNAL SERVICES                                              |
|   [ OpenWeatherMap ]  [ Google Maps ]  [ YouTube Data API v3 ] |
+------------------------------------------------------------------+
```

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | FastAPI 0.115 | Async REST API framework |
| **Runtime** | Python 3.12 + Uvicorn | ASGI server |
| **ORM** | SQLAlchemy 2.0 (async) | Database abstraction |
| **Database** | PostgreSQL 16 | Primary data store |
| **Validation** | Pydantic v2 | Request/response schema enforcement |
| **HTTP Client** | HTTPX | Async external API calls |
| **Migrations** | Alembic | Schema version control |
| **Frontend** | React 18 + Vite | SPA with fast HMR |
| **Styling** | Tailwind CSS | Utility-first CSS framework |
| **Charts** | Recharts | Temperature and weather visualizations |
| **Maps** | React Leaflet | Interactive in-browser maps (OSM tiles) |
| **Routing** | React Router v6 | Client-side routing |
| **Containerization** | Docker + Docker Compose | Reproducible environments |
| **Testing** | pytest + pytest-asyncio | Async API test suite |

---

## Features

### CRUD Operations

| Operation | Endpoint | Description |
|---|---|---|
| **CREATE** | `POST /api/v1/weather/queries` | Geocode location, validate date range, fetch + persist weather |
| **READ (list)** | `GET /api/v1/weather/queries` | Paginated list with location search filter |
| **READ (detail)** | `GET /api/v1/weather/queries/{id}` | Full query with all daily records |
| **UPDATE** | `PATCH /api/v1/weather/queries/{id}` | Edit label, notes, or date range |
| **DELETE** | `DELETE /api/v1/weather/queries/{id}` | Cascade-delete query and records |
| **UPDATE record** | `PATCH /api/v1/weather/records/{id}` | Manually correct a daily record |
| **DELETE record** | `DELETE /api/v1/weather/records/{id}` | Remove a single daily record |

### Location Resolution

The system accepts **any** of the following location formats:

| Format | Example |
|---|---|
| City name | `New York`, `London`, `Tokyo` |
| City + country | `Paris, FR` |
| ZIP / Postal code | `10001`, `EC1A 1BB`, `A1A 1A1` |
| GPS coordinates | `40.7128,-74.0060`, `48.8566, 2.3522` |
| Landmark | `Eiffel Tower`, `Grand Canyon` |
| Full address | `1600 Pennsylvania Ave NW, Washington DC` |

### Data Export

- **CSV** — Flat tabular format, one row per daily record, suitable for Excel/Google Sheets
- **JSON** — Nested structure preserving query metadata and record hierarchy
- Both formats support filtering by `query_ids` or bulk export of all data
- Responses are streamed with `Content-Disposition` headers for direct browser download

### Integrations

| Integration | Endpoint | Notes |
|---|---|---|
| **Google Maps** | `GET /api/v1/integrations/maps/location?location=...` | Embed URL, static map URL, place details |
| **YouTube** | `GET /api/v1/integrations/youtube/location?location=...` | Top 6 travel/location videos |
| **Maps (query)** | `GET /api/v1/integrations/maps/query/{id}` | Map for a stored query location |
| **YouTube (query)** | `GET /api/v1/integrations/youtube/query/{id}` | Videos for a stored query location |

---

## Database Schema

### `locations`

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Primary key |
| `raw_input` | VARCHAR(500) | Original user-provided location string |
| `resolved_name` | VARCHAR(500) | Human-readable geocoded name |
| `country` | VARCHAR(100) | ISO country code |
| `state` | VARCHAR(100) | State/region |
| `city` | VARCHAR(200) | City name |
| `latitude` | FLOAT | Decimal degrees |
| `longitude` | FLOAT | Decimal degrees |
| `place_id` | VARCHAR(500) | Google Places ID |
| `created_at` | TIMESTAMPTZ | Auto-set on insert |
| `updated_at` | TIMESTAMPTZ | Auto-updated on change |

### `weather_queries`

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Primary key |
| `location_id` | UUID (FK) | -> locations, CASCADE delete |
| `date_from` | DATE | Start of requested range |
| `date_to` | DATE | End of requested range |
| `label` | VARCHAR(300) | Optional user label |
| `status` | ENUM | `pending`, `success`, `failed` |
| `notes` | TEXT | Free-form notes |
| `created_at` | TIMESTAMPTZ | Auto-set on insert |
| `updated_at` | TIMESTAMPTZ | Auto-updated on change |

### `weather_records`

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Primary key |
| `query_id` | UUID (FK) | -> weather_queries, CASCADE delete |
| `record_date` | DATE | The date this record represents |
| `temp_min` | FLOAT | Minimum temperature (C) |
| `temp_max` | FLOAT | Maximum temperature (C) |
| `temp_avg` | FLOAT | Average/daytime temperature (C) |
| `feels_like` | FLOAT | Perceived temperature (C) |
| `humidity` | INTEGER | Relative humidity % (0-100) |
| `pressure` | FLOAT | Atmospheric pressure hPa |
| `wind_speed` | FLOAT | Wind speed m/s |
| `wind_direction` | INTEGER | Wind direction degrees 0-360 |
| `visibility` | INTEGER | Visibility in meters |
| `uv_index` | FLOAT | UV index |
| `cloud_cover` | INTEGER | Cloud cover % (0-100) |
| `precipitation` | FLOAT | Rainfall mm |
| `snow` | FLOAT | Snowfall mm |
| `weather_main` | VARCHAR(100) | Main condition e.g. `Clear`, `Rain` |
| `weather_description` | VARCHAR(300) | Detailed description |
| `weather_icon` | VARCHAR(50) | OpenWeatherMap icon code |
| `sunrise` | TIMESTAMPTZ | Sunrise time |
| `sunset` | TIMESTAMPTZ | Sunset time |
| `raw_data` | TEXT | Full JSON payload from API |
| `created_at` | TIMESTAMPTZ | Auto-set on insert |
| `updated_at` | TIMESTAMPTZ | Auto-updated on change |

**Relationships:**
```
locations (1) --< weather_queries (1) --< weather_records
```

---

## API Reference

**Base URL:** `http://localhost:8000/api/v1`
**Interactive Docs:** `http://localhost:8000/api/v1/docs`

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `POST` | `/weather/current` | Live current weather (not persisted) |
| `POST` | `/weather/queries` | **CREATE** - New date-range query |
| `GET` | `/weather/queries` | **READ** - List all queries (paginated) |
| `GET` | `/weather/queries/{id}` | **READ** - Single query with records |
| `PATCH` | `/weather/queries/{id}` | **UPDATE** - Edit query metadata/dates |
| `DELETE` | `/weather/queries/{id}` | **DELETE** - Remove query + all records |
| `PATCH` | `/weather/records/{id}` | **UPDATE** - Correct a daily record |
| `DELETE` | `/weather/records/{id}` | **DELETE** - Remove a single record |
| `POST` | `/export` | Export data (CSV or JSON) |
| `GET` | `/integrations/maps/location` | Google Maps for any location |
| `GET` | `/integrations/maps/query/{id}` | Google Maps for stored query |
| `GET` | `/integrations/youtube/location` | YouTube videos for any location |
| `GET` | `/integrations/youtube/query/{id}` | YouTube videos for stored query |

---

## Request & Response Examples

### CREATE - New Weather Query

**Request:**
```http
POST /api/v1/weather/queries
Content-Type: application/json

{
  "location": "Tokyo, Japan",
  "date_from": "2024-07-01",
  "date_to": "2024-07-07",
  "label": "Summer Tokyo Trip",
  "notes": "Holiday planning research"
}
```

**Response `201 Created`:**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "location": {
    "resolved_name": "Tokyo, JP",
    "country": "JP",
    "latitude": 35.6762,
    "longitude": 139.6503
  },
  "date_from": "2024-07-01",
  "date_to": "2024-07-07",
  "label": "Summer Tokyo Trip",
  "status": "success",
  "weather_records": [
    {
      "record_date": "2024-07-01",
      "temp_min": 23.5,
      "temp_max": 31.2,
      "temp_avg": 28.0,
      "humidity": 78,
      "pressure": 1009.0,
      "wind_speed": 3.2,
      "weather_description": "scattered clouds"
    }
  ]
}
```

### EXPORT - Download CSV

**Request:**
```http
POST /api/v1/export
Content-Type: application/json

{
  "format": "csv",
  "include_records": true
}
```

**Response:** Binary CSV stream
`Content-Disposition: attachment; filename="weather_export_20240226T120000Z.csv"`

---

## Error Handling

All errors use a consistent JSON structure:

```json
{
  "error": "Validation error",
  "detail": "date_from must be on or before date_to.",
  "field": "date_range"
}
```

### HTTP Status Codes

| Code | Meaning |
|---|---|
| `200` | Success |
| `201` | Created |
| `404` | Not Found |
| `422` | Unprocessable Entity (validation failure) |
| `500` | Internal Server Error |
| `502` | Bad Gateway (external API unavailable) |

---

## Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | YES | PostgreSQL async connection string |
| `OPENWEATHER_API_KEY` | YES | Free at openweathermap.org/api |
| `GOOGLE_MAPS_API_KEY` | Optional | Maps Embed, Static Maps, Geocoding, Places. Falls back to OpenStreetMap |
| `YOUTUBE_API_KEY` | Optional | YouTube Data API v3. Falls back to mock data |
| `DEBUG` | Optional | Enables SQL logging. Default: false |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 (or Docker)

### Local Development

```bash
# 1. Clone & configure
git clone https://github.com/Jinendran10/Weather-App.git
cd Weather-App
cp .env.example .env
# Add your API keys to .env

# 2. Start PostgreSQL via Docker
docker run -d --name weathervault_db \
  -e POSTGRES_USER=weather_user \
  -e POSTGRES_PASSWORD=weather_pass \
  -e POSTGRES_DB=weatherdb \
  -p 5432:5432 postgres:16-alpine

# 3. Backend
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 4. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

- API: `http://localhost:8000/api/v1/docs`
- App: `http://localhost:3000`

---

## Docker Deployment

```bash
# Start all services
docker-compose up --build

# With pgAdmin4 on http://localhost:5050
docker-compose --profile dev up --build

# Stop
docker-compose down
```

| Service | URL |
|---|---|
| React App | `http://localhost:3000` |
| API Docs | `http://localhost:8000/api/v1/docs` |
| pgAdmin | `http://localhost:5050` |

---

## Running Tests

```bash
cd backend
source venv/bin/activate   # venv\Scripts\activate on Windows

# Full suite with coverage
pytest

# Specific file
pytest tests/test_weather.py -v

# HTML coverage report
pytest --cov=app --cov-report=html
```

Tests use **in-memory SQLite** and **mocked API calls** - no live credentials required.

### Test Coverage Areas

| Area | Test |
|---|---|
| Health check | `test_health_check` |
| CREATE + date validation | `test_create_weather_query`, `test_create_query_invalid_date_range` |
| READ / 404 | `test_list_weather_queries`, `test_get_weather_query_not_found` |
| UPDATE / DELETE | `test_update_weather_query`, `test_delete_weather_query` |
| Current weather | `test_get_current_weather` |
| YouTube / Maps | `test_youtube_for_location`, `test_maps_for_location` |
| Export validation | `test_export_empty_returns_404`, `test_export_invalid_format` |
| Input validators | GPS detection, ZIP detection, sanitizer |

---

## Project Structure

```
Weather-App/
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI app, middleware, error handlers
│   │   ├── config.py                 # Pydantic settings from environment
│   │   ├── database.py               # Async engine, session, Base
│   │   ├── models/weather.py         # ORM: Location, WeatherQuery, WeatherRecord
│   │   ├── schemas/weather.py        # Pydantic v2 schemas
│   │   ├── routers/
│   │   │   ├── weather.py            # CRUD endpoints
│   │   │   ├── export.py             # Streaming CSV/JSON export
│   │   │   └── integrations.py       # Maps + YouTube endpoints
│   │   ├── services/
│   │   │   ├── geocoding_service.py  # Multi-provider location resolution
│   │   │   ├── weather_service.py    # OpenWeatherMap API client
│   │   │   ├── maps_service.py       # Google Maps URL builder
│   │   │   └── youtube_service.py    # YouTube Data API v3 client
│   │   └── utils/validators.py       # GPS/ZIP detection, input sanitizer
│   ├── tests/
│   │   ├── conftest.py               # SQLite test DB + ASGI client fixtures
│   │   ├── test_weather.py           # CRUD + weather tests
│   │   └── test_integrations.py      # Integration + export tests
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── alembic.ini
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SearchBar.jsx         # Location input
│   │   │   ├── WeatherCard.jsx       # Weather data display
│   │   │   ├── WeatherHistory.jsx    # CRUD list
│   │   │   ├── DateRangeForm.jsx     # Query creation form
│   │   │   ├── MapView.jsx           # Leaflet map
│   │   │   ├── YouTubePanel.jsx      # YouTube video grid
│   │   │   └── ExportButtons.jsx     # CSV/JSON download
│   │   ├── pages/
│   │   │   ├── Home.jsx              # Live weather
│   │   │   ├── History.jsx           # CRUD management
│   │   │   └── QueryDetail.jsx       # Charts + table + map + videos
│   │   └── services/api.js           # Axios client
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Scalability Considerations

| Concern | Current | Production Path |
|---|---|---|
| **Connection pooling** | `pool_size=10` | PgBouncer / RDS Proxy |
| **Weather caching** | Fresh on each query | Redis TTL cache by `(lat, lon, date)` |
| **Rate limiting** | OWM plan limits | `slowapi` middleware per key |
| **Background tasks** | Sync in request | Celery + Redis for long fetches |
| **Location dedup** | 0.01 degree proximity | PostGIS `ST_DWithin` |
| **Auth** | Not required (per spec) | JWT + PostgreSQL row-level security |
| **Migrations** | `create_all` on startup | Alembic scripts for zero-downtime |
| **Observability** | Uvicorn logs | OpenTelemetry + Prometheus + Grafana |
| **Scaling** | Single process | Multiple Uvicorn workers behind nginx |

---

## License

MIT

---

*Built to demonstrate production-level API design, full CRUD persistence, external API integration, and clean full-stack architecture.*
