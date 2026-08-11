# Handoff Report — Phase F Frontend Integration

## 1. Observation
- **User Rule Emoji Violation**: Inspected `apps/web/app/(app)/dashboard/page.tsx`. Line 74 contained colored emoji `👋`. Replaced with Lucide React SVG icon `<Sparkles className="w-5 h-5 text-primary stroke-current inline-block" />`. Scanned all source files in `apps/web` with regex pattern `[\uD800-\uDBFF][\uDC00-\uDFFF]` — 0 emojis remaining in project source code.
- **API Endpoint Mismatches**: Fixed path builder signatures in `apps/web/lib/api/endpoints.ts`:
  - `UPDATE_METADATA`: `(documentId: string, versionId: string) => /documents/${documentId}/versions/${versionId}/metadata`
  - `TRIGGER_OCR`: `(documentId: string, versionId: string) => /documents/${documentId}/versions/${versionId}/ocr`
  - `APPROVE`: `(documentId: string, versionId: string) => /documents/${documentId}/versions/${versionId}/approve` and `(jobId: string) => /jobs/${jobId}/approve`
  - `OCR_JOB_STATUS`: `(jobId: string) => /jobs/${jobId}`
  - `UPDATE_BLOCK`: `(documentId: string, versionId: string, blockId: string) => /documents/${documentId}/versions/${versionId}/ocr/blocks/${blockId}` and `(jobId: string, blockId: string) => /jobs/${jobId}/blocks/${blockId}`
- **Dashboard Real Data Binding**: In `apps/web/app/(app)/dashboard/page.tsx`, replaced static `MOCK_DOCUMENTS` with dynamic `useDocuments()` hook data, adding loading and empty table states.
- **Mock-to-Live API Switch Verification**: Enhanced `apps/web/lib/api/client.ts` to sanitize `BASE_URL` and `endpoint` slash formatting when `NEXT_PUBLIC_API_MODE=live` (`http://localhost:8000/api/v1`).
- **Quality Gates Execution**:
  - `pnpm --filter web test`: 5 passed test files, 31 passed tests (0 failed).
  - `pnpm --filter web build`: Next.js 14.2.35 production build succeeded cleanly.
  - `uv run pytest`: 240 passed, 4 skipped (Postgres connection offline fallback).
  - `uv run ruff check .`: Passed, 0 errors.
  - `uv run ruff format --check .`: Passed, 97 files checked.
  - `uv run mypy app`: Success, 0 issues in 62 source files.

## 2. Logic Chain
1. **Rule Compliance**: Project rule 00 & global user rule mandate "không dùng icon màu phải dùng icon SVG". Replacing emoji `👋` with Lucide React `Sparkles` SVG component ensures total visual consistency and compliance.
2. **Endpoint Mismatch Fix**: Backend routers (`apps/api/app/modules/documents/router.py` & `jobs/router.py`) declare nested resources like `/documents/{id}/versions/{vid}/ocr`. Updating `endpoints.ts` and `queries/index.ts` to take required path parameters ensures full contract parity between Next.js frontend and FastAPI backend.
3. **Data Binding**: Binding `dashboard/page.tsx` to `useDocuments()` ensures TanStack Query handles caching, background fetching, loading, and empty list states without breaking on live deployment.
4. **Mock vs Live Routing**: In `client.ts`, checking `NEXT_PUBLIC_API_MODE !== "live"` routes internal mock calls to `/api/...` and live calls to `${NEXT_PUBLIC_API_BASE_URL}...`.

## 3. Caveats
- Backend tests skipping 4 Postgres tests (`test_alembic.py`, `test_models_pg.py`) is expected when local PostgreSQL server is not running during offline test runs.

## 4. Conclusion
Phase F Frontend Integration is 100% completed, fully compliant with project rules, and all quality gates pass without regressions.

## 5. Verification Method
To independently verify the implementation, run:

```bash
# 1. Web Unit Tests
pnpm --filter web test

# 2. Web Production Build & Typecheck
pnpm --filter web build

# 3. Backend Health Gates
cd apps/api
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```
