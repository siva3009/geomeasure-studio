"""
GeoMeasure Studio — FastAPI Application
Main entry point with CORS, lifespan, and router registration.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import health, upload, files, measurements, api_keys, external_v1, assistant

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize DB on startup."""
    logger.info(f"Starting GeoMeasure Studio API (environment: {settings.environment})...")
    try:
        init_db()
        logger.info("Database schema verified and initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        if not settings.is_in_memory_allowed:
            logger.critical("Persistent database connection is REQUIRED in this environment. Startup aborted.")
            raise e
        logger.warning("Continuing in local/test environment with in-memory storage fallback enabled.")
    yield
    # Cleanup AI gateway HTTP client on shutdown
    try:
        from app.services.ai.gateway import ai_gateway
        await ai_gateway.aclose()
    except Exception:
        pass
    logger.info("Shutting down GeoMeasure Studio API.")


app = FastAPI(
    title="GeoMeasure Studio API",
    description=(
        "Geospatial file measurement API. Upload KML or zipped Shapefile "
        "files to extract geometry metadata and compute accurate measurements."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(files.router)
app.include_router(measurements.router)
app.include_router(api_keys.router)
app.include_router(external_v1.router)
app.include_router(assistant.router)


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "GeoMeasure Studio API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health/",
    }
