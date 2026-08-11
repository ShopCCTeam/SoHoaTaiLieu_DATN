# Báo Cáo Phân Tích DB Vector Storage & Hybrid Search (Phase D)

**Dự án**: Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên  
**Thư mục làm việc**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_d_2`  
**Ngày**: 2026-08-11  
**Tác giả**: Explorer 2 Phase D  

---

## 1. Tổng Quan Mục Tiêu Phân Tích

Báo cáo này phân tích kiến trúc cơ sở dữ liệu lưu trữ Vector (DB Vector Storage) và Chiến lược Tìm kiếm Hỗn hợp (Hybrid Search Strategy) phục vụ cho Phase D (RAG Pipeline & Retrieval System) thuộc Backend FastAPI (`apps/api/`).

Phân tích bao gồm 3 thành phần chính:
1. **ORM Model `DocumentChunk`**: Bảng `document_chunks` chứa văn bản được chia nhỏ (chunks), embedding vector BGE-M3 (1024 dim), full-text search vector (`tsvector`), bounding box OCR (`bbox`), cùng cơ chế tương thích SQLite cho unit test.
2. **Alembic Migration `0005_document_chunks_pgvector.py`**: Kích hoạt extension `vector`, xây dựng chỉ mục vector HNSW (Cosine distance) và chỉ mục GIN full-text search trên PostgreSQL, có cơ chế phân nhánh dialect cho SQLite.
3. **Hybrid Search Strategy**: Kết hợp Cosine Similarity từ `pgvector` và điểm Full-Text Search `ts_rank_cd` từ PostgreSQL thông qua thuật toán **Reciprocal Rank Fusion (RRF)** trong 1 câu truy vấn SQL (CTE), kèm chiến lược fallback trên SQLite phục vụ pytest.

---

## 2. Thiết Kế ORM Model `DocumentChunk`

### 2.1. Cấu Trúc Cột & Kiểu Dữ Liệu

Bảng `document_chunks` chịu trách nhiệm lưu trữ thông tin các đoạn văn bản đã được cắt nhỏ từ tài liệu (giai đoạn ingest tài liệu / OCR completed) để phục vụ việc tìm kiếm ngữ nghĩa và trích dẫn.

| Tên Cột | Kiểu Dữ Liệu PostgreSQL | Kiểu Dữ Liệu SQLite (Test) | Ràng Buộc | Mô Tả |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | `VARCHAR(36)` | `PRIMARY KEY` | Chunk ID (UUID v4) |
| `document_id` | `VARCHAR(36)` | `VARCHAR(36)` | `NOT NULL`, `FK(documents.id CASCADE)` | ID tài liệu gốc |
| `version_id` | `VARCHAR(36)` | `VARCHAR(36)` | `NOT NULL`, `FK(document_versions.id CASCADE)` | ID phiên bản tài liệu chứa chunk |
| `chunk_index` | `INTEGER` | `INTEGER` | `NOT NULL` | Thứ tự chunk trong phiên bản (0-indexed) |
| `content` | `TEXT` | `TEXT` | `NOT NULL` | Nội dung văn bản của chunk |
| `embedding` | `vector(1024)` | `JSON` / `TEXT` | `NULLABLE` | Vector embedding 1024 chiều (BGE-M3) |
| `page_number` | `INTEGER` | `INTEGER` | `NULLABLE` | Trang PDF xuất phát (1-indexed) |
| `bbox` | `JSONB` / `JSON` | `JSON` | `NULLABLE` | Bounding box `[x0, y0, x1, y1]` từ OCR (nếu có) |
| `tsvector` | `tsvector` | `TEXT` | `NULLABLE` | Full-text search vector của PostgreSQL |
| `created_at` | `TIMESTAMPTZ` | `DATETIME` | `NOT NULL`, `DEFAULT now()` | Thời điểm tạo chunk |
| `updated_at` | `TIMESTAMPTZ` | `DATETIME` | `NOT NULL`, `DEFAULT now()` | Thời điểm cập nhật cuối |

### 2.2. Giải Pháp Tương Thích SQLite (Pytest Unit Tests)

Trong bộ testsuite hiện tại (`apps/api/tests/conftest.py`), unit tests chạy trên engine `sqlite+aiosqlite:///:memory:` thông qua `Base.metadata.create_all`. SQLite không có kiểu dữ liệu native `vector` của pgvector hay `tsvector` của PostgreSQL.

