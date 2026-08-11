# Báo Cáo Phân Tích Search API, RBAC Filtering & Celery Indexing Task (Phase D)

**Dự án**: Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên  
**Thư mục làm việc**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_d_3_gen2`  
**Tác giả**: Explorer 3 Phase D (Replacement)  
**Thời gian**: 2026-08-11  

---

## 1. Tổng Quan & Mục Tiêu Phân Tích

Báo cáo này hoàn thiện bức tranh kiến trúc Phase D (RAG Pipeline & Retrieval System) cho Backend FastAPI (`apps/api/`). Trong khi Explorer 1 đã phân tích Embedding Engine (`EmbeddingService`) & Text Chunking Strategy (`TextChunkerService`), và Explorer 2 đã phân tích DB Vector Storage (`DocumentChunk` model, Alembic Migration `0005` pgvector/HNSW/GIN & `search_hybrid` RRF CTE), báo cáo của Explorer 3 tập trung phân tích 4 thành phần tích hợp & giao tiếp cuối cùng:

1. **Search REST API Endpoints**: Thiết kế endpoint `POST /search` (và `GET /search`) tiếp nhận tham số `query`, `top_k`, `document_ids`, và `scope` filtering (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`).
2. **OpenAPI Spec Gap Analysis & Patch**: Rà soát `docs/api/openapi.yaml`, bổ sung định nghĩa path `/search` bị thiếu và các schemas `SearchQuery`, `SearchResultItem`, `SearchResponse`.
3. **Celery Indexing Task (`index_document_chunks_task`)**: Tự động kích hoạt sau khi tác vụ OCR hoàn thành thành công (`DocumentVersion.ocr_status == 'SUCCEEDED'`), chuyển đổi `OCRBlock` thành `DocumentChunk`, sinh embedding vector và lưu vào PostgreSQL/pgvector.
4. **RBAC Scope Enforcement**: Kiểm soát phân quyền tìm kiếm nghiêm ngặt theo vai trò người dùng (`student` chỉ tìm trong scope `PUBLIC` & `STUDENT_AFFAIRS`, `staff`/`admin` tìm thêm `INTERNAL`), lọc triệt để từ tầng SQL CTE query.

---

## 2. Thiết Kế Search REST API Endpoints (`apps/api/app/modules/search/`)

### 2.1. Lựa Chọn Phương Thức HTTP (`POST /search` vs `GET /search`)

Hệ thống hỗ trợ cả hai phương thức để tối ưu cho các Use Case khác nhau:

- **`POST /search` (Primary Endpoint)**: Phù hợp cho RAG Retrieval vì payload chứa cấu trúc phức tạp (`query`, `top_k`, `document_ids` list, `scope` array). Tránh giới hạn độ dài URL và các vấn đề URL encoding ký tự tiếng Việt hoặc câu hỏi dài từ giao diện UI.
- **`GET /search` (Convenience Endpoint)**: Dành cho truy vấn nhanh từ URL Query String (ví dụ `GET /api/v1/search?q=nghi+hoc&top_k=10`), ánh xạ trực tiếp sang logic của `POST /search`.

### 2.2. DTO Schemas (`apps/api/app/modules/search/schemas.py`)

