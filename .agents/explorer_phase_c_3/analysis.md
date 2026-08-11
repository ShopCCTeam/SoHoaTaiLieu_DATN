# Báo Cáo Phân Tích OCR Review APIs, Celery Integration & Approval Invariants (Phase C)

> **Người thực hiện**: Explorer Phase C 3  
> **Thư mục làm việc**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_c_3`  
> **Ngày phân tích**: 2026-08-11  
> **Trạng thái**: Hoàn tất phân tích đọc (Read-only Analysis)

---

## 1. Tóm Tắt Tổng Quan (Executive Summary)

Dựa trên việc kiểm tra chi tiết codebase (`apps/api`), tài liệu kiến trúc (`docs/domain/document-lifecycle.md`, `docs/rules/04-database-rag-ocr.md`), và hợp đồng OpenAPI (`docs/api/openapi.yaml`), Explorer Phase C 3 báo cáo kết quả khảo sát:

1. **OpenAPI Contract**:
   - Spec `docs/api/openapi.yaml` đã có sẵn các schema `OCRBlock` và `OCRReviewStatus` (với các giá trị `PENDING`, `APPROVED`, `CORRECTED`).
   - Tuy nhiên, phần `paths:` **chưa định nghĩa** 3 endpoints bắt buộc cho OCR Review:
     - `GET /documents/{id}/versions/{vid}/ocr`
     - `PATCH /documents/{id}/versions/{vid}/ocr/blocks/{bid}`
     - `POST /documents/{id}/versions/{vid}/ocr/batch-review`
2. **Celery Worker Integration**:
   - Tệp `apps/api/app/worker/tasks.py` hiện mới chứa hàm mock `_async_process_document` (chuyển trạng thái `Job` từ `QUEUED` -> `PROCESSING` -> `SUCCEEDED`).
   - Cần bổ sung logic tích hợp OCR Engine (PaddleOCR primary / Tesseract fallback), lưu dữ liệu các block vào bảng `ocr_blocks`, đánh giá confidence score theo ngưỡng (`OCR_CONFIDENCE_THRESHOLD = 0.8`), và cập nhật cờ `DocumentVersion.requires_review`.
3. **Approval Invariant Check**:
   - Hàm `approve_document_version` trong `apps/api/app/modules/documents/service.py` đã kiểm tra điều kiện pre-check `version.ocr_status == 'SUCCEEDED'` và `version.requires_review == False`.
   - Cần bổ sung truy vấn kiểm tra bất biến trực tiếp từ DB: **không còn block nghi ngờ nào (`confidence < 0.8` hoặc `requires_review = True`) ở trạng thái `review_status = 'PENDING'`** trước khi chuyển phiên bản sang `APPROVED`.

---

## 2. Chi Tiết OpenAPI Contract cho OCR Review Endpoints

Cần bổ sung 3 endpoint vào `docs/api/openapi.yaml` tuân thủ OpenAPI 3.1.0:

### 2.1. `GET /documents/{id}/versions/{vid}/ocr`
- **Mục đích**: Lấy danh sách các trang và OCR blocks của một phiên bản tài liệu (kèm bounding box, text, confidence, review_status).
- **Parameters**:
  - `id` (path, string): Document ID.
  - `vid` (path, string): Version ID.
  - `page` (query, integer, optional): Lọc theo số trang (`page_number >= 1`).
  - `requires_review` (query, boolean, optional): Lọc các block nghi ngờ (`requires_review=true`).
  - `review_status` (query, schema `OCRReviewStatus`, optional): Lọc theo trạng thái `PENDING`, `APPROVED`, `CORRECTED`.
- **Response `200 OK`**:
  ```yaml
  content:
    application/json:
      schema:
        allOf:
          - $ref: '#/components/schemas/SuccessEnvelope'
          - type: object
            properties:
              data:
                type: object
                required: [version_id, ocr_status, requires_review, total_blocks, pending_reviews, blocks]
                properties:
                  version_id: { type: string }
                  ocr_status: { type: string, enum: [NOT_STARTED, QUEUED, PROCESSING, SUCCEEDED, FAILED] }
                  requires_review: { type: boolean }
                  total_blocks: { type: integer }
                  pending_reviews: { type: integer, description: "Số block cần review còn PENDING" }
                  blocks:
                    type: array
                    items: { $ref: '#/components/schemas/OCRBlock' }
  ```
- **Lỗi có thể trả về**: `401 Unauthorized`, `403 Forbidden`, `404 NotFound`.

---

### 2.2. `PATCH /documents/{id}/versions/{vid}/ocr/blocks/{bid}`
- **Mục đích**: Duyệt (approve) hoặc chỉnh sửa (correct) một OCR block đơn lẻ.
- **Parameters**:
  - `id` (path, string), `vid` (path, string), `bid` (path, string).
- **Request Body**:
  ```yaml
  content:
    application/json:
      schema:
        type: object
        required: [review_status]
        properties:
          review_status:
            $ref: '#/components/schemas/OCRReviewStatus' # APPROVED hoặc CORRECTED
          text:
            type: string
            description: "Text đã sửa (bắt buộc khi review_status = CORRECTED)"
  ```
- **Xử lý nghiệp vụ (Business Logic)**:
  1. Cập nhật `review_status` sang `APPROVED` hoặc `CORRECTED`.
  2. Nếu `text` thay đổi hoặc `review_status == 'CORRECTED'`:
     - Lưu text cũ vào `original_text` (nếu chưa có).
     - Ghi nhận `text` mới.
     - Đánh dấu `is_edited = True`, `edited_by = current_user.id`, `edited_at = now()`.
  3. Ghi nhận `reviewed_by = current_user.id`, `reviewed_at = now()`.
  4. **Tự động re-evaluate cờ `DocumentVersion.requires_review`**: Đếm số block nghi ngờ (`requires_review=true`) còn `PENDING`. Nếu bằng `0`, cập nhật `DocumentVersion.requires_review = False`.
- **Response `200 OK`**: Trả về `OCRBlock` đã cập nhật nằm trong `SuccessEnvelope`.
- **Lỗi có thể trả về**: `400/422 ValidationError`, `401 Unauthorized`, `403 Forbidden`, `404 NotFound`.

---

### 2.3. `POST /documents/{id}/versions/{vid}/ocr/batch-review`
- **Mục đích**: Duyệt hàng loạt (batch review) nhiều OCR block hoặc toàn bộ các block đang chờ duyệt của một phiên bản.
- **Request Body**:
  ```yaml
  content:
    application/json:
      schema:
        type: object
        properties:
          accept_all_pending:
            type: boolean
            description: "Nếu true, tự động phê duyệt (APPROVED) tất cả các block nghi ngờ đang PENDING"
          actions:
            type: array
            items:
              type: object
              required: [block_id, review_status]
              properties:
                block_id: { type: string }
                review_status: { $ref: '#/components/schemas/OCRReviewStatus' }
                text: { type: string }
  ```
- **Xử lý nghiệp vụ**:
  1. Chạy trong một DB Transaction duy nhất.
  2. Cập nhật trạng thái duyệt cho danh sách các block được chỉ định hoặc toàn bộ các block `PENDING`.
  3. Kiểm tra lại toàn bộ phiên bản: Nếu không còn block nào có `requires_review = True` và `review_status = 'PENDING'`, tự động giải phóng cờ `DocumentVersion.requires_review = False`.
- **Response `200 OK`**:
  ```yaml
  content:
    application/json:
      schema:
        allOf:
          - $ref: '#/components/schemas/SuccessEnvelope'
          - type: object
            properties:
              data:
                type: object
                required: [reviewed_count, remaining_pending_count, version_requires_review]
                properties:
                  reviewed_count: { type: integer }
                  remaining_pending_count: { type: integer }
                  version_requires_review: { type: boolean }
  ```

---

## 3. Kiến Trúc Celery Async OCR Pipeline Integration

### 3.1. Trạng Thái Hiện Tại của Celery Task
Trong `apps/api/app/worker/tasks.py`:
- Task `process_document_task(job_id, version_id)` gọi `_async_process_document`.
- Hiện tại code chỉ giả lập tiến độ (`job.progress = 50 -> 100`) và cập nhật `version.ocr_status = "SUCCEEDED"`.
- Chưa khởi tạo model ORM `OCRBlock`, chưa chạy PaddleOCR, chưa lưu dữ liệu bbox/text/confidence vào DB.

### 3.2. Thiết Kế Tích Hợp Chi Tiết (Pipeline Flow)

```
[Upload PDF] 
     │
     ▼
