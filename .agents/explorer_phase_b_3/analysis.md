# Báo Cáo Phân Tích Kỹ Thuật: Celery Async Tasks, PDF Magic Bytes Validation, File Size Limits & Error Handling (Phase B)

> **Mô tả**: Báo cáo phân tích chuyên sâu cho Phase B (Document Management & Storage) thuộc hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên (`SoHoaTaiLieu_DATN`).  
> **Tác giả**: Explorer 3 (Phase B)  
> **Ngày thực hiện**: 2026-08-11  
> **Trạng thái**: READ-ONLY Investigation Completed  

---

## 1. Tổng Quan & Mục Tiêu Phân Tích

Mục tiêu của nghiên cứu này là thiết kế kiến trúc xử lý tài liệu bất đồng bộ (Celery + Redis), cơ chế kiểm tra tính hợp lệ của file PDF (Magic Bytes + File Size Limit 50MB), quy trình chuyển đổi trạng thái công việc (Status Machine Pipeline), cùng hệ thống báo lỗi chuẩn **RFC 7807 Problem Details** cho Phase B.

### Phạm Vi Khảo Sát
1. Cấu hình Celery Worker trong `apps/api/app/worker/` và các cài đặt Redis Broker trong `app/core/config.py`.
2. Quy trình xử lý tài liệu chạy nền (Background Tasks Pipeline) và sơ đồ chuyển trạng thái (`UPLOADING` -> `PROCESSING` -> `READY` / `FAILED`).
3. Dịch vụ xác thực file PDF: kiểm tra PDF Magic Bytes (`%PDF-`), giới hạn dung lượng file (tối đa 50MB), xác thực MIME type `application/pdf`.
4. Định dạng lỗi chuẩn RFC 7807 cho các kịch bản: file không hợp lệ (`INVALID_FILE_TYPE`), vượt dung lượng (`FILE_SIZE_EXCEEDED`), không đủ quyền scope (`FORBIDDEN`), không tìm thấy tài liệu (`NOT_FOUND`).
5. Chiến lược Unit Test và Integration Test cho Celery Async Tasks và PDF Validator Service.

---

## 2. Phân Tích Hiện Trạng Codebase

### 2.1 Cấu Hình Hệ Thống Hiện Tại (`app/core/config.py`)
- Quản lý thiết lập bằng Pydantic `Settings`.
- Đã có cấu hình Redis cơ bản: `redis_url: str = "redis://localhost:6379/0"`.
- Đã có cấu hình MinIO cơ bản:
  - `minio_endpoint: str = "localhost:9000"`
  - `minio_access_key: str = "minioadmin"`
  - `minio_secret_key: SecretStr = Field(...)`
  - `minio_bucket: str = "ctsv-documents"`
- **Thiếu sót cần bổ sung cho Celery**:
  - `celery_broker_url`: mặc định kết nối tới Redis DB 0 (`redis://localhost:6379/0`).
  - `celery_result_backend`: mặc định kết nối tới Redis DB 1 (`redis://localhost:6379/1`).
  - `celery_task_always_eager`: cờ cấu hình chạy đồng bộ cho pytest fixture (`default = False`).
  - `celery_task_time_limit`: giới hạn cứng thời gian xử lý (default = 300s / 5 phút).
  - `celery_task_soft_time_limit`: giới hạn mềm để giải phóng tài nguyên (default = 240s / 4 phút).

### 2.2 Hệ Thống Xử Lý Lỗi Hiện Tại (`app/core/errors.py`)
- Định dạng lỗi tuân thủ RFC 7807 (`ProblemDetail` model).
- Đã hỗ trợ các mã `ErrorCode`: `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `VALIDATION_ERROR`, `INVALID_FILE_TYPE`, `IDEMPOTENCY_KEY_MISMATCH`, `RATE_LIMIT`, `CONFLICT`, `INTERNAL`.
- **Cần bổ sung**:
  - `FILE_SIZE_EXCEEDED` (Mã HTTP status `413 Payload Too Large`).
  - Helper functions: `payload_too_large(detail, request_id)` và `invalid_file_type(detail, request_id)`.

### 2.3 Chuẩn OpenAPI Contract (`docs/api/openapi.yaml`)
- Sơ đồ enum `DocumentStatus`: `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `ARCHIVED`.
- Sơ đồ enum `JobStatus`: `QUEUED`, `PROCESSING`, `SUCCEEDED`, `FAILED`, `CANCELLED`.
- Sơ đồ enum `DocumentScope`: `PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`.
- Endpoint `POST /documents`:
  - Trả về `202 Accepted` với body `UploadResponse` (`document_id`, `job_id`, `status: "QUEUED"`).
  - Yêu cầu header `Idempotency-Key` (UUID v4/v7).

