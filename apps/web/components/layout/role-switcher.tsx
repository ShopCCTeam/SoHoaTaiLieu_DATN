"use client";

import React, { useState, useEffect } from "react";
import { useAuthStore, DEMO_USERS } from "@/lib/auth/session";
import { UserRole } from "@/lib/api/types";
import { Shield, UserCheck, GraduationCap, ChevronDown, Check } from "lucide-react";

export const RoleSwitcher: React.FC = () => {
  const { user, switchRole } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || !user) {
    return (
      <div className="h-8 w-28 rounded-xl bg-primary-100/50 animate-pulse border border-primary-200" />
    );
  }

  const roles: { role: UserRole; label: string; icon: React.ReactNode; color: string }[] = [
    {
      role: "admin",
      label: "Quản Trị Viên (Admin)",
      icon: <Shield className="w-4 h-4 stroke-current text-rose-600 dark:text-rose-400" />,
      color: "bg-rose-50 text-rose-700 border-rose-200",
    },
    {
      role: "staff",
      label: "Cán Bộ CTSV (Staff)",
      icon: <UserCheck className="w-4 h-4 stroke-current text-amber-600 dark:text-amber-400" />,
      color: "bg-amber-50 text-amber-700 border-amber-200",
    },
    {
      role: "student",
      label: "Sinh Viên (Student)",
      icon: <GraduationCap className="w-4 h-4 stroke-current text-sky-600 dark:text-sky-400" />,
      color: "bg-sky-50 text-sky-700 border-sky-200",
    },
  ];

  const activeItem = roles.find((r) => r.role === user.role) || roles[0];

  return (
    <div className="relative inline-block text-left">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 hover:bg-primary-50 dark:hover:bg-slate-800 transition-all text-xs font-semibold shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
        title="Chuyển đổi nhanh Role Demo"
      >
        <span className="text-muted-foreground hidden sm:inline">Role:</span>
        <span className="flex items-center gap-1.5">
          {activeItem.icon}
          <span className="capitalize text-slate-800 dark:text-slate-200">{user.role}</span>
        </span>
        <ChevronDown className="w-3.5 h-3.5 stroke-current text-slate-500 ml-0.5" />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-64 rounded-2xl border border-primary-200 bg-white/95 dark:bg-slate-900/95 shadow-xl backdrop-blur-xl z-50 p-1.5 animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="px-3 py-2 text-[11px] font-bold tracking-wider text-muted-foreground uppercase border-b border-primary-100 dark:border-slate-800 mb-1">
              Chuyển đổi Tài khoản Demo
            </div>
            <div className="space-y-1">
              {roles.map((item) => {
                const isSelected = user.role === item.role;
                const demoUser = DEMO_USERS[item.role];
                return (
                  <button
                    key={item.role}
                    onClick={() => {
                      switchRole(item.role);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center justify-between p-2.5 rounded-xl text-xs transition-all text-left ${
                      isSelected
                        ? "bg-primary-100/70 dark:bg-slate-800 font-semibold text-slate-900 dark:text-white"
                        : "hover:bg-slate-50 dark:hover:bg-slate-800/50 text-slate-700 dark:text-slate-300"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="p-1.5 rounded-lg bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                        {item.icon}
                      </div>
                      <div>
                        <div className="font-semibold">{item.label}</div>
                        <div className="text-[10px] text-muted-foreground truncate max-w-[140px]">
                          {demoUser.email}
                        </div>
                      </div>
                    </div>
                    {isSelected && (
                      <Check className="w-4 h-4 stroke-current text-primary-600" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