Để tránh lỗi `CompileError` / `NotImplementedError` khi khởi tạo DB schema trên SQLite mà vẫn giữ nguyên type safety và tính năng native trên PostgreSQL, áp dụng pattern `TypeDecorator` tương tự như `_UUID` và `_INet` trong `app/models/refresh_session.py`:

```python
from typing import Any
from sqlalchemy import JSON, Text
from sqlalchemy.types import TypeDecorator

class _Vector(TypeDecorator[list[float]]):
    """Lưu Vector(1024) trên PostgreSQL, fallback thành JSON/TEXT trên SQLite."""
    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 1024):
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())

class _TSVector(TypeDecorator[Any]):
    """Lưu TSVECTOR trên PostgreSQL, fallback thành TEXT trên SQLite."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import TSVECTOR
            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(Text())
```

### 2.3. Mã Nguồn Đề Xuất Cho `app/models/document_chunk.py`

```python
"""DocumentChunk ORM model — Lưu trữ Vector Embedding & TSVector cho Hybrid Search.

Table: document_chunks
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.document_version import DocumentVersion


class _Vector(TypeDecorator[list[float]]):
    """Vector(dim) cho PostgreSQL pgvector, fallback JSON cho SQLite."""

    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 1024):
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())


class _TSVector(TypeDecorator[Any]):
    """TSVECTOR cho PostgreSQL, fallback Text cho SQLite."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import TSVECTOR

            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(Text())


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_document_version", "document_id", "version_id"),
        Index("ix_document_chunks_version_index", "version_id", "chunk_index"),
        Index("ix_document_chunks_version_page", "version_id", "page_number"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="Document Chunk ID (UUID v4)",
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID tài liệu sở hữu chunk này",
    )
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID phiên bản tài liệu tương ứng",
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Thứ tự chunk trong tài liệu (0-indexed)",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Nội dung văn bản của chunk",
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        _Vector(1024),
        nullable=True,
        comment="Embedding vector 1024 chiều (BGE-M3)",
    )
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Số trang PDF gốc chứa chunk (1-indexed)",
    )
    bbox: Mapped[Any | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Bounding box [x0, y0, x1, y1] từ OCR",
    )
    tsvector: Mapped[Any | None] = mapped_column(
        _TSVector(),
        nullable=True,
        comment="Vector phục vụ full-text search PostgreSQL",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    document: Mapped[Document] = relationship("Document", foreign_keys=[document_id])
    version: Mapped[DocumentVersion] = relationship("DocumentVersion", foreign_keys=[version_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DocumentChunk id={self.id} doc={self.document_id} idx={self.chunk_index}>"
```

---

## 3. Thiết Kế Alembic Migration `0005_document_chunks_pgvector.py`

### 3.1. Phân Tích Chỉ Mục Chỉ Định (Index Strategy)

1. **Vector Index: HNSW (Hierarchical Navigable Small World)**
   - Oper: `vector_cosine_ops` (phục vụ Cosine Distance `<=>`).
   - Tham số khuyến nghị: `m = 16`, `ef_construction = 64`.
   - **So sánh với IVFFlat**:
     - *IVFFlat*: Cần chạy training qua danh sách trung tâm (lists) sau khi đã có dữ liệu ban đầu. Nếu insert dữ liệu mới liên tục mà không `REINDEX`, chất lượng recall suy giảm.
     - *HNSW*: Xây dựng đồ thị linh hoạt ngay từ khi insert từng dòng. Đạt độ chính xác recall > 95% với thời gian truy vấn cực nhanh (vài ms) trên dataset ~10K–100K vectors mà không cần giai đoạn warm-up training.
     - **Kết luận**: Chọn **HNSW** cho `document_chunks.embedding`.

