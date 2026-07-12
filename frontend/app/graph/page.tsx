"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Network, RefreshCw, Info, X } from "lucide-react";
import { getGraphData, GraphNode, GraphData } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import dynamic from "next/dynamic";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

const NODE_COLORS: Record<string, string> = {
  Decision: "#3b82f6",
  Person: "#10b981",
  Reason: "#f59e0b",
  Alternative: "#8b5cf6",
};

const LEGEND = [
  { type: "Decision", color: "#3b82f6" },
  { type: "Person", color: "#10b981" },
  { type: "Reason", color: "#f59e0b" },
  { type: "Alternative", color: "#8b5cf6" },
];

export default function GraphPage() {
  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });
  const [fullData, setFullData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [sources, setSources] = useState<string[]>([]);
  const [selectedSource, setSelectedSource] = useState<string>("all");
  const [graphKey, setGraphKey] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

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
      
      const allSources = data.nodes.map(n => n.source).filter((s): s is string => !!s && s !== '');
      const uniqueSources = Array.from(new Set(allSources));
      setSources(uniqueSources);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { 
    load(); 
  }, [load]);

  // Filter graph data by selected source
  useEffect(() => {
    if (selectedSource === "all") {
      setGraphData(fullData);
    } else {
      const filteredNodes = fullData.nodes.filter(n => n.source === selectedSource);
      const nodeIds = new Set(filteredNodes.map(n => n.id));
      
      const filteredLinks = fullData.links.filter(l => {
        const sourceId = typeof l.source === 'string' ? l.source : l.source?.id;
        const targetId = typeof l.target === 'string' ? l.target : l.target?.id;
        return nodeIds.has(sourceId) && nodeIds.has(targetId);
      });
      
      setGraphData({ nodes: filteredNodes, links: filteredLinks });
    }
    setGraphKey(prev => prev + 1);
  }, [selectedSource, fullData]);

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

  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const r = node.type === "Decision" ? 8 : 5;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = node.color;
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.5)";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    
    // Always show labels for better visibility
    const fontSize = node.type === "Decision" ? 12 : 10;
    ctx.font = `${fontSize / globalScale}px Sans-Serif`;
    ctx.fillStyle = "#ffffff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const label = node.label || node.id || "";
    const maxLen = node.type === "Decision" ? 40 : 30;
    const displayLabel = label.length > maxLen ? label.slice(0, maxLen) + "..." : label;
    ctx.fillText(displayLabel, node.x, node.y + r + 12 / globalScale);
  }, []);

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-blue-500/20">
            <Network className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">Knowledge Graph</h1>
            <p className="text-xs text-white/50">
              {graphData.nodes.length} nodes · {graphData.links.length} edges · {sources.length} sources
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Source Filter */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-white/60">Filter by File:</label>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="px-3 py-2 text-sm rounded-lg bg-slate-800 border border-white/20 text-white focus:outline-none focus:border-blue-400 min-w-[280px] cursor-pointer [&>option]:text-black [&>option]:bg-white"
            >
              <option value="all">📁 All Files ({fullData.nodes.length} nodes)</option>
              {sources.length > 0 && sources.map((src, idx) => {
                const count = fullData.nodes.filter(n => n.source === src).length;
                let filename = src;
                let icon = "📄";
                
                if (src.includes(':')) {
                  const parts = src.split(':');
                  const type = parts[0];
                  filename = parts.slice(1).join(':');
                  
                  if (type === 'document') icon = '📄';
                  else if (type === 'slack') icon = '💬';
                  else if (type === 'audio') icon = '🎵';
                  else if (type === 'image') icon = '🖼️';
                }
                
                return (
                  <option key={`source-${idx}`} value={src}>
                    {icon} {filename} ({count} nodes)
                  </option>
                );
              })}
            </select>
            <span className="text-xs text-white/40">
              {selectedSource === "all" ? `All ${sources.length} files` : `Filtered view`}
            </span>
          </div>

          {/* Legend */}
          <div className="hidden md:flex items-center gap-3">
            {LEGEND.map(({ type, color }) => (
              <div key={type} className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-xs text-white/60">{type}</span>
              </div>
            ))}
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={load}
            disabled={loading}
            className="border-white/20 text-white hover:bg-white/10"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Graph Canvas */}
      <div ref={containerRef} className="flex-1 relative overflow-hidden">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="flex flex-col items-center gap-3">
              <RefreshCw className="w-8 h-8 text-blue-400 animate-spin" />
              <p className="text-white/60 text-sm">Loading graph...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="text-center space-y-3">
              <p className="text-red-400">{error}</p>
              <Button size="sm" onClick={load} className="bg-blue-600 hover:bg-blue-700 text-white">
                Retry
              </Button>
            </div>
          </div>
        )}

        {!loading && !error && graphData.nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="text-center space-y-2">
              <Network className="w-12 h-12 text-white/20 mx-auto" />
              <p className="text-white/40">No data yet. Ingest some documents first.</p>
            </div>
          </div>
        )}

        {!loading && graphData.nodes.length > 0 && (
          <ForceGraph2D
            key={graphKey}
            graphData={graphData}
            width={dimensions.width}
            height={dimensions.height}
            nodeCanvasObject={paintNode}
            nodeCanvasObjectMode={() => "replace"}
            linkColor={() => "rgba(148,163,184,0.8)"}
            linkWidth={3}
            linkDirectionalArrowLength={8}
            linkDirectionalArrowRelPos={1}
            linkDirectionalParticles={3}
            linkDirectionalParticleWidth={3}
            linkDirectionalParticleSpeed={0.005}
            linkLabel="label"
            onNodeClick={(node: any) => setSelected(node as GraphNode)}
            backgroundColor="transparent"
            cooldownTicks={150}
            d3AlphaDecay={0.01}
            d3VelocityDecay={0.2}
            linkDistance={80}
            chargeStrength={-300}
            enableNodeDrag={true}
            enableZoomInteraction={true}
            enablePanInteraction={true}
          />
        )}

        {/* Node Detail Panel */}
        {selected && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="absolute top-4 right-4 w-72 bg-slate-800/90 backdrop-blur-md border border-white/10 rounded-2xl p-4 shadow-2xl"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <span
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: NODE_COLORS[selected.type] ?? "#64748b" }}
                />
                <Badge
                  className="text-xs"
                  style={{ backgroundColor: NODE_COLORS[selected.type] + "33", color: NODE_COLORS[selected.type], border: "none" }}
                >
                  {selected.type}
                </Badge>
              </div>
              <button onClick={() => setSelected(null)} className="text-white/40 hover:text-white transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-white text-sm font-medium leading-snug mb-3">{selected.label}</p>
            {selected.subject && (
              <div className="mb-2">
                <p className="text-white/40 text-xs uppercase tracking-wider mb-0.5">Subject</p>
                <p className="text-white/80 text-xs">{selected.subject}</p>
              </div>
            )}
            {selected.impact && (
              <div className="mb-2">
                <p className="text-white/40 text-xs uppercase tracking-wider mb-0.5">Impact</p>
                <p className="text-white/80 text-xs">{selected.impact}</p>
              </div>
            )}
            {selected.source && (
              <div>
                <p className="text-white/40 text-xs uppercase tracking-wider mb-0.5">Source</p>
                <p className="text-white/60 text-xs truncate">{selected.source}</p>
              </div>
            )}
          </motion.div>
        )}

        {/* Hint and Filename */}
        {!loading && graphData.nodes.length > 0 && (
          <div className="absolute bottom-4 left-4 space-y-2 z-20">
            {/* Always show current filter status */}
            <div className="px-4 py-3 rounded-xl bg-blue-600/90 backdrop-blur-md border border-blue-400/30 shadow-lg">
              <p className="text-blue-200 text-xs uppercase tracking-wider mb-1 font-semibold">
                {selectedSource === "all" ? "Viewing All Files" : "Currently Viewing"}
              </p>
              <p className="text-white text-base font-bold">
                {selectedSource === "all" ? (
                  `📂 All Files (${sources.length} sources)`
                ) : (
                  `📄 ${selectedSource.includes(':') ? selectedSource.split(':').slice(1).join(':') : selectedSource}`
                )}
              </p>
              <p className="text-blue-200 text-xs mt-1">
                {graphData.nodes.length} nodes · {graphData.links.length} edges
              </p>
            </div>
            <div className="flex items-center gap-2 text-white/30 text-xs bg-slate-800/50 px-3 py-2 rounded-lg backdrop-blur-sm">
              <Info className="w-3 h-3" />
              Click a node to inspect · Scroll to zoom · Drag to pan
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
