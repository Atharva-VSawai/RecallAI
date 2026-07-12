"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { MessageSquare, Search, Zap, FileText, Mail, RefreshCw } from "lucide-react";
import { getActivityFeed, type ActivityEvent } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

const eventMeta: Record<ActivityEvent["type"], { icon: React.ElementType; badgeClass: string; label: string }> = {
  slack: { icon: MessageSquare, badgeClass: "badge-slack", label: "Slack" },
  gmail: { icon: Mail, badgeClass: "badge-query", label: "Gmail" },
  query: { icon: Search, badgeClass: "badge-query", label: "Query" },
  impact: { icon: Zap, badgeClass: "badge-impact", label: "Impact" },
  ingest: { icon: FileText, badgeClass: "badge-chroma", label: "Ingest" },
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
      console.error('Failed to fetch events:', error);
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    fetchEvents();
    
    // Auto-refresh every 10 seconds
    const interval = setInterval(fetchEvents, 10000);
    
    return () => clearInterval(interval);
  }, [fetchEvents]);

  const handleRefresh = () => {
    setLoading(true);
    fetchEvents();
  };

  return (
    <div className="max-w-2xl mx-auto px-6 py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-10"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-1">Activity Feed</h1>
            <p className="text-sm text-gray-600">
              Recent ingestions, queries, and AI agent activity.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </span>
            <motion.button
              onClick={handleRefresh}
              disabled={loading}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="flex items-center gap-2 px-3 py-2 rounded-full bg-blue-100 hover:bg-blue-200 text-blue-700 text-sm font-medium transition-colors disabled:opacity-50 border border-blue-200"
            >
              <motion.div
                animate={loading ? { rotate: 360 } : {}}
                transition={{ duration: 1, repeat: loading ? Infinity : 0, ease: "linear" }}
              >
                <RefreshCw size={14} />
              </motion.div>
              {loading ? "Refreshing..." : "Refresh"}
            </motion.button>
          </div>
        </div>
      </motion.div>

      <div className="relative">
        {/* Timeline vertical line */}
        <div className="absolute left-5 top-0 bottom-0 w-px timeline-line" />

        <div className="space-y-1">
          {events.map((event, i) => {
            const meta = eventMeta[event.type];
            const Icon = meta.icon;

            return (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08, duration: 0.4 }}
                className="relative flex gap-5 pb-8"
              >
                {/* Icon dot */}
                <div className="relative z-10 shrink-0 w-10 h-10 rounded-full glass-card border border-gray-200 flex items-center justify-center">
                  <Icon size={15} className="text-gray-600" />
                </div>

                {/* Content */}
                <div className="flex-1 glass-card rounded-xl p-4 border border-gray-200 hover:border-blue-400 transition-colors">
                  <div className="flex items-start justify-between gap-3 mb-1.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${meta.badgeClass}`}>
                        {meta.label}
                      </span>
                      <span className="text-sm font-medium text-gray-900">{event.title}</span>
                    </div>
                    <span className="text-xs text-gray-600 shrink-0">{timeAgo(event.timestamp)}</span>
                  </div>
                  <p className="text-xs text-gray-600">{event.description}</p>
                  {event.source && (
                    <p className="text-xs text-blue-600/70 mt-1 font-mono">{event.source}</p>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {events.length === 0 && !loading && (
        <div className="text-center text-gray-600 text-sm py-20">
          No activity yet. Start by querying or ingesting data.
        </div>
      )}
      
      {loading && events.length === 0 && (
        <div className="text-center text-gray-600 text-sm py-20">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            className="inline-block mb-2"
          >
            <RefreshCw size={20} />
          </motion.div>
          <div>Loading activity...</div>
        </div>
      )}
    </div>
  );
}
