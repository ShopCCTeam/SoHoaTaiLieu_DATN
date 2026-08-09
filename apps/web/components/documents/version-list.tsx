"use client";

import React, { useState } from "react";
import Link from "next/link";
import { DocumentVersion, DocumentStatus } from "@/lib/api/types";
import { StatusBadge } from "./status-badge";
import { formatDate, formatFileSize } from "@/lib/utils/format";
import { useAuthStore } from "@/lib/auth/session";
import { hasPermission } from "@/lib/auth/permissions";
import {
  GitCommit,
  Plus,
  Play,
  CheckCircle2,
  ArrowRight,
  FileText,
  Sparkles,
  RefreshCw,
} from "lucide-react";

interface VersionListProps {
  documentId: string;
  versions: DocumentVersion[];
  onTriggerOCR?: (versionId: string) => void;
  onApproveVersion?: (versionId: string) => void;
  onCreateNewVersion?: () => void;
}

export const VersionList: React.FC<VersionListProps> = ({
  documentId,
  versions: initialVersions,
  onTriggerOCR,
  onApproveVersion,
  onCreateNewVersion,
}) => {
  const { user } = useAuthStore();
  const [versions, setVersions] = useState<DocumentVersion[]>(initialVersions);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const canApprove = hasPermission(user?.role, "canApproveDocument");
  const canUpload = hasPermission(user?.role, "canUploadDocuments");

  const handleTriggerOCR = (versionId: string) => {
    setProcessingId(versionId);
    setTimeout(() => {
      setVersions((prev) =>
        prev.map((v) => (v.id === versionId ? { ...v, status: "review" as DocumentStatus } : v))
      );
      setProcessingId(null);
      if (onTriggerOCR) onTriggerOCR(versionId);
    }, 1000);
  };

  const handleApprove = (versionId: string) => {
    setProcessingId(versionId);
    setTimeout(() => {
      setVersions((prev) =>
        prev.map((v) => (v.id === versionId ? { ...v, status: "approved" as DocumentStatus } : v))
      );
      setProcessingId(null);
      if (onApproveVersion) onApproveVersion(versionId);
    }, 1000);
  };

  return (
    <div className="glass-panel p-6 rounded-3xl border border-primary-200/80 space-y-6 shadow-sm">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-primary-100 dark:border-slate-800 pb-4">
        <div>
          <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
            <GitCommit className="w-5 h-5 stroke-current text-primary-600" />
            <span>Lịch sử các Phiên bản (Document Versions)</span>
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Quản lý cây phiên bản, theo dõi thay thế văn bản và kích hoạt OCR / Duyệt RAG
          </p>
        </div>

        {canUpload && (
          <button
            onClick={onCreateNewVersion}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary-400 text-slate-950 font-bold text-xs shadow-rose-subtle hover:bg-primary-500 transition-all active:scale-[0.98]"
          >
            <Plus className="w-4 h-4 stroke-current" />
            <span>Tạo Phiên bản v{versions.length + 1}</span>
          </button>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-primary-100 dark:border-slate-800 text-muted-foreground uppercase text-[10px] tracking-wider font-bold">
              <th className="pb-3 px-3">Phiên bản</th>
              <th className="pb-3 px-3">Trạng thái</th>
              <th className="pb-3 px-3">Người tạo & Ngày tạo</th>
              <th className="pb-3 px-3">Quan hệ Thay thế</th>
              <th className="pb-3 px-3">Tóm tắt Thay đổi</th>
              <th className="pb-3 px-3 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-primary-100/60 dark:divide-slate-800/60">
            {versions.map((ver) => {
              const isProcessing = processingId === ver.id;
              return (
                <tr key={ver.id} className="hover:bg-primary-50/40 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="py-3.5 px-3 font-mono font-bold text-slate-900 dark:text-white">
                    v{ver.versionNumber}.0
                  </td>
                  <td className="py-3.5 px-3">
                    <StatusBadge status={ver.status} />
                  </td>
                  <td className="py-3.5 px-3">
                    <div className="font-semibold text-slate-800 dark:text-slate-200">
                      {ver.createdBy}
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono">
                      {formatDate(ver.createdAt)}
                    </div>
                  </td>
                  <td className="py-3.5 px-3">
                    {ver.supersedesVersionId ? (
                      <span className="px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 text-[10px] font-medium">
                        Thay thế v{ver.versionNumber - 1}.0
                      </span>
                    ) : ver.supersededByVersionId ? (
                      <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 text-[10px] font-medium">
                        Đã bị thay thế bởi v{ver.versionNumber + 1}.0
                      </span>
                    ) : (
                      <span className="text-muted-foreground text-[11px]">—</span>
                    )}
                  </td>
                  <td className="py-3.5 px-3 text-slate-700 dark:text-slate-300 max-w-xs truncate">
                    {ver.changeSummary || "Khởi tạo ban đầu"}
                  </td>
                  <td className="py-3.5 px-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {ver.status === "DRAFT" && (
                        <button
                          onClick={() => handleTriggerOCR(ver.id)}
                          disabled={isProcessing}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-pink-500 text-white font-bold text-[11px] hover:bg-pink-600 transition-all shadow-sm disabled:opacity-50"
                        >
                          {isProcessing ? (
                            <RefreshCw className="w-3.5 h-3.5 stroke-current animate-spin" />
                          ) : (
                            <Play className="w-3.5 h-3.5 stroke-current fill-current" />
                          )}
                          <span>Kích hoạt OCR</span>
                        </button>
                      )}

                      {ver.status === "UNDER_REVIEW" && canApprove && (
                        <button
                          onClick={() => handleApprove(ver.id)}
                          disabled={isProcessing}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-bold text-[11px] hover:bg-emerald-700 transition-all shadow-sm disabled:opacity-50"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5 stroke-current" />
                          <span>Duyệt Ban Hành</span>
                        </button>
                      )}

                      <Link
                        href={`/documents/${documentId}/review`}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary-100 text-slate-900 font-medium text-[11px] hover:bg-primary-200 transition-all"
                      >
                        <span>Mở BBox Viewer</span>
                      </Link>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
