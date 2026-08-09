"use client";

import React, { useState } from "react";
import { OCRBlock } from "@/lib/api/types";
import { useAuthStore } from "@/lib/auth/session";
import { Check, Edit3, CheckCircle2, RotateCcw, Sparkles, AlertCircle } from "lucide-react";

interface BlockEditorProps {
  block: OCRBlock;
  isSelected: boolean;
  onSelect: () => void;
  onSaveBlock: (updatedBlock: OCRBlock) => void;
}

export const BlockEditor: React.FC<BlockEditorProps> = ({
  block,
  isSelected,
  onSelect,
  onSaveBlock,
}) => {
  const { user } = useAuthStore();
  const [text, setText] = useState(block.text);
  const [isEditing, setIsEditing] = useState(false);
  const [showDiff, setShowDiff] = useState(false);

  const hasChanged = text !== block.text || (block.originalText && text !== block.originalText);

  const handleSave = () => {
    const updated: OCRBlock = {
      ...block,
      text,
      isEdited: true,
      editedBy: user?.fullName || "Bạn (Cán bộ CTSV)",
      editedAt: new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }),
      originalText: block.originalText || block.text,
    };
    onSaveBlock(updated);
    setIsEditing(false);
    setShowDiff(false);
  };

  const handleReset = () => {
    if (block.originalText) {
      setText(block.originalText);
    }
  };

  return (
    <div
      onClick={onSelect}
      className={`p-4 rounded-2xl border transition-all cursor-pointer ${
        isSelected
          ? "border-primary-400 bg-primary-50/70 shadow-rose-subtle ring-2 ring-primary-300"
          : "border-primary-200/70 bg-white/80 dark:bg-slate-900/80 hover:border-primary-300"
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-[10px] font-bold text-slate-700 dark:text-slate-300">
            Block #{block.id} (Trang {block.pageNumber})
          </span>

          {/* Confidence Badge */}
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
              block.confidence < 0.9
                ? "bg-amber-100 text-amber-800 border border-amber-300"
                : "bg-emerald-100 text-emerald-800"
            }`}
          >
            Độ tin cậy: {(block.confidence * 100).toFixed(0)}%
          </span>

          {block.isEdited && (
            <span className="px-2 py-0.5 rounded bg-primary-200 text-slate-900 text-[10px] font-bold inline-flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 stroke-current text-primary-700" />
              <span>Đã chỉnh sửa bởi bạn</span>
            </span>
          )}
        </div>

        {!isEditing && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(true);
            }}
            className="p-1 rounded-lg text-slate-500 hover:text-primary-700 hover:bg-primary-100 transition-colors text-xs font-semibold flex items-center gap-1"
          >
            <Edit3 className="w-3.5 h-3.5 stroke-current" />
            <span>Sửa</span>
          </button>
        )}
      </div>

      {isEditing ? (
        <div className="space-y-3 pt-1" onClick={(e) => e.stopPropagation()}>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={3}
            className="w-full p-2.5 rounded-xl border border-primary-300 bg-white dark:bg-slate-950 text-xs font-sans focus:outline-none focus:ring-2 focus:ring-primary-400"
          />

          {/* Diff View */}
          {block.originalText && block.originalText !== text && (
            <div className="p-2.5 rounded-xl bg-amber-50/80 border border-amber-200 text-[11px] space-y-1">
              <div className="font-semibold text-amber-900 flex items-center gap-1">
                <Sparkles className="w-3 h-3 stroke-current text-amber-700" />
                <span>So sánh với bản OCR gốc:</span>
              </div>
              <div className="text-rose-700 line-through font-mono">- {block.originalText}</div>
              <div className="text-emerald-700 font-mono">+ {text}</div>
            </div>
          )}

          <div className="flex items-center justify-end gap-2">
            {block.originalText && (
              <button
                type="button"
                onClick={handleReset}
                className="px-2.5 py-1 rounded-lg border border-slate-200 text-[11px] font-semibold hover:bg-slate-100 text-slate-600 flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3 stroke-current" />
                <span>Khôi phục gốc</span>
              </button>
            )}
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="px-2.5 py-1 rounded-lg border border-slate-200 text-[11px] font-semibold hover:bg-slate-100"
            >
              Hủy
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-3 py-1 rounded-lg bg-primary-400 text-slate-950 font-bold text-[11px] shadow-sm hover:bg-primary-500 flex items-center gap-1"
            >
              <Check className="w-3.5 h-3.5 stroke-current" />
              <span>Xác nhận Sửa</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="text-xs text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed font-sans mt-1">
          {block.text}
        </div>
      )}

      {block.editedBy && !isEditing && (
        <div className="mt-2 pt-2 border-t border-primary-100 dark:border-slate-800 text-[10px] text-muted-foreground flex items-center justify-between">
          <span>Chỉnh sửa lần cuối bởi: {block.editedBy}</span>
          <span>{block.editedAt}</span>
        </div>
      )}
    </div>
  );
};
