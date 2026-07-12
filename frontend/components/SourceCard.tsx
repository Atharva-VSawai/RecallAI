import { Database, Search, GitBranch } from "lucide-react";
import { motion } from "framer-motion";
import type { SourceTrace } from "@/lib/api";

const toolMeta: Record<string, { label: string; badgeClass: string; icon: React.ElementType }> = {
  search_decisions: { label: "Neo4j", badgeClass: "badge-neo4j", icon: GitBranch },
  search_raw_memory: { label: "ChromaDB", badgeClass: "badge-chroma", icon: Database },
  find_related_decisions: { label: "Neo4j Graph", badgeClass: "badge-neo4j", icon: GitBranch },
  find_decisions_by_person: { label: "Neo4j", badgeClass: "badge-neo4j", icon: GitBranch },
};

export default function SourceCard({ trace }: { trace: SourceTrace }) {
  const meta = toolMeta[trace.tool] ?? { label: trace.tool, badgeClass: "badge-chroma", icon: Search };
  const Icon = meta.icon;

  return (
    <motion.div 
      className="glass-card rounded-lg p-4 space-y-2 hover:border-orange-400 transition-all cursor-pointer group"
      whileHover={{ scale: 1.02, y: -2 }}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="flex items-center gap-2">
        <motion.div
          whileHover={{ rotate: 360 }}
          transition={{ duration: 0.5 }}
        >
          <Icon size={14} className="text-gray-600 group-hover:text-orange-600 transition-colors" />
        </motion.div>
        <span className={`text-xs px-2 py-0.5 rounded-full border ${meta.badgeClass}`}>
          {meta.label}
        </span>
        <span className="text-xs text-gray-600 font-mono group-hover:text-gray-900 transition-colors">{trace.tool}</span>
      </div>
      {trace.args && Object.keys(trace.args).length > 0 && (
        <p className="text-xs text-gray-600">
          Query: <span className="text-gray-900 group-hover:text-orange-600 transition-colors">{Object.values(trace.args)[0] as string}</span>
        </p>
      )}
      {trace.result_preview && (
        <p className="text-xs text-gray-600 line-clamp-3 font-mono leading-relaxed group-hover:text-gray-800 transition-colors">
          {trace.result_preview}
        </p>
      )}
    </motion.div>
  );
}
