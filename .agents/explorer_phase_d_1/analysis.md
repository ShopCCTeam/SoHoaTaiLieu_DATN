# Báo cáo Phân tích Kiến trúc Phase D: Embedding Engine & Text Chunking

## 1. Tổng quan & Mục tiêu

Phase D chịu trách nhiệm xây dựng 2 thành phần cốt lõi của RAG Pipeline trong Hệ thống Số hoá & Quản lý Tài liệu CTSV:
1. **Embedding Engine (`EmbeddingService`)**: Sinh vector embedding 1024 chiều từ mô hình BGE-M3 (BAAI/bge-m3) phục vụ pgvector indexing. Sử dụng thiết kế Strategy pattern để hỗ trợ primary adapter (SentenceTransformers / HuggingFace) và mock fallback (dùng cho dev/pytest không cần tải model ML).
2. **Text Chunking Strategy (`TextChunkerService`)**: Phân đoạn văn bản dựa trên dữ liệu cấu trúc OCR (`OCRPage`, `OCRBlock`) thu được từ Phase C. Thực hiện recursive text splitting nhưng bảo toàn metadata từng chunk bao gồm `chunk_index`, `page_number`, `block_ids`, `bbox` `[x0, y0, x1, y1]`, và nội dung `text`.
3. **Cấu hình Chunking**: Thiết lập các tham số `chunk_size` (500 - 1000 ký tự/tokens) và `chunk_overlap` (50 - 100 ký tự/tokens) linh hoạt qua Pydantic Settings.

---

## 2. Khảo sát Codebase & Điểm tích hợp

### 2.1 Hiệu trạng Phase C OCR Pipeline
Trong `apps/api/app/`:
- Model ORM: `OCRPage` (`models/ocr_page.py`) và `OCRBlock` (`models/ocr_block.py`).
  - `OCRBlock` chứa các trường: `page_number` (int, 1-indexed), `block_index` (int, 0-indexed), `text_content` (str), `confidence` (float), `bbox` (`[x0, y0, x1, y1]` JSONB), `requires_review` (bool), `review_status` (StrEnum).
- OCR Service: `OcrEngineService` (`services/ocr_engine.py`) trả về danh sách dataclass `OcrPageResult` chứa `OcrBlockResult`.
- Cấu hình hệ thống: `Settings` (`core/config.py`) dùng Pydantic Settings (12-factor).

### 2.2 Luồng dữ liệu giữa Phase C và Phase D
```
[PDF Document] -> [Phase C: OcrEngineService] -> [OCRPage / OCRBlock]
                                                        |
                                                        v
                                       [Phase D: TextChunkerService]
                                                        |
                                          (Splitting + Metadata Bounding Box)
                                                        v
                                          [List of DocumentChunk DTOs]
                                                        |
                                                        v
                                       [Phase D: EmbeddingService]
                                                        |
                                          (BGE-M3 1024-dim Vector Generation)
                                                        v
                                        [Vector Storage / pgvector Table]
```

---

## 3. Thiết kế Embedding Engine (`EmbeddingService`)

### 3.1 Chọn Lựa Mô Hình
Mô hình chọn lựa: **BGE-M3** (`BAAI/bge-m3`).
- Đa ngôn ngữ (Multilingual): Tối ưu hoá đặc biệt cho tiếng Việt và các văn bản hành chính HUST/CTSV.
- Vector dimension: 1024 chiều (dense vector).
- Chuẩn hoá vector: L2 Normalization được bật mặc định để khoảng cách Cosine và Inner Product trên pgvector tương đương nhau.

### 3.2 Strategy Pattern Design
Thiết kế bao gồm 1 interface trừu tượng `EmbeddingStrategy` và 2 adapter triển khai:

1. **`EmbeddingStrategy` (Abstract Base Class)**:
   - `embed_text(text: str) -> list[float]`: Sinh vector 1024 chiều cho 1 đoạn văn bản.
   - `embed_batch(texts: list[str]) -> list[list[float]]`: Sinh vector theo lô (batch processing).
   - `@property dimension -> int`: Trả về 1024.

