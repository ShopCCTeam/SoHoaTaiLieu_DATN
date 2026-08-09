"use client";

import React from "react";
import Link from "next/link";
import { useAuthStore } from "@/lib/auth/session";
import { MOCK_DOCUMENTS } from "@/lib/mocks/fixtures";
import { StatusBadge } from "@/components/documents/status-badge";
import { formatDate } from "@/lib/utils/format";
import {
  FileText,
  Clock,
  Cpu,
  MessageSquare,
  Upload,
  ArrowUpRight,
  Sparkles,
} from "lucide-react";

export default function DashboardPage() {
  const { user } = useAuthStore();

  const totalDocs = MOCK_DOCUMENTS.length;
  const pendingReviewCount = MOCK_DOCUMENTS.filter(
    (d) => d.status === "UNDER_REVIEW" || d.status === "DRAFT",
  ).length;
  const approvedCount = MOCK_DOCUMENTS.filter(
    (d) => d.status === "APPROVED",
  ).length;

  const stats = [
    {
      title: "Tổng tài liệu số hóa",
      value: totalDocs.toString(),
      subtext: "Bao gồm tất cả các phiên bản",
      icon: <FileText className="w-5 h-5 stroke-current text-primary-700 dark:text-primary-300" />,
      bg: "bg-primary-100/70 dark:bg-slate-900/90 border-primary-200 dark:border-slate-800",
    },
    {
      title: "Chờ hiệu chỉnh OCR",
      value: pendingReviewCount.toString(),
      subtext: "Cần cán bộ kiểm tra bbox",
      icon: <Clock className="w-5 h-5 stroke-current text-amber-700 dark:text-amber-400" />,
      bg: "bg-amber-50/80 dark:bg-slate-900/90 border-amber-200 dark:border-amber-900/50",
    },
    {
      title: "Đã index RAG Vector",
      value: approvedCount.toString(),
      subtext: "Sẵn sàng cho Chatbot RAG",
      icon: <Cpu className="w-5 h-5 stroke-current text-emerald-700 dark:text-emerald-400" />,
      bg: "bg-emerald-50/80 dark:bg-slate-900/90 border-emerald-200 dark:border-emerald-900/50",
    },
    {
      title: "Truy vấn RAG hôm nay",
      value: "128",
      subtext: "+18% so với hôm qua",
      icon: <MessageSquare className="w-5 h-5 stroke-current text-sky-700 dark:text-sky-400" />,
      bg: "bg-sky-50/80 dark:bg-slate-900/90 border-sky-200 dark:border-sky-900/50",
    },
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="relative glass-panel p-6 md:p-8 rounded-3xl border border-primary-200/90 dark:border-slate-800 shadow-rose-subtle overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary-300/20 dark:bg-primary-500/10 rounded-full blur-3xl -z-10" />
        
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-200/70 dark:bg-slate-800 border border-primary-300 dark:border-slate-700 text-xs font-semibold text-slate-900 dark:text-slate-100">
              <Sparkles className="w-3.5 h-3.5 stroke-current text-primary-700 dark:text-primary-300" />
              <span>Hệ Thống Số Hóa Tài Liệu CTSV — Phase F0 Active</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-black text-slate-900 dark:text-white tracking-tight">
              Xin chào, {user?.fullName || "Người dùng"}! 👋
            </h1>
            <p className="text-xs md:text-sm text-slate-700 dark:text-slate-300 max-w-2xl">
              Bạn đang làm việc với quyền <span className="font-bold capitalize text-slate-900 dark:text-white">{user?.role}</span> ({user?.department}). 
              Dưới đây là tổng quan tài liệu Công tác sinh viên và trạng thái xử lý OCR / LangChain RAG.
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/documents/upload"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary-400 text-slate-950 font-bold text-xs shadow-rose-subtle hover:bg-primary-500 hover:shadow-rose-glow transition-all active:scale-[0.98]"
            >
              <Upload className="w-4 h-4 stroke-current" />
              <span>Số hóa File mới</span>
            </Link>

            <Link
              href="/chat"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/90 dark:bg-slate-900 border border-primary-200 dark:border-slate-700 text-slate-900 dark:text-white font-semibold text-xs hover:bg-primary-100 dark:hover:bg-slate-800 transition-all active:scale-[0.98]"
            >
              <MessageSquare className="w-4 h-4 stroke-current" />
              <span>Hỏi Trợ lý RAG</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Analytics Stat Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((item, idx) => (
          <div
            key={idx}
            className={`p-5 rounded-2xl border ${item.bg} backdrop-blur-md transition-all hover:scale-[1.02] shadow-sm`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                {item.title}
              </span>
              <div className="p-2 rounded-xl bg-white/90 dark:bg-slate-950 border border-slate-200/60 dark:border-slate-800 shadow-sm">
                {item.icon}
              </div>
            </div>
            <div className="mt-4">
              <div className="text-2xl font-black text-slate-900 dark:text-white">
                {item.value}
              </div>
              <p className="text-[11px] text-slate-600 dark:text-slate-400 mt-1 font-medium">
                {item.subtext}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Documents Section */}
      <div className="glass-panel rounded-3xl border border-primary-200/80 dark:border-slate-800 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Văn bản / Tài liệu vừa cập nhật
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
              Danh sách tài liệu Công tác sinh viên mới nhất trong hệ thống
            </p>
          </div>
          <Link
            href="/documents"
            className="inline-flex items-center gap-1 text-xs font-bold text-primary-700 hover:text-primary-800 dark:text-primary-300"
          >
            <span>Xem tất cả ({MOCK_DOCUMENTS.length})</span>
            <ArrowUpRight className="w-4 h-4 stroke-current" />
          </Link>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-primary-100 dark:border-slate-800 text-slate-500 dark:text-slate-400 uppercase text-[10px] tracking-wider font-bold">
                <th className="pb-3 px-3">Tên tài liệu / Số hiệu</th>
                <th className="pb-3 px-3">Loại văn bản</th>
                <th className="pb-3 px-3">Trạng thái</th>
                <th className="pb-3 px-3">Đơn vị ban hành</th>
                <th className="pb-3 px-3">Ngày ban hành</th>
                <th className="pb-3 px-3 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-primary-100/60 dark:divide-slate-800/60">
              {MOCK_DOCUMENTS.slice(0, 5).map((doc) => (
                <tr
                  key={doc.id}
                  className="hover:bg-primary-50/50 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <td className="py-3.5 px-3">
                    <div className="font-bold text-slate-900 dark:text-white max-w-md truncate">
                      {doc.title}
                    </div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                      {doc.codeNumber || doc.id}
                    </div>
                  </td>
                  <td className="py-3.5 px-3">
                    <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 font-mono text-[10px] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                      {doc.type}
                    </span>
                  </td>
                  <td className="py-3.5 px-3">
                    <StatusBadge status={doc.status} />
                  </td>
                  <td className="py-3.5 px-3 text-slate-700 dark:text-slate-300 font-medium">
                    {doc.issuingBody || "—"}
                  </td>
                  <td className="py-3.5 px-3 text-slate-600 dark:text-slate-400">
                    {formatDate(doc.effectiveFrom || doc.createdAt)}
                  </td>
                  <td className="py-3.5 px-3 text-right">
                    <Link
                      href={doc.status === "UNDER_REVIEW" ? `/documents/${doc.id}/review` : `/documents/${doc.id}`}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-800 border border-primary-200 dark:border-slate-700 text-slate-900 dark:text-white font-bold text-[11px] hover:bg-primary-100 dark:hover:bg-slate-700 transition-all shadow-sm"
                    >
                      <span>{doc.status === "UNDER_REVIEW" ? "Hiệu chỉnh OCR" : "Chi tiết"}</span>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
