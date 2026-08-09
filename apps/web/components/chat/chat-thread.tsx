"use client";

import React, { useState, useEffect, useRef } from "react";
import { ChatMessage, Citation } from "@/lib/api/types";
import { AnswerCard } from "./answer-card";
import { Send, Sparkles, Trash2 } from "lucide-react";

interface ChatThreadProps {
  messages?: ChatMessage[];
  onSendMessage?: (prompt: string) => void;
  isGenerating?: boolean;
}

export const ChatThread: React.FC<ChatThreadProps> = ({
  messages: externalMessages,
  onSendMessage,
  isGenerating: externalIsGenerating = false,
}) => {
  const [internalMessages, setInternalMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [internalIsTyping, setInternalIsTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const isControlled = Boolean(externalMessages && onSendMessage);
  const messages = isControlled ? externalMessages! : internalMessages;
  const isTyping = isControlled ? externalIsGenerating : internalIsTyping;

  // Initial Welcome Message & Sync with localStorage for standalone mode
  useEffect(() => {
    if (isControlled) return;

    try {
      const stored = localStorage.getItem("ctsv_chat_messages");
      if (stored) {
        setInternalMessages(JSON.parse(stored));
        return;
      }
    } catch (e) {
      console.error(e);
    }

    const defaultMsg: ChatMessage = {
      id: "msg_welcome",
      sender: "assistant",
      content:
        "Xin chào! Tôi là Trợ lý AI hỏi đáp văn bản Công tác Sinh viên (được huấn luyện trên mô hình LangChain RAG & Vector Database). Bạn cần tra cứu thủ tục học vụ, học bổng, điểm rèn luyện hay quy định nào?",
      timestamp: new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }),
    };
    setInternalMessages([defaultMsg]);
  }, [isControlled]);

  useEffect(() => {
    if (!isControlled && internalMessages.length > 0) {
      try {
        localStorage.setItem("ctsv_chat_messages", JSON.stringify(internalMessages));
      } catch (e) {
        console.error(e);
      }
    }
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isControlled]);

  const handleSendMessage = (textToSend?: string) => {
    const queryText = textToSend || input;
    if (!queryText.trim() || isTyping) return;

    if (isControlled && onSendMessage) {
      onSendMessage(queryText);
      setInput("");
      return;
    }

    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}`,
      sender: "user",
      content: queryText,
      timestamp: new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }),
    };

    setInternalMessages((prev) => [...prev, userMsg]);
    setInput("");
    setInternalIsTyping(true);

    // Simulate RAG Backend Answer Generation with Citations
    setTimeout(() => {
      let answerText = "";
      let citations: Citation[] = [];

      const qLower = queryText.toLowerCase();

      if (qLower.includes("nghỉ học") || qLower.includes("tạm hoãn") || qLower.includes("bảo lưu")) {
        answerText =
          "Theo Hướng dẫn Thủ tục Xin Tạm hoãn Học tập & Bảo lưu Kết quả Học tập (Số HD-CTSV/2026-05):\n\n1. **Điều kiện:** Sinh viên được xin tạm dừng học tập nếu ốm đau dài ngày (có xác nhận y tế), thi hành nghĩa vụ quân sự hoặc có lý do cá nhân hợp lệ (đã học tối thiểu 01 học kỳ).\n2. **Quy trình nộp:** Sinh viên truy cập Cổng CTSV (ctsv.example.edu.vn), chọn 'Đơn xin tạm dừng học tập', tải minh chứng PDF/ảnh và gửi trực tuyến.\n3. **Thời gian xử lý:** Phòng CTSV duyệt trong vòng 03 ngày làm việc.";

        citations = [
          {
            documentId: "doc_02",
            documentTitle: "Hướng dẫn Thủ tục Xin Tạm hoãn Học tập",
            documentVersionId: "ver_02_01",
            pageNumber: 1,
            chunkId: "mock-chunk-02-1",
            quote: "Sinh viên vì lý do cá nhân khác nhưng phải học ít nhất 01 học kỳ tại trường và không thuộc diện bị buộc xuất học.",
            score: 0.96,
          },
          {
            documentId: "doc_02",
            documentTitle: "Hướng dẫn Thủ tục Xin Tạm hoãn Học tập",
            documentVersionId: "ver_02_01",
            pageNumber: 2,
            chunkId: "mock-chunk-02-2",
            quote: "Phòng CTSV tiếp nhận và duyệt hồ sơ trong 03 ngày làm việc.",
            score: 0.92,
          },
        ];
      } else if (qLower.includes("học bổng")) {
        answerText =
          "Căn cứ Quy định Xét cấp Học bổng Khuyến khích Học tập Học kỳ II 2025-2026 (Số QĐ-HB/2026-02):\n\n- **Học bổng Loại Khá:** Điểm TBCHP ≥ 3.20/4.00, Điểm Rèn luyện ≥ 80 điểm (Tốt).\n- **Học bổng Loại Xuất sắc:** Điểm TBCHP ≥ 3.60/4.00, Điểm Rèn luyện ≥ 90 điểm (Xuất sắc).\n- Danh sách do Hội đồng Học bổng xét duyệt từ cao xuống thấp đến hết chỉ tiêu.";

        citations = [
          {
            documentId: "doc_03",
            documentTitle: "Quy định Xét cấp Học bổng Khuyến khích Học tập",
            documentVersionId: "ver_03_01",
            pageNumber: 1,
            chunkId: "mock-chunk-03-1",
            quote: "Điểm trung bình chung học tập đạt từ 3.20/4.00 trở lên và điểm rèn luyện đạt loại Tốt.",
            score: 0.98,
          },
        ];
      } else if (qLower.includes("rèn luyện") || qLower.includes("điểm")) {
        answerText =
          "Căn cứ Quy chế Đánh giá Kết quả Rèn luyện Sinh viên Đại học Chính quy (Số QĐ-CTSV/2026-01):\n\nĐiểm rèn luyện được đánh giá theo 5 tiêu chí tổng cộng 100 điểm. Sinh viên tham gia NCKH, cuộc thi cấp Trường hoặc tình nguyện được cộng từ 5 đến 15 điểm rèn luyện.";

        citations = [
          {
            documentId: "doc_01",
            documentTitle: "Quy chế Đánh giá Kết quả Rèn luyện Sinh viên",
            documentVersionId: "ver_01_02",
            pageNumber: 3,
            chunkId: "mock-chunk-01-3",
            quote: "Cập nhật tiêu chí cộng điểm rèn luyện cho hoạt động nghiên cứu khoa học và tình nguyện 2026.",
            score: 0.95,
          },
        ];
      } else {
        answerText =
          "Xin lỗi, câu hỏi của bạn không nằm trong phạm vi văn bản Công tác Sinh viên hiện có trong cơ sở dữ liệu Vector RAG. Bạn có thể thử tra cứu lại với các từ khóa liên quan đến 'bảo lưu', 'học bổng' hoặc 'điểm rèn luyện'.";
      }

      const botMsg: ChatMessage = {
        id: `msg_${Date.now()}`,
        sender: "assistant",
        content: answerText,
        timestamp: new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }),
        citations,
      };

      setInternalMessages((prev) => [...prev, botMsg]);
      setInternalIsTyping(false);
    }, 1000);
  };

  const handleClearHistory = () => {
    localStorage.removeItem("ctsv_chat_messages");
    const defaultMsg: ChatMessage = {
      id: "msg_welcome",
      sender: "assistant",
      content: "Đã xóa lịch sử trò chuyện. Bạn cần trợ giúp gì về văn bản CTSV?",
      timestamp: new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }),
    };
    setInternalMessages([defaultMsg]);
  };

  const suggestions = [
    "Thủ tục nghỉ học tạm thời và bảo lưu kết quả?",
    "Điều kiện xét học bổng khuyến khích học tập?",
    "Tiêu chí tính điểm rèn luyện sinh viên?",
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] max-w-5xl mx-auto space-y-4">
      {/* Header Info & Clear Button */}
      <div className="flex items-center justify-between glass-panel px-6 py-3 rounded-2xl border border-primary-200/80 shadow-sm flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-bold text-slate-900 dark:text-white">
            Trợ lý Chatbot RAG LangChain CTSV Online
          </span>
        </div>

        <button
          onClick={handleClearHistory}
          aria-label="Xóa lịch sử trò chuyện"
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl border border-rose-200 bg-rose-50 text-rose-700 text-xs font-semibold hover:bg-rose-100 transition-all"
          title="Xóa lịch sử hội thoại"
        >
          <Trash2 className="w-3.5 h-3.5 stroke-current" />
          <span>Xóa Lịch Sử</span>
        </button>
      </div>

      {/* Messages Thread Container */}
      <div className="flex-1 overflow-y-auto px-2 py-4 space-y-4">
        {messages.map((msg) => (
          <AnswerCard key={msg.id} message={msg} />
        ))}

        {isTyping && (
          <div className="flex justify-start">
            <div className="glass-panel p-4 rounded-3xl border border-primary-200 text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2 shadow-sm">
              <Sparkles className="w-4 h-4 stroke-current text-primary-600 animate-spin" />
              <span>Đang truy vấn Vector Database & Tổng hợp câu trả lời...</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Quick Suggestions Pills */}
      <div className="flex flex-wrap items-center gap-2 flex-shrink-0 px-2">
        <span className="text-[11px] font-bold text-muted-foreground uppercase">
          Gợi ý:
        </span>
        {suggestions.map((sug, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(sug)}
            className="px-3 py-1 rounded-xl bg-white/80 dark:bg-slate-900/80 border border-primary-200 text-[11px] font-semibold text-slate-800 dark:text-slate-200 hover:bg-primary-100 hover:border-primary-300 transition-all"
          >
            {sug}
          </button>
        ))}
      </div>

      {/* Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendMessage();
        }}
        className="glass-panel p-2 rounded-2xl border border-primary-300 flex items-center gap-2 shadow-rose-subtle flex-shrink-0"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Hỏi bất kỳ câu hỏi nào về quy chế, bảo lưu, học bổng..."
          className="flex-1 h-11 px-4 bg-transparent text-xs md:text-sm text-foreground focus:outline-none placeholder:text-muted-foreground"
        />
        <button
          type="submit"
          disabled={!input.trim() || isTyping}
          aria-label="Gửi câu hỏi RAG"
          className="h-11 px-5 rounded-xl bg-gradient-to-r from-primary-400 to-rose-400 text-slate-950 font-bold text-xs shadow-rose-subtle hover:shadow-rose-glow transition-all flex items-center gap-1.5 disabled:opacity-50 active:scale-[0.98]"
        >
          <span>Gửi</span>
          <Send className="w-4 h-4 stroke-current" />
        </button>
      </form>
    </div>
  );
};
