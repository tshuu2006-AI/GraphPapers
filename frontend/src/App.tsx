import React, { useState } from "react";
import { GraphCanvas } from "./components/GraphCanvas";
import { GraphData, GraphNode } from "./types";

/**
 * Sample mock citation dataset demonstrating seed paper and top references.
 */
const SAMPLE_GRAPH_DATA: GraphData = {
  target_id: "W3035965352",
  nodes: [
    {
      id: "W3035965352",
      label: "NumPy Array Programming",
      title: "Array programming with NumPy",
      doi: "10.1038/s41586-020-2649-2",
      year: 2020,
      citation_count: 23755,
      authors: ["Charles R. Harris", "K. Jarrod Millman", "Stéfan J. van der Walt"],
      venue: "Nature",
      is_target: true,
      open_access: {
        is_oa: true,
        oa_status: "hybrid",
        oa_url: "https://www.nature.com/articles/s41586-020-2649-2.pdf",
      },
      pdf_url: "https://www.nature.com/articles/s41586-020-2649-2.pdf",
      landing_page_url: "https://doi.org/10.1038/s41586-020-2649-2",
    },
    {
      id: "W2145620138",
      label: "Matplotlib 2D Graphics",
      title: "Matplotlib: A 2D Graphics Environment",
      doi: "10.1109/mcse.2007.55",
      year: 2007,
      citation_count: 40985,
      authors: ["John D. Hunter"],
      venue: "Computing in Science & Engineering",
      is_target: false,
      open_access: {
        is_oa: true,
        oa_status: "gold",
      },
      pdf_url: "https://doi.org/10.1109/mcse.2007.55",
    },
    {
      id: "W2995254148",
      label: "SciPy 1.0",
      title: "SciPy 1.0: Fundamental Algorithms for Scientific Computing in Python",
      doi: "10.1038/s41592-019-0686-2",
      year: 2020,
      citation_count: 39741,
      authors: ["Pauli Virtanen", "Ralf Gommers"],
      venue: "Nature Methods",
      is_target: false,
      open_access: {
        is_oa: true,
        oa_status: "gold",
      },
    },
    {
      id: "W2964177439",
      label: "PyTorch Framework",
      title: "PyTorch: An Imperative Style, High-Performance Deep Learning Library",
      doi: "10.5555/3454287.3455008",
      year: 2019,
      citation_count: 16139,
      authors: ["Adam Paszke", "Sam Gross"],
      venue: "NeurIPS",
      is_target: false,
      open_access: {
        is_oa: false,
      },
    },
  ],
  links: [
    { source: "W3035965352", target: "W2145620138", type: "cites", weight: 1.0 },
    { source: "W3035965352", target: "W2995254148", type: "cites", weight: 1.0 },
    { source: "W3035965352", target: "W2964177439", type: "cites", weight: 1.0 },
  ],
};

/**
 * Props for the application header bar.
 */
export interface AppHeaderProps {
  /** Currently selected paper node, or null if none is selected. */
  selectedNode: GraphNode | null;
}

/**
 * Top application navigation and selection header.
 *
 * @param props - Header props conforming to {@link AppHeaderProps}.
 * @returns Rendered header element.
 */
export const AppHeader: React.FC<AppHeaderProps> = ({
  selectedNode,
}): React.ReactElement => {
  return (
    <header className="px-6 py-4 bg-white border-b border-slate-200 shadow-sm flex items-center justify-between">
      <h1 className="text-xl font-bold text-slate-800">Academic Citation Graph Visualizer</h1>
      {selectedNode && (
        <div className="text-sm text-slate-600">
          Selected: <span className="font-semibold text-slate-900">{selectedNode.title}</span> (
          {selectedNode.citation_count.toLocaleString()} citations)
        </div>
      )}
    </header>
  );
};

/**
 * Main application root component hosting the citation graph visualizer interface.
 *
 * @returns Root application React component element.
 */
export const App: React.FC = (): React.ReactElement => {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  /** Handler invoked when user selects a paper node on the canvas */
  const handleNodeSelect = (node: GraphNode): void => {
    setSelectedNode(node);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-100 font-sans">
      <AppHeader selectedNode={selectedNode} />

      <main className="flex-1 p-4 relative">
        <GraphCanvas
          data={SAMPLE_GRAPH_DATA}
          selectedNodeId={selectedNode?.id}
          onNodeClick={handleNodeSelect}
          className="w-full h-full shadow-sm"
        />
      </main>
    </div>
  );
};

export default App;