```python
"""Pydantic Schemas for Search API Module."""

from __future__ import annotations

from pydantic import BaseModel, Field
from app.core.enums import DocumentScopeCode


class SearchQuerySchema(BaseModel):
    """Payload yêu cầu tìm kiếm RAG."""

    query: str = Field(..., min_length=1, max_length=1000, description="Từ khoá hoặc câu hỏi tìm kiếm")
    top_k: int = Field(default=10, ge=1, le=100, description="Số lượng kết quả trả về tối đa")
    document_ids: list[str] | None = Field(default=None, description="Danh sách ID tài liệu giới hạn tìm kiếm")
    scope: list[DocumentScopeCode] | DocumentScopeCode | None = Field(
        default=None, description="Scope tài liệu muốn lọc (nếu không truyền sẽ lấy theo quyền của Role)"
    )


class SearchResultItemSchema(BaseModel):
    """Mỗi đoạn văn bản (chunk) kết quả trả về."""

    chunk_id: str = Field(..., description="ID của chunk")
    document_id: str = Field(..., description="ID tài liệu sở hữu")
    version_id: str = Field(..., description="ID phiên bản tài liệu")
    document_title: str = Field(..., description="Tiêu đề tài liệu")
    chunk_index: int = Field(..., description="Thứ tự chunk trong tài liệu (0-indexed)")
    content: str = Field(..., description="Nội dung đoạn văn bản chunk")
    page_number: int | None = Field(None, description="Số trang PDF gốc (1-indexed)")
    bbox: list[float] | None = Field(None, description="Bounding box [x0, y0, x1, y1] PDF coordinates")
    score: float = Field(..., description="Điểm tương đồng RRF composite score")
    vector_similarity: float = Field(default=0.0, description="Điểm Cosine Similarity (0..1)")
    fts_score: float = Field(default=0.0, description="Điểm Full-Text Search ts_rank_cd")


class SearchResponseEnvelope(BaseModel):
    """Envelope chuẩn cho kết quả Search API (Envelope pattern {success, data, total})."""

    success: bool = Field(default=True)
    data: list[SearchResultItemSchema]
    total: int
```

### 2.3. Router Implementation Sketch (`apps/api/app/modules/search/router.py`)

```python
"""FastAPI Router for Search endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from app.modules.search import service
from app.modules.search.schemas import (
    SearchQuerySchema,
    SearchResponseEnvelope,
    SearchResultItemSchema,
)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponseEnvelope)
async def search_documents_post(
    body: SearchQuerySchema,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SearchResponseEnvelope:
    """Tìm kiếm tài liệu & đoạn văn bản bằng Hybrid Search (Vector + Full-Text Search + RRF)."""
    request_id = getattr(request.state, "request_id", "")
    
    results = await service.execute_search(
        session=session,
        user=current_user,
        query_payload=body,
        request_id=request_id,
    )
    
    return SearchResponseEnvelope(
        data=[SearchResultItemSchema.model_validate(r) for r in results],
        total=len(results),
    )


@router.get("", response_model=SearchResponseEnvelope)
async def search_documents_get(
    q: str = Query(..., min_length=1, description="Từ khoá hoặc câu hỏi tìm kiếm"),
    top_k: int = Query(10, ge=1, le=100),
    scope: list[str] | None = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SearchResponseEnvelope:
    """Convenience GET endpoint cho tìm kiếm từ URL Query String."""
    query_payload = SearchQuerySchema(
        query=q,
        top_k=top_k,
        scope=scope,  # type: ignore[arg-type]
    )
    results = await service.execute_search(
        session=session,
        user=current_user,
        query_payload=query_payload,
    )
    return SearchResponseEnvelope(
        data=[SearchResultItemSchema.model_validate(r) for r in results],
        total=len(results),
    )
```

---

## 3. OpenAPI Spec Gap Analysis & Proposed Patch (`docs/api/openapi.yaml`)

### 3.1. Hiện Trạng Trong `docs/api/openapi.yaml`

Khi kiểm tra `docs/api/openapi.yaml`:
- Tag `search` đã được định nghĩa tại dòng 36 (`- name: search`).
- Tuy nhiên, trong phần `paths:`, **chưa có định nghĩa route `/search`**.
- Trong phần `components/schemas:`, **chưa có các schema `SearchQuery`, `SearchResultItem`, `SearchResponse`**.

### 3.2. Đoạn Patch Đề Xuất Cho `docs/api/openapi.yaml`

#### 1) Thêm Schemas vào `components/schemas`:

