# docs/runbooks — Operational Guides

> Thư mục này chứa hướng dẫn vận hành cho production / staging.

## Sẽ có (khi Phase BE ready)

- `01-deploy.md` — cách deploy FastAPI + Celery + Postgres lên server.
- `02-backup.md` — chiến lược backup PostgreSQL + MinIO.
- `03-incident-ocr-failure.md` — xử lý khi OCR job fail liên tục.
- `04-reindex.md` — cách reindex vector khi đổi embedding model.
- `05-rollback-model.md` — cách rollback model OCR về version trước.
- `06-rate-limit.md` — điều chỉnh rate limit khi traffic tăng.

## Cấu trúc mỗi runbook

1. **Trigger**: khi nào cần chạy runbook này.
2. **Pre-check**: cần verify gì trước.
3. **Steps**: từng bước cụ thể, có command.
4. **Verify**: cách check thành công.
5. **Rollback**: nếu fail, làm gì để revert.
