"use client";

import React, { useEffect, useState } from "react";
import { OCRBlock, OCRPage } from "@/lib/api/types";
import { apiBinaryClient } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";
import { BlockEditor } from "./block-editor";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FileText,
  AlertTriangle,
} from "lucide-react";

interface OCRReviewPaneProps {
  documentTitle: string;
  initialBlocks: OCRBlock[];
  documentId?: string;
  versionId?: string;
  pages?: OCRPage[];
  authToken?: string | null;
}

export const OCRReviewPane: React.FC<OCRReviewPaneProps> = ({
  documentTitle,
  initialBlocks,
  documentId,
  versionId,
  pages,
  authToken,
}) => {
  const [blocks, setBlocks] = useState<OCRBlock[]>(initialBlocks);
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(
    initialBlocks[0]?.id || null,
  );
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [toastMessage, setToastMessage] = useState<string>("");
  const [pageImageUrl, setPageImageUrl] = useState<string | null>(null);
  const [imageUnavailable, setImageUnavailable] = useState(false);

  const pageBlocks = blocks.filter((block) => block.pageNumber === currentPage);
  const pageNumbers = pages?.map((page) => page.pageNumber) ?? blocks.map((block) => block.pageNumber);
  const totalPages = Math.max(...pageNumbers, 1);
  const currentPageMeta = pages?.find((page) => page.pageNumber === currentPage);
  const usePixelCoordinates = Boolean(currentPageMeta?.width && currentPageMeta?.height);

  useEffect(() => {
    let objectUrl: string | null = null;
    let isActive = true;
    setPageImageUrl(null);
    setImageUnavailable(false);

    if (!documentId || !versionId || !authToken || !currentPageMeta?.imageKey) {
      setImageUnavailable(true);
      return () => undefined;
    }

    void apiBinaryClient(
      API_ENDPOINTS.DOCUMENTS.OCR_PAGE_IMAGE(documentId, versionId, currentPage),
      { token: authToken },
    )
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (isActive) {
          setPageImageUrl(objectUrl);
        }
      })
      .catch(() => {
        if (isActive) {
          setImageUnavailable(true);
        }
      });

    return () => {
      isActive = false;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [authToken, currentPage, currentPageMeta?.imageKey, documentId, versionId]);

  const handleSaveBlock = (updated: OCRBlock) => {
    setBlocks((previous) => previous.map((block) => (block.id === updated.id ? updated : block)));
    setToastMessage(`Đã cập nhật Block #${updated.id} thành công!`);
    setTimeout(() => setToastMessage(""), 3000);
  };

  const bboxStyle = (block: OCRBlock): React.CSSProperties => {
    const [xMin, yMin, xMax, yMax] = block.bbox;
    if (usePixelCoordinates && currentPageMeta?.width && currentPageMeta.height) {
      return {
        left: `${(xMin / currentPageMeta.width) * 100}%`,
        top: `${(yMin / currentPageMeta.height) * 100}%`,
        width: `${((xMax - xMin) / currentPageMeta.width) * 100}%`,
        height: `${((yMax - yMin) / currentPageMeta.height) * 100}%`,
      };
    }

    return {
      left: `${xMin}%`,
      top: `${yMin}%`,
      width: `${xMax}%`,
      height: `${yMax}%`,
    };
  };

  return (
    <div className="space-y-4">
      {toastMessage && (
        <div className="p-3 rounded-2xl bg-emerald-500 text-white text-xs font-bold flex items-center gap-2 shadow-rose-subtle animate-in fade-in slide-in-from-top-2">
          <CheckCircle2 className="w-4 h-4 stroke-current" />
          <span>{toastMessage}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-7 glass-panel p-4 md:p-6 rounded-3xl border border-primary-200/80 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-primary-100 dark:border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 stroke-current text-primary-600" />
              <span className="font-bold text-xs text-slate-900 dark:text-white">
                Bản render Trang {currentPage} / {totalPages}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                aria-label="Trang trước"
                onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                disabled={currentPage === 1}
                className="p-1 rounded-lg border border-primary-200 hover:bg-primary-100 disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4 stroke-current" />
              </button>
              <span className="text-xs font-mono font-bold">Trang {currentPage}</span>
              <button
                type="button"
                aria-label="Trang sau"
                onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                disabled={currentPage === totalPages}
                className="p-1 rounded-lg border border-primary-200 hover:bg-primary-100 disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4 stroke-current" />
              </button>
            </div>
          </div>

          <div
            className="relative w-full bg-slate-50 dark:bg-slate-950 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-inner select-none"
            style={
              currentPageMeta?.width && currentPageMeta.height
                ? { aspectRatio: `${currentPageMeta.width} / ${currentPageMeta.height}` }
                : { aspectRatio: "1 / 1.4" }
            }
          >
            {pageImageUrl ? (
              <img
                src={pageImageUrl}
                alt={`Ảnh OCR trang ${currentPage} của ${documentTitle}`}
                className="absolute inset-0 h-full w-full object-fill"
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center px-6 text-center text-xs text-muted-foreground">
                {imageUnavailable
                  ? "Ảnh render chưa sẵn sàng hoặc bạn không có quyền xem trang này."
                  : "Đang tải ảnh render trang…"}
              </div>
            )}

            {pageBlocks.map((block) => {
              const isSelected = selectedBlockId === block.id;
              const isLowConfidence = block.confidence < 0.9;

              return (
                <button
                  key={block.id}
                  type="button"
                  aria-label={`Chọn block ${block.id}`}
                  onClick={() => setSelectedBlockId(block.id)}
                  style={bboxStyle(block)}
                  className={`absolute rounded-lg border-2 transition-all cursor-pointer flex items-center justify-between p-1.5 text-[10px] font-mono font-bold ${
                    isSelected
                      ? "border-rose-500 bg-rose-500/20 shadow-rose-glow ring-2 ring-rose-400 z-20"
                      : isLowConfidence
                        ? "border-amber-400 bg-amber-400/15 hover:bg-amber-400/30 z-10"
                        : "border-primary-400 bg-primary-400/15 hover:bg-primary-400/30 z-0"
                  }`}
                  title={`Block #${block.id} (${(block.confidence * 100).toFixed(0)}%)`}
                >
                  <span className="bg-slate-900 text-white px-1 rounded text-[9px]">#{block.id}</span>
                  {isLowConfidence && (
                    <AlertTriangle className="w-3 h-3 stroke-current text-amber-600" />
                  )}
                </button>
              );
            })}
          </div>

          <div className="text-[11px] text-muted-foreground text-center flex items-center justify-center gap-4">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-primary-400/30 border border-primary-400" />
              <span>BBox OCR chuẩn</span>
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
            {pageBlocks.map((block) => (
              <BlockEditor
                key={block.id}
                block={block}
                isSelected={selectedBlockId === block.id}
                onSelect={() => setSelectedBlockId(block.id)}
                onSaveBlock={handleSaveBlock}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
