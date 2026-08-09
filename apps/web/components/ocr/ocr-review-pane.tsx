"use client";

import React, { useState } from "react";
import { OCRBlock } from "@/lib/api/types";
import { BlockEditor } from "./block-editor";
import {
  Eye,
  CheckCircle2,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Save,
  FileText,
  AlertTriangle,
} from "lucide-react";

interface OCRReviewPaneProps {
  documentTitle: string;
  initialBlocks: OCRBlock[];
}

export const OCRReviewPane: React.FC<OCRReviewPaneProps> = ({
  documentTitle,
  initialBlocks,
}) => {
  const [blocks, setBlocks] = useState<OCRBlock[]>(initialBlocks);
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(
    initialBlocks[0]?.id || null
  );
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [toastMessage, setToastMessage] = useState<string>("");

  const pageBlocks = blocks.filter((b) => b.pageNumber === currentPage);
  const totalPages = Math.max(...blocks.map((b) => b.pageNumber), 1);

  const handleSaveBlock = (updated: OCRBlock) => {
    setBlocks((prev) => prev.map((b) => (b.id === updated.id ? updated : b)));
    setToastMessage(`Đã cập nhật Block #${updated.id} thành công!`);
    setTimeout(() => setToastMessage(""), 3000);
  };

  return (
    <div className="space-y-4">
      {/* Toast Banner */}
      {toastMessage && (
        <div className="p-3 rounded-2xl bg-emerald-500 text-white text-xs font-bold flex items-center gap-2 shadow-rose-subtle animate-in fade-in slide-in-from-top-2">
          <CheckCircle2 className="w-4 h-4 stroke-current" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Split-View Container */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Side: Document Preview Canvas with BBox Overlay */}
        <div className="lg:col-span-7 glass-panel p-4 md:p-6 rounded-3xl border border-primary-200/80 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-primary-100 dark:border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 stroke-current text-primary-600" />
              <span className="font-bold text-xs text-slate-900 dark:text-white">
                Bản render Trang {currentPage} / {totalPages}
              </span>
            </div>

            {/* Page Navigation */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-1 rounded-lg border border-primary-200 hover:bg-primary-100 disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4 stroke-current" />
              </button>
              <span className="text-xs font-mono font-bold">
                Trang {currentPage}
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="p-1 rounded-lg border border-primary-200 hover:bg-primary-100 disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4 stroke-current" />
              </button>
            </div>
          </div>

          {/* Interactive Document Page Container */}
          <div className="relative w-full aspect-[1/1.4] bg-slate-50 dark:bg-slate-950 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-inner p-6 select-none">
            {/* Document Watermark Mock Background */}
            <div className="space-y-4 opacity-40 pointer-events-none">
              <div className="h-4 bg-slate-300 dark:bg-slate-700 rounded w-2/3 mx-auto" />
              <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded w-full" />
              <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded w-5/6" />
              <div className="h-20 bg-slate-200 dark:bg-slate-800 rounded w-full my-6" />
              <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded w-4/5" />
              <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded w-full" />
            </div>

            {/* Render OCR Bounding Box Overlays */}
            {pageBlocks.map((blk) => {
              const [x, y, w, h] = blk.bbox;
              const isSelected = selectedBlockId === blk.id;
              const isLowConfidence = blk.confidence < 0.9;

              return (
                <div
                  key={blk.id}
                  onClick={() => setSelectedBlockId(blk.id)}
                  style={{
                    left: `${x}%`,
                    top: `${y}%`,
                    width: `${w}%`,
                    height: `${h}%`,
                  }}
                  className={`absolute rounded-lg border-2 transition-all cursor-pointer flex items-center justify-between p-1.5 text-[10px] font-mono font-bold ${
                    isSelected
                      ? "border-rose-500 bg-rose-500/20 shadow-rose-glow ring-2 ring-rose-400 z-20"
                      : isLowConfidence
                      ? "border-amber-400 bg-amber-400/15 hover:bg-amber-400/30 z-10"
                      : "border-primary-400 bg-primary-400/15 hover:bg-primary-400/30 z-0"
                  }`}
                  title={`Block #${blk.id} (${(blk.confidence * 100).toFixed(0)}%)`}
                >
                  <span className="bg-slate-900 text-white px-1 rounded text-[9px]">
                    #{blk.id}
                  </span>
                  {isLowConfidence && (
                    <AlertTriangle className="w-3 h-3 stroke-current text-amber-600" />
                  )}
                </div>
              );
            })}
          </div>

          <div className="text-[11px] text-muted-foreground text-center flex items-center justify-center gap-4">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-primary-400/30 border border-primary-400" />
              <span>BBox OCR Chuẩn</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-amber-400/30 border border-amber-400" />
              <span>Cần kiểm tra (&lt;90%)</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-rose-500/30 border border-rose-500" />
              <span>Đang chọn</span>
            </span>
          </div>
        </div>

        {/* Right Side: List of Text Blocks */}
        <div className="lg:col-span-5 glass-panel p-4 md:p-6 rounded-3xl border border-primary-200/80 space-y-4 shadow-sm max-h-[800px] overflow-y-auto">
          <div className="flex items-center justify-between border-b border-primary-100 dark:border-slate-800 pb-3 sticky top-0 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md z-10">
            <div>
              <h3 className="font-bold text-xs text-slate-900 dark:text-white">
                Danh sách Block Text (Trang {currentPage})
              </h3>
              <p className="text-[10px] text-muted-foreground">
                Click vào block để sửa nội dung và kiểm tra sai sót OCR
              </p>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-primary-100 text-primary-800 font-bold text-[10px]">
              {pageBlocks.length} Blocks
            </span>
          </div>

          <div className="space-y-3">
            {pageBlocks.map((blk) => (
              <BlockEditor
                key={blk.id}
                block={blk}
                isSelected={selectedBlockId === blk.id}
                onSelect={() => setSelectedBlockId(blk.id)}
                onSaveBlock={handleSaveBlock}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
