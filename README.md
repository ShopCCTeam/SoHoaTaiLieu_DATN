# Hệ thống Số hoá và Quản lý Tài liệu Công tác Sinh viên

> Đồ án tốt nghiệp về số hoá, kiểm duyệt và truy xuất tài liệu Công tác Sinh viên bằng OCR, RAG và LangChain.

## Trạng thái hiện tại

Hệ thống đã có **backend FastAPI chạy được**, worker Celery, lưu trữ MinIO, PostgreSQL với pgvector, Redis, OCR native và RAG nội bộ qua Ollama. Frontend Next.js vẫn hỗ trợ cả **live mode** và **mock mode** nhằm phục vụ demo/UI test; mock route không được xem là bằng chứng backend production.

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| Frontend Next.js | Có implementation | F0–F6; live mode gọi FastAPI, mock mode phục vụ UI/demo. |
| Auth và RBAC | Có implementation | JWT access token, refresh rotation, backend scope check. |
| Upload và OCR | Có implementation | PDF 300 DPI; JPEG/PNG một trang; PaddleOCR primary, Tesseract fallback. |
| OCR review | Có implementation | Ảnh PNG private, proxy qua API sau kiểm tra RBAC. |
| Search và chat RAG | Có implementation | Hybrid retrieval, guardrail cosine 0.6, citation, Ollama nội bộ. |
| Worker và indexing | Có implementation | Celery xử lý OCR/indexing; job chỉ thành công sau indexing. |
| OCR training offline | Scaffold | `services/ocr-training/` chưa phải pipeline fine-tune hoàn chỉnh. |

## Kiến trúc

```text
Người dùng
    │
    ▼
Next.js 14 (apps/web)
    │ HTTPS / Bearer access token
    ▼
FastAPI (apps/api)
    ├── PostgreSQL 16 + pgvector
    ├── MinIO (raw upload và PNG review private)
    ├── Redis (Celery broker/result backend)
    └── Celery worker (apps/api/app/worker)
            ├── PaddleOCR primary / Tesseract fallback
            ├── chunking và BGE-M3 embedding
            └── Ollama nội bộ: bge-m3 + qwen2.5:7b
```

## Stack đã chốt

| Layer | Công nghệ |
|---|---|
| Frontend | Next.js 14 App Router, TypeScript strict, Tailwind, Zustand, TanStack Query |
| Backend | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy async, Alembic |
| Database | PostgreSQL 16, pgvector, full-text search |
| Queue và storage | Celery, Redis, MinIO |
| OCR | PaddleOCR primary, Tesseract chỉ fallback runtime |
| RAG | LangChain, BGE-M3 1024 chiều, Ollama/Qwen2.5 nội bộ |
| Tooling | pnpm, uv, Ruff, mypy, pytest, Playwright, Docker Compose |

## Cấu trúc repository

```text
SoHoaTaiLieu_DATN/
├── apps/
│   ├── web/                         # Next.js UI, test và mock route demo
│   └── api/                         # FastAPI, models, services, worker, Alembic, pytest
├── packages/
│   └── contracts/                   # TypeScript sinh từ docs/api/openapi.yaml
├── infra/
│   └── docker/
│       ├── Dockerfile.api
│       └── docker-compose.yml       # PostgreSQL, Redis, MinIO, Ollama, API, worker
├── services/
│   ├── worker/                      # Tài liệu scaffold cũ; worker thật nằm trong apps/api/app/worker
│   └── ocr-training/                # Scaffold huấn luyện offline
├── docs/
│   ├── api/                         # OpenAPI contract và ghi chú API
│   ├── domain/                      # RBAC, lifecycle, citation spec
│   ├── adr/                         # Architecture Decision Records
│   └── PROGRESS.md                  # Nhật ký implementation và evidence
├── data/                            # Không commit dữ liệu thật
├── models/                          # Không commit model/checkpoint
├── AGENTS.md                        # Entry point cho agent
└── MANUS.md                         # Quy tắc thao tác chi tiết
```

## Chạy và kiểm chứng

Các lệnh dưới đây không chạy migration hay tạo dữ liệu seed. Hãy đọc `AGENTS.md`, `MANUS.md` và `.env.example` trước khi khởi động môi trường lần đầu; không đưa `.env` hoặc tài liệu thật vào repository.

```bash
# Contract và frontend
pnpm openapi:lint
pnpm --filter @ctsv/contracts generate
pnpm --filter web lint
pnpm --filter web typecheck
pnpm --filter web test
pnpm --filter web build

# Backend
cd apps/api
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app
uv run pytest -q

# Tổng hợp workspace
cd ../..
pnpm check
```

Compose chuẩn ở `infra/docker/docker-compose.yml`. Dùng `docker compose` hoặc `docker-compose` tuỳ binary đã cài, và chỉ khởi động/rebuild service khi đã được phê duyệt:

```bash
docker-compose --env-file .env.example -f infra/docker/docker-compose.yml config
```

## Contract, bảo mật và dữ liệu

`docs/api/openapi.yaml` là **single source of truth**. Mọi thay đổi endpoint/schema phải cập nhật contract trước, tái sinh `packages/contracts`, sau đó mới đổi backend/frontend.

Backend là security boundary: scope/RBAC phải được kiểm tra trước storage, database, vector search hoặc retrieval. Ảnh review OCR không dùng URL MinIO public. Chat chỉ tạo citation từ evidence đã qua guardrail cosine `0.6`; khi thiếu evidence, trả no-answer và không tạo citation giả.

Không commit password, token, `.env*`, PDF/ảnh/tài liệu thật, OCR text thật, dữ liệu training hay model artifact. Dùng fixture synthetic cho test và smoke test.

## Tài liệu quan trọng

| Tài liệu | Mục đích |
|---|---|
| `MANUS.md` | Quy tắc dự án tổng hợp, bắt buộc đọc trước thay đổi. |
| `AGENTS.md` | Quy tắc thao tác, stack, quality gate. |
| `docs/PROGRESS.md` | Mốc đã triển khai và giới hạn evidence. |
| `docs/api/openapi.yaml` | Contract API chuẩn. |
| `docs/domain/rbac-matrix.md` | Ma trận quyền và scope. |
| `docs/domain/document-lifecycle.md` | State machine document/version/job/index. |
| `docs/domain/citation-spec.md` | Schema và quy tắc citation RAG. |

## Bản quyền

Đồ án tốt nghiệp, sử dụng phi thương mại.
