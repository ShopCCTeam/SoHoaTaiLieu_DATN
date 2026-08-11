## 2026-08-11T08:16:31Z
You are Explorer 3 Phase D (Replacement) for 'Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên'.
Your working directory is `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_d_3_gen2`.

Analyze Search API, RBAC Filtering & Celery Indexing Task for Phase D in `apps/api/`:
1. Search REST API Endpoints: `POST /search` or `GET /search` with `query`, `top_k`, `document_ids`, `scope` filtering (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`).
2. OpenAPI Spec: Check `docs/api/openapi.yaml` for search schemas (`SearchQuery`, `SearchResultItem`, `SearchResponse`) and missing path definitions.
3. Celery Task: `index_document_chunks_task(version_id)` triggered automatically after OCR completion (`DocumentVersion.ocr_status == 'SUCCEEDED'`).
4. RBAC Scope Enforcement: Users can only search chunks from documents within their allowed scopes (`PUBLIC` for students, `STUDENT_AFFAIRS` for staff, `INTERNAL` for admin).

Write `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_d_3_gen2\analysis.md` and `handoff.md`, then send a message back to parent.
