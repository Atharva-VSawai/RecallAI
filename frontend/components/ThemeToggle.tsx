"use client";

import { motion } from "framer-motion";
import { Sun, Moon } from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";

export function ThemeToggle() {
  const { resolvedTheme, toggleTheme } = useTheme();
  const isLight = resolvedTheme === "light";

  return (
    <motion.button
      onClick={toggleTheme}
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.92 }}
      aria-label={isLight ? "Switch to dark mode" : "Switch to light mode"}
      className="relative h-10 w-10 rounded-full glass flex items-center justify-center overflow-hidden glow-accent"
    >
      <motion.div
        initial={false}
        animate={{ rotate: isLight ? 180 : 0, scale: isLight ? 0 : 1, opacity: isLight ? 0 : 1 }}
        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
        className="absolute"
      >
        <Moon size={18} className="text-foreground" />
      </motion.div>

      <motion.div
        initial={false}
        animate={{ rotate: isLight ? 0 : -180, scale: isLight ? 1 : 0, opacity: isLight ? 1 : 0 }}
        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
        className="absolute"
      >
        <Sun size={18} className="text-foreground" />
      </motion.div>

      {/* sheen */}
      <span className="absolute inset-0 rounded-full bg-gradient-to-tr from-accent/0 via-white/10 to-accent/0 opacity-0 hover:opacity-100 transition-opacity duration-300" />
    </motion.button>
  );
}
