import React from "react";
import { Loader2 } from "lucide-react";

export default function LoadingPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="w-8 h-8 stroke-current text-primary-500 animate-spin" />
        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
          Đang tải dữ liệu số hóa...
        </span>
      </div>
    </div>
  );
}
