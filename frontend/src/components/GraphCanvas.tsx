import React, { useEffect, useRef, useCallback } from "react";
import cytoscape, { Core, EventObject, LayoutOptions } from "cytoscape";
import { GraphData, GraphNode } from "../types";

/**
 * Props for the {@link GraphCanvas} component.
 */
export interface GraphCanvasProps {
  /** Node-link graph dataset conforming to {@link GraphData} schema. */
  data: GraphData;
  /** Optional callback fired when an academic paper node is clicked or tapped. */
  onNodeClick?: (node: GraphNode) => void;
  /** Optional CSS class name for styling the canvas outer wrapper container. */
  className?: string;
  /** Optional inline styles applied to the canvas outer wrapper container. */
  style?: React.CSSProperties;
  /** Optional identifier of the node currently highlighted or selected across the application. */
  selectedNodeId?: string | null;
}

/**
 * Props for the floating zoom and fit canvas controls overlay.
 */
export interface CanvasControlsProps {
  /** Callback to increase zoom level. */
  onZoomIn: () => void;
  /** Callback to decrease zoom level. */
  onZoomOut: () => void;
  /** Callback to center and fit all elements in viewport. */
  onFit: () => void;
}

/**
 * Floating toolbar component providing interactive graph navigation controls.
 *
 * @param props - Component properties conforming to {@link CanvasControlsProps}.
 * @returns Rendered floating controls element.
 */
export const CanvasControls: React.FC<CanvasControlsProps> = ({
  onZoomIn,
  onZoomOut,
  onFit,
}): React.ReactElement => {
  return (
    <div
      className="absolute bottom-4 right-4 z-10 flex flex-col gap-1.5 bg-white/90 backdrop-blur border border-slate-200 shadow-md rounded-lg p-1.5 text-xs text-slate-700"
      role="toolbar"
      aria-label="Graph canvas navigation controls"
    >
      <button
        type="button"
        onClick={onZoomIn}
        title="Zoom In"
        aria-label="Zoom In"
        className="w-8 h-8 flex items-center justify-center font-bold hover:bg-slate-100 rounded transition-colors"
      >
        +
      </button>
      <button
        type="button"
        onClick={onZoomOut}
        title="Zoom Out"
        aria-label="Zoom Out"
        className="w-8 h-8 flex items-center justify-center font-bold hover:bg-slate-100 rounded transition-colors"
      >
        -
      </button>
      <button
        type="button"
        onClick={onFit}
        title="Fit Graph to View"
        aria-label="Fit Graph to View"
        className="w-8 h-8 flex items-center justify-center text-[10px] font-semibold hover:bg-slate-100 rounded transition-colors"
      >
        Fit
      </button>
    </div>
  );
};

/**
 * Props for the floating graph legend component.
 */
export interface GraphLegendProps {
  /** Optional custom class name for the legend container. */
  className?: string;
}

/**
 * Informational overlay displaying node color conventions and sizing criteria.
 *
 * @param props - Component properties conforming to {@link GraphLegendProps}.
 * @returns Rendered graph legend overlay element.
 */
export const GraphLegend: React.FC<GraphLegendProps> = ({
  className = "",
}): React.ReactElement => {
  return (
    <div
      className={`absolute top-4 left-4 z-10 bg-white/90 backdrop-blur border border-slate-200 shadow-sm rounded-lg px-3 py-2 text-xs text-slate-600 flex flex-col gap-1 ${className}`}
      aria-label="Citation graph legend"
    >
      <div className="flex items-center gap-2 font-medium text-slate-800 mb-0.5">
        <span>Citation Graph</span>
      </div>
      <div className="flex items-center gap-2">
        <span
          className="w-3 h-3 rounded-full bg-violet-600 border border-violet-900 inline-block"
          aria-hidden="true"
        />
        <span>Seed / Target Paper</span>
      </div>
      <div className="flex items-center gap-2">
        <span
          className="w-3 h-3 rounded-full bg-blue-500 border border-white inline-block"
          aria-hidden="true"
        />
        <span>Reference Paper</span>
      </div>
      <div className="flex items-center gap-2">
        <span
          className="w-3 h-3 rounded-full bg-blue-500 border-2 border-emerald-500 inline-block"
          aria-hidden="true"
        />
        <span>Open Access (PDF Available)</span>
      </div>
      <div className="text-[10px] text-slate-400 mt-1 italic">
        * Node diameter reflects citation count
      </div>
    </div>
  );
};

