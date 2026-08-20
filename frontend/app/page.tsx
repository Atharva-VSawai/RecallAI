"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, ArrowRight, CheckCircle2, Database, FileSearch, FileText, GitBranch, Inbox, LockKeyhole, MessageSquare, Moon, Network, Search, ShieldCheck, Sun, Upload } from "lucide-react";
import { getActivityFeed, getGraphData, listFiles, type ActivityEvent, type FileMetadata, type GraphData } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
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
  const items = [[FileText, files.length, "Indexed files"], [GitBranch, graph?.nodes.length ?? 0, "Knowledge graph entities"], [Activity, activity.length, "Recorded activity events"]] as const;
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
  return <div className="page-container"><div className="page-header"><div><p className="page-eyebrow">{activeProject ? `Workspace / ${activeProject.name}` : "Workspace"}</p><h1 className="page-title">Knowledge overview</h1><p className="page-description">Documents, activity, and connected knowledge for this workspace.</p></div><div className="flex flex-wrap gap-2">{can("knowledge:write") && <Link href="/query?tab=upload" className="btn-secondary inline-flex h-10 items-center gap-2 rounded-md px-4 text-sm font-medium"><Upload size={15} />Add knowledge</Link>}<Link href="/query" className="btn-primary inline-flex h-10 items-center gap-2 rounded-md px-4 text-sm font-medium"><Search size={15} />Ask knowledge</Link></div></div>{loading ? <LoadingState label="Loading workspace data…" /> : hasError ? <ErrorState title="Some workspace data is temporarily unavailable." onRetry={() => void load()} /> : <><Stats files={files} activity={activity} graph={graph} /><div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]"><Panel title="Recent activity" action={<Link href="/activity" className="subtle-link">View all</Link>}>{activity.length ? <div className="divide-y divide-card-border">{activity.slice(0, 6).map((event) => <div key={event.id} className="flex gap-3 px-4 py-3"><span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md bg-surface-elevated"><Activity size={14} className="text-foreground-muted" /></span><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{event.title}</p><p className="mt-0.5 truncate text-xs text-foreground-muted">{event.description}</p></div><span className="shrink-0 text-[11px] text-foreground-dim">{timeAgo(event.timestamp)}</span></div>)}</div> : <EmptyState icon={Activity} title="No activity yet" description="Activity will appear here when documents, queries, meetings, or integrations are processed." action={can("knowledge:write") ? { href: "/query?tab=upload", label: "Add knowledge" } : undefined} />}</Panel><Panel title="Indexed files" action={<Link href="/sources" className="subtle-link">Manage sources</Link>}>{files.length ? <div className="divide-y divide-card-border">{files.slice(0, 6).map((file) => <div key={file.hash} className="flex items-center gap-3 px-4 py-3"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-surface-elevated text-foreground-muted"><FileText size={15} /></span><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{file.filename}</p><p className="mt-0.5 truncate text-[11px] text-foreground-dim">{file.type || file.source}</p></div><span className="text-[11px] text-foreground-dim">{file.uploaded_at ? timeAgo(file.uploaded_at) : ""}</span></div>)}</div> : <EmptyState icon={Inbox} title="No knowledge sources yet" description="Upload a document or connect an integration to begin building organizational memory." action={can("knowledge:write") ? { href: "/query?tab=upload", label: "Add knowledge" } : undefined} />}</Panel></div><div className="mt-4"><Panel title="Knowledge graph" action={<Link href="/graph" className="subtle-link">Open graph</Link>}><div className="grid divide-y divide-card-border sm:grid-cols-3 sm:divide-x sm:divide-y-0"><div className="p-4"><p className="text-xs text-foreground-muted">Entities</p><p className="mt-2 text-xl font-semibold">{graph?.nodes.length ?? 0}</p></div><div className="p-4"><p className="text-xs text-foreground-muted">Relationships</p><p className="mt-2 text-xl font-semibold">{graph?.edges.length ?? 0}</p></div><div className="p-4"><p className="text-xs text-foreground-muted">Status</p><p className="mt-2 text-sm font-medium">{graph?.nodes.length ? "Data available" : "No graph data"}</p></div></div></Panel></div></>}</div>;
}

function MarketingMockup() {
  return <div className="marketing-mockup"><div className="marketing-mockup-top"><span className="marketing-dot" /><span className="marketing-dot" /><span className="marketing-dot" /><span className="marketing-mockup-label">Recall workspace</span><span className="marketing-status">Live</span></div><div className="marketing-mockup-body"><aside><span className="marketing-mini-logo">R</span><div className="marketing-line wide" /><div className="marketing-line" /><div className="marketing-line" /><div className="marketing-line short" /></aside><main><div className="marketing-search"><Search size={14} /> Ask across your knowledge</div><div className="marketing-answer"><span className="marketing-answer-icon"><Network size={15} /></span><div><p>What changed in the launch scope?</p><p className="marketing-muted">Answer grounded in 4 connected sources</p></div></div><div className="marketing-sources"><span>Quarterly planning</span><span>#product-decisions</span><span>Launch notes</span></div></main></div></div>;
}

function MarketingCard({ tone, icon: Icon, title, text, children }: { tone: string; icon: typeof Database; title: string; text: string; children: React.ReactNode }) {
  return <article className={`marketing-feature marketing-${tone}`}><div className="marketing-feature-copy"><span className="marketing-feature-icon"><Icon size={20} /></span><h3>{title}</h3><p>{text}</p></div>{children}</article>;
}

function LandingPage() {
  const { theme, toggleTheme } = useTheme();
  return <div className="marketing-page">
    <header className="marketing-nav"><Link href="/" className="marketing-brand"><span>R</span>Recall<span className="marketing-brand-accent">.AI</span></Link><nav className="marketing-nav-links"><a href="#platform">Platform</a><a href="#sources">Sources</a><a href="#workflow">Workflow</a><a href="#trust">Trust</a></nav><div className="marketing-nav-actions"><button type="button" onClick={toggleTheme} className="marketing-theme-button" aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}>{theme === "light" ? <Moon size={15} /> : <Sun size={15} />}{theme === "light" ? "Dark" : "Light"}</button><Link href="/login" className="marketing-login">Sign in <ArrowRight size={14} /></Link><Link href="/signup" className="marketing-nav-cta">Create workspace</Link></div></header>
    <main>
      <section className="marketing-hero"><div className="marketing-hero-copy"><p className="marketing-kicker">Enterprise knowledge infrastructure</p><h1>Make every decision easier to find again.</h1><p className="marketing-hero-lead">Recall turns documents, conversations, meetings, and decisions into a living knowledge layer your organization can search, understand, and build on.</p><div className="marketing-actions"><Link href="/signup" className="marketing-button dark">Create your workspace <ArrowRight size={16} /></Link><Link href="/login" className="marketing-text-link">Sign in <ArrowRight size={16} /></Link></div><div className="marketing-proof"><span><CheckCircle2 size={15} />Source-backed answers</span><span><CheckCircle2 size={15} />Workspace-aware access</span></div></div><div className="marketing-hero-art"><div className="marketing-orbit orbit-one" /><div className="marketing-orbit orbit-two" /><MarketingMockup /></div></section>
      <section id="platform" className="marketing-intro"><p className="marketing-kicker">One operating layer</p><h2>From scattered inputs to shared organizational memory.</h2><p>Recall gives your team one place to preserve context, retrieve knowledge, and revisit the reasoning behind important work.</p></section>
      <section className="marketing-features"><MarketingCard tone="pink" icon={FileSearch} title="Ask the knowledge you already have" text="Search across indexed sources and inspect the evidence behind an answer."><div className="marketing-mini-query"><Search size={15} /><span>Where did we decide this?</span><ArrowRight size={15} /></div></MarketingCard><MarketingCard tone="teal" icon={Network} title="See how decisions connect" text="Explore people, reasons, alternatives, and impact through a connected knowledge graph."><div className="marketing-mini-graph"><span /><i /><b /><em /><strong /></div></MarketingCard><MarketingCard tone="lavender" icon={Database} title="Keep context in the workspace" text="Separate organizational knowledge by project and workspace boundaries."><div className="marketing-mini-workspace"><span><ShieldCheck size={14} />Workspace isolated</span><div /><div /><div /></div></MarketingCard></section>
      <section id="sources" className="marketing-sources-section"><div className="marketing-section-heading"><p className="marketing-kicker">Meet knowledge where it lives</p><h2>Built around the sources your teams already use.</h2><p>Bring working knowledge into one place without changing where your team works.</p></div><div className="marketing-source-grid"><div className="marketing-source-card peach"><FileText size={21} /><h3>Documents & PDFs</h3><p>Extract text and decisions from working documents.</p></div><div className="marketing-source-card mint"><Upload size={21} /><h3>Spreadsheets</h3><p>Index Excel and CSV knowledge for retrieval.</p></div><div className="marketing-source-card ochre"><MessageSquare size={21} /><h3>Slack & Teams</h3><p>Bring conversation and meeting context together.</p></div><div className="marketing-source-card cream"><Activity size={21} /><h3>Audio & images</h3><p>Transcribe audio and extract text with OCR.</p></div></div></section>
      <section id="workflow" className="marketing-workflow"><div className="marketing-section-heading"><p className="marketing-kicker">A clear path from input to insight</p><h2>Knowledge that keeps moving.</h2><p>Every source has a visible journey from ingestion to retrieval, so the system stays understandable as it grows.</p></div><div className="marketing-steps"><div><span>01</span><h3>Connect or upload</h3><p>Add documents, files, integrations, images, audio, or spreadsheets.</p></div><div><span>02</span><h3>Process and index</h3><p>Recall extracts, embeds, and records the knowledge your team can use.</p></div><div><span>03</span><h3>Query and explore</h3><p>Ask questions, review sources, inspect activity, and follow connected decisions.</p></div></div></section>
      <section id="trust" className="marketing-trust"><div><p className="marketing-kicker">Designed for responsible reuse</p><h2>Make the reasoning behind work durable.</h2><p>Preserve the decisions, people, alternatives, and impact that help the next person move with confidence.</p></div><div className="marketing-trust-card"><LockKeyhole size={22} /><h3>Workspace boundaries by design.</h3><p>Keep knowledge scoped to the project and organization it belongs to, with role-aware access throughout the application.</p><div><CheckCircle2 size={15} />Project-aware sources</div><div><CheckCircle2 size={15} />Permission-aware actions</div><div><CheckCircle2 size={15} />Activity visibility</div></div></section>
      <section className="marketing-cta"><div className="marketing-cta-art"><div /><div /><div /><Network size={42} /></div><div><p className="marketing-kicker">Your team’s shared memory</p><h2>Keep the important context close.</h2><p>Start building a knowledge layer that helps your organization remember how work gets done.</p><div className="marketing-actions"><Link href="/signup" className="marketing-button dark">Create your workspace <ArrowRight size={16} /></Link><Link href="/login" className="marketing-button light">Sign in</Link></div></div></section>
    </main>
    <footer className="marketing-footer"><span>© {new Date().getFullYear()} Recall.AI</span><span>Enterprise knowledge platform</span></footer>
  </div>;
}
