"use client";

import React, { useEffect, useState } from "react";
import { useTheme } from "@/components/theme-provider";
import { Sun, Moon } from "lucide-react";

export const ThemeToggle: React.FC = () => {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="w-9 h-9 rounded-xl bg-primary-100/50 border border-primary-200 animate-pulse" />
    );
  }

  const isDark = resolvedTheme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="p-2 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 hover:bg-primary-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 transition-all shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-400 flex items-center justify-center"
      title={isDark ? "Chuyển sang Giao diện Sáng (Light Mode)" : "Chuyển sang Giao diện Tối (Dark Mode)"}
    >
      {isDark ? (
        <Sun className="w-4 h-4 stroke-current text-amber-400" />
      ) : (
        <Moon className="w-4 h-4 stroke-current text-slate-700" />
      )}
    </button>
  );
};
