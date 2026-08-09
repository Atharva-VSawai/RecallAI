"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, ArrowRight, FileText, GitBranch, Inbox, Network, Search, ShieldCheck, Upload } from "lucide-react";
import { getActivityFeed, getGraphData, listFiles, type ActivityEvent, type FileMetadata, type GraphData } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state";

function timeAgo(iso: string) {
  const minutes = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1_440) return `${Math.floor(minutes / 60)}h ago`;
  return `${Math.floor(minutes / 1_440)}d ago`;
}

function Panel({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return <section className="panel overflow-hidden"><div className="panel-header"><h2 className="panel-title">{title}</h2>{action}</div>{children}</section>;
}

function Stats({ files, activity, graph }: { files: FileMetadata[]; activity: ActivityEvent[]; graph: GraphData | null }) {
  const items = [
    [FileText, files.length, "Indexed files"],
    [GitBranch, graph?.nodes.length ?? 0, "Knowledge graph entities"],
    [Activity, activity.length, "Recorded activity events"],
  ] as const;
  return <div className="mb-4 grid gap-3 sm:grid-cols-3">{items.map(([Icon, value, label]) => <div key={label} className="panel p-4"><Icon size={16} className="text-accent" /><p className="mt-4 text-2xl font-semibold">{value}</p><p className="mt-1 text-xs text-foreground-muted">{label}</p></div>)}</div>;
}

export default function HomePage() {
  const { activeProject, user } = useAuth();
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const loadVersion = useRef(0);
  const activeProjectId = activeProject?.id;

  const load = useCallback(async () => {
    if (!activeProjectId) { setFiles([]); setActivity([]); setGraph(null); setLoading(false); return; }
    const version = ++loadVersion.current;
    setLoading(true); setHasError(false);
    const [filesResult, activityResult, graphResult] = await Promise.allSettled([listFiles(), getActivityFeed(user?.id), getGraphData()]);
    if (version !== loadVersion.current) return;
    if (filesResult.status === "fulfilled") setFiles(filesResult.value);
    if (activityResult.status === "fulfilled") setActivity(activityResult.value);
    if (graphResult.status === "fulfilled") setGraph(graphResult.value);
    setHasError([filesResult, activityResult, graphResult].some((result) => result.status === "rejected"));
    setLoading(false);
  }, [activeProjectId, user?.id]);

  useEffect(() => { const timer = window.setTimeout(() => { void load(); }, 0); return () => window.clearTimeout(timer); }, [load]);
  if (!user) return <LandingPage />;

  return <div className="page-container">
    <div className="page-header"><div><p className="page-eyebrow">{activeProject ? `Workspace / ${activeProject.name}` : "Workspace"}</p><h1 className="page-title">Knowledge overview</h1><p className="page-description">Documents, activity, and connected knowledge for this workspace.</p></div><div className="flex flex-wrap gap-2"><Link href="/query?tab=upload" className="btn-secondary inline-flex h-10 items-center gap-2 rounded-md px-4 text-sm font-medium"><Upload size={15} />Add knowledge</Link><Link href="/query" className="btn-primary inline-flex h-10 items-center gap-2 rounded-md px-4 text-sm font-medium"><Search size={15} />Ask knowledge</Link></div></div>
    {loading ? <LoadingState label="Loading workspace data…" /> : hasError ? <ErrorState title="Some workspace data is temporarily unavailable." onRetry={() => void load()} /> : <>
      <Stats files={files} activity={activity} graph={graph} />
      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <Panel title="Recent activity" action={<Link href="/activity" className="subtle-link">View all</Link>}>{activity.length ? <div className="divide-y divide-card-border">{activity.slice(0, 6).map((event) => <div key={event.id} className="flex gap-3 px-4 py-3"><span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md bg-surface-elevated"><Activity size={14} className="text-foreground-muted" /></span><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{event.title}</p><p className="mt-0.5 truncate text-xs text-foreground-muted">{event.description}</p></div><span className="shrink-0 text-[11px] text-foreground-dim">{timeAgo(event.timestamp)}</span></div>)}</div> : <EmptyState icon={Activity} title="No activity yet" description="Activity will appear here when documents, queries, meetings, or integrations are processed." action={{ href: "/query?tab=upload", label: "Add knowledge" }} />}</Panel>
        <Panel title="Indexed files" action={<Link href="/sources" className="subtle-link">Manage sources</Link>}>{files.length ? <div className="divide-y divide-card-border">{files.slice(0, 6).map((file) => <div key={file.hash} className="flex items-center gap-3 px-4 py-3"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-surface-elevated text-foreground-muted"><FileText size={15} /></span><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{file.filename}</p><p className="mt-0.5 truncate text-[11px] text-foreground-dim">{file.type || file.source}</p></div><span className="text-[11px] text-foreground-dim">{file.uploaded_at ? timeAgo(file.uploaded_at) : ""}</span></div>)}</div> : <EmptyState icon={Inbox} title="No knowledge sources yet" description="Upload a document or connect an integration to begin building organizational memory." action={{ href: "/query?tab=upload", label: "Add knowledge" }} />}</Panel>
      </div>
      <div className="mt-4"><Panel title="Knowledge graph" action={<Link href="/graph" className="subtle-link">Open graph</Link>}><div className="grid divide-y divide-card-border sm:grid-cols-3 sm:divide-x sm:divide-y-0"><div className="p-4"><p className="text-xs text-foreground-muted">Entities</p><p className="mt-2 text-xl font-semibold">{graph?.nodes.length ?? 0}</p></div><div className="p-4"><p className="text-xs text-foreground-muted">Relationships</p><p className="mt-2 text-xl font-semibold">{graph?.edges.length ?? 0}</p></div><div className="p-4"><p className="text-xs text-foreground-muted">Status</p><p className="mt-2 text-sm font-medium">{graph?.nodes.length ? "Data available" : "No graph data"}</p></div></div></Panel></div>
    </>}
  </div>;
}

function LandingPage() {
  return <div className="-mt-14 flex min-h-screen items-center bg-background px-6 py-12 md:-ml-[var(--sidebar-width)]"><div className="mx-auto w-full max-w-xl"><div className="flex items-center gap-2 text-sm font-semibold"><span className="grid h-8 w-8 place-items-center rounded-md bg-accent text-white">R</span>Recall<span className="text-accent">.AI</span></div><div className="mt-12"><p className="page-eyebrow">Enterprise knowledge platform</p><h1 className="mt-2 text-4xl font-semibold tracking-tight">Organizational knowledge, connected.</h1><p className="mt-4 max-w-lg text-base leading-7 text-foreground-muted">Sign in to search, preserve, and understand the knowledge within your workspace.</p><div className="mt-8 flex gap-3"><Link href="/login" className="btn-primary inline-flex h-10 items-center gap-2 rounded-md px-4 text-sm font-medium">Sign in <ArrowRight size={16} /></Link><Link href="/signup" className="btn-secondary inline-flex h-10 items-center rounded-md px-4 text-sm font-medium">Create account</Link></div></div><div className="mt-12 grid gap-3 border-t border-card-border pt-6 sm:grid-cols-2"><div className="panel p-4"><Network size={16} className="text-accent" /><p className="mt-3 text-sm font-medium">Connected context</p><p className="mt-1 text-xs leading-5 text-foreground-muted">Trace answers to sources and relationships.</p></div><div className="panel p-4"><ShieldCheck size={16} className="text-success" /><p className="mt-3 text-sm font-medium">Workspace scoped</p><p className="mt-1 text-xs leading-5 text-foreground-muted">Keep each project&apos;s knowledge isolated.</p></div></div></div></div>;
}
