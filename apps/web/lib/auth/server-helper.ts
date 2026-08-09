/**
 * Server-side mock auth helper.
 *
 * Quy tắc mock auth:
 * - Bearer token không parse được → null → caller phải return 401.
 * - Token sai / hết hạn → null → 401.
 * - KHÔNG BAO GIỜ fallback admin. Mọi cố ý security bypass phải fail đúng cách
 *   để test phát hiện được.
 *
 * Khi BE thật chạy, file này không còn — middleware sẽ verify JWT qua JWKS.
 */
import { parseMockToken, DEMO_USERS } from "./mock-tokens";
import type { User } from "../api/types";

export function getMockUserFromRequest(request: Request): User | null {
  const authHeader = request.headers.get("authorization") || "";
  if (!authHeader.startsWith("Bearer ")) return null;
  const token = authHeader.slice("Bearer ".length);
  const parsed = parseMockToken(token);
  if (!parsed) return null;
  const demoUser = DEMO_USERS[parsed.role];
  if (!demoUser || demoUser.email !== parsed.email) return null;
  // Map sang User domain (không expose password).
  return {
    id: demoUser.id,
    email: demoUser.email,
    fullName: demoUser.fullName,
    role: demoUser.role,
    department: demoUser.department,
    avatarUrl: demoUser.avatarUrl,
  };
}

export function requireMockUser(request: Request): { user: User } | { problem: import("../api/types").ProblemDetail } {
  const user = getMockUserFromRequest(request);
  if (!user) {
    return {
      problem: {
        type: "http://localhost:3000/problems/unauthorized",
        title: "Chưa xác thực",
        status: 401,
        detail: "Token không hợp lệ hoặc đã hết hạn.",
        code: "UNAUTHORIZED",
        requestId: crypto.randomUUID(),
      },
    };
  }
  return { user };
}
