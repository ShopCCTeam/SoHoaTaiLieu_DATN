"use client";

import React from "react";
import Link from "next/link";
import { useParams, notFound } from "next/navigation";
import { MOCK_DOCUMENTS, MOCK_OCR_BLOCKS } from "@/lib/mocks/fixtures";
import { OCRReviewPane } from "@/components/ocr/ocr-review-pane";
import { ArrowLeft, Edit3, Sparkles } from "lucide-react";

export default function DocumentOCRReviewPage() {
  const params = useParams();
  const rawId = params?.id;
  const docId = Array.isArray(rawId) ? rawId[0] : (rawId as string);

  const document = MOCK_DOCUMENTS.find((d) => d.id === docId);

  /* MUST-FIX 3.3: Use Next.js notFound() if document id does not exist */
  if (!document) {
    notFound();
  }

  const blocks = MOCK_OCR_BLOCKS[docId] || MOCK_OCR_BLOCKS["doc_02"];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 glass-panel p-6 rounded-3xl border border-primary-200/80 shadow-rose-subtle">
        <div className="flex items-center gap-4">
          <Link
            href={`/documents/${docId}`}
            className="p-2.5 rounded-2xl bg-white/80 dark:bg-slate-900 border border-primary-200 text-slate-700 hover:bg-primary-100 transition-colors"
            title="Quay lại chi tiết văn bản"
            aria-label="Quay lại chi tiết văn bản"
          >
            <ArrowLeft className="w-5 h-5 stroke-current" />
          </Link>
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[11px] font-bold mb-1">
              <Sparkles className="w-3.5 h-3.5 stroke-current text-amber-600" />
              <span>Chế độ Hiệu chỉnh OCR BBox (PaddleOCR/Tesseract)</span>
            </div>
            <h1 className="text-xl font-black text-slate-900 dark:text-white tracking-tight">
              {document.title}
            </h1>
          </div>
        </div>
      </div>

      {/* Main Review Split View */}
      <OCRReviewPane
        documentTitle={document.title}
        initialBlocks={blocks}
      />
    </div>
  );
}
