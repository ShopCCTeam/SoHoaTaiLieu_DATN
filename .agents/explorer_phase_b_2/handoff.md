# Handoff Report — Phase B (DB Models, Alembic Migration & MinIO Storage)

> **Agent**: Explorer 2 (Phase B - DB & Storage)  
> **Thư mục**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_2`  
> **Recipient**: Parent (Conversation ID: `9f83b9ff-33a4-4ee5-a9e2-f52e7b90ad52`)  
> **Thời gian**: 2026-08-11  

---

## 1. Observation (Quan sát thực tế)

1. **DB Models hiện tại (`apps/api/app/models/`)**:
   - `User` (`user.py`): PK `id` `String(36)`, `role` enum (`admin`, `staff`, `student`), `is_active`, timestamps.
   - `DocumentScope` (`document_scope.py`): PK `id` `Integer`, unique `code` `String(32)` (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`).
   - `RefreshSession` (`refresh_session.py`): Sử dụng custom `_UUID` (CHAR(36) trên SQLite, UUID trên Postgres) và `_INet` (String(45) trên SQLite, INET trên Postgres) giúp bảo đảm **Database Portability**.
   - `Base` (`apps/api/app/db/base.py`): `DeclarativeBase` duy nhất cho toàn bộ ORM models.

2. **Alembic Migrations hiện tại (`apps/api/alembic/versions/`)**:
   - `0001_users_and_scopes.py`: Tạo `users`, `document_scopes`, seed 3 scopes mặc định.
   - `0002_refresh_sessions.py`: Tạo `refresh_sessions` hỗ trợ rotation & family revocation.
   - `alembic/env.py`: Đã cấu hình async migration online/offline mode và hỗ trợ fallback SQLite cho unit test.

3. **Cấu hình MinIO (`apps/api/app/core/config.py`)**:
   - `minio_endpoint` (`localhost:9000`), `minio_access_key` (`minioadmin`), `minio_secret_key` (`minioadmin`), `minio_bucket` (`ctsv-documents`), `minio_secure` (`False`).
   - `validate_production()` kiểm tra `MINIO_SECRET_KEY` không được dùng giá trị mặc định khi ở môi trường `production`/`staging`.

4. **Test Fixtures hiện tại (`apps/api/tests/conftest.py`)**:
   - Khởi tạo SQLite async engine `db_engine` và session `db_session` với `create_savepoint`.
   - `pg_engine` cho integration test trên PostgreSQL.

---

## 2. Logic Chain (Chuỗi lập luận)

1. **Thiết kế Model SQLAlchemy**:
   - Bảng `documents` cần lưu thông tin metadata tổng quan (tiêu đề, loại văn bản, phạm vi scope, số hiệu, ngày hiệu lực, tác giả, tags). Trường `tags` và `metadata_json` sử dụng custom `_JSONB` (PG JSONB, SQLite JSON) để đảm bảo linh hoạt mở rộng và test compatibility.
   - Bảng `document_versions` đại diện cho từng phiên bản file đính kèm. Khóa chính `id` là UUID, khóa ngoại `document_id` trỏ về `documents.id`. Có chỉ mục duy nhất `(document_id, version_number)`.
   - Cả 2 mô hình sử dụng `_UUID` TypeDecorator để tương thích 100% khi chạy unit test trên SQLite in-memory mà không làm hỏng tính năng native UUID của PostgreSQL.

2. **Alembic Migration Plan (`0003_documents_and_versions.py`)**:
   - Tạo migration `0003` trỏ `down_revision = "0002"`.
   - Tạo các chỉ mục tối ưu truy vấn: `ix_documents_status`, `ix_documents_type`, `ix_documents_scope_code`, `ix_documents_deleted_at`, `ix_document_versions_document_id`, `ix_document_versions_checksum`.

3. **MinIO S3 Integration (`storage.py`)**:
   - Đóng gói SDK `minio.Minio` chính thức của Python.
   - Bọc các hàm đồng bộ trong `asyncio.to_thread` để tránh làm kẹt event loop của FastAPI.
   - Hỗ trợ đầy đủ: `ensure_bucket_exists`, `upload_bytes`, `download_bytes`, `get_presigned_url`, `delete_file`, `file_exists`.

4. **Test Strategy**:
   - Cung cấp `MockStorageService` fixture lưu dữ liệu file in-memory dict cho unit tests.
   - Thêm `seeded_document` và `seeded_document_version` fixtures vào `conftest.py`.

---

## 3. Caveats (Lưu ý & Giới hạn)

- **Phạm vi chưa khảo sát**: Các bảng liên quan đến Celery Job queue (`jobs`) và kết quả OCR (`ocr_blocks`) nằm trong phạm vi Phase C.
- **Giả định**: MinIO server chạy ở chế độ S3-compatible tiêu chuẩn trên cổng 9000 trong local dev Docker stack (`docker-compose.yml`).
- **Lưu ý triển khai**: Khi Implementer tạo migration `0003`, cần khai báo import model `Document` và `DocumentVersion` vào `alembic/env.py` và `app/models/__init__.py` để autodiscovery hoạt động tốt.

---

## 4. Conclusion (Kết luận)

Đã hoàn thành thiết kế chi tiết toàn bộ lớp cơ sở dữ liệu và dịch vụ lưu trữ cho Phase B:
- File báo cáo phân tích toàn diện được lưu tại `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_2\analysis.md`.
- Thiết kế đảm bảo nguyên tắc **Database Portability** (chạy chuẩn trên PostgreSQL và SQLite), chuẩn mã hóa bảo mật, tuân thủ OpenAPI contract và hướng dẫn dự án (`00-08.mdc`).

---

## 5. Verification Method (Phương pháp kiểm tra độc lập)

Để xác minh thiết kế khi tiến hành cài đặt code:

1. **Kiểm tra cú pháp & Type Check**:
   ```bash
   cd apps/api
   uv run mypy app
   uv run ruff check app tests
   ```

2. **Chạy Test Suite sẵn có & Test mới**:
   ```bash
   cd apps/api
   uv run pytest
   ```

3. **Kiểm tra Migration Alembic**:
   ```bash
   cd apps/api
   uv run alembic check
   ```

---
