# Báo Cáo Phân Tích Chuyên Sâu Frontend Integration (Phase F)

**Dự án**: Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên  
**Người thực hiện**: Explorer 3 (Frontend Integration Specialist)  
**Thư mục làm việc**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_e_3`  
**Thời gian**: 2026-08-11T16:05:00+07:00  

---

## 1. Executive Summary

Phân tích toàn bộ ứng dụng Frontend Next.js 14 (`apps/web`), tầng kết nối API client (`apps/web/lib/api/`), quản lý trạng thái (`Zustand` & `TanStack Query`), cơ chế chuyển đổi `NEXT_PUBLIC_API_MODE=mock` vs `live`, kiểm tra sự tương thích giữa hợp đồng API (`packages/contracts`) với các endpoint FastAPI backend (`apps/api`), kiểm tra việc tuân thủ quy tắc người dùng (Icon SVG, tiếng Việt 100%), và xác minh các lệnh build / test của ứng dụng Web.

---

## 2. Cấu Trúc Tổng Quan Frontend & 12 Web Routes (`apps/web/app`)

Ứng dụng Frontend được xây dựng theo kiến trúc Next.js 14 App Router, sử dụng TypeScript Strict, Tailwind CSS, Framer Motion, Zustand v5, TanStack Query v5, Zod và React Hook Form.

### Danh Sách Audit 12 Web Routes:

| STT | App Route Path | Mục Đích & Chức Năng | API Dependencies & Query Hooks | Trạng Thái Mới/Cũ |
|---|---|---|---|---|
| 1 | `app/page.tsx` | Root redirect | N/A (Tự động redirect tới `/dashboard`) | Hoạt động tốt |
| 2 | `app/(auth)/login/page.tsx` | Trang Đăng nhập | Quick role switcher (`admin`, `staff`, `student`), `useAuthStore.login()` | Hoạt động tốt |
| 3 | `app/(app)/dashboard/page.tsx` | Dashboard Tổng quan | Thống kê số hóa, văn bản mới. Hiện đang dùng `MOCK_DOCUMENTS` trực tiếp | Cần refactor dùng `useDocuments()` |
| 4 | `app/(app)/documents/page.tsx` | Kho Văn bản & Tài liệu | `useDocuments()` hook, component `DocumentTable` | Hoạt động tốt |
| 5 | `app/(app)/documents/upload/page.tsx` | Tải lên & Số hóa PDF | Component `UploadDropzone`, SHA-256 checksum, magic bytes validation | Hoạt động tốt |
| 6 | `app/(app)/documents/[id]/page.tsx` | Chi tiết Văn bản | Xem metadata, danh sách phiên bản, nhật ký audit history log. Sử dụng `notFound()` | Hoạt động tốt |
| 7 | `app/(app)/documents/[id]/review/page.tsx` | Hiệu chỉnh BBox OCR | Split pane `OCRReviewPane`, chỉnh sửa bounding box PaddleOCR / Tesseract | Hoạt động tốt |
| 8 | `app/(app)/search/page.tsx` | Tra cứu RAG Vector | `useSearchRAG(query)` hook, kết quả `SearchResultCard` với score BGE-M3 | Hoạt động tốt |
| 9 | `app/(app)/chat/page.tsx` | Trợ lý AI Chatbot RAG | `useChatRAGMutation()` hook, `ChatThread` với trích dẫn `citations` | Hoạt động tốt |
| 10 | `app/(app)/admin/users/page.tsx` | Quản lý User & Role | `useAdminUsers()` hook, kiểm tra RBAC role `admin` (403 nếu sai role) | Hoạt động tốt |
| 11 | `app/(app)/admin/models/page.tsx` | Quản lý Models & RAG | `useAdminModels()` hook, kiểm tra RBAC role `admin` (403 nếu sai role) | Hoạt động tốt |
| 12 | `app/not-found.tsx` / `app/error.tsx` | Error & 404 Handlers | Xử lý lỗi hệ thống & trang 404 chuẩn Next.js | Hoạt động tốt |

---

## 3. Kiến Trúc Tầng Kết Nối API & Cơ Chế Mock vs Live Mode

### 3.1. Cấu hình `NEXT_PUBLIC_API_MODE`
Tầng API Client (`apps/web/lib/api/client.ts`) kiểm tra môi trường:
- `NEXT_PUBLIC_API_BASE_URL` (Mặc định: `http://localhost:8000/api/v1`)
- `NEXT_PUBLIC_API_MODE` (`mock` hoặc `live`)

```typescript
// apps/web/lib/api/client.ts
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
const IS_MOCK = process.env.NEXT_PUBLIC_API_MODE !== "live";

const url = IS_MOCK && endpoint.startsWith("/")
  ? `/api${endpoint}`
  : `${BASE_URL}${endpoint}`;
```