---

## 3. Đề Xuất Thiết Kế Chi Tiết

### 3.1 Dịch Vụ Kiểm Tra File PDF (`PdfValidatorService`)

#### Nguyên Lý Hoạt Động
Để tránh tấn công giả mạo đuôi file (File Extension Spoofing) hoặc cạn kiệt tài nguyên (DoS qua file dung lượng lớn), việc kiểm tra file phải thực hiện theo cơ chế **Streamed Inspection**:

1. **Header Inspection (Magic Bytes)**: Read 1024 bytes đầu tiên của file stream. Kiểm tra xem 5 bytes đầu tiên có bắt đầu bằngchuỗi magic bytes `%PDF-` (`b"%PDF-"`) hay không.
2. **MIME Type Validation**: Kiểm tra header `Content-Type` của request multipart có là `application/pdf`.
3. **Streamed Size & Checksum Calculation**: Đọc từng chunk 64KB để tính tổng dung lượng và băm SHA-256 đồng thời. Nếu tổng dung lượng vượt quá **50MB** (52,428,800 bytes), dừng đọc ngay lập tức và ném lỗi `FILE_SIZE_EXCEEDED` (`413 Payload Too Large`).

#### Thiết Kế Code Đề Xuất (`app/services/pdf_validator.py`)

```python
"""PDF File Validation Service (Magic Bytes, File Size, Content-Type, SHA-256)."""

from __future__ import annotations

import hashlib
from typing import BinaryIO, AsyncIterator

from fastapi import UploadFile

from app.core.errors import ApiError, ErrorCode, status


class PdfValidatorService:
    MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    PDF_MAGIC_BYTES: bytes = b"%PDF-"
    ALLOWED_MIME_TYPE: str = "application/pdf"

    @classmethod
    async def validate_upload_file(
        cls,
        upload_file: UploadFile,
        request_id: str = "",
    ) -> tuple[str, int]:
        """Validate UploadFile stream.

        Returns:
            tuple[str, int]: (sha256_checksum_hex, total_file_size_bytes)

        Raises:
            ApiError: HTTP 415 nếu sai Magic Bytes / Content-Type.
            ApiError: HTTP 413 nếu dung lượng vượt quá 50MB.
        """
        # 1. Check Content-Type header
        if upload_file.content_type and upload_file.content_type.lower() != cls.ALLOWED_MIME_TYPE:
            raise ApiError(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                code=ErrorCode.INVALID_FILE_TYPE,
                title="Định dạng file không hỗ trợ",
                detail=f"Content-Type '{upload_file.content_type}' không phải 'application/pdf'.",
                request_id=request_id,
            )

        # 2. Read initial header chunk for Magic Bytes
        header = await upload_file.read(1024)
        if len(header) < 5 or not header.startswith(cls.PDF_MAGIC_BYTES):
            raise ApiError(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                code=ErrorCode.INVALID_FILE_TYPE,
                title="File PDF không hợp lệ",
                detail="Nội dung file không đúng định dạng PDF (thiếu magic bytes '%PDF-').",
                request_id=request_id,
            )

        # 3. Stream chunk reading to calculate SHA-256 & verify size limit
        hasher = hashlib.sha256(header)
        total_bytes = len(header)

        while chunk := await upload_file.read(64 * 1024):  # 64KB chunk
            total_bytes += len(chunk)
            if total_bytes > cls.MAX_FILE_SIZE_BYTES:
                raise ApiError(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    code="FILE_SIZE_EXCEEDED",
                    title="Dung lượng file vượt quá giới hạn",
                    detail="Dung lượng file PDF không được vượt quá 50MB.",
                    request_id=request_id,
                )
            hasher.update(chunk)

        # Reset pointer cho phép ghi vào Storage
        await upload_file.seek(0)
        return hasher.hexdigest(), total_bytes
```

---

### 3.2 Cấu Hình Celery Worker & Redis Broker

#### Đề Xuất Cập Nhật Settings (`app/core/config.py`)
Thêm các biến cấu hình Celery vào `Settings`:

```python
    # ---- Celery & Redis ----
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_always_eager: bool = False
    celery_task_time_limit: int = 300  # 5 minutes
    celery_task_soft_time_limit: int = 240  # 4 minutes
```

