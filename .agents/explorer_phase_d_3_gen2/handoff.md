# Handoff Report — Phase D: Search API, RBAC Filtering & Celery Indexing Task

**Agent**: Explorer 3 Phase D (Replacement)  
**Working Directory**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_d_3_gen2`  
**Handoff Type**: Hard Handoff (Task Completed)  
**Date**: 2026-08-11  

---

## 1. Observation

Direct observations from codebase inspection:

1. **OpenAPI Contract (`docs/api/openapi.yaml`)**:
   - Dòng 36 định nghĩa tag `- name: search`.
   - Các dòng 384–673 (phần `paths:`) **thiếu hoàn toàn** route `/search`.
   - Các dòng 60–376 (phần `components/schemas:`) **thiếu** các schema `SearchQuery`, `SearchResultItem`, `SearchResponse`.

2. **RBAC Scope Helper (`apps/api/app/modules/documents/dependencies.py`)**:
   - Dòng 14–26: Hàm `get_allowed_scopes_for_user(user)` trả về `['PUBLIC', 'STUDENT_AFFAIRS', 'INTERNAL']` cho `admin`/`staff` và `['PUBLIC', 'STUDENT_AFFAIRS']` cho `student`.

3. **Celery Worker Tasks (`apps/api/app/worker/tasks.py`)**:
   - Dòng 41–171: Task `process_document_task(job_id, version_id)`. Bước 6 (dòng 146–162) chuyển `version.ocr_status = "SUCCEEDED"`, nhưng hiện tại chưa gọi `index_document_chunks_task`.

4. **Celery Configuration (`apps/api/app/worker/celery_app.py`)**:
   - Dòng 32–34: Cấu hình `task_routes` chỉ mới có `app.worker.tasks.process_document_task`. Chưa khai báo route cho `index_document_chunks_task`.

5. **Search Module Directory (`apps/api/app/modules/search/`)**:
   - Thư mục `apps/api/app/modules/search` hiện **chưa tồn tại** (chưa có `router.py`, `schemas.py`, `service.py`).

6. **Domain RBAC Matrix (`docs/domain/rbac-matrix.md`)**:
   - Dòng 14–20: Phân định rõ scope `PUBLIC` (tất cả), `STUDENT_AFFAIRS` (`student`, `staff`, `admin`), `INTERNAL` (`staff`, `admin`).

---

## 2. Logic Chain

1. **Từ Observation 1 & 6**: Dự án áp dụng nguyên tắc Contract-First (`docs/api/openapi.yaml` là Single Source of Truth). Vì tag `search` đã được khai báo nhưng route `/search` và các schemas liên quan chưa có, bước đầu tiên của triển khai Phase D là patch `docs/api/openapi.yaml` với route `POST /search` (và `GET /search`) cùng các schemas `SearchQuery`, `SearchResultItem`, `SearchResponse`.
2. **Từ Observation 2 & 6**: `get_allowed_scopes_for_user(user)` trong `dependencies.py` đã đóng gói chính xác quy tắc phân quyền scope. Khi tiếp nhận yêu cầu tìm kiếm từ client, lấy giao (intersection) giữa scope client yêu cầu và `get_allowed_scopes_for_user(user)` tạo ra `effective_scopes`. Điều này đảm bảo role `student` không thể truy cập tài liệu `INTERNAL` ngay cả khi truyền `scope=INTERNAL` trong request payload.
3. **Từ Observation 3 & 4**: Tác vụ OCR `process_document_task` hoàn thành với `version.ocr_status = "SUCCEEDED"`. Thêm lời gọi `index_document_chunks_task.delay(version_id)` sau `await session.commit()` trong `process_document_task` giúp luồng dữ liệu tự động chuyển từ OCR sang Text Chunking & Vector Indexing mà không cần can thiệp thủ công.
4. **Từ Observation 5**: Tạo mới module `apps/api/app/modules/search/` (`router.py`, `schemas.py`, `service.py`) để tiếp nhận HTTP request, gọi `EmbeddingService` sinh vector truy vấn 1024 chiều, và gọi `search_hybrid` thực thi SQL CTE RRF trên PostgreSQL (kèm SQLite fallback cho test).

---

## 3. Caveats

1. **SQLite Pytest Fallback**: Trong môi trường local dev/pytest, DB chạy trên SQLite in-memory (`sqlite+aiosqlite:///:memory:`). SQLite không hỗ trợ toán tử `<=>` của pgvector hay `tsvector`/`ts_rank_cd` của PostgreSQL, nên `search_hybrid` sử dụng Python-level RRF Fallback.
2. **Mock Embedding Strategy**: Để unit test và CI chạy tức thì mà không cần GPU hay tải weights 2.2GB của model BGE-M3, `EmbeddingService` tự động dùng `MockEmbeddingStrategy` (sinh vector L2-normalized 1024-dim từ hash SHA256).

---

## 4. Conclusion

Kiến trúc Search REST API, OpenAPI Spec patch, Celery Indexing Task và RBAC Scope Filtering cho Phase D đã được phân tích đầy đủ và nhất quán với thiết kế DB Vector Storage (Explorer 2) và Embedding/Chunking Engine (Explorer 1). Đã sẵn sàng cho giai đoạn Implementer triển khai code.

---

## 5. Verification Method

### Các file cần kiểm tra:
- `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_d_3_gen2\analysis.md` (Báo cáo chi tiết)
- `E:\SoHoaTaiLieu_DATN\docs\api\openapi.yaml` (Contract YAML)
- `E:\SoHoaTaiLieu_DATN\apps\api\app\modules\documents\dependencies.py` (Scope Helper)
- `E:\SoHoaTaiLieu_DATN\apps\api\app\worker\tasks.py` (Celery Tasks)

### Lệnh kiểm tra sau khi triển khai:
1. Static Analysis:
   ```bash
   cd apps/api && uv run ruff check app tests
   cd apps/api && uv run mypy app
   ```
2. Unit & Integration Tests:
   ```bash
   cd apps/api && uv run pytest tests/test_search*.py tests/test_indexing*.py
   ```
3. OpenAPI Contract Sync Verification:
   ```bash
   pnpm openapi:lint
   ```
