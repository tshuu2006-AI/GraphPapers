"""Domain schemas and data transfer objects for academic papers and citation networks.

Provides Pydantic models for papers, authors, Open Access licensing, and standard
node-link graph structures compatible with Cytoscape, D3, and NetworkX.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class Author(BaseModel):
    """Academic author entity containing identity and affiliation metadata."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(description="Full display name of the author")
    id: Optional[str] = Field(default=None, description="Unique author identifier (e.g. OpenAlex ID)")
    orcid: Optional[str] = Field(default=None, description="ORCID researcher identifier URI")
    institution: Optional[str] = Field(default=None, description="Primary institutional affiliation name")


class OpenAccessInfo(BaseModel):
    """Open Access status, licensing, and repository access metadata."""

    model_config = ConfigDict(extra="ignore")

    is_oa: bool = Field(default=False, description="Whether the paper is openly accessible")
    oa_status: Optional[str] = Field(default=None, description="OA category (gold, green, hybrid, bronze, closed)")
    oa_url: Optional[str] = Field(default=None, description="Canonical open access full-text URL")
    any_repository_has_fulltext: bool = Field(default=False, description="Whether an OA copy exists in any repository")
    license: Optional[str] = Field(default=None, description="Copyright license code (e.g. cc-by)")
    version: Optional[str] = Field(default=None, description="Manuscript version (e.g. publishedVersion)")


class PaperReference(BaseModel):
    """Compact model representing a referenced or citing academic paper."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="OpenAlex ID or canonical identifier (e.g., https://openalex.org/W...)")
    doi: Optional[str] = Field(default=None, description="DOI string or URL")
    title: str = Field(default="Untitled", description="Title of the paper")
    publication_year: Optional[int] = Field(default=None, description="Year published")
    cited_by_count: int = Field(default=0, description="Total citation count")
    authors: List[Author] = Field(default_factory=list, description="List of paper authors")
    venue: Optional[str] = Field(default=None, description="Journal, conference, or publisher venue")
    open_access: OpenAccessInfo = Field(default_factory=OpenAccessInfo, description="Open Access availability")
    pdf_url: Optional[str] = Field(default=None, description="Direct Open Access PDF URL if available")
    landing_page_url: Optional[str] = Field(default=None, description="Landing page URL for the paper")


class PaperDetails(BaseModel):
    """Detailed metadata of an academic paper along with its top references."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="OpenAlex ID or canonical identifier")
    doi: Optional[str] = Field(default=None, description="DOI string or URL")
    title: str = Field(default="Untitled", description="Title of the paper")
    publication_year: Optional[int] = Field(default=None, description="Year published")
    publication_date: Optional[str] = Field(default=None, description="Exact publication date (YYYY-MM-DD)")
    cited_by_count: int = Field(default=0, description="Total citations received")
    abstract: Optional[str] = Field(default=None, description="Abstract text of the paper")
    authors: List[Author] = Field(default_factory=list, description="List of authors")
    venue: Optional[str] = Field(default=None, description="Journal, conference, or publishing source")
    open_access: OpenAccessInfo = Field(default_factory=OpenAccessInfo, description="Open Access metadata")
    pdf_url: Optional[str] = Field(default=None, description="Direct link to full-text PDF if open access")
    landing_page_url: Optional[str] = Field(default=None, description="Publisher landing page")
    referenced_works_count: int = Field(default=0, description="Total count of references cited by this paper")
    top_references: List[PaperReference] = Field(
        default_factory=list,
        description="Top most-cited references cited by this paper (up to 10)",
    )

    @property
    def references(self) -> List[PaperReference]:
        """Convenience alias for top_references list."""
        return self.top_references


class GraphNode(BaseModel):
    """Represents an individual node in the citation graph."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="Unique node identifier (canonical OpenAlex ID or DOI)")
    label: str = Field(description="Short label or title for display")
    title: str = Field(description="Full paper title")
    doi: Optional[str] = Field(default=None, description="DOI string or URL")
    year: Optional[int] = Field(default=None, description="Publication year")
    citation_count: int = Field(default=0, description="Total citations received")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    venue: Optional[str] = Field(default=None, description="Publication venue or journal")
    is_target: bool = Field(default=False, description="True if this is the seed target paper")
    open_access: OpenAccessInfo = Field(default_factory=OpenAccessInfo, description="Open Access details")
    pdf_url: Optional[str] = Field(default=None, description="Direct link to Open Access PDF")
    landing_page_url: Optional[str] = Field(default=None, description="Publisher landing page")


class GraphEdge(BaseModel):
    """Represents a directed citation edge between two papers."""

    model_config = ConfigDict(extra="ignore")

    source: str = Field(description="Source paper identifier (citing paper)")
    target: str = Field(description="Target paper identifier (cited paper)")
    type: str = Field(default="cites", description="Relationship type (e.g., cites, references)")
    weight: float = Field(default=1.0, description="Edge weight for layout or graph algorithms")


class GraphData(BaseModel):
    """Standard node-link representation of the citation graph conforming to Cytoscape/D3/NetworkX specs."""

    model_config = ConfigDict(extra="ignore")

    nodes: List[GraphNode] = Field(default_factory=list, description="List of graph nodes (papers)")
    links: List[GraphEdge] = Field(default_factory=list, description="List of directed links between papers")
    target_id: Optional[str] = Field(default=None, description="Identifier of the target paper node")

    @property
    def edges(self) -> List[GraphEdge]:
        """Convenience alias for links."""
        return self.links

    @classmethod
    def from_paper_details(cls, paper: PaperDetails) -> GraphData:
        """Construct a standard node-link GraphData instance from a PaperDetails object.

        Args:
            paper: PaperDetails instance containing seed paper info and top references.

        Returns:
            GraphData instance with target and reference nodes plus directed citation links.
        """
        target_id: str = paper.id or paper.doi or "target"
        target_node = GraphNode(
            id=target_id,
            label=paper.title,
            title=paper.title,
            doi=paper.doi,
            year=paper.publication_year,
            citation_count=paper.cited_by_count,
            authors=[a.name for a in paper.authors],
            venue=paper.venue,
            is_target=True,
            open_access=paper.open_access,
            pdf_url=paper.pdf_url,
            landing_page_url=paper.landing_page_url,
        )

        nodes: List[GraphNode] = [target_node]
        links: List[GraphEdge] = []

        for ref in paper.top_references:
            ref_id: str = ref.id or ref.doi or f"ref_{len(nodes)}"
            ref_node = GraphNode(
                id=ref_id,
                label=ref.title,
                title=ref.title,
                doi=ref.doi,
                year=ref.publication_year,
                citation_count=ref.cited_by_count,
                authors=[a.name for a in ref.authors],
                venue=ref.venue,
                is_target=False,
                open_access=ref.open_access,
                pdf_url=ref.pdf_url,
                landing_page_url=ref.landing_page_url,
            )
            nodes.append(ref_node)
            links.append(
                GraphEdge(
                    source=target_id,
                    target=ref_id,
                    type="cites",
                    weight=1.0,
                )
            )

        return cls(nodes=nodes, links=links, target_id=target_id)
