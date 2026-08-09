import { NextRequest, NextResponse } from "next/server";
import { getMockUserFromRequest } from "@/lib/auth/server-helper";

export const dynamic = 'force-dynamic';

/* DEMO ONLY — Replaced when real FastAPI Admin Users endpoint is connected */

export async function GET(request: NextRequest) {
  const user = getMockUserFromRequest(request);

  if (user.role !== "admin") {
    return NextResponse.json(
      { success: false, message: "403 Forbidden — Chỉ Admin mới có quyền quản lý người dùng." },
      { status: 403 }
    );
  }

  const users = [
    {
      id: "u_admin",
      fullName: "Nguyễn Văn Quản Trị",
      email: "admin@phenikaa-uni.edu.vn",
      role: "admin",
      department: "Phòng CTSV & CNTT",
      status: "active",
      createdAt: "2026-01-01T00:00:00Z",
    },
    {
      id: "u_staff",
      fullName: "Lê Thị Chuyên Viên",
      email: "staff@phenikaa-uni.edu.vn",
      role: "staff",
      department: "Phòng Công tác Sinh viên",
      status: "active",
      createdAt: "2026-01-10T00:00:00Z",
    },
    {
      id: "u_student",
      fullName: "Trần Văn Sinh Viên",
      email: "student@phenikaa-uni.edu.vn",
      role: "student",
      department: "Khoa CNTT - K16",
      status: "active",
      createdAt: "2026-02-01T00:00:00Z",
    },
  ];

  return NextResponse.json({
    success: true,
    data: users,
  });
}
