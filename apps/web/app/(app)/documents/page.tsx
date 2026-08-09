"use client";

import React from "react";
import Link from "next/link";
import { DocumentTable } from "@/components/documents/document-table";
import { useDocuments } from "@/lib/api/queries";
import { MOCK_DOCUMENTS } from "@/lib/mocks/fixtures";
import { Upload, FileText, Sparkles } from "lucide-react";

export default function DocumentsListPage() {
  const { data: documents = MOCK_DOCUMENTS, isLoading } = useDocuments();

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 glass-panel p-6 rounded-3xl border border-primary-200/80 shadow-rose-subtle">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-primary-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-[11px] font-bold">
            <Sparkles className="w-3.5 h-3.5 stroke-current text-primary-600 dark:text-primary-400" />
            <span>Kho Văn Bản & Tài Liệu Công Tác Sinh Viên</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
            Danh sách Văn bản Số hóa
          </h1>
          <p className="text-xs text-muted-foreground">
            Quản lý quy chế, quy định, thông báo, quyết định & theo dõi tiến trình OCR / RAG.
          </p>
        </div>

        <Link
          href="/documents/upload"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary-400 text-slate-950 font-bold text-xs shadow-rose-subtle hover:bg-primary-500 hover:shadow-rose-glow transition-all active:scale-[0.98]"
        >
          <Upload className="w-4 h-4 stroke-current" />
          <span>Upload File Mới</span>
        </Link>
      </div>

      {/* Main Table */}
      {isLoading ? (
        <div className="glass-panel p-12 text-center space-y-3 rounded-2xl">
          <div className="w-8 h-8 border-4 border-primary-300 border-t-primary-600 rounded-full animate-spin mx-auto" />
          <p className="text-xs text-muted-foreground">Đang truy vấn danh sách văn bản...</p>
        </div>
      ) : (
        <DocumentTable initialDocuments={documents} />
      )}
    </div>
  );
}