2. **`SentenceTransformersEmbeddingStrategy` (Primary Adapter)**:
   - Sử dụng thư viện `sentence-transformers` với model name `BAAI/bge-m3`.
   - Tự động phát hiện GPU/CPU (`cuda` / `cpu`).
   - Thực hiện L2 Normalization (`normalize_embeddings=True`).
   - Xử lý batch size tối ưu (mặc định 32).

3. **`MockEmbeddingStrategy` (Dev / Pytest Fallback Adapter)**:
   - Không yêu cầu cài đặt PyTorch hoặc tải weights 2.2GB của BGE-M3.
   - Sinh vector 1024 chiều một cách deterministic dựa trên hash MD5/SHA256 của chuỗi đầu vào (hoặc seed ngẫu nhiên).
   - Đảm bảo vector được L2-normalize.
   - Cho phép các unit test và CI pipeline chạy tức thì (< 10ms) mà không tốn bộ nhớ RAM/GPU.

4. **`EmbeddingService` (Service Orchestrator)**:
   - Nhận `primary_strategy` và `fallback_strategy` qua Dependency Injection.
   - Fallback tự động: Nếu `SentenceTransformersEmbeddingStrategy` gặp lỗi thiếu thư viện hoặc hết VRAM/RAM, tự động chuyển sang `MockEmbeddingStrategy` kèm theo structlog warning log.

### 3.3 Thiết kế Class Sketch cho `EmbeddingService`
```python
from abc import ABC, abstractmethod
import hashlib
import numpy as np
from structlog import get_logger

logger = get_logger(__name__)

BGE_M3_DIMENSION = 1024


class EmbeddingStrategy(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        pass


class SentenceTransformersEmbeddingStrategy(EmbeddingStrategy):
    def __init__(self, model_name: str = "BAAI/bge-m3", device: str | None = None) -> None:
        self.model_name = model_name
        self.device = device
        self._model = None

    def _load_model(self) -> None:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device=self.device)
            except Exception as exc:
                raise RuntimeError(f"Failed to load SentenceTransformer model '{self.model_name}': {exc}") from exc

    @property
    def dimension(self) -> int:
        return BGE_M3_DIMENSION

    def embed_text(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._load_model()
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings.tolist()


class MockEmbeddingStrategy(EmbeddingStrategy):
    def __init__(self, dimension: int = BGE_M3_DIMENSION) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _generate_vector(self, text: str) -> list[float]:
        # Deterministic generation using text hash seed
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self._dimension)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_text(self, text: str) -> list[float]:
        return self._generate_vector(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]


class EmbeddingService:
    def __init__(
        self,
        primary_strategy: EmbeddingStrategy | None = None,
        fallback_strategy: EmbeddingStrategy | None = None,
    ) -> None:
        self.primary_strategy = primary_strategy or SentenceTransformersEmbeddingStrategy()
        self.fallback_strategy = fallback_strategy or MockEmbeddingStrategy()

    def embed_text(self, text: str) -> list[float]:
        try:
            return self.primary_strategy.embed_text(text)
        except Exception as exc:
            logger.warning("primary_embedding_failed_using_fallback", error=str(exc))
            return self.fallback_strategy.embed_text(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            return self.primary_strategy.embed_batch(texts)
        except Exception as exc:
            logger.warning("primary_batch_embedding_failed_using_fallback", error=str(exc))
            return self.fallback_strategy.embed_batch(texts)
```

---

## 4. Thiết kế Text Chunking Strategy (`TextChunkerService`)

