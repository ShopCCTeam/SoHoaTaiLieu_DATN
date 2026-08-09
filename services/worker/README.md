# services/worker — Celery Worker

> **Trạng thái**: scaffold. Sẽ code ở Phase 1 BE.

## Trách nhiệm

- OCR pipeline: PDF → render → preprocess → PaddleOCR → lưu `ocr_blocks`.
- Embedding pipeline: text → chunk → BGE-M3 → lưu `embeddings`.
- Indexing pipeline: embedding → pgvector insert/update.

## Tính chất bắt buộc

- **Idempotent**: chạy 2 lần với cùng `idempotency_key` → kết quả giống nhau.
- **Retry**: tối đa 3 lần với backoff (60s / 300s / 1800s).
- **Lưu state vào `jobs` table**, không phải memory.
- **Cập nhật `progress` mỗi 5–10%** để FE poll biết tiến độ.

## Ref

- `.cursor/rules/04-database-rag-ocr.mdc` (section OCR & RAG pipeline).
- `.cursor/rules/08-governance.mdc` (idempotency + logging).
