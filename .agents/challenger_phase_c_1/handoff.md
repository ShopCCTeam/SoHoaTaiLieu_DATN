# Phase C Challenger 1 Empirical Test & Invariant Verification Report

## 1. Observation

Direct code and test observations from `apps/api`:

- **Approval Invariant Assertion (`apps/api/app/modules/documents/service.py:575-606`)**:
  ```python
  if version.ocr_status != "SUCCEEDED":
      raise conflict(detail="Chỉ có thể phê duyệt phiên bản khi OCR thành công (ocr_status == 'SUCCEEDED').")

  pending_suspicious_stmt = select(func.count(OCRBlock.id)).where(
      OCRBlock.version_id == version.id,
      OCRBlock.requires_review == True,
      OCRBlock.review_status == "PENDING",
  )
  pending_suspicious_count = (await session.execute(pending_suspicious_stmt)).scalar_one()

  if pending_suspicious_count > 0:
      raise conflict(
          detail=f"Phiên bản còn {pending_suspicious_count} block OCR nghi ngờ chưa được kiểm tra (requires_review=true). Vui lòng thực hiện OCR review trước khi phê duyệt."
      )
  ```
- **OCR Engine Thresholding (`apps/api/app/services/ocr_engine.py:241-255`)**:
  `OCR_CONFIDENCE_THRESHOLD = 0.80`. When `block.confidence < 0.80`, sets `requires_review = True`, `review_status = "PENDING"`, and `has_warnings = True`.
- **OCR Block Review APIs (`apps/api/app/modules/documents/router.py:359-463`)**:
  - `GET /documents/{id}/versions/{vid}/ocr` with filters (`page`, `requires_review`, `review_status`).
  - `PATCH /documents/{id}/versions/{vid}/ocr/blocks/{bid}` for single block review (`APPROVED`, `CORRECTED`).
  - `POST /documents/{id}/versions/{vid}/ocr/batch-review` for batch review (`accept_all_pending=true`).
- **Authored Test Suite (`apps/api/tests/test_phase_c_challenger1.py`)**:
  Authored 11 comprehensive empirical test cases covering invariants, review APIs, filtering, edge cases, and RBAC.
- **Empirical Execution Command & Output**:
  - Command: `uv run pytest tests/test_phase_c_challenger1.py tests/test_ocr_api.py tests/test_ocr.py`
  - Output: `20 passed in 9.71s`

## 2. Logic Chain

1. **Approval Invariant Stress Testing**:
   - Tested attempting to approve a document version with pending suspicious OCR blocks (`confidence=0.60`, `review_status="PENDING"`). The API returned HTTP `409 Conflict` with code `"CONFLICT"` and message indicating unreviewed suspicious blocks exist (`test_approval_invariant_returns_409_when_pending_suspicious_blocks_exist`).
   - Tested attempting to approve a document version with `ocr_status="PROCESSING"`. The API returned HTTP `409 Conflict` with detail `ocr_status == 'SUCCEEDED'` (`test_approval_invariant_returns_409_when_ocr_not_succeeded`).
   - Tested patching all suspicious blocks to `APPROVED` or `CORRECTED`, which automatically resets `version.requires_review = False`. Subsequent approval succeeded with HTTP `200 OK` and version status `"APPROVED"` (`test_approval_succeeds_only_after_all_suspicious_blocks_reviewed`).

2. **OCR Block Review APIs & Filtering Verification**:
   - Single block review `PATCH` with status `CORRECTED` updated `text_content`, stored `edited_text`, retained `original_text`, and populated `reviewed_by` with the reviewing staff user ID (`test_single_ocr_block_patch_approved_and_corrected`).
   - Batch review `POST` with `accept_all_pending=True` updated 2 pending suspicious blocks to `APPROVED`, reduced `pending_reviews` to 0, and updated `version_requires_review` to `False` (`test_batch_review_ocr_accept_all_pending`).
   - OCR detail `GET` with query params `page=1`, `page=2`, `requires_review=true`, and `review_status=PENDING` correctly filtered blocks matching exact criteria (`test_ocr_detail_page_filtering_and_query_params`).

3. **Edge Cases & Boundary Conditions**:
   - **Zero confidence score (`confidence=0.0`)**: OCR engine service flagged block with `confidence=0.0` as `requires_review=True`, `review_status="PENDING"`, and page `has_warnings=True` (`test_edge_case_zero_confidence_score`).
   - **Empty text content (`text_content=""`)**: Block with empty string text content was persisted and patched to empty text without raising validation or database errors (`test_edge_case_empty_text_content`).
   - **Out-of-bounds bounding boxes (`[x0, y0, x1, y1]`)**: Tested negative coordinates `[-50.0, -20.0, 100.0, 50.0]`, inverted coordinates `[500.0, 700.0, 50.0, 600.0]`, and oversized coordinates `[0.0, 0.0, 99999.0, 99999.0]`. All coordinates were persisted and returned accurately in JSON (`test_edge_case_out_of_bounds_bounding_boxes`).
   - **Non-existent block ID**: Attempting to patch block `non_existent_block_9999` returned HTTP `404 Not Found` with code `"NOT_FOUND"` (`test_edge_case_non_existent_block_id`).
   - **RBAC Protection**: Student user role attempting single patch or batch review returned HTTP `403 Forbidden` (`test_edge_case_student_forbidden_from_ocr_review`).

## 3. Caveats

- Tests for local PostgreSQL native pgvector instance (`test_alembic.py`, `test_models_pg.py`) are automatically skipped when local PostgreSQL daemon on localhost:5432 is offline. All tests execute cleanly against SQLite in-memory DB. No caveats regarding Phase C OCR pipeline functionality.

## 4. Conclusion

Phase C OCR Pipeline implementation is empirically verified and robust:
- Approval invariant strictly blocks document approval (`409 Conflict`) whenever unreviewed suspicious OCR blocks exist.
- Single block review, batch review, and page filtering APIs work as specified in contracts.
- Edge cases (empty text, zero confidence, out-of-bounds bounding boxes, non-existent block IDs, student RBAC restriction) pass all empirical tests without failures.

## 5. Verification Method

To independently verify the empirical test suite:

```bash
cd E:\SoHoaTaiLieu_DATN\apps\api
uv run pytest tests/test_phase_c_challenger1.py tests/test_ocr_api.py tests/test_ocr.py
```

To run the full backend test suite:

```bash
cd E:\SoHoaTaiLieu_DATN\apps\api
uv run pytest
```

Invalidation conditions: Any test failure in `test_phase_c_challenger1.py` or approval failing to return `409 Conflict` when pending suspicious OCR blocks exist.
