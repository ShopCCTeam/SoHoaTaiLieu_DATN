import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User, UserRole } from "../api/types";

export const DEMO_USERS: Record<UserRole, User> = {
  admin: {
    id: "usr_admin_01",
    email: "admin@example.edu.vn",
    fullName: "Nguyễn Văn Quản Trị",
    role: "admin",
    scopes: ["ALL"],
    department: "Phòng Công tác Sinh viên & CNTT",
    avatarUrl: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150",
  },
  staff: {
    id: "usr_staff_01",
    email: "staff@example.edu.vn",
    fullName: "Lê Thị Chuyên Viên",
    role: "staff",
    scopes: ["ALL"],
    department: "Phòng Công tác Sinh viên",
    avatarUrl: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150",
  },
  student: {
    id: "usr_student_01",
    email: "student@example.edu.vn",
    fullName: "Trần Minh Sinh Viên",
    role: "student",
    scopes: ["PUBLIC", "STUDENT_AFFAIRS"],
    department: "Khoa Công nghệ Thông tin",
    avatarUrl: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150",
  },
};

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, role?: UserRole) => void;
  switchRole: (role: UserRole) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: DEMO_USERS.admin, // Default to admin for seamless evaluation
      token: "mock_jwt_token_admin_2026",
      isAuthenticated: true,
      login: (email: string, role: UserRole = "admin") => {
        const foundRole = (Object.keys(DEMO_USERS) as UserRole[]).find(
          (r) => DEMO_USERS[r].email === email
        ) || role;
        
        const demoUser = DEMO_USERS[foundRole];
        set({
          user: demoUser,
          token: `mock_jwt_token_${foundRole}_2026`,
          isAuthenticated: true,
        });
      },
      switchRole: (role: UserRole) => {
        const demoUser = DEMO_USERS[role];
        set({
          user: demoUser,
          token: `mock_jwt_token_${role}_2026`,
          isAuthenticated: true,
        });
      },
      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        });
      },
    }),
    {
      name: "ctsv_auth_session",
    }
  )
);