#### Thiết Kế Celery Application (`apps/api/app/worker/celery_app.py`)

```python
"""Celery Worker Instance & Configuration."""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ctsv_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    result_expires=86400,  # 24 giờ
    worker_prefetch_multiplier=1,  # Ngăn 1 worker ôm nhiều task nặng cùng lúc
    task_always_eager=settings.celery_task_always_eager,
    task_routes={
        "app.worker.tasks.process_document_task": {"queue": "documents"},
    },
)
```

---

### 3.3 Pipeline Xử Lý Bất Đồng Bộ & Chuyển Đổi Trạng Thái (State Machine)

#### Sơ Đồ Luồng Xử Lý Tài Liệu

```
[Client] 
   │
   │  1. POST /documents (multipart: file, title, scope, Idempotency-Key)
   ▼
[FastAPI Route]
   │  2. Validate PDF (Magic Bytes %PDF-, size ≤ 50MB, Content-Type)
   │  3. Upload raw file stream to MinIO S3 ("ctsv-documents/raw/{version_id}.pdf")
   │  4. DB Transaction:
   │     - Insert Document (status = DRAFT)
   │     - Insert DocumentVersion (status = DRAFT, ocr_status = QUEUED, file_size, checksum)
   │     - Insert Job (type = OCR, status = QUEUED, progress = 0)
   │  5. Trigger process_document_task.delay(job_id, version_id)
   │  6. Return HTTP 202 Accepted { success: true, data: { document_id, job_id, status: "QUEUED" } }
   ▼
[Redis Broker Queue: "documents"]
   │
   ▼
[Celery Worker: process_document_task]
   │
   ├──► State Transition 1: Update Job (status = PROCESSING, progress = 10%)
   │                        Update DocumentVersion (ocr_status = PROCESSING)
   │
   ├──► Step A: Fetch document version metadata from DB
   ├──► Step B: Download PDF stream from MinIO S3
   ├──► Step C: Compute page count & PDF structure verification (PyMuPDF fitz) -> progress = 40%
   ├──► Step D: Trigger OCR / Text extraction pipeline (Phase C hook) -> progress = 80%
   │
   ├──► Success Path:
   │      Update Job (status = SUCCEEDED, progress = 100%, finished_at = now())
   │      Update DocumentVersion (ocr_status = SUCCEEDED, status = UNDER_REVIEW)
   │
   └──► Failure Path (Catch Exception):
          Update Job (status = FAILED, error = str(exc), finished_at = now())
          Update DocumentVersion (ocr_status = FAILED)
          Log structured error with structlog
```

#### Thiết Kế Celery Task Core (`apps/api/app/worker/tasks.py`)

```python
"""Celery Background Tasks for Document Processing Pipeline."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from celery import shared_task
from structlog import get_logger

from app.core.config import get_settings
from app.db.session import get_session_factory

logger = get_logger(__name__)


def run_async(coro: Any) -> Any:
    """Helper chạy async coroutine bên trong Celery worker thread."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(name="app.worker.tasks.process_document_task", bind=True, max_retries=3)
def process_document_task(self, job_id: str, version_id: str) -> dict[str, Any]:
    """Task xử lý bất đồng bộ file tài liệu PDF sau khi upload.

    Chuyển trạng thái:
      - Job: QUEUED -> PROCESSING -> SUCCEEDED / FAILED
      - DocumentVersion.ocr_status: QUEUED -> PROCESSING -> SUCCEEDED / FAILED
    """
    logger.info("start_process_document_task", job_id=job_id, version_id=version_id)
    return run_async(_async_process_document(job_id, version_id))


async def _async_process_document(job_id: str, version_id: str) -> dict[str, Any]:
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Fetch Job & Version
        # 1. Update status to PROCESSING
        # 2. Download file from MinIO
        # 3. Analyze PDF structure & extract metadata
        # 4. Update status to SUCCEEDED or FAILED
        # Return summary dict
        pass
```

---

### 3.4 Định Dạng Lỗi RFC 7807 Cho Phase B

Tất cả các phản hồi lỗi từ API phải tuân thủ chuẩn RFC 7807 (`application/problem+json`).

