import { Database, GitBranch, Search } from "lucide-react";
import type { SourceTrace } from "@/lib/api";

const toolMeta: Record<string, { label: string; icon: typeof Search }> = {
  search_decisions: { label: "Knowledge graph", icon: GitBranch },
  search_raw_memory: { label: "Knowledge source", icon: Database },
  find_related_decisions: { label: "Knowledge graph", icon: GitBranch },
  find_decisions_by_person: { label: "Knowledge graph", icon: GitBranch },
};

export default function SourceCard({ trace }: { trace: SourceTrace }) {
  const meta = toolMeta[trace.tool] ?? { label: "Knowledge source", icon: Search };
  const Icon = meta.icon;
  const searchText = trace.args?.query ?? trace.args?.topic ?? trace.args?.person_name ?? "";
  return <article className="rounded-md border border-card-border bg-card p-4"><div className="flex items-center gap-2"><span className="grid h-7 w-7 place-items-center rounded-md bg-surface-elevated text-foreground-muted"><Icon size={14} /></span><span className="text-xs font-medium text-foreground">{meta.label}</span></div>{searchText && <p className="mt-3 text-xs text-foreground-muted">Query: <span className="text-foreground">{String(searchText)}</span></p>}{trace.result_preview && <p className="mt-2 line-clamp-3 text-xs leading-5 text-foreground-muted">{trace.result_preview}</p>}</article>;
}
