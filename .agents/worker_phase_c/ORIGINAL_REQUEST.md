## 2026-08-11T08:03:48Z

You are Worker Phase C for 'Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên' (SoHoaTaiLieu_DATN).
Your working directory is `E:\SoHoaTaiLieu_DATN\.agents\worker_phase_c`.

## Objectives
Implement Phase C (OCR Pipeline) in `apps/api/`:
1. ORM Models & Alembic Migration:
   - Create `OCRPage` (`apps/api/app/models/ocr_page.py`) and `OCRBlock` (`apps/api/app/models/ocr_block.py`), register in `apps/api/app/models/__init__.py`.
   - Create Alembic migration `0004_ocr_pages_and_blocks.py` creating `ocr_pages` and `ocr_blocks` tables, with composite index `ix_ocr_blocks_version_page` on `(version_id, page_number)`.
2. OCR Engine Service:
   - Implement `OcrEngineService` with Strategy pattern: PaddleOCR primary engine, Tesseract fallback runtime engine.
   - Bounding boxes `[x0, y0, x1, y1]`, confidence score calculation, thresholding (`OCR_CONFIDENCE_THRESHOLD = 0.80`). If confidence < 0.80, set `requires_review = True` and `review_status = 'PENDING'`. Otherwise `requires_review = False` and `review_status = 'APPROVED'`.
3. Celery Pipeline Integration:
   - Integrate OCR processing into `process_document_task` (`apps/api/app/worker/tasks.py`), persisting `OCRPage` and `OCRBlock` instances to DB, updating `DocumentVersion.ocr_status = 'SUCCEEDED'` and setting `DocumentVersion.requires_review = True` if any suspicious blocks exist.
4. OCR Review APIs & Approval Invariants:
   - Implement 3 REST endpoints:
     - `GET /documents/{id}/versions/{vid}/ocr`
     - `PATCH /documents/{id}/versions/{vid}/ocr/blocks/{bid}`
     - `POST /documents/{id}/versions/{vid}/ocr/batch-review`
   - Enforce DB invariant assertion in `approve_document_version` (`apps/api/app/modules/documents/service.py`): verify zero suspicious pending blocks (`requires_review == True` and `review_status == 'PENDING'`) before approving a version.
5. OpenAPI Spec & Tests:
   - Update `docs/api/openapi.yaml` with the 3 OCR review endpoints.
   - Write thorough unit & integration tests (`tests/test_ocr.py`, `tests/test_ocr_api.py`).
   - Run quality checks: `uv run pytest` (>= 80% coverage), `uv run ruff check app tests`, `uv run ruff format --check app tests`, `uv run mypy app`.
