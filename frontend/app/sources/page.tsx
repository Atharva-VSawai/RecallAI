"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarDays, File, FileAudio, FileSpreadsheet, FileText, Image as ImageIcon, Loader2, RefreshCw, Search, Trash2, Upload } from "lucide-react";
import { deleteFile, listFiles, type FileMetadata } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state";

function sourceIcon(type: string | null | undefined) {
  const normalized = (type ?? "").toLowerCase();
  if (["pdf"].includes(normalized)) return FileText;
  if (["xls", "xlsx", "csv"].includes(normalized)) return FileSpreadsheet;
  if (["mp3", "wav", "m4a", "mp4", "mov", "avi"].includes(normalized)) return FileAudio;
  if (["png", "jpg", "jpeg", "gif", "webp"].includes(normalized)) return ImageIcon;
  return File;
}

function sourceType(type: string | null | undefined) { return type ? type.toUpperCase() : "FILE"; }
function displayDate(value: string | null | undefined) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date unavailable" : new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(date);
}

export default function SourcesPage() {
  const { activeProject, can } = useAuth();
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [deleting, setDeleting] = useState<FileMetadata | null>(null);
  const [busy, setBusy] = useState(false);
  const activeProjectId = activeProject?.id;

  const load = useCallback(async () => {
    if (!activeProjectId) { setFiles([]); setLoading(false); return; }
    setLoading(true); setError(false);
    try { const result = await listFiles(); setFiles(result.files); } catch { setFiles([]); setError(true); } finally { setLoading(false); }
  }, [activeProjectId]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { const refresh = () => void load(); window.addEventListener("recallai:files-changed", refresh); return () => window.removeEventListener("recallai:files-changed", refresh); }, [load]);

  const visibleFiles = useMemo(() => files.filter((file) => `${file.filename ?? ""} ${file.type ?? ""} ${file.source ?? ""}`.toLowerCase().includes(search.toLowerCase().trim())), [files, search]);
  const confirmDelete = async () => {
    if (!deleting) return;
    setBusy(true);
    try { if (await deleteFile(deleting.source)) { setDeleting(null); window.dispatchEvent(new Event("recallai:files-changed")); await load(); } } finally { setBusy(false); }
  };

  return <div className="page-container">
    <div className="page-header"><div><p className="page-eyebrow">Knowledge management</p><h1 className="page-title">Sources</h1><p className="page-description">Review and manage the files indexed in {activeProject?.name ?? "this workspace"}.</p></div>{can("knowledge:write") && <Button asChild><Link href="/query?tab=upload"><Upload size={16} />Add knowledge</Link></Button>}</div>
    <section className="panel overflow-hidden">
      <div className="panel-header flex-wrap py-3"><div className="relative min-w-[220px] flex-1"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground-dim" /><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search sources" className="pl-9" aria-label="Search sources" /></div><Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}><RefreshCw size={15} className={loading ? "animate-spin" : ""} />Refresh</Button></div>
      {loading ? <LoadingState label="Loading sources…" /> : error ? <ErrorState title="We couldn’t load your sources." onRetry={() => void load()} /> : visibleFiles.length === 0 ? <EmptyState icon={FileText} title={search ? "No sources match your search" : "No knowledge sources yet"} description={search ? "Try a different filename or source type." : "Upload a document or connect an integration to begin building organizational memory."} action={search || !can("knowledge:write") ? undefined : { href: "/query?tab=upload", label: "Add knowledge" }} /> : <div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><thead className="border-b border-card-border bg-background-secondary text-xs font-medium text-foreground-dim"><tr><th className="px-4 py-3">Name</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Added</th><th className="px-4 py-3">Source</th><th className="w-16 px-4 py-3"><span className="sr-only">Actions</span></th></tr></thead><tbody className="divide-y divide-card-border">{visibleFiles.map((file) => { const Icon = sourceIcon(file.type); return <tr key={`${file.source}-${file.hash}`} className="transition-colors hover:bg-surface-elevated/60"><td className="max-w-[360px] px-4 py-3"><div className="flex min-w-0 items-center gap-3"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-surface-elevated text-foreground-muted"><Icon size={16} /></span><span className="truncate font-medium text-foreground">{file.filename}</span></div></td><td className="px-4 py-3"><span className="rounded border border-card-border bg-background px-2 py-1 text-[11px] font-medium text-foreground-muted">{sourceType(file.type)}</span></td><td className="whitespace-nowrap px-4 py-3 text-foreground-muted"><span className="inline-flex items-center gap-1.5"><CalendarDays size={13} />{displayDate(file.uploaded_at)}</span></td><td className="max-w-[200px] px-4 py-3 text-xs text-foreground-dim"><span className="block truncate">{file.source}</span></td><td className="px-4 py-3">{can("knowledge:delete") && <button onClick={() => setDeleting(file)} className="rounded-md p-2 text-foreground-dim hover:bg-danger/10 hover:text-danger" aria-label={`Delete ${file.filename}`}><Trash2 size={16} /></button>}</td></tr>; })}</tbody></table></div>}
      {!loading && !error && files.length > 0 && <div className="border-t border-card-border px-4 py-3 text-xs text-foreground-dim">{visibleFiles.length} of {files.length} source{files.length === 1 ? "" : "s"}</div>}
    </section>
    <Dialog open={Boolean(deleting)} onOpenChange={(open) => !open && !busy && setDeleting(null)}><DialogContent><DialogHeader><DialogTitle>Delete source?</DialogTitle><DialogDescription>This removes {deleting?.filename ?? "this source"} and its indexed knowledge from this workspace. This action cannot be undone.</DialogDescription></DialogHeader><DialogFooter><Button variant="ghost" onClick={() => setDeleting(null)} disabled={busy}>Cancel</Button><Button variant="destructive" onClick={() => void confirmDelete()} disabled={busy}>{busy ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />}Delete source</Button></DialogFooter></DialogContent></Dialog>
  </div>;
}
