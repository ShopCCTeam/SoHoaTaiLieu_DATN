import { NextRequest, NextResponse } from "next/server";

export const dynamic = 'force-dynamic';

/* DEMO ONLY — Replaced when real FastAPI LangChain RAG endpoint is connected */

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const prompt = body.prompt || "";

    const response = {
      answer: `Theo Quy chế Công tác Sinh viên (QU-CTSV/2026-01) và Hướng dẫn Xin tạm hoãn học tập, đối với câu hỏi "${prompt}":\n\n1. Sinh viên cần hoàn thành tối thiểu 80% số buổi điểm danh rèn luyện.\n2. nộp đơn xác nhận tới Phòng CTSV trong thời hạn 14 ngày làm việc kể từ khi ban hành thông báo.`,
      citations: [
        {
          documentId: "doc_01",
          documentTitle: "Quy chế Đánh giá Kết quả Rèn luyện Sinh viên Đại học Chính quy",
          pageNumber: 1,
          relevanceScore: 0.94,
          quote: "Sinh viên hoàn thành chương trình rèn luyện 90 điểm trở lên được xếp loại Xuất sắc theo Quy chế...",
        },
        {
          documentId: "doc_02",
          documentTitle: "Hướng dẫn Thủ tục Xin Tạm hoàn Học tập & Bảo lưu Kết quả Học tập",
          pageNumber: 2,
          relevanceScore: 0.88,
          quote: "Trường hợp xin tạm dừng học tập, sinh viên phải nộp đơn xin tạm hoãn trước khi học kỳ bắt đầu 2 tuần...",
        },
      ],
    };

    return NextResponse.json({
      success: true,
      data: response,
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, message: "Dữ liệu truy vấn không hợp lệ" },
      { status: 400 }
    );
  }
}