### 4.1 Thách thức & Nguyên lý Bảo toàn Metadata
Văn bản từ OCR không phải là một chuỗi thô (raw string) duy nhất mà gồm các `OCRBlock` gắn liền với `page_number` và toạ độ khung bao `bbox` `[x0, y0, x1, y1]`.
Nếu chỉ ghép toàn bộ văn bản rồi chia theo ký tự thô, hệ thống sẽ **mất dấu toạ độ bbox** và **số trang**, dẫn đến việc không thể hiển thị Citation Bounding Box highlight trên giao diện UI (F3 / F5 frontend citation preview).

### 4.2 Cấu trúc DTO `DocumentChunk`
```python
from dataclasses import dataclass, field

@dataclass
class DocumentChunk:
    chunk_index: int              # Thứ tự chunk trong phiên bản tài liệu (0, 1, 2...)
    page_number: int              # Số trang chủ đạo (1-indexed)
    page_numbers: list[int]       # Danh sách các trang nếu chunk trải dài qua trang
    block_ids: list[str]          # Danh sách ID các OCRBlock cấu thành chunk này
    bbox: list[float]             # [x0, y0, x1, y1] Bounding box hợp nhất trên trang chủ đạo
    text: str                     # Nội dung văn bản của chunk
    char_count: int               # Số ký tự
    token_count: int              # Số token ước tính
```

### 4.3 Thuật Toán Recursive Splitting Bảo Toàn Metadata

1. **Giai đoạn 1 — Gom cụm nguồn (Source Assembly)**:
   - Đọc danh sách `OCRBlock` được sắp xếp theo thứ tự `(page_number.asc(), block_index.asc())`.
   - Lưu trữ từng đơn vị khối nhỏ nhất: `BlockUnit(text, page_number, block_id, bbox)`.

2. **Giai đoạn 2 — Phân tách & Gom nhóm Đệ quy (Recursive Grouping & Splitting)**:
   - Thứ tự ưu tiên ký tự phân tách (Separators):
     1. Double newline `\n\n` (ngắt đoạn/mục).
     2. Single newline `\n` (ngắt dòng).
     3. Sentence boundary `. `, `? `, `! ` (ngắt câu).
     4. Clause boundary `; `, `, ` (ngắt mệnh đề).
     5. Word boundary ` ` (ngắt từ).
   - Tích tụ các `BlockUnit` liên tiếp cho đến khi tổng kích thước ký tự/token đạt ngưỡng `chunk_size`.
   - Nếu 1 `OCRBlock` đơn lẻ có độ dài vượt quá `chunk_size`, thực hiện chia nhỏ văn bản trong block đó theo ký tự phân tách và nhân bản metadata `bbox` + `page_number` của block đó cho các sub-chunk.

3. **Giai đoạn 3 — Tính toán Bounding Box Hợp nhất (Composite BBox Fusion)**:
   - Khi hợp nhất các `BlockUnit` $B_1, B_2, \dots, B_k$ thuộc cùng một trang thành 1 `DocumentChunk`, toạ độ `bbox` hợp nhất được tính theo công thức Min-Max Envelope:
     $$x_0 = \min_{i=1..k} (x_{0, i}), \quad y_0 = \min_{i=1..k} (y_{0, i})$$
     $$x_1 = \max_{i=1..k} (x_{1, i}), \quad y_1 = \max_{i=1..k} (y_{1, i})$$
   - Nếu chunk chứa các block thuộc nhiều trang khác nhau, `page_number` lấy trang bắt đầu (hoặc trang chiếm đa số ký tự), và `bbox` được hợp nhất từ các block thuộc `page_number` chủ đạo đó.

4. **Giai đoạn 4 — Tạo Overlap (Chunk Overlap Generation)**:
   - Duy trì cửa sổ trượt (sliding window) chứa `chunk_overlap` ký tự từ các `BlockUnit` cuối của chunk trước đó sang chunk tiếp theo.
   - Giữ nguyên liên kết `block_ids` và recalculate `bbox` cho phần overlap.

---

## 5. Cấu hình Chunking & Parameter Tuning

