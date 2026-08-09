"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useAuthStore } from "@/lib/auth/session";
import { hasPermission } from "@/lib/auth/permissions";
import {
  LayoutDashboard,
  FileText,
  Search,
  MessageSquare,
  Users,
  Cpu,
  BookOpen,
  Sparkles,
  Upload,
  PanelLeftClose,
  PanelLeftOpen,
  User as UserIcon,
} from "lucide-react";

export const Sidebar: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);
  const pathname = usePathname();
  const { user } = useAuthStore();

  const canAccessAdmin = hasPermission(user?.role, "canAccessAdminPanel");

  // NEED-FIX 4.2: Read & Persist collapse state in localStorage
  useEffect(() => {
    setMounted(true);
    try {
      const stored = localStorage.getItem("sidebar_collapsed");
      if (stored !== null) {
        setIsCollapsed(stored === "true");
      }
    } catch {
      // Ignore SSR errors
    }
  }, []);

  const handleToggleCollapse = () => {
    const nextState = !isCollapsed;
    setIsCollapsed(nextState);
    try {
      localStorage.setItem("sidebar_collapsed", String(nextState));
    } catch {
      // Ignore
    }
  };

  // Global Keyboard Shortcut listener: Ctrl+[ or Cmd+[ to toggle collapse
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "[") {
        e.preventDefault();
        handleToggleCollapse();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isCollapsed]);

  const navItems = [
    {
      title: "Tổng quan",
      href: "/dashboard",
      icon: <LayoutDashboard className="w-5 h-5 stroke-current flex-shrink-0" />,
      badge: null,
    },
    {
      title: "Danh sách Tài liệu",
      href: "/documents",
      icon: <FileText className="w-5 h-5 stroke-current flex-shrink-0" />,
      badge: null,
    },
    {
      title: "Upload & Số hóa",
      href: "/documents/upload",
      icon: <Upload className="w-5 h-5 stroke-current flex-shrink-0" />,
      badge: "Mới",
    },
    {
      title: "Tra cứu Thông minh",
      href: "/search",
      icon: <Search className="w-5 h-5 stroke-current flex-shrink-0" />,
      badge: null,
    },
    {
      title: "Trợ lý AI Chatbot",
      href: "/chat",
      icon: <MessageSquare className="w-5 h-5 stroke-current flex-shrink-0" />,
      badge: "RAG",
    },
  ];

  const adminItems = [
    {
      title: "Quản lý User & Role",
      href: "/admin/users",
      icon: <Users className="w-5 h-5 stroke-current flex-shrink-0" />,
    },
    {
      title: "Quản lý Models & RAG",
      href: "/admin/models",
      icon: <Cpu className="w-5 h-5 stroke-current flex-shrink-0" />,
    },
  ];

  const checkIsActive = (href: string) => {
    if (href === "/documents") {
      return pathname === "/documents" || (pathname.startsWith("/documents/") && !pathname.startsWith("/documents/upload"));
    }
    if (href === "/dashboard") {
      return pathname === "/dashboard" || pathname === "/";
    }
    return pathname === href || pathname.startsWith(href + "/");
  };

  return (
    <motion.aside
      animate={{ width: isCollapsed ? 76 : 270 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="relative h-screen sticky top-0 flex flex-col glass-panel border-r border-primary-200/60 dark:border-slate-800/80 z-30 select-none shadow-glass overflow-hidden"
    >
      {/* Brand Header */}
      <div className={`h-16 flex items-center border-b border-primary-100/80 dark:border-slate-800/80 ${isCollapsed ? "justify-center px-2" : "px-4"}`}>
        <Link href="/dashboard" aria-label="Trang chủ Dashboard" className="flex items-center gap-3 overflow-hidden min-w-0">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-300 to-rose-300 dark:from-primary-700 dark:to-rose-800 flex items-center justify-center text-slate-900 dark:text-white shadow-sm flex-shrink-0">
            <BookOpen className="w-5 h-5 stroke-current" />
          </div>
          <AnimatePresence>
            {!isCollapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                className="flex flex-col whitespace-nowrap overflow-hidden"
              >
                <span className="font-extrabold text-sm tracking-tight text-slate-900 dark:text-white leading-tight truncate">
                  Số hóa CTSV
                </span>
                <span className="text-[10px] text-primary-700 dark:text-primary-300 font-medium tracking-wide truncate">
                  OCR & RAG LangChain
                </span>
              </motion.div>
            )}
          </AnimatePresence>
        </Link>
      </div>

      {/* Nav Content */}
      <div className="flex-1 overflow-y-auto px-2 sm:px-3 py-4 space-y-6">
        {/* Main Section */}
        <div>
          {!isCollapsed && (
            <div className="px-3 mb-2 text-[10px] font-bold tracking-wider text-slate-500 dark:text-slate-400 uppercase">
              Menu chính
            </div>
          )}
          <nav className="space-y-1">
            {navItems.map((item) => {
              const isActive = checkIsActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-label={item.title}
                  className={`relative flex items-center gap-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                    isCollapsed ? "justify-center px-0 w-11 h-11 mx-auto" : "px-3"
                  } ${
                    isActive
                      ? "bg-primary-200/90 dark:bg-primary-900/40 text-slate-900 dark:text-primary-100 font-bold border border-primary-300/60 dark:border-primary-700/50 shadow-sm"
                      : "text-slate-700 dark:text-slate-300 hover:bg-primary-100/50 dark:hover:bg-slate-800/60"
                  }`}
                  title={isCollapsed ? item.title : undefined}
                >
                  {item.icon}
                  {!isCollapsed && (
                    <span className="flex-1 truncate">
                      {item.title}
                    </span>
                  )}

                  {!isCollapsed && item.badge && (
                    <span className="px-1.5 py-0.5 text-[9px] font-extrabold rounded-md bg-white/90 dark:bg-slate-900 text-slate-900 dark:text-slate-100 border border-primary-200 dark:border-slate-700">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Admin Section */}
        {canAccessAdmin && (
          <div>
            {!isCollapsed && (
              <div className="px-3 mb-2 text-[10px] font-bold tracking-wider text-slate-500 dark:text-slate-400 uppercase flex items-center gap-1.5">
                <Sparkles className="w-3 h-3 stroke-current text-rose-500" />
                <span>Quản trị hệ thống</span>
              </div>
            )}
            <nav className="space-y-1">
              {adminItems.map((item) => {
                const isActive = checkIsActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-label={item.title}
                    className={`relative flex items-center gap-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                      isCollapsed ? "justify-center px-0 w-11 h-11 mx-auto" : "px-3"
                    } ${
                      isActive
                        ? "bg-rose-500/90 dark:bg-rose-950/60 text-white font-bold border border-rose-400/50 dark:border-rose-800/60 shadow-sm"
                        : "text-slate-700 dark:text-slate-300 hover:bg-rose-50/60 dark:hover:bg-slate-800/60"
                    }`}
                    title={isCollapsed ? item.title : undefined}
                  >
                    {item.icon}
                    {!isCollapsed && (
                      <span className="flex-1 truncate">
                        {item.title}
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>
        )}
      </div>

      {/* Premium Integrated Sidebar Footer */}
      <div className="p-2.5 border-t border-primary-100/80 dark:border-slate-800/80 bg-white/40 dark:bg-slate-900/40">
        <div className="flex items-center justify-between gap-2">
          {/* User Profile Info Card */}
          {!isCollapsed ? (
            <div className="flex items-center gap-2.5 min-w-0 flex-1 px-1">
              <div className="w-8 h-8 rounded-full bg-primary-200 dark:bg-slate-800 border border-primary-300 dark:border-slate-700 flex items-center justify-center text-slate-800 dark:text-slate-200 font-bold text-xs flex-shrink-0">
                {user?.fullName ? user.fullName.charAt(0) : <UserIcon className="w-4 h-4 stroke-current" />}
              </div>
              <div className="flex flex-col min-w-0 flex-1">
                <span className="text-xs font-bold text-slate-900 dark:text-white truncate">
                  {user?.fullName || "Quản trị viên"}
                </span>
                <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium capitalize truncate">
                  {user?.role || "Admin"} • {user?.department || "CTSV"}
                </span>
              </div>
            </div>
          ) : null}

          {/* Toggle Button with Tooltip and Icon */}
          <button
            onClick={handleToggleCollapse}
            aria-label={isCollapsed ? "Mở rộng thanh menu (Ctrl+[)" : "Thu gọn thanh menu (Ctrl+[)"}
            className={`p-2 rounded-xl border border-primary-200/80 dark:border-slate-700/80 bg-white/80 dark:bg-slate-800/80 hover:bg-primary-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-all shadow-sm flex items-center justify-center flex-shrink-0 ${
              isCollapsed ? "w-11 h-11 mx-auto" : ""
            }`}
            title={isCollapsed ? "Mở rộng thanh menu (Ctrl+[)" : "Thu gọn thanh menu (Ctrl+[)"}
          >
            {isCollapsed ? (
              <PanelLeftOpen className="w-5 h-5 stroke-current text-primary-700 dark:text-primary-300" />
            ) : (
              <PanelLeftClose className="w-4 h-4 stroke-current text-slate-600 dark:text-slate-300" />
            )}
          </button>
        </div>
      </div>
    </motion.aside>
  );
};
