"use client";

import React, { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { validateFile, validateFileMagicBytes, calculateChecksum } from "@/lib/utils/file";
import { formatFileSize } from "@/lib/utils/format";
import { DocumentType } from "@/lib/api/types";
import {
  UploadCloud,
  FileCheck,
  AlertCircle,
  Hash,
  Sparkles,
  ArrowRight,
  RefreshCw,
} from "lucide-react";

export const UploadDropzone: React.FC = () => {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [checksum, setChecksum] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isUploading, setIsUploading] = useState<boolean>(false);

  // Metadata form states
  const [title, setTitle] = useState<string>("");
  const [type, setType] = useState<DocumentType>("THONG_BAO");
  const [codeNumber, setCodeNumber] = useState<string>("");
  const [issuingBody, setIssuingBody] = useState<string>("Phòng Công tác Sinh viên");
  const [tags, setTags] = useState<string>("Số hóa, CTSV");

  const handleFileSelect = async (file: File) => {
    setError("");
    const validation = validateFile(file);
    if (!validation.valid) {
      setError(validation.error || "File không hợp lệ");
      setSelectedFile(null);
      setChecksum("");
      return;
    }

    /* NEED-FIX 4.4: Check PDF Magic Bytes header %PDF- */
    const magicValidation = await validateFileMagicBytes(file);
    if (!magicValidation.valid) {
      setError(magicValidation.error || "File bị lỗi định dạng header.");
      setSelectedFile(null);
      setChecksum("");
      return;
    }

    setSelectedFile(file);
    setTitle(file.name.replace(/\.[^/.]+$/, ""));
    setCodeNumber(`TB-CTSV/2026-${Math.floor(Math.random() * 90 + 10)}`);

    // Calculate checksum
    try {
      const hash = await calculateChecksum(file);
      setChecksum(hash);
    } catch {
      setChecksum("sha256_mock_hash_calculated");
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadProgress(10);

    // Simulate progress
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 90) {
          clearInterval(interval);
          return 90;
        }
        return prev + 20;
      });
    }, 200);

    setTimeout(() => {
      clearInterval(interval);
      setUploadProgress(100);

      // Create new mock document
      const newDoc = {
        id: `doc_${Date.now()}`,
        title: title || selectedFile.name,
        type,
        status: "review" as const, // Put into review state for OCR editing test
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        latestVersion: 1,
        scope: "PUBLIC",
        codeNumber: codeNumber || `QĐ-CTSV/${Date.now()}`,
        issuingBody: issuingBody || "Phòng CTSV",
        effectiveFrom: new Date().toISOString().split("T")[0],
        tags: tags.split(",").map((t) => t.trim()),
        authorId: "usr_admin_01",
        fileUrl: "/sample-doc.pdf",
        fileSize: selectedFile.size,
        pageCount: Math.floor(Math.random() * 5 + 1),
      };

      // Save to localStorage for persistence
      try {
        const stored = localStorage.getItem("custom_mock_documents");
        const list = stored ? JSON.parse(stored) : [];
        list.unshift(newDoc);
        localStorage.setItem("custom_mock_documents", JSON.stringify(list));
      } catch (err) {
        console.error(err);
      }

      setIsUploading(false);
      router.push(`/documents/${newDoc.id}/review`);
    }, 1500);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Dropzone Container */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`glass-panel p-8 md:p-12 rounded-3xl border-2 border-dashed transition-all cursor-pointer text-center relative overflow-hidden ${
          selectedFile
            ? "border-primary-400 bg-primary-50/50"
            : "border-primary-200 hover:border-primary-400 hover:bg-primary-50/30"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.webp,.docx"
          onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
          className="hidden"
        />

        {selectedFile ? (
          <div className="space-y-3">
            <div className="w-14 h-14 rounded-2xl bg-primary-200 text-primary-800 flex items-center justify-center mx-auto shadow-sm">
              <FileCheck className="w-7 h-7 stroke-current" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white text-base truncate max-w-lg mx-auto">
                {selectedFile.name}
              </h3>
              <p className="text-xs text-muted-foreground mt-1">
                Kích thước: {formatFileSize(selectedFile.size)} • Loại: {selectedFile.type || "PDF Document"}
              </p>
            </div>

            {checksum && (
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/80 dark:bg-slate-900 border border-primary-200 text-[11px] font-mono text-slate-700 dark:text-slate-300">
                <Hash className="w-3.5 h-3.5 stroke-current text-primary-600" />
                <span>SHA-256: {checksum.substring(0, 24)}...</span>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-primary-200 to-rose-300 text-slate-900 flex items-center justify-center mx-auto shadow-rose-subtle">
              <UploadCloud className="w-8 h-8 stroke-current" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white text-lg">
                Kéo thả tập tin văn bản Công tác Sinh viên vào đây
              </h3>
              <p className="text-xs text-muted-foreground mt-1">
                Hỗ trợ định dạng PDF, PNG, JPG, WEBP, DOCX (Dung lượng tối đa 50MB)
              </p>
            </div>
            <button
              type="button"
              aria-label="Chọn file từ máy tính"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary-400 text-slate-950 font-bold text-xs shadow-rose-subtle hover:bg-primary-500 transition-all"
            >
              <span>Chọn File từ máy tính</span>
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 stroke-current flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Metadata Preview & Form */}
      {selectedFile && (
        <form onSubmit={handleSubmit} className="glass-panel p-6 rounded-3xl border border-primary-200/80 space-y-6 shadow-sm">
          <div className="border-b border-primary-100 dark:border-slate-800 pb-3 flex items-center gap-2">
            <Sparkles className="w-4 h-4 stroke-current text-primary-600" />
            <h3 className="font-bold text-slate-900 dark:text-white text-sm">
              Xác nhận Metadata Văn bản trước khi Kích hoạt OCR
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Tên văn bản / Tiêu đề:
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                className="w-full h-10 px-3 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs focus:outline-none focus:ring-2 focus:ring-primary-400"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Loại văn bản:
              </label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value as DocumentType)}
                className="w-full h-10 px-3 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-primary-400"
              >
                <option value="QUY_CHE">Quy chế</option>
                <option value="QUY_DINH">Quy định</option>
                <option value="THONG_BAO">Thông báo</option>
                <option value="QUYET_DINH">Quyết định</option>
                <option value="HUONG_DAN">Hướng dẫn</option>
                <option value="MAU_DON">Mẫu đơn</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Số hiệu văn bản:
              </label>
              <input
                type="text"
                value={codeNumber}
                onChange={(e) => setCodeNumber(e.target.value)}
                className="w-full h-10 px-3 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs focus:outline-none focus:ring-2 focus:ring-primary-400 font-mono"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Đơn vị ban hành:
              </label>
              <input
                type="text"
                value={issuingBody}
                onChange={(e) => setIssuingBody(e.target.value)}
                className="w-full h-10 px-3 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs focus:outline-none focus:ring-2 focus:ring-primary-400"
              />
            </div>
          </div>

          {/* Upload Progress Bar */}
          {isUploading && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <RefreshCw className="w-3.5 h-3.5 stroke-current animate-spin text-primary-600" />
                  <span>Đang tải lên & Kích hoạt tiến trình OCR...</span>
                </span>
                <span className="font-mono text-primary-700">{uploadProgress}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-primary-100 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary-400 to-rose-400 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setSelectedFile(null)}
              className="px-4 py-2 rounded-xl border border-primary-200 text-xs font-semibold hover:bg-primary-50 transition-all"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              disabled={isUploading}
              aria-label="Xác nhận và bắt đầu số hóa OCR"
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-primary-400 to-rose-400 text-slate-950 font-bold text-xs shadow-rose-subtle hover:shadow-rose-glow transition-all flex items-center gap-2 active:scale-[0.98] disabled:opacity-50"
            >
              <span>Xác nhận & Bắt đầu Số hóa OCR</span>
              <ArrowRight className="w-4 h-4 stroke-current" />
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