- Khi `NEXT_PUBLIC_API_MODE=mock`: Mọi request bắt đầu bằng `/` (ví dụ `/documents`) sẽ được điều hướng tới Next.js API Route Handlers tại `apps/web/app/api/*` (`/api/documents`).
- Khi `NEXT_PUBLIC_API_MODE=live`: Request gửi thẳng tới Backend FastAPI tại `${BASE_URL}/*` (`http://localhost:8000/api/v1/documents`).
- Thanh `Topbar` hiển thị Badge trạng thái trực quan (`MOCK` màu vàng hổ phách, `LIVE` màu xanh ngọc).

### 3.2. Quản lý Trạng Thái & Auth Session
- **Auth Store**: Sử dụng `Zustand` v5 với `persist` middleware trong `apps/web/lib/auth/session.ts` (`ctsv_auth_session`).
- **Data Fetching**: Sử dụng `TanStack Query` v5 (`useQuery`, `useMutation`) trong `apps/web/lib/api/queries/index.ts`. Mọi request đều gọi `apiClient<T>`, unwrap envelope `{ success: true, data: T }`, rồi qua mapper `snake_case → camelCase` trước khi giao cho React Components.

---

## 4. Audit Tương Thích Chuẩn Hợp Đồng (OpenAPI / Contracts / FastAPI / Web)

Bảng đối chiếu toàn bộ API endpoints giữa FE `API_ENDPOINTS` (`apps/web/lib/api/endpoints.ts`), Next.js Mock (`apps/web/app/api/`), Chuẩn Contract (`packages/contracts`), và Backend FastAPI Router (`apps/api/app/modules/`):

### 4.1. Bảng Đối Chiếu Endpoint URL & HTTP Method

| Phân Loại API | Path trong FE `endpoints.ts` | Path trong Backend FastAPI Router | Trạng Thái Khớp | Ghi Chú & Mismatch Phát Hiện |
|---|---|---|---|---|
| **Auth Login** | `POST /auth/login` | `POST /api/v1/auth/login` | ✅ Khớp | FastAPI set `HttpOnly` refresh cookie `rt` + trả `access_token` |
| **Auth Me** | `GET /auth/me` | `GET /api/v1/auth/me` | ✅ Khớp | Xác thực Bearer Token |
| **Auth Refresh** | N/A (thiếu trong `endpoints.ts`) | `POST /api/v1/auth/refresh` | ⚠️ Cần bổ sung | Cần bổ sung `AUTH.REFRESH: "/auth/refresh"` vào FE |
| **Auth Logout** | N/A (thiếu trong `endpoints.ts`) | `POST /api/v1/auth/logout` | ⚠️ Cần bổ sung | Cần bổ sung `AUTH.LOGOUT: "/auth/logout"` vào FE |
| **Documents List** | `GET /documents` | `GET /api/v1/documents` | ✅ Khớp | Hỗ trợ lọc status, type, q, page, limit + RBAC scope |
| **Documents Detail** | `GET /documents/{id}` | `GET /api/v1/documents/{id}` | ✅ Khớp | Trả thông tin chi tiết tài liệu + danh sách phiên bản |
| **Documents Upload** | `POST /documents` | `POST /api/v1/documents` | ✅ Khớp | Multipart/form-data + header `Idempotency-Key` (202 Accepted) |
| **Create Version** | `POST /documents/{id}/versions` | `POST /api/v1/documents/{id}/versions` | ✅ Khớp | Multipart/form-data + header `Idempotency-Key` (202 Accepted) |
| **Update Metadata** | `PATCH /document-versions/{vid}/metadata` | `PATCH /api/v1/documents/{id}/versions/{vid}/metadata` | ❌ Bất đồng Path! | FE gọi `/document-versions/...`, BE yêu cầu `/documents/{id}/versions/{vid}/metadata` |
| **Trigger OCR** | `POST /document-versions/{vid}/ocr` | `POST /api/v1/documents/{id}/versions/{vid}/ocr` | ❌ Bất đồng Path! | FE gọi `/document-versions/...`, BE yêu cầu `/documents/{id}/versions/{vid}/ocr` |
| **Approve Version** | `POST /document-versions/{vid}/approve` | `POST /api/v1/documents/{id}/versions/{vid}/approve` | ❌ Bất đồng Path! | FE gọi `/document-versions/...`, BE yêu cầu `/documents/{id}/versions/{vid}/approve` |
| **OCR Job Status** | `GET /ocr-jobs/{id}` | `GET /api/v1/jobs/{id}` | ❌ Bất đồng Path! | FE dùng `/ocr-jobs/...`, BE dùng `/jobs/{id}` |
| **OCR Block Patch** | `PATCH /ocr-blocks/{id}` | `PATCH /api/v1/documents/{id}/versions/{vid}/ocr/blocks/{bid}` | ❌ Bất đồng Path! | FE dùng `/ocr-blocks/...`, BE dùng nested path |
| **Search Query** | `GET /search` hoặc `POST /search` | `GET /api/v1/search` / `POST /api/v1/search` | ✅ Khớp | RRF Hybrid Search |

