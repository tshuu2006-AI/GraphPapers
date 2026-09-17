"""Service layer handling academic external data aggregation and processing."""

from app.services.academic import AcademicService, AcademicServiceError, PaperNotFoundError

__all__: list[str] = [
    "AcademicService",
    "AcademicServiceError",
    "PaperNotFoundError",
]