### 5.1 Tham số Cấu hình Đề xuất (`app/core/config.py`)
```python
# Embedding & Chunking Configurations
embedding_model_name: str = "BAAI/bge-m3"
embedding_dimension: int = 1024
embedding_strategy: Literal["sentence_transformers", "mock"] = "mock"
embedding_batch_size: int = 32

chunk_size: int = 800          # Kích thước đề xuất: 800 ký tự (~150-200 tokens)
chunk_overlap: int = 100       # Gối đầu đề xuất: 100 ký tự (~20-25 tokens)
chunk_min_size: int = 50       # Loại bỏ các chunk nhiễu quá ngắn (< 50 ký tự)
```

### 5.2 Bảng So Sánh Chiến Lược Kích Thước Chunk

| Tiêu chí | Chunk Nhỏ (200-400 chars) | Chunk Vừa (500-1000 chars) [Đề xuất] | Chunk Lớn (1200-2000 chars) |
|---|---|---|---|
| Độ chính xác Vector Search | Cao (Rất tập trung) | Rất cao (Cân bằng ngữ cảnh) | Trung bình (Bị loãng vector) |
| Bảo toàn Ngữ cảnh RAG | Thấp (Dễ mất ý câu) | Tốt (Vừa đủ 1-2 đoạn văn) | Rất tốt (Nhiều đoạn văn) |
| Toạ độ Citation BBox | Chính xác từng dòng | Chính xác từng đoạn văn | Khung bao bị phủ quá rộng |
| Chi phí Lưu trữ Vector | Số lượng chunk lớn | Vừa phải | Số lượng chunk ít |

---

## 6. Đề xuất Chi tiết Sửa đổi Codebase (Proposed Patch Structure)

### 6.1 Cập nhật `apps/api/app/core/config.py`
Thêm các biến cấu hình Pydantic Settings cho Embedding Engine và Text Chunker.

### 6.2 Tạo mới `apps/api/app/schemas/chunk.py`
Định nghĩa Pydantic DTOs cho `ChunkCreate`, `ChunkPublic`, `DocumentChunk`.

### 6.3 Tạo mới `apps/api/app/services/embedding_service.py`
Chứa `EmbeddingStrategy`, `SentenceTransformersEmbeddingStrategy`, `MockEmbeddingStrategy`, `EmbeddingService`.

### 6.4 Tạo mới `apps/api/app/services/chunking_service.py`
Chứa `TextChunkerService` và logic recursive text splitting tích hợp bbox fusion.

---

## 7. Phương pháp Kiểm thử & Xác minh (Verification Plan)

1. **Unit Test `EmbeddingService`**:
   - Kiểm tra `MockEmbeddingStrategy`: Sinh vector 1024 chiều, kiểm tra L2 norm == 1.0.
   - Kiểm tra tính deterministic: Chuỗi đầu vào giống nhau trả về vector giống nhau.
   - Kiểm tra batch embedding: Danh sách N chuỗi trả về N vector 1024 chiều.
   - Kiểm tra fallback graceful khi `SentenceTransformersEmbeddingStrategy` quăng exception.

2. **Unit Test `TextChunkerService`**:
   - Phân đoạn văn bản mẫu từ OCR blocks.
   - Verification 1: Tất cả chunk thu được đều giữ đúng `page_number` và `bbox` hợp lệ `[x0, y0, x1, y1]`.
   - Verification 2: Kích thước các chunk <= `chunk_size` (trừ trường hợp 1 từ/khối đơn vượt kích thước).
   - Verification 3: Tính gối đầu `chunk_overlap` xuất hiện chính xác ở ranh giới giữa chunk $i$ và $i+1$.
   - Verification 4: Hợp nhất toạ độ bbox ($x_0 = \min, y_0 = \min, x_1 = \max, y_1 = \max$) chính xác với toạ độ các block cấu thành.

3. **Static Check**:
   - `uv run ruff check app tests` (0 errors).
   - `uv run mypy app` (0 errors).
