"""Paper metadata retrieval endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.models.paper import PaperDetails
from app.services.academic import AcademicService, AcademicServiceError, PaperNotFoundError

router = APIRouter(prefix="/papers", tags=["Papers"])


@router.get("", response_model=PaperDetails)
@router.get("/{doi:path}", response_model=PaperDetails)
async def get_paper(
    doi: Optional[str] = None,
    doi_query: Optional[str] = Query(
        default=None,
        alias="doi",
        description="DOI query parameter fallback (e.g. 10.1038/s41586-020-2649-2)",
    ),
) -> PaperDetails:
    """Retrieve metadata and top 10 most-cited references for an academic paper by DOI.

    Accepts the DOI either as a path parameter (URL-encoded or raw) or as a `?doi=` query parameter.
    Enriches paper records with Open Access PDF links resolved concurrently via Unpaywall.

    Args:
        doi: Optional DOI string from the URL path.
        doi_query: Optional DOI string provided via query string.

    Returns:
        Validated PaperDetails instance with paper metadata and top references.

    Raises:
        HTTPException(400): If no valid DOI is supplied or empty string is passed.
        HTTPException(404): If paper is not found in OpenAlex.
        HTTPException(502): If upstream academic service APIs encounter an unrecoverable failure.
    """
    target_doi: Optional[str] = doi or doi_query
    if not target_doi or not target_doi.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid DOI must be provided either as a path parameter or 'doi' query parameter.",
        )

    service: AcademicService = AcademicService()
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
