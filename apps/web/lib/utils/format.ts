import { DocumentStatus } from "../api/types";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}


export function formatDate(dateString?: string): string {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(date);
  } catch {
    return dateString;
  }
}

export function formatDateTime(dateString?: string): string {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  } catch {
    return dateString;
  }
}

export function formatFileSize(bytes?: number): string {
  if (bytes === undefined || bytes === null || isNaN(bytes)) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function getStatusLabel(status: DocumentStatus): string {
  const map: Record<DocumentStatus, string> = {
    DRAFT: "Bản Nháp",
    UNDER_REVIEW: "Chờ Hiệu Chỉnh",
    APPROVED: "Đã Ban Hành",
    ARCHIVED: "Lưu Trữ",
  };
  return map[status] || status;
}

export function getStatusBadgeVariant(status: DocumentStatus): {
  bgClass: string;
  textClass: string;
  borderClass: string;
  dotClass: string;
} {
  switch (status) {
    case "APPROVED":
      return {
        bgClass: "bg-emerald-500/10",
        textClass: "text-emerald-700 dark:text-emerald-400",
        borderClass: "border-emerald-500/20",
        dotClass: "bg-emerald-500",
      };
    case "UNDER_REVIEW":
      return {
        bgClass: "bg-amber-500/10",
        textClass: "text-amber-700 dark:text-amber-400",
        borderClass: "border-amber-500/20",
        dotClass: "bg-amber-500",
      };
    case "DRAFT":
      return {
        bgClass: "bg-slate-500/10",
        textClass: "text-slate-700 dark:text-slate-400",
        borderClass: "border-slate-500/20",
        dotClass: "bg-slate-400",
      };
    case "ARCHIVED":
      return {
        bgClass: "bg-rose-500/10",
        textClass: "text-rose-700 dark:text-rose-400",
        borderClass: "border-rose-500/20",
        dotClass: "bg-rose-500",
      };
  }
}
