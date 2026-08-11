# Antigravity Global Project Context & Rules (`GEMINI.md`)

> **Entry point chính cho Antigravity AI Agent** làm việc trong workspace `SoHoaTaiLieu_DATN`.

## 📌 Tổng Quan Dự Án
**Tên dự án**: Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên  
**Tech Stack**: Next.js 14 (Frontend) + FastAPI / Python 3.11 (Backend) + PostgreSQL 16 / pgvector + Celery + MinIO.  
**Tính năng cốt lõi**: OCR (PaddleOCR fine-tuned) + RAG (LangChain + BGE-M3 + Ollama) + RBAC 3 roles (`admin`, `staff`, `student`).

---

## ⚡ Quy Tắc Tuyệt Đối Của Người Dùng (Global User Rules)
1. **ICONS**: **Không dùng icon màu. Bắt buộc phải dùng icon SVG** (Lucide React SVG components hoặc custom SVG vector).
2. **NGÔN NGỮ GIAO TIẾP**: 100% tiếng Việt với người dùng. Code identifier bằng tiếng Anh.
3. **KHÔNG COMMIT PHÁ HUỶ**: `.env*`, `node_modules/`, `.next/`, `data/**`, `models/**`, PDF mẫu, model checkpoints.

---

## 📚 Bảng Điều Hướng Hệ Thống Rules (`.agents/rules/`)

Agent làm việc phải tuân thủ các file quy chuẩn tương ứng trong thư mục `.agents/rules/`:

| STT | File Rule | Phạm Vi & Khi Nào Đọc |
|---|---|---|
| 00 | [`00-communication.md`](file:///E:/SoHoaTaiLieu_DATN/.agents/rules/00-communication.md) | **Mọi session**: Ngôn ngữ giao tiếp, tone, đặt tên, style, icon SVG rule. |
| 01 | [`01-design-principles.md`](file:///E:/SoHoaTaiLieu_DATN/.agents/rules/01-design-principles.md) | **Mọi session**: Nguyên tắc SOLID, Clean Architecture 4 layers, Design Patterns. |
| 02 | [`02-frontend-nextjs.md`](file:///E:/SoHoaTaiLieu_DATN/.agents/rules/02-frontend-nextjs.md) | **Sửa FE (`apps/web`)**: Next.js 14 App Router, React 18, Zustand, TanStack Query. |
| 03 | [`03-backend-api.md`](file:///E:/SoHoaTaiLieu_DATN/.agents/rules/03-backend-api.md) | **Sửa BE (`apps/api`)**: FastAPI, OpenAPI contract-first, Auth cookie, RFC 7807 error. |
| 04 | [`04-database-rag-ocr.md`](file:///E:/SoHoaTaiLieu_DATN/.agents/rules/04-database-rag-ocr.md) | **Sửa DB / AI**: PostgreSQL pgvector, RAG Pipeline (LangChain+Ollama), PaddleOCR. |
| 05 | [`05-testing.md`](file:///E:/SoHoaTaiLieu_DATN/.agents/rules/05-testing.md) | **Khi viết test**: TDD pattern (RED-GREEN-REFACTOR), Vitest, pytest, Playwright. |
| 06 | [`06-security.md`](file:///E:/SoHoaTaiLieu_DATN/.agents/rules/06-security.md) | **Bảo mật**: Auth, JWT, RBAC 3 roles, input validation magic bytes, rate limit. |
| 07 | [`07-skill-activation.md`](file:///E:/SoHoaTaiLieu_DATN/.agents/rules/07-skill-activation.md) | **Trước khi làm task**: Tra cứu & kích hoạt 27 Agent Skills phù hợp. |
| 08 | [`08-governance.md`](file:///E:/SoHoaTaiLieu_DATN/.agents/rules/08-governance.md) | **Mọi session**: Giới hạn quyền agent, RAG safety, cấm commit tự động. |

---

## 🚀 Lệnh Kiểm Tra Nhanh
- **FE**: `cd apps/web && pnpm dev` (Local Dev) | `pnpm test` (Unit Test)
- **BE**: `cd apps/api && uv run uvicorn app.main:app --reload` | `uv run pytest`
- **Full Workspace Check**: `pnpm check`
