# Handoff Report — Explorer 2 Phase D

**Dự án**: Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên  
**Thư mục làm việc**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_d_2`  
**Ngày**: 2026-08-11  
**Người thực hiện**: Explorer 2 Phase D  
**Handoff Type**: Hard (Hoàn tất phân tích Phase D DB Vector Storage & Hybrid Search)  

---

## 1. Observation (Quan Sát Trực Tiếp)

- **Codebase hiện tại (`apps/api/`)**:
  - Đã có 4 migrations từ `0001` đến `0004` trong `apps/api/alembic/versions/`.
  - Migration `0004_ocr_pages_and_blocks.py` đã định nghĩa các bảng `ocr_pages` và `ocr_blocks`.
  - Chưa có model `DocumentChunk` hay migration `0005` cho vector storage.
  - Phụ thuộc trong `pyproject.toml`: `sqlalchemy>=2.0.36`, `asyncpg>=0.30.0`, `alembic>=1.13.3`, `aiosqlite>=0.20.0`. Gói `pgvector` chưa có trong dependencies của `pyproject.toml`.
  - File `apps/api/app/models/refresh_session.py` (dòng 22-65) áp dụng pattern `TypeDecorator` (`_UUID`, `_INet`) để hỗ trợ song song PostgreSQL và SQLite unit tests.
  - File `apps/api/tests/conftest.py` (dòng 63-78) chạy SQLite engine với `Base.metadata.create_all` cho các unit tests.
- **Tài liệu quy định**:
  - `docs/adr/0001-backend-stack.md`: Chốt PostgreSQL 16 + pgvector (`vector(1024)` cho BGE-M3 model), không sử dụng Qdrant riêng.
  - `docs/domain/citation-spec.md`: Quy định cấu trúc citation trích dẫn (`document_id`, `version_id`, `chunk_id`, `quote`, `score`, `bbox`, `page_number`, `title`).
  - `.agents/rules/04-database-rag-ocr.md`: Chỉ định HNSW index (`<=>` cosine similarity) và tsvector + GIN index cho combined search RAG retrieval. Bắt buộc metadata filtering scope TRƯỚC KHI vector search.

---

## 2. Logic Chain (Chuỗi Lập Luận Kiến Trúc)

1. **Từ Quan Sát Pytest SQLite Engine & SQLAlchemy Base**:
   - Do unit test chạy SQLite in-memory qua `Base.metadata.create_all`, nếu ORM Model `DocumentChunk` dùng trực tiếp `pgvector.sqlalchemy.Vector` hoặc `postgresql.TSVECTOR` mà không có fallback wrapper, SQLite DDL compilation sẽ thất bại.
   - **Suy luận**: Bắt buộc phải định nghĩa custom `TypeDecorator` (`_Vector` và `_TSVector`) để khi dialect là SQLite, SQLAlchemy tự chuyển thành `JSON`/`TEXT`, đảm bảo 100% Pytest unit test không bị gãy.

2. **Từ Yêu Cầu Migration `0005_document_chunks_pgvector.py`**:
   - Cần lệnh `CREATE EXTENSION IF NOT EXISTS vector;` và các chỉ mục PostgreSQL đặc thù (`HNSW` với `vector_cosine_ops` và `GIN` cho `tsvector`).
   - SQLite không hỗ trợ extensions hay syntax HNSW/GIN.
   - **Suy luận**: Trong script migration `0005`, kiểm tra `op.get_bind().dialect.name == "postgresql"`. Nếu là Postgres thì kích hoạt extension, tạo chỉ mục HNSW/GIN và Trigger tự động cập nhật `tsvector`. Nếu là SQLite thì chỉ tạo các chỉ mục B-Tree tiêu chuẩn.

3. **Từ Chiến Lược Tìm Kiếm Hỗn Hợp (Hybrid Search Strategy)**:
   - Cosine Distance trong pgvector trả về khoảng cách $d = 1 - sim$, trong khi `ts_rank_cd` của PostgreSQL trả về điểm FTS không bị giới hạn trên. Phép cộng tuyến tính có trọng số (Weighted Linear Combination) dễ bị méo do điểm FTS không đồng nhất thang đo.
   - **Suy luận**: Chọn **Reciprocal Rank Fusion (RRF)** làm giải pháp chủ đạo với hằng số $k=60$. RRF chuyển đổi điểm số thô thành điểm thứ hạng $1 / (k + rank)$, triệt tiêu lệch thang đo.
   - RRF được gói gọn trong 1 câu lệnh PostgreSQL SQL CTE duy nhất với `ROW_NUMBER()`, giúp giảm thiểu roundtrip giữa API và DB server.
   - Khi chạy dưới SQLite (pytest), `HybridSearchService` tự động chuyển sang Python RRF fallback (tính Cosine Similarity trên JSON array và FTS keyword match) để unit test chạy trơn tru.

---

## 3. Caveats (Các Điểm Lưu Ý & Giả Định)

1. **Dependencies**: Đề xuất bổ sung `pgvector>=0.3.0` vào `dependencies` trong `pyproject.toml` để ứng dụng có sẵn `from pgvector.sqlalchemy import Vector`.
2. **Benchmark HNSW Parameter**: Tham số HNSW `m=16`, `ef_construction=64` được thiết lập làm chuẩn mặc định cho dataset ~10K–100K chunks. Đối với dataset sản xuất lớn hơn (> 500K chunks), cần benchmark thực nghiệm giá trị `ef_search` khi query để tối ưu giữa latency và recall.
3. **Vietnamese Text Search Config**: Trong câu lệnh `to_tsvector('simple', ...)` hiện tại sử dụng dictionary `'simple'`. Nếu dự án mở rộng hỗ trợ unaccent hoặc vietnamese dictionary mở rộng trong PostgreSQL (`pg_trgm` / `unaccent`), trigger và query FTS có thể nâng cấp thêm `unaccent()`.

---

## 4. Conclusion (Kết Luận Phân Tích)

1. **ORM Model `DocumentChunk`**: Đã thiết kế hoàn chỉnh trong `analysis.md` với đầy đủ các thuộc tính `id`, `document_id`, `version_id`, `chunk_index`, `content`, `embedding` (Vector 1024), `page_number`, `bbox`, `tsvector`, quan hệ hai chiều với `Document` và `DocumentVersion`, cùng wrapper `_Vector` và `_TSVector` an toàn cho SQLite.
2. **Alembic Migration `0005`**: Đã xây dựng hoàn chỉnh script migration `0005_document_chunks_pgvector.py` với chỉ mục HNSW cosine distance (`m=16, ef_construction=64`), chỉ mục GIN full-text search, trigger tự động cập nhật tsvector và cơ chế phân nhánh dialect SQLite.
3. **Hybrid Search Strategy**: Đã thiết kế dịch vụ `HybridSearchService` (`app/services/hybrid_search.py`) với thuật toán Reciprocal Rank Fusion (RRF) $k=60$ chạy bằng SQL CTE tối ưu trên PostgreSQL và Python RRF fallback trên SQLite cho Pytest unit test. Tuân thủ 100% quy định RBAC scope pre-filtering và Citation Spec.

---

## 5. Verification Method (Phương Pháp Kiểm Thu)

Khi Implementer tiến hành triển khai mã nguồn thực tế, thực hiện các bước kiểm thử độc lập sau:

1. **Kiểm tra Migration Alembic trên PostgreSQL**:
   ```bash
   cd apps/api
   uv run alembic upgrade head
   ```
   *Điều kiện đạt*: Tạo thành công bảng `document_chunks`, extension `vector`, trigger `tsvectorupdate`, chỉ mục HNSW `ix_document_chunks_embedding_hnsw` và GIN `ix_document_chunks_tsvector_gin`.

2. **Kiểm tra Migration / Unit Test trên SQLite (Pytest)**:
   ```bash
   cd apps/api
   uv run pytest tests/test_models.py
   ```
   *Điều kiện đạt*: Mọi unit test chạy trên SQLite in-memory pass 100% không gặp lỗi `CompileError` hay `NotImplementedError` liên quan đến `Vector` hoặc `TSVECTOR`.

3. **Kiểm tra Hybrid Search Integration Test**:
   - Chạy test suite integration trên PostgreSQL (nếu có container Postgres):
     ```bash
     cd apps/api
     uv run pytest tests/test_hybrid_search.py -m integration
     ```
   - Xác minh kết quả trả về từ `search_hybrid` có thứ tự `rrf_score` giảm dần, chứa đầy đủ metadata trích dẫn (`document_id`, `version_id`, `title`, `page_number`, `bbox`, `content`).

---

**Đã ghi nhận báo cáo chi tiết tại**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_d_2\analysis.md`
