import { NextRequest, NextResponse } from "next/server";
import { MOCK_DOCUMENTS } from "@/lib/mocks/fixtures";
import { getMockUserFromRequest } from "@/lib/auth/server-helper";
import { Document } from "@/lib/api/types";

export const dynamic = 'force-dynamic';

/* DEMO ONLY — Replaced when real FastAPI backend endpoint /documents is connected */

export async function GET(request: NextRequest) {
  const user = getMockUserFromRequest(request);

  // Role-based scoping check
  let docs = [...MOCK_DOCUMENTS];
  if (user.role === "student") {
    docs = docs.filter((d) => d.scope === "PUBLIC" || d.scope === "STUDENT_AFFAIRS");
  }

  const { searchParams } = new URL(request.url);
  const status = searchParams.get("status");
  const type = searchParams.get("type");
  const query = searchParams.get("query");

  if (status && status !== "ALL") {
    docs = docs.filter((d) => d.status === status);
  }
  if (type && type !== "ALL") {
    docs = docs.filter((d) => d.type === type);
  }
  if (query) {
    const q = query.toLowerCase();
    docs = docs.filter(
      (d) =>
        d.title.toLowerCase().includes(q) ||
        d.codeNumber?.toLowerCase().includes(q) ||
        d.issuingBody?.toLowerCase().includes(q) ||
        d.tags.some((t) => t.toLowerCase().includes(q))
    );
  }

  return NextResponse.json({
    success: true,
    data: docs,
    total: docs.length,
  });
}

export async function POST(request: NextRequest) {
  const user = getMockUserFromRequest(request);

  if (user.role === "student") {
    return NextResponse.json(
      { success: false, message: "Sinh viên không có quyền upload văn bản." },
      { status: 403 }
    );
  }

  try {
    const body = await request.json();
    const newDoc: Document = {
      id: `doc_${Date.now()}`,
      title: body.title || "Văn bản mới tải lên",
      type: body.type || "THONG_BAO",
      status: "processing",
      scope: body.scope || "STUDENT_AFFAIRS",
      effectiveFrom: body.effectiveFrom || new Date().toISOString().split("T")[0],
      issuingBody: body.issuingBody || "Phòng CTSV",
      latestVersion: 1,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      tags: body.tags || ["Số hóa"],
      authorId: user.id || "usr_admin_01",
      fileUrl: "/sample-doc.pdf",
      fileSize: 1024000,
    };

    /* DEMO MOCK HANDLER — Replaces when real FastAPI BE is connected */
    MOCK_DOCUMENTS.unshift(newDoc);

    return NextResponse.json({
      success: true,
      data: newDoc,
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, message: "Dữ liệu không hợp lệ" },
      { status: 400 }
    );
  }
}