```yaml
    # ----- Search RAG Schemas (Phase D) -----
    SearchQuery:
      type: object
      required: [query]
      properties:
        query:
          type: string
          minLength: 1
          maxLength: 1000
          description: Từ khoá hoặc câu hỏi tìm kiếm ngữ nghĩa
        top_k:
          type: integer
          default: 10
          minimum: 1
          maximum: 100
          description: Số lượng kết quả tối đa
        document_ids:
          type: array
          items: { type: string }
          description: Lọc danh sách ID tài liệu cụ thể
        scope:
          type: array
          items: { $ref: '#/components/schemas/DocumentScope' }
          description: Lọc theo danh sách scope (nếu không truyền sẽ tự động lấy theo quyền của Role)

    SearchResultItem:
      type: object
      required: [chunk_id, document_id, version_id, document_title, chunk_index, content, score]
      properties:
        chunk_id:
          type: string
          description: ID của đoạn văn bản (chunk)
        document_id:
          type: string
          description: ID của tài liệu gốc
        version_id:
          type: string
          description: ID của phiên bản tài liệu
        document_title:
          type: string
          description: Tiêu đề của tài liệu
        chunk_index:
          type: integer
          description: Thứ tự chunk trong phiên bản tài liệu (0-indexed)
        content:
          type: string
          description: Nội dung đoạn văn bản chunk
        page_number:
          type: [integer, "null"]
          description: Số trang PDF chứa chunk (1-indexed)
        bbox:
          type: [array, "null"]
          items: { type: number }
          minItems: 4
          maxItems: 4
          description: Bounding box [x0, y0, x1, y1] PDF coordinates
        score:
          type: number
          description: Điểm tương đồng hợp nhất (RRF composite score)
        vector_similarity:
          type: number
          description: Điểm tương đồng Cosine Similarity (0..1)
        fts_score:
          type: number
          description: Điểm số Full-Text Search (ts_rank_cd)

    SearchResponse:
      allOf:
        - $ref: '#/components/schemas/SuccessEnvelope'
        - type: object
          properties:
            data:
              type: array
              items: { $ref: '#/components/schemas/SearchResultItem' }
            total:
              type: integer
```

#### 2) Thêm Path `/search` vào `paths:`:

```yaml
  /search:
    post:
      tags: [search]
      summary: Tìm kiếm tài liệu & đoạn văn bản (Hybrid Search RAG)
      description: |
        Thực hiện tìm kiếm hỗn hợp kết hợp Vector Search (BGE-M3 1024-dim) và PostgreSQL Full-Text Search.
        Áp dụng thuật toán Reciprocal Rank Fusion (RRF) để xếp hạng kết quả.
        Tự động kiểm soát quyền xem tài liệu (RBAC scope filtering) dựa trên Role của JWT Token.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SearchQuery'
      responses:
        '200':
          description: OK — Trả về danh sách kết quả tìm kiếm được xếp hạng
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchResponse'
        '401': { $ref: '#/components/responses/Unauthorized' }
        '403': { $ref: '#/components/responses/Forbidden' }
        '422': { $ref: '#/components/responses/ValidationError' }

    get:
      tags: [search]
      summary: Tìm kiếm từ URL Query String (Convenience GET endpoint)
      parameters:
        - in: query
          name: q
          required: true
          schema: { type: string, minLength: 1 }
          description: Từ khoá hoặc câu hỏi tìm kiếm
        - in: query
          name: top_k
          required: false
          schema: { type: integer, default: 10, minimum: 1, maximum: 100 }
        - in: query
          name: scope
          required: false
          schema:
            type: array
            items: { $ref: '#/components/schemas/DocumentScope' }
      responses:
        '200':
          description: OK — Trả về kết quả tìm kiếm
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchResponse'
        '401': { $ref: '#/components/responses/Unauthorized' }
        '403': { $ref: '#/components/responses/Forbidden' }
        '422': { $ref: '#/components/responses/ValidationError' }
```

---

## 4. Kiến Trúc Tác Vụ Celery Indexing (`index_document_chunks_task`)

### 4.1. Luồng Kích Hoạt Tự Động (Automation Trigger Flow)

Theo nguyên lý State Machine định nghĩa trong `docs/domain/document-lifecycle.md` và `apps/api/app/worker/tasks.py`:

