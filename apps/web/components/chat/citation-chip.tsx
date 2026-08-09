"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Citation } from "@/lib/api/types";
import { FileText, ExternalLink, Sparkles, BookOpen } from "lucide-react";

interface CitationChipProps {
  citation: Citation;
}

export const CitationChip: React.FC<CitationChipProps> = ({ citation }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <Link
        href={`/documents/${citation.documentId}?page=${citation.pageNumber}`}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-primary-100 dark:bg-slate-800 border border-primary-300 text-xs font-semibold text-slate-900 dark:text-slate-100 hover:bg-primary-200 hover:border-primary-400 transition-all shadow-sm group"
      >
        <BookOpen className="w-3.5 h-3.5 stroke-current text-primary-700 dark:text-primary-300" />
        <span className="truncate max-w-[140px]">{citation.documentTitle}</span>
        <span className="px-1.5 py-0.2 rounded bg-white dark:bg-slate-950 font-mono text-[10px] text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-800">
          Trang {citation.pageNumber}
        </span>
        <ExternalLink className="w-3 h-3 stroke-current text-slate-400 group-hover:text-slate-900 transition-colors" />
      </Link>

      {/* Quote Preview Tooltip */}
      {showTooltip && (
        <div className="absolute bottom-full left-0 mb-2 w-72 p-3 rounded-2xl bg-white/95 dark:bg-slate-900/95 border border-primary-200 shadow-xl backdrop-blur-xl z-50 text-xs space-y-1.5 animate-in fade-in slide-in-from-bottom-2 duration-150">
          <div className="flex items-center justify-between font-bold text-slate-900 dark:text-white border-b border-primary-100 dark:border-slate-800 pb-1">
            <span className="truncate">{citation.documentTitle}</span>
            <span className="text-[10px] text-primary-700 font-mono">
              Score: {(citation.score * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-[11px] text-slate-700 dark:text-slate-300 italic bg-primary-50/50 dark:bg-slate-950/50 p-2 rounded-xl border border-primary-100">
            &ldquo;{citation.quote}&rdquo;
          </p>
        </div>
      )}
    </div>
  );
};
