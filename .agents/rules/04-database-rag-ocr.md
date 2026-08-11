# Database, RAG Pipeline & OCR Pipeline

## PostgreSQL Conventions
- **Naming**: snake_case cho table & column. Plural cho table (`documents`, `document_versions`).
- **Primary key**: UUID v7 hoặc bigint identity. Không dùng auto-increment smallint.
- **Timestamp**: luôn có `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ` (trigger auto-update).
- **Soft delete**: cột `deleted_at TIMESTAMPTZ NULL` thay vì `DELETE`.
- **Foreign key**: luôn khai báo, có `ON DELETE` rõ ràng.
- **Migration**: chỉ tạo qua Alembic. Không sửa migration đã chạy — tạo migration mới.

## pgvector (Đã chốt — Không dùng Qdrant trong MVP)
- **Extension**: `CREATE EXTENSION IF NOT EXISTS vector;`
- **Cột vector**: `vector(1024)` cho BGE-M3. Index bằng **HNSW** (`<=>` cosine similarity).
- **Combined search**: full-text (tsvector + GIN) UNION pgvector → rerank.
- **Metadata filter**: bắt buộc filter `scope` và `deleted_at IS NULL` TRƯỚC KHI vector search.

## RAG Pipeline (LangChain + Ollama + pgvector)
- **Chunking**: RecursiveCharacterTextSplitter, chunk_size=800, chunk_overlap=150.
- **Embedding**: BGE-M3 (1024 dim) — model nằm trong `model_versions.is_active = true`.
- **Vector store**: pgvector (dùng chung PostgreSQL).
- **Retrieval**: tsvector UNION pgvector → rerank bằng cross-encoder → top-K=5.
- **LLM**: Ollama local (Qwen2.5 hoặc Llama-3.1 8B instruct) qua `LLMProvider` adapter.
- **Citation**: tuân thủ `docs/domain/citation-spec.md` (`document_id, document_version_id, title, page_number, chunk_id, quote, score, bbox`).
- **Safety**: khi retrieval score < 0.6 hoặc top-K rỗng → `has_sufficient_evidence=false`, **KHÔNG** tạo citation giả.

## OCR Pipeline

### Inference (Production — Celery worker)
- **Engine**: PaddleOCR (primary) với model `model_versions.is_active = true`.
- **Flow**: load PDF từ MinIO → preprocess → PaddleOCR detect+recognize → lưu `ocr_blocks`.
- **Review trigger**: nếu `confidence < threshold` (mặc định 0.9) → set `requires_review=true`.
- **Approval**: Version APPROVED khi `requires_review=false` HOẶC mọi block cần review đều có `review_status ∈ {APPROVED, CORRECTED}`.

### Training (Offline — Makefile)
- **Engine**: PaddleOCR Vietnamese recognizer fine-tune bằng dữ liệu riêng.
- **Train/val/test split**: **theo tài liệu** (document-level), KHÔNG random theo trang/dòng → tránh data leakage.
- **Metrics bắt buộc**: CER (Character Error Rate), WER (Word Error Rate), processing_time_ms/page, accuracy %.
- **Tesseract**: CHỈ là fallback runtime khi PaddleOCR fail. KHÔNG dùng để đánh giá model fine-tune.
- **Model Card**: Mỗi model phải có `MODEL_CARD.md`.

### Training commands
```bash
make data-audit       # Quét data/raw, thống kê
make data-validate    # Validate format, checksum
make ocr-baseline     # Chạy pretrained model, đo baseline metrics
make ocr-train        # Fine-tune recognizer
make ocr-eval         # So sánh baseline vs fine-tuned
```
