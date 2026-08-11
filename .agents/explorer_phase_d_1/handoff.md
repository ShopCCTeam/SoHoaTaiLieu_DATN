# Báo cáo Handoff Phase D: Embedding Engine & Text Chunking Analysis

## 1. Observation (Quan sát)

1. **OCR Block & Page Models (`apps/api/app/models/ocr_block.py`, `ocr_page.py`)**:
   - `OCRBlock` (dòng 35-161):
     - `page_number`: Integer, 1-indexed (dòng 67-72).
     - `block_index`: Integer, 0-indexed (dòng 73-77).
     - `text_content`: Text (dòng 78-82).
     - `bbox`: JSON (`[x0, y0, x1, y1]`, dòng 88-92).
     - `confidence`: Float (dòng 83-87).
     - `version_id`: String(36) ForeignKey `document_versions.id` (dòng 53-59).
   - `OCRPage` (dòng 22-97):
     - `page_number`: Integer, 1-indexed (dòng 40-44).
     - `version_id`: String(36) ForeignKey `document_versions.id` (dòng 33-39).
     - `blocks`: Relationship tới `OCRBlock` order theo `block_index.asc()` (dòng 91-96).

2. **OCR Engine Service Pattern (`apps/api/app/services/ocr_engine.py`)**:
   - Strategy Pattern đã áp dụng thành công ở Phase C với `OcrEngineStrategy` (ABC, dòng 45-52), `PaddleOcrStrategy` (dòng 54-97), `TesseractOcrStrategy` (dòng 99-139), `FallbackMockOcrStrategy` (dòng 141-202), và orchestrator `OcrEngineService` (dòng 204-257).

3. **System Settings (`apps/api/app/core/config.py`)**:
   - Dùng `pydantic_settings.BaseSettings` (dòng 19-161).
   - Đã có cấu hình OCR: `ocr_default_confidence_threshold: float = 0.9`, `ocr_default_engine = "paddleocr"` (dòng 76-78). Chưa có biến cấu hình Embedding Engine & Chunking.

4. **API Spec Contract (`docs/api/openapi.yaml`)**:
   - `Citation` schema (dòng 277-296): bao gồm `document_id`, `document_version_id`, `title`, `page_number`, `chunk_id`, `quote`, `score`, và `bbox` (`[x_min, y_min, x_max, y_max]`). Điều này khẳng định mỗi chunk và citation bắt buộc phải giữ lại `bbox` và `page_number`.

5. **Dependencies (`apps/api/pyproject.toml`)**:
   - Dependencies hiện tại chưa bao gồm `sentence-transformers` hoặc `numpy` làm dependency chính (dòng 9-35). `dev` dependencies bao gồm `pytest`, `ruff`, `mypy` (dòng 37-49).

---

## 2. Logic Chain (Chuỗi Luận Lý)

1. Từ **Observation 1 & 4**: Các đơn vị văn bản OCR thu được có toạ độ bounding box `[x0, y0, x1, y1]` theo từng block trên từng trang. API Spec yêu cầu Citation phải trả về `bbox` 4 phần tử và `page_number`.
   -> Do đó, quá trình Text Chunking không thể chỉ gộp văn bản thành chuỗi thô rồi cắt ngẫu nhiên, mà phải nhóm các `OCRBlock` theo thứ tự đệ quy (Recursive Text Splitting) và tính toán bounding box hợp nhất Min-Max Envelope ($x_0 = \min x_0, y_0 = \min y_0, x_1 = \max x_1, y_1 = \max y_1$) cho từng `DocumentChunk`.

2. Từ **Observation 2**: `OcrEngineService` triển khai Strategy Pattern rất hiệu quả với primary (PaddleOCR), fallback (Tesseract) và dev/pytest mock (FallbackMockOcrStrategy).
   -> Áp dụng mô hình Strategy tương tự cho `EmbeddingService`: Interface `EmbeddingStrategy` + `SentenceTransformersEmbeddingStrategy` (Primary model `BAAI/bge-m3` 1024 chiều) + `MockEmbeddingStrategy` (sinh vector 1024-dim deterministic hash cho pytest/dev).

