# ADR-0001: Chốt Backend Stack (Python + FastAPI + pgvector)

> **Trạng thái**: Accepted · **Ngày**: 2026-08-09 · **Tác giả**: Agent (theo quyết định của team)

## Bối cảnh

Dự án cần một backend cho hệ thống số hoá tài liệu CTSV với các yêu cầu:
- OCR pipeline (PaddleOCR + Tesseract fallback).
- RAG pipeline (LangChain + embedding + LLM local).
- File storage (PDF lớn, có thể 50 MB / file).
- Background job (OCR mất nhiều phút, không thể blocking HTTP request).
- RBAC 3 roles.
- Audit log cho mọi mutation quan trọng.
- Triển khai được trong đồ án tốt nghiệp (2–3 tháng).

## Quyết định

| Layer | Công nghệ | Lý do |
|---|---|---|
| **Ngôn ngữ** | Python 3.11 | Cùng ngôn ngữ với PaddleOCR, LangChain, HuggingFace. Tránh phải quản lý 2 ecosystem. |
| **Web framework** | FastAPI | Async tốt, type-safe với Pydantic, OpenAPI tự động, dễ demo với Swagger UI. |
| **ORM** | SQLAlchemy 2.x (async) + Alembic | Chuẩn Python, async hỗ trợ tốt, Alembic quản lý migration chuyên nghiệp. |
| **Database** | PostgreSQL 16 + pgvector | 1 DB cho cả metadata, full-text search và vector embedding. Tránh phải đồng bộ giữa 2 hệ thống. Với 200 PDF và vector ~1024 dim, pgvector đủ sức. |
| **Queue** | Celery + Redis | Chuẩn Python, ecosystem tốt, có Flower dashboard cho demo. |
| **Storage** | MinIO (S3-compatible) | Tương thích S3, chuyên cho file lớn, có thể self-host hoặc chuyển sang AWS S3 sau này không cần đổi code. |
| **OCR** | PaddleOCR (primary) + Tesseract (fallback runtime only) | PaddleOCR tốt cho tiếng Việt, hỗ trợ fine-tune. Tesseract chỉ là safety net. |
| **Embedding** | BGE-M3 (1024 dim) | Multilingual, tốt cho tiếng Việt, dimension vừa phải. |
| **LLM** | Ollama local (Qwen2.5 7B hoặc Llama-3.1 8B) | Local, không tốn chi phí API, dễ demo. Adapter pattern để swap provider sau. |
| **Testing** | pytest + pytest-asyncio + HTTPX + Ruff + mypy | Chuẩn Python, nhanh, type-safe. |
| **Deployment** | Docker Compose | Đơn giản cho đồ án, dễ reproduce. |

## Lý do chọn pgvector thay vì Qdrant

**Đã cân nhắc Qdrant** (vector DB riêng). Với dataset ~200 PDF × ~10 pages × ~5 chunks = ~10K vector, lý thuyết pgvector cho kết quả retrieval ngang ngửa Qdrant. **Đây là GIẢ ĐỊNH cần benchmark** với dữ liệu thật của dự án (HNSW `ef_construction`, `m`, `ef_search`) trước khi kết luận; chưa có số liệu thực nghiệm trong repo này.

**pgvector thắng vì**:
- 1 DB duy nhất → backup, migration, audit, RBAC đều ở một chỗ.
- Không phải đồng bộ metadata giữa PostgreSQL và Qdrant.
- Vector + full-text + metadata filter trong cùng 1 SQL query.
- Index HNSW đã ổn định từ pgvector 0.5+.

**Khi nào chuyển sang Qdrant**:
- Dataset > 1M vector.
- Cần filter động phức tạp (geo, multi-tenant).
- Cần replication riêng cho vector layer.

## Hệ quả

### Tích cực
- Stack thống nhất 1 ngôn ngữ (Python).
- Mọi AI/ML đều chạy trong cùng ecosystem với web framework.
- OpenAPI tự động sinh từ FastAPI → FE consume types qua `openapi-typescript`.
- pgvector đơn giản hoá deployment & backup.

### Tiêu cực
- Phải học Alembic + SQLAlchemy 2.x async (nếu team chưa quen).
- Python GIL có thể ảnh hưởng đến throughput CPU-bound (mitigated bằng Celery worker riêng).
- pgvector cần tuning HNSW parameters (ef_construction, m) cho từng dataset.

## Phương án bị loại

| Phương án | Lý do loại |
|---|---|
| **Node.js + Fastify** | Phải duy trì 2 ecosystem (Node cho API + Python cho AI). Vibe coding dễ tạo 2 kiến trúc song song. |
| **Microservice tách riêng (API + AI service + Vector DB)** | Over-engineer cho đồ án 3 tháng. Phức tạp deployment. |
| **MongoDB** | Mất RBAC row-level mạnh của PostgreSQL. Vector search yếu hơn pgvector. |
| **Qdrant riêng** | Phải đồng bộ metadata + vector ở 2 nơi. Chưa có lợi ích rõ ràng ở ~10K vector (cần benchmark). |
| **OpenAI API thay Ollama** | Tốn chi phí, cần internet, không phù hợp demo offline. |

## Tài liệu tham chiếu

- `docs/api/openapi.yaml`
- `docs/domain/rbac-matrix.md`
- `docs/domain/document-lifecycle.md`
- `.cursor/rules/04-database-rag-ocr.mdc`
