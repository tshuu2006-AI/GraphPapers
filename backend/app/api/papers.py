from fastapi import APIRouter, HTTPException, Query, status

from app.models.paper import PaperDetails
from app.services.academic import AcademicService, AcademicServiceError, PaperNotFoundError

router = APIRouter(prefix="/papers", tags=["Papers"])


@router.get("", response_model=PaperDetails)
@router.get("/{doi:path}", response_model=PaperDetails)
async def get_paper(
    doi: str | None = None,
    doi_query: str | None = Query(default=None, alias="doi", description="DOI query parameter fallback"),
) -> PaperDetails:
    """Retrieve metadata and top 10 most-cited references for a paper by DOI."""
    target_doi = doi or doi_query
    if not target_doi:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid DOI must be provided either as a path parameter or 'doi' query parameter.",
        )

    service = AcademicService()
    try:
        return await service.get_paper_by_doi(target_doi)
    except PaperNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except AcademicServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
