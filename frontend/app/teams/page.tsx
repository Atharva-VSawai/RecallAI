"use client";

import { useEffect, useState } from "react";
import { CalendarDays, CircleOff, Loader2, RefreshCw, ShieldCheck, Video } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { connectTeams, disconnectTeams, getTeamsMeeting, getTeamsStatus, listTeamsMeetings, syncTeams, type TeamsMeeting, type TeamsStatus } from "@/lib/api";

type MeetingDetails = TeamsMeeting & { knowledge: Record<string, unknown>[]; participants: string[] };

export default function TeamsPage() {
  const { can, activeProject } = useAuth();
  const [status, setStatus] = useState<TeamsStatus | null>(null);
  const [meetings, setMeetings] = useState<TeamsMeeting[]>([]);
  const [selected, setSelected] = useState<MeetingDetails | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = async () => {
    try {
      setStatus(await getTeamsStatus());
      setMeetings(await listTeamsMeetings());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load Teams");
    }
  };

  useEffect(() => { if (activeProject) void load(); }, [activeProject?.id]);

  const handleConnect = async () => {
    try { await connectTeams(); } catch (error) { setMessage(error instanceof Error ? error.message : "Could not connect Teams"); }
  };

  const handleDisconnect = async () => {
    setBusy(true);
    try { await disconnectTeams(); setSelected(null); await load(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Could not disconnect Teams"); }
    finally { setBusy(false); }
  };

  const runSync = async () => {
    setBusy(true);
    setMessage("");
    try {
      const result = await syncTeams();
      setMessage(result.message ?? (result.mocked_count ? `${result.mocked_count} mock transcript${result.mocked_count === 1 ? "" : "s"} processed through the knowledge pipeline.` : `${result.count} meeting transcript${result.count === 1 ? "" : "s"} processed.`));
      await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Teams sync failed"); }
    finally { setBusy(false); }
  };

  const openMeeting = async (meeting: TeamsMeeting) => {
    try { setSelected(await getTeamsMeeting(meeting.id)); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Unable to load meeting"); }
  };

  return (
    <main className="min-h-screen px-6 py-12 md:px-12">
      <div className="mx-auto max-w-6xl space-y-8">
        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.25em] text-accent">Knowledge sources / Microsoft Teams</p>
            <h1 className="mt-3 font-display text-4xl font-bold">Meetings, remembered.</h1>
            <p className="mt-3 max-w-2xl text-foreground-muted">Connect Teams to bring transcripts, decisions, risks, action items, and requirements into this project&apos;s knowledge graph.</p>
          </div>
          {can("project:manage") && (status?.connected ?
            <Button variant="outline" className="rounded-xl" onClick={handleDisconnect} disabled={busy}><CircleOff size={16} /> Disconnect</Button> :
            <Button className="btn-primary rounded-xl" onClick={handleConnect}><Video size={16} /> Connect Teams</Button>)}
        </div>

        {message && <div className="rounded-xl border border-accent/30 bg-accent/10 px-4 py-3 text-sm text-foreground-muted">{message}</div>}
        {status?.mock_transcripts_enabled && <div className="rounded-xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-foreground-muted"><strong className="text-warning">Development transcript mode:</strong> Teams transcript calls fall back to a mock Graph transcript when transcript admin consent is unavailable.</div>}

        <section className="grid gap-5 md:grid-cols-3">
          <div className="glass rounded-2xl p-5 md:col-span-2">
            <div className="flex items-center gap-3"><div className="rounded-xl bg-accent/15 p-3 text-accent"><Video /></div><div><p className="font-semibold">Microsoft Teams</p><p className="text-sm text-foreground-muted">Project-level connection</p></div><span className={`ml-auto rounded-full px-3 py-1 text-xs font-semibold ${status?.connected ? "bg-success/15 text-success" : "bg-foreground-dim/15 text-foreground-muted"}`}>{status?.connected ? "Connected" : status?.status === "reauthorization_required" ? "Reconnect required" : "Not connected"}</span></div>
            <div className="mt-6 flex items-center gap-2 text-sm text-foreground-muted"><ShieldCheck size={16} className="text-success" /> OAuth tokens are encrypted and never sent to the browser.</div>
            {status?.email && <p className="mt-2 text-sm text-foreground-dim">Connected as {status.email}</p>}
          </div>
          <div className="glass rounded-2xl p-5"><p className="text-sm text-foreground-muted">This project</p><p className="mt-2 text-3xl font-bold">{meetings.length}</p><p className="text-sm text-foreground-dim">meetings indexed</p>{status?.connected && can("knowledge:write") && <Button variant="outline" className="mt-5 w-full rounded-xl" onClick={runSync} disabled={busy}>{busy ? <Loader2 className="animate-spin" size={16} /> : <RefreshCw size={16} />} Sync meetings</Button>}</div>
        </section>

        <section className="grid gap-5 lg:grid-cols-[1fr_1.25fr]">
          <div className="glass rounded-2xl p-5"><div className="mb-4 flex items-center justify-between"><h2 className="font-display text-xl font-semibold">Recent meetings</h2><CalendarDays size={18} className="text-accent" /></div>{meetings.length === 0 ? <p className="py-10 text-center text-sm text-foreground-muted">Connect Teams and sync to see meetings here.</p> : <div className="space-y-2">{meetings.map((meeting) => <button key={meeting.id} onClick={() => void openMeeting(meeting)} className="w-full rounded-xl border border-card-border p-4 text-left transition hover:border-accent/50 hover:bg-card-hover"><p className="font-medium">{meeting.title}</p><p className="mt-1 text-xs text-foreground-dim">{meeting.start ? new Date(meeting.start).toLocaleString() : "Date unavailable"}</p></button>)}</div>}</div>
          <div className="glass min-h-[300px] rounded-2xl p-5">{selected ? <><p className="text-sm uppercase tracking-widest text-accent">Meeting details</p><h2 className="mt-2 font-display text-2xl font-semibold">{selected.title}</h2><p className="mt-2 text-sm text-foreground-muted">{selected.participants?.length ?? 0} participants · {selected.knowledge?.length ?? 0} extracted items</p><div className="mt-6 space-y-3">{(selected.knowledge ?? []).map((item) => <div key={String(item.id)} className="rounded-xl border border-card-border p-4"><div className="flex items-center justify-between gap-3"><span className="rounded-full bg-accent/15 px-2.5 py-1 text-xs font-semibold text-accent">{String(item.category).replace("_", " ")}</span>{item.deadline != null && <span className="text-xs text-warning">Due {String(item.deadline)}</span>}</div><p className="mt-2 font-medium">{String(item.title)}</p><p className="mt-1 text-sm text-foreground-muted">{String(item.details ?? "")}</p></div>)}</div></> : <div className="flex h-full min-h-[260px] items-center justify-center text-sm text-foreground-muted">Select a meeting to inspect extracted knowledge.</div>}</div>
        </section>
      </div>
    </main>
  );
}
