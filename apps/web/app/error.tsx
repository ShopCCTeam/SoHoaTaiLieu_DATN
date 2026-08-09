"use client";

import React, { useEffect } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Telemetry & Diagnostic error logging hook
    console.error("[Telemetry Exception Captured]:", {
      message: error.message,
      stack: error.stack,
      digest: error.digest,
      timestamp: new Date().toISOString(),
      userAgent: typeof window !== "undefined" ? window.navigator.userAgent : "SSR",
    });
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <div className="glass-panel p-8 rounded-3xl max-w-md w-full text-center space-y-4 border border-rose-200 shadow-rose-subtle">
        <div className="w-12 h-12 rounded-2xl bg-rose-100 dark:bg-rose-950 flex items-center justify-center text-rose-600 mx-auto">
          <AlertCircle className="w-6 h-6 stroke-current" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">
            Đã xảy ra lỗi hệ thống!
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            {error.message || "Hệ thống gặp sự cố trong quá trình xử lý yêu cầu."}
          </p>
          {error.digest && (
            <p className="text-[10px] font-mono text-slate-400 mt-2">
              Digest ID: {error.digest}
            </p>
          )}
        </div>
        <button
          onClick={() => reset()}
          aria-label="Thử lại thao tác"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary-400 text-slate-950 font-bold text-xs shadow-rose-subtle hover:bg-primary-500 transition-all"
        >
          <RefreshCw className="w-4 h-4 stroke-current" />
          <span>Thử lại</span>
        </button>
      </div>
    </div>
  );
}
