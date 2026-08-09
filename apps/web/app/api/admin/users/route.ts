import { NextRequest, NextResponse } from "next/server";
import { requireMockUser } from "@/lib/auth/server-helper";
import { problemResponse } from "@/lib/api/problem-response";

export const dynamic = "force-dynamic";

/* DEMO ONLY — Replaced when real FastAPI Admin Users endpoint is connected */

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
      "Chỉ Admin mới có quyền quản lý người dùng.",
    );
  }

  // Trả snake_case envelope (FE mapper sẽ convert sang camelCase domain).
  const users = [
    {
      id: "u_admin",
      full_name: "Nguyễn Văn Quản Trị",
      email: "admin@example.edu.vn",
      role: "admin",
      department: "Phòng CTSV & CNTT",
    },
    {
      id: "u_staff",
      full_name: "Lê Thị Chuyên Viên",
      email: "staff@example.edu.vn",
      role: "staff",
      department: "Phòng Công tác Sinh viên",
    },
    {
      id: "u_student",
      full_name: "Trần Văn Sinh Viên",
      email: "student@example.edu.vn",
      role: "student",
      department: "Khoa CNTT - K16",
    },
  ];

  return NextResponse.json({
    success: true,
    data: users,
  });
}