2. **Full-Text Search Index: GIN (Generalized Inverted Index)**
   - Tạo GIN Index trên cột `tsvector`.
   - GIN giúp tăng tốc độ tìm kiếm từ khóa với toán tử `@@` gấp hàng trăm lần so với việc scan bảng.
   - Cột `tsvector` trong PostgreSQL có thể tự động cập nhật thông qua `GENERATED ALWAYS AS (to_tsvector('simple', coalesce(content, '')))` hoặc DDL Trigger.

3. **Cơ Chế Phân Nhánh Dialect (PostgreSQL vs SQLite)**
   Alembic migration phải chạy an toàn trong môi trường test/local (khi URL dùng SQLite) mà không throw error do extension hay toán tử của Postgres.

### 3.2. Mã Nguồn Đề Xuất Cho Migration `0005`

```python
"""Create document_chunks table and pgvector/GIN indexes for Phase D.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-11
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Enable pgvector extension nếu là PostgreSQL
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Xây dựng kiểu cột dựa trên dialect
    if is_postgres:
        from pgvector.sqlalchemy import Vector
        embedding_type = Vector(1024)
        tsvector_type = postgresql.TSVECTOR()
    else:
        embedding_type = sa.JSON()
        tsvector_type = sa.Text()

    # 3. Tạo bảng document_chunks
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", embedding_type, nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("bbox", sa.JSON(), nullable=True),
        sa.Column("tsvector", tsvector_type, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["version_id"], ["document_versions.id"], ondelete="CASCADE"
        ),
    )

    # 4. Standard B-Tree Indexes
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_version_id", "document_chunks", ["version_id"])
    op.create_index("ix_document_chunks_page_number", "document_chunks", ["page_number"])
    op.create_index(
        "ix_document_chunks_document_version",
        "document_chunks",
        ["document_id", "version_id"],
    )
    op.create_index(
        "ix_document_chunks_version_index",
        "document_chunks",
        ["version_id", "chunk_index"],
    )
    op.create_index(
        "ix_document_chunks_version_page",
        "document_chunks",
        ["version_id", "page_number"],
    )

    # 5. Postgres-Specific Vector & Full-Text Search Indexes & Trigger
    if is_postgres:
        # HNSW Index cho Vector Cosine Distance
        op.create_index(
            "ix_document_chunks_embedding_hnsw",
            "document_chunks",
            ["embedding"],
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        )
        # GIN Index cho Full-Text Search
        op.create_index(
            "ix_document_chunks_tsvector_gin",
            "document_chunks",
            ["tsvector"],
            postgresql_using="gin",
        )
        # Trigger tự động sinh tsvector từ content khi INSERT/UPDATE
        op.execute(
            """
            CREATE OR REPLACE FUNCTION document_chunks_tsvector_trigger() RETURNS trigger AS $$
            begin
              new.tsvector := to_tsvector('simple', coalesce(new.content, ''));
              return new;
            end
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
            ON document_chunks FOR EACH ROW EXECUTE FUNCTION document_chunks_tsvector_trigger();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("DROP TRIGGER IF EXISTS tsvectorupdate ON document_chunks;")
        op.execute("DROP FUNCTION IF EXISTS document_chunks_tsvector_trigger();")
        op.drop_index("ix_document_chunks_tsvector_gin", table_name="document_chunks")
        op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")

    op.drop_index("ix_document_chunks_version_page", table_name="document_chunks")
    op.drop_index("ix_document_chunks_version_index", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_version", table_name="document_chunks")
    op.drop_index("ix_document_chunks_page_number", table_name="document_chunks")
    op.drop_index("ix_document_chunks_version_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")

    op.drop_table("document_chunks")
```

---

## 4. Chiến Lược Hybrid Search (Vector + Full-Text Search)

### 4.1. Toán Tử & Hàm Tính Đội Lệch / Điểm Số

1. **pgvector Cosine Distance**:
   - Trong `pgvector`, toán tử `<=>` trả về khoảng cách Cosine $d \in [0, 2]$.
   - Điểm tương đồng Cosine (Cosine Similarity): $S_{\text{vec}} = 1 - (embedding \Leftrightarrow query\_vec)$.

