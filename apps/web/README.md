# Hệ Thống Số Hoá & Quản Lý Tài Liệu Công Tác Sinh Viên (Next.js 14 Frontend)

Đồ án tốt nghiệp đại học: **"Xây dựng hệ thống số hoá và quản lý tài liệu Công tác sinh viên ứng dụng OCR, RAG và LangChain"**

## 🌟 Công Nghệ Sử Dụng (Tech Stack)
- **Framework:** Next.js 14+ (App Router), React 18, TypeScript Strict
- **Design & Styling:** Tailwind CSS, Framer Motion (2026 Rose Tint Aesthetics: `#FDF3F4`, `#FED3DD`, `#F4ABB4`)
- **State Management:** TanStack Query v5, Zustand v5
- **Form & Validation:** React Hook Form + Zod
- **Icons:** Lucide React (SVG monochrome, tuân thủ strict WCAG)
- **Testing:** Vitest + React Testing Library, Playwright (E2E)

> **Lưu ý**: Project không dùng Radix UI / shadcn. Tất cả component là **tự viết** dựa trên Tailwind + Framer Motion. Nếu cần primitive phức tạp (Dialog, Popover), cân nhắc thêm dependency vào `apps/web/package.json` trước khi dùng.

## 🚀 Hướng Dẫn Chạy Dự Án

### 1. Cài đặt các gói phụ thuộc
```bash
pnpm install
```

### 2. Chạy môi trường phát triển (Development Server)
```bash
pnpm dev
```
Giao diện sẽ chạy tại `http://localhost:3000`.

### 3. Chạy Kiểm Thử (Unit Tests)
```bash
pnpm test          # chạy 1 lần
pnpm test:watch    # chạy watch mode
```

### 4. Build Production
```bash
pnpm build
```

### 5. Lint + Type-check
```bash
pnpm lint
pnpm typecheck
```

### 6. End-to-End test (Playwright)
```bash
pnpm test:e2e
```

## 🔐 Tài Khoản Demo (Role Matrix)

> ⚠️ **Chỉ dùng cho demo / development**. Trong production dùng tài khoản thật qua OAuth/JWT.

- **Admin**: `admin@example.edu.vn` (Quyền cao nhất: Xem, Upload, Sửa OCR, Duyệt, Quản trị hệ thống & Models)
- **Staff (Cán bộ CTSV)**: `staff@example.edu.vn` (Quyền: Xem tất cả, Upload, Sửa OCR, Duyệt)
- **Student (Sinh viên)**: `student@example.edu.vn` (Quyền: Xem tài liệu công khai/theo scope, Chatbot RAG)

Password demo mặc định: `demo_password` (mock store, không qua BE thật).
