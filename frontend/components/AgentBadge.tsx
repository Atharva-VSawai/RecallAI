import { Zap, Search } from "lucide-react";
import { motion } from "framer-motion";

export default function AgentBadge({ agent }: { agent: "QUERY" | "IMPACT" }) {
  const isImpact = agent === "IMPACT";
  return (
    <motion.span
      initial={{ scale: 0, rotate: -180 }}
      animate={{ scale: 1, rotate: 0 }}
      transition={{ type: "spring", stiffness: 200, damping: 15 }}
      whileHover={{ scale: 1.1, rotate: 5 }}
      className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border font-medium cursor-default ${
        isImpact ? "badge-impact" : "badge-query"
      }`}
    >
      <motion.div
        animate={{ rotate: [0, 10, -10, 0] }}
        transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
      >
        {isImpact ? <Zap size={11} /> : <Search size={11} />}
      </motion.div>
      {isImpact ? "Impact Agent" : "Query Agent"}
    </motion.span>
  );
}
