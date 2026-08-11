# Forensic Audit Report — Phase B (Re-Audit)

**Work Product**: `apps/api/` (FastAPI Backend, Document Processing Pipeline, Celery Worker, Jobs, Storage)  
**Profile**: General Project / Benchmark Integrity Mode  
**Verdict**: INTEGRITY VIOLATION  

## Executive Summary
Biện pháp Re-Audit Phase B đã kiểm tra độc lập toàn bộ 4 hạng mục theo yêu cầu:
1. **Pytest Test Suite Execution**: 116 tests PASS, 0 FAIL (4 SKIPPED do môi trường PostgreSQL local không chạy). -> **PASS**
2. **Code Coverage**: Đạt **77.55%** (yêu cầu >= 80.00%). Thất bại ngưỡng yêu cầu 80%. -> **FAIL**
3. **Static Analysis & Type Checks**: `ruff check`, `ruff format --check`, `mypy app` đều vượt qua 100% sạch sẽ (0 lỗi). -> **PASS**
4. **Authentic Implementation & Anti-Facade Inspection**: Kiểm tra chi tiết mã nguồn trong `tasks.py`, `modules/documents/`, `modules/jobs/`, `services/storage.py` không phát hiện mã hardcode kết quả, không có facade/dummy implementation, không có bypass test. -> **PASS**

Do Check 2 không đạt ngưỡng 80% coverage (đạt 77.55%), kết luận theo nguyên tắc kiểm toán độc lập là **INTEGRITY VIOLATION** (không đáp ứng tiêu chuẩn kiểm thử coverage).

---

## Detailed Check Results

### Check 1: Unit & Integration Test Suite (`pytest`)
- **Lệnh thực thi**: `uv run pytest --cov=app --cov-report=term-missing`
- **Kết quả**:
  - Total collected: 120 tests
  - Passed: 116 tests
  - Skipped: 4 tests (`test_alembic.py:97`, `test_models_pg.py:24`, `test_models_pg.py:63`, `test_models_pg.py:138` do thiếu kết nối PostgreSQL)
  - Failed: 0 tests
- **Đánh giá**: **PASS** (Tất cả 116 tests active đều pass 100%).

### Check 2: Global Code Coverage (>= 80%)
- **Lệnh thực thi**: `uv run pytest --cov=app --cov-report=term-missing`
- **Kết quả**:
  - Total Statements: 1510
  - Missed Statements: 339
  - Measured Coverage: **77.55%**
- **Bảng phân tích Coverage theo Module**:
  - `app/core/config.py`: 100.00%
  - `app/core/errors.py`: 95.92%
  - `app/core/logging.py`: 90.00%
  - `app/core/middleware.py`: 100.00%
  - `app/db/session.py`: 84.38%
  - `app/models/*`: 92% - 100%
  - `app/modules/auth/refresh_service.py`: 60.67% (Missed 35 stmts)
  - `app/modules/auth/router.py`: 72.31% (Missed 36 stmts)
  - `app/modules/documents/router.py`: 50.43% (Missed 57 stmts)
  - `app/modules/documents/service.py`: 54.55% (Missed 85 stmts)
  - `app/modules/jobs/router.py`: 54.76% (Missed 19 stmts)
  - `app/services/storage.py`: 52.17% (Missed 44 stmts)
  - `app/worker/tasks.py`: 76.56% (Missed 15 stmts)
- **Đánh giá**: **FAIL** (77.55% < 80.00%).

### Check 3: Code Style, Formatting & Type Safety
- `uv run ruff check app tests` -> Output: `All checks passed!` -> **PASS**
- `uv run ruff format --check app tests` -> Output: `60 files already formatted` -> **PASS**
- `uv run mypy app` -> Output: `Success: no issues found in 41 source files` -> **PASS**
- **Đánh giá**: **PASS**

### Check 4: Integrity Forensics (Hardcoded Results & Facade Detection)
Kiểm tra trực tiếp các file target:
1. `apps/api/app/worker/tasks.py`:
   - `run_async` xử lý chính xác coroutine trong Celery worker thread cũng như eager mode mà không làm treo hay xung đột event loop.
   - Trạng thái Job và DocumentVersion chuyển đổi thực tế trong DB: `PROCESSING` -> progress `10%` -> `50%` -> `100%` -> `SUCCEEDED`/`UNDER_REVIEW` (hoặc `FAILED` nếu có ngoại lệ).
   - Không phát hiện stub hay hardcode kết quả.
2. `apps/api/app/modules/documents/`:
   - Service & Router triển khai đầy đủ truy vấn SQLAlchemy lọc scope theo role (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`), pagination, Idempotency check thực tế, lưu trữ file qua Storage Service, khởi tạo bản ghi DB thực thụ.
   - Quy trình phê duyệt phiên bản (`approve_document_version`) kiểm tra thực sự trạng thái `ocr_status == 'SUCCEEDED'` và xử lý chuyển phiên bản cũ sang `SUPERSEDED`.
3. `apps/api/app/modules/jobs/`:
   - Lấy trạng thái Job thực tế từ DB, phân quyền owner/staff/admin chuẩn xác.
   - Huỷ job (`cancel_job`) kiểm tra trạng thái và cập nhật timestamp `finished_at`.
4. `apps/api/app/services/storage.py`:
   - Triển khai `LocalStorageService` ghi/đọc file thực sự lên ổ đĩa temp và `MinioStorageService` tương tác qua SDK S3.
- **Đánh giá**: **PASS** (Logic thực sự, không có gian lận).

---

## Conclusion & Actionable Recommendations
- **Verdict**: **INTEGRITY VIOLATION**
- **Lý do**: Mặc dù logic mã nguồn đạt chuẩn chân thực (không cheating), 116 tests pass và type/lint sạch 100%, nhưng chỉ số code coverage hiện tại chỉ đạt **77.55%** (chưa đạt mốc tối thiểu 80.00%).
- **Hành động khắc phục**: Cần bổ sung test case trong `tests/test_documents_router.py`, `tests/test_documents_versions.py`, `tests/test_jobs_router.py` và `tests/test_services_storage.py` để phủ các luồng lỗi / edge cases, đưa coverage toàn hệ thống lên >= 80%.
