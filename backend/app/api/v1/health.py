from typing import Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.database import SessionLocal
from app.services.vector_service import vector_service

router = APIRouter()


class HealthCheckResponse(BaseModel):
    status: str
    service: str
    database: Optional[str] = None
    qdrant: Optional[str] = None


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Service Health Check",
    description="Returns the health status of the Clario backend service, with optional database and vector store details.",
)
async def get_health(verbose: bool = False):
    db_status = None
    qdrant_status = None

    if verbose:
        # Check PostgreSQL
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception:
            db_status = "error"

        # Check Qdrant
        qdrant_status = "connected" if vector_service.check_health() else "disconnected"

    return HealthCheckResponse(
        status="healthy",
        service="clario-backend",
        database=db_status,
        qdrant=qdrant_status,
    )
