import pytest
import httpx
from app.services.academic import (
    AcademicService,
    PaperNotFoundError,
    normalize_doi,
    reconstruct_abstract,
    apply_unpaywall_data,
)
from app.models.paper import OpenAccessInfo, PaperDetails, PaperReference


def test_normalize_doi():
    assert normalize_doi("10.1038/s41586-020-2649-2") == "10.1038/s41586-020-2649-2"
    assert normalize_doi("https://doi.org/10.1038/s41586-020-2649-2") == "10.1038/s41586-020-2649-2"
    assert normalize_doi("http://dx.doi.org/10.1038/s41586-020-2649-2") == "10.1038/s41586-020-2649-2"
    assert normalize_doi("doi: 10.1038/s41586-020-2649-2 ") == "10.1038/s41586-020-2649-2"


def test_reconstruct_abstract():
    inverted_index = {
        "Array": [0],
        "programming": [1],
        "with": [2],
        "NumPy": [3],
        "is": [4],
        "powerful.": [5],
    }
    result = reconstruct_abstract(inverted_index)
    assert result == "Array programming with NumPy is powerful."
    assert reconstruct_abstract(None) is None


def test_apply_unpaywall_data():
    base_oa = OpenAccessInfo(is_oa=False)
    unpaywall_payload = {
        "is_oa": True,
        "oa_status": "gold",
        "best_oa_location": {
            "url_for_pdf": "https://example.com/paper.pdf",
            "url_for_landing_page": "https://example.com/paper",
            "url": "https://example.com/paper.pdf",
            "license": "cc-by",
            "version": "publishedVersion",
        },
        "has_repository_copy": True,
    }

    oa_info, pdf_url, landing = apply_unpaywall_data(
        oa_info=base_oa,
        current_pdf_url=None,
        current_landing_page="https://doi.org/10.1000/1",
        unpaywall_data=unpaywall_payload,
    )
    assert oa_info.is_oa is True
    assert oa_info.oa_status == "gold"
    assert oa_info.license == "cc-by"
    assert oa_info.version == "publishedVersion"
    assert pdf_url == "https://example.com/paper.pdf"
    assert landing == "https://example.com/paper"


@pytest.mark.asyncio
async def test_academic_service_mocked_with_unpaywall():
    sample_work = {
        "id": "https://openalex.org/W3035965352",
        "doi": "https://doi.org/10.1038/s41586-020-2649-2",
        "title": "Array programming with NumPy",
        "publication_year": 2020,
        "publication_date": "2020-09-16",
        "cited_by_count": 23000,
        "abstract_inverted_index": {"NumPy": [0], "paper": [1]},
        "authorships": [
            {
                "author": {"display_name": "Charles R. Harris", "id": "https://openalex.org/A1"},
                "institutions": [{"display_name": "NumPy Team"}],
            }
        ],
        "primary_location": {
            "source": {"display_name": "Nature"},
            "pdf_url": "https://nature.com/numpy.pdf",
            "landing_page_url": "https://nature.com/articles/numpy",
        },
        "open_access": {
            "is_oa": True,
            "oa_status": "hybrid",
            "oa_url": "https://nature.com/numpy.pdf",
        },
        "referenced_works": [
            "https://openalex.org/W1",
            "https://openalex.org/W2",
        ],
    }

    sample_references_result = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "doi": "https://doi.org/10.1000/ref1",
                "title": "Reference Paper 1",
                "publication_year": 2018,
                "cited_by_count": 5000,
                "authorships": [{"author": {"display_name": "Alice"}}],
                "primary_location": {"source": {"display_name": "Journal of Computing"}},
                "open_access": {"is_oa": False},
            },
            {
                "id": "https://openalex.org/W2",
                "doi": "https://doi.org/10.1000/ref2",
                "title": "Reference Paper 2",
                "publication_year": 2019,
                "cited_by_count": 8000,
                "authorships": [{"author": {"display_name": "Bob"}}],
                "primary_location": {"source": {"display_name": "Science"}},
                "open_access": {"is_oa": False},
            },
        ]
    }

    unpaywall_target = {
        "doi": "10.1038/s41586-020-2649-2",
        "is_oa": True,
        "oa_status": "gold",
        "best_oa_location": {
            "url_for_pdf": "https://unpaywall.org/target-better.pdf",
            "url_for_landing_page": "https://doi.org/10.1038/s41586-020-2649-2",
            "license": "cc-by",
        },
    }

    unpaywall_ref2 = {
        "doi": "10.1000/ref2",
        "is_oa": True,
        "oa_status": "green",
        "best_oa_location": {
            "url_for_pdf": "https://unpaywall.org/ref2-green.pdf",
            "url_for_landing_page": "https://doi.org/10.1000/ref2",
            "version": "acceptedVersion",
        },
    }

    unpaywall_called_urls = []

    async def mock_handler(request: httpx.Request):
        url = str(request.url)
        if "api.unpaywall.org" in url:
            unpaywall_called_urls.append(url)
            if "10.1038/s41586-020-2649-2" in url:
                return httpx.Response(200, json=unpaywall_target)
            elif "10.1000/ref2" in url:
                return httpx.Response(200, json=unpaywall_ref2)
            return httpx.Response(404, json={"message": "Not found in Unpaywall"})

        if "https://doi.org/10.1038/s41586-020-2649-2" in url:
            return httpx.Response(200, json=sample_work)
        elif "/works?filter=" in url or "/works" in url:
            return httpx.Response(200, json=sample_references_result)
        return httpx.Response(404, json={"message": "Not found"})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        service = AcademicService(client=client)
        paper = await service.get_paper_by_doi("10.1038/s41586-020-2649-2")

        assert isinstance(paper, PaperDetails)
        assert paper.title == "Array programming with NumPy"
        # Check Unpaywall enrichment on target paper
        assert paper.pdf_url == "https://unpaywall.org/target-better.pdf"
        assert paper.open_access.oa_status == "gold"
        assert paper.open_access.license == "cc-by"

        # References check
        assert len(paper.top_references) == 2
        # Ref 2 had highest citations (8000), was enriched with Unpaywall PDF
        ref_top = paper.top_references[0]
        assert ref_top.title == "Reference Paper 2"
        assert ref_top.pdf_url == "https://unpaywall.org/ref2-green.pdf"
        assert ref_top.open_access.is_oa is True
        assert ref_top.open_access.oa_status == "green"
        assert ref_top.open_access.version == "acceptedVersion"

        # Ref 1 was not found in Unpaywall, retains original non-OA
        ref_second = paper.top_references[1]
        assert ref_second.title == "Reference Paper 1"
        assert ref_second.pdf_url is None
        assert ref_second.open_access.is_oa is False

        # Verify Unpaywall was called for target paper AND references
        assert len(unpaywall_called_urls) == 3


@pytest.mark.asyncio
async def test_academic_service_not_found():
    async def mock_handler(request: httpx.Request):
        return httpx.Response(404, json={"message": "Not found"})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        service = AcademicService(client=client)
        with pytest.raises(PaperNotFoundError):
            await service.get_paper_by_doi("10.1000/invalid-doi-12345")