2. **PostgreSQL Full-Text Search Rank**:
   - Sử dụng `websearch_to_tsquery('simple', query_text)` để parse câu hỏi tự nhiên thành tsquery an toàn.
   - Điểm FTS: `ts_rank_cd(tsvector, websearch_to_tsquery('simple', query_text))`.

### 4.2. So Sánh Thuật Toán Tổng Hợp (RRF vs Weighted Score)

#### Thuật Toán 1: Reciprocal Rank Fusion (RRF) — **Đề Xuất Chọn**
- **Công thức**:
  $$RRF\_Score(d) = \frac{1}{k + r_{\text{vec}}(d)} + \frac{1}{k + r_{\text{fts}}(d)}$$
  (với $k = 60$ là hằng số chuẩn quốc tế từ nghiên cứu của Cormack et al.).
- **Nguyên lý**: Lấy danh sách Top N (vd: N=50) từ Vector Search (xếp hạng $r_{\text{vec}}$) và Top N từ FTS Search (xếp hạng $r_{\text{fts}}$). Cấu trúc RRF tính điểm dựa trên thứ hạng (rank) chứ không phụ thuộc vào giá trị điểm số thô (raw score).
- **Ưu điểm vượt trội**:
  - Triệt tiêu hoàn toàn sự chênh lệch thang đo giữa Cosine Similarity (trong khoảng [0, 1]) và `ts_rank_cd` (giá trị không bị chặn trên, phụ thuộc tần suất từ).
  - Kháng nhiễu cực tốt khi một trong hai phương pháp cho ra outlier.
  - Không đòi hỏi tinh chỉnh trọng số $\alpha$ tùy thuộc ngữ cảnh câu hỏi.

#### Thuật Toán 2: Weighted Score (Linear Combination)
- **Công thức**:
  $$Score(d) = \alpha \cdot S_{\text{vec\_norm}}(d) + (1 - \alpha) \cdot S_{\text{fts\_norm}}(d)$$
- **Nhược điểm**: `ts_rank_cd` biến thiên rất rộng, việc Min-Max Normalization phụ thuộc vào tập ứng viên Top N trả về, dẫn đến điểm tổng hợp bị méo mó nếu câu hỏi chứa từ xuất hiện dày đặc.

### 4.3. Đánh Giá Hiệu Năng SQL CTE Đơn Trên PostgreSQL

Chúng ta có thể thực thi RRF **trực tiếp trong 1 câu lệnh SQL duy nhất** trên PostgreSQL bằng cách kết hợp Common Table Expressions (CTE) và Window Function `ROW_NUMBER()`:

```sql
WITH allowed_docs AS (
    -- RBAC & Metadata filtering áp dụng ĐẦU TIÊN
    SELECT id FROM documents 
    WHERE scope IN (:scopes) AND deleted_at IS NULL AND status = 'APPROVED'
),
vector_matches AS (
    SELECT 
        c.id,
        ROW_NUMBER() OVER (ORDER BY c.embedding <=> :query_vec ASC) AS rank_vec,
        1.0 - (c.embedding <=> :query_vec) AS vec_sim
    FROM document_chunks c
    JOIN allowed_docs d ON c.document_id = d.id
    WHERE c.embedding IS NOT NULL
    ORDER BY c.embedding <=> :query_vec ASC
    LIMIT :top_n
),
fts_matches AS (
    SELECT 
        c.id,
        ROW_NUMBER() OVER (ORDER BY ts_rank_cd(c.tsvector, websearch_to_tsquery('simple', :query_text)) DESC) AS rank_fts,
        ts_rank_cd(c.tsvector, websearch_to_tsquery('simple', :query_text)) AS fts_score
    FROM document_chunks c
    JOIN allowed_docs d ON c.document_id = d.id
    WHERE c.tsvector @@ websearch_to_tsquery('simple', :query_text)
    ORDER BY fts_score DESC
    LIMIT :top_n
)
SELECT 
    c.id,
    c.document_id,
    c.version_id,
    c.chunk_index,
    c.content,
    c.page_number,
    c.bbox,
    d.title AS document_title,
    COALESCE(v.vec_sim, 0.0) AS vector_similarity,
    COALESCE(f.fts_score, 0.0) AS fts_score,
    COALESCE(1.0 / (60.0 + v.rank_vec), 0.0) + COALESCE(1.0 / (60.0 + f.rank_fts), 0.0) AS rrf_score
FROM document_chunks c
JOIN documents d ON c.document_id = d.id
LEFT JOIN vector_matches v ON c.id = v.id
LEFT JOIN fts_matches f ON c.id = f.id
WHERE v.id IS NOT NULL OR f.id IS NOT NULL
ORDER BY rrf_score DESC
LIMIT :limit;
```