[Celery Task: process_document_task]
     │
     ├─► 1. Tải PDF từ MinIO Storage (via StorageService)
     ├─► 2. Render trang PDF thành hình ảnh (300 DPI)
     ├─► 3. Chạy PaddleOCR (Text Detection + Text Recognition)
     │      (Fallback sang Tesseract nếu PaddleOCR ném lỗi runtime)
     ├─► 4. Với mỗi Text Block phát hiện được:
     │      ├─ Trích xuất bounding box: [x_min, y_min, x_max, y_max]
     │      ├─ Đánh giá confidence score (cô lập 0.0 .. 1.0)
     │      └─ So sánh với threshold (OCR_CONFIDENCE_THRESHOLD = 0.8):
     │          • Confidence < 0.8  => requires_review = True,  review_status = 'PENDING'
     │          • Confidence >= 0.8 => requires_review = False, review_status = 'APPROVED'
     ├─► 5. Persist danh sách OCRBlock vào DB (bảng ocr_blocks)
     ├─► 6. Tính toán cờ cấp phiên bản:
     │      • Nếu CÓ ÍT NHẤT 1 block có requires_review == True 
     │        => Set DocumentVersion.requires_review = True
     │      • Ngược lại => Set DocumentVersion.requires_review = False
     └─► 7. Cập nhật Job & Version:
            • Job.status = 'SUCCEEDED', Job.progress = 100
            • DocumentVersion.ocr_status = 'SUCCEEDED'
            • DocumentVersion.status = 'UNDER_REVIEW'
