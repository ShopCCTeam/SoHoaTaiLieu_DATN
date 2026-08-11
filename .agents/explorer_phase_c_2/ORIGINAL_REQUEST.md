## 2026-08-11T06:29:10Z
<USER_REQUEST>
You are Explorer 2 for Phase C (OCR Pipeline) of the SoHoaTaiLieu_DATN project.

Your working directory is: E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_c_2

Objective:
Investigate and analyze Database Models, Alembic Migrations, and Storage representation for Phase C OCR results.

Scope & Boundaries:
- READ-ONLY exploration.
- Focus on:
  1. Designing ORM models for `ocr_pages` and `ocr_blocks` tables (or `document_version_ocr` relationship) in `apps/api/app/models/`.
  2. Fields: `id`, `version_id`, `page_number`, `block_index`, `text_content`, `confidence`, `bbox` (JSONB `[x0, y0, x1, y1]`), `requires_review` (bool), `review_status` (`PENDING`, `APPROVED`, `REJECTED`, `CORRECTED`), `edited_text`.
  3. Alembic migration script design for Phase C.
  4. DB indexes on `(version_id, page_number)` for fast retrieval.

Output Requirements:
- Write comprehensive analysis to `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_c_2\analysis.md`.
- Write handoff report to `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_c_2\handoff.md`.
- Send message to parent (conversation ID: 9f83b9ff-33a4-4ee5-a9e2-f52e7b90ad52) when finished.

</USER_REQUEST>
