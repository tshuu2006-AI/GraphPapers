"""Application entrypoint initializing FastAPI, middlewares, and route registrations."""

from typing import Any, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.router import api_router
from app.core.config import settings


def create_application() -> FastAPI:
    """Instantiate and configure the FastAPI application.

    Configures CORS middleware, registers health check and API v1 routers,
    and sets OpenAPI documentation endpoints.

    Returns:
        Configured FastAPI application instance.
    """
    application: FastAPI = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        debug=settings.DEBUG,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root health check endpoint (GET /health)
    application.include_router(health_router)

    # API endpoints prefixed with /api (GET /api/health, GET /api/papers, GET /api/graph, etc.)
    application.include_router(api_router, prefix=settings.API_V1_STR)

    @application.get("/", tags=["Root"])
    async def root() -> Dict[str, Any]:
        """Root welcome endpoint providing service status and documentation links.

        Returns:
            Dictionary containing welcome message, version, docs, and health URL.
        """
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "version": settings.VERSION,
            "docs": "/docs",
            "health": f"{settings.API_V1_STR}/health",
        }

    return application


app: FastAPI = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
