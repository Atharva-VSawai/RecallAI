"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, FileText, Mail, MessageSquare, RefreshCw, Search, Zap } from "lucide-react";
import { getActivityFeed, type ActivityEvent } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState, LoadingState } from "@/components/ui/state";

const eventMeta: Record<ActivityEvent["type"], { icon: typeof Activity; label: string; color: string }> = {
  slack: { icon: MessageSquare, label: "Slack", color: "text-accent" },
  gmail: { icon: Mail, label: "Email", color: "text-warning" },
  query: { icon: Search, label: "Query", color: "text-accent" },
  impact: { icon: Zap, label: "Impact", color: "text-warning" },
  ingest: { icon: FileText, label: "Ingestion", color: "text-success" },
};
const eventTypes = Object.keys(eventMeta) as ActivityEvent["type"][];
function displayTime(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? "Time unavailable" : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date); }

export default function ActivityPage() {
  const { user, activeProject } = useAuth();
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [typeFilter, setTypeFilter] = useState<"all" | ActivityEvent["type"]>("all");
  const [search, setSearch] = useState("");
  const projectId = activeProject?.id;

  const load = useCallback(async () => {
    if (!projectId) { setEvents([]); setLoading(false); return; }
    setLoading(true);
    try { setEvents(await getActivityFeed(user?.id)); } finally { setLastRefresh(new Date()); setLoading(false); }
  }, [projectId, user?.id]);

  useEffect(() => { const timer = window.setTimeout(() => { void load(); }, 0); const refresh = window.setInterval(() => { void load(); }, 30_000); return () => { window.clearTimeout(timer); window.clearInterval(refresh); }; }, [load]);
  const visibleEvents = useMemo(() => events.filter((event) => (typeFilter === "all" || event.type === typeFilter) && `${event.title} ${event.description} ${event.source ?? ""}`.toLowerCase().includes(search.toLowerCase().trim())), [events, search, typeFilter]);

  return <div className="page-container">
    <div className="page-header"><div><p className="page-eyebrow">Workspace history</p><h1 className="page-title">Activity</h1><p className="page-description">Review document processing, knowledge queries, and integration events in this workspace.</p></div><div className="flex items-center gap-3"><span className="hidden text-xs text-foreground-dim sm:inline">{lastRefresh ? `Updated ${lastRefresh.toLocaleTimeString()}` : ""}</span><Button variant="outline" onClick={() => void load()} disabled={loading}><RefreshCw size={16} className={loading ? "animate-spin" : ""} />Refresh</Button></div></div>
    <section className="panel overflow-hidden"><div className="panel-header flex-wrap py-3"><div className="relative min-w-[210px] flex-1"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground-dim" /><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search activity" className="pl-9" aria-label="Search activity" /></div><select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value as "all" | ActivityEvent["type"])} className="h-10 rounded-md border border-card-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-accent"><option value="all">All actions</option>{eventTypes.map((type) => <option key={type} value={type}>{eventMeta[type].label}</option>)}</select></div>
      {loading ? <LoadingState label="Loading activity…" /> : visibleEvents.length === 0 ? <EmptyState icon={Activity} title={events.length ? "No activity matches these filters" : "No activity yet"} description={events.length ? "Try clearing your search or choosing another action type." : "Activity will appear here when documents, queries, meetings, or integrations are processed."} action={events.length ? undefined : { href: "/query?tab=upload", label: "Add knowledge" }} /> : <div className="divide-y divide-card-border">{visibleEvents.map((event) => { const meta = eventMeta[event.type]; const Icon = meta.icon; return <article key={event.id} className="flex gap-3 px-4 py-4 transition-colors hover:bg-surface-elevated/60"><span className={`mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-md bg-surface-elevated ${meta.color}`}><Icon size={16} /></span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><div className="flex min-w-0 items-center gap-2"><span className="rounded border border-card-border bg-background px-2 py-0.5 text-[11px] font-medium text-foreground-muted">{meta.label}</span><h2 className="truncate text-sm font-medium">{event.title}</h2></div><time className="shrink-0 text-xs text-foreground-dim">{displayTime(event.timestamp)}</time></div><p className="mt-1 text-sm leading-5 text-foreground-muted">{event.description}</p>{event.source && <p className="mt-2 truncate text-xs text-foreground-dim">Source: {event.source}</p>}</div></article>; })}</div>}
      {!loading && visibleEvents.length > 0 && <div className="border-t border-card-border px-4 py-3 text-xs text-foreground-dim">{visibleEvents.length} of {events.length} event{events.length === 1 ? "" : "s"}</div>}
    </section>
  </div>;
}
