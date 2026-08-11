# Handoff Report — Phase F Frontend Integration Deep-Dive

**Agent**: Explorer 3 (Frontend Integration Specialist)  
**Working Directory**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_e_3`  
**Recipient**: Parent Agent (`8b21cd22-8f5a-4b2f-8b30-148a1a6b04c5`)  
**Date**: 2026-08-11T16:05:00+07:00  

---

## 1. Observation

- **Cấu trúc Web Routes**: `apps/web/app/` gồm 12 web routes (`/`, `/login`, `/dashboard`, `/documents`, `/documents/upload`, `/documents/[id]`, `/documents/[id]/review`, `/search`, `/chat`, `/admin/users`, `/admin/models`, `not-found/error`).
- **Tầng API Client**: `apps/web/lib/api/client.ts` hỗ trợ 2 chế độ via `NEXT_PUBLIC_API_MODE`:
  - `mock`: gọi Next.js local API route handlers tại `/api/*` (`apps/web/app/api/*`).
  - `live`: gọi thẳng FastAPI backend tại `http://localhost:8000/api/v1/*`.
- **Thực thi Kiểm tra (Tool Commands & Execution)**:
  - `pnpm --filter web test`: **PASSED 4/4 test files (26 tests total)**.
  - `pnpm --filter web build`: **SUCCESSFUL BUILD** (Next.js 14 compiled without type/lint errors).
- **Phát hiện Bất đồng Endpoint Path (Mismatches)**:
  1. `DOCUMENTS.UPDATE_METADATA`: FE dùng `/document-versions/${versionId}/metadata` (`apps/web/lib/api/endpoints.ts`:11), nhưng FastAPI dùng `PATCH /documents/{id}/versions/{vid}/metadata` (`apps/api/app/modules/documents/router.py`:278).
  2. `DOCUMENTS.TRIGGER_OCR`: FE dùng `/document-versions/${versionId}/ocr` (line 12), nhưng FastAPI dùng `POST /documents/{id}/versions/{vid}/ocr` (line 305).
  3. `DOCUMENTS.APPROVE`: FE dùng `/document-versions/${versionId}/approve` (line 13), nhưng FastAPI dùng `POST /documents/{id}/versions/{vid}/approve` (line 334).
  4. `OCR.JOB_STATUS`: FE dùng `/ocr-jobs/${id}` (line 17), nhưng FastAPI dùng `GET /jobs/${id}` (`apps/api/app/modules/jobs/router.py`:22).
  5. `OCR.UPDATE_BLOCK`: FE dùng `/ocr-blocks/${id}` (line 18), nhưng FastAPI dùng `PATCH /documents/{id}/versions/{vid}/ocr/blocks/{bid}` (line 391).
- **Phát hiện Bất đồng Tên Trường Schema (Field Mismatches)**:
  - `OCRBlockResponse` trong FastAPI schema (`apps/api/app/modules/documents/schemas.py`:143-150) định nghĩa `text_content`, `job_id`, `version_id`, trong khi OpenAPI contract & FE `mappers.ts`:96 kỳ vọng `text`, `ocr_job_id`.
- **Phát hiện Vi Phục Quy Tắc User Rules**:
  - Icon Rule Violation: Tệp `apps/web/app/(app)/dashboard/page.tsx`:74 chứa emoji icon màu `👋` (`Xin chào, {user?.fullName || "Người dùng"}! 👋`).

---

## 2. Logic Chain

1. Từ **Observation 1 & 2**: FE đã có sẵn cấu trúc hoàn chỉnh cho 12 routes và hạ tầng API Client hai chế độ `mock` và `live` sạch sẽ, tích hợp RFC 7807 problem detail và Zustand store.
2. Từ **Observation 3**: Việc thực thi `pnpm --filter web test` và `pnpm --filter web build` đều thành công cho thấy mã FE hiện tại sạch lints và typecheck.
3. Từ **Observation 4 & 5**: Khi chuyển `NEXT_PUBLIC_API_MODE=live`, FE sẽ gặp lỗi 404/422 ở các tính năng chỉnh sửa Metadata phiên bản, kích hoạt OCR, phê duyệt phiên bản, và xem trạng thái Job do sự bất đồng giữa đường dẫn trong `apps/web/lib/api/endpoints.ts` và router của FastAPI `apps/api/app/modules/`.
4. Từ **Observation 6**: Emoji icon màu `👋` tại `dashboard/page.tsx`:74 vi phạm quy tắc người dùng "không dùng icon màu phải dùng icon SVG".

---

## 3. Caveats

- Chưa kiểm tra việc truyền nhận file PDF thực tế với dịch vụ MinIO trên môi trường Docker live (do đang ở chế độ read-only investigation).
- Mức độ tương thích giữa backend FastAPI và FE ở các endpoint Admin Models (`/admin/models`) và Chat RAG (`/chat/query`) sẽ cần bổ sung router backend tương ứng trong Phase 2/3.

---

## 4. Conclusion

FE (`apps/web`) sẵn sàng cho tích hợp Phase F với backend FastAPI. Cần thực hiện 4 điều chỉnh chiến lược nhỏ trước khi chuyển `NEXT_PUBLIC_API_MODE=live`:
1. Cập nhật `apps/web/lib/api/endpoints.ts` để khớp đường dẫn nested của FastAPI.
2. Bổ sung mapper fallback cho trường `text` / `text_content` trong `apps/web/lib/api/mappers.ts`.
3. Thay thế static `MOCK_DOCUMENTS` ở `app/(app)/dashboard/page.tsx` bằng `useDocuments()`.
4. Thay thế emoji `👋` tại `dashboard/page.tsx`:74 bằng SVG icon component.

---

## 5. Verification Method

Thực hiện các lệnh sau để kiểm tra độc lập:
1. Vitest tests: `cd apps/web && pnpm test`
2. Build check: `cd apps/web && pnpm build`
3. Type check: `cd apps/web && pnpm typecheck`
4. Lồng ghép kiểm tra icon SVG: `grep -rn "👋" apps/web/`
