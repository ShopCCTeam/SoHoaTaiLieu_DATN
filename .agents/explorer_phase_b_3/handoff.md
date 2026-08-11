# Handoff Report — Explorer 3 (Phase B: Document Management & Storage)

> **Agent**: Explorer 3 (Phase B)  
> **Folder**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_3`  
> **Handoff Type**: Hard Handoff (Task Complete)  
> **Target Recipient**: Orchestrator / Implementer Phase B  

---

## 1. Observation

1. **Config & Env Setup (`apps/api/app/core/config.py`)**:
   - `Settings` chứa `redis_url: str = "redis://localhost:6379/0"` (dòng 50) và `minio_endpoint: str = "localhost:9000"`, `minio_bucket: str = "ctsv-documents"` (dòng 53-56).
   - Hiện chưa khai báo explicit `celery_broker_url`, `celery_result_backend`, hay `celery_task_always_eager`.
2. **Error Handling (`apps/api/app/core/errors.py`)**:
   - `ProblemDetail` hỗ trợ chuẩn RFC 7807 (dòng 16-25).
   - `ErrorCode` đã định nghĩa `INVALID_FILE_TYPE`, `IDEMPOTENCY_KEY_MISMATCH`, `NOT_FOUND`, `FORBIDDEN` (dòng 30-37).
   - Thiếu `FILE_SIZE_EXCEEDED` (mã HTTP status 413) trong `ErrorCode` và các helper builder tương ứng.
3. **OpenAPI Specification (`docs/api/openapi.yaml`)**:
   - Status Enums: `DocumentStatus` (`DRAFT`, `UNDER_REVIEW`, `APPROVED`, `ARCHIVED`), `JobStatus` (`QUEUED`, `PROCESSING`, `SUCCEEDED`, `FAILED`, `CANCELLED`), `DocumentScope` (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`).
   - Request upload `POST /documents` yêu cầu `Idempotency-Key` (UUID), file PDF ≤ 50MB, magic bytes `%PDF-`, MIME `application/pdf`, trả về `202 Accepted` kèm `UploadResponse`.

---

## 2. Logic Chain

1. **Từ Quan sát 1 (Cấu hình Settings hiện tại)**:
   - Celery cần broker URL và result backend URL rõ ràng. Việc bổ sung `celery_broker_url`, `celery_result_backend`, `celery_task_always_eager` vào `app/core/config.py` cho phép cấu hình linh hoạt giữa các môi trường Dev, Staging, Production và Pytest.
2. **Từ Quan sát 2 (Cơ chế báo lỗi RFC 7807)**:
   - Các trường hợp tải file hỏng hoặc quá 50MB cần trả về `application/problem+json` theo đúng quy ước dự án. Việc thêm `FILE_SIZE_EXCEEDED` và helper `invalid_file_type` / `payload_too_large` đảm bảo tương thích 100% với Frontend error handler.
3. **Từ Quan sát 3 (Yêu cầu xác thực PDF & Celery Task)**:
   - Đọc stream chunk (1024 bytes đầu) để check `%PDF-` tránh giả mạo file extension.
   - Stream băm SHA-256 đồng thời đếm byte để ngắt ngay khi vượt quá 50MB bảo vệ bộ nhớ RAM.
   - Chuyển tiếp file lên MinIO, tạo Job `QUEUED` và đẩy Celery task xử lý nền đảm bảo API phản hồi nhanh trong 202 Accepted.
   - Celery task cập nhật trạng thái `QUEUED` -> `PROCESSING` -> `SUCCEEDED` / `FAILED` cho phép Frontend poll progress qua API `/jobs/{id}`.

---

## 3. Caveats

- **Chưa thử nghiệm trực tiếp với Redis / MinIO thật**: Do đây là quy trình READ-ONLY investigation, việc kết nối thực tế tới Redis container / MinIO service sẽ được thực hiện ở bước triển khai/test.
- **Phụ thuộc Phase C (OCR)**: Celery task `process_document_task` được thiết kế khung xử lý pipeline hoàn chỉnh, khi đến Phase C chỉ cần gắn hook OCR engine (PaddleOCR/Tesseract) vào vị trí đã chừa sẵn.

---

## 4. Conclusion

- Kiến trúc Celery async task, PDF Magic Bytes Validator service, dung lượng 50MB limit, và chuẩn lỗi RFC 7807 cho Phase B đã được phân tích và thiết kế chi tiết trong `analysis.md`.
- Tất cả các trường hợp lỗi (`INVALID_FILE_TYPE`, `FILE_SIZE_EXCEEDED`, `FORBIDDEN`, `NOT_FOUND`) đã được định hình rõ ràng theo schema RFC 7807.
- Đã lập chiến lược Unit Test với `CELERY_TASK_ALWAYS_EAGER = True` đảm bảo test suite chạy nhanh, độc lập và phủ 100% các nhánh xử lý.

---

## 5. Verification Method

### 5.1 Các File Cần Kiểm Tra
- `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_3\analysis.md` (Báo cáo phân tích chi tiết)
- `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_3\handoff.md` (Báo cáo handoff này)

### 5.2 Lệnh Kiểm Tra Dự An
Sau khi Implementer tạo code theo bản thiết kế:
1. `cd apps/api && uv run pytest tests/test_pdf_validator.py tests/test_worker_tasks.py`
2. `cd apps/api && uv run ruff check app tests`
3. `cd apps/api && uv run mypy app`
