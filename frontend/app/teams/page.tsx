"use client";

import { useCallback, useEffect, useState } from "react";
import { CalendarDays, CheckCircle2, CircleOff, CloudOff, Loader2, RefreshCw, ShieldCheck, Video } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state";
import { useAuth } from "@/contexts/AuthContext";
import { connectTeams, disconnectTeams, getTeamsMeeting, getTeamsStatus, listTeamsMeetings, syncTeams, type TeamsMeeting, type TeamsStatus } from "@/lib/api";

type MeetingDetails = TeamsMeeting & { knowledge: Record<string, unknown>[]; participants: string[] };
function displayDate(value?: string | number | null) { if (!value) return "Not available"; const date = new Date(value); return Number.isNaN(date.getTime()) ? "Not available" : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: typeof value === "string" ? "short" : undefined }).format(date); }

export default function TeamsPage() {
  const { can, activeProject } = useAuth();
  const [status, setStatus] = useState<TeamsStatus | null>(null);
  const [meetings, setMeetings] = useState<TeamsMeeting[]>([]);
  const [selected, setSelected] = useState<MeetingDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [transcriptAccess, setTranscriptAccess] = useState<"available" | "requires_admin_consent" | null>(null);
  const activeProjectId = activeProject?.id;

  const load = useCallback(async () => {
    if (!activeProjectId) { setLoading(false); setStatus(null); setMeetings([]); return; }
    setLoading(true); setHasError(false);
    const [statusResult, meetingsResult] = await Promise.allSettled([getTeamsStatus(), listTeamsMeetings()]);
    if (statusResult.status === "fulfilled") setStatus(statusResult.value);
    if (meetingsResult.status === "fulfilled") setMeetings(meetingsResult.value);
    setHasError(statusResult.status === "rejected" || meetingsResult.status === "rejected");
    setLoading(false);
  }, [activeProjectId]);

  useEffect(() => { const timer = window.setTimeout(() => { void load(); }, 0); return () => window.clearTimeout(timer); }, [load]);
  const handleConnect = async () => { setNotice(null); try { await connectTeams(); } catch { setNotice("We couldn’t start the Microsoft Teams connection."); } };
  const handleDisconnect = async () => { setBusy(true); setNotice(null); try { await disconnectTeams(); setSelected(null); setNotice("Microsoft Teams has been disconnected."); await load(); } catch { setNotice("We couldn’t disconnect Microsoft Teams."); } finally { setBusy(false); } };
  const runSync = async () => { setBusy(true); setNotice(null); try { const result = await syncTeams(); const total = result.count + result.mocked_count; setTranscriptAccess(result.transcript_access === "requires_admin_consent" ? "requires_admin_consent" : result.transcript_access === "available" ? "available" : null); setNotice(`${total} meeting transcript${total === 1 ? " was" : "s were"} processed.`); await load(); } catch { setNotice("We couldn’t sync Teams data. Please try again."); } finally { setBusy(false); } };
  const openMeeting = async (meeting: TeamsMeeting) => { setBusy(true); setNotice(null); try { setSelected(await getTeamsMeeting(meeting.id)); } catch { setNotice("We couldn’t load this meeting’s extracted knowledge."); } finally { setBusy(false); } };
  const canManage = can("project:manage");

  return <div className="page-container">
    <div className="page-header"><div><p className="page-eyebrow">Integration</p><h1 className="page-title">Microsoft Teams</h1><p className="page-description">Bring meeting transcripts and the knowledge extracted from them into this workspace.</p></div>{canManage && (status?.connected ? <Button variant="outline" onClick={() => void handleDisconnect()} disabled={busy}><CircleOff size={16} />Disconnect</Button> : <Button onClick={() => void handleConnect()} disabled={busy}><Video size={16} />Connect Teams</Button>)}</div>
    {notice && <div className="mb-4 rounded-md border border-card-border bg-card px-4 py-3 text-sm text-foreground-muted">{notice}</div>}
    {transcriptAccess === "requires_admin_consent" && <div className="mb-4 rounded-md border border-warning/35 bg-warning/10 px-4 py-3 text-sm text-foreground-muted"><strong className="text-warning">Transcript access requires administrator consent.</strong> A Teams administrator can grant access before transcripts can be indexed.</div>}
    {loading ? <LoadingState label="Loading Teams connection…" /> : hasError ? <ErrorState title="We couldn’t load Teams data." onRetry={() => void load()} /> : <>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(220px,.5fr)]"><section className="panel p-5"><div className="flex flex-wrap items-start gap-3"><span className="grid h-11 w-11 place-items-center rounded-md bg-accent/15 text-accent"><Video size={21} /></span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="text-base font-semibold">Microsoft Teams</h2><span className={`rounded border px-2 py-0.5 text-[11px] font-medium ${status?.connected ? "border-success/30 bg-success/10 text-success" : "border-card-border bg-surface-elevated text-foreground-muted"}`}>{status?.connected ? "Connected" : status?.status === "reauthorization_required" ? "Reconnect required" : "Not connected"}</span></div><p className="mt-1 text-sm text-foreground-muted">Project-level connection</p></div></div><dl className="mt-5 grid gap-4 border-t border-card-border pt-4 text-sm sm:grid-cols-3"><div><dt className="text-xs text-foreground-dim">Connected account</dt><dd className="mt-1 truncate text-foreground">{status?.email ?? "Not connected"}</dd></div><div><dt className="text-xs text-foreground-dim">Last connection update</dt><dd className="mt-1 text-foreground">{displayDate(status?.updated_at)}</dd></div><div><dt className="text-xs text-foreground-dim">Transcript access</dt><dd className="mt-1 text-foreground">{transcriptAccess === "requires_admin_consent" ? "Admin consent required" : status?.connected ? "Available after sync" : "Connect Teams first"}</dd></div></dl><p className="mt-5 flex items-center gap-2 text-xs text-foreground-muted"><ShieldCheck size={15} className="text-success" />OAuth tokens are encrypted and never sent to the browser.</p></section>
        <section className="panel p-5"><p className="text-sm text-foreground-muted">This workspace</p><p className="mt-2 text-3xl font-semibold">{meetings.length}</p><p className="mt-1 text-sm text-foreground-dim">meetings indexed</p>{status?.connected && can("knowledge:write") && <Button variant="outline" className="mt-5 w-full" onClick={() => void runSync()} disabled={busy}>{busy ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}Sync meetings</Button>}</section></div>
      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(280px,.8fr)_minmax(0,1.2fr)]"><section className="panel overflow-hidden"><div className="panel-header"><h2 className="panel-title">Recent meetings</h2><CalendarDays size={17} className="text-foreground-dim" /></div>{meetings.length === 0 ? <EmptyState icon={CalendarDays} title="No meetings indexed" description={status?.connected ? "Sync Teams to retrieve available meeting transcripts." : "Connect Teams to begin indexing meeting knowledge."} /> : <div className="divide-y divide-card-border">{meetings.map((meeting) => <button key={meeting.id} onClick={() => void openMeeting(meeting)} className={`w-full px-4 py-3 text-left transition-colors hover:bg-surface-elevated ${selected?.id === meeting.id ? "bg-accent/10" : ""}`}><p className="truncate text-sm font-medium">{meeting.title}</p><p className="mt-1 text-xs text-foreground-dim">{displayDate(meeting.start)}</p></button>)}</div>}</section>
        <section className="panel min-h-80 p-5">{selected ? <><p className="page-eyebrow">Meeting knowledge</p><h2 className="mt-1 text-xl font-semibold">{selected.title}</h2><p className="mt-2 text-sm text-foreground-muted">{selected.participants?.length ?? 0} participants · {selected.knowledge?.length ?? 0} extracted items</p><div className="mt-5 space-y-3">{selected.knowledge?.length ? selected.knowledge.map((item, index) => <article key={String(item.id ?? index)} className="rounded-md border border-card-border p-4"><div className="flex flex-wrap items-center justify-between gap-2"><span className="rounded border border-accent/30 bg-accent/10 px-2 py-0.5 text-[11px] font-medium capitalize text-accent">{String(item.category ?? "Knowledge").replaceAll("_", " ")}</span>{item.deadline != null && <span className="text-xs text-warning">Due {String(item.deadline)}</span>}</div><p className="mt-2 text-sm font-medium">{String(item.title ?? "Untitled item")}</p>{item.details != null && <p className="mt-1 text-xs leading-5 text-foreground-muted">{String(item.details)}</p>}</article>) : <EmptyState icon={CheckCircle2} title="No extracted items" description="This meeting does not have extracted knowledge available yet." />}</div></> : <EmptyState icon={CloudOff} title="Select a meeting" description="Choose a recent meeting to inspect the knowledge extracted from its transcript." />}</section></div>
    </>}
  </div>;
}