### 4.2. Mismatch Chi Tiết Cần Sửa Cho Phase F Integration

1. **OCR Block Response Field Naming Mismatch**:
   - In `@ctsv/contracts` & FE `mappers.ts`: `text: string`, `ocr_job_id: string`, `page_number: number`.
   - In FastAPI `OCRBlockResponse` (`apps/api/app/modules/documents/schemas.py` line 143-150): `text_content: str`, `job_id: str`, `version_id: str`.
   - **Khắc phục**: Thêm alias hoặc điều chỉnh `OCRBlockResponse` trong Backend / Mapper để đảm bảo trường `text` và `ocr_job_id` khớp với hợp đồng OpenAPI.

2. **Dashboard Data Source**:
   - `app/(app)/dashboard/page.tsx` hiện nhập trực tiếp `MOCK_DOCUMENTS` từ `@/lib/mocks/fixtures`.
   - **Khắc phục**: Chuyển sang sử dụng `useDocuments()` hook để lấy dữ liệu động từ API khi ở cả hai chế độ `mock` và `live`.

---

## 5. Kiểm Tra Việc Tuân Thủ Quy Tắc Người Dùng (User Rules Compliance)

### 5.1. Quy Tắc Icon (NO colored icons, MUST use SVG icons)
- **Kiểm tra**: Tất cả các component trong `apps/web/components` và thanh điều hướng `Sidebar`, `Topbar` đều dùng Lucide React SVG components (`<FileText className="stroke-current" />`, v.v.).
- **Lỗi vi phạm phát hiện**:
  - Tệp `apps/web/app/(app)/dashboard/page.tsx` dòng 74 chứa emoji icon màu `👋` (`Xin chào, {user?.fullName || "Người dùng"}! 👋`).
  - **Khắc phục**: Thay thế emoji `👋` bằng SVG Icon component từ Lucide React (ví dụ `Sparkles` hoặc `Handshake` hoặc `UserIcon`).

### 5.2. Quy Tắc Ngôn Ngữ UI (100% tiếng Việt)
- **Kiểm tra**: 100% giao diện người dùng (nút bấm, tiêu đề, nhãn form, bảng dữ liệu, thông báo lỗi RFC 7807, placeholder) đều hiển thị bằng tiếng Việt chuẩn.
- Các thuật ngữ chuyên ngành cố định (PDF, SHA-256, RAG, OCR, Admin, Staff, Student, Scope: PUBLIC) được giữ nguyên theo đúng quy chuẩn domain.

---

## 6. Kiểm Tra Build & Test Executable

1. **Vitest Unit Tests**:
   - Lệnh: `pnpm --filter web test`
   - Kết quả: **PASSED 100%** (4 test files, 26 tests passed).
   - Danh sách tệp test:
     - `tests/auth/permissions.test.ts` (7 tests)
     - `tests/lib/api-client.test.ts` (5 tests)
     - `tests/lib/file.test.ts` (11 tests)
     - `tests/components/status-badge.test.tsx` (3 tests)

2. **Production Build**:
   - Lệnh: `pnpm --filter web build`
   - Kết quả: **SUCCESSFUL BUILD** (Next.js 14 App Router compiled & generated production pages).

---

## 7. Chiến Lược Tích Hợp Frontend-Backend Phase F (Action Plan)

1. **Đồng bộ hóa Endpoints trong `apps/web/lib/api/endpoints.ts`**:
   - Sửa các endpoint path bị bất đồng để khớp chính xác với router FastAPI backend.
   - Thêm `AUTH.REFRESH` và `AUTH.LOGOUT`.
2. **Cập nhật Mapper `apps/web/lib/api/mappers.ts`**:
   - Hỗ trợ linh hoạt cả hai định dạng trường `text` / `text_content` và `ocr_job_id` / `job_id` trong DTO trả về từ OCR API.
3. **Refactor Dashboard Page**:
   - Chuyển `app/(app)/dashboard/page.tsx` từ dùng static `MOCK_DOCUMENTS` sang `useDocuments()`.
4. **Sửa vi phạm Icon Rule**:
   - Thay emoji màu `👋` tại `dashboard/page.tsx` dòng 74 bằng Lucide SVG icon.