```

### 3.3. DB Model & Migration Yêu Cầu (`OCRBlock`)
Cần tạo ORM model `app/models/ocr_block.py` và Alembic migration `0004_ocr_blocks.py`:

```python
class OCRBlock(Base):
    __tablename__ = "ocr_blocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ocr_job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox: Mapped[list[float]] = mapped_column(JSON, nullable=False) # [x_min, y_min, x_max, y_max]
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="APPROVED") # PENDING, APPROVED, CORRECTED
    reviewed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    edited_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
```

---

## 4. Phân Tích Bất Biến Duyệt Phiên Bản (Approval Invariant Check)

### 4.1. Định Nghĩa Bất Biến Duyệt (Approval Invariants)
Theo tài liệu kiến trúc vòng đời tài liệu (`docs/domain/document-lifecycle.md`) và quy định dữ liệu (`docs/rules/04-database-rag-ocr.md`), một `DocumentVersion` **chỉ được phép phê duyệt (status = 'APPROVED') khi thỏa mãn đồng thời 3 bất biến**:

1. **Bất biến 1 (OCR Status)**: `version.ocr_status == 'SUCCEEDED'`.
2. **Bất biến 2 (Version Flag)**: `version.requires_review == False`.
3. **Bất biến 3 (Block Level Review Complete)**: Tất cả các OCR block có `confidence < 0.8` (hoặc `requires_review = True`) đều **phải có `review_status IN ('APPROVED', 'CORRECTED')`** (không được còn bất kỳ block nghi ngờ nào ở trạng thái `PENDING`).

### 4.2. Cơ Chế Kiểm Tra Bảo Vệ (Defensive Enforcement) trong Service

Trong `apps/api/app/modules/documents/service.py`, hàm `approve_document_version` cần thực hiện kiểm tra như sau:

```python
async def approve_document_version(
    session: AsyncSession,
    document: Document,
    version: DocumentVersion,
    request_id: str = "",
) -> DocumentVersion:
    # Check 1: OCR status phải SUCCEEDED
    if version.ocr_status != "SUCCEEDED":
        raise conflict(
            detail="Chỉ có thể phê duyệt phiên bản khi OCR thành công (ocr_status == 'SUCCEEDED').",
            request_id=request_id,
        )

    # Check 2: Đếm trực tiếp từ DB các block nghi ngờ còn PENDING (Defensive DB Check)
    pending_suspicious_stmt = select(func.count(OCRBlock.id)).where(
        OCRBlock.version_id == version.id,
        OCRBlock.requires_review == True,
        OCRBlock.review_status == "PENDING",
    )
    pending_suspicious_count = (await session.execute(pending_suspicious_stmt)).scalar_one()

    if pending_suspicious_count > 0:
        # Đồng bộ lại cờ requires_review nếu bị out-of-sync
        if not version.requires_review:
            version.requires_review = True
            await session.commit()

        raise conflict(
            detail=f"Phiên bản còn {pending_suspicious_count} block OCR nghi ngờ chưa được kiểm tra (requires_review=true). Vui lòng thực hiện OCR review trước khi phê duyệt.",
            request_id=request_id,
        )

    # Check 3: Cờ requires_review cấp phiên bản phải là False
    if version.requires_review:
        raise conflict(
            detail="Phiên bản yêu cầu kiểm tra OCR trước khi phê duyệt.",
            request_id=request_id,
        )

    # ... Thực hiện chuyển trạng thái phiên bản & tài liệu sang APPROVED ...
