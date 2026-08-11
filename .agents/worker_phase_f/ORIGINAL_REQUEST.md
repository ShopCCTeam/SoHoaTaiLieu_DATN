## 2026-08-11T09:14:11Z

<USER_REQUEST>
You are Worker for Phase F (Frontend Integration) in SoHoaTaiLieu_DATN.

Your working directory is: `E:\SoHoaTaiLieu_DATN\.agents\worker_phase_f`
Identity: Archetype `teamwork_preview_worker`, Role: Full-Stack / Frontend Engineer

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task Scope & Requirements for Phase F:
1. **Fix User Rule Violation**:
   - Inspect `apps/web/app/(app)/dashboard/page.tsx`. Line 74 contains a colored emoji `👋`.
   - REPLACE IT with a Lucide React SVG icon component (e.g. `<Sparkles className="w-5 h-5 text-primary" />` or `<Hand className="..." />`). NO colored emoji icons anywhere in `apps/web`.

2. **Fix API Endpoint Path Mismatches**:
   - Inspect `apps/web/lib/api/endpoints.ts` and `apps/web/lib/api/` versus FastAPI backend routes (`apps/api/app/modules/`) and `docs/api/openapi.yaml`.
   - Update `endpoints.ts` to match actual backend routes:
     - `UPDATE_METADATA`: `/documents/{documentId}/versions/{versionId}/metadata`
     - `TRIGGER_OCR`: `/documents/{documentId}/versions/{versionId}/ocr`
     - `APPROVE`: `/jobs/{jobId}/approve`
     - `OCR_JOB_STATUS`: `/jobs/{jobId}`
     - `UPDATE_BLOCK`: `/jobs/{jobId}/blocks/{blockId}`
   - Ensure all client functions in `apps/web/lib/api/` pass required path parameters (e.g., `documentId`, `versionId`, `jobId`).

3. **Dashboard Real Data Binding**:
   - In `apps/web/app/(app)/dashboard/page.tsx`, replace static `MOCK_DOCUMENTS` with dynamic `useDocuments()` hook data (or fallback to empty list gracefully when API returns empty).

4. **Verify Mock-to-Live API Switch**:
   - Verify `apps/web/lib/api/client.ts` correctly targets `NEXT_PUBLIC_API_MODE=live` endpoint (`http://localhost:8000/api/v1`).

5. **Quality Gates & Tests**:
   - Run `pnpm --filter web test` (ensure all tests pass).
   - Run `pnpm --filter web build` (ensure clean production build without TypeScript or ESLint errors).
   - Also verify backend health gates remain 100% passing: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy app`.

6. **Documentation & Handoff**:
   - Record progress in `.agents/worker_phase_f/progress.md`.
   - Write `changes.md` and `handoff.md` in `.agents/worker_phase_f/`.
   - Send completion message to parent.
</USER_REQUEST>
