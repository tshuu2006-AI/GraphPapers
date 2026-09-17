"""Main API router combining all sub-routers under the /api prefix."""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.papers import router as papers_router
from app.api.routes import router as routes_router

api_router = APIRouter()

# Register health check at /health (under prefix /api, this becomes /api/health)
api_router.include_router(health_router)

# Register paper endpoints at /papers (under prefix /api, this becomes /api/papers)
api_router.include_router(papers_router)

# Register graph endpoint at /graph (under prefix /api, this becomes /api/graph)
api_router.include_router(routes_router)

__all__ = ["api_router"]
