from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthCheckResponse(BaseModel):
    status: str
    service: str


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Service Health Check",
    description="Returns the health status of the Clario backend service.",
)
async def get_health():
    return HealthCheckResponse(
        status="healthy",
        service="clario-backend"
    )
