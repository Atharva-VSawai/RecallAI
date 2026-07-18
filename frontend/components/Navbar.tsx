"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  Home,
  Activity,
  Search,
  LogIn,
  LogOut,
  Menu,
  X,
  Network,
  Zap,
  User,
  Mail,
  Shield,
  ChevronDown,
  Settings,
  Copy,
  Check,
} from "lucide-react";
import { motion, AnimatePresence, useMotionValue, useSpring } from "framer-motion";
import { checkHealth } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";

const links = [
  { href: "/", label: "Home", icon: Home },
  { href: "/query", label: "Query", icon: Search },
  { href: "/graph", label: "Graph", icon: Network },
  { href: "/activity", label: "Activity", icon: Activity },
];

function MagneticLink({
  href,
  label,
  icon: Icon,
  active,
  onClick,
}: {
  href: string;
  label: string;
  icon: React.ElementType;
  active: boolean;
  onClick?: () => void;
}) {
  const ref = useRef<HTMLAnchorElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 150, damping: 15, mass: 0.1 });
  const springY = useSpring(y, { stiffness: 150, damping: 15, mass: 0.1 });

  const handleMove = (e: React.MouseEvent) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    x.set((e.clientX - cx) * 0.18);
    y.set((e.clientY - cy) * 0.18);
  };

  const handleLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.div style={{ x: springX, y: springY }} className="relative">
      <Link
        ref={ref}
        href={href}
        onClick={onClick}
        onMouseMove={handleMove}
        onMouseLeave={handleLeave}
        className={`relative flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
          active ? "text-white" : "text-foreground-muted hover:text-foreground"
        }`}
      >
        {active && (
          <motion.div
            layoutId="nav-pill"
            className="absolute inset-0 rounded-full bg-gradient-to-r from-accent to-accent-2 shadow-lg shadow-accent/25"
            transition={{ type: "spring", stiffness: 350, damping: 30 }}
          />
        )}
        <span className="relative z-10 flex items-center gap-2">
          <Icon size={16} />
          {label}
        </span>
      </Link>
    </motion.div>
  );
}

/** Generates a gradient + initials avatar from an email */
function getAvatarProps(email: string | undefined | null) {
  const initials = email
    ? email
        .split("@")[0]
        .replace(/[^a-zA-Z0-9]/g, " ")
        .split(" ")
        .filter(Boolean)
        .slice(0, 2)
        .map((w) => w[0].toUpperCase())
        .join("")
    : "?";

  // Deterministic gradient from email char sum
  const sum = (email ?? "").split("").reduce((a, c) => a + c.charCodeAt(0), 0);
  const gradients = [
    "from-cyan-500 to-blue-600",
    "from-violet-500 to-purple-600",
    "from-pink-500 to-rose-600",
    "from-emerald-500 to-teal-600",
    "from-orange-500 to-amber-600",
    "from-indigo-500 to-cyan-500",
  ];
  const gradient = gradients[sum % gradients.length];
  return { initials, gradient };
}

