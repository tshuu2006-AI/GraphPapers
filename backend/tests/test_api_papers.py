import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from main import app
from app.models.paper import Author, OpenAccessInfo, PaperDetails, PaperReference

client = TestClient(app)


@pytest.fixture
def mock_paper_details():
    return PaperDetails(
        id="https://openalex.org/W3035965352",
        doi="10.1038/s41586-020-2649-2",
        title="Array programming with NumPy",
        publication_year=2020,
        publication_date="2020-09-16",
        cited_by_count=23755,
        abstract="Array programming with NumPy is standard in Python.",
        authors=[
            Author(name="Charles R. Harris", id="https://openalex.org/A1", institution="NumPy")
        ],
        venue="Nature",
        open_access=OpenAccessInfo(is_oa=True, oa_status="hybrid"),
        referenced_works_count=41,
        top_references=[
            PaperReference(
                id="https://openalex.org/W1",
                doi="10.1000/ref1",
                title="Matplotlib: A 2D Graphics Environment",
                publication_year=2007,
                cited_by_count=40985,
            )
        ],
    )


def test_get_paper_success(mock_paper_details):
    with patch(
        "app.api.papers.AcademicService.get_paper_by_doi",
        new=AsyncMock(return_value=mock_paper_details),
    ):
        response = client.get("/api/papers/10.1038/s41586-020-2649-2")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Array programming with NumPy"
        assert data["cited_by_count"] == 23755
        assert len(data["top_references"]) == 1
        assert data["top_references"][0]["title"] == "Matplotlib: A 2D Graphics Environment"


def test_get_paper_query_param(mock_paper_details):
    with patch(
        "app.api.papers.AcademicService.get_paper_by_doi",
        new=AsyncMock(return_value=mock_paper_details),
    ):
        response = client.get("/api/papers?doi=10.1038/s41586-020-2649-2")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Array programming with NumPy"


def test_get_paper_missing_doi():
    response = client.get("/api/papers")
    assert response.status_code == 400
