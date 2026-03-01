"""
WeatherVault – FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import init_db
from app.routers import weather, export, integrations
from app.services.weather_service import RateLimitError, weather_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup / shutdown tasks."""
    # ── Database init
    await init_db()

    # ── Validate OpenWeatherMap API key at startup so any issue is
    #    surfaced immediately in the server logs rather than on the
    #    first real user request.
    key_status = await weather_service.validate_api_key()
    if key_status["valid"]:
        logger.info(
            "[startup] OpenWeatherMap API key OK – key: %s  (%s)",
            key_status.get("masked_key", "****"),
            key_status.get("reason", ""),
        )
    else:
        logger.warning(
            "[startup] OpenWeatherMap API key issue – key: %s  reason: %s",
            key_status.get("masked_key", "(not set)"),
            key_status.get("reason", "unknown"),
        )

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-grade weather API with full CRUD persistence, "
        "OpenWeatherMap integration, Google Maps, YouTube, and data export."
    ),
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global error handlers ─────────────────────────────────────────────────────
@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={"error": "Database error", "detail": str(exc)},
    )


@app.exception_handler(RateLimitError)
async def rate_limit_exception_handler(request: Request, exc: RateLimitError):
    """Return a 429 with a user-friendly message when the weather API rate limit is hit."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": str(exc),
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "detail": str(exc)},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(weather.router, prefix=settings.API_PREFIX)
app.include_router(export.router, prefix=settings.API_PREFIX)
app.include_router(integrations.router, prefix=settings.API_PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get(f"{settings.API_PREFIX}/health", tags=["Health"])
async def health_check():
    """Liveness probe endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": f"{settings.API_PREFIX}/docs",
    }