```
[User Upload PDF / Trigger OCR]
             |
             v
   [process_document_task]
             |
   (Run OCR Engine & Persist OCRBlocks)
             |
             v
[DocumentVersion.ocr_status == 'SUCCEEDED']
             |
             +---> trigger automatically: index_document_chunks_task.delay(version_id)
                                                  |
                                                  v
                                     [index_document_chunks_task]
                                                  |
                                   1. Fetch OCRBlocks of Version
                                   2. TextChunkerService -> DocumentChunk DTOs
                                   3. EmbeddingService -> 1024-dim Vectors
                                   4. Persist to DB document_chunks Table
```

### 4.2. Mã Nguồn Đề Xuất Cho Celery Task (`apps/api/app/worker/tasks.py`)

```python
@shared_task(name="app.worker.tasks.index_document_chunks_task", bind=True, max_retries=3) # type: ignore[untyped-decorator]
def index_document_chunks_task(self: Any, version_id: str) -> Any:
    """Celery task tự động chia nhỏ văn bản và đánh chỉ mục Vector cho phiên bản tài liệu.

    Được kích hoạt sau khi process_document_task chuyển ocr_status -> SUCCEEDED.
    """
    logger.info("start_index_document_chunks_task", version_id=version_id)
    return run_async(_async_index_document_chunks(version_id))


async def _async_index_document_chunks(version_id: str) -> dict[str, Any]:
    session_factory = get_session_factory()

    async with session_factory() as session:
        # 1. Fetch DocumentVersion và các OCRBlock thuộc version
        version_res = await session.execute(
            select(DocumentVersion).where(DocumentVersion.id == version_id)
        )
        version = version_res.scalar_one_or_none()

        if not version or version.ocr_status != "SUCCEEDED":
            logger.warning("index_task_skipped_invalid_version_or_status", version_id=version_id)
            return {"status": "SKIPPED", "reason": "Version not found or OCR status not SUCCEEDED"}

        blocks_res = await session.execute(
            select(OCRBlock)
            .where(OCRBlock.version_id == version_id)
            .order_by(OCRBlock.page_number.asc(), OCRBlock.block_index.asc())
        )
        blocks = list(blocks_res.scalars().all())

        if not blocks:
            logger.warning("index_task_no_ocr_blocks_found", version_id=version_id)
            return {"status": "SUCCEEDED", "chunk_count": 0}

        try:
            # 2. Xóa các chunk cũ nếu đây là lần re-indexing (Bảo đảm Idempotency)
            await session.execute(
                delete(DocumentChunk).where(DocumentChunk.version_id == version_id)
            )

            # 3. Phân đoạn văn bản bằng TextChunkerService
            chunker = TextChunkerService()
            chunk_dtos = chunker.chunk_ocr_blocks(blocks)

            if not chunk_dtos:
                await session.commit()
                return {"status": "SUCCEEDED", "chunk_count": 0}

            # 4. Sinh vector embedding 1024 chiều bằng EmbeddingService
            embedding_service = EmbeddingService()
            texts = [c.text for c in chunk_dtos]
            vectors = embedding_service.embed_batch(texts)

            # 5. Khởi tạo và lưu ORM DocumentChunk instances
            for idx, (c_dto, vec) in enumerate(zip(chunk_dtos, vectors, strict=False)):
                chunk_id = f"chunk_{uuid.uuid4().hex}"
                chunk_orm = DocumentChunk(
                    id=chunk_id,
                    document_id=version.document_id,
                    version_id=version.id,
                    chunk_index=idx,
                    content=c_dto.text,
                    embedding=vec,
                    page_number=c_dto.page_number,
                    bbox=c_dto.bbox,
                )
                session.add(chunk_orm)

            await session.commit()

            logger.info(
                "index_document_chunks_task_succeeded",
                version_id=version_id,
                chunk_count=len(chunk_dtos),
            )
            return {
                "status": "SUCCEEDED",
                "version_id": version_id,
                "chunk_count": len(chunk_dtos),
            }
        except Exception as exc:
            logger.exception("index_document_chunks_task_failed", version_id=version_id, error=str(exc))
            await session.rollback()
            return {"status": "FAILED", "error": str(exc)}
```

