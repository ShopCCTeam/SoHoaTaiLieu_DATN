import { NextResponse } from "next/server";
import { DEMO_USERS } from "@/lib/auth/session";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email } = body;

    const user = Object.values(DEMO_USERS).find((u) => u.email === email) || DEMO_USERS.admin;

    return NextResponse.json({
      success: true,
      accessToken: `mock_jwt_token_${user.role}_2026`,
      user,
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Lỗi đăng nhập hệ thống" },
      { status: 400 }
    );
  }
}
