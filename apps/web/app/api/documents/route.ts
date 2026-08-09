import { NextRequest, NextResponse } from "next/server";
import { MOCK_DOCUMENTS } from "@/lib/mocks/fixtures";
import { requireMockUser } from "@/lib/auth/server-helper";
import { problemResponse } from "@/lib/api/problem-response";

export const dynamic = "force-dynamic";

/* DEMO ONLY — Replaced when real FastAPI backend endpoint /documents is connected */

export async function GET(request: NextRequest) {
  const auth = requireMockUser(request);
  if ("problem" in auth) {
    return problemResponse(
      auth.problem.status,
      auth.problem.code,
      auth.problem.title,
      auth.problem.detail,
      auth.problem.requestId,
    );
  }

  const user = auth.user;
  // Role-based scoping check
  let docs = [...MOCK_DOCUMENTS];
  if (user.role === "student") {
    docs = docs.filter(
      (d) => d.scope === "PUBLIC" || d.scope === "STUDENT_AFFAIRS",
    );
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
        d.tags.some((t) => t.toLowerCase().includes(q)),
    );
  }

  // Return shape phải khớp OpenAPI (snake_case envelope).
  return NextResponse.json({
    success: true,
    data: docs,
    total: docs.length,
    page: 1,
    limit: docs.length,
  });
}

export async function POST(request: NextRequest) {
  const auth = requireMockUser(request);
  if ("problem" in auth) {
    return problemResponse(
      auth.problem.status,
      auth.problem.code,
      auth.problem.title,
      auth.problem.detail,
      auth.problem.requestId,
    );
  }

  const user = auth.user;
  if (user.role === "student") {
    return problemResponse(
      403,
      "FORBIDDEN",
      "Sinh viên không có quyền upload văn bản.",
    );
  }

  // Mock create document — trả UploadResponse (snake_case).
  // BE thật sẽ enqueue OCR job và trả 202 Accepted + job_id.
  const newDoc = {
    document_id: `doc_${Date.now()}`,
    job_id: `job_${Date.now()}`,
    status: "QUEUED" as const,
  };
  return NextResponse.json(
    {
      success: true,
      data: newDoc,
    },
    { status: 202 },
  );
}
