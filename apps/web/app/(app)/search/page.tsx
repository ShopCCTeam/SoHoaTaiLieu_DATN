"use client";

import React, { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useSearchRAG } from "@/lib/api/queries";
import { SearchResultCard } from "@/components/search/result-card";
import { Inbox, Search, SlidersHorizontal, Sparkles } from "lucide-react";

function parseTags(value: string): string[] {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

export default function SearchRAGPage() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";
  const [query, setQuery] = useState(initialQuery);
  const [activeQuery, setActiveQuery] = useState(initialQuery);
  const [keyword, setKeyword] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [activeFilters, setActiveFilters] = useState({
    keyword: "",
    tags: [] as string[],
  });

  const { data: results = [], isLoading } = useSearchRAG(activeQuery, activeFilters);

  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery);
      setActiveQuery(initialQuery);
    }
  }, [initialQuery]);

  function handleSearchSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (query.trim()) {
      setActiveQuery(query.trim());
      setActiveFilters({ keyword: keyword.trim(), tags: parseTags(tagsInput) });
    }
  }

  function resetMetadataFilters() {
    setKeyword("");
    setTagsInput("");
    setActiveFilters({ keyword: "", tags: [] });
  }

  const hasMetadataFilters = Boolean(activeFilters.keyword || activeFilters.tags.length > 0);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="glass-panel space-y-4 rounded-3xl border border-primary-200/80 p-6 shadow-rose-subtle md:p-8">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-primary-100 px-3 py-0.5 text-[11px] font-bold text-slate-800 dark:bg-slate-800 dark:text-slate-200">
            <Sparkles className="h-3.5 w-3.5 stroke-current text-primary-600 dark:text-primary-400" />
            <span>Công Cụ Tra Cứu Thông Minh RAG Vector BGE-M3</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">
            Tra cứu Văn bản & Quy chế CTSV
          </h1>
          <p className="text-xs text-muted-foreground">
            Tìm kiếm ngữ nghĩa kết hợp full-text; bộ lọc metadata/tag được áp dụng trước candidate retrieval.
          </p>
        </div>

        <form onSubmit={handleSearchSubmit} className="space-y-3">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                id="rag-query"
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Nhập câu hỏi hoặc từ khóa (ví dụ: nghỉ học tạm thời, điểm rèn luyện, học bổng...)"
                className="h-11 w-full rounded-xl border border-primary-200 bg-white/80 pl-10 pr-4 text-xs text-foreground shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-primary-400 dark:border-slate-800 dark:bg-slate-900/80"
              />
            </div>
            <button
              type="submit"
              aria-label="Thực hiện tìm kiếm RAG"
              className="flex h-11 items-center gap-2 rounded-xl bg-primary-400 px-6 text-xs font-bold text-slate-950 shadow-rose-subtle transition-all hover:bg-primary-500 active:scale-[0.98]"
            >
              <Search className="h-4 w-4 stroke-current" />
              <span>Tìm kiếm RAG</span>
            </button>
          </div>

          <details className="rounded-xl border border-primary-100 bg-white/50 p-3 dark:border-slate-800 dark:bg-slate-950/40">
            <summary className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-200">
              <SlidersHorizontal className="h-4 w-4" />
              Bộ lọc metadata và tag
            </summary>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <div>
                <label htmlFor="rag-keyword" className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-200">
                  Từ khóa metadata
                </label>
                <input
                  id="rag-keyword"
                  value={keyword}
                  onChange={(event) => setKeyword(event.target.value)}
                  placeholder="Tên, số hiệu, đơn vị ban hành hoặc tag"
                  className="h-10 w-full rounded-xl border border-primary-200 bg-white/80 px-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary-400 dark:border-slate-800 dark:bg-slate-900/80"
                />
              </div>
              <div>
                <label htmlFor="rag-tags" className="mb-1 block text-xs font-medium text-slate-700 dark:text-slate-200">
                  Tag bắt buộc
                </label>
                <input
                  id="rag-tags"
                  value={tagsInput}
                  onChange={(event) => setTagsInput(event.target.value)}
                  placeholder="Ví dụ: quy_che, dao_tao"
                  className="h-10 w-full rounded-xl border border-primary-200 bg-white/80 px-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary-400 dark:border-slate-800 dark:bg-slate-900/80"
                />
              </div>
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">Các tag cách nhau bằng dấu phẩy; tất cả tag đã nhập phải cùng có trên tài liệu.</p>
          </details>
        </form>
      </div>

      {activeQuery ? (
        <div className="flex items-center justify-between px-2 text-xs font-semibold text-slate-700 dark:text-slate-300">
          <span>
            Kết quả tra cứu cho: <span className="font-bold text-slate-900 dark:text-white">&ldquo;{activeQuery}&rdquo;</span>
          </span>
          <div className="flex items-center gap-3">
            <span className="text-muted-foreground">Tìm thấy {results.length} đoạn trích tương đồng</span>
            {hasMetadataFilters ? (
              <button
                type="button"
                onClick={resetMetadataFilters}
                className="text-xs font-semibold text-primary-700 hover:text-primary-800 dark:text-primary-300"
              >
                Xóa metadata/tag
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {isLoading ? (
        <div className="glass-panel space-y-3 rounded-3xl p-12 text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-primary-300 border-t-primary-600" />
          <p className="text-xs text-muted-foreground">Đang tính toán vector tương đồng BGE-M3...</p>
        </div>
      ) : results.length > 0 ? (
        <div className="space-y-4">
          {results.map((result) => (
            <SearchResultCard
              key={result.chunkId}
              result={result}
              highlightQuery={activeQuery}
            />
          ))}
        </div>
      ) : activeQuery ? (
        <div className="glass-panel space-y-3 rounded-3xl p-12 text-center">
          <Inbox className="mx-auto h-10 w-10 text-muted-foreground" />
          <p className="text-xs font-bold text-slate-700 dark:text-slate-300">Không tìm thấy kết quả RAG nào phù hợp.</p>
        </div>
      ) : null}
    </div>
  );
}
