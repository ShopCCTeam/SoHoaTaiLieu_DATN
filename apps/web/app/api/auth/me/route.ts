import { NextResponse } from "next/server";
import { requireMockUser } from "@/lib/auth/server-helper";
import { problemResponse } from "@/lib/api/problem-response";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
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
  return NextResponse.json({
    success: true,
    data: auth.user,
  });
}