/**
 * Calculates a node size in pixels proportional to its citation count.
 * Uses bounded logarithmic scaling to cleanly display orders-of-magnitude differences.
 *
 * @param citationCount - Total number of citations received by the paper.
 * @param minCitation - Minimum citation count observed among dataset nodes.
 * @param maxCitation - Maximum citation count observed among dataset nodes.
 * @param minSize - Lower bound diameter in pixels for nodes with low citations. Default: 34.
 * @param maxSize - Upper bound diameter in pixels for nodes with high citations. Default: 80.
 * @returns Pixel diameter to assign to the Cytoscape node element.
 */
export function calculateNodeSize(
  citationCount: number,
  minCitation: number,
  maxCitation: number,
  minSize: number = 34,
  maxSize: number = 80
): number {
  if (maxCitation <= minCitation) {
    return Math.round((minSize + maxSize) / 2);
  }
  const norm =
    Math.log1p(Math.max(0, citationCount - minCitation)) /
    Math.log1p(Math.max(1, maxCitation - minCitation));

  return Math.round(minSize + norm * (maxSize - minSize));
}

/**
 * Truncates long scientific paper titles for on-canvas label rendering.
 *
 * @param label - Raw label or paper title string.
 * @param maxLength - Maximum allowable characters before appending ellipsis. Default: 26.
 * @returns Formatted and truncated label string.
 */
export function formatLabel(label: string, maxLength: number = 26): string {
  if (!label) return "Untitled";
  return label.length > maxLength ? `${label.slice(0, maxLength - 3)}...` : label;
}

/**
 * Interactive React graph component built with Cytoscape.js for rendering academic citation networks.
 *
 * Visualizes seed papers and their top-cited reference nodes using a physics-based CoSE layout,
 * dynamically sizing nodes proportionally to their citation impact and highlighting Open Access full-text availability.
 *
 * @param props - Component configuration properties conforming to {@link GraphCanvasProps}.
 * @returns Rendered graph visualization container element.
 *
 * @example
 * ```tsx
 * <GraphCanvas
 *   data={graphData}
 *   selectedNodeId={activePaperId}
 *   onNodeClick={(node) => handlePaperSelect(node)}
 * />
 * ```
 */
