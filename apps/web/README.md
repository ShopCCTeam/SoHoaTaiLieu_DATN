# Hệ Thống Số Hóa & Quản Lý Tài Liệu Công Tác Sinh Viên (Next.js 14 Frontend)

Đồ án tốt nghiệp đại học: **"Xây dựng hệ thống số hóa và quản lý tài liệu Công tác sinh viên ứng dụng OCR, RAG và LangChain"**

## 🌟 Công Nghệ Sử Dụng (Tech Stack)
- **Framework:** Next.js 14+ (App Router), React 18, TypeScript Strict
- **Design & Styling:** Tailwind CSS, Radix UI / shadcn/ui primitives, Framer Motion (2026 Rose Tint Aesthetics: `#FDF3F4`, `#FED3DD`, `#F4ABB4`)
- **State Management:** TanStack Query v5, Zustand v5
- **Form & Validation:** React Hook Form + Zod
- **Icons:** Lucide React (SVG monochrome adaptives, tuân thủ strict WCAG & user guidelines)
- **Testing:** Vitest + React Testing Library

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
pnpm test
```

### 4. Build Production
```bash
pnpm build
```

## 🔐 Tài Khoản Demo (Role Matrix)
- **Admin**: `admin@phenikaa-uni.edu.vn` (Quyền cao nhất: Xem, Upload, Sửa OCR, Duyệt, Quản trị hệ thống & Models)
- **Staff (Cán bộ CTSV)**: `staff@phenikaa-uni.edu.vn` (Quyền: Xem tất cả, Upload, Sửa OCR, Duyệt)
- **Student (Sinh viên)**: `student@phenikaa-uni.edu.vn` (Quyền: Xem tài liệu công khai/theo scope, Chatbot RAG)
