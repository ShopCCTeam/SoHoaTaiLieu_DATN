"use client";

import React, { useState, useEffect } from "react";
import { ChatThread } from "@/components/chat/chat-thread";
import { useChatRAGMutation } from "@/lib/api/queries";
import { ChatMessage } from "@/lib/api/types";
import { Bot } from "lucide-react";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("chat_thread_history");
      if (stored) {
        setMessages(JSON.parse(stored));
        return;
      }
    } catch (e) {
      console.error(e);
    }

    setMessages([
      {
        id: "msg_welcome",
        sender: "assistant",
        content:
          "Xin chào! Tôi là Trợ lý AI Trợ giúp Quy chế & Số hóa Tài liệu Công tác Sinh viên (RAG LangChain). Bạn có thể hỏi tôi về quy định rèn luyện, thủ tục xin tạm hoãn học tập, học bổng, hoặc bất kỳ quy chế sinh viên nào.",
        timestamp: "2026-02-15 08:00",
      },
    ]);
  }, []);

  const chatMutation = useChatRAGMutation();

  const handleSendMessage = async (prompt: string) => {
    const userMsg: ChatMessage = {
      id: `msg_u_${Date.now()}`,
      sender: "user",
      content: prompt,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const updated = [...messages, userMsg];
    setMessages(updated);

    try {
      const data = await chatMutation.mutateAsync(prompt);
      const botMsg: ChatMessage = {
        id: `msg_b_${Date.now()}`,
        sender: "assistant",
        content: data.answer,
        citations: data.citations,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      const finalMessages = [...updated, botMsg];
      setMessages(finalMessages);
      try {
        localStorage.setItem("chat_thread_history", JSON.stringify(finalMessages));
      } catch (e) {
        console.error(e);
      }
    } catch (error) {
      const errorMsg: ChatMessage = {
        id: `msg_err_${Date.now()}`,
        sender: "assistant",
        content: "Không thể kết nối dịch vụ RAG LangChain. Vui lòng kiểm tra lại mạng hoặc máy chủ.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages([...updated, errorMsg]);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto flex flex-col h-[calc(100vh-100px)]">
      {/* Header Banner */}
      <div className="glass-panel p-4 md:p-6 rounded-3xl border border-primary-200/80 shadow-rose-subtle flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-primary-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-[11px] font-bold">
              <Bot className="w-3.5 h-3.5 stroke-current text-primary-600 dark:text-primary-400" />
              <span>Trợ Lý Hỏi Đáp RAG LangChain (Phase F5 Active)</span>
            </div>
            <h1 className="text-xl font-black text-slate-900 dark:text-white tracking-tight">
              Trợ lý AI Trợ giúp Quy chế CTSV
            </h1>
          </div>
        </div>
      </div>

      {/* Main Chat Thread */}
      <div className="flex-1 min-h-0">
        <ChatThread
          messages={messages}
          onSendMessage={handleSendMessage}
          isGenerating={chatMutation.isPending}
        />
      </div>
    </div>
  );
}