```

---

## 5. Hướng Dẫn Sửa Đổi Cho Implementer (Proposed Implementation Artifacts)

### 5.1. File `docs/api/openapi.yaml` (Cập nhật endpoints OCR Review)
Thêm các route dưới tag `ocr` hoặc `documents`:
- `GET /documents/{id}/versions/{vid}/ocr`
- `PATCH /documents/{id}/versions/{vid}/ocr/blocks/{bid}`
- `POST /documents/{id}/versions/{vid}/ocr/batch-review`

### 5.2. File `apps/api/app/models/ocr_block.py`
Tạo model `OCRBlock` như phân tích ở Mục 3.3 và đăng ký tại `app/models/__init__.py`.

### 5.3. File `apps/api/app/modules/documents/schemas.py`
Bổ sung các Pydantic schema:
- `OCRBlockResponse`
- `OCRVersionDetailResponse`
- `OCRBlockReviewPatchSchema`
- `OCRBatchReviewSchema`
- `OCRBatchReviewResponse`

### 5.4. File `apps/api/app/modules/documents/service.py`
Bổ sung các hàm service:
- `get_version_ocr_detail(session, version)`
- `review_single_ocr_block(session, version, block_id, review_status, text, user)`
- `batch_review_ocr_blocks(session, version, actions, accept_all_pending, user)`
- Cập nhật `approve_document_version` với DB invariant assertion.

### 5.5. File `apps/api/app/modules/documents/router.py`
Khai báo 3 endpoint tương ứng với các dependency kiểm tra quyền `require_staff_or_admin`.

---

## 6. Kết Luận & Đánh Giá Tương Thích (Verification Summary)

- **Tính khả thi**: Kiến trúc thiết kế hoàn toàn tương thích với Phase 1 & Phase 1.1 đã triển khai, sử dụng đúng pattern Async SQLAlchemy, Pydantic v2 schemas, RFC 7807 problem details, và Celery task architecture.
- **Rủi ro & Lưu ý**:
  1. Khi thực hiện `batch-review` hoặc `PATCH block`, cần đảm bảo tính toán chính xác số block nghi ngờ còn lại để tự động gỡ cờ `DocumentVersion.requires_review` sang `False`.
  2. Bounding box `bbox` cần giữ chuẩn 4 phần tử `[x_min, y_min, x_max, y_max]` phù hợp với giao diện Frontend vẽ lớp vẽ đè (canvas overlay).

