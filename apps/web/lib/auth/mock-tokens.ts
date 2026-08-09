/**
 * Mock token store. Token format: `mock_<role>_<email>`.
 * Server-side route dùng để resolve role từ Authorization header.
 *
 * SECURITY: Mock này CHỈ dùng cho FE dev. Khi BE thật chạy, mock auth
 * route sẽ không còn — token sẽ do BE ký.
 */
import type { UserRole } from "../api/types";

const MOCK_TOKEN_PREFIX = "mock_";

export function makeMockToken(role: UserRole, email: string): string {
  // Token = base64(role:email) để giả lập ký tự có chữ ký.
  const raw = `${role}:${email}`;
  return `mock_${Buffer.from(raw).toString("base64url")}`;
}

export function parseMockToken(
  token: string | null | undefined,
): { role: UserRole; email: string } | null {
  if (!token?.startsWith(MOCK_TOKEN_PREFIX)) return null;
  const payload = token.slice(MOCK_TOKEN_PREFIX.length);
  try {
    const decoded = Buffer.from(payload, "base64url").toString("utf-8");
    const [role, email] = decoded.split(":");
    if (!role || !email) return null;
    if (role !== "admin" && role !== "staff" && role !== "student") return null;
    return { role: role as UserRole, email };
  } catch {
    return null;
  }
}

/**
 * Demo user database (mock).
 * Password cho mỗi user = "Demo@2026" (chỉ dùng mock).
 */
export const MOCK_PASSWORD = "Demo@2026";

export interface DemoUser {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  department: string;
  avatarUrl: string;
  password: string;
}

export const DEMO_USERS: Record<UserRole, DemoUser> = {
  admin: {
    id: "usr_admin_01",
    email: "admin@example.edu.vn",
    fullName: "Nguyễn Văn Quản Trị",
    role: "admin",
    department: "Phòng Công tác Sinh viên & CNTT",
    avatarUrl:
      "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150",
    password: MOCK_PASSWORD,
  },
  staff: {
    id: "usr_staff_01",
    email: "staff@example.edu.vn",
    fullName: "Lê Thị Chuyên Viên",
    role: "staff",
    department: "Phòng Công tác Sinh viên",
    avatarUrl:
      "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150",
    password: MOCK_PASSWORD,
  },
  student: {
    id: "usr_student_01",
    email: "student@example.edu.vn",
    fullName: "Trần Minh Sinh Viên",
    role: "student",
    department: "Khoa Công nghệ Thông tin",
    avatarUrl:
      "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150",
    password: MOCK_PASSWORD,
  },
};