### 4.3. Tích Hợp Kích Hoạt Trong `process_document_task`

Trong `apps/api/app/worker/tasks.py` tại bước 6 của `_async_process_document`:

```python
            # 6. Complete processing
            job.progress = 100
            job.status = "SUCCEEDED"
            job.finished_at = datetime.now(UTC)

            version.ocr_status = "SUCCEEDED"
            version.requires_review = has_suspicious_blocks
            version.status = "UNDER_REVIEW"
            await session.commit()

            # Kích hoạt tự động tác vụ đánh chỉ mục indexing task
            index_document_chunks_task.delay(version_id=version.id)
```

---

## 5. Thực Thi RBAC Scope Enforcement Tầng API & SQL

### 5.1. Quy Tắc Phân Quyền Scope Theo Role (`docs/domain/rbac-matrix.md`)

| User Role | Document Scopes Được Phép Tìm Kiếm |
|---|---|
| `student` | `PUBLIC`, `STUDENT_AFFAIRS` |
| `staff` | `PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL` |
| `admin` | `PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL` |

### 5.2. Logic Tính Toán Effective Scopes Tại Application Service (`apps/api/app/modules/search/service.py`)

```python
"""Search Application Service — Phụ trách orchestrate Auth, Embedding & Hybrid Search."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.modules.documents.dependencies import get_allowed_scopes_for_user
from app.modules.search.schemas import SearchQuerySchema
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search import HybridSearchResult, search_hybrid


async def execute_search(
    session: AsyncSession,
    user: User,
    query_payload: SearchQuerySchema,
    request_id: str = "",
) -> list[HybridSearchResult]:
    """Xử lý yêu cầu tìm kiếm với kiểm soát quyền RBAC Scope nghiêm ngặt."""
    # 1. Xác định danh sách Scope được phép tối đa của User dựa trên Role
    role_allowed_scopes = get_allowed_scopes_for_user(user)

    # 2. Xử lý bộ lọc Scope do Client yêu cầu
    if query_payload.scope:
        if isinstance(query_payload.scope, str):
            requested = [query_payload.scope]
        else:
            requested = [s.value if hasattr(s, "value") else str(s) for s in query_payload.scope]

        # Giao giữa danh sách client yêu cầu và danh sách role cho phép
        effective_scopes = list(set(requested).intersection(set(role_allowed_scopes)))
    else:
        effective_scopes = role_allowed_scopes

    # Nếu không còn scope nào hợp lệ (vd: student cố tình lọc scope=INTERNAL) -> Trả về rỗng ngay lập tức
    if not effective_scopes:
        return []

    # 3. Sinh vector embedding cho câu truy vấn
    embedding_service = EmbeddingService()
    query_vec = embedding_service.embed_text(query_payload.query)

    # 4. Thực thi Hybrid Search trên DB (SQL CTE pgvector + FTS RRF)
    results = await search_hybrid(
        session=session,
        query_text=query_payload.query,
        query_vector=query_vec,
        allowed_scopes=effective_scopes,
        document_ids=query_payload.document_ids,
        limit=query_payload.top_k,
    )

    return results
```

### 5.3. Bảo Mật Lọc Scope Tại Tầng SQL Query

Trong câu truy vấn CTE `search_hybrid` (đã phân tích ở báo cáo Explorer 2):

```sql
WITH allowed_docs AS (
    SELECT id, title FROM documents 
    WHERE scope = ANY(:scopes) 
      AND deleted_at IS NULL 
      AND status = 'APPROVED'
      -- Thêm bộ lọc document_ids nếu client yêu cầu
      AND (:doc_ids IS NULL OR id = ANY(:doc_ids))
)
...
```

