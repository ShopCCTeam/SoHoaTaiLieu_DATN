# Makefile gốc — lệnh tiện cho local dev (Unix-style; Windows dùng WSL hoặc gọi trực tiếp).
# Windows PowerShell user: dùng `pnpm api:dev` thay cho `make api-shell`.

DC := docker compose -f infra/docker/docker-compose.yml

.PHONY: help up down logs ps restart db-shell api-shell minio-shell seed test lint typecheck check

help:
	@echo "Available targets:"
	@echo "  up         - Start Postgres + Redis + MinIO + API"
	@echo "  down       - Stop stack + remove containers (giữ volumes)"
	@echo "  logs       - Tail logs của tất cả services"
	@echo "  db-shell   - Bash vào Postgres container"
	@echo "  api-shell  - Bash vào API container"
	@echo "  minio-shell- MinIO client shell"
	@echo "  seed       - Seed 3 demo users (admin/staff/student)"
	@echo "  test       - Run pytest (BE)"
	@echo "  lint       - Run ruff"
	@echo "  typecheck  - Run mypy"
	@echo "  check      - Lint + typecheck + test"

up:
	$(DC) up -d --build
	@echo "Stack lên. Đợi ~10s cho Postgres healthcheck xong rồi chạy: make seed"

down:
	$(DC) down

logs:
	$(DC) logs -f

ps:
	$(DC) ps

restart:
	$(DC) restart

db-shell:
	$(DC) exec postgres psql -U $${POSTGRES_USER:-ctsv_app} -d $${POSTGRES_DB:-ctsv}

api-shell:
	$(DC) exec api /bin/bash

minio-shell:
	$(DC) exec minio /bin/bash

seed:
	$(DC) exec api uv run python -m app.modules.auth.seed

test:
	cd apps/api && uv run pytest

lint:
	cd apps/api && uv run ruff check app tests

typecheck:
	cd apps/api && uv run mypy app

check: lint typecheck test
	@echo "All BE checks passed."