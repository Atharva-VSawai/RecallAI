"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, FileText, GitBranch, Inbox, Network, Search, ShieldCheck, Upload } from "lucide-react";
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
  const { activeProject, user, can } = useAuth();
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
    if (filesResult.status === "fulfilled") setFiles(filesResult.value.files);
    if (activityResult.status === "fulfilled") setActivity(activityResult.value);
    if (graphResult.status === "fulfilled") setGraph(graphResult.value);
    setHasError([filesResult, activityResult, graphResult].some((result) => result.status === "rejected"));
    setLoading(false);
  }, [activeProjectId, user?.id]);

  useEffect(() => { const timer = window.setTimeout(() => { void load(); }, 0); return () => window.clearTimeout(timer); }, [load]);
  if (!user) return <LandingPage />;

  return <div className="page-container">
    <div className="page-header"><div><p className="page-eyebrow">{activeProject ? `Workspace / ${activeProject.name}` : "Workspace"}</p><h1 className="page-title">Knowledge overview</h1><p className="page-description">Documents, activity, and connected knowledge for this workspace.</p></div><div className="flex flex-wrap gap-2">{can("knowledge:write") && <Link href="/query?tab=upload" className="btn-secondary inline-flex h-10 items-center gap-2 rounded-md px-4 text-sm font-medium"><Upload size={15} />Add knowledge</Link>}<Link href="/query" className="btn-primary inline-flex h-10 items-center gap-2 rounded-md px-4 text-sm font-medium"><Search size={15} />Ask knowledge</Link></div></div>
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
  return (
    <div className="-mt-[var(--topbar-height)] flex min-h-screen bg-[#0B1220] md:-ml-[var(--sidebar-width)] overflow-hidden">
      {/* Background visual (radial gradient + faint grid) */}
      <div className="absolute inset-0 z-0 pointer-events-none" style={{
        backgroundImage: `radial-gradient(circle at 30% 40%, rgba(59, 130, 246, 0.08) 0%, transparent 50%), linear-gradient(rgba(38, 52, 73, 0.2) 1px, transparent 1px), linear-gradient(90deg, rgba(38, 52, 73, 0.2) 1px, transparent 1px)`,
        backgroundSize: '100% 100%, 40px 40px, 40px 40px',
      }}></div>

      <div className="relative z-10 grid w-full lg:grid-cols-[55%_45%] max-w-[1400px] mx-auto">
        {/* Left Area: Product Presentation */}
        <div className="flex flex-col justify-center px-8 py-16 lg:px-16 xl:px-24">
          <div className="flex items-center gap-2 text-sm font-semibold mb-12">
            <span className="grid h-7 w-7 place-items-center rounded bg-accent text-white font-bold text-xs">R</span>
            Recall<span className="text-accent">.AI</span>
          </div>

          <p className="text-[11px] font-semibold tracking-widest text-[#64748B] uppercase mb-4">
            Enterprise Knowledge Platform
          </p>
          <h1 className="text-4xl md:text-5xl lg:text-[56px] font-bold leading-[1.1] tracking-tight text-foreground mb-6">
            Your organization&apos;s knowledge should never leave with your people.
          </h1>
          <p className="text-lg text-[#94A3B8] max-w-xl leading-relaxed mb-4">
            Connect documents, meetings, conversations, and decisions into a searchable organizational knowledge layer.
          </p>
          <p className="text-base text-[#64748B] max-w-xl mb-12 font-medium">
            Preserve context. Understand decisions. Accelerate knowledge transfer.
          </p>

          {/* Knowledge Flow Visualization */}
          <div className="relative mt-4 max-w-md hidden md:block">
            <div className="absolute top-0 bottom-10 left-[19px] w-px bg-[#263449]"></div>
            <div className="space-y-6">
              {[
                { label: "Documents", icon: FileText },
                { label: "Meetings", icon: Activity },
                { label: "Conversations", icon: Inbox },
                { label: "Decisions", icon: GitBranch },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-4 relative group cursor-default">
                  <div className="w-10 h-10 rounded-full border border-[#263449] bg-[#111827] flex items-center justify-center z-10 transition-colors duration-300 group-hover:border-accent group-hover:bg-[#151F2F]">
                    <item.icon size={16} className="text-[#94A3B8] group-hover:text-accent transition-colors duration-300" />
                  </div>
                  <div className="flex-1 py-2 px-4 rounded-md border border-transparent transition-colors duration-300 group-hover:border-[#263449] group-hover:bg-[#111827]/50">
                    <span className="text-sm font-medium text-[#94A3B8] group-hover:text-foreground transition-colors duration-300">{item.label}</span>
                  </div>
                </div>
              ))}
              <div className="flex items-center gap-4 relative mt-2 pt-2">
                <div className="w-10 h-10 rounded-full border border-accent bg-accent/10 flex items-center justify-center z-10">
                  <Network size={18} className="text-accent" />
                </div>
                <div className="flex-1">
                  <span className="text-base font-semibold text-foreground">Organizational Knowledge</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Area: Authentication Card */}
        <div className="flex items-center justify-center p-8 lg:p-16">
          <div className="w-full max-w-[420px] bg-[#111827] rounded-xl border border-[#263449] shadow-lg">
            <div className="p-8 md:p-10">
              <div className="flex justify-center mb-6">
                <div className="grid h-12 w-12 place-items-center rounded-lg bg-[#151F2F] border border-[#263449] text-foreground shadow-sm">
                  <Network size={22} className="text-accent" />
                </div>
              </div>
              <h2 className="text-[26px] font-semibold text-center text-foreground mb-2 tracking-tight">Welcome back</h2>
              <p className="text-[15px] text-center text-[#94A3B8] mb-8">Sign in to access your organization&apos;s knowledge.</p>

              <div className="space-y-3">
                <Link 
                  href="/login" 
                  className="w-full h-11 bg-accent text-white rounded-md text-[15px] font-medium flex items-center justify-center transition-colors duration-200 hover:bg-[#2563EB]"
                >
                  Sign in
                </Link>
                <Link 
                  href="/signup" 
                  className="w-full h-11 bg-transparent text-foreground border border-[#263449] rounded-md text-[15px] font-medium flex items-center justify-center transition-colors duration-200 hover:bg-[#151F2F] hover:border-[#3A4960]"
                >
                  Create account
                </Link>
              </div>
            </div>
            
            {/* Feature indicators */}
            <div className="border-t border-[#263449] bg-[#151F2F]/30 rounded-b-xl p-6 md:px-10">
              <div className="grid grid-cols-1 gap-4">
                <div className="flex items-start gap-3">
                  <ShieldCheck size={16} className="text-accent mt-0.5 shrink-0" />
                  <div>
                    <p className="text-xs font-semibold text-foreground">Workspace isolation</p>
                    <p className="text-[12px] text-[#94A3B8] mt-0.5 leading-snug">Keep each organization&apos;s knowledge securely separated.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
