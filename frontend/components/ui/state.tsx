import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: { href: string; label: string };
};

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return <div className="empty-state">
    <span className="empty-state-icon"><Icon size={19} /></span>
    <p className="empty-state-title">{title}</p>
    <p className="empty-state-description">{description}</p>
    {action && <Button asChild size="sm" className="mt-4"><Link href={action.href}>{action.label}</Link></Button>}
  </div>;
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return <div className="flex min-h-48 items-center justify-center gap-2 text-sm text-foreground-muted"><Loader2 size={16} className="animate-spin text-accent" />{label}</div>;
}

export function ErrorState({ title = "We couldn’t load this data.", onRetry }: { title?: string; onRetry?: () => void }) {
  return <div className="flex min-h-48 flex-col items-center justify-center px-5 text-center"><AlertCircle size={22} className="text-danger" /><p className="mt-3 text-sm text-foreground">{title}</p><p className="mt-1 text-xs text-foreground-muted">Try again in a moment. If the problem continues, contact your administrator.</p>{onRetry && <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>Retry</Button>}</div>;
}
