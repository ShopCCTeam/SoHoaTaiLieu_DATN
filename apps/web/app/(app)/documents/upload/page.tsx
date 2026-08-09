"use client";

import React from "react";
import Link from "next/link";
import { UploadDropzone } from "@/components/documents/upload-dropzone";
import { ArrowLeft, UploadCloud } from "lucide-react";

export default function DocumentUploadPage() {
  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between glass-panel p-6 rounded-3xl border border-primary-200/80 shadow-rose-subtle">
        <div className="flex items-center gap-4">
          <Link
            href="/documents"
            className="p-2.5 rounded-2xl bg-white/80 dark:bg-slate-900 border border-primary-200 text-slate-700 hover:bg-primary-100 transition-colors"
            title="Quay lại danh sách"
          >
            <ArrowLeft className="w-5 h-5 stroke-current" />
          </Link>
          <div>
            <h1 className="text-xl font-black text-slate-900 dark:text-white tracking-tight">
              Tải lên & Số hóa Tài liệu CTSV
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Hệ thống tự động trích xuất nội dung văn bản qua PaddleOCR / Tesseract OCR và tính toán SHA-256 Checksum.
            </p>
          </div>
        </div>
      </div>

      {/* Upload Dropzone */}
      <UploadDropzone />
    </div>
  );
}