---

## 5. Chiến Lược Fallback Chi Tiết Cho SQLite (Pytest Unit Tests)

Do Pytest unit test sử dụng SQLite in-memory, SQLite không hỗ trợ toán tử `<=>` hay `tsvector` / `ts_rank_cd`. `HybridSearchService` sẽ phát hiện dialect hiện tại và kích hoạt fallback mode như sau:

### 5.1. Thuật Toán Fallback Trực Tiếp Bằng Python
1. **FTS Search Fallback**:
   - Sử dụng truy vấn SQL `LIKE '%query%'` trên cột `content` hoặc tách từ tiếng Việt cơ bản.
   - Xếp hạng theo độ dài chuỗi trùng khớp hoặc tần suất xuất hiện từ khóa.
2. **Vector Search Fallback**:
   - Lấy tập các chunks từ DB.
   - Nếu `embedding` lưu dưới dạng JSON Array: Tính Cosine Similarity bằng Python:
     $$\text{sim}(u, v) = \frac{\sum u_i v_i}{\sqrt{\sum u_i^2} \sqrt{\sum v_i^2}}$$
3. **RRF Hybrid Ranking**:
   - Trích xuất Top N từ FTS Python và Top N từ Vector Python.
   - Áp dụng đúng công thức RRF $1/(60 + rank_{vec}) + 1/(60 + rank_{fts})$ trong Python để ghép thứ hạng.

### 5.2. Mã Nguồn Đề Xuất `app/services/hybrid_search.py`

