# Makefile — Workspace convenience commands
#
# Quy ước:
# - FE: apps/web (Next.js)
# - API: apps/api (FastAPI) — khi có code
# - Worker: services/worker (Celery) — khi có code
# - OCR training: services/ocr-training — khi có code

.PHONY: help install dev build test lint typecheck check format clean \
        api-install api-test api-lint api-typecheck api-migrate api-run api-worker \
        fe-install fe-dev fe-build fe-test fe-lint fe-typecheck fe-test-e2e \
        docker-up docker-down docker-logs \
        data-audit data-validate ocr-baseline ocr-train ocr-eval

# Default
help:
	@echo "Workspace commands:"
	@echo "  install       pnpm install ở root"
	@echo "  dev           Chạy FE dev server"
	@echo "  build         Build FE production"
	@echo "  test          Chạy FE unit test"
	@echo "  lint          ESLint FE"
	@echo "  typecheck     tsc --noEmit"
	@echo "  check         lint + typecheck + test"
	@echo "  format        Prettier write"
	@echo "  api-*         FastAPI commands (cần apps/api có code)"
	@echo "  fe-*          Frontend commands"
	@echo "  docker-*      Docker Compose (cần infra/docker/compose.yaml)"
	@echo "  data-*        OCR training commands (cần services/ocr-training)"

# -------------------- Root --------------------
install:
	pnpm install

dev:
	pnpm dev

build:
	pnpm build

test:
	pnpm test

lint:
	pnpm lint

typecheck:
	pnpm typecheck

check:
	pnpm check

format:
	pnpm format

clean:
	pnpm -r exec rm -rf .next dist build node_modules/.cache

# -------------------- Frontend --------------------
fe-install:
	cd apps/web && pnpm install --frozen-lockfile

fe-dev:
	cd apps/web && pnpm dev

fe-build:
	cd apps/web && pnpm build

fe-test:
	cd apps/web && pnpm test

fe-lint:
	cd apps/web && pnpm lint

fe-typecheck:
	cd apps/web && pnpm typecheck

fe-test-e2e:
	cd apps/web && pnpm test:e2e

# -------------------- Backend (sau khi có apps/api) --------------------
api-install:
	cd apps/api && uv sync --frozen

api-test:
	cd apps/api && uv run pytest

api-lint:
	cd apps/api && uv run ruff check . && uv run ruff format --check .

api-typecheck:
	cd apps/api && uv run mypy app

api-migrate:
	cd apps/api && uv run alembic upgrade head

api-run:
	cd apps/api && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

api-worker:
	cd services/worker && uv run celery -A app.workers.celery_app worker --loglevel=info

# -------------------- Docker --------------------
docker-up:
	cd infra/docker && docker compose up -d

docker-down:
	cd infra/docker && docker compose down

docker-logs:
	cd infra/docker && docker compose logs -f

# -------------------- OCR Training (sau khi có services/ocr-training) --------------------
data-audit:
	cd services/ocr-training && uv run python scripts/data_audit.py

data-validate:
	cd services/ocr-training && uv run python scripts/data_validate.py

ocr-baseline:
	cd services/ocr-training && uv run python scripts/run_baseline.py

ocr-train:
	cd services/ocr-training && uv run python scripts/train.py

ocr-eval:
	cd services/ocr-training && uv run python scripts/eval.py
