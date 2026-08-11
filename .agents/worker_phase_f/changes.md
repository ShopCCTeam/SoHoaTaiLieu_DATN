# Changes Summary — Phase F Frontend Integration

## Overview
Phase F integration tasks completed with zero regressions. All user rules, API route parameters, dynamic dashboard bindings, live API switches, and quality gates are verified and passing.

## Files Modified

### 1. `apps/web/app/(app)/dashboard/page.tsx`
- **User Rule Compliance**: Replaced colored emoji `👋` on line 74 with Lucide React SVG icon `<Sparkles className="w-5 h-5 text-primary stroke-current inline-block" />`.
- **Dynamic Data Binding**: Replaced static `MOCK_DOCUMENTS` with dynamic `useDocuments()` hook from `@/lib/api/queries`. Added loading spinner state (`isLoading`) and empty state gracefully.

### 2. `apps/web/lib/api/endpoints.ts`
- **Endpoint Route Realignment**:
  - `UPDATE_METADATA`: Updated signature to `(documentId: string, versionId: string) => /documents/${documentId}/versions/${versionId}/metadata`.
  - `TRIGGER_OCR`: Updated signature to `(documentId: string, versionId: string) => /documents/${documentId}/versions/${versionId}/ocr`.
  - `APPROVE`: Updated signatures under `DOCUMENTS` `(documentId: string, versionId: string)` and added `JOBS.APPROVE` `(jobId: string) => /jobs/${jobId}/approve`.
  - `OCR_JOB_STATUS`: Updated signature to `(jobId: string) => /jobs/${jobId}` under `OCR` & `JOBS`.
  - `UPDATE_BLOCK`: Updated signature to `(jobId: string, blockId: string) => /jobs/${jobId}/blocks/${blockId}` under `OCR` / `JOBS` and `(documentId: string, versionId: string, blockId: string)` under `DOCUMENTS`.

### 3. `apps/web/lib/api/queries/index.ts`
- **Client Functions & Param Passing**:
  - Added `useUpdateMetadataMutation`, `useTriggerOCRMutation`, `useApproveVersionMutation`, `useJobStatusQuery`, and `useUpdateBlockMutation`.
  - Exported hooks wrapping `apiClient` using `API_ENDPOINTS` builders with explicit required path parameters (`documentId`, `versionId`, `jobId`, `blockId`).

### 4. `apps/web/lib/api/client.ts`
- **Mock-to-Live API Switch**: Cleaned up URL formatting logic to strip trailing slashes from `BASE_URL` and ensure leading slash on `endpoint` when `NEXT_PUBLIC_API_MODE=live`.

### 5. `apps/web/tests/lib/endpoints.test.ts` (New File)
- **Unit Tests**: Added test suite verifying all builder functions in `API_ENDPOINTS` return exact OpenAPI/FastAPI endpoint path strings with proper path parameter substitution.

## Verification & Test Results
- `pnpm --filter web test`: 31 tests passed (5 test files).
- `pnpm --filter web build`: Next.js production build succeeded with zero errors.
- `uv run pytest`: 240 tests passed (4 skipped).
- `uv run ruff check .`: 0 errors.
- `uv run ruff format --check .`: 97 files cleanly formatted.
- `uv run mypy app`: 0 issues in 62 source files.