/** Circular avatar button that opens a profile dropdown */
function UserAvatarMenu({
  email,
  onLogout,
}: {
  email: string | undefined | null;
  onLogout: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const { initials, gradient } = getAvatarProps(email);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const copyEmail = async () => {
    if (!email) return;
    await navigator.clipboard.writeText(email);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const displayName = email ? email.split("@")[0] : "User";
  const domain = email ? "@" + email.split("@")[1] : "";

  return (
    <div ref={menuRef} className="relative">
      {/* Avatar trigger */}
      <motion.button
        whileHover={{ scale: 1.07 }}
        whileTap={{ scale: 0.93 }}
        onClick={() => setOpen((v) => !v)}
        className="relative flex items-center gap-2 group focus:outline-none"
        aria-label="Open user menu"
      >
        {/* Avatar circle */}
        <div
          className={`relative w-9 h-9 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg ring-2 ring-white/10 group-hover:ring-accent/50 transition-all duration-200`}
        >
          <span className="text-white text-xs font-bold tracking-wide select-none">
            {initials}
          </span>
          {/* Online pulse */}
          <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-success rounded-full border-2 border-background shadow-sm" />
        </div>
        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown size={14} className="text-foreground-muted" />
        </motion.div>
      </motion.button>

      {/* Dropdown */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
            className="absolute right-0 top-[calc(100%+10px)] w-72 glass-strong border border-card-border-strong rounded-2xl shadow-2xl shadow-black/30 overflow-hidden z-50"
          >
            {/* Header — avatar + name */}
            <div className="relative p-4 pb-3">
              {/* Subtle gradient header bg */}
              <div
                className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-10 pointer-events-none`}
              />
              <div className="relative flex items-center gap-3">
                <div
                  className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-xl flex-shrink-0`}
                >
                  <span className="text-white text-base font-bold select-none">
                    {initials}
                  </span>
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-bold text-foreground truncate capitalize">
                    {displayName}
                  </p>
                  <p className="text-xs text-foreground-dim truncate">{domain}</p>
                  <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full bg-success/15 border border-success/30 text-success text-[10px] font-semibold">
                    <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                    Active
                  </span>
                </div>
              </div>
            </div>

            {/* Divider */}
            <div className="h-px bg-card-border mx-4" />

            {/* Details rows */}
            <div className="p-2 space-y-0.5">
              {/* Email row with copy */}
              <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-card-hover transition-colors group/row">
                <div className="w-7 h-7 rounded-lg bg-accent/10 flex items-center justify-center flex-shrink-0">
                  <Mail size={13} className="text-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[10px] text-foreground-dim font-semibold uppercase tracking-wider">
                    Email
                  </p>
                  <p className="text-xs text-foreground truncate">{email}</p>
                </div>
                <button
                  onClick={copyEmail}
                  className="opacity-0 group-hover/row:opacity-100 transition-opacity p-1 rounded-lg hover:bg-card"
                  title="Copy email"
                >
                  {copied ? (
                    <Check size={12} className="text-success" />
                  ) : (
                    <Copy size={12} className="text-foreground-muted" />
                  )}
                </button>
              </div>

              {/* Account type */}
              <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-card-hover transition-colors">
                <div className="w-7 h-7 rounded-lg bg-accent-2/10 flex items-center justify-center flex-shrink-0">
                  <User size={13} className="text-accent-2" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[10px] text-foreground-dim font-semibold uppercase tracking-wider">
                    Account
                  </p>
                  <p className="text-xs text-foreground">Standard User</p>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-accent-2/15 border border-accent-2/30 text-accent-2 text-[10px] font-bold">
                  USER
                </span>
              </div>

              {/* Security */}
              <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-card-hover transition-colors">
                <div className="w-7 h-7 rounded-lg bg-accent-3/10 flex items-center justify-center flex-shrink-0">
                  <Shield size={13} className="text-accent-3" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[10px] text-foreground-dim font-semibold uppercase tracking-wider">
                    Auth Provider
                  </p>
                  <p className="text-xs text-foreground">Supabase / Email</p>
                </div>
              </div>
            </div>

            {/* Divider */}
            <div className="h-px bg-card-border mx-4" />

            {/* Actions */}
            <div className="p-2">
              <Link
                href="/activity"
                onClick={() => setOpen(false)}
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-card-hover transition-colors w-full"
              >
                <div className="w-7 h-7 rounded-lg bg-card flex items-center justify-center flex-shrink-0">
                  <Settings size={13} className="text-foreground-muted" />
                </div>
                <span className="text-xs font-medium text-foreground">View My Activity</span>
              </Link>

              <button
                onClick={() => {
                  setOpen(false);
                  onLogout();
                }}
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-danger/10 transition-colors w-full group/logout mt-0.5"
              >
                <div className="w-7 h-7 rounded-lg bg-danger/10 flex items-center justify-center flex-shrink-0 group-hover/logout:bg-danger/20 transition-colors">
                  <LogOut size={13} className="text-danger" />
                </div>
                <span className="text-xs font-medium text-danger">Sign Out</span>
              </button>
            </div>

            {/* Footer */}
            <div className="px-4 py-2.5 border-t border-card-border bg-card/30">
              <p className="text-[10px] text-foreground-dim text-center">
                Recall.AI · Organizational Memory Engine
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function Navbar() {
  const path = usePathname();
  const router = useRouter();
  const { user } = useAuth();
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [llmProvider, setLlmProvider] = useState<"groq" | "ollama">("groq");

  useEffect(() => {
    const saved = localStorage.getItem("llm_provider") as "groq" | "ollama";
    if (saved) setLlmProvider(saved);
  }, []);

  const toggleProvider = () => {
    const next = llmProvider === "groq" ? "ollama" : "groq";
    setLlmProvider(next);
    localStorage.setItem("llm_provider", next);
  };

  useEffect(() => {
    const checkApiHealth = async () => {
      const isHealthy = await checkHealth();
      setHealthy(isHealthy);
    };
    checkApiHealth();
    const interval = setInterval(checkApiHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  const statusColor =
    healthy === null ? "bg-warning" : healthy ? "bg-success" : "bg-danger";
  const statusText =
    healthy === null ? "Checking..." : healthy ? "API Online" : "API Offline";

  const { initials, gradient } = getAvatarProps(user?.email);

  return (
    <motion.header
      initial={{ y: -24, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-500 ${
        scrolled ? "py-2" : "py-4"
      }`}
    >
      <nav
        className={`mx-4 md:mx-6 lg:mx-8 rounded-2xl border transition-all duration-500 ${
          scrolled
            ? "glass-strong shadow-2xl shadow-black/20 border-card-border-strong"
            : "glass border-card-border"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 md:px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2 group">
              <motion.div
                whileHover={{ scale: 1.05, rotate: -2 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                className="flex items-center gap-2"
              >
                <div className="relative">
                  <img
                    src="/logo2.png"
                    alt="Recall.AI"
                    className="h-10 w-auto object-contain relative z-10"
                  />
                  <div className="absolute inset-0 bg-accent/20 blur-xl rounded-full" />
                </div>
                <span className="font-display text-xl font-bold tracking-tight text-gradient hidden sm:block">
                  Recall.AI
                </span>
              </motion.div>
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center gap-1">
              {links.map(({ href, label, icon }) => (
                <MagneticLink
                  key={href}
                  href={href}
                  label={label}
                  icon={icon}
                  active={path === href}
                />
              ))}
            </div>

            {/* Right Section */}
            <div className="hidden md:flex items-center gap-3">
              {/* API status */}
              <motion.div
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.98 }}
                onClick={async () => {
                  setHealthy(null);
                  const isHealthy = await checkHealth();
                  setHealthy(isHealthy);
                }}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full glass-border cursor-pointer transition-colors hover:bg-card-hover"
                title="Click to refresh API status"
              >
                <motion.span
                  animate={
                    healthy ? { scale: [1, 1.3, 1], opacity: [1, 0.8, 1] } : {}
                  }
                  transition={{ duration: 2, repeat: Infinity }}
                  className={`w-2 h-2 rounded-full ${statusColor} shadow-[0_0_10px_currentColor]`}
                />
                <span className="text-xs font-semibold text-foreground-muted">
                  {statusText}
                </span>
              </motion.div>

              {/* LLM provider toggle */}
              <motion.div
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.98 }}
                onClick={toggleProvider}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full glass-border cursor-pointer transition-colors hover:bg-card-hover"
                title={`Currently using ${
                  llmProvider === "groq" ? "Groq (Cloud)" : "Ollama (Local)"
                }. Click to switch.`}
              >
                <div
                  className={`w-2 h-2 rounded-full ${
                    llmProvider === "ollama"
                      ? "bg-purple-500"
                      : "bg-orange-500"
                  } shadow-[0_0_10px_currentColor]`}
                />
                <span className="text-xs font-semibold text-foreground-muted uppercase tracking-wider">
                  {llmProvider}
                </span>
              </motion.div>

              <ThemeToggle />

              {/* Auth section */}
              {user ? (
                <UserAvatarMenu email={user.email} onLogout={handleLogout} />
              ) : (
                <Button
                  onClick={() => router.push("/login")}
                  size="sm"
                  className="btn-primary rounded-full gap-2"
                >
                  <LogIn size={16} />
                  <span>Login</span>
                </Button>
              )}
            </div>

            {/* Mobile Menu Button */}
            <div className="flex md:hidden items-center gap-2">
              <ThemeToggle />
              <motion.button
                whileTap={{ scale: 0.9 }}
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="h-10 w-10 rounded-full glass flex items-center justify-center text-foreground"
                aria-label="Toggle menu"
                aria-expanded={mobileMenuOpen}
              >
                {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
              </motion.button>
            </div>
          </div>
        </div>
      </nav>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.98 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="mx-4 md:mx-6 lg:mx-8 mt-2 rounded-2xl glass-strong border border-card-border-strong overflow-hidden"
          >
            <div className="p-4 space-y-2">
              {links.map(({ href, label, icon: Icon }, i) => (
                <motion.div
                  key={href}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <Link
                    href={href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                      path === href
                        ? "bg-gradient-to-r from-accent to-accent-2 text-white shadow-lg shadow-accent/25"
                        : "text-foreground-muted hover:text-foreground hover:bg-card"
                    }`}
                  >
                    <Icon size={18} />
                    {label}
                  </Link>
                </motion.div>
              ))}

              <div className="pt-3 border-t border-card-border-strong space-y-3">
                <div className="flex items-center justify-between px-4 py-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${statusColor} shadow-[0_0_10px_currentColor]`}
                    />
                    <span className="text-xs font-semibold text-foreground-muted">
                      {statusText}
                    </span>
                  </div>
                  <Zap size={14} className="text-foreground-dim" />
                </div>

                <div
                  className="flex items-center justify-between px-4 py-2 cursor-pointer hover:bg-card rounded-xl transition-colors"
                  onClick={toggleProvider}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        llmProvider === "ollama"
                          ? "bg-purple-500"
                          : "bg-orange-500"
                      } shadow-[0_0_10px_currentColor]`}
                    />
                    <span className="text-xs font-semibold text-foreground-muted uppercase">
                      Model: {llmProvider}
                    </span>
                  </div>
                  <span className="text-xs text-foreground-dim">Switch</span>
                </div>

                {/* Mobile user section */}
                {user ? (
                  <div className="space-y-2">
                    {/* User info card */}
                    <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-card/50 border border-card-border">
                      <div
                        className={`w-10 h-10 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg flex-shrink-0`}
                      >
                        <span className="text-white text-sm font-bold select-none">
                          {initials}
                        </span>
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-bold text-foreground truncate capitalize">
                          {user.email?.split("@")[0]}
                        </p>
                        <p className="text-xs text-foreground-dim truncate">
                          {user.email}
                        </p>
                      </div>
                    </div>

                    <Button
                      onClick={() => {
                        handleLogout();
                        setMobileMenuOpen(false);
                      }}
                      variant="outline"
                      className="w-full rounded-xl gap-2 border-danger/30 text-danger hover:bg-danger/10 hover:border-danger/50"
                    >
                      <LogOut size={18} />
                      Sign Out
                    </Button>
                  </div>
                ) : (
                  <Button
                    onClick={() => {
                      router.push("/login");
                      setMobileMenuOpen(false);
                    }}
                    className="w-full btn-primary rounded-xl gap-2"
                  >
                    <LogIn size={18} />
                    Login
                  </Button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
