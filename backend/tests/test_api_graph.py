import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from main import app
from app.models.paper import Author, OpenAccessInfo, PaperDetails, PaperReference
from app.services.academic import AcademicServiceError, PaperNotFoundError

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
        abstract="Array programming with NumPy is fundamental.",
        authors=[
            Author(name="Charles R. Harris", id="https://openalex.org/A1", institution="NumPy")
        ],
        venue="Nature",
        open_access=OpenAccessInfo(
            is_oa=True,
            oa_status="hybrid",
            oa_url="https://nature.com/numpy.pdf",
            license="cc-by",
        ),
        pdf_url="https://nature.com/numpy.pdf",
        landing_page_url="https://doi.org/10.1038/s41586-020-2649-2",
        referenced_works_count=41,
        top_references=[
            PaperReference(
                id="https://openalex.org/W1",
                doi="10.1000/ref1",
                title="Matplotlib: A 2D Graphics Environment",
                publication_year=2007,
                cited_by_count=40985,
                authors=[Author(name="John D. Hunter")],
                venue="Computing in Science & Engineering",
                open_access=OpenAccessInfo(is_oa=True, oa_status="gold"),
                pdf_url="https://example.com/matplotlib.pdf",
                landing_page_url="https://doi.org/10.1000/ref1",
            ),
            PaperReference(
                id="https://openalex.org/W2",
                doi="10.1000/ref2",
                title="SciPy 1.0: Fundamental Algorithms",
                publication_year=2020,
                cited_by_count=39741,
                authors=[Author(name="Pauli Virtanen")],
                venue="Nature Methods",
                open_access=OpenAccessInfo(is_oa=False),
                pdf_url=None,
                landing_page_url="https://doi.org/10.1000/ref2",
            ),
        ],
    )


def test_get_graph_success(mock_paper_details):
    with patch(
        "app.api.routes.AcademicService.get_paper_by_doi",
        new=AsyncMock(return_value=mock_paper_details),
    ):
        response = client.get("/api/graph?doi=10.1038/s41586-020-2649-2")
        assert response.status_code == 200
        data = response.json()

        # Validate node-link structure
        assert "nodes" in data
        assert "links" in data
        assert "target_id" in data
        assert data["target_id"] == "https://openalex.org/W3035965352"

        # 1 target paper + 2 references = 3 nodes
        nodes = data["nodes"]
        assert len(nodes) == 3

        # Target node assertions
        target_node = next(n for n in nodes if n["is_target"] is True)
        assert target_node["id"] == "https://openalex.org/W3035965352"
        assert target_node["title"] == "Array programming with NumPy"
        assert target_node["citation_count"] == 23755
        assert target_node["open_access"]["is_oa"] is True
        assert target_node["pdf_url"] == "https://nature.com/numpy.pdf"
        assert "Charles R. Harris" in target_node["authors"]

        # Reference nodes assertions
        ref_nodes = [n for n in nodes if n["is_target"] is False]
        assert len(ref_nodes) == 2
        assert any(n["title"] == "Matplotlib: A 2D Graphics Environment" for n in ref_nodes)

        # Directed edges assertions: 2 edges from target to each reference
        links = data["links"]
        assert len(links) == 2
        for link in links:
            assert link["source"] == "https://openalex.org/W3035965352"
            assert link["type"] == "cites"
            assert link["target"] in ["https://openalex.org/W1", "https://openalex.org/W2"]


def test_get_graph_missing_doi():
    response = client.get("/api/graph")
    assert response.status_code == 422


def test_get_graph_empty_doi():
    response = client.get("/api/graph?doi=%20%20")
    assert response.status_code == 400


def test_get_graph_not_found():
    with patch(
        "app.api.routes.AcademicService.get_paper_by_doi",
        new=AsyncMock(side_effect=PaperNotFoundError("DOI not found")),
    ):
        response = client.get("/api/graph?doi=10.9999/not-exist")
        assert response.status_code == 404
        assert "DOI not found" in response.json()["detail"]


def test_get_graph_upstream_service_error():
    with patch(
        "app.api.routes.AcademicService.get_paper_by_doi",
        new=AsyncMock(side_effect=AcademicServiceError("Upstream API error")),
    ):
        response = client.get("/api/graph?doi=10.1038/s41586-020-2649-2")
        assert response.status_code == 502
        assert "Upstream API error" in response.json()["detail"]
