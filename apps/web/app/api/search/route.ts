import { NextRequest, NextResponse } from "next/server";
import { MOCK_DOCUMENTS } from "@/lib/mocks/fixtures";

export const dynamic = "force-dynamic";

/* DEMO ONLY — Replaced when real FastAPI RAG search endpoint is connected */

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q") || "";

  // SearchResult shape — phải match OpenAPI sau khi Phase 1 định nghĩa.
  // MVP: trả document + score + snippet + pageNumber.
  const results = [
    {
      document: MOCK_DOCUMENTS[0],
      score: 0.94,
      snippet:
        "Sinh viên hoàn thành chương trình rèn luyện 90 điểm trở lên được xếp loại Xuất sắc theo Quy chế...",
      pageNumber: 1,
    },
    {
      document: MOCK_DOCUMENTS[1],
      score: 0.88,
      snippet:
        "Trường hợp xin tạm dừng học tập, sinh viên phải nộp đơn xin tạm hoãn trước khi học kỳ bắt đầu 2 tuần...",
      pageNumber: 2,
    },
    {
      document: MOCK_DOCUMENTS[2],
      score: 0.82,
      snippet:
        "Hạn nộp hồ sơ xét học bổng Khuyến khích học tập kỳ 1 năm học 2026-2027 kết thúc vào ngày 15/03/2026...",
      pageNumber: 1,
    },
  ];

  return NextResponse.json({
    success: true,
    data: results,
    total: results.length,
  });
}
