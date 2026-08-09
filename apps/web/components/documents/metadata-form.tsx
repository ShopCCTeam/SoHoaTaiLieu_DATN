"use client";

import React, { useState } from "react";
import { Document, DocumentType } from "@/lib/api/types";
import { useAuthStore } from "@/lib/auth/session";
import { hasPermission } from "@/lib/auth/permissions";
import { Save, Check, Shield, FileText, Calendar, Building, Tag } from "lucide-react";

interface MetadataFormProps {
  document: Document;
  onSave?: (updatedDoc: Document) => void;
}

export const MetadataForm: React.FC<MetadataFormProps> = ({
  document,
  onSave,
}) => {
  const { user } = useAuthStore();
  const canEdit = hasPermission(user?.role, "canUploadDocuments");

  const [title, setTitle] = useState(document.title);
  const [type, setType] = useState<DocumentType>(document.type);
  const [codeNumber, setCodeNumber] = useState(document.codeNumber || "");
  const [issuingBody, setIssuingBody] = useState(document.issuingBody || "");
  const [effectiveFrom, setEffectiveFrom] = useState(document.effectiveFrom || "");
  const [effectiveTo, setEffectiveTo] = useState(document.effectiveTo || "");
  const [scope, setScope] = useState(document.scope);
  const [tagsInput, setTagsInput] = useState(document.tags.join(", "));
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canEdit) return;

    const updated: Document = {
      ...document,
      title,
      type,
      codeNumber,
      issuingBody,
      effectiveFrom,
      effectiveTo,
      scope,
      tags: tagsInput.split(",").map((t) => t.trim()).filter(Boolean),
      updatedAt: new Date().toISOString(),
    };

    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
    if (onSave) onSave(updated);
  };

  return (
    <form onSubmit={handleSubmit} className="glass-panel p-6 rounded-3xl border border-primary-200/80 space-y-6 shadow-sm">
      <div className="flex items-center justify-between border-b border-primary-100 dark:border-slate-800 pb-4">
        <div>
          <h3 className="font-bold text-slate-900 dark:text-white text-base">
            Thông tin Metadata Văn bản
          </h3>
          <p className="text-xs text-muted-foreground">
            Cập nhật siêu dữ liệu tiêu chuẩn cho tìm kiếm RAG và quản lý phiên bản
          </p>
        </div>
        {savedSuccess && (
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-emerald-100 text-emerald-800 text-xs font-semibold animate-in fade-in">
            <Check className="w-4 h-4 stroke-current" />
            <span>Đã lưu thành công!</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Title */}
        <div className="md:col-span-2 space-y-1">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            Tên văn bản / Tiêu đề chính:
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={!canEdit}
            required
            className="w-full h-10 px-3 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs focus:outline-none focus:ring-2 focus:ring-primary-400 disabled:opacity-70"
          />
        </div>

        {/* Type */}
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            Loại văn bản:
          </label>
          <select
            value={type}
            onChange={(e) => setType(e.target.value as DocumentType)}
            disabled={!canEdit}
            className="w-full h-10 px-3 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-primary-400 disabled:opacity-70"
          >
            <option value="QUY_CHE">Quy chế</option>
            <option value="QUY_DINH">Quy định</option>
            <option value="THONG_BAO">Thông báo</option>
            <option value="QUYET_DINH">Quyết định</option>
            <option value="HUONG_DAN">Hướng dẫn</option>
            <option value="MAU_DON">Mẫu đơn</option>
          </select>
        </div>

        {/* Code Number */}
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            Số hiệu văn bản:
          </label>
          <input
            type="text"
            value={codeNumber}
            onChange={(e) => setCodeNumber(e.target.value)}
            disabled={!canEdit}
            className="w-full h-10 px-3 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-primary-400 disabled:opacity-70"
          />
        </div>

        {/* Issuing Body */}
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            Đơn vị ban hành:
          </label>
          <input
            type="text"
            value={issuingBody}
            onChange={(e) => setIssuingBody(e.target.value)}
            disabled={!canEdit}
            className="w-full h-10 px-3 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs focus:outline-none focus:ring-2 focus:ring-primary-400 disabled:opacity-70"
          />
        </div>

        {/* Access Scope */}
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            Phạm vi truy cập (Scope):
          </label>
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            disabled={!canEdit}
            className="w-full h-10 px-3 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-primary-400 disabled:opacity-70"
          >
            <option value="PUBLIC">Công khai (Toàn bộ Sinh viên)</option>
            <option value="STUDENT_AFFAIRS">Nội bộ Công tác Sinh viên</option>
            <option value="INTERNAL">Nội bộ Cán bộ & Quản trị viên</option>
          </select>
        </div>

        {/* Dates */}
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            Ngày hiệu lực:
          </label>
          <input
            type="date"
            value={effectiveFrom}
            onChange={(e) => setEffectiveFrom(e.target.value)}
            disabled={!canEdit}
            className="w-full h-10 px-3 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs focus:outline-none focus:ring-2 focus:ring-primary-400 disabled:opacity-70"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            Ngày hết hiệu lực (nếu có):
          </label>
          <input
            type="date"
            value={effectiveTo}
            onChange={(e) => setEffectiveTo(e.target.value)}
            disabled={!canEdit}
            className="w-full h-10 px-3 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs focus:outline-none focus:ring-2 focus:ring-primary-400 disabled:opacity-70"
          />
        </div>

        {/* Tags */}
        <div className="md:col-span-2 space-y-1">
          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            Thẻ phân loại (Tags):
          </label>
          <input
            type="text"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            disabled={!canEdit}
            placeholder="Rèn luyện, Học bổng, Khen thưởng..."
            className="w-full h-10 px-3 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs focus:outline-none focus:ring-2 focus:ring-primary-400 disabled:opacity-70"
          />
        </div>
      </div>

      {canEdit && (
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-primary-400 to-rose-400 text-slate-950 font-bold text-xs shadow-rose-subtle hover:shadow-rose-glow transition-all active:scale-[0.98]"
          >
            <Save className="w-4 h-4 stroke-current" />
            <span>Lưu Thay Đổi Metadata</span>
          </button>
        </div>
      )}
    </form>
  );
};
