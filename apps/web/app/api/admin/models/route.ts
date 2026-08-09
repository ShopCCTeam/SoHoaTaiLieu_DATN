import { NextRequest, NextResponse } from "next/server";
import { requireMockUser } from "@/lib/auth/server-helper";
import { problemResponse } from "@/lib/api/problem-response";

export const dynamic = "force-dynamic";

/* DEMO ONLY — Replaced when real FastAPI Admin Models endpoint is connected */

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

  if (auth.user.role !== "admin") {
    return problemResponse(
      403,
      "FORBIDDEN",
      "Chỉ Admin mới có quyền quản lý Models.",
    );
  }

  const models = [
    {
      id: "mod_01",
      name: "BGE-M3 Multilingual Vector Embeddings",
      version: "v2.1.0",
      is_active: true,
      dimension: 1024,
      accuracy_score: 96.4,
      deployed_at: "2026-02-01T10:00:00Z",
    },
    {
      id: "mod_02",
      name: "PaddleOCR Vietnamese Layout Parser",
      version: "v1.4.2",
      is_active: true,
      dimension: 0,
      accuracy_score: 94.8,
      deployed_at: "2026-01-20T14:30:00Z",
    },
  ];

  return NextResponse.json({
    success: true,
    data: models,
  });
}
