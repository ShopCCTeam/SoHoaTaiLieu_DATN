"use client";

import React, { useState } from "react";
import Link from "next/link";
import { DocumentTable } from "@/components/documents/document-table";
import { useDocuments } from "@/lib/api/queries";
import { MOCK_DOCUMENTS } from "@/lib/mocks/fixtures";
import { FileText, Search, Sparkles, Upload } from "lucide-react";

function parseTags(value: string): string[] {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

export default function DocumentsListPage() {
  const [keyword, setKeyword] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [appliedFilters, setAppliedFilters] = useState({
    keyword: "",
    tags: [] as string[],
  });
  const { data: documents = MOCK_DOCUMENTS, isLoading } = useDocuments(appliedFilters);

  const hasAppliedFilters = Boolean(
    appliedFilters.keyword || appliedFilters.tags.length > 0,
  );

  function applyFilters(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAppliedFilters({ keyword: keyword.trim(), tags: parseTags(tagsInput) });
  }

  function resetFilters() {
    setKeyword("");
    setTagsInput("");
    setAppliedFilters({ keyword: "", tags: [] });
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="glass-panel flex flex-col items-start justify-between gap-4 rounded-3xl border border-primary-200/80 p-6 shadow-rose-subtle sm:flex-row sm:items-center">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-primary-100 px-3 py-0.5 text-[11px] font-bold text-slate-800 dark:bg-slate-800 dark:text-slate-200">
            <Sparkles className="h-3.5 w-3.5 stroke-current text-primary-600 dark:text-primary-400" />
            <span>Kho Văn Bản & Tài Liệu Công Tác Sinh Viên</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">
            Danh sách Văn bản Số hóa
          </h1>
          <p className="text-xs text-muted-foreground">
            Quản lý quy chế, quy định, thông báo, quyết định và theo dõi tiến trình OCR / RAG.
          </p>
        </div>

        <Link
          href="/documents/upload"
          className="inline-flex items-center gap-2 rounded-xl bg-primary-400 px-5 py-2.5 text-xs font-bold text-slate-950 shadow-rose-subtle transition-all hover:bg-primary-500 hover:shadow-rose-glow active:scale-[0.98]"
        >
          <Upload className="h-4 w-4 stroke-current" />
          <span>Upload File Mới</span>
        </Link>
      </div>

      <form
        onSubmit={applyFilters}
        className="glass-panel grid gap-3 rounded-2xl border border-primary-200/80 p-4 shadow-sm md:grid-cols-[1fr_1fr_auto_auto]"
      >
        <div>
          <label htmlFor="document-keyword" className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-200">
            Từ khóa metadata
          </label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              id="document-keyword"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="Tên, số hiệu, đơn vị ban hành hoặc tag"
              className="h-10 w-full rounded-xl border border-primary-200 bg-white/80 pl-9 pr-3 text-xs text-foreground transition-all focus:outline-none focus:ring-2 focus:ring-primary-400 dark:border-slate-800 dark:bg-slate-900/80"
            />
          </div>
        </div>
        <div>
          <label htmlFor="document-tags" className="mb-1 block text-xs font-semibold text-slate-700 dark:text-slate-200">
            Tag bắt buộc
          </label>
          <input
            id="document-tags"
            value={tagsInput}
            onChange={(event) => setTagsInput(event.target.value)}
            placeholder="Ví dụ: quy_che, dao_tao"
            className="h-10 w-full rounded-xl border border-primary-200 bg-white/80 px-3 text-xs text-foreground transition-all focus:outline-none focus:ring-2 focus:ring-primary-400 dark:border-slate-800 dark:bg-slate-900/80"
          />
        </div>
        <button
          type="submit"
          className="mt-auto h-10 rounded-xl bg-primary-400 px-4 text-xs font-bold text-slate-950 transition-all hover:bg-primary-500"
        >
          Áp dụng
        </button>
        {hasAppliedFilters ? (
          <button
            type="button"
            onClick={resetFilters}
            className="mt-auto h-10 rounded-xl border border-primary-200 px-4 text-xs font-semibold text-slate-700 transition-all hover:bg-primary-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Xóa bộ lọc
          </button>
        ) : (
          <span className="mt-auto flex h-10 items-center text-xs text-muted-foreground">
            Tag cách nhau bằng dấu phẩy.
          </span>
        )}
      </form>

      {isLoading ? (
        <div className="glass-panel space-y-3 rounded-2xl p-12 text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-primary-300 border-t-primary-600" />
          <p className="text-xs text-muted-foreground">Đang truy vấn danh sách văn bản...</p>
        </div>
      ) : (
        <DocumentTable initialDocuments={documents} />
      )}
    </div>
  );
}