```python
"""Hybrid Search Service — Kết hợp pgvector và PostgreSQL Full-Text Search (RRF).

Có SQLite fallback hỗ trợ Pytest unit tests.
"""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class HybridSearchResult:
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        version_id: str,
        chunk_index: int,
        content: str,
        page_number: int | None,
        bbox: Any | None,
        document_title: str,
        rrf_score: float,
        vector_similarity: float = 0.0,
        fts_score: float = 0.0,
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.version_id = version_id
        self.chunk_index = chunk_index
        self.content = content
        self.page_number = page_number
        self.bbox = bbox
        self.document_title = document_title
        self.rrf_score = rrf_score
        self.vector_similarity = vector_similarity
        self.fts_score = fts_score


async def search_hybrid(
    session: AsyncSession,
    query_text: str,
    query_vector: list[float],
    allowed_scopes: list[str],
    top_n_candidates: int = 50,
    limit: int = 10,
    rrf_k: int = 60,
) -> list[HybridSearchResult]:
    """Thực hiện Hybrid Search kết hợp Vector Search & Full-Text Search.

    Sử dụng RRF (Reciprocal Rank Fusion) để ghép thứ hạng.
    """
    bind = session.bind
    dialect_name = bind.dialect.name if bind else "postgresql"

    if dialect_name == "sqlite":
        return await _search_hybrid_sqlite(
            session, query_text, query_vector, allowed_scopes, top_n_candidates, limit, rrf_k
        )

    # PostgreSQL Execution via CTE
    sql = text(
        """
        WITH allowed_docs AS (
            SELECT id, title FROM documents 
            WHERE scope = ANY(:scopes) AND deleted_at IS NULL AND status = 'APPROVED'
        ),
        vector_matches AS (
            SELECT 
                c.id,
                ROW_NUMBER() OVER (ORDER BY c.embedding <=> :query_vec ASC) AS rank_vec,
                1.0 - (c.embedding <=> :query_vec) AS vec_sim
            FROM document_chunks c
            JOIN allowed_docs d ON c.document_id = d.id
            WHERE c.embedding IS NOT NULL
            ORDER BY c.embedding <=> :query_vec ASC
            LIMIT :top_n
        ),
        fts_matches AS (
            SELECT 
                c.id,
                ROW_NUMBER() OVER (ORDER BY ts_rank_cd(c.tsvector, websearch_to_tsquery('simple', :query_text)) DESC) AS rank_fts,
                ts_rank_cd(c.tsvector, websearch_to_tsquery('simple', :query_text)) AS fts_score
            FROM document_chunks c
            JOIN allowed_docs d ON c.document_id = d.id
            WHERE c.tsvector @@ websearch_to_tsquery('simple', :query_text)
            ORDER BY fts_score DESC
            LIMIT :top_n
        )
        SELECT 
            c.id,
            c.document_id,
            c.version_id,
            c.chunk_index,
            c.content,
            c.page_number,
            c.bbox,
            ad.title AS document_title,
            COALESCE(v.vec_sim, 0.0) AS vector_similarity,
            COALESCE(f.fts_score, 0.0) AS fts_score,
            COALESCE(1.0 / (:rrf_k + v.rank_vec), 0.0) + COALESCE(1.0 / (:rrf_k + f.rank_fts), 0.0) AS rrf_score
        FROM document_chunks c
        JOIN allowed_docs ad ON c.document_id = ad.id
        LEFT JOIN vector_matches v ON c.id = v.id
        LEFT JOIN fts_matches f ON c.id = f.id
        WHERE v.id IS NOT NULL OR f.id IS NOT NULL
        ORDER BY rrf_score DESC
        LIMIT :limit;
        """
    )

    # Format vector cho pgvector string literal [v1, v2, ...]
    vector_str = f"[{','.join(map(str, query_vector))}]"

    result = await session.execute(
        sql,
        {
            "scopes": allowed_scopes,
            "query_vec": vector_str,
            "query_text": query_text,
            "top_n": top_n_candidates,
            "limit": limit,
            "rrf_k": float(rrf_k),
        },
    )
    rows = result.mappings().all()

    return [
        HybridSearchResult(
            chunk_id=r["id"],
            document_id=r["document_id"],
            version_id=r["version_id"],
            chunk_index=r["chunk_index"],
            content=r["content"],
            page_number=r["page_number"],
            bbox=r["bbox"],
            document_title=r["document_title"],
            rrf_score=float(r["rrf_score"]),
            vector_similarity=float(r["vector_similarity"]),
            fts_score=float(r["fts_score"]),
        )
        for r in rows
    ]


async def _search_hybrid_sqlite(
    session: AsyncSession,
    query_text: str,
    query_vector: list[float],
    allowed_scopes: list[str],
    top_n_candidates: int,
    limit: int,
    rrf_k: int,
) -> list[HybridSearchResult]:
    """Python-level RRF Fallback dành riêng cho SQLite (pytest unit tests)."""
    # 1. Fetch chunks từ DB thuộc scope cho phép
    sql = text(
        """
        SELECT c.id, c.document_id, c.version_id, c.chunk_index, c.content, 
               c.page_number, c.bbox, c.embedding, d.title AS document_title
        FROM document_chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE d.scope IN (:scopes) AND d.deleted_at IS NULL AND d.status = 'APPROVED'
        """
    )
    res = await session.execute(sql, {"scopes": allowed_scopes})
    rows = res.mappings().all()

    if not rows:
        return []

    # 2. Vector search via Python cosine similarity
    def cosine_sim(v1: list[float], v2: list[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        return dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0

    vector_scored = []
    fts_scored = []

    words = [w.lower() for w in query_text.split() if w.strip()]

    for r in rows:
        c_id = r["id"]
        content_lower = r["content"].lower()

        # Vector score
        emb = r["embedding"]
        if isinstance(emb, str):
            import json

            emb = json.loads(emb)
        sim = cosine_sim(query_vector, emb) if emb else 0.0
        vector_scored.append((c_id, sim))

        # FTS score (simple keyword match ratio)
        matches = sum(1 for w in words if w in content_lower)
        fts_score = matches / len(words) if words else 0.0
        if fts_score > 0:
            fts_scored.append((c_id, fts_score))

    # Sort & Assign Ranks
    vector_scored.sort(key=lambda x: x[1], reverse=True)
    fts_scored.sort(key=lambda x: x[1], reverse=True)

    vec_ranks = {item[0]: idx + 1 for idx, item in enumerate(vector_scored[:top_n_candidates])}
    fts_ranks = {item[0]: idx + 1 for idx, item in enumerate(fts_scored[:top_n_candidates])}

    vec_sim_map = dict(vector_scored)
    fts_score_map = dict(fts_scored)

    # Compute RRF
    candidate_ids = set(vec_ranks.keys()).union(set(fts_ranks.keys()))
    row_map = {r["id"]: r for r in rows}

    results = []
    for c_id in candidate_ids:
        r = row_map[c_id]
        r_vec = vec_ranks.get(c_id)
        r_fts = fts_ranks.get(c_id)

        rrf_score = 0.0
        if r_vec is not None:
            rrf_score += 1.0 / (rrf_k + r_vec)
        if r_fts is not None:
            rrf_score += 1.0 / (rrf_k + r_fts)

        results.append(
            HybridSearchResult(
                chunk_id=r["id"],
                document_id=r["document_id"],
                version_id=r["version_id"],
                chunk_index=r["chunk_index"],
                content=r["content"],
                page_number=r["page_number"],
                bbox=r["bbox"],
                document_title=r["document_title"],
                rrf_score=rrf_score,
                vector_similarity=vec_sim_map.get(c_id, 0.0),
                fts_score=fts_score_map.get(c_id, 0.0),
            )
        )

    results.sort(key=lambda x: x.rrf_score, reverse=True)
    return results[:limit]
```

