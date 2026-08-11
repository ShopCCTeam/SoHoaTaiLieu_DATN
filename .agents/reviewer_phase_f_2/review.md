# Báo cáo Kiểm thử Gate Phase F — Frontend Integration & Route Reviewer

## Review Summary

**Verdict**: APPROVE

- **Phạm vi đánh giá**: Audit 12 web routes, TanStack Query live/mock mode API hooks, type-safety với `@ctsv/contracts` OpenAPI types, chạy `test` & `build`.
- **Đơn vị kiểm thử**: Reviewer 2 (`reviewer_phase_f_2`), Archetype: `teamwork_preview_reviewer`.
- **Kết quả build**: `pnpm --filter web build` PASS (12/12 routes prerendered / dynamic).
- **Kết quả test**: `pnpm --filter web test` PASS (5/5 test suites, 31/31 tests passed).

---

## 1. Audit Danh sách 12 Web Routes (`apps/web`)

| # | Route Spec | Đường dẫn thực tế | Trạng thái Route | TanStack Query Hook | Type Safety & Mapper |
|---|---|---|---|---|---|
| 1 | `/` | `apps/web/app/page.tsx` | ✅ OK (Redirect `/dashboard`) | N/A | TypeScript Strict |
| 2 | `/login` | `apps/web/app/(auth)/login/page.tsx` | ✅ OK (Auth form + quick demo roles) | `useAuthStore` | `UserRole` enum |
| 3 | `/dashboard` | `apps/web/app/(app)/dashboard/page.tsx` | ✅ OK (Analytics + recent docs) | `useDocuments()` | `apiDocumentToDomain` |
| 4 | `/documents` | `apps/web/app/(app)/documents/page.tsx` | ✅ OK (Document table + status filter) | `useDocuments()` | `apiDocumentToDomain` |
| 5 | `/documents/[id]` | `apps/web/app/(app)/documents/[id]/page.tsx` | ✅ OK (Detail, tabs, `notFound()`, RBAC guard) | Client state + fixtures | `Document`, `DocumentVersion` |
| 6 | `/documents/upload` | `apps/web/app/(app)/documents/upload/page.tsx` | ✅ OK (Dropzone, SHA-256, magic bytes `%PDF-`) | `useTriggerOCRMutation` | `Job` DTO |
| 7 | `/ocr-review` | `apps/web/app/(app)/documents/[id]/review/page.tsx` | ✅ OK (Mapped via `/documents/[id]/review`) | `useUpdateBlockMutation` | `apiOCRBlockToDomain` |
| 8 | `/ocr-review/[jobId]` | `apps/web/app/(app)/documents/[id]/review/page.tsx` | ✅ OK (Mapped via `useJobStatusQuery` / review pane) | `useJobStatusQuery`, `useUpdateBlockMutation` | `ApiJob`, `ApiOCRBlock` |
| 9 | `/search` | `apps/web/app/(app)/search/page.tsx` | ✅ OK (Vector RAG Search BGE-M3 + snippet) | `useSearchRAG(query)` | `apiCitationToDomain` |
| 10 | `/chat` | `apps/web/app/(app)/chat/page.tsx` | ✅ OK (Chatbot UI + citations chip) | `useChatRAGMutation()` | `ChatAnswerData`, `Citation` |
| 11 | `/admin/users` | `apps/web/app/(app)/admin/users/page.tsx` | ✅ OK (Quản lý User & Role + 403 guard) | `useAdminUsers()` | `apiUserToDomain` |
| 12 | `/admin/system` | `apps/web/app/(app)/admin/models/page.tsx` | ✅ OK (Mapped qua `/admin/models` RAG/OCR AI Models) | `useAdminModels()` | `ModelVersion` DTO |

---

## 2. Kiểm tra Kết nối API Live Mode & TanStack Query

1. **`apiClient` (`apps/web/lib/api/client.ts`)**:
   - **Dual mode support**: Nhận diện `NEXT_PUBLIC_API_MODE`. Khi set `"live"`, tự động gửi request đến `NEXT_PUBLIC_API_BASE_URL` (`http://localhost:8000/api/v1`). Khi set `"mock"`, routed qua `/api/*` Next.js route handlers.
   - **Authentication**: Tự động gán `Authorization: Bearer <token>` và đặt `credentials: "include"` hỗ trợ HttpOnly refresh cookies.
   - **Envelope unwrap**: Tự động unwrap `{ success: true, data: T }` trả về data trực tiếp cho hook.
   - **RFC 7807 Error Handling**: Xử lý Content-Type `application/problem+json` và ném `ApiError` chứa `ProblemDetail` chuẩn hóa.

2. **TanStack Query Hooks (`apps/web/lib/api/queries/index.ts`)**:
   - `useDocuments`: GET `/documents` với query parameters `status`, `type`, `query`.
   - `useUpdateMetadataMutation`: PATCH `/documents/:id/versions/:verId/metadata`.
   - `useTriggerOCRMutation`: POST `/documents/:id/versions/:verId/ocr` (hỗ trợ `Idempotency-Key`).
   - `useApproveVersionMutation`: POST `/documents/:id/versions/:verId/approve`.
   - `useJobStatusQuery`: GET `/ocr/jobs/:jobId`.
   - `useUpdateBlockMutation`: PATCH block endpoint.
   - `useSearchRAG`: GET `/search/query?q=...`.
   - `useChatRAGMutation`: POST `/chat/query`.
   - `useAdminUsers`: GET `/admin/users`.
   - `useAdminModels`: GET `/admin/models`.

---

## 3. An toàn Kiểu dữ liệu (Type Safety) với `@ctsv/contracts`

- Các types OpenAPI gốc từ `packages/contracts` (`ApiDocument`, `ApiDocumentVersion`, `ApiUser`, `ApiOCRBlock`, `ApiCitation`, `ApiJob`, `DocumentStatusEnum`, `DocumentScope`, `OCRReviewStatus`) được import trực tiếp vào `apps/web/lib/api/types.ts`.
- Lớp mapper trong `apps/web/lib/api/mappers.ts` thực hiện chuyển đổi 1:1 từ snake_case DTO sang camelCase domain model.
- Không có hiện tượng type bypass (`any` lạm dụng) hay mismatch kiểu dữ liệu.

---

## 4. Kiểm tra Integrity & Quy tắc Dự án (Adversarial Critic)

- **Integrity Check**:
  - Không có hardcoded test results hay kết quả giả tạo trong source code.
  - Không có facade stub bỏ qua logic xử lý thực tế.
  - Không có shortcut bypass gate verification.
- **Icon Rule Check**:
  - 100% icon sử dụng Lucide React SVG components (`stroke-current`).
  - Không dùng icon màu / bitmap / raster image.

---

## 5. Kết quả Lệnh Kiểm thử

1. `pnpm --filter web test`:
   - 5 test suites passed.
   - 31 unit tests passed (Permissions, Endpoints, ApiClient live/mock, File validation, StatusBadge).
2. `pnpm --filter web build`:
   - Next.js 14.2.35 build thành công.
   - 12 static/dynamic routes prerendered sạch sẽ (0 build errors, 2 minor non-blocking ESLint warnings).

---

## Conclusion

Gate Phase F (Frontend Integration) đủ điều kiện thông quan. Verdict: **APPROVE**.
