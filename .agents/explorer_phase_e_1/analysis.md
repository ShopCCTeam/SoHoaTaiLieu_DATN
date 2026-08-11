# Phân Tích Kiến Trúc & Kiểm Tra Codebase Phase E (RAG Chatbot with Citations)

> **Báo cáo của Explorer 1** | Ngày: 2026-08-11
> **Thư mục làm việc**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_e_1`

---

## 1. Kết Quả Kiểm Tra Sức Khỏe Codebase Backend (`apps/api`)

Đã thực hiện 4 lệnh kiểm tra chất lượng trên backend `apps/api` để xác minh hoàn thành Phase D remediation:

| Lệnh Kiểm Tra | Kết Quả | Trạng Thái | Chi Tiết |
|---|---|---|---|
| `uv run pytest` | **209 passed, 1 skipped** (103.57s) | PASS | Tất cả 210 test case trong `tests/` đều vượt qua thành công, 0 lỗi. |
| `uv run ruff check .` | **All checks passed!** | PASS | Không có cảnh báo hay lỗi linter nào. |
| `uv run ruff format --check .` | **81 files already formatted** | PASS | 100% codebase tuân thủ chuẩn định dạng ruff. |
| `uv run mypy app` | **Success: no issues found in 51 source files** | PASS | Static type checking đạt 0 lỗi trên 51 file nguồn Python. |

**Kết luận Phase D Remediation**: Tất cả các lỗi linter/test/type-check trước đó đã được giải quyết triệt me. Backend `apps/api` hoàn toàn sạch sẽ và sẵn sàng 100% cho Phase E.

---

## 2. Phân Tích Hạ Tầng Search, Chunking & Citation Hiện Có

### 2.1. Cấu trúc CSDL & Data Model
- **`DocumentChunk`** (`app/models/document_chunk.py`):
  - Khóa chính `id` (UUID v4).
  - Thuộc tính liên quan: `document_id`, `version_id`, `chunk_index` (0-indexed), `page_number` (1-indexed), `text` (nội dung text), `token_count`, `block_ids` (JSON list).
  - Bounding box envelope: `bbox` dạng `[x0, y0, x1, y1]`.
  - Vector embedding: `embedding` (Vector 1024-dim từ BGE-M3).
  - Full-text search tsvector: `fulltext_tsv` (PostgreSQL `TSVECTOR`).
- **`Document`** (`app/models/document.py`):
  - Thuộc tính scope: `scope` (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`).
  - Phân quyền RBAC scope lọc qua `get_allowed_scopes_for_user(user)`.
  - Xóa mềm: `deleted_at IS NULL` (bảo đảm tài liệu xóa mềm không bao giờ xuất hiện trong search/chat).

### 2.2. Services Hiện Có
- **`ChunkingService`** (`app/services/chunking.py`):
  - Tách đoạn văn bản từ `OCRBlock`/`OCRPage` bằng thuật toán đệ quy.
  - Tính toánBounding Box Envelope chính xác `[x0, y0, x1, y1]`.
  - Giữ lại thông tin `page_number`, `block_ids`, `token_count`.
- **`EmbeddingService`** (`app/services/embedding.py`):
  - Áp dụng Strategy Pattern: `EmbeddingStrategy` (ABC), `MockEmbeddingStrategy` (SHA-256 deterministic 1024-dim vector cho dev/test), `BGEM3EmbeddingStrategy` (API endpoint BGE-M3 1024-dim với fallback tự động).
- **`SearchService`** (`app/modules/search/service.py`):
  - Đã triển khai thuật toán **RRF (Reciprocal Rank Fusion) Hybrid Search** kết hợp Vector Cosine Distance và PostgreSQL Full-text search (`plainto_tsquery`).
  - Lọc RBAC scope nghiêm ngặt theo vai trò người dùng (`allowed_scopes`).

### 2.3. Quy Chuẩn Trích Dẫn Citations (`docs/domain/citation-spec.md`)
- Schema chuẩn:
  ```json
  {
    "document_id": "string (UUID)",
    "document_version_id": "string (UUID)",
    "title": "string (Title hiện tại của văn bản tại thời điểm query)",
    "page_number": 1,
    "chunk_id": "string (UUID)",
    "quote": "string (Tối đa 300 ký tự, cắt tại word boundary + '...')",
    "score": 0.95,
    "bbox": [10.0, 20.0, 100.0, 200.0]
  }
  ```
- **Quy tắc bắt buộc**:
  1. Trích dẫn phải lấy tiêu đề live `title` từ CSDL tại thời điểm truy vấn.
  2. Lọc quyền đọc `allowed_scopes` ngay trong truy vấn retrieval DB.
  3. Đoạn trích `quote` bị giới hạn 300 ký tự và không cắt giữa từ.
  4. Nếu `has_sufficient_evidence = false`, trả `citations: []` (không sinh citation giả hoặc score = 0).

---

## 3. Quy Hoạch Kiến Trúc Phase E (RAG Chatbot)

### 3.1. Cấu Trúc Module Chat (`apps/api/app/modules/chat/`)
Cần khởi tạo thư mục mới `apps/api/app/modules/chat/` chứa các file:
```
apps/api/app/modules/chat/
├── __init__.py
├── router.py         # Endpoint POST /api/v1/chat/query
├── schemas.py        # Pydantic schemas (ChatQueryRequest, Citation, ChatData, ChatResponse)
└── service.py        # Chat RAG Pipeline (LCEL Chain / Context synthesis / Citation building)
```

