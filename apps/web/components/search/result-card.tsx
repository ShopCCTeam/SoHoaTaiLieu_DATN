"use client";

import React from "react";
import Link from "next/link";
import type { SearchResult } from "@/lib/api/types";
import { ExternalLink, Sparkles } from "lucide-react";

interface ResultCardProps {
  result: SearchResult;
  highlightQuery?: string;
}

function renderHighlightedText(text: string, keyword: string) {
  if (!keyword.trim()) return text;

  const escapedKeyword = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escapedKeyword})`, "gi"));
  return (
    <span>
      {parts.map((part, index) =>
        part.toLowerCase() === keyword.toLowerCase() ? (
          <mark
            key={`${part}-${index}`}
            className="rounded bg-primary-300 px-1 font-bold text-slate-950"
          >
            {part}
          </mark>
        ) : (
          part
        ),
      )}
    </span>
  );
}

export const SearchResultCard: React.FC<ResultCardProps> = ({
  result,
  highlightQuery = "",
}) => {
  const displayScore = result.vectorScore ?? result.score;
  const scoreLabel = result.vectorScore === null ? "RRF hybrid" : "Cosine vector";

  return (
    <article className="glass-panel group space-y-3 rounded-3xl border border-primary-200/80 p-5 shadow-sm transition-all hover:border-primary-400 hover:shadow-rose-glow md:p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-[10px] text-slate-700 dark:bg-slate-800 dark:text-slate-300">
              {result.documentType}
            </span>
            <span className="rounded-md bg-primary-100 px-2 py-0.5 text-[10px] font-semibold text-slate-800">
              Scope: {result.documentScope}
            </span>
            <span className="rounded-md bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              Trang {result.pageNumber}
            </span>
          </div>

          <Link
            href={`/documents/${result.documentId}?page=${result.pageNumber}`}
            className="block line-clamp-2 text-base font-extrabold text-slate-900 transition-colors group-hover:text-primary-700 dark:text-white dark:group-hover:text-primary-300 md:text-lg"
          >
            {renderHighlightedText(result.documentTitle, highlightQuery)}
          </Link>
        </div>

        <div className="flex shrink-0 flex-col items-end">
          <span className="inline-flex items-center gap-1 rounded-xl bg-gradient-to-r from-primary-200 to-rose-200 px-2.5 py-1 text-xs font-bold text-slate-950 shadow-sm">
            <Sparkles className="h-3.5 w-3.5 stroke-current text-primary-700" />
            <span>Score: {(displayScore * 100).toFixed(0)}%</span>
          </span>
          <span className="mt-0.5 text-[10px] text-muted-foreground">{scoreLabel}</span>
        </div>
      </div>

      <div className="rounded-2xl border border-primary-100 bg-white/70 p-3 font-sans text-xs leading-relaxed text-slate-700 dark:border-slate-800 dark:bg-slate-950/70 dark:text-slate-300">
        {renderHighlightedText(result.text, highlightQuery)}
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-primary-100/60 pt-1 text-xs text-muted-foreground dark:border-slate-800">
        <span>Chunk: {result.chunkId}</span>
        <Link
          href={`/documents/${result.documentId}?page=${result.pageNumber}`}
          className="inline-flex items-center gap-1 text-xs font-bold text-slate-900 transition-colors hover:text-primary-700 dark:text-slate-100"
        >
          <span>Xem tài liệu</span>
          <ExternalLink className="h-3.5 w-3.5 stroke-current" />
        </Link>
      </div>
    </article>
  );
};
