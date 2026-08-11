# Security Standards

## Authentication
- Password hashing: bcrypt cost ≥ 12, hoặc Argon2id.
- Session: JWT ngắn hạn (15 phút) + refresh token rotation (7 ngày).
- Logout: invalidate refresh token ở server DB/Redis, không chỉ xoá phía client.
- Demo account: phải đánh dấu rõ `IS_DEMO=true`, cấm dùng trong production.

## Authorization (RBAC)
- 3 Roles chính: `admin`, `staff`, `student`.
- **Luôn check permission ở backend**. FE chỉ ẩn UI phục vụ UX, không phải ranh giới bảo mật.
- Scope check: `student` chỉ xem được `scope IN ('PUBLIC', 'STUDENT_AFFAIRS')`. Xem tài liệu `INTERNAL` bắt buộc role `staff` hoặc `admin`.

## Input Validation & Upload Protection
- Validate mọi endpoint (body, query, param, file).
- File upload: check **MIME magic bytes** (`%PDF-`, `\xFF\xD8\xFF` cho JPEG), **KHÔNG tin tưởng extension**.
- Giới hạn dung lượng: PDF ≤ 50MB, ảnh ≤ 10MB.
- Chống path traversal trong filename (`../`, `\\`).

## Secrets & Environment
- File `.env` chứa DB password, JWT secret, API keys.
- `.env` nằm trong `.gitignore`. **TUYỆT ĐỐI KHÔNG COMMIT `.env`**.
- File `.env.example` chứa keys placeholder không có dữ liệu thật.

## Logging & Privacy
- Log structured JSON: `{timestamp, level, requestId, userId, action, result, duration}`.
- **KHÔNG LOG**: password, JWT token, checksum file, PII (email SV, tên thật SV, MSSV).
- Log retention 30 ngày.

## Rate Limiting
- `/auth/login`: 5 requests / 15 phút / IP.
- `/chat/query`: 30 requests / phút / user.
- `/documents` POST (upload): 10 requests / giờ / user.
- Phản hồi HTTP 429 Too Many Requests kèm `Retry-After` header.

## Audit Trail
- Log mọi mutation quan trọng vào bảng `audit_logs` (append-only): thay đổi role, approve tài liệu, kích hoạt model version, xoá tài liệu. Giữ audit log ≥ 1 năm.
