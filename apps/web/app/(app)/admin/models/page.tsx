"use client";

import React from "react";
import { useAdminModels } from "@/lib/api/queries";
import { Cpu, CheckCircle2, RotateCcw, Lock } from "lucide-react";
import { useAuthStore } from "@/lib/auth/session";

export default function AdminModelsPage() {
  const { user } = useAuthStore();
  const { data: models = [], isLoading } = useAdminModels();

  if (user?.role !== "admin") {
    return (
      <div className="max-w-xl mx-auto my-12 glass-panel p-8 rounded-3xl border border-rose-200 text-center space-y-4 shadow-rose-subtle">
        <div className="w-14 h-14 rounded-2xl bg-rose-100 dark:bg-rose-950 flex items-center justify-center text-rose-600 mx-auto">
          <Lock className="w-7 h-7 stroke-current" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          403 - Giới Hạn Quyền Quản Trị Viên
        </h2>
        <p className="text-xs text-muted-foreground">
          Chức năng Quản lý Models & LangChain RAG chỉ dành cho tài khoản Admin.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 glass-panel p-6 rounded-3xl border border-primary-200/80 shadow-rose-subtle">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-bold">
            <Cpu className="w-3.5 h-3.5 stroke-current text-emerald-600" />
            <span>Quản Lý Phiên Bản Model RAG & OCR</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
            Quản lý AI Models & Training Runs
          </h1>
        </div>
      </div>

      {/* Models Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {isLoading ? (
          <div className="col-span-2 glass-panel p-12 text-center rounded-3xl space-y-3">
            <div className="w-8 h-8 border-4 border-primary-300 border-t-primary-600 rounded-full animate-spin mx-auto" />
            <p className="text-xs text-muted-foreground">Đang truy vấn danh sách AI Models...</p>
          </div>
        ) : (
          models.map((mod: any) => (
            <div
              key={mod.id}
              className="glass-panel p-6 rounded-3xl border border-primary-200/80 space-y-4 shadow-sm"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 text-[10px] font-bold font-mono">
                    {mod.version}
                  </span>
                  <h3 className="font-bold text-slate-900 dark:text-white text-base mt-1">
                    {mod.name}
                  </h3>
                </div>
                <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600">
                  <CheckCircle2 className="w-5 h-5 stroke-current" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-primary-100 dark:border-slate-800">
                <div>
                  <span className="text-muted-foreground">Độ chính xác RAG:</span>
                  <div className="font-bold text-slate-900 dark:text-white font-mono">{mod.accuracyScore}%</div>
                </div>
                <div>
                  <span className="text-muted-foreground">Kích thước Vector:</span>
                  <div className="font-bold text-slate-900 dark:text-white font-mono">{mod.dimension || "N/A"}</div>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button aria-label="Rollback version model" className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-primary-200 text-slate-900 dark:text-white font-bold text-xs hover:bg-primary-100 transition-all">
                  <RotateCcw className="w-3.5 h-3.5 stroke-current" />
                  <span>Rollback</span>
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