---

## 6. Đánh Giá Bảo Mật & Tuân Thủ Quy Định (RBAC & Citation Alignment)

1. **Ràng buộc RBAC & Metadata Filtering**:
   - Quy định tại `docs/domain/rbac-matrix.md` và `.agents/rules/04-database-rag-ocr.md`: Mọi truy vấn Vector/Hybrid Search **phải thực hiện filter scope** (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`) và `deleted_at IS NULL` **TRƯỚC KHI** tính toán Vector similarity hay FTS rank.
   - Truy vấn CTE đề xuất ở trên thực hiện filtering trong CTE `allowed_docs`, đảm bảo không bị rò rỉ dữ liệu hoặc tính toán thừa trên các tài liệu user không có quyền truy cập.

2. **Khớp với Citation Spec (`docs/domain/citation-spec.md`)**:
   - `HybridSearchResult` cung cấp đầy đủ thông tin: `document_id`, `version_id`, `document_title`, `page_number`, `chunk_id`, `content`, `bbox`, `rrf_score`.
   - Đáp ứng các yêu cầu trích dẫn bắt buộc cho Phase D Chat RAG Endpoint.

---

## 7. Tóm Tắt & Kết Luận

1. **ORM Model `DocumentChunk`**:
   - Sử dụng `_Vector(1024)` và `_TSVector()` custom `TypeDecorator` để tương thích trong suốt giữa PostgreSQL pgvector và SQLite unit tests.
2. **Alembic Migration `0005`**:
   - Sử dụng HNSW index cho `embedding` vector (cosine distance) và GIN index cho `tsvector`. Tự động phân nhánh cho SQLite test.
3. **Hybrid Search Strategy**:
   - Chọn **Reciprocal Rank Fusion (RRF)** với $k=60$ làm thuật toán chuẩn.
   - Triển khai 1 câu SQL CTE duy nhất cực kỳ tối ưu trên PostgreSQL và có Python RRF Fallback cho SQLite pytest.
