from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import settings
from app.models.paper import Author, OpenAccessInfo, PaperDetails, PaperReference

logger = logging.getLogger(__name__)


class AcademicServiceError(Exception):
    """Base exception for academic service errors."""


class PaperNotFoundError(AcademicServiceError):
    """Raised when a paper cannot be found by its DOI or identifier."""


def normalize_doi(doi: str) -> str:
    """Normalize DOI string by stripping URLs and 'doi:' prefixes."""
    clean = doi.strip()
    clean = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^doi:\s*", "", clean, flags=re.IGNORECASE)
    return clean.strip()


def reconstruct_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> Optional[str]:
    """Reconstruct plain-text abstract from OpenAlex inverted index representation."""
    if not inverted_index:
        return None

    word_positions: List[Tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))

    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


def extract_authors(authorships: Optional[List[Dict[str, Any]]]) -> List[Author]:
    """Extract list of authors from OpenAlex authorships structure."""
    if not authorships:
        return []

    authors: List[Author] = []
    for item in authorships:
        author_data = item.get("author") or {}
        name = author_data.get("display_name")
        if not name:
            continue

        institutions = item.get("institutions") or []
        first_institution = institutions[0].get("display_name") if institutions else None

        authors.append(
            Author(
                name=name,
                id=author_data.get("id"),
                orcid=author_data.get("orcid"),
                institution=first_institution,
            )
        )
    return authors


def extract_open_access_and_pdf(work: Dict[str, Any]) -> Tuple[OpenAccessInfo, Optional[str], Optional[str]]:
    """Extract Open Access metadata, direct PDF URL, and landing page URL from OpenAlex work."""
    oa_data = work.get("open_access") or {}
    primary_loc = work.get("primary_location") or {}
    source = primary_loc.get("source") or {}

    oa_info = OpenAccessInfo(
        is_oa=bool(oa_data.get("is_oa")),
        oa_status=oa_data.get("oa_status"),
        oa_url=oa_data.get("oa_url"),
        any_repository_has_fulltext=bool(oa_data.get("any_repository_has_fulltext")),
    )

    pdf_url = primary_loc.get("pdf_url") or oa_info.oa_url
    landing_page_url = primary_loc.get("landing_page_url") or work.get("doi")

    return oa_info, pdf_url, landing_page_url


def parse_work_to_reference(work: Dict[str, Any]) -> PaperReference:
    """Parse raw OpenAlex work dictionary into PaperReference model."""
    oa_info, pdf_url, landing_page_url = extract_open_access_and_pdf(work)
    primary_loc = work.get("primary_location") or {}
    source = primary_loc.get("source") or {}
    venue = source.get("display_name")

    return PaperReference(
        id=work.get("id") or "",
        doi=work.get("doi"),
        title=work.get("title") or work.get("display_name") or "Untitled",
        publication_year=work.get("publication_year"),
        cited_by_count=work.get("cited_by_count") or 0,
        authors=extract_authors(work.get("authorships")),
        venue=venue,
        open_access=oa_info,
        pdf_url=pdf_url,
        landing_page_url=landing_page_url,
    )


def apply_unpaywall_data(
    oa_info: OpenAccessInfo,
    current_pdf_url: Optional[str],
    current_landing_page: Optional[str],
    unpaywall_data: Optional[Dict[str, Any]],
) -> Tuple[OpenAccessInfo, Optional[str], Optional[str]]:
    """Enrich or override Open Access metadata and PDF URL with Unpaywall results."""
    if not unpaywall_data:
        return oa_info, current_pdf_url, current_landing_page

    is_oa = bool(unpaywall_data.get("is_oa", oa_info.is_oa))
    oa_status = unpaywall_data.get("oa_status") or oa_info.oa_status
    best_loc = unpaywall_data.get("best_oa_location") or {}

    pdf_url = best_loc.get("url_for_pdf") or current_pdf_url
    oa_url = best_loc.get("url") or pdf_url or oa_info.oa_url
    landing_page = (
        best_loc.get("url_for_landing_page")
        or unpaywall_data.get("doi_url")
        or current_landing_page
    )
    has_repo = bool(unpaywall_data.get("has_repository_copy", oa_info.any_repository_has_fulltext))
    license_type = best_loc.get("license") or oa_info.license
    version = best_loc.get("version") or oa_info.version

    enriched_oa = OpenAccessInfo(
        is_oa=is_oa,
        oa_status=oa_status,
        oa_url=oa_url,
        any_repository_has_fulltext=has_repo,
        license=license_type,
        version=version,
    )
    return enriched_oa, pdf_url, landing_page