export const GraphCanvas: React.FC<GraphCanvasProps> = ({
  data,
  onNodeClick,
  className = "",
  style,
  selectedNodeId,
}): React.ReactElement => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);

  // Initialize and update Cytoscape instance when dataset or click handler changes
  useEffect(() => {
    if (!containerRef.current) return;

    // Determine citation bounds for dynamic proportional sizing
    const citationCounts: number[] = data.nodes.map((n: GraphNode) => n.citation_count || 0);
    const minCitation: number = citationCounts.length > 0 ? Math.min(...citationCounts) : 0;
    const maxCitation: number = citationCounts.length > 0 ? Math.max(...citationCounts) : 1;

    // Transform GraphData into Cytoscape element definitions
    const cytoscapeElements = [
      ...data.nodes.map((node: GraphNode) => ({
        group: "nodes" as const,
        data: {
          id: node.id,
          label: formatLabel(node.label || node.title),
          fullTitle: node.title,
          size: calculateNodeSize(node.citation_count, minCitation, maxCitation),
          isTarget: Boolean(node.is_target),
          isOA: Boolean(node.open_access?.is_oa || node.pdf_url),
          citationCount: node.citation_count,
          year: node.year,
          nodeRaw: node,
        },
      })),
      ...data.links.map((link, index: number) => ({
        group: "edges" as const,
        data: {
          id: `edge_${link.source}_${link.target}_${index}`,
          source: link.source,
          target: link.target,
          type: link.type || "cites",
        },
      })),
    ];

    // Destroy existing instance if container is reused
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    // Initialize Cytoscape core with custom style rules
    const cy: Core = cytoscape({
      container: containerRef.current,
      elements: cytoscapeElements,
      boxSelectionEnabled: false,
      autounselectify: false,
      wheelSensitivity: 0.3,
      style: [
        // Standard Reference Nodes
        {
          selector: "node",
          style: {
            width: "data(size)",
            height: "data(size)",
            label: "data(label)",
            "font-size": "11px",
            "font-family": "Inter, system-ui, -apple-system, sans-serif",
            color: "#334155",
            "text-valign": "bottom",
            "text-margin-y": 6,
            "text-max-width": "130px",
            "text-wrap": "ellipsis",
            "background-color": "#3b82f6",
            "border-width": 2,
            "border-color": "#ffffff",
            "overlay-padding": 4,
            "transition-property": "background-color, border-color, border-width, width, height",
            "transition-duration": 0.25,
          },
        },
        // Target Seed Paper Node
        {
          selector: "node[?isTarget]",
          style: {
            "background-color": "#7c3aed",
            "border-width": 4,
            "border-color": "#4c1d95",
            color: "#1e1b4b",
            "font-weight": "bold",
          },
        },
        // Open Access Nodes (indicates direct PDF accessibility)
        {
          selector: "node[?isOA]",
          style: {
            "border-color": "#10b981",
            "border-width": 3,
          },
        },
        // Target Paper + Open Access
        {
          selector: "node[?isTarget][?isOA]",
          style: {
            "border-color": "#10b981",
            "border-width": 4,
          },
        },
        // Active / Selected Node State
        {
          selector: "node:selected",
          style: {
            "border-color": "#f59e0b",
            "border-width": 5,
            "background-color": "#ea580c",
            color: "#0f172a",
            "font-weight": "bold",
          },
        },
        // Directed Citation Edges
        {
          selector: "edge",
          style: {
            width: 1.8,
            "line-color": "#cbd5e1",
            "target-arrow-color": "#94a3b8",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 1.1,
            opacity: 0.85,
          },
        },
        // Edge highlighting when incident node is selected
        {
          selector: "edge:selected",
          style: {
            width: 3,
            "line-color": "#f59e0b",
            "target-arrow-color": "#f59e0b",
            opacity: 1,
          },
        },
      ],
    });

    cyRef.current = cy;

    // Configure the CoSE (Compound Spring Embedder) physics layout
    const coseLayoutOptions: LayoutOptions = {
      name: "cose",
      animate: true,
      animationDuration: 750,
      refresh: 20,
      fit: true,
      padding: 60,
      randomize: false,
      componentSpacing: 120,
      nodeRepulsion: () => 450000,
      nodeOverlap: 25,
      idealEdgeLength: () => 110,
      edgeElasticity: () => 100,
      nestingFactor: 5,
      gravity: 80,
      numIter: 1000,
      initialTemp: 200,
      coolingFactor: 0.95,
      minTemp: 1.0,
    };

    const layout = cy.layout(coseLayoutOptions);
    layout.run();

    // Event listener: node click / tap
    cy.on("tap", "node", (evt: EventObject) => {
      const targetNode = evt.target;
      const rawData = targetNode.data("nodeRaw") as GraphNode;
      if (onNodeClick && rawData) {
        onNodeClick(rawData);
      }
    });

    // Cleanup on unmount or dependency change
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [data, onNodeClick]);

  // Synchronize externally controlled selectedNodeId without rerunning layout
  useEffect(() => {
    const cy: Core | null = cyRef.current;
    if (!cy) return;

    cy.nodes().unselect();
    if (selectedNodeId) {
      const match = cy.getElementById(selectedNodeId);
      if (match.length > 0) {
        match.select();
      }
    }
  }, [selectedNodeId]);

  /** Zoom into the viewport center by 25%. */
  const handleZoomIn: () => void = useCallback(() => {
    const cy: Core | null = cyRef.current;
    if (cy) cy.zoom(cy.zoom() * 1.25);
  }, []);

  /** Zoom out of the viewport center by 20%. */
  const handleZoomOut: () => void = useCallback(() => {
    const cy: Core | null = cyRef.current;
    if (cy) cy.zoom(cy.zoom() * 0.8);
  }, []);

  /** Fit entire graph layout into visible canvas bounds. */
  const handleFit: () => void = useCallback(() => {
    const cy: Core | null = cyRef.current;
    if (cy) cy.fit(undefined, 50);
  }, []);

  return (
    <div
      className={`relative w-full h-full min-h-[500px] bg-slate-50 overflow-hidden border border-slate-200 rounded-xl ${className}`}
      style={style}
    >
      {/* Cytoscape DOM container */}
      <div ref={containerRef} className="w-full h-full absolute inset-0" />

      {/* Floating Canvas Controls */}
      <CanvasControls
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onFit={handleFit}
      />

      {/* Graph Legend */}
      <GraphLegend />
    </div>
  );
};

export default GraphCanvas;
