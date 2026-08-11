## 2026-08-11T05:59:52Z
<USER_REQUEST>
You are Explorer 3 for Phase B (Document Management & Storage) of the SoHoaTaiLieu_DATN project.

Your working directory is: E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_3

Objective:
Investigate and analyze Celery Async Tasks, PDF Magic Bytes Validation, File Size Enforcement, and Error Handling for Phase B.

Scope & Boundaries:
- READ-ONLY exploration. DO NOT modify any source code.
- Focus on:
  1. Celery worker configuration in `apps/api/app/worker/` and Redis broker settings in `core/config.py`.
  2. Designing background tasks for document processing (status transitions: UPLOADING -> PROCESSING -> READY / FAILED).
  3. PDF validation requirements: checking PDF magic bytes (`%PDF-`), enforcing max file size (50MB), content type verification.
  4. RFC 7807 error responses for invalid files, file size exceeded, scope unauthorized, document not found.

Output Requirements:
- Write your comprehensive analysis and implementation proposal to `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_3\analysis.md`.
- Write your handoff report to `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_b_3\handoff.md` following the Handoff Protocol.
- Send a message to parent (conversation ID: 9f83b9ff-33a4-4ee5-a9e2-f52e7b90ad52) when finished.

Completion Criteria:
- Detailed design of PDF validation service, Celery async task pipeline, file size limits, RFC 7807 error formats, and async task unit tests.

</USER_REQUEST>
