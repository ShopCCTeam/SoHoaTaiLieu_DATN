# Architecture Decision Records (ADR)

Format: theo [MADR](https://adr.github.io/madr/). Mỗi ADR ghi ngắn gọn **bối cảnh → quyết định → hệ quả**; nếu sau này đổi, ghi ADR mới thay vì sửa cũ.

---

## ADR-001: Job queue cho OCR worker

**Trạng thái:** Accepted  
**Ngày:** 2026-08-09  
**Bối cảnh:** Hệ thống cần job nền xử lý OCR (vài phút → vài chục phút mỗi file), retry khi fail, persist state, schedule.  
**Quyết định:** Chọn **Celery + Redis** làm job queue mặc định.  
**Lý do:**
- Hệ sinh thái trưởng thành, retry/acks/chord/canvas đầy đủ.
- Beat scheduler phục vụ backup/cleanup định kỳ.
- Nhiều tài liệu tham khảo cho FastAPI + Celery + pgvector.
**Phương án bị bác:** RQ (đơn giản nhưng yếu hơn về retry/dlq), ARQ (async-native nhưng ít tài liệu).  
**Hệ quả:** Thêm service `redis` + `worker` trong docker-compose; thêm `celery[redis]` vào `apps/api/pyproject.toml`.

## ADR-002: Stack OCR

**Trạng thái:** Accepted  
**Ngày:** 2026-08-09  
**Bối cảnh:** OCR cần fine-tune recognizer trên văn bản hành chính tiếng Việt in (PDF scan, ảnh).  
**Quyết định:** **PaddleOCR** (PaddlePaddle) với pretrained checkpoint, fine-tune recognizer.  
**Lý do:**
- Hỗ trợ tốt tiếng Việt ngay từ pretrained; pipeline detector + recognizer rõ ràng.
- Có cộng đồng lớn, tài liệu fine-tune phong phú.
- Hiệu năng inference tốt cả trên CPU lẫn GPU.
**Phương án bị bác:** VietOCR (nhỏ hơn, ít multimodal), docTR (PyTorch nhưng pipeline OCR-VN ít tài liệu), Surya (tiềm năng nhưng còn non).  
**Hệ quả:** `services/ocr-training/` dùng PaddlePaddle; Dockerfile tách `worker-ocr` chạy inference, image training đặt riêng; `OCR_MODEL_PATH` cấu hình qua env.

## ADR-003: LLM Provider

**Trạng thái:** Accepted  
**Ngày:** 2026-08-09  
**Bối cảnh:** Hệ thống RAG cần LLM sinh câu trả lời từ context.  
**Quyết thái:** **Ollama (cục bộ)** làm provider mặc định, có adapter OpenAI-compatible cho cloud.  
**Lý do:**
- Dữ liệu nội bộ (Công tác sinh viên), không muốn rò rỉ qua API cloud.
- Ollama chạy Qwen2.5 / Vistral / Llama 3.1 trên máy local.
- Adaptive đổi qua OpenAI/Anthropic khi cần qua adapter.
**Hệ quả:** `LLM_PROVIDER=ollama`, `LLM_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=qwen2.5:7b-instruct`; `langchain.chat_models.ChatOpenAI` dùng base_url OpenAI-compatible.

## ADR-004: Embedding

**Trạng thái:** Proposed  
**Ngày:** 2026-08-09 (chốt khi vào Phase 7)  
**Bối cảnh:** Cần embedding đa ngôn ngữ, tốt cho tiếng Việt, có thể chạy cục bộ.  
**Phương án dự kiến:** **BGE-M3** (BAAI) — 8K context, đa ngôn ngữ, chạy qua sentence-transformers hoặc Ollama.  
**Lý do:** Phổ biến, benchmark MTEB cao, hỗ trợ tiếng Việt trong nhóm ngôn ngữ Đông Á.  
**Hệ quả:** Vector dim ~1024; cấu hình `EMBEDDING_MODEL=BAAI/bge-m3`; pgvector index HNSW.

## ADR-005: Cài Agent Skills

**Trạng thái:** Accepted  
**Ngày:** 2026-08-09  
**Bối cảnh:** Muốn tận dụng các Agent Skill từ AutoSkill (https://github.com/ECNU-ICALK/AutoSkill) để hỗ trợ vibe-coding.  
**Quyết định:** Cài vào `.skills/` ở gốc dự án (project-specific), gồm 27 skill (xem `.skills/README.md`).  
**Lý do:**
- Auto-loaded bởi Cursor Agent Skills.
- Project-specific nên không phát tán ra môi trường khác.
- Dễ quản lý phiên bản trong Git.
**Hệ quả:** Script `install_skills.ps1` để tái cài; entry `.skills/` đã được track trong Git (trừ cache).

## ADR-006: Vector store

**Trạng thái:** Accepted  
**Ngày:** 2026-08-09  
**Bối cảnh:** Cần lưu embedding + metadata + vector search kết hợp full-text.  
**Quyết định:** **pgvector** (trong cùng Postgres), kết hợp `tsvector` cho full-text.  
**Lý do:**
- Đơn giản hóa stack (chỉ một DB).
- Hỗ trợ hybrid query SQL + vector trong cùng transaction.
- Permission filter áp dụng ngay trong SQL.
**Phương án bị bác:** Qdrant/Chroma (thêm 1 service, đồng bộ với Postgres phức tạp hơn).  
**Hệ quả:** Docker image `pgvector/pgvector:pg16`; indexes HNSW + GIN tsvector.

## ADR-007: Migrations

**Trạng thái:** Accepted  
**Bối cảnh:** Quản lý schema Postgres.  
**Quyết định:** **Alembic** (chuẩn de-facto của SQLAlchemy).  
**Hệ quả:** Mỗi migration toggle được; CI chạy `alembic upgrade head` ở test; production dùng `alembic upgrade` riêng.

## ADR-008: RBAC

**Trạng thái:** Accepted  
**Bối cảnh:** Phân quyền 3 vai trò admin/staff/student + scope-based filtering.  
**Quyết định:** **JWT (access + refresh)** + FastAPI dependency `require_role + require_scope`.  
**Lý do:** stateless, dễ tích hợp với Next.js frontend (HTTP-only cookie hoặc localStorage).  
**Hệ quả:** Table `users`, `roles`, `user_roles`, `audit_logs`; `app/core/security.py` chứa helpers.

## ADR-009: OCR dataset split

**Trạng thái:** Accepted  
**Bối cảnh:** Tránh leakage giữa train/val/test trong OCR fine-tune.  
**Quyết định:** **Chia theo `document_id` hoặc `template_group`** (70/15/15), KHÔNG chia theo từng dòng.  
**Lý do:** Cùng một văn bản nhiều dòng giống nhau → leak nặng nếu split ngẫu nhiên.  
**Hệ quả:** `data/manifests/ocr_v1.csv` có cột `split` đã khóa; `scripts/split.py` ghi manifest checksum.

## ADR-010: Frontend Mock trước

**Trạng thái:** Accepted  
**Bối cảnh:** Giai đoạn đầu chưa có backend, FE cần chạy được để làm việc song song.  
**Quyết định:** FE dùng **MSW (Mock Service Worker)** + flag `NEXT_PUBLIC_API_MODE=mock|live`.  
**Lý do:** Không tốn backend infra; khi BE ready, chỉ cần đổi flag.  
**Hệ quả:** `lib/mocks/` chứa fixtures + handlers; CI chạy E2E với mock.

## ADR-011: Object storage

**Trạng thái:** Accepted  
**Bối cảnh:** Lưu file PDF/ảnh gốc từ upload.  
**Quyết định:** **MinIO** (S3-compatible) trong dev + prod.  
**Lý do:** Tương thích S3 → dễ chuyển sang AWS S3 sau này.  
**Hệ quả:** Adapter `app/services/storage.py` đóng gói, không để logic b leak ra ngoài.

## ADR-012: Chat pipeline

**Trạng thái:** Accepted  
**Bối cảnh:** Hỏi đáp có trích dẫn.  
**Quyết định:** **LangChain LCEL** (không dùng Agent tự trị trong MVP).  
**Lý do:** Dễ test, kiểm soát prompt, debug từng bước.  
**Hệ quả:** `services/rag/pipeline.py` định nghĩa chain: `normalize → perm_check → retrieve → rerank → build_context → prompt → llm → parse_citations`.
