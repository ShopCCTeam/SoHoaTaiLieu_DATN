import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/* DEMO ONLY — Replaced when real FastAPI LangChain RAG endpoint is connected */

export async function POST(request: NextRequest) {
  let body: { prompt?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      {
        type: "http://localhost:3000/problems/validation_error",
        title: "Dữ liệu không hợp lệ",
        status: 422,
        code: "VALIDATION_ERROR",
        requestId: crypto.randomUUID(),
      },
      { status: 422, headers: { "Content-Type": "application/problem+json" } },
    );
  }

  const prompt = body.prompt || "";

  // Mock response shape phải khớp OpenAPI ChatResponse (snake_case).
  const response = {
    answer: `Theo Quy chế Công tác Sinh viên (QU-CTSV/2026-01) và Hướng dẫn Xin tạm hoãn học tập, đối với câu hỏi "${prompt}":\n\n1. Sinh viên cần hoàn thành tối thiểu 80% số buổi điểm danh rèn luyện.\n2. Nộp đơn xác nhận tới Phòng CTSV trong thời hạn 14 ngày làm việc kể từ khi ban hành thông báo.`,
    citations: [
      {
        document_id: "doc_01",
        document_version_id: "docv_01",
        title: "Quy chế Đánh giá Kết quả Rèn luyện Sinh viên Đại học Chính quy",
        page_number: 1,
        chunk_id: "chk_01",
        quote:
          "Sinh viên hoàn thành chương trình rèn luyện 90 điểm trở lên được xếp loại Xuất sắc theo Quy chế...",
        score: 0.94,
      },
      {
        document_id: "doc_02",
        document_version_id: "docv_02",
        title: "Hướng dẫn Thủ tục Xin Tạm hoàn Học tập & Bảo lưu Kết quả Học tập",
        page_number: 2,
        chunk_id: "chk_02",
        quote:
          "Trường hợp xin tạm dừng học tập, sinh viên phải nộp đơn xin tạm hoãn trước khi học kỳ bắt đầu 2 tuần...",
        score: 0.88,
      },
    ],
    has_sufficient_evidence: true,
  };

  return NextResponse.json({
    success: true,
    data: response,
  });
}
