# Hệ Thống Số Hoá & Quản Lý Tài Liệu Công Tác Sinh Viên

> Đồ án tốt nghiệp: **"Xây dựng hệ thống số hoá và quản lý tài liệu Công tác sinh viên ứng dụng OCR, RAG và LangChain"**

## 🏛 Kiến trúc

```
                         Người dùng (Web Browser)
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │   Next.js 14 (apps/web)  │  ← Frontend (đã xong F0–F6)
                    └──────────┬───────────────┘
                               │ HTTPS / JWT
                               ▼
                    ┌──────────────────────────┐
                    │   FastAPI  (apps/api)    │  ← Backend (đang scaffold)
                    │  REST API + RBAC + Auth  │
                    └────┬─────┬─────────┬─────┘
                         │     │         │
              ┌──────────┘     │         └─────────────┐
              ▼                ▼                       ▼
      ┌──────────────┐  ┌──────────────┐         ┌──────────────┐
      │ PostgreSQL 16│  │    MinIO     │         │    Redis     │
      │ + pgvector   │  │ (S3 file)   │         │  (broker)    │
      └──────────────┘  └──────────────┘         └──────┬───────┘
                                                       │
                                                       ▼
                                              ┌──────────────────┐
                                              │  Celery Worker   │
                                              │  - OCR pipeline  │
                                              │  - Embedding     │
                                              │  - Indexing      │
                                              └─────────┬────────┘
                                                        │
                                                        ▼
                                              ┌──────────────────┐
                                              │   Ollama (LLM)   │
                                              │  + BGE-M3 embed  │
                                              └──────────────────┘
```

## 📦 Tech stack (đã chốt)

| Layer | Tech |
|---|---|
| **Frontend** | Next.js 14 App Router · TypeScript Strict · Tailwind · Zustand · TanStack Query |
| **Backend** | Python 3.11 · FastAPI · Pydantic v2 · SQLAlchemy 2.x · Alembic |
| **Database** | PostgreSQL 16 + pgvector (vector + full-text + metadata) |
| **Queue** | Celery + Redis |
| **Storage** | MinIO (S3-compatible) |
| **OCR** | PaddleOCR (primary) + Tesseract (fallback runtime only) |
| **Embedding** | BGE-M3 multilingual (1024 dim) |
| **LLM** | Ollama local (Qwen2.5 hoặc Llama-3.1 8B) — provider adapter để swap |
| **Tooling** | pnpm · uv · Ruff · mypy · pytest · Playwright · Docker Compose |

## 📂 Cấu trúc repo

```
SoHoaTaiLieu_DATN/
├── apps/
│   ├── web/                    # Next.js Frontend (F0–F6 done)
│   └── api/                    # FastAPI Backend (scaffold — chưa có code)
├── services/
│   ├── worker/                 # Celery worker (scaffold)
│   └── ocr-training/           # OCR training pipeline (offline)
├── packages/
│   └── contracts/              # Shared FE/BE types (scaffold)
├── infra/
│   └── docker/                 # Dockerfile, docker-compose.yaml
├── docs/
│   ├── api/                    # OpenAPI spec, contract notes
│   ├── domain/                 # RBAC matrix, lifecycle, citation spec
│   ├── adr/                    # Architecture Decision Records
│   ├── evaluation/             # OCR training reports
│   └── runbooks/               # Operational guides
├── data/                       # ⚠️ KHÔNG commit dữ liệu thật
├── models/                     # ⚠️ KHÔNG commit model artifact
├── .cursor/rules/              # 8 rule files (xem AGENTS.md)
├── .skills/                    # 27 Agent Skill
├── AGENTS.md
└── README.md                   # file này
```

## 🚀 Cách chạy (hiện tại)

### Frontend (đã chạy được)

```bash
pnpm install
pnpm dev               # http://localhost:3000
pnpm test              # Vitest
pnpm build             # Production build
pnpm lint              # ESLint
```

Tài khoản demo (chỉ chạy mock, **KHÔNG dùng trong production**):
- `admin@example.edu.vn` / `demo_password`
- `staff@example.edu.vn` / `demo_password`
- `student@example.edu.vn` / `demo_password`

### Backend (chưa có code — đang ở phase foundation)

Sẽ hướng dẫn chi tiết sau khi Phase 0 BE được phê duyệt. Theo dõi `docs/PROGRESS.md`.

## 🔐 Quy tắc bảo mật dữ liệu

> **CẢNH BÁO**: Repo này có thể chứa dữ liệu sinh viên thật (PDF, ảnh, transcript).

- **KHÔNG commit** PDF, ảnh trang, ảnh dòng chữ, OCR text, hay transcript của tài liệu thật.
- **KHÔNG commit** model checkpoint, log training, hoặc dữ liệu processed.
- `.gitignore` đã loại trừ: `data/**`, `models/**`, `runs/`, `mlruns/`, `*.pdparams`, `*.safetensors`, `*.ckpt`, `*.onnx`, `*.pth`, `*.pt`, `.env*`.
- Khi cần demo, dùng dữ liệu synthetic ở `data/fixtures/synthetic/` (được commit).

## 🧪 Quality gate (sẽ chạy trong CI)

```bash
# Frontend
pnpm install --frozen-lockfile
pnpm --filter web lint
pnpm --filter web exec tsc --noEmit
pnpm --filter web test
pnpm --filter web build

# Backend (sau khi có code)
cd apps/api
uv sync
ruff check .
ruff format --check .
mypy app
pytest
alembic upgrade head
```

## 📚 Tài liệu quan trọng

| File | Mục đích |
|---|---|
| `AGENTS.md` | Entry point cho AI agent |
| `.cursor/rules/` | 8 rule file cho AI |
| `docs/PROGRESS.md` | Nhật ký tiến độ dự án |
| `docs/api/README.md` | API contract tổng quan |
| `docs/api/openapi.yaml` | OpenAPI spec machine-readable |
| `docs/domain/rbac-matrix.md` | Ma trận phân quyền |
| `docs/domain/document-lifecycle.md` | State machine cho Document/Job/Index |
| `docs/domain/citation-spec.md` | Schema citation RAG |
| `docs/adr/0001-backend-stack.md` | ADR-0001 — chốt stack Python + pgvector |

## 📝 License & bản quyền

Đồ án tốt nghiệp — phi thương mại.
