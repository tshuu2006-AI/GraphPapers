from fastapi import APIRouter, HTTPException, Query, status

from app.models.paper import GraphData
from app.services.academic import AcademicService, AcademicServiceError, PaperNotFoundError

router = APIRouter(tags=["Graph"])


@router.get("/graph", response_model=GraphData, summary="Get Citation Graph")
@router.get("/api/graph", response_model=GraphData, include_in_schema=False)
async def get_graph(
    doi: str = Query(..., description="DOI of the target academic paper (e.g. 10.1038/s41586-020-2649-2)"),
) -> GraphData:
    """Accept a DOI query parameter, invoke AcademicService, and return a standard node-link JSON graph structure."""
    clean_doi = doi.strip()
    if not clean_doi:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The 'doi' query parameter must not be empty.",
        )

    service = AcademicService()
    try:
        paper_details = await service.get_paper_by_doi(clean_doi)
        return GraphData.from_paper_details(paper_details)
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
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while building citation graph: {exc}",
        ) from exc
