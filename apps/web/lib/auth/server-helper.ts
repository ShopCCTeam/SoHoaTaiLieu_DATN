import { NextRequest } from "next/server";
import { DEMO_USERS } from "@/lib/auth/session";

/**
 * Server-side helper to extract mock user from request headers
 * DEMO ONLY — Replaced when real FastAPI backend with JWT validation is connected
 */
export function getMockUserFromRequest(request: NextRequest) {
  const authHeader = request.headers.get("authorization") || "";
  if (authHeader.includes("staff")) {
    return DEMO_USERS.staff;
  }
  if (authHeader.includes("student")) {
    return DEMO_USERS.student;
  }
  return DEMO_USERS.admin;
}
