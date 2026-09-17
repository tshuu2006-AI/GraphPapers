/**
 * Graph and paper domain types for Academic Citation Graph Visualizer.
 * @module types/graph
 */

/**
 * Open Access status, license, and repository full-text details for an academic work.
 */
export interface OpenAccessInfo {
  /** Indicates whether the publication is freely accessible via Open Access. */
  is_oa: boolean;
  /** Open Access classification status (e.g., 'gold', 'hybrid', 'green', 'bronze', 'closed'). */
  oa_status?: string | null;
  /** Canonical Open Access URL for full-text viewing or download. */
  oa_url?: string | null;
  /** Whether a full-text copy exists in any institutional or preprint repository. */
  any_repository_has_fulltext?: boolean;
  /** Copyright license associated with the document (e.g., 'cc-by', 'cc-by-nc'). */
  license?: string | null;
  /** Manuscript version available (e.g., 'publishedVersion', 'acceptedVersion'). */
  version?: string | null;
}

/**
 * Node entity in the citation graph representing an individual academic paper.
 */
export interface GraphNode {
  /** Canonical unique identifier (e.g., OpenAlex work ID 'https://openalex.org/W...' or DOI). */
  id: string;
  /** Abbreviated display label formatted for rendering inside or alongside graph nodes. */
  label: string;
  /** Complete title of the scientific article. */
  title: string;
  /** Digital Object Identifier (DOI) string if available. */
  doi?: string | null;
  /** Year the paper was published. */
  year?: number | null;
  /** Total count of citations received by this paper across academic databases. */
  citation_count: number;
  /** List of primary author names. */
  authors: string[];
  /** Journal, conference proceedings, or publisher source name. */
  venue?: string | null;
  /** Distinguishes whether this paper is the initial seed/target paper searched by the user. */
  is_target: boolean;
  /** Open Access metadata and licensing information. */
  open_access?: OpenAccessInfo;
  /** Direct link to the open-access PDF full text when resolved. */
  pdf_url?: string | null;
  /** Landing page on the publisher or repository website. */
  landing_page_url?: string | null;
}

/**
 * Directed citation edge connecting a citing paper to a cited paper.
 */
export interface GraphEdge {
  /** Identifier of the citing paper (origin/tail of the directed citation link). */
  source: string;
  /** Identifier of the cited paper (destination/arrowhead of the directed citation link). */
  target: string;
  /** Relationship type describing the edge connection (default: 'cites'). */
  type: string;
  /** Numeric weight or significance score assigned to the connection (e.g., for graph layouts). */
  weight?: number;
}

/**
 * Standard node-link citation graph dataset conforming to graph visualization libraries.
 */
export interface GraphData {
  /** Collection of academic paper nodes belonging to the citation graph. */
  nodes: GraphNode[];
  /** Collection of directed citation links between papers in the graph. */
  links: GraphEdge[];
  /** Identifier of the focal target paper from which references or citations originate. */
  target_id?: string | null;
}
