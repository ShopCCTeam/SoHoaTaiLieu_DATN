# infra/docker — Docker Compose & Dockerfile

> **Trạng thái**: scaffold. Sẽ code ở Phase 0 BE.

## Services (dự kiến)

| Service | Image | Port | Mục đích |
|---|---|---|---|
| `postgres` | postgres:16 + pgvector | 5432 | DB chính |
| `redis` | redis:7-alpine | 6379 | Celery broker + cache |
| `minio` | minio/minio:latest | 9000, 9001 | S3-compatible storage |
| `api` | Dockerfile local | 8000 | FastAPI |
| `worker` | Dockerfile local | — | Celery worker |
| `flower` | mher/flower | 5555 | Celery dashboard (dev) |

## Files (sẽ có)

- `infra/docker/Dockerfile.api` — FastAPI image (python:3.11-slim + uv).
- `infra/docker/Dockerfile.worker` — Celery worker image.
- `infra/docker/compose.yaml` — orchestration toàn bộ stack.
- `infra/docker/init-pgvector.sql` — `CREATE EXTENSION vector;`.
- `infra/docker/minio-init.sh` — tạo buckets `documents`, `datasets`, `models`.
