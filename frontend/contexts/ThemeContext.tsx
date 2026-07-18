"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";

type Theme = "dark" | "light";

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: Exclude<Theme, "system">;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const STORAGE_KEY = "recallai-theme";

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const stored = typeof window !== "undefined" ? (localStorage.getItem(STORAGE_KEY) as Theme | null) : null;
    const initial = stored ?? "dark";
    setThemeState(initial);
    applyTheme(initial);
  }, []);

  const applyTheme = (next: Theme) => {
    const root = document.documentElement;
    if (next === "light") {
      root.classList.add("light");
    } else {
      root.classList.remove("light");
    }
  };

  const setTheme = (next: Theme) => {
    setThemeState(next);
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
  };

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
  };

  return (
    <ThemeContext.Provider
      value={{
        theme,
        resolvedTheme: theme,
        toggleTheme,
        setTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}

/* Inline script helper — place in <head> of layout.tsx to avoid flash */
export const themeInitScript = `
  (function() {
    try {
      const theme = localStorage.getItem("${STORAGE_KEY}") || "dark";
      if (theme === "light") document.documentElement.classList.add("light");
      else document.documentElement.classList.remove("light");
    } catch (e) {}
  })();
`;
