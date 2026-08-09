/**
 * RFC 7807 Problem Details helper cho Next.js route handlers (mock).
 *
 * Khi BE thật chạy, server sẽ tự trả Content-Type: application/problem+json.
 * Mock route cũng phải trả đúng format để FE code path xác thực giống prod.
 */
import { NextResponse } from "next/server";
import type { ProblemDetail } from "@/lib/api/types";

export function problemResponse(
  status: number,
  code: ProblemDetail["code"],
  title: string,
  detail?: string | null,
  requestId?: string | null,
  errors?: ProblemDetail["errors"] | null,
): NextResponse {
  const body: ProblemDetail = {
    type: `http://localhost:3000/problems/${code.toLowerCase()}`,
    title,
    status,
    ...(detail ? { detail } : {}),
    code,
    requestId: requestId ?? cryptoRandomId(),
    ...(errors ? { errors } : {}),
  };
  return NextResponse.json(body, {
    status,
    headers: { "Content-Type": "application/problem+json" },
  });
}

function cryptoRandomId(): string {
  // RFC 9562 — fallback khi crypto.randomUUID không có sẵn (Node 18 cũ).
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `req_${Math.random().toString(36).slice(2)}_${Date.now().toString(36)}`;
}
