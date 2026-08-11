## 2026-08-11T09:21:25Z
<USER_REQUEST>
You are Reviewer 2 for Phase F (Frontend Integration) gate verification in SoHoaTaiLieu_DATN.

Your working directory is: `E:\SoHoaTaiLieu_DATN\.agents\reviewer_phase_f_2`
Identity: Archetype `teamwork_preview_reviewer`, Role: Frontend Integration & Route Reviewer

Objective:
1. Audit all 12 web routes in `apps/web`:
   - `/`, `/login`, `/dashboard`, `/documents`, `/documents/[id]`, `/documents/upload`, `/ocr-review`, `/ocr-review/[jobId]`, `/search`, `/chat`, `/admin/users`, `/admin/system`
   - Verify TanStack Query API hooks connect properly in live mode.
   - Verify type safety between `@ctsv/contracts` OpenAPI types and React components.
2. Run verification commands:
   - `pnpm --filter web test`
   - `pnpm --filter web build`
3. Write your review report in `E:\SoHoaTaiLieu_DATN\.agents\reviewer_phase_f_2\review.md` and `handoff.md`. Send completion message with your verdict (APPROVE / VETO).
</USER_REQUEST>
