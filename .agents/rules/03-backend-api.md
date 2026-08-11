# Backend Standards — FastAPI / Python

Scope: `apps/api/**/*.py`, `apps/api/**/*.toml`, `packages/**/*.{ts,py}`

> Áp dụng cho Backend code. Đã chốt stack ở `docs/adr/0001-backend-stack.md`.

## 0. Contract-first (bắt buộc)
- **`docs/api/openapi.yaml` là single source of truth** cho API contract.
- FastAPI code **phải khớp** OpenAPI đã chốt. Không tự ý đổi endpoint, status, schema.
- **CI so sánh**: sau khi FastAPI generate `openapi.json` runtime, CI phải diff với `docs/api/openapi.yaml`. Nếu lệch → fail build.
- **Update contract trước** khi sửa code: mở PR chỉnh `openapi.yaml` → review → merge → mới sửa code.

## 1. Nguyên tắc chung (bắt buộc)
- **Layered Architecture**: `presentation` → `application` (use case) → `domain` (entity) → `infrastructure` (DB, MinIO, Redis).
- **API Design**: RESTful, JSON, versioned URL (`/api/v1/...`).
- **Auth**: JWT bearer token (HS256, 15 phút) + refresh token rotation (7 ngày). Lưu `Authorization: Bearer <token>`.
- **Validation**: validate ở boundary handler bằng **Pydantic v2**. Không dùng `any` / `dict` rồi parse thủ công.
- **Logging**: structured log (JSON), có `requestId`, `userId`, **KHÔNG** log password, token, PDF content, OCR text, PII.
- **Testing**: pytest + pytest-asyncio + HTTPX. Unit test cho service, integration test cho endpoint.

## 2. API Response Contract

### 2.1 Success Envelope
```json
{
  "success": true,
  "data": { /* payload */ },
  "total": 123,    // optional, chỉ ở list endpoint
  "page": 1,       // optional
  "limit": 20      // optional
}
```

### 2.2 Error — RFC 7807 Problem Details
```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/problem+json

{
  "type": "https://api.example.edu.vn/problems/validation-error",
  "title": "Dữ liệu không hợp lệ",
  "status": 422,
  "detail": "Tệp tải lên không đúng định dạng PDF",
  "code": "INVALID_FILE_TYPE",
  "request_id": "req_01HXYZ...",
  "errors": [
    { "field": "file", "message": "MIME magic bytes không khớp %PDF-" }
  ]
}
```

### 2.3 Auth Pattern — Token Storage
- **Access token**: JWT HS256, lifetime 15 phút.
  - FE giữ trong memory (Zustand store). Truyền qua `Authorization: Bearer <access_token>`.
- **Refresh token**: opaque random 32 bytes (KHÔNG phải JWT), lifetime 7 ngày.
  - Server set qua `HttpOnly` cookie `rt`.
  - KHÔNG lưu refresh token trong `localStorage`/`sessionStorage`.
  - KHÔNG trả refresh token trong response body.
- **Cookie attributes**: `HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth; Max-Age=604800`.

### 2.4 Upload Pattern — Bất đồng bộ
Upload PDF/file lớn KHÔNG trả Document ngay. Trả **202 Accepted** với `job_id`:
```json
{
  "success": true,
  "data": {
    "document_id": "doc_01HXYZ...",
    "job_id": "job_01HABC...",
    "status": "QUEUED"
  }
}
```
FE poll `GET /api/v1/jobs/{job_id}` mỗi 2 giây, tối đa 60 lần.

## 3. Idempotency-Key Header
Bắt buộc có `Idempotency-Key` header cho các endpoints:
- `POST /documents` (upload)
- `POST /documents/{id}/versions`
- `POST /documents/{id}/versions/{vid}/ocr`
- `POST /admin/model-versions/{id}/activate`
- `POST /jobs/{id}/cancel`
- `POST /admin/model-versions/{id}/reindex`

KHÔNG áp dụng Idempotency-Key cho: `/auth/login`, `/auth/refresh`, `/auth/logout`, `/chat/query`, `/search`, các `GET` request.

## 4. Security Checklist
- Mọi endpoint có auth trừ `/auth/login`, `/auth/refresh`, `/health`.
- Mọi endpoint có permission check (`has_permission(user, Permission.X)`).
- Permission check **TRƯỚC** retrieval.
- Input validation đầy đủ (check MIME magic bytes `%PDF-`).
- Rate limit: `/auth/login` (5/15min), `/chat/query` (30/min), upload (10/hour).
- Password: bcrypt cost ≥ 12 hoặc Argon2id.

## 5. Background Jobs (Celery)
- Broker/Backend: Redis.
- Task idempotency key, retry ≤ 3 lần (backoff 60s/300s/1800s).
- Progress update qua `self.update_state()`.

## 6. Quality Gate
```bash
cd apps/api
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest --cov=app --cov-fail-under=80
```
