"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Network, RefreshCw, Info, X, Layers, Box, Square } from "lucide-react";
import { getGraphData, GraphNode, GraphData } from "@/lib/api";
import { Button } from "@/components/ui/button";
import dynamic from "next/dynamic";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });
const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), { ssr: false });

const NODE_COLORS: Record<string, string> = {
  Decision: "#06b6d4",   // accent (cyan)
  Person: "#10b981",     // success (green)
  Reason: "#f59e0b",     // warning (amber)
  Alternative: "#8b5cf6", // accent-2 (violet)
};

const LEGEND = [
  { type: "Decision", color: "#06b6d4" },
  { type: "Person", color: "#10b981" },
  { type: "Reason", color: "#f59e0b" },
  { type: "Alternative", color: "#8b5cf6" },
];

export default function GraphPage() {
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; links: { source: string; target: string; label: string }[] }>({ nodes: [], links: [] });
  const [fullData, setFullData] = useState<{ nodes: GraphNode[]; links: { source: string; target: string; label: string }[] }>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [sources, setSources] = useState<string[]>([]);
  const [selectedSource, setSelectedSource] = useState<string>("all");
  const [graphKey, setGraphKey] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const [is3D, setIs3D] = useState(false);
  const [highlightNodes, setHighlightNodes] = useState(new Set<string>());
  const [highlightLinks, setHighlightLinks] = useState(new Set<string>());

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data: GraphData = await getGraphData();
      const processedData = {
        nodes: data.nodes.map((n) => ({ ...n, color: NODE_COLORS[n.type] ?? "#64748b" })),
        links: data.edges.map((e) => ({ source: e.source, target: e.target, label: e.type })),
      };
      setFullData(processedData);
      setGraphData(processedData);

      const allSources = data.nodes.map((n) => n.source).filter((s): s is string => !!s && s !== "");
      setSources(Array.from(new Set(allSources)));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load graph");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const clearSelection = useCallback(() => {
    setSelected(null);
    setHighlightNodes(new Set());
    setHighlightLinks(new Set());
  }, []);

  useEffect(() => {
    if (selectedSource === "all") {
      setGraphData(fullData);
    } else {
      const filteredNodes = fullData.nodes.filter((n) => n.source === selectedSource);
      const nodeIds = new Set(filteredNodes.map((n) => n.id));
      const filteredLinks = fullData.links.filter((l) => {
        const sourceId = typeof l.source === "string" ? l.source : (l.source as GraphNode)?.id;
        const targetId = typeof l.target === "string" ? l.target : (l.target as GraphNode)?.id;
        return nodeIds.has(sourceId) && nodeIds.has(targetId);
      });
      setGraphData({ nodes: filteredNodes, links: filteredLinks });
    }
    setGraphKey((prev) => prev + 1);
    clearSelection();
  }, [selectedSource, fullData, clearSelection]);

  useEffect(() => {
    const update = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelected(node);
    
    // Find all links connecting to this node
    const connectedLinks = new Set<string>();
    const connectedNodes = new Set<string>();
    connectedNodes.add(node.id);
    
    // Using fullData to trace even if not filtered, but we highlight within current view
    graphData.links.forEach((link: any) => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source?.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target?.id;
      
      if (sourceId === node.id || targetId === node.id) {
        connectedLinks.add(`${sourceId}-${targetId}`);
        connectedNodes.add(sourceId);
        connectedNodes.add(targetId);
      }
    });
    
    setHighlightNodes(connectedNodes);
    setHighlightLinks(connectedLinks);
  }, [graphData]);


  const paintNode = useCallback((node: GraphNode & { x?: number; y?: number; color?: string }, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const isSelected = selected?.id === node.id;
    const isHighlighted = highlightNodes.size > 0 ? highlightNodes.has(node.id) : true;
    const isDimmed = highlightNodes.size > 0 && !isHighlighted;

    const x = node.x ?? 0;
    const y = node.y ?? 0;
    const r = node.type === "Decision" ? 8 : 5;

    // Glow effect
    if (!isDimmed) {
        ctx.shadowColor = node.color ?? "#06b6d4";
        ctx.shadowBlur = 12;
    }
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fillStyle = isDimmed ? "rgba(100, 116, 139, 0.2)" : (node.color ?? "#64748b");
    ctx.fill();
    ctx.shadowBlur = 0;

    if (!isDimmed) {
        ctx.strokeStyle = isSelected ? "#fff" : "rgba(255,255,255,0.4)";
        ctx.lineWidth = isSelected ? 2 : 1.5;
        ctx.stroke();
    }

    if (!isDimmed || isSelected) {
        const fontSize = node.type === "Decision" ? 12 : 10;
        ctx.font = `${fontSize / globalScale}px Inter, sans-serif`;
        ctx.fillStyle = isSelected ? "#fff" : "rgba(248,250,252,0.9)";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        const label = node.label || node.id || "";
        const maxLen = node.type === "Decision" ? 40 : 30;
        const displayLabel = label.length > maxLen ? label.slice(0, maxLen) + "…" : label;
        ctx.fillText(displayLabel, x, y + r + 12 / globalScale);
    }
  }, [selected, highlightNodes]);

  const linkColor = useCallback((link: any) => {
    if (highlightLinks.size === 0) return "rgba(148,163,184,0.4)";
    const sourceId = typeof link.source === 'string' ? link.source : link.source?.id;
    const targetId = typeof link.target === 'string' ? link.target : link.target?.id;
    const linkId = `${sourceId}-${targetId}`;
    return highlightLinks.has(linkId) ? "#06b6d4" : "rgba(148,163,184,0.1)";
  }, [highlightLinks]);

  const linkWidth = useCallback((link: any) => {
    if (highlightLinks.size === 0) return 2;
    const sourceId = typeof link.source === 'string' ? link.source : link.source?.id;
    const targetId = typeof link.target === 'string' ? link.target : link.target?.id;
    const linkId = `${sourceId}-${targetId}`;
    return highlightLinks.has(linkId) ? 3 : 1;
  }, [highlightLinks]);

  return (
    <div className="flex flex-col h-screen pt-28 pb-4 relative overflow-hidden">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex items-center justify-between px-6 py-4 glass border-b border-card-border z-10 relative flex-wrap gap-4"
      >
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-accent to-accent-2 shadow-lg shadow-accent/25">
            <Network className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold font-display text-foreground">Knowledge Graph</h1>
            <p className="text-xs text-foreground-muted">
              {graphData.nodes.length} nodes · {graphData.links.length} edges · {sources.length} sources
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 flex-wrap">
          {/* Source filter */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-foreground-dim flex items-center gap-1">
              <Layers size={10} />
              Filter by File
            </label>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="glow-input px-3 py-2 text-sm rounded-xl min-w-[260px] cursor-pointer"
            >
              <option value="all">📁 All Files ({fullData.nodes.length} nodes)</option>
              {sources.map((src, idx) => {
                const count = fullData.nodes.filter((n) => n.source === src).length;
                let filename = src;
                let icon = "📄";
                if (src.includes(":")) {
                  const parts = src.split(":");
                  const type = parts[0];
                  filename = parts.slice(1).join(":");
                  if (type === "slack") icon = "💬";
                  else if (type === "audio") icon = "🎵";
                  else if (type === "image") icon = "🖼️";
                }
                return (
                  <option key={`source-${idx}`} value={src}>
                    {icon} {filename} ({count} nodes)
                  </option>
                );
              })}
            </select>
          </div>

          {/* Legend */}
          <div className="hidden md:flex items-center gap-4">
            {LEGEND.map(({ type, color }) => (
              <div key={type} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full shadow-[0_0_6px_currentColor]" style={{ backgroundColor: color, color }} />
                <span className="text-xs text-foreground-muted">{type}</span>
              </div>
            ))}
          </div>
          
          <Button
            size="sm"
            variant="outline"
            onClick={() => setIs3D(!is3D)}
            className="btn-secondary rounded-xl gap-2"
          >
            {is3D ? <Square className="w-4 h-4" /> : <Box className="w-4 h-4" />}
            {is3D ? "2D View" : "3D View"}
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={load}
            className="btn-secondary rounded-xl gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </motion.div>

      {/* Graph Canvas */}
      <div ref={containerRef} className="flex-1 relative overflow-hidden bg-background">
        {/* Loading */}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
            <div className="flex flex-col items-center gap-4">
              <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }}>
                <RefreshCw className="w-8 h-8 text-accent" />
              </motion.div>
              <p className="text-foreground-muted text-sm">Loading knowledge graph…</p>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="text-center space-y-4">
              <p className="text-danger">{error}</p>
              <Button size="sm" onClick={load} className="btn-primary rounded-xl">Retry</Button>
            </div>
          </div>
        )}

        {/* Empty */}
        {!loading && !error && graphData.nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="text-center space-y-3">
              <Network className="w-12 h-12 text-foreground-dim mx-auto" />
              <p className="text-foreground-muted">No data yet. Ingest some documents first.</p>
            </div>
          </div>
        )}

        {/* Graph */}
        {!loading && graphData.nodes.length > 0 && (
            is3D ? (
                <ForceGraph3D
                  key={`3d-${graphKey}`}
                  graphData={graphData}
                  width={dimensions.width}
                  height={dimensions.height}
                  nodeLabel="label"
                  nodeColor={(node: any) => {
                    const isHighlighted = highlightNodes.size > 0 ? highlightNodes.has(node.id) : true;
                    return isHighlighted ? (node.color ?? "#64748b") : "rgba(100, 116, 139, 0.2)";
                  }}
                  nodeVal={(node: any) => (node.type === "Decision" ? 12 : 5)}
                  linkColor={linkColor}
                  linkWidth={linkWidth}
                  linkDirectionalArrowLength={3.5}
                  linkDirectionalArrowRelPos={1}
                  linkDirectionalParticles={highlightLinks.size > 0 ? (link: any) => {
                    const sourceId = typeof link.source === 'string' ? link.source : link.source?.id;
                    const targetId = typeof link.target === 'string' ? link.target : link.target?.id;
                    return highlightLinks.has(`${sourceId}-${targetId}`) ? 3 : 0;
                  } : 3}
                  linkDirectionalParticleWidth={2}
                  linkDirectionalParticleColor={() => "#06b6d4"}
                  onNodeClick={(node: any) => handleNodeClick(node)}
                  backgroundColor="rgba(0,0,0,0)"
                />
            ) : (
                <ForceGraph2D
                  key={`2d-${graphKey}`}
                  graphData={graphData}
                  width={dimensions.width}
                  height={dimensions.height}
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  nodeCanvasObject={paintNode as any}
                  nodeCanvasObjectMode={() => "replace"}
                  linkColor={linkColor}
                  linkWidth={linkWidth}
                  linkDirectionalArrowLength={8}
                  linkDirectionalArrowRelPos={1}
                  linkDirectionalParticles={highlightLinks.size > 0 ? (link: any) => {
                    const sourceId = typeof link.source === 'string' ? link.source : link.source?.id;
                    const targetId = typeof link.target === 'string' ? link.target : link.target?.id;
                    return highlightLinks.has(`${sourceId}-${targetId}`) ? 3 : 0;
                  } : 3}
                  linkDirectionalParticleWidth={2}
                  linkDirectionalParticleSpeed={0.005}
                  linkDirectionalParticleColor={() => "#06b6d4"}
                  linkLabel="label"
                  onNodeClick={(node: any) => handleNodeClick(node)}
                  backgroundColor="transparent"
                  cooldownTicks={150}
                  d3AlphaDecay={0.01}
                  d3VelocityDecay={0.2}
                  enableNodeDrag={true}
                  enableZoomInteraction={true}
                  enablePanInteraction={true}
                />
            )
        )}

        {/* Node Detail Panel */}
        <AnimatePresence>
          {selected && (
            <motion.div
              initial={{ opacity: 0, x: 20, scale: 0.96 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 20, scale: 0.96 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className="absolute top-4 right-4 w-72 glass-strong rounded-2xl p-5 shadow-2xl border border-card-border-strong z-20"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full shadow-[0_0_8px_currentColor]"
                    style={{ backgroundColor: NODE_COLORS[selected.type] ?? "#64748b", color: NODE_COLORS[selected.type] ?? "#64748b" }}
                  />
                  <span
                    className="text-xs px-2.5 py-0.5 rounded-full font-semibold"
                    style={{
                      backgroundColor: (NODE_COLORS[selected.type] ?? "#64748b") + "22",
                      color: NODE_COLORS[selected.type] ?? "#64748b",
                    }}
                  >
                    {selected.type}
                  </span>
                </div>
                <button
                  onClick={clearSelection}
                  className="text-foreground-dim hover:text-foreground transition-colors p-1 rounded-lg hover:bg-card"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <p className="text-foreground text-sm font-semibold leading-snug mb-4">{selected.label}</p>

              {[
                { label: "Subject", value: selected.subject },
                { label: "Impact", value: selected.impact },
                { label: "Source", value: selected.source },
              ]
                .filter((f) => f.value)
                .map((field) => (
                  <div key={field.label} className="mb-3">
                    <p className="text-foreground-dim text-xs uppercase tracking-widest mb-1">{field.label}</p>
                    <p className="text-foreground-muted text-xs leading-relaxed truncate">{field.value}</p>
                  </div>
                ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Bottom status bar */}
        {!loading && graphData.nodes.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="absolute bottom-4 left-4 space-y-2 z-20 pointer-events-none"
          >
            <div className="glass-strong rounded-xl px-4 py-3 border border-card-border-strong shadow-lg">
              <p className="text-foreground-dim text-xs uppercase tracking-widest mb-1 font-semibold">
                {selectedSource === "all" ? "Viewing All Files" : "Currently Viewing"}
              </p>
              <p className="text-foreground text-sm font-bold">
                {selectedSource === "all"
                  ? `📂 All Files (${sources.length} sources)`
                  : `📄 ${selectedSource.includes(":") ? selectedSource.split(":").slice(1).join(":") : selectedSource}`}
              </p>
              <p className="text-foreground-muted text-xs mt-1">
                {graphData.nodes.length} nodes · {graphData.links.length} edges
              </p>
            </div>
            <div className="flex items-center gap-2 text-foreground-dim text-xs glass px-3 py-2 rounded-lg border border-card-border pointer-events-auto">
              <Info className="w-3 h-3" />
              Click node to inspect/highlight · Scroll to zoom · Drag to pan
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