**Đặc điểm bảo mật cốt lõi**:
1. **Scope Filtering Isolate**: Tất cả truy vấn `document_chunks` đều `JOIN allowed_docs`. Các tài liệu thuộc scope `INTERNAL` (hoặc tài liệu đã bị xóa `deleted_at IS NOT NULL`, hoặc chưa được duyệt `status != 'APPROVED'`) **hoàn toàn bị gạch tên khỏi tập ứng viên trước khi tính toán Cosine Similarity hay ts_rank_cd**.
2. **Không rò rỉ Metadata**: Người dùng role `student` sẽ không nhận được bất kỳ chunk nào hay tiêu đề của tài liệu `INTERNAL`.

---

## 6. Sơ Đồ Luồng Tích Hợp Toàn Bộ Pipeline Phase D (Full Integration Flow)

```
========================================================================================
                               INGESTION & INDEXING PHASE
========================================================================================
[PDF Upload] -> [process_document_task] -> (OCR Output: OCRBlocks in DB)
                                                |
                                                v  (ocr_status == 'SUCCEEDED')
                                  [index_document_chunks_task]
                                                |
                               +----------------+----------------+
                               |                                 |
                               v                                 v
                     [TextChunkerService]              [EmbeddingService]
                     (Recursive Splitting +            (BGE-M3 1024-dim Vector
                      Metadata BBox Fusion)             Generation + Mock Fallback)
                               |                                 |
                               +----------------+----------------+
                                                |
                                                v
                                 [DB: document_chunks Table]
                                 (pgvector HNSW + GIN tsvector)

========================================================================================
                               SEARCH & RETRIEVAL PHASE
========================================================================================
[Client App] -> POST /api/v1/search { query: "...", top_k: 10 } (JWT Bearer Token)
                     |
                     v
            [FastAPI Search Router]
                     |
            [search.service: execute_search]
                     |
        +------------+------------+
        |                         |
        v                         v
[get_allowed_scopes_for_user]  [EmbeddingService.embed_text(query)]
(RBAC Scope: student ->        (Vector 1024-dim cho câu hỏi)
 PUBLIC, STUDENT_AFFAIRS)         |
        |                         |
        +------------+------------+
                     |
                     v
         [search_hybrid(SQL CTE)]
         - CTE 1: Filter allowed_docs by Scope & Status
         - CTE 2: Top N Vector Cosine Distance (<=>)
         - CTE 3: Top N Full-Text Search Rank (ts_rank_cd)
         - RRF Score Fusion: 1/(60 + r_vec) + 1/(60 + r_fts)
                     |
                     v
         [SearchResponseEnvelope] -> [Client App UI]
========================================================================================
```

---

## 7. Kế Hoạch Kiểm Thử & Xác Minh (Verification & Test Plan)

### 7.1. Unit Tests
1. `tests/test_search_schemas.py`: Validation các trường `query`, `top_k`, `scope` trong `SearchQuerySchema`.
2. `tests/test_search_service_rbac.py`:
   - Verify `student` role chỉ sinh `effective_scopes` = `['PUBLIC', 'STUDENT_AFFAIRS']`.
   - Verify `staff`/`admin` role sinh `effective_scopes` = `['PUBLIC', 'STUDENT_AFFAIRS', 'INTERNAL']`.
   - Verify khi `student` yêu cầu `scope=['INTERNAL']`, kết quả trả về `[]` ngay lập tức.
3. `tests/test_indexing_task.py`:
   - Mock `OCRBlock` records, gọi `index_document_chunks_task(version_id)`.
   - Verify `DocumentChunk` records được insert thành công vào DB với `embedding` 1024 chiều và `bbox` hợp lệ.

### 7.2. Integration & End-to-End Tests
1. `tests/test_search_router.py`:
   - Test endpoint `POST /api/v1/search` với token `student` và `staff`.
   - Verify cấu trúc response chuẩn envelope `{ success: true, data: [...], total: N }`.
   - Verify 401 Unauthorized khi thiếu Authorization header.

### 7.3. Governance & Quality Gates
- static check: `uv run ruff check app tests` (0 errors), `uv run mypy app` (0 errors).
- contract check: `oasdiff` đối chiếu `docs/api/openapi.yaml` sau khi patch route `/search`.
