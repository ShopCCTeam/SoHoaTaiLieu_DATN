import { NextResponse } from "next/server";
import { DEMO_USERS, MOCK_PASSWORD, makeMockToken } from "@/lib/auth/mock-tokens";
import { problemResponse } from "@/lib/api/problem-response";
import type { User, UserRole } from "@/lib/api/types";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  let body: { email?: string; password?: string };
  try {
    body = await request.json();
  } catch {
    return problemResponse(
      422,
      "VALIDATION_ERROR",
      "Dữ liệu không hợp lệ",
      "Body phải là JSON hợp lệ.",
    );
  }

  const { email, password } = body;
  if (!email || !password) {
    return problemResponse(
      422,
      "VALIDATION_ERROR",
      "Thiếu email hoặc password",
      "Body phải có đủ trường email và password.",
    );
  }

  // Tìm user theo email — KHÔNG fallback admin.
  const matchedEntry = Object.values(DEMO_USERS).find(
    (u) => u.email === email,
  );
  if (!matchedEntry) {
    return problemResponse(
      401,
      "UNAUTHORIZED",
      "Sai thông tin đăng nhập",
      "Email không tồn tại trong hệ thống.",
    );
  }

  // Verify password (mock).
  if (password !== MOCK_PASSWORD) {
    return problemResponse(
      401,
      "UNAUTHORIZED",
      "Sai thông tin đăng nhập",
      "Email hoặc mật khẩu không đúng.",
    );
  }

  const accessToken = makeMockToken(matchedEntry.role, matchedEntry.email);
  const refreshToken = makeMockToken(matchedEntry.role, matchedEntry.email);
  // Set HttpOnly refresh cookie — giả lập BE thật.
  const cookieValue = `rt=${refreshToken}; HttpOnly; SameSite=Lax; Path=/api/v1/auth; Max-Age=604800`;

  const user: User = {
    id: matchedEntry.id,
    email: matchedEntry.email,
    fullName: matchedEntry.fullName,
    role: matchedEntry.role,
    department: matchedEntry.department,
    avatarUrl: matchedEntry.avatarUrl,
  };

  return NextResponse.json(
    {
      success: true,
      data: {
        access_token: accessToken,
        expires_in: 900,
        user,
      },
    },
    {
      headers: {
        "Set-Cookie": cookieValue,
      },
    },
  );
}
