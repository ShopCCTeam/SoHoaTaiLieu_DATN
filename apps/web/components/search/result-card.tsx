"use client";

import React from "react";
import Link from "next/link";
import { Document } from "@/lib/api/types";
import { StatusBadge } from "@/components/documents/status-badge";
import { formatDate } from "@/lib/utils/format";
import { FileText, Sparkles, ExternalLink, Calendar, Tag } from "lucide-react";

interface ResultCardProps {
  document: Document;
  snippet?: string;
  score?: number;
  pageNumber?: number;
  highlightKeyword?: string;
  highlightQuery?: string;
}

export const ResultCard: React.FC<ResultCardProps> = ({
  document,
  snippet = "Trích đoạn quy định Công tác sinh viên có chứa từ khóa tìm kiếm...",
  score = 0.94,
  pageNumber,
  highlightKeyword = "",
  highlightQuery = "",
}) => {
  const kw = highlightKeyword || highlightQuery;
  const renderHighlightedText = (text: string, keyword: string) => {
    if (!keyword.trim()) return text;
    const parts = text.split(new RegExp(`(${keyword})`, "gi"));
    return (
      <span>
        {parts.map((part, i) =>
          part.toLowerCase() === keyword.toLowerCase() ? (
            <mark
              key={i}
              className="bg-primary-300 text-slate-950 font-bold px-1 rounded"
            >
              {part}
            </mark>
          ) : (
            part
          )
        )}
      </span>
    );
  };

  return (
    <div className="glass-panel p-5 md:p-6 rounded-3xl border border-primary-200/80 hover:border-primary-400 hover:shadow-rose-glow transition-all space-y-3 shadow-sm group">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={document.status} />
            <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-[10px] font-mono text-slate-700 dark:text-slate-300">
              {document.type}
            </span>
            <span className="px-2 py-0.5 rounded-md bg-primary-100 text-slate-800 text-[10px] font-semibold">
              Scope: {document.scope}
            </span>
            {pageNumber && (
              <span className="px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 text-[10px] font-bold">
                Trang {pageNumber}
              </span>
            )}
          </div>

          <Link
            href={`/documents/${document.id}${pageNumber ? `?page=${pageNumber}` : ""}`}
            className="text-base md:text-lg font-extrabold text-slate-900 dark:text-white group-hover:text-primary-700 dark:group-hover:text-primary-300 transition-colors line-clamp-2 block"
          >
            {renderHighlightedText(document.title, kw)}
          </Link>
        </div>

        {/* Vector Score */}
        <div className="flex flex-col items-end flex-shrink-0">
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-gradient-to-r from-primary-200 to-rose-200 text-slate-950 text-xs font-bold shadow-sm">
            <Sparkles className="w-3.5 h-3.5 stroke-current text-primary-700" />
            <span>Score: {(score * 100).toFixed(0)}%</span>
          </span>
          <span className="text-[10px] text-muted-foreground mt-0.5">BGE-M3 Vector</span>
        </div>
      </div>

      {/* Snippet with Highlight */}
      <div className="p-3 rounded-2xl bg-white/70 dark:bg-slate-950/70 border border-primary-100 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-sans">
        {renderHighlightedText(snippet, kw)}
      </div>

      {/* Footer Details */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground pt-1 border-t border-primary-100/60 dark:border-slate-800">
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5 stroke-current text-slate-400" />
            <span>{formatDate(document.effectiveFrom || document.createdAt)}</span>
          </span>
          <span>•</span>
          <span>{document.issuingBody || "Phòng CTSV"}</span>
        </div>

        <Link
          href={`/documents/${document.id}${pageNumber ? `?page=${pageNumber}` : ""}`}
          className="inline-flex items-center gap-1 text-xs font-bold text-slate-900 dark:text-slate-100 hover:text-primary-700 transition-colors"
        >
          <span>Xem tài liệu</span>
          <ExternalLink className="w-3.5 h-3.5 stroke-current" />
        </Link>
      </div>
    </div>
  );
};

export const SearchResultCard = ResultCard;