### 3.2. Chi Tiết Các Thành Phần Sẽ Triển Khai

#### A. Config Settings (`apps/api/app/core/config.py`)
Bổ sung các tham số cấu hình LLM theo ADR-012:
```python
# ---- LLM & Chat RAG ----
llm_provider: Literal["ollama", "mock"] = "mock"
llm_base_url: str = "http://localhost:11434/v1"
llm_model_name: str = "qwen2.5:7b-instruct"
llm_temperature: float = 0.2
llm_max_tokens: int = 1024
```

#### B. Service LLM Adapter (`apps/api/app/services/llm.py`)
Tạo service adapter tuân thủ Strategy Pattern:
- `LLMStrategy` (ABC): Định nghĩa interface `generate_answer(prompt: str, context: str) -> str`.
- `MockLLMStrategy`: Sinh câu trả lời giả lập dựa trên context nhằm phục vụ `pytest` và môi trường không có Ollama.
- `OllamaLLMStrategy`: Gọi Ollama server qua LangChain `ChatOpenAI` hoặc `httpx` Async Client (với fallback sang Mock nếu Ollama offline).
- `LLMService`: Context wrapper cho router và chat service.

#### C. Schemas (`apps/api/app/modules/chat/schemas.py`)
```python
from pydantic import BaseModel, Field
from typing import Literal

class ChatQueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000, description="Câu hỏi RAG")
    scope: str | None = Field(None, description="Tùy chọn lọc phạm vi tài liệu")
    top_k: int = Field(5, ge=1, le=20, description="Số lượng chunk ngữ cảnh tối đa")

class CitationItem(BaseModel):
    document_id: str
    document_version_id: str
    title: str
    page_number: int
    chunk_id: str
    quote: str
    score: float
    bbox: list[float] | None = None

class ChatData(BaseModel):
    answer: str
    citations: list[CitationItem]
    has_sufficient_evidence: bool

class ChatResponse(BaseModel):
    success: Literal[True] = True
    data: ChatData
```

#### D. Pipeline & Service Logic (`apps/api/app/modules/chat/service.py`)
Quy trình 6 bước trong `process_chat_query`:
1. **Lấy danh sách scope người dùng được phép**: `allowed_scopes = get_allowed_scopes_for_user(current_user)`.
2. **Hybrid Search Retrieval**: Gọi `search_documents(...)` từ `search.service` để lấy top `top_k` chunks (ví dụ top 5).
3. **Đánh giá Bằng Chứng (Evidence Verification)**:
   - Nếu danh sách chunk rỗng hoặc điểm số cao nhất `top_score < 0.30`:
   - Trả về: `has_sufficient_evidence = False`, `answer = "Tôi không tìm thấy thông tin phù hợp trong các văn bản quy định hiện hành."`, `citations = []`.
4. **Xây Dựng Context & Prompt**: Ghép nội dung các chunks kèm chỉ số trang, tiêu đề văn bản vào System Prompt (Tiếng Việt).
5. **Gọi LLM Generation**: Gửi Prompt sang `LLMService`.
6. **Xây Dựng Citations & Format Quote**: Duyệt qua từng chunk được dùng, cắt quote <= 300 ký tự (theo boundary từ), lấy live `title` của tài liệu và trả về `ChatData`.

#### E. Router (`apps/api/app/modules/chat/router.py`)
- Endpoint: `POST /api/v1/chat/query`
- Dependency: `current_user: User = Depends(get_current_user)`, `session: AsyncSession = Depends(get_session)`.
- Đăng ký router trong `apps/api/app/main.py`: `app.include_router(chat_router, prefix=settings.api_prefix)`.

#### F. OpenAPI Contract Spec (`docs/api/openapi.yaml`)
1. Thêm `ChatQueryRequest` vào `components/schemas`.
2. Khai báo path `/chat/query` trong `paths`:
   ```yaml
   /chat/query:
     post:
       tags: [chat]
       summary: Hỏi đáp RAG với tài liệu (có trích dẫn)
       security:
         - BearerAuth: []
       requestBody:
         required: true
         content:
           application/json:
             schema:
               $ref: '#/components/schemas/ChatQueryRequest'
       responses:
         '200':
           description: OK — Trả về câu trả lời RAG + trích dẫn
           content:
             application/json:
               schema:
                 $ref: '#/components/schemas/ChatResponse'
         '401': { $ref: '#/components/responses/Unauthorized' }
         '403': { $ref: '#/components/responses/Forbidden' }
         '422': { $ref: '#/components/responses/ValidationError' }
   ```

---

## 4. Kế Hoạch Kiểm Thử Cho Implementer
1. **Unit Test (`tests/test_chat_router.py` & `tests/test_llm_service.py`)**:
   - Test `ChatQueryRequest` validation (trống, quá dài).
   - Test RAG chat thành công có citations với `MockLLMStrategy`.
   - Test RAG chat khi không đủ evidence (`has_sufficient_evidence = False`).
   - Test phân quyền RBAC scope (sinh viên không thấy tài liệu `INTERNAL`).
2. **Lệnh Verification**:
   - `uv run pytest tests/test_chat_router.py`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run mypy app`
   - `pnpm --filter @ctsv/contracts generate` (Sync types sang Frontend).
