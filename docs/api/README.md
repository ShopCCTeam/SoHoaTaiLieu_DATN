# OpenAPI Contract — Single Source of Truth

> File này là **nguồn chuẩn duy nhất** cho hợp đồng API giữa Frontend (Next.js) và Backend (FastAPI).
> Mọi endpoint phải khớp với spec này. Khi cần thay đổi, cập nhật file này trước rồi mới sửa code.

## Quy ước chung

| Mục | Giá trị |
|---|---|
| **Base URL (production)** | `https://api.<domain>/api/v1` |
| **Base URL (dev local)** | `http://localhost:8000/api/v1` |
| **Auth** | `Authorization: Bearer <jwt_access_token>` |
| **Content-Type** | `application/json` hoặc `multipart/form-data` (upload) |
| **Versioning** | URL prefix `/api/v1` |
| **Date format** | ISO 8601 UTC (`2026-08-09T14:00:00Z`) |
| **ID format** | UUID v7 cho entity, `job_xxx` cho job, `chunk_xxx` cho chunk |

## 1. Response chuẩn

### 1.1 Success — envelope `{ success, data }`

```json
{
  "success": true,
  "data": { /* payload */ },
  "total": 123,        // chỉ có ở list endpoint
  "page": 1,           // chỉ có ở list endpoint
  "limit": 20          // chỉ có ở list endpoint
}
```

### 1.2 Error — RFC 7807 Problem Details

```json
{
  "type": "https://api.example.edu.vn/problems/validation-error",
  "title": "Dữ liệu không hợp lệ",
  "status": 422,
  "detail": "Tệp tải lên không đúng định dạng PDF",
  "code": "INVALID_FILE_TYPE",
  "request_id": "req_01HXYZ...",
  "errors": [           // optional, cho validation chi tiết
    { "field": "file", "message": "MIME type không hợp lệ" }
  ]
}
```

### 1.3 HTTP Status Codes

| Status | Khi nào |
|---|---|
| 200 | Thành công |
| 201 | Tạo resource |
| 204 | Xoá resource (không body) |
| 400 | Body không parse được |
| 401 | Thiếu/invalid JWT |
| 403 | Auth OK nhưng không đủ permission |
| 404 | Resource không tồn tại |
| 409 | Conflict (VD: duplicate version) |
| 422 | Validate fail (Pydantic) |
| 429 | Rate limit |
| 500 | Lỗi server không expect |

## 2. Endpoints

### 2.1 Auth

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| POST | `/auth/login` | public | Đăng nhập, trả `access_token` + `refresh_token` |
| POST | `/auth/refresh` | public (cần refresh token) | Cấp access token mới |
| POST | `/auth/logout` | authenticated | Invalidate refresh token |
| GET | `/auth/me` | authenticated | Trả thông tin user hiện tại |

### 2.2 Documents

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/documents` | any (filter theo scope) | Danh sách documents, có filter & pagination |
| POST | `/documents` | staff/admin | Upload PDF, **trả về job** (async) |
| GET | `/documents/{id}` | any (check scope) | Chi tiết document + latest version |
| PATCH | `/documents/{id}` | staff/admin | Cập nhật metadata |
| DELETE | `/documents/{id}` | admin | Soft delete |
| GET | `/documents/{id}/versions` | any | Danh sách versions |
| POST | `/documents/{id}/versions` | staff/admin | Upload version mới (supersede) |
| GET | `/documents/{id}/versions/{vid}` | any | Chi tiết version |
| PATCH | `/documents/{id}/versions/{vid}/metadata` | staff/admin | Sửa metadata version |
| POST | `/documents/{id}/versions/{vid}/ocr` | staff/admin | Trigger OCR job |
| POST | `/documents/{id}/versions/{vid}/approve` | staff/admin | Approve version |

### 2.3 Jobs (Polling)

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/jobs/{id}` | authenticated (own + admin) | Trạng thái job (`QUEUED/PROCESSING/SUCCEEDED/FAILED/CANCELLED`) |
| POST | `/jobs/{id}/cancel` | authenticated (own + admin) | Huỷ job |

**Polling rule (FE)**: poll `/jobs/{id}` mỗi **2 giây**, tối đa 60 lần. Sau đó dừng và hiển thị "đang xử lý, vui lòng tải lại sau".

### 2.4 OCR

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/document-versions/{vid}/ocr-blocks` | any (check scope) | Danh sách block OCR theo trang |
| PATCH | `/ocr-blocks/{id}` | staff/admin | Sửa text của 1 block (track edited_by) |

### 2.5 Search & RAG

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| POST | `/search` | authenticated | Hybrid search (full-text + pgvector) |
| POST | `/chat/query` | authenticated | RAG: trả answer + citations |

**Citation schema** (xem `docs/domain/citation-spec.md`):

```json
{
  "document_id": "doc_...",
  "document_version_id": "ver_...",
  "title": "Quy chế công tác sinh viên",
  "page_number": 12,
  "chunk_id": "chunk_...",
  "quote": "Nội dung được trích dẫn...",
  "score": 0.82,
  "bbox": [120, 240, 950, 410]
}
```

### 2.6 Admin

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/admin/users` | admin | Danh sách user |
| POST | `/admin/users` | admin | Tạo user |
| PATCH | `/admin/users/{id}` | admin | Cập nhật user (role, status) |
| GET | `/admin/model-versions` | admin | Danh sách model OCR/embedding |
| POST | `/admin/model-versions/{id}/activate` | admin | Kích hoạt model |
| GET | `/admin/training-runs` | admin | Lịch sử training |

### 2.7 Audit

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/audit-logs` | admin | Lọc theo user_id, document_id, action, time range |

## 3. Versioning & Breaking change policy

- Tăng version URL (`/api/v2`) khi breaking field type hoặc xoá field.
- Thêm field optional → vẫn giữ v1.
- Đổi enum value → phải tăng version.

## 4. OpenAPI machine-readable

Spec đầy đủ ở `docs/api/openapi.yaml` (sẽ generate từ FastAPI sau khi code BE ready).
Trong giai đoạn foundation, file `openapi.yaml` là **draft** — chưa sync với code.

## 5. Lịch sử thay đổi

| Ngày | Thay đổi | Tác giả |
|---|---|---|
| 2026-08-09 | Khởi tạo contract ban đầu (NO-GO code BE) | Agent |
