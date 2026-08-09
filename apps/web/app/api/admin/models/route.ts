import { NextRequest, NextResponse } from "next/server";
import { getMockUserFromRequest } from "@/lib/auth/server-helper";

export const dynamic = 'force-dynamic';

/* DEMO ONLY — Replaced when real FastAPI Admin Models endpoint is connected */

export async function GET(request: NextRequest) {
  const user = getMockUserFromRequest(request);

  if (user.role !== "admin") {
    return NextResponse.json(
      { success: false, message: "403 Forbidden — Chỉ Admin mới có quyền quản lý Models." },
      { status: 403 }
    );
  }

  const models = [
    {
      id: "mod_01",
      name: "BGE-M3 Multilingual Vector Embeddings",
      version: "v2.1.0",
      status: "active",
      dimension: 1024,
      accuracyScore: 96.4,
      deployedAt: "2026-02-01T10:00:00Z",
    },
    {
      id: "mod_02",
      name: "PaddleOCR Vietnamese Layout Parser",
      version: "v1.4.2",
      status: "active",
      dimension: 0,
      accuracyScore: 94.8,
      deployedAt: "2026-01-20T14:30:00Z",
    },
  ];

  return NextResponse.json({
    success: true,
    data: models,
  });
}
