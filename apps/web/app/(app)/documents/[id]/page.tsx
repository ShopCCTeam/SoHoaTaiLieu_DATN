"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, notFound } from "next/navigation";
import { useAuthStore } from "@/lib/auth/session";
import { MOCK_DOCUMENTS, MOCK_VERSIONS } from "@/lib/mocks/fixtures";
import { Document, DocumentVersion } from "@/lib/api/types";
import { StatusBadge } from "@/components/documents/status-badge";
import { MetadataForm } from "@/components/documents/metadata-form";
import { VersionList } from "@/components/documents/version-list";
import { formatDate } from "@/lib/utils/format";
import {
  ArrowLeft,
  FileText,
  GitCommit,
  History,
  Edit3,
  Lock,
  Inbox,
} from "lucide-react";

export default function DocumentDetailPage() {
  const params = useParams();
  const rawId = params?.id;
  const docId = Array.isArray(rawId) ? rawId[0] : (rawId as string);

  const { user } = useAuthStore();

  const [document, setDocument] = useState<Document | null>(null);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "versions" | "history">("overview");
  const [loading, setLoading] = useState(true);
  const [isNotFound, setIsNotFound] = useState(false);

  useEffect(() => {
    if (!docId) return;

    let found = MOCK_DOCUMENTS.find((d) => d.id === docId);
    if (!found) {
      try {
        const stored = localStorage.getItem("custom_mock_documents");
        if (stored) {
          const list: Document[] = JSON.parse(stored);
          found = list.find((d) => d.id === docId);
        }
      } catch (e) {
        console.error(e);
      }
    }

    if (!found) {
      /* MUST-FIX 3.3: Use Next.js notFound() instead of masking bug with MOCK_DOCUMENTS[0] */
      setIsNotFound(true);
      setLoading(false);
      return;
    }

    setDocument(found);
    const vList = MOCK_VERSIONS[found.id] || [
      {
        id: `ver_${found.id}_01`,
        documentId: found.id,
        versionNumber: found.latestVersion,
        status: found.status,
        createdAt: found.createdAt,
        createdBy: "Nguyễn Văn Quản Trị",
        effectiveFrom: found.effectiveFrom,
        fileUrl: "/sample-doc.pdf",
        fileSize: found.fileSize || 1500000,
        checksum: "sha256_mock_hash_2026",
        changeSummary: "Phiên bản hiện tại đang hiển thị.",
      },
    ];
    setVersions(vList);
    setLoading(false);
  }, [docId]);

  if (isNotFound) {
    notFound();
  }

  if (loading || !document) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center space-y-4">
        <div className="w-10 h-10 border-4 border-primary-300 border-t-primary-600 rounded-full animate-spin mx-auto" />
        <p className="text-xs text-muted-foreground">Đang tải thông tin tài liệu...</p>
      </div>
    );
  }

  // Role Access Guard for Student Role
  if (user?.role === "student" && document.scope === "INTERNAL") {
    return (
      <div className="max-w-xl mx-auto my-12 glass-panel p-8 rounded-3xl border border-rose-200 text-center space-y-4 shadow-rose-subtle">
        <div className="w-14 h-14 rounded-2xl bg-rose-100 dark:bg-rose-950 flex items-center justify-center text-rose-600 mx-auto">
          <Lock className="w-7 h-7 stroke-current" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">
            403 - Giới Hạn Truy Cấp Tài Liệu Nội Bộ
          </h2>
          <p className="text-xs text-muted-foreground mt-2">
            Tài khoản Sinh viên của bạn chỉ có quyền xem các văn bản phạm vi PUBLIC hoặc STUDENT_AFFAIRS. 
            Văn bản này có phạm vi <span className="font-bold text-rose-600">INTERNAL</span>.
          </p>
        </div>
        <div className="pt-2">
          <Link
            href="/documents"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary-400 text-slate-950 font-bold text-xs shadow-rose-subtle hover:bg-primary-500 transition-all"
          >
            <ArrowLeft className="w-4 h-4 stroke-current" />
            <span>Quay lại Danh sách</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header Card */}
      <div className="glass-panel p-6 rounded-3xl border border-primary-200/80 shadow-rose-subtle space-y-4">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <Link
              href="/documents"
              className="p-2.5 rounded-2xl bg-white/80 dark:bg-slate-900 border border-primary-200 text-slate-700 hover:bg-primary-100 transition-colors mt-0.5"
              title="Quay lại danh sách"
              aria-label="Quay lại danh sách văn bản"
            >
              <ArrowLeft className="w-5 h-5 stroke-current" />
            </Link>
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={document.status} />
                <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-[10px] font-mono text-slate-700 dark:text-slate-300">
                  {document.codeNumber || document.id}
                </span>
                <span className="px-2 py-0.5 rounded-md bg-primary-100 text-slate-800 text-[10px] font-semibold">
                  Scope: {document.scope}
                </span>
              </div>
              <h1 className="text-xl md:text-2xl font-black text-slate-900 dark:text-white tracking-tight">
                {document.title}
              </h1>
              <p className="text-xs text-muted-foreground">
                Đơn vị ban hành: <span className="font-semibold text-slate-700 dark:text-slate-300">{document.issuingBody || "CTSV"}</span> • Ngày ban hành: <span className="font-mono">{formatDate(document.effectiveFrom || document.createdAt)}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href={`/documents/${document.id}/review`}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-rose-400 text-white font-bold text-xs shadow-sm hover:opacity-90 transition-all active:scale-[0.98]"
            >
              <Edit3 className="w-4 h-4 stroke-current" />
              <span>Hiệu Chỉnh BBox OCR</span>
            </Link>
          </div>
        </div>

        {/* Tab Selection Navigation */}
        <div className="flex items-center gap-2 border-t border-primary-100 dark:border-slate-800 pt-4">
          {[
            { key: "overview", label: "Tổng quan & Metadata", icon: FileText },
            { key: "versions", label: `Phiên bản (${versions.length})`, icon: GitCommit },
            { key: "history", label: "Lịch sử chỉnh sửa", icon: History },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? "bg-primary-400 text-slate-950 shadow-rose-subtle"
                    : "text-slate-600 dark:text-slate-300 hover:bg-primary-100/60"
                }`}
              >
                <Icon className="w-4 h-4 stroke-current" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && (
        <MetadataForm
          document={document}
          onSave={(updated) => setDocument(updated)}
        />
      )}

      {activeTab === "versions" && (
        versions.length > 0 ? (
          <VersionList
            documentId={document.id}
            versions={versions}
          />
        ) : (
          <div className="glass-panel p-12 rounded-3xl text-center space-y-3">
            <Inbox className="w-10 h-10 text-muted-foreground mx-auto stroke-current" />
            <p className="text-xs font-bold text-slate-700 dark:text-slate-300">Chưa có phiên bản nào khác của văn bản này.</p>
          </div>
        )
      )}

      {activeTab === "history" && (
        <div className="glass-panel p-6 rounded-3xl border border-primary-200/80 space-y-4 shadow-sm">
          <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
            <History className="w-5 h-5 stroke-current text-primary-600" />
            <span>Nhật ký Lịch sử Hệ thống (Audit Log)</span>
          </h3>
          <div className="space-y-3">
            {[
              {
                time: "2026-02-15 10:15",
                user: user?.fullName || "Nguyễn Văn Quản Trị",
                action: "Cập nhật Metadata văn bản",
                details: "Đã thay đổi ngày hiệu lực và thẻ phân loại Tags",
              },
              {
                time: "2026-02-10 09:00",
                user: "Lê Thị Chuyên Viên",
                action: "Khởi tạo tiến trình OCR PaddleOCR",
                details: "Trích xuất 6 block bboxes trang 1 & trang 2",
              },
            ].map((log, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-2xl bg-white/70 dark:bg-slate-900/70 border border-primary-100 dark:border-slate-800 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2"
              >
                <div>
                  <div className="font-bold text-slate-900 dark:text-white">{log.action}</div>
                  <div className="text-muted-foreground text-[11px] mt-0.5">{log.details}</div>
                </div>
                <div className="text-right text-[11px]">
                  <span className="font-semibold text-slate-700 dark:text-slate-300">{log.user}</span>
                  <div className="font-mono text-muted-foreground">{log.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
