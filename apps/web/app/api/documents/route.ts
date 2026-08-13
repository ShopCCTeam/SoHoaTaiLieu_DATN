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
  const q = searchParams.get("q");
  const keyword = searchParams.get("keyword");
  const tags = searchParams.getAll("tags").map((tag) => tag.trim().toLowerCase()).filter(Boolean);

  if (status && status !== "ALL") {
    docs = docs.filter((d) => d.status === status);
  }
  if (type && type !== "ALL") {
    docs = docs.filter((d) => d.type === type);
  }
  if (q) {
    const query = q.toLowerCase();
    docs = docs.filter(
      (d) => d.title.toLowerCase().includes(query) || d.codeNumber?.toLowerCase().includes(query),
    );
  }
  if (keyword) {
    const metadataKeyword = keyword.toLowerCase();
    docs = docs.filter(
      (d) =>
        d.title.toLowerCase().includes(metadataKeyword) ||
        d.codeNumber?.toLowerCase().includes(metadataKeyword) ||
        d.issuingBody?.toLowerCase().includes(metadataKeyword) ||
        d.tags.some((tag) => tag.toLowerCase().includes(metadataKeyword)),
    );
  }
  if (tags.length > 0) {
    docs = docs.filter((d) => {
      const documentTags = new Set(d.tags.map((tag) => tag.toLowerCase()));
      return tags.every((tag) => documentTags.has(tag));
    });
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
