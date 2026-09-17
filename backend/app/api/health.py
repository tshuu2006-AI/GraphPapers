"""Health check endpoints for backend service readiness and diagnostics."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Payload schema returned by the health check endpoint."""

    model_config = ConfigDict(extra="ignore")

    status: str = Field(default="ok", description="Overall health status string ('ok')")
    project: str = Field(description="Name of the backend project")
    version: str = Field(description="Current deployed version string")
    environment: str = Field(description="Runtime environment identifier")


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint to verify backend service readiness.

    Returns:
        HealthResponse instance containing status, project name, version, and environment.
    """
    return HealthResponse(
        status="ok",
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )
