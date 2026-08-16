"use client";

import dynamic from "next/dynamic";
import type { ForceGraphProps as ForceGraph2DProps } from "react-force-graph-2d";
import type { ForceGraphProps as ForceGraph3DProps } from "react-force-graph-3d";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ComponentType } from "react";
import { Box, ChevronRight, Filter, Info, Layers, Maximize2, Network, RefreshCw, Search, Square, X } from "lucide-react";
import { getGraphData, type GraphData, type GraphNode } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state";

const ForceGraph2D = dynamic<ForceGraph2DProps<GraphNode, GraphLink>>(() => import("react-force-graph-2d").then((module) => module.default as unknown as ComponentType<ForceGraph2DProps<GraphNode, GraphLink>>), { ssr: false });
const ForceGraph3D = dynamic<ForceGraph3DProps<GraphNode, GraphLink>>(() => import("react-force-graph-3d").then((module) => module.default as unknown as ComponentType<ForceGraph3DProps<GraphNode, GraphLink>>), { ssr: false });

type GraphLink = { source: string | GraphNode; target: string | GraphNode; label: string };
type RenderNode = GraphNode & { color: string; x?: number; y?: number };
type RenderGraph = { nodes: RenderNode[]; links: GraphLink[] };
type ForceNode = { id?: string | number; x?: number; y?: number; [key: string]: unknown };
type ForceLink = { source?: string | number | ForceNode; target?: string | number | ForceNode; [key: string]: unknown };

const NODE_COLORS: Record<GraphNode["type"], string> = { Decision: "#3B82F6", Person: "#22C55E", Reason: "#F59E0B", Alternative: "#8B5CF6" };
const NODE_TYPES = Object.keys(NODE_COLORS) as GraphNode["type"][];

function nodeId(value: string | GraphNode) { return typeof value === "string" ? value : value.id; }
function sourceLabel(source: string) { const [kind, ...rest] = source.split(":"); return rest.length ? rest.join(":") : kind; }

export default function GraphPage() {
  const [data, setData] = useState<RenderGraph>({ nodes: [], links: [] });
  const [pagination, setPagination] = useState<GraphData["pagination"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [selected, setSelected] = useState<RenderNode | null>(null);
  const [selectedSource, setSelectedSource] = useState("all");
  const [selectedType, setSelectedType] = useState<"all" | GraphNode["type"]>("all");
  const [search, setSearch] = useState("");
  const [is3D, setIs3D] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [highlightedIds, setHighlightedIds] = useState<Set<string>>(new Set());
  const graphContainerRef = useRef<HTMLDivElement>(null);
  const loadInFlight = useRef(false);

  const load = useCallback(async (offset = 0, append = false) => {
    if (loadInFlight.current) return;
    loadInFlight.current = true;
    setLoading(true); setHasError(false); setSelected(null); setHighlightedIds(new Set());
    try {
      const response: GraphData = await getGraphData(offset);
      const incoming = { nodes: response.nodes.map((node) => ({ ...node, color: NODE_COLORS[node.type] })), links: response.edges.map((edge) => ({ source: edge.source, target: edge.target, label: edge.type })) };
      setData((current) => {
        if (!append) return incoming;
        const nodes = new Map(current.nodes.map((node) => [node.id, node]));
        incoming.nodes.forEach((node) => nodes.set(node.id, node));
        const links = new Map(current.links.map((link) => [`${nodeId(link.source)}:${nodeId(link.target)}:${link.label}`, link]));
        incoming.links.forEach((link) => links.set(`${nodeId(link.source)}:${nodeId(link.target)}:${link.label}`, link));
        return { nodes: Array.from(nodes.values()), links: Array.from(links.values()) };
      });
      setPagination(response.pagination);
    } catch { setHasError(true); } finally { setLoading(false); loadInFlight.current = false; }
  }, []);

  const loadMore = useCallback(() => {
    if (pagination?.has_more) void load(pagination.offset + pagination.returned_decisions, true);
  }, [load, pagination]);

  useEffect(() => { const timer = window.setTimeout(() => { void load(); }, 0); return () => window.clearTimeout(timer); }, [load]);
  useEffect(() => {
    const container = graphContainerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(([entry]) => setDimensions({ width: Math.floor(entry.contentRect.width), height: Math.floor(entry.contentRect.height) }));
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const sources = useMemo(() => Array.from(new Set(data.nodes.flatMap((node) => node.source ? [node.source] : []))).sort(), [data.nodes]);
  const graphData = useMemo<RenderGraph>(() => {
    const term = search.trim().toLowerCase();
    const nodes = data.nodes.filter((node) => (selectedSource === "all" || node.source === selectedSource) && (selectedType === "all" || node.type === selectedType) && (!term || node.label.toLowerCase().includes(term)));
    const ids = new Set(nodes.map((node) => node.id));
    return { nodes, links: data.links.filter((link) => ids.has(nodeId(link.source)) && ids.has(nodeId(link.target))) };
  }, [data, search, selectedSource, selectedType]);

  const selectNode = useCallback((rawNode: ForceNode) => {
    const node = rawNode as unknown as RenderNode;
    const connections = new Set<string>([node.id]);
    graphData.links.forEach((link) => { if (nodeId(link.source) === node.id || nodeId(link.target) === node.id) { connections.add(nodeId(link.source)); connections.add(nodeId(link.target)); } });
    setSelected(node); setHighlightedIds(connections);
  }, [graphData.links]);

  const nodeCanvasObject = useCallback((rawNode: ForceNode, context: CanvasRenderingContext2D, scale: number) => {
    const node = rawNode as unknown as RenderNode;
    const isSelected = node.id === selected?.id;
    const isDimmed = highlightedIds.size > 0 && !highlightedIds.has(node.id);
    const radius = node.type === "Decision" ? 7 : 5;
    const x = node.x ?? 0; const y = node.y ?? 0;
    context.beginPath(); context.arc(x, y, radius, 0, 2 * Math.PI);
    context.fillStyle = isDimmed ? "rgba(100,116,139,.18)" : node.color;
    context.fill();
    context.strokeStyle = isSelected ? "#F8FAFC" : "rgba(248,250,252,.55)";
    context.lineWidth = isSelected ? 2 / scale : 1 / scale;
    context.stroke();
    if (node.type === "Decision" || isSelected || highlightedIds.has(node.id)) {
      const label = node.label.length > 36 ? `${node.label.slice(0, 36)}…` : node.label;
      context.font = `${11 / scale}px Inter, sans-serif`; context.fillStyle = isDimmed ? "rgba(148,163,184,.35)" : "#E2E8F0";
      context.textAlign = "center"; context.textBaseline = "top"; context.fillText(label, x, y + radius + 4 / scale);
    }
  }, [highlightedIds, selected?.id]);

  const linkColor = useCallback((rawLink: ForceLink) => {
    const link = rawLink as unknown as GraphLink;
    const connected = highlightedIds.size === 0 || (highlightedIds.has(nodeId(link.source)) && highlightedIds.has(nodeId(link.target)));
    return connected ? "rgba(148,163,184,.45)" : "rgba(148,163,184,.10)";
  }, [highlightedIds]);

  const openFullscreen = () => { const element = graphContainerRef.current; if (element?.requestFullscreen) void element.requestFullscreen(); };
  const resetSelection = () => { setSelected(null); setHighlightedIds(new Set()); };

  return <div className="flex h-[calc(100dvh-var(--topbar-height))] min-h-[540px] flex-col overflow-hidden bg-background">
    <header className="border-b border-card-border bg-background-secondary px-4 py-3 md:px-6"><div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-3"><span className="grid h-9 w-9 place-items-center rounded-md bg-accent/15 text-accent"><Network size={19} /></span><div><h1 className="text-lg font-semibold">Knowledge graph</h1><p className="mt-0.5 text-xs text-foreground-muted">{data.nodes.length} nodes · {data.links.length} edges · {sources.length} sources</p></div></div><div className="flex flex-wrap items-center gap-2"><Button variant="outline" size="sm" onClick={() => setIs3D((value) => !value)}>{is3D ? <Square size={15} /> : <Box size={15} />}{is3D ? "2D view" : "3D view"}</Button><Button variant="outline" size="sm" onClick={openFullscreen}><Maximize2 size={15} />Fullscreen</Button><Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}><RefreshCw size={15} className={loading ? "animate-spin" : ""} />Refresh</Button></div></div>
      <div className="mt-3 grid gap-2 md:grid-cols-[minmax(190px,1fr)_180px_180px_auto]"><div className="relative"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground-dim" /><Input value={search} onChange={(event) => setSearch(event.target.value)} className="h-9 pl-9" placeholder="Search entities" aria-label="Search graph entities" /></div><label className="relative"><Layers size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-foreground-dim" /><select value={selectedSource} onChange={(event) => { setSelectedSource(event.target.value); resetSelection(); }} className="h-9 w-full appearance-none rounded-md border border-card-border bg-background pl-9 pr-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-accent"><option value="all">All sources</option>{sources.map((source) => <option key={source} value={source}>{sourceLabel(source)}</option>)}</select></label><label className="relative"><Filter size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-foreground-dim" /><select value={selectedType} onChange={(event) => { setSelectedType(event.target.value as "all" | GraphNode["type"]); resetSelection(); }} className="h-9 w-full appearance-none rounded-md border border-card-border bg-background pl-9 pr-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-accent"><option value="all">All entity types</option>{NODE_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}</select></label><div className="hidden items-center gap-3 lg:flex">{NODE_TYPES.map((type) => <span key={type} className="inline-flex items-center gap-1.5 text-xs text-foreground-muted"><i className="h-2 w-2 rounded-full" style={{ backgroundColor: NODE_COLORS[type] }} />{type}</span>)}</div></div>
    </header>
    <div ref={graphContainerRef} className="relative min-h-0 flex-1 bg-background">
      {!loading && !hasError && pagination && <div className="pointer-events-none absolute left-1/2 top-3 z-10 -translate-x-1/2 rounded-md border border-card-border bg-card/95 px-3 py-1.5 text-xs text-foreground-muted shadow">Showing {pagination.offset + pagination.returned_decisions} of {pagination.total_decisions} decisions</div>}
      {loading ? <LoadingState label="Loading knowledge graph…" /> : hasError ? <ErrorState title="Knowledge graph temporarily unavailable." onRetry={() => void load()} /> : graphData.nodes.length === 0 ? <EmptyState icon={Network} title="No graph data yet" description="Ingest a document or sync an integration to start building connected organizational knowledge." action={{ href: "/query?tab=upload", label: "Add knowledge" }} /> : <>{dimensions.width > 0 && (is3D ? <ForceGraph3D graphData={graphData} width={dimensions.width} height={dimensions.height} nodeLabel="label" nodeColor={(node: RenderNode) => highlightedIds.size === 0 || highlightedIds.has(node.id) ? node.color : "rgba(100,116,139,.18)"} nodeVal={(node: RenderNode) => node.type === "Decision" ? 9 : 5} linkColor={linkColor} linkWidth={1.4} linkDirectionalArrowLength={2.8} linkDirectionalArrowRelPos={1} onNodeClick={selectNode} backgroundColor="#0B1220" /> : <ForceGraph2D graphData={graphData} width={dimensions.width} height={dimensions.height} nodeCanvasObject={nodeCanvasObject} nodeCanvasObjectMode={() => "replace"} linkColor={linkColor} linkWidth={1.25} linkDirectionalArrowLength={6} linkDirectionalArrowRelPos={1} onNodeClick={selectNode} backgroundColor="transparent" cooldownTicks={120} d3AlphaDecay={0.02} d3VelocityDecay={0.28} />)}</>}
      {!loading && !hasError && graphData.nodes.length > 0 && <div className="pointer-events-none absolute bottom-4 left-4 hidden items-center gap-2 rounded-md border border-card-border bg-card px-3 py-2 text-xs text-foreground-muted md:flex"><Info size={14} />Select an entity to inspect its connected knowledge. Scroll to zoom and drag to pan.</div>}
      {!loading && !hasError && pagination?.has_more && <div className="absolute bottom-4 right-4 z-10 rounded-md border border-card-border bg-card p-2 shadow-lg"><Button variant="outline" size="sm" onClick={loadMore}>Load next {pagination.limit} decisions</Button></div>}
      {selected && <aside className="absolute inset-x-3 bottom-3 z-10 rounded-lg border border-card-border bg-card p-4 shadow-2xl sm:inset-x-auto sm:right-4 sm:top-4 sm:bottom-auto sm:w-80"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><span className="inline-flex items-center gap-1.5 rounded border px-2 py-1 text-[11px] font-medium" style={{ borderColor: `${NODE_COLORS[selected.type]}55`, backgroundColor: `${NODE_COLORS[selected.type]}16`, color: NODE_COLORS[selected.type] }}><i className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: NODE_COLORS[selected.type] }} />{selected.type}</span><h2 className="mt-3 text-base font-semibold leading-6">{selected.label}</h2></div><button onClick={resetSelection} className="rounded-md p-1.5 text-foreground-dim hover:bg-surface-elevated hover:text-foreground" aria-label="Close entity inspector"><X size={16} /></button></div><dl className="mt-4 space-y-3 text-sm">{[{ label: "Subject", value: selected.subject }, { label: "Impact", value: selected.impact }, { label: "Source", value: selected.source }].filter((item) => item.value).map((item) => <div key={item.label}><dt className="text-[11px] font-medium uppercase tracking-wide text-foreground-dim">{item.label}</dt><dd className="mt-1 break-words text-xs leading-5 text-foreground-muted">{item.value}</dd></div>)}</dl><div className="mt-4 border-t border-card-border pt-3 text-xs text-foreground-muted"><ChevronRight size={14} className="mr-1 inline text-accent" />{Math.max(highlightedIds.size - 1, 0)} connected entit{highlightedIds.size === 2 ? "y" : "ies"}</div></aside>}
    </div>
  </div>;
}