3. Từ **Observation 3**: Pydantic Settings quản lý 12-factor config tập trung.
   -> Cần bổ sung các cấu hình `EMBEDDING_MODEL_NAME`, `EMBEDDING_DIMENSION`, `EMBEDDING_STRATEGY`, `CHUNK_SIZE`, `CHUNK_OVERLAP` vào `Settings` trong `app/core/config.py`.

4. Từ **Observation 5**: Môi trường dev/pytest cần chạy nhanh mà không phụ thuộc vào GPU hay việc tải model weights BGE-M3 (2.2GB).
   -> `MockEmbeddingStrategy` sử dụng SHA-256 seed sinh L2-normalized numpy array 1024 chiều cho phép toàn bộ pytest suite pass trong < 100ms mà không tốn tài nguyên.

---

## 3. Caveats (Cảnh báo & Giới hạn)

1. **Khối OCR đơn quá lớn**: Nếu 1 `OCRBlock` đơn lẻ chứa đoạn văn bản dài vượt quá `chunk_size` (vd: > 800 ký tự), thuật toán splitting cần chia nhỏ văn bản trong block đó và giữ nguyên `bbox` + `page_number` của block đó cho các sub-chunk.
2. **Chunk trải dài nhiều trang**: Với văn bản liên tục qua ranh giới trang, `DocumentChunk` đề xuất lưu `page_number` của trang bắt đầu (hoặc trang chiếm đa số ký tự) và danh sách `page_numbers` để hiển thị Citation chính xác.
3. **Thư viện NATIVE ML**: Trong môi trường CODE_ONLY hoặc CI không có PyTorch/sentence-transformers, `EmbeddingService` sẽ tự động chuyển sang `MockEmbeddingStrategy`.

---

## 4. Conclusion (Kết luận)

1. Thiết kế `EmbeddingService` theo Strategy Pattern với BGE-M3 1024-dimension:
   - Primary strategy: `SentenceTransformersEmbeddingStrategy` (`BAAI/bge-m3`, L2-normalized embeddings).
   - Dev/Test fallback: `MockEmbeddingStrategy` (Deterministic hash-based 1024-dim vectors).
   - Orchestrator: `EmbeddingService` với tự động fallback và log cảnh báo qua structlog.

2. Thiết kế `TextChunkerService` bảo toàn metadata:
   - Input: Danh sách `OCRBlock` / `OcrBlockResult` xếp theo trang & index.
   - Mechanism: Recursive character splitting theo thứ tự ưu tiên `\n\n` -> `\n` -> `. ` -> `; ` -> ` `.
   - BBox Fusion: Tính envelope bounding box $x_0 = \min x_0, y_0 = \min y_0, x_1 = \max x_1, y_1 = \max y_1$ cho mọi block nằm trong chunk.
   - Output: `DocumentChunk` mang đầy đủ `chunk_index`, `page_number`, `page_numbers`, `block_ids`, `bbox`, `text`, `char_count`, `token_count`.

3. Cấu hình mặc định:
   - `CHUNK_SIZE`: 800 ký tự (~150-200 tokens tiếng Việt).
   - `CHUNK_OVERLAP`: 100 ký tự (~20-25 tokens tiếng Việt).
   - Nằm trong `app/core/config.py`.

---

## 5. Verification Method (Phương pháp Kiểm chứng)

Sau khi Implementer triển khai code trong Phase D:
1. Run static checks:
   - `cd apps/api && uv run ruff check app tests`
   - `cd apps/api && uv run mypy app`
2. Run unit tests cho Embedding & Chunking:
   - `cd apps/api && uv run pytest tests/test_embedding_service.py`
   - `cd apps/api && uv run pytest tests/test_chunking_service.py`
3. Invalidation conditions:
   - Trả về vector khác 1024 chiều.
   - Vector không được L2 normalize (`norm != 1.0`).
   - Text chunk mất thuộc tính `bbox` hoặc `page_number`.
   - Dynamic chunk size vượt ngưỡng `chunk_size` mà không có lý do khối OCR đơn lẻ quá lớn.