class AcademicService:
    """Service to interact with academic APIs, specifically OpenAlex and Unpaywall."""

    OPENALEX_BASE_URL = "https://api.openalex.org"
    UNPAYWALL_BASE_URL = "https://api.unpaywall.org/v2"

    def __init__(self, client: Optional[httpx.AsyncClient] = None, timeout: float = 15.0):
        self._client = client
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        user_agent = f"{settings.PROJECT_NAME}/{settings.VERSION}"
        if settings.OPENALEX_EMAIL:
            user_agent += f" (mailto:{settings.OPENALEX_EMAIL})"
        return {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }

    def _get_openalex_params(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if settings.OPENALEX_EMAIL:
            params["mailto"] = settings.OPENALEX_EMAIL
        if extra:
            params.update(extra)
        return params

    def _get_unpaywall_email(self) -> str:
        return settings.UNPAYWALL_EMAIL or settings.OPENALEX_EMAIL or "graphpapers.academic.app@gmail.com"

    async def _fetch_openalex(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform an HTTP GET request against the OpenAlex API."""
        try:
            response = await client.get(
                url,
                params=self._get_openalex_params(params),
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            if response.status_code == 404:
                raise PaperNotFoundError(f"Resource not found at {url}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise PaperNotFoundError(f"Resource not found: {exc}") from exc
            raise AcademicServiceError(f"HTTP error {exc.response.status_code} from OpenAlex: {exc}") from exc
        except httpx.RequestError as exc:
            raise AcademicServiceError(f"Network error connecting to OpenAlex: {exc}") from exc

    async def fetch_unpaywall_oa(
        self,
        client: httpx.AsyncClient,
        doi: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Query the Unpaywall API for Open Access PDF link and metadata for a DOI."""
        if not doi:
            return None

        cleaned_doi = normalize_doi(doi)
        if not cleaned_doi:
            return None

        url = f"{self.UNPAYWALL_BASE_URL}/{cleaned_doi}"
        params = {"email": self._get_unpaywall_email()}

        try:
            response = await client.get(
                url,
                params=params,
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code != 404:
                logger.warning(
                    "Unpaywall returned status %d for DOI %s: %s",
                    response.status_code,
                    cleaned_doi,
                    response.text,
                )
            return None
        except Exception as exc:
            logger.debug("Failed to fetch Unpaywall info for DOI %s: %s", cleaned_doi, exc)
            return None

    async def get_top_references(
        self,
        referenced_works: List[str],
        limit: int = 10,
        client: Optional[httpx.AsyncClient] = None,
    ) -> List[PaperReference]:
        """Fetch the top most-cited papers from a list of OpenAlex work IDs."""
        if not referenced_works or limit <= 0:
            return []

        # Extract clean OpenAlex IDs (e.g., 'W3035965352' from 'https://openalex.org/W3035965352')
        clean_ids = [ref.split("/")[-1] for ref in referenced_works if ref]
        if not clean_ids:
            return []

        # OpenAlex allows combining IDs with '|' up to 50 items per query
        chunk_size = 50
        chunks = [clean_ids[i : i + chunk_size] for i in range(0, len(clean_ids), chunk_size)]

        async def fetch_chunk(c: httpx.AsyncClient, chunk_ids: List[str]) -> List[Dict[str, Any]]:
            filter_query = "|".join(chunk_ids)
            url = f"{self.OPENALEX_BASE_URL}/works"
            params = {
                "filter": f"openalex_id:{filter_query}",
                "sort": "cited_by_count:desc",
                "per_page": min(limit, len(chunk_ids)),
            }
            try:
                res = await self._fetch_openalex(c, url, params=params)
                return res.get("results", [])
            except Exception:
                return []

        active_client = client or self._client
        if active_client:
            tasks = [fetch_chunk(active_client, chunk) for chunk in chunks]
            results_nested = await asyncio.gather(*tasks)
        else:
            async with httpx.AsyncClient() as new_client:
                tasks = [fetch_chunk(new_client, chunk) for chunk in chunks]
                results_nested = await asyncio.gather(*tasks)

        all_candidates: List[Dict[str, Any]] = [item for sublist in results_nested for item in sublist]

        # Deduplicate candidates by OpenAlex ID in case of overlaps
        seen_ids = set()
        deduped: List[Dict[str, Any]] = []
        for item in all_candidates:
            item_id = item.get("id")
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                deduped.append(item)

        # Sort descending by citation count and take top `limit`
        deduped.sort(key=lambda x: x.get("cited_by_count") or 0, reverse=True)
        top_slice = deduped[:limit]

        return [parse_work_to_reference(work) for work in top_slice]

    async def get_paper_by_doi(self, doi: str) -> PaperDetails:
        """Retrieve paper metadata and top 10 most-cited references, enriching OA PDF links via Unpaywall."""
        cleaned_doi = normalize_doi(doi)
        if not cleaned_doi:
            raise ValueError("DOI must not be empty.")

        work_url = f"{self.OPENALEX_BASE_URL}/works/https://doi.org/{cleaned_doi}"

        if self._client:
            return await self._process_paper(self._client, work_url, cleaned_doi)
        else:
            async with httpx.AsyncClient() as client:
                return await self._process_paper(client, work_url, cleaned_doi)

    async def _process_paper(
        self,
        client: httpx.AsyncClient,
        work_url: str,
        cleaned_doi: str,
    ) -> PaperDetails:
        """Internal helper to fetch OpenAlex metadata, top references, and Unpaywall OA concurrently."""
        # 1. Fetch main paper metadata from OpenAlex
        work_data = await self._fetch_openalex(client, work_url)
        referenced_works = work_data.get("referenced_works") or []

        # 2. Fetch top 10 most-cited references from OpenAlex
        top_references = await self.get_top_references(
            referenced_works=referenced_works,
            limit=10,
            client=client,
        )

        # 3. Check for Open Access PDFs concurrently using Unpaywall API via asyncio.gather
        #    Dispatch calls for both target paper and each reference node
        unpaywall_tasks = [
            self.fetch_unpaywall_oa(client, cleaned_doi),
            *(self.fetch_unpaywall_oa(client, ref.doi) for ref in top_references),
        ]
        unpaywall_results = await asyncio.gather(*unpaywall_tasks, return_exceptions=True)

        target_unpaywall = (
            unpaywall_results[0]
            if unpaywall_results and not isinstance(unpaywall_results[0], Exception)
            else None
        )
        references_unpaywall = [
            res if not isinstance(res, Exception) else None
            for res in unpaywall_results[1:]
        ]

        # 4. Enrich target paper OA data with Unpaywall info
        oa_info, pdf_url, landing_page_url = extract_open_access_and_pdf(work_data)
        oa_info, pdf_url, landing_page_url = apply_unpaywall_data(
            oa_info=oa_info,
            current_pdf_url=pdf_url,
            current_landing_page=landing_page_url,
            unpaywall_data=target_unpaywall,
        )

        # 5. Enrich each reference with its Unpaywall OA data
        enriched_references: List[PaperReference] = []
        for ref, ref_unpaywall in zip(top_references, references_unpaywall):
            ref_oa, ref_pdf, ref_landing = apply_unpaywall_data(
                oa_info=ref.open_access,
                current_pdf_url=ref.pdf_url,
                current_landing_page=ref.landing_page_url,
                unpaywall_data=ref_unpaywall,
            )
            enriched_ref = ref.model_copy(
                update={
                    "open_access": ref_oa,
                    "pdf_url": ref_pdf,
                    "landing_page_url": ref_landing,
                }
            )
            enriched_references.append(enriched_ref)

        primary_loc = work_data.get("primary_location") or {}
        source = primary_loc.get("source") or {}
        venue = source.get("display_name")

        return PaperDetails(
            id=work_data.get("id") or "",
            doi=work_data.get("doi") or cleaned_doi,
            title=work_data.get("title") or work_data.get("display_name") or "Untitled",
            publication_year=work_data.get("publication_year"),
            publication_date=work_data.get("publication_date"),
            cited_by_count=work_data.get("cited_by_count") or 0,
            abstract=reconstruct_abstract(work_data.get("abstract_inverted_index")),
            authors=extract_authors(work_data.get("authorships")),
            venue=venue,
            open_access=oa_info,
            pdf_url=pdf_url,
            landing_page_url=landing_page_url,
            referenced_works_count=len(referenced_works),
            top_references=enriched_references,
        )
