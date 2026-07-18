"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, Search, Zap, FileText, Mail, RefreshCw, Activity } from "lucide-react";
import { getActivityFeed, type ActivityEvent } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

const eventMeta: Record<
  ActivityEvent["type"],
  { icon: React.ElementType; color: string; bgGradient: string; label: string }
> = {
  slack: {
    icon: MessageSquare,
    color: "text-accent",
    bgGradient: "from-accent to-accent-2",
    label: "Slack",
  },
  gmail: {
    icon: Mail,
    color: "text-accent-2",
    bgGradient: "from-accent-2 to-accent-3",
    label: "Gmail",
  },
  query: {
    icon: Search,
    color: "text-accent-3",
    bgGradient: "from-accent-3 to-accent",
    label: "Query",
  },
  impact: {
    icon: Zap,
    color: "text-warning",
    bgGradient: "from-warning to-accent",
    label: "Impact",
  },
  ingest: {
    icon: FileText,
    color: "text-success",
    bgGradient: "from-success to-accent",
    label: "Ingest",
  },
};

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
}

export default function ActivityPage() {
  const { user } = useAuth();
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchEvents = useCallback(async () => {
    try {
      const newEvents = await getActivityFeed(user?.id);
      setEvents(newEvents);
      setLastRefresh(new Date());
    } catch (error) {
      console.error("Failed to fetch events:", error);
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    fetchEvents();
    const interval = setInterval(fetchEvents, 10000);
    return () => clearInterval(interval);
  }, [fetchEvents]);

  const handleRefresh = () => {
    setLoading(true);
    fetchEvents();
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Ambient orbs */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="orb orb-cyan w-[400px] h-[400px] -top-32 -right-32 opacity-30" />
        <div className="orb orb-violet w-[400px] h-[400px] -bottom-32 -left-32 opacity-20" />
      </div>

      <div className="relative z-10 max-w-2xl mx-auto px-6 py-32">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="mb-10"
        >
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="inline-flex items-center gap-2 glass rounded-full px-4 py-1.5 text-xs font-semibold text-foreground-muted border border-card-border mb-4">
                <Activity size={12} className="text-accent" />
                Live Feed
              </div>
              <h1 className="text-3xl md:text-4xl font-black font-display text-foreground mb-2">
                Activity <span className="text-gradient">Feed</span>
              </h1>
              <p className="text-foreground-muted text-sm">
                Recent ingestions, queries, and AI agent activity.
              </p>
            </div>

            <div className="flex flex-col items-end gap-2">
              <span className="text-xs text-foreground-dim">
                Updated: {lastRefresh.toLocaleTimeString()}
              </span>
              <motion.button
                onClick={handleRefresh}
                disabled={loading}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="btn-secondary flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium disabled:opacity-50"
              >
                <motion.div
                  animate={loading ? { rotate: 360 } : {}}
                  transition={{ duration: 1, repeat: loading ? Infinity : 0, ease: "linear" }}
                >
                  <RefreshCw size={14} />
                </motion.div>
                {loading ? "Refreshing…" : "Refresh"}
              </motion.button>
            </div>
          </div>
        </motion.div>

        {/* Timeline */}
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-5 top-0 bottom-0 w-px bg-gradient-to-b from-accent/40 via-accent-2/30 to-transparent" />

          <AnimatePresence>
            <div className="space-y-2">
              {events.map((event, i) => {
                const meta = eventMeta[event.type];
                const Icon = meta.icon;

                return (
                  <motion.div
                    key={event.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.06, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                    className="relative flex gap-5 pb-6"
                  >
                    {/* Icon dot */}
                    <div className={`relative z-10 shrink-0 w-10 h-10 rounded-full bg-gradient-to-br ${meta.bgGradient} flex items-center justify-center shadow-lg shadow-accent/20`}>
                      <Icon size={15} className="text-white" />
                    </div>

                    {/* Card */}
                    <motion.div
                      whileHover={{ y: -2, borderColor: "var(--card-border-strong)" }}
                      transition={{ duration: 0.25 }}
                      className="flex-1 glass rounded-xl p-4 border border-card-border"
                    >
                      <div className="flex items-start justify-between gap-3 mb-1.5">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`text-xs px-2.5 py-0.5 rounded-full glass border border-card-border font-semibold ${meta.color}`}>
                            {meta.label}
                          </span>
                          <span className="text-sm font-semibold text-foreground">
                            {event.title}
                          </span>
                        </div>
                        <span className="text-xs text-foreground-dim shrink-0">
                          {timeAgo(event.timestamp)}
                        </span>
                      </div>
                      <p className="text-xs text-foreground-muted leading-relaxed">
                        {event.description}
                      </p>
                      {event.source && (
                        <p className="text-xs text-accent mt-1.5 font-mono opacity-75">
                          {event.source}
                        </p>
                      )}
                    </motion.div>
                  </motion.div>
                );
              })}
            </div>
          </AnimatePresence>
        </div>

        {/* Empty state */}
        {events.length === 0 && !loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-24"
          >
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl glass border border-card-border mb-4">
              <Activity size={28} className="text-foreground-dim" />
            </div>
            <p className="text-foreground-muted text-sm">
              No activity yet. Start by querying or ingesting data.
            </p>
          </motion.div>
        )}

        {/* Loading state */}
        {loading && events.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-24 flex flex-col items-center gap-3"
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            >
              <RefreshCw size={24} className="text-accent" />
            </motion.div>
            <p className="text-foreground-muted text-sm">Loading activity…</p>
          </motion.div>
        )}
      </div>
    </div>
  );
}
