from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.api.router import api_router
from app.api.v1.health import HealthCheckResponse, get_health
import app.models  # noqa: F401 - ensure all models are registered

# Ensure tables are registered if database is reachable
try:
    Base.metadata.create_all(bind=engine)
except Exception as err:
    import logging
    logging.getLogger(__name__).warning(f"Database table initialization skipped: {err}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Knowledge Intelligence & RAG Platform API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root level GET /health endpoint as specified in requirements
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check endpoint",
    tags=["Health"],
)
async def root_health(verbose: bool = False):
    return await get_health(verbose=verbose)


# Include API Routers under /api/v1
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "service": settings.SERVICE_NAME,
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
