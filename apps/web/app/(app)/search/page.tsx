"use client";

import React, { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useSearchRAG } from "@/lib/api/queries";
import { SearchResultCard } from "@/components/search/result-card";
import { Search, Sparkles, SlidersHorizontal, Inbox } from "lucide-react";

export default function SearchRAGPage() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  const [query, setQuery] = useState(initialQuery);
  const [activeQuery, setActiveQuery] = useState(initialQuery);

  const { data: results = [], isLoading } = useSearchRAG(activeQuery);

  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery);
      setActiveQuery(initialQuery);
    }
  }, [initialQuery]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      setActiveQuery(query.trim());
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="glass-panel p-6 md:p-8 rounded-3xl border border-primary-200/80 shadow-rose-subtle space-y-4">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-primary-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-[11px] font-bold">
            <Sparkles className="w-3.5 h-3.5 stroke-current text-primary-600 dark:text-primary-400" />
            <span>Công Cụ Tra Cứu Thông Minh RAG Vector BGE-M3</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
            Tra cứu Văn bản & Quy chế CTSV
          </h1>
          <p className="text-xs text-muted-foreground">
            Tìm kiếm ngữ nghĩa (Semantic Vector Search) + Khớp từ khóa trực tiếp từ toàn bộ kho tài liệu số hóa.
          </p>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearchSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 stroke-current text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Nhập câu hỏi hoặc từ khóa (ví dụ: nghỉ học tạm thời, điểm rèn luyện, học bổng...)"
              className="w-full h-11 pl-10 pr-4 rounded-xl border border-primary-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary-400 transition-all shadow-sm"
            />
          </div>
          <button
            type="submit"
            aria-label="Thực hiện tìm kiếm RAG"
            className="px-6 h-11 rounded-xl bg-primary-400 text-slate-950 font-bold text-xs shadow-rose-subtle hover:bg-primary-500 transition-all flex items-center gap-2 active:scale-[0.98]"
          >
            <Search className="w-4 h-4 stroke-current" />
            <span>Tìm kiếm RAG</span>
          </button>
        </form>
      </div>

      {/* Results Header */}
      {activeQuery && (
        <div className="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300 px-2">
          <span>
            Kết quả tra cứu cho: <span className="font-bold text-slate-900 dark:text-white">&ldquo;{activeQuery}&rdquo;</span>
          </span>
          <span className="text-muted-foreground">Tìm thấy {results.length} đoạn trích tương đồng</span>
        </div>
      )}

      {/* Results List */}
      {isLoading ? (
        <div className="glass-panel p-12 rounded-3xl text-center space-y-3">
          <div className="w-8 h-8 border-4 border-primary-300 border-t-primary-600 rounded-full animate-spin mx-auto" />
          <p className="text-xs text-muted-foreground">Đang tính toán vector tương đồng BGE-M3...</p>
        </div>
      ) : results.length > 0 ? (
        <div className="space-y-4">
          {results.map((item: any, idx: number) => (
            <SearchResultCard
              key={idx}
              document={item.document}
              score={item.score}
              snippet={item.snippet}
              pageNumber={item.pageNumber}
              highlightQuery={activeQuery}
            />
          ))}
        </div>
      ) : activeQuery ? (
        <div className="glass-panel p-12 rounded-3xl text-center space-y-3">
          <Inbox className="w-10 h-10 text-muted-foreground mx-auto stroke-current" />
          <p className="text-xs font-bold text-slate-700 dark:text-slate-300">Không tìm thấy kết quả RAG nào phù hợp.</p>
        </div>
      ) : null}
    </div>
  );
}
