"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, ChevronDown, CircleHelp, Database, FileSearch, FolderOpen, GitBranch, LayoutDashboard, LogOut, Menu, Moon, PanelLeftClose, PanelLeftOpen, Settings, ShieldCheck, Sun, UserCircle, Users, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { checkHealth } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import WorkspaceManager from "@/components/WorkspaceManager";
import { useTheme } from "@/contexts/ThemeContext";

const workspaceNavigation = [
  ["/", "Overview", LayoutDashboard],
  ["/query", "Ask knowledge", FileSearch],
  ["/graph", "Knowledge graph", GitBranch],
  ["/teams", "Teams", Users],
  ["/activity", "Activity", ShieldCheck],
] as const;

const managementNavigation = [
  ["/sources", "Sources", FolderOpen],
  ["/settings", "Settings", Settings],
] as const;

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === href : pathname.startsWith(href);
}

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, projects, activeProject, setActiveProjectId } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [workspaceOpen, setWorkspaceOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [managerOpen, setManagerOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => typeof window !== "undefined" && localStorage.getItem("recallai_sidebar_collapsed") === "true");
  const [width, setWidth] = useState(() => {
    if (typeof window === "undefined") return 240;
    const savedWidth = Number(localStorage.getItem("recallai_sidebar_width"));
    return savedWidth >= 200 && savedWidth <= 360 ? savedWidth : 240;
  });
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const resizing = useRef(false);
  const workspaceRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    document.documentElement.style.setProperty("--sidebar-width", `${collapsed ? 64 : width}px`);
    localStorage.setItem("recallai_sidebar_collapsed", String(collapsed));
    localStorage.setItem("recallai_sidebar_width", String(width));
  }, [collapsed, width]);

  useEffect(() => { void checkHealth().then(setHealthy); }, []);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      const target = event.target as Node;
      if (profileRef.current && !profileRef.current.contains(target)) setProfileOpen(false);
      if (workspaceRef.current && !workspaceRef.current.contains(target)) setWorkspaceOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        router.push("/query");
      }
    };
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, [router]);

  useEffect(() => {
    const move = (event: MouseEvent) => {
      if (resizing.current) setWidth(Math.min(360, Math.max(200, event.clientX)));
    };
    const stopResize = () => { resizing.current = false; document.body.style.cursor = ""; };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", stopResize);
    return () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", stopResize); };
  }, []);

  const logout = async () => { await supabase.auth.signOut(); router.push("/login"); };
  const openManager = () => { setWorkspaceOpen(false); setProfileOpen(false); setManagerOpen(true); };

  if (!user && ["/", "/login", "/signup", "/forgot-password"].includes(pathname)) return null;
  const sidebarWidth = mobileOpen ? 280 : collapsed ? 64 : width;

  return <>
    <header className="fixed inset-x-0 top-0 z-50 h-16 border-b border-card-border bg-background-secondary">
      <div className="flex h-full items-center gap-2 px-3 sm:gap-3 sm:px-4">
        <button className="rounded-md p-2 text-foreground-muted hover:bg-card hover:text-foreground md:hidden" onClick={() => setMobileOpen((open) => !open)} aria-label="Toggle navigation" aria-expanded={mobileOpen}>{mobileOpen ? <X size={18} /> : <Menu size={18} />}</button>
        <Link href="/" className="flex shrink-0 items-center gap-2 border-r border-card-border pr-3" aria-label="Recall.AI home"><span className="grid h-7 w-7 place-items-center rounded-md bg-accent text-xs font-bold text-white">R</span><span className="hidden text-sm font-semibold tracking-tight xs:inline">Recall<span className="text-accent">.AI</span></span></Link>
        <div ref={workspaceRef} className="relative hidden min-w-48 md:block">
          <button onClick={() => setWorkspaceOpen((open) => !open)} className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-card" aria-expanded={workspaceOpen} aria-haspopup="menu"><Database size={15} className="text-accent" /><span className="min-w-0 flex-1 truncate text-xs font-semibold">{activeProject?.name ?? "Select workspace"}</span><ChevronDown size={14} className="text-foreground-dim" /></button>
          {workspaceOpen && <div className="absolute left-0 top-10 w-64 rounded-lg border border-card-border bg-card p-1 shadow-xl" role="menu">
            {projects.length ? projects.map((project) => <button key={project.id} onClick={() => { setActiveProjectId(project.id); setWorkspaceOpen(false); }} className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-xs ${project.id === activeProject?.id ? "bg-accent/10 text-accent" : "text-foreground-muted hover:bg-surface-elevated hover:text-foreground"}`} role="menuitem"><span className={`h-1.5 w-1.5 rounded-full ${project.id === activeProject?.id ? "bg-accent" : "bg-foreground-dim"}`} /><span className="truncate">{project.name}</span></button>) : <p className="px-3 py-2 text-xs text-foreground-dim">No workspaces available.</p>}
            <div className="my-1 border-t border-card-border" />
            <button onClick={openManager} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-xs font-medium text-accent hover:bg-accent/10" role="menuitem">Manage workspaces</button>
          </div>}
        </div>
        <Link href="/query" className="hidden min-w-0 flex-1 items-center md:flex"><span className="flex w-full max-w-xl items-center gap-2 rounded-md border border-card-border bg-background px-3 py-1.5 text-xs text-foreground-dim transition-colors hover:border-card-border-strong"><FileSearch size={14} />Search knowledge <kbd className="ml-auto rounded border border-card-border px-1.5 py-0.5 font-mono text-[10px]">⌘ K</kbd></span></Link>
        <div className="ml-auto flex items-center gap-1"><button className="rounded-md p-2 text-foreground-muted hover:bg-card hover:text-foreground" aria-label="Help"><CircleHelp size={17} /></button><button className="rounded-md p-2 text-foreground-muted hover:bg-card hover:text-foreground" aria-label="Notifications"><Bell size={17} /></button><button onClick={toggleTheme} className="rounded-md p-2 text-foreground-muted hover:bg-card hover:text-foreground" aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`} title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}>{theme === "light" ? <Moon size={17} /> : <Sun size={17} />}</button>
          <div ref={profileRef} className="relative ml-1"><button onClick={() => setProfileOpen((open) => !open)} className="grid h-8 w-8 place-items-center rounded-md bg-accent/15 text-xs font-semibold text-accent hover:bg-accent/25 focus:outline-none focus:ring-2 focus:ring-accent/50" aria-label="Open profile menu" aria-expanded={profileOpen} aria-haspopup="menu">{user?.email?.[0]?.toUpperCase() ?? "A"}</button>
            {profileOpen && <div className="absolute right-0 top-10 w-64 rounded-lg border border-card-border bg-card p-1 shadow-xl" role="menu"><div className="border-b border-card-border px-3 py-3"><p className="truncate text-xs font-semibold text-foreground">{user?.email ?? "Account"}</p><p className="mt-1 truncate text-[11px] text-foreground-dim">{activeProject?.name ?? "No active workspace"}</p></div><Link href="/settings" onClick={() => setProfileOpen(false)} className="flex items-center gap-2 rounded-md px-3 py-2 text-xs text-foreground-muted hover:bg-surface-elevated hover:text-foreground" role="menuitem"><UserCircle size={15} />Profile & settings</Link><button onClick={openManager} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-xs text-foreground-muted hover:bg-surface-elevated hover:text-foreground" role="menuitem"><Database size={15} />Manage workspaces</button><button onClick={logout} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-xs text-danger hover:bg-danger/10" role="menuitem"><LogOut size={15} />Sign out</button></div>}
          </div>
        </div>
      </div>
    </header>
    {mobileOpen && <button className="fixed inset-0 top-16 z-30 bg-slate-900/20 md:hidden" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <aside style={{ width: sidebarWidth }} className={`${mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"} fixed bottom-0 left-0 top-16 z-40 border-r border-card-border bg-background-secondary transition-[width,transform] duration-150`}>
      <div className="flex h-full min-w-0 flex-col px-2 py-3"><div className="mb-3 flex items-center justify-between px-1"><span className={`text-[10px] font-semibold uppercase tracking-wider text-foreground-dim ${collapsed && !mobileOpen ? "sr-only" : ""}`}>Workspace</span><button onClick={() => setCollapsed((value) => !value)} className="hidden rounded-md p-1.5 text-foreground-dim hover:bg-card hover:text-foreground md:block" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>{collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}</button></div>
        <nav className="min-h-0 space-y-0.5 overflow-y-auto" aria-label="Workspace navigation">{workspaceNavigation.map(([href, label, Icon]) => <Link title={collapsed && !mobileOpen ? label : undefined} key={href} href={href} onClick={() => setMobileOpen(false)} aria-current={isActive(pathname, href) ? "page" : undefined} className={`flex items-center gap-3 rounded-md px-2 py-2 text-sm ${isActive(pathname, href) ? "bg-accent/15 font-medium text-accent" : "text-foreground-muted hover:bg-card hover:text-foreground"}`}><Icon className="shrink-0" size={16} />{(!collapsed || mobileOpen) && <span className="truncate">{label}</span>}</Link>)}</nav>
        <div className="my-4 border-t border-card-border" /><p className={`mb-2 px-1 text-[10px] font-semibold uppercase tracking-wider text-foreground-dim ${collapsed && !mobileOpen ? "sr-only" : ""}`}>Manage</p>
        <nav className="space-y-0.5" aria-label="Management navigation">{managementNavigation.map(([href, label, Icon]) => <Link title={collapsed && !mobileOpen ? label : undefined} key={href} href={href} onClick={() => setMobileOpen(false)} aria-current={isActive(pathname, href) ? "page" : undefined} className={`flex items-center gap-3 rounded-md px-2 py-2 text-sm ${isActive(pathname, href) ? "bg-accent/15 font-medium text-accent" : "text-foreground-muted hover:bg-card hover:text-foreground"}`}><Icon className="shrink-0" size={16} />{(!collapsed || mobileOpen) && <span>{label}</span>}</Link>)}</nav>
        <div className="mt-auto space-y-2"><div title={healthy === null ? "Checking API" : healthy ? "API available" : "API unavailable"} className="flex items-center gap-2 rounded-md border border-card-border bg-card px-2 py-2"><span className={`h-2 w-2 shrink-0 rounded-full ${healthy === null ? "bg-foreground-dim" : healthy ? "bg-success" : "bg-danger"}`} />{(!collapsed || mobileOpen) && <span className="truncate text-[11px] text-foreground-muted">{healthy === null ? "Checking API" : healthy ? "API available" : "API unavailable"}</span>}</div><button title={collapsed && !mobileOpen ? "Sign out" : undefined} onClick={logout} className="flex w-full items-center gap-3 rounded-md px-2 py-2 text-sm text-foreground-muted hover:bg-card hover:text-foreground"><LogOut className="shrink-0" size={16} />{(!collapsed || mobileOpen) && "Sign out"}</button></div>
      </div>
      {!collapsed && <button onMouseDown={() => { resizing.current = true; document.body.style.cursor = "col-resize"; }} className="absolute -right-1 top-0 hidden h-full w-2 cursor-col-resize md:block" aria-label="Resize sidebar"><span className="absolute bottom-1/2 left-0 h-8 w-px bg-transparent hover:bg-accent" /></button>}
    </aside>
    {managerOpen && <WorkspaceManager onClose={() => setManagerOpen(false)} />}
  </>;
}
