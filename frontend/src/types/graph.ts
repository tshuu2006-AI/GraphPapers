export interface OpenAccessInfo {
  is_oa: boolean;
  oa_status?: string | null;
  oa_url?: string | null;
  any_repository_has_fulltext?: boolean;
  license?: string | null;
  version?: string | null;
}

export interface GraphNode {
  id: string;
  label: string;
  title: string;
  doi?: string | null;
  year?: number | null;
  citation_count: number;
  authors: string[];
  venue?: string | null;
  is_target: boolean;
  open_access?: OpenAccessInfo;
  pdf_url?: string | null;
  landing_page_url?: string | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  weight?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphEdge[];
  target_id?: string | null;
}
