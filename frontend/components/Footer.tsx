"use client";

import { usePathname } from "next/navigation";

export default function Footer() {
  const pathname = usePathname();
  if (["/", "/login", "/signup", "/forgot-password", "/graph"].includes(pathname)) return null;
  return (
    <footer className="app-footer border-t border-card-border bg-background-secondary px-4 py-3 text-xs text-foreground-dim md:px-8">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <span>© {new Date().getFullYear()} Recall.AI</span>
        <span>Enterprise knowledge platform</span>
      </div>
    </footer>
  );
}