#### 1. Lỗi Magic Bytes / File Không Phải PDF (HTTP 415)
```json
{
  "type": "https://api.example.edu.vn/problems/invalid_file_type",
  "title": "File PDF không hợp lệ",
  "status": 415,
  "detail": "Nội dung file không đúng định dạng PDF (thiếu magic bytes '%PDF-').",
  "code": "INVALID_FILE_TYPE",
  "request_id": "01912abc-3456-7890-abcd-ef1234567890"
}
```

#### 2. Lỗi Vượt Dung Lượng 50MB (HTTP 413)
```json
{
  "type": "https://api.example.edu.vn/problems/file_size_exceeded",
  "title": "Dung lượng file vượt quá giới hạn",
  "status": 413,
  "detail": "Dung lượng file PDF không được vượt quá 50MB.",
  "code": "FILE_SIZE_EXCEEDED",
  "request_id": "01912abc-3456-7890-abcd-ef1234567891"
}
```

#### 3. Lỗi Không Đủ Quyền Truy Cập Scope (HTTP 403)
```json
{
  "type": "https://api.example.edu.vn/problems/forbidden",
  "title": "Không đủ quyền",
  "status": 403,
  "detail": "Tài khoản sinh viên không có quyền tải lên hoặc truy cập tài liệu thuộc scope INTERNAL.",
  "code": "FORBIDDEN",
  "request_id": "01912abc-3456-7890-abcd-ef1234567892"
}
```

#### 4. Lỗi Không Tìm Thấy Tài Liệu (HTTP 404)
```json
{
  "type": "https://api.example.edu.vn/problems/not_found",
  "title": "Không tìm thấy",
  "status": 404,
  "detail": "Tài liệu với ID 'doc_01HXYZ9876' không tồn tại trên hệ thống.",
  "code": "NOT_FOUND",
  "request_id": "01912abc-3456-7890-abcd-ef1234567893"
}
```

---

## 4. Chiến Lược Testing (Unit & Integration Test)

### 4.1 Pytest Fixture Cấu Hình Celery Eager Mode
Trong `apps/api/tests/conftest.py`, thêm fixture cấu hình Celery chạy synchronous để test task không cần Redis server:

```python
@pytest.fixture(autouse=True)
def celery_eager_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cấu hình Celery chạy eager mode trong pytest (không cần Redis server)."""
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    get_settings.cache_clear()
```

### 4.2 Unit Tests Cho PDF Validator (`tests/test_pdf_validator.py`)
- Test case 1: Test file PDF chuẩn (`b"%PDF-1.7 ..."`), dung lượng 1MB -> Trả về SHA-256 & bytes count.
- Test case 2: Test file thiếu Magic Bytes (file text `b"Hello world"` hoặc `b"PNG..."`) -> Ném `ApiError` 415 `INVALID_FILE_TYPE`.
- Test case 3: Test file dung lượng 51MB -> Ném `ApiError` 413 `FILE_SIZE_EXCEEDED`.
- Test case 4: Test Content-Type không hợp lệ (`text/plain`) -> Ném `ApiError` 415 `INVALID_FILE_TYPE`.

### 4.3 Unit & Integration Tests Cho Celery Tasks (`tests/test_worker_tasks.py`)
- Test case 1: Run `process_document_task.delay(job_id, version_id)` thành công. Xử lý mock MinIO download -> Cập nhật Job status = `SUCCEEDED`, DocumentVersion.ocr_status = `SUCCEEDED`.
- Test case 2: Fail path khi MinIO trả về lỗi hoặc file hỏng -> Cập nhật Job status = `FAILED`, ghi nhận error message.

---

## 5. Kết Luận & Khuyến Nghị Thực Hiện

1. **Khuyến nghị triển khai**:
   - Thêm `celery_broker_url`, `celery_result_backend`, `celery_task_always_eager` vào `app/core/config.py`.
   - Bổ sung `FILE_SIZE_EXCEEDED` vào `ErrorCode` trong `app/core/errors.py`.
   - Tạo module `app/services/pdf_validator.py` và gói `app/worker/` (`celery_app.py`, `tasks.py`).
2. **Tính khép kín & An toàn**:
   - Việc kiểm tra Magic Bytes và File Size Limit ở ngay lớp Stream Ingestion giúp bảo vệ MinIO Storage và Celery Worker khỏi các file độc hại hoặc file quá khổ gây tràn RAM.
   - Sơ đồ chuyển trạng thái `QUEUED` -> `PROCESSING` -> `SUCCEEDED`/`FAILED` đảm bảo tính minh bạch và nhất quán trạng thái cho Frontend qua Polling API (`/jobs/{id}`).
