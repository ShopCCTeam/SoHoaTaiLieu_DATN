"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth/session";
import { RoleSwitcher } from "./role-switcher";
import { ThemeToggle } from "./theme-toggle";
import { Search, LogOut, User as UserIcon, Database, Menu } from "lucide-react";

interface TopbarProps {
  onToggleMobileSidebar?: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ onToggleMobileSidebar }) => {
  const { user, logout } = useAuthStore();
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isMock = process.env.NEXT_PUBLIC_API_MODE !== "live";

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <header className="h-16 sticky top-0 z-20 glass-panel border-b border-primary-200/80 dark:border-slate-800 px-4 md:px-6 flex items-center justify-between gap-3">
      {/* Mobile Toggle Button */}
      <button
        onClick={onToggleMobileSidebar}
        aria-label="Mở menu điều hướng mobile"
        className="md:hidden p-2 rounded-xl border border-primary-200 text-slate-700 dark:text-slate-300 hover:bg-primary-100 transition-colors"
        title="Mở menu"
      >
        <Menu className="w-5 h-5 stroke-current" />
      </button>

      {/* Global Search Bar */}
      <form onSubmit={handleSearchSubmit} className="flex-1 max-w-md relative">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 stroke-current text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm kiếm tài liệu Công tác sinh viên, quy chế, học bổng..."
            className="w-full h-10 pl-10 pr-4 rounded-xl border border-primary-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/70 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary-400 transition-all shadow-sm"
          />
        </div>
      </form>

      {/* Right Action Items */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Theme Toggle Button (Light / Dark Mode) */}
        <ThemeToggle />

        {/* API Mode Indicator Badge */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-primary-200/80 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 text-[11px] font-medium text-slate-700 dark:text-slate-300">
          <Database className="w-3.5 h-3.5 stroke-current text-primary-600 dark:text-primary-400" />
          <span>API:</span>
          <span className={`font-bold px-1.5 py-0.2 rounded text-[10px] ${isMock ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300" : "bg-emerald-100 text-emerald-800"}`}>
            {isMock ? "MOCK" : "LIVE"}
          </span>
        </div>

        {/* Role Switcher Component */}
        <RoleSwitcher />

        {/* User Info & Logout */}
        {mounted && user ? (
          <div className="flex items-center gap-2 pl-2 border-l border-primary-200 dark:border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary-300 to-rose-400 flex items-center justify-center text-slate-950 font-bold text-xs shadow-sm flex-shrink-0">
                <UserIcon className="w-4 h-4 stroke-current" />
              </div>
              <div className="hidden xl:flex flex-col text-left">
                <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 leading-tight">
                  {user.fullName}
                </span>
                <span className="text-[10px] text-muted-foreground truncate max-w-[140px]">
                  {user.email}
                </span>
              </div>
            </div>

            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              aria-label="Đăng xuất khỏi hệ thống"
              className="p-2 rounded-xl text-slate-500 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-slate-800 transition-colors ml-1"
              title="Đăng xuất"
            >
              <LogOut className="w-4 h-4 stroke-current" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => router.push("/login")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-primary-400 text-slate-900 text-xs font-semibold hover:bg-primary-500 transition-all shadow-sm"
          >
            <UserIcon className="w-3.5 h-3.5 stroke-current" />
            <span>Đăng nhập</span>
          </button>
        )}
      </div>
    </header>
  );
};
