# Handoff Report — Explorer 1 (Phase B Document Management)

> **Handoff Type**: Hard Handoff (Task Exploration Complete)  
> **Agent**: Explorer 1  
> **Target Recipient**: Orchestrator / Implementer Agent  
> **Working Directory**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_1`  
> **Date**: 2026-08-11  

---

## 1. Observation

- **OpenAPI & API Contract**:
  - `docs/api/openapi.yaml` (dòng 500–580): Định nghĩa endpoint `/documents` (GET & POST), các schemas (`Document`, `DocumentVersion`, `UploadResponse`, `JobStatus`), security (`bearerAuth`), response envelopes, header `Idempotency-Key` và RFC 7807 error responses.
  - `docs/api/README.md` (dòng 78–98): Liệt kê 11 endpoints cho Document Management (`/documents`, `/documents/{id}`, `/documents/{id}/versions`, `/documents/{id}/versions/{vid}/ocr`, `/documents/{id}/versions/{vid}/approve`, `/jobs/{id}`).
- **RBAC Scope Rules**:
  - `docs/domain/rbac-matrix.md` (dòng 14–39): Quy định scope: `PUBLIC` (tất cả), `STUDENT_AFFAIRS` (student, staff, admin), `INTERNAL` (staff, admin). Sinh viên truy cập `INTERNAL` bị chặn với 403 Forbidden. Quyền Delete chỉ dành riêng cho `admin`.
- **Document Lifecycle & Invariants**:
  - `docs/domain/document-lifecycle.md` (dòng 12–46, 70–102): State machine cho Document (`DRAFT`, `UNDER_REVIEW`, `APPROVED`, `ARCHIVED`), Version approval rules (`ocr_status == SUCCEEDED`, `requires_review` check) và Job status (`QUEUED`, `PROCESSING`, `SUCCEEDED`, `FAILED`, `CANCELLED`).
- **FastAPI Core Foundation & Auth**:
  - `apps/api/app/core/enums.py` (dòng 11–24): `UserRole` (`admin`, `staff`, `student`) và `DocumentScopeCode` (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`).
  - `apps/api/app/core/errors.py` (dòng 100–190): Các hàm helper RFC 7807 (`unauthorized`, `forbidden`, `not_found`, `validation_error`, `conflict`, `idempotency_mismatch`).
  - `apps/api/app/modules/auth/dependencies.py` (dòng 23–72): `get_current_user` Bearer JWT dependency giải mã token và nạp `User` từ DB.
  - `apps/api/app/core/config.py` (dòng 52–58): Cấu hình MinIO (`minio_endpoint`, `minio_access_key`, `minio_secret_key`, `minio_bucket`).
- **Test Infrastructure**:
  - `apps/api/tests/conftest.py` (dòng 56–193): Các async pytest fixtures (`db_engine`, `pg_engine`, `db_session_factory`, `seeded_user`, `api_client`). Hiện tại 84 unit/integration tests đang PASS 100%.

---

## 2. Logic Chain

1. **Từ Observation 1 (OpenAPI & README)**: Cần xây dựng 11 REST API handlers trong `apps/api/app/modules/documents/router.py` và `apps/api/app/modules/jobs/router.py`, trả về response envelope `{ success: true, data: ... }` và lỗi RFC 7807 khi thất bại.
2. **Từ Observation 2 (RBAC Scope Matrix)**: Trong `GET /documents` và `GET /documents/{id}`, backend phải áp dụng scope filter dựa trên `current_user.role`. Nếu `user.role == "student"`, query chỉ chọn tài liệu thuộc scope `PUBLIC` hoặc `STUDENT_AFFAIRS`. Thao tác `DELETE` kiểm tra `user.role == "admin"`.
3. **Từ Observation 3 (Lifecycle Invariants)**: Khi thực hiện `POST /documents/{id}/versions/{vid}/approve`, service phải kiểm tra phiên bản có `ocr_status == "SUCCEEDED"` và tất cả các block nghi vấn đã được duyệt.
4. **Từ Observation 4 (Core & Config)**: Việc upload file PDF cần thực hiện qua `StorageService` (MinIO/S3 hoặc Mock local storage trong test) và kiểm tra file size ≤ 50MB, MIME `application/pdf`, cùng magic bytes `%PDF-`.
5. **Từ Observation 5 (Test Suite)**: Mở rộng test suite bằng cách tạo các file `test_documents_router.py`, `test_documents_rbac.py`, `test_documents_upload.py`, `test_documents_versions.py`, `test_jobs_router.py` sử dụng `api_client` và `db_session_factory`.

---

## 3. Caveats

- **Read-Only Exploration**: Explorer 1 KHÔNG thực hiện sửa đổi bất kỳ file source code nào trong `apps/` hay `packages/`.
- **Môi Trường MinIO / Docker**: Khi chạy test local, hệ thống dùng SQLite in-memory và Mock storage service. Khi deploy stack, `Settings.minio_endpoint` sẽ kết nối với MinIO container qua `boto3`.
- **Cập Nhật OpenAPI Spec**: File `openapi.yaml` hiện tại có định nghĩa `/documents` GET/POST; Implementer cần bổ sung chi tiết 9 endpoints còn lại vào `openapi.yaml` để đảm bảo tính khớp 1:1 với hợp đồng.

---

## 4. Conclusion

Nhiệm vụ phân tích và khảo sát yêu cầu Phase B (Document Management & Storage APIs) đã hoàn thành xuất sắc. Đề xuất kiến trúc chi tiết, ORM models (`Document`, `DocumentVersion`, `Job`), RBAC scope rules, security/storage protocol, và chiến lược pytest suite đã được ghi lại đầy đủ tại `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_1\analysis.md`. Sẵn sàng bàn giao cho Implementer tiến hành lập trình.

---

## 5. Verification Method

1. **Đọc Báo Cáo Phân Tích**:  
   Xem nội dung `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_1\analysis.md` để kiểm tra thiết kế ORM models, ma trận RBAC và danh sách endpoints.
2. **Chạy Pytest Baseline**:  
   Chạy lệnh terminal:
   ```bash
   cd apps/api
   uv run pytest
   ```
   Xác nhận 84 tests hiện tại pass 100%.
3. **Điều Kiện Vô Hiệu Hoá (Invalidation Conditions)**:  
   Nếu có sự thay đổi quy định về RBAC Scope (vd: mở quyền xem `INTERNAL` cho sinh viên) hoặc thay đổi cấu trúc error RFC 7807, báo cáo phân tích này phải được cập nhật lại.
