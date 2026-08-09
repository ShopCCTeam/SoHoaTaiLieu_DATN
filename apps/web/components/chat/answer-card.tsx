"use client";

import React, { useState } from "react";
import { ChatMessage } from "@/lib/api/types";
import { CitationChip } from "./citation-chip";
import { Sparkles, BookOpen, ThumbsUp, ThumbsDown, Copy, Check } from "lucide-react";

interface AnswerCardProps {
  message: ChatMessage;
}

export const AnswerCard: React.FC<AnswerCardProps> = ({ message }) => {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isUser = message.sender === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-2xl px-5 py-3.5 rounded-3xl bg-gradient-to-r from-primary-400 to-rose-400 text-slate-950 font-medium text-xs md:text-sm shadow-rose-subtle space-y-1">
          <div>{message.content}</div>
          <div className="text-[10px] text-slate-800 opacity-75 text-right font-mono">
            {message.timestamp}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-3xl glass-panel p-5 md:p-6 rounded-3xl border border-primary-200/90 shadow-sm space-y-4">
        {/* Assistant Header */}
        <div className="flex items-center justify-between border-b border-primary-100 dark:border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-xl bg-gradient-to-tr from-primary-300 to-rose-400 flex items-center justify-center text-slate-950 shadow-sm">
              <Sparkles className="w-4 h-4 stroke-current" />
            </div>
            <div>
              <span className="font-bold text-xs text-slate-900 dark:text-white">
                Trợ lý RAG LangChain CTSV
              </span>
              <span className="text-[10px] text-primary-700 dark:text-primary-300 ml-2 font-mono">
                Model: GPT-4o-mini + Qdrant
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-lg hover:bg-primary-100 text-slate-500 hover:text-slate-900 transition-colors"
              title="Sao chép câu trả lời"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 stroke-current text-emerald-600" />
              ) : (
                <Copy className="w-3.5 h-3.5 stroke-current" />
              )}
            </button>
            <button
              onClick={() => setFeedback("up")}
              className={`p-1.5 rounded-lg hover:bg-primary-100 transition-colors ${
                feedback === "up" ? "text-emerald-600 bg-emerald-50" : "text-slate-500"
              }`}
              title="Hữu ích"
            >
              <ThumbsUp className="w-3.5 h-3.5 stroke-current" />
            </button>
            <button
              onClick={() => setFeedback("down")}
              className={`p-1.5 rounded-lg hover:bg-rose-50 transition-colors ${
                feedback === "down" ? "text-rose-600 bg-rose-50" : "text-slate-500"
              }`}
              title="Chưa chính xác"
            >
              <ThumbsDown className="w-3.5 h-3.5 stroke-current" />
            </button>
          </div>
        </div>

        {/* Message Content */}
        <div className="text-xs md:text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-sans whitespace-pre-wrap">
          {message.content}
        </div>

        {/* Citations Section */}
        {message.citations && message.citations.length > 0 && (
          <div className="pt-3 border-t border-primary-100 dark:border-slate-800 space-y-2">
            <div className="text-[11px] font-bold tracking-wider text-muted-foreground uppercase flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 stroke-current text-primary-600" />
              <span>Nguồn trích dẫn (Citations - RAG Grounding):</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {message.citations.map((cite, idx) => (
                <CitationChip key={idx} citation={cite} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
