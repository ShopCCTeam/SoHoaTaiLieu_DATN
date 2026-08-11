# Handoff Report — Explorer 2 (Phase C: OCR Pipeline DB Schema & Storage Design)

**Agent**: Explorer 2 (Phase C - OCR Pipeline)  
**Working Directory**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_c_2`  
**Date**: 2026-08-11  
**Target Recipient**: Parent / Orchestrator / Implementer  

---

## 1. Observation (Quan Sát Tự Nhiên & Bằng Chứng)

- **Cấu trúc ORM Models hiện tại**:
  - `apps/api/app/db/base.py:11`: Kế thừa `DeclarativeBase`. Single source of truth cho Alembic scan `Base.metadata`.
  - `apps/api/app/models/document_version.py:42-45`: Trường `ocr_status` (`NOT_STARTED`, `QUEUED`, `PROCESSING`, `SUCCEEDED`, `FAILED`) và `requires_review` (Boolean, default False) đã được định nghĩa.
  - `apps/api/app/models/job.py:30-35`: Trường `type` chứa enum `OCR` và `target_version_id` liên kết tới `document_versions.id`.
  - `apps/api/app/core/enums.py:1-25`: Chưa có `OCRReviewStatus` và `OCRPageStatus`.

- **Alembic Migrations hiện tại**:
  - `apps/api/alembic/versions/0003_documents_versions_and_jobs.py:61-113`: Đã tạo bảng `document_versions` và `jobs`. Đã sẵn sàng cho revision kế tiếp `0004`.

- **OpenAPI Contract & FE Mapper Spec**:
  - `docs/api/openapi.yaml:140-148`: `OCRReviewStatus` có enum `PENDING`, `APPROVED`, `CORRECTED`.
  - `docs/api/openapi.yaml:240-275`: `OCRBlock` schema yêu cầu các thuộc tính `id`, `ocr_job_id`, `page_number`, `bbox` (`[x0, y0, x1, y1]`), `text`, `confidence`, `requires_review`, `review_status`, `reviewed_by`, `reviewed_at`, `is_edited`, `edited_by`, `edited_at`, `original_text`, `processing_time_ms`.
  - `apps/web/lib/api/types.ts:77-97` & `apps/web/lib/api/mappers.ts:96-115`: FE đã hỗ trợ map trực tiếp từ DTO backend `ocr_blocks` sang domain model cho giao diện Review split-view (Phase F3).

- **Yêu cầu nhiệm vụ bổ sung từ User Request**:
  - Bổ sung giá trị `REJECTED` vào enum `OCRReviewStatus` (`PENDING`, `APPROVED`, `REJECTED`, `CORRECTED`).
  - Thiết kế bảng `ocr_pages` và `ocr_blocks` với đầy đủ các trường: `id`, `version_id`, `page_number`, `block_index`, `text_content`, `confidence`, `bbox` (JSONB `[x0, y0, x1, y1]`), `requires_review` (bool), `review_status`, `edited_text`.
  - Đánh chỉ mục composite index bắt buộc trên `(version_id, page_number)` để đảm bảo tốc độ truy vấn cao.

---

## 2. Logic Chain (Chuỗi Lý Luận)

1. **Từ Quan Sát Cấu Trúc DB Hiện Tại & Yêu Cầu OCR**:
   - `document_versions` đại diện cho file PDF được upload. Khi xử lý OCR, một version có thể chứa $N$ trang và mỗi trang chứa $M$ block văn bản.
   - Việc tách riêng 2 bảng `ocr_pages` và `ocr_blocks` cho phép vừa quản lý metadata cấp trang (số trang, kích thước, ảnh preview MinIO), vừa quản lý chi tiết từng khối văn bản bóc tách được.

2. **Từ Yêu Cầu Tối Ưu Truy Vấn Màn Hình Review Split-View**:
   - Giao diện FE split-view tải các block OCR theo từng trang (`page_number`).
   - Do đó, việc đánh chỉ mục composite `ix_ocr_blocks_version_page` trên `(version_id, page_number)` sẽ giúp truy vấn `WHERE version_id = :v AND page_number = :p` đạt độ phức tạp $O(\log N)$ thay vì quét toàn bộ bảng.

3. **Từ Quy Trình Duyệt Dữ Liệu OCR (Human-in-the-Loop)**:
   - Khi OCR hoàn tất, cờ `requires_review` được đặt là `true` cho các block có `confidence < threshold` (mặc định 0.90).
   - Enum `OCRReviewStatus` quản lý vòng đời duyệt: `PENDING` (chờ xem) -> `APPROVED` (đúng), `CORRECTED` (đã sửa văn bản) hoặc `REJECTED` (loại bỏ block nhiễu).
   - Trường `edited_text` lưu văn bản sau hiệu chỉnh, trong khi `original_text` giữ nguyên văn bản thô OCR để đối chiếu.

4. **Từ Đồng Bộ Alembic Migration**:
   - Revision `0004_ocr_pages_and_blocks.py` kế thừa từ `0003` và thiết kế các lệnh `create_table`, `create_index` và `drop_table` chuẩn xác để bảo đảm tính toàn vẹn dữ liệu khi upgrade / downgrade.

---

## 3. Caveats (Lưu Ý & Giới Hạn)

- **Thực thi Read-Only**: Agent chỉ thực hiện phân tích và thiết kế kiến trúc. Chưa thực hiện tạo/sửa file nguồn trong `apps/api/app/models/` hoặc `apps/api/alembic/versions/`.
- **Hệ tọa độ `bbox`**: Giá trị `bbox` được lưu dưới dạng mảng JSON `[x0, y0, x1, y1]` theo hệ tọa độ chuẩn PDF (points). Màn hình FE canvas có trách nhiệm chuyển đổi tọa độ này sang điểm ảnh pixel dựa trên tỉ lệ hiển thị (zoom level).
- **SQLite vs PostgreSQL (JSONB vs JSON)**: SQLAlchemy `JSON` type được sử dụng trong ORM Model để tương thích cả `aiosqlite` khi chạy pytest local lẫn `JSONB` trên PostgreSQL 16.

---

## 4. Conclusion (Kết Luận)

- Đã thiết kế hoàn chỉnh hai ORM Models `OCRPage` và `OCRBlock` tuân thủ chuẩn SQLAlchemy 2.x Async.
- Đã thiết kế Alembic Migration `0004_ocr_pages_and_blocks.py` với đầy đủ chỉ mục composite `(version_id, page_number)`, `(version_id, page_number, block_index)` và `(version_id, requires_review, review_status)`.
- Kết quả phân tích chi tiết đã được ghi tại: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_c_2\analysis.md`.

---

## 5. Verification Method (Phương Pháp Kiểm Chứng Cho Agent Tiếp Theo)

Khi Implementer triển khai mã nguồn và migration cho Phase C, có thể kiểm chứng độc lập bằng các bước sau:

1. **Kiểm tra cú pháp & Type Check**:
   ```bash
   cd apps/api
   uv run mypy app
   uv run ruff check app tests
   ```

2. **Chạy Alembic Migration (hoặc Pytest Integration Test)**:
   ```bash
   cd apps/api
   uv run pytest tests/test_alembic.py
   ```

3. **Kiểm tra Schema & Indexes trong DB Shell**:
   - Kiểm tra bảng `ocr_pages` và `ocr_blocks` được tạo thành công.
   - Xử lý kiểm tra index bằng câu lệnh PostgreSQL:
     ```sql
     \d ocr_blocks
     ```
     Xác nhận có chỉ mục `ix_ocr_blocks_version_page` trên 2 cột `(version_id, page_number)`.
