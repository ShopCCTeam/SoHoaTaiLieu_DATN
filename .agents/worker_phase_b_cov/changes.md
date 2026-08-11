# Changes Log - Worker Phase B (Coverage Boost)

## Summary of Changes
Added `apps/api/tests/test_coverage_boost.py` containing 16 comprehensive unit test functions to target previously unreached code branches in `documents`, `jobs`, `storage`, and `pdf_validator` modules.

## Files Added / Modified

### 1. `apps/api/tests/test_coverage_boost.py` (New File)
- **Document Service Unit Tests**:
  - `test_get_document_by_id_include_deleted`: Soft-deleted document lookups with `include_deleted=True` vs `include_deleted=False`.
  - `test_update_document_service_all_fields`: Updating document metadata with all schema fields (`title`, `type`, `scope`, `code_number`, `issuing_body`, `effective_from`, `effective_to`, `tags`).
  - `test_create_document_and_idempotency`: Document creation & idempotency key matching vs mismatch handling (409 conflict).
  - `test_create_document_version_and_idempotency`: Version creation & idempotency key matching vs checksum mismatch (409 conflict).
  - `test_update_document_version_metadata_approved_conflict`: Updating metadata of APPROVED versions raising 409 conflict.
  - `test_trigger_version_ocr_and_idempotency`: Version OCR trigger & idempotency matching vs version mismatch.
  - `test_approve_document_version_logic_and_errors`: Version approval invariant checks (`ocr_status != SUCCEEDED`, `requires_review == True`) and prior approved version superseding logic.
- **Document Router Edge Cases**:
  - `test_documents_router_not_found_endpoints`: 404 responses for non-existent document IDs across GET, PATCH, DELETE, version list/upload/detail/metadata/OCR/approve.
  - `test_documents_router_version_not_found_on_existing_doc`: 404 responses for non-existent version IDs on existing document.
- **Jobs Router Edge Cases**:
  - `test_jobs_router_status_and_cancel_edge_cases`: GET job status 404 / 403 forbidden, POST job cancel 404 / 403 forbidden / 409 conflict (finished job) / 200 OK (cancellation of queued job by admin).
- **Storage Service Edge Cases & Fallbacks**:
  - `test_local_storage_service_methods`: Local file upload, download, `FileNotFoundError` on non-existent download, file delete.
  - `test_minio_storage_service_fallbacks`: `MinioStorageService` fallback to `LocalStorageService` when MinIO client throws exception/import error.
  - `test_get_storage_service_production_env`: Factory function instantiating `MinioStorageService` in non-test environment (`APP_ENV=production`).
- **PDF Security & Validator Edge Cases**:
  - `test_pdf_validator_service_class_method`: Classmethod wrapper `PdfValidatorService.validate_upload_file`.
  - `test_pdf_validation_security_edge_cases`: PDF magic bytes missing (415), invalid content-type (415), payload size exceeding 50MB (413), stream chunk size check (413/415).
- **Celery Exception Fallbacks & Dependencies Edge Cases**:
  - `test_celery_task_delay_exception_handling`: `get_idempotency_key` empty header validation (422), `check_document_access` deleted doc (404), Celery `process_document_task.delay` exception handling and logger warning output.

## Quality Metrics & Coverage Report
- **Pytest Coverage**: **91.46%** global line coverage (target >= 82%).
- **Tests Result**: 132 passed, 4 skipped (Postgres DB integration tests skipped on non-Postgres host).
- **Ruff Check**: All checks passed!
- **Ruff Format Check**: 61 files formatted cleanly.
- **Mypy Typecheck**: Success: no issues found in 41 source files.
