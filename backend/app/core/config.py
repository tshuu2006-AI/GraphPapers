"""Application configuration and environment settings for Academic Citation Graph Visualizer.

Uses pydantic-settings to load configuration from environment variables and .env files.
"""

from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings and environment variable bindings."""

    PROJECT_NAME: str = Field(
        default="Academic Citation Graph Visualizer",
        description="Public display name of the application",
    )
    VERSION: str = Field(
        default="0.1.0",
        description="Application semantic version",
    )
    API_V1_STR: str = Field(
        default="/api",
        description="Global prefix for version 1 API endpoints",
    )
    ENVIRONMENT: str = Field(
        default="development",
        description="Runtime environment (development, staging, production)",
    )
    DEBUG: bool = Field(
        default=True,
        description="Flag enabling FastAPI debug mode and auto-reload",
    )

    # CORS configuration
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        description="List of allowed CORS origins for browser cross-origin requests",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse comma-separated string or list into a validated list of origins.

        Args:
            v: Raw value from environment variable or default configuration.

        Returns:
            List of origin URL strings.
        """
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Third-Party External APIs
    SEMANTIC_SCHOLAR_API_KEY: Optional[str] = Field(
        default=None,
        description="Optional API key for Semantic Scholar graph access",
    )
    OPENALEX_EMAIL: Optional[str] = Field(
        default=None,
        description="Contact email address sent in OpenAlex polite pool requests",
    )
    UNPAYWALL_EMAIL: str = Field(
        default="graphpapers.academic.app@gmail.com",
        description="Email address required by the Unpaywall API v2",
    )

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings: Settings = Settings()
