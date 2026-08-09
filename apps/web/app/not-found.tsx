import React from "react";
import Link from "next/link";
import { FileQuestion, ArrowLeft } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <div className="glass-panel p-8 rounded-3xl max-w-md w-full text-center space-y-4 border border-primary-200 shadow-rose-subtle">
        <div className="w-12 h-12 rounded-2xl bg-primary-100 flex items-center justify-center text-primary-700 mx-auto">
          <FileQuestion className="w-6 h-6 stroke-current" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">
            404 - Trang Không Tồn Tại
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            Đường dẫn tài liệu hoặc trang bạn tìm kiếm không có trong hệ thống CTSV.
          </p>
        </div>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary-400 text-slate-950 font-bold text-xs shadow-rose-subtle hover:bg-primary-500 transition-all"
        >
          <ArrowLeft className="w-4 h-4 stroke-current" />
          <span>Về Trang Chủ</span>
        </Link>
      </div>
    </div>
  );
}
