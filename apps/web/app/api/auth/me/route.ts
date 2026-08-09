import { NextResponse } from "next/server";
import { DEMO_USERS } from "@/lib/auth/session";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const authHeader = request.headers.get("authorization") || "";
  let user = DEMO_USERS.admin;

  if (authHeader.includes("staff")) {
    user = DEMO_USERS.staff;
  } else if (authHeader.includes("student")) {
    user = DEMO_USERS.student;
  }

  return NextResponse.json({
    success: true,
    user,
  });
}
