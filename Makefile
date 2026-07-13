# Makefile — SICOP-MDSJ
# Comandos comunes del monorepo. Uso: make <target>

.PHONY: help dev-infra dev backend-dev frontend-dev build test lint db-migrate db-seed backup-db clean

help:
	@echo "SICOP-MDSJ — comandos disponibles:"
	@echo ""
	@echo "  dev-infra       Levanta postgres + redis (dev)"
	@echo "  dev             Levanta stack completo (backend + frontend + infra)"
	@echo "  backend-dev     Backend con recarga (uvicorn --reload)"
	@echo "  frontend-dev    Frontend con Vite dev server"
	@echo ""
	@echo "  build           Build de imágenes producción"
	@echo "  test            Corre tests backend + frontend"
	@echo "  lint            Ruff (backend) + ESLint (frontend)"
	@echo ""
	@echo "  db-migrate      alembic upgrade head"
	@echo "  db-seed         Carga datos iniciales (roles, umbrales default)"
	@echo "  backup-db       pg_dump manual"
	@echo ""
	@echo "  clean           Limpia artefactos (cache, dist, node_modules)"

# ─── Infra ────────────────────────────────────────────────────────
dev-infra:
	docker compose -f docker-compose.dev.yml up -d postgres redis sqlserver

dev:
	docker compose -f docker-compose.dev.yml up -d backend
	cd frontend && npm run dev

# ─── Backend ──────────────────────────────────────────────────────
backend-dev:
	docker compose -f docker-compose.dev.yml up -d backend

# ─── Frontend ─────────────────────────────────────────────────────
frontend-dev:
	cd frontend && npm run dev

# ─── Build ────────────────────────────────────────────────────────
build:
	docker compose build

# ─── Test ─────────────────────────────────────────────────────────
test:
	cd backend && pytest
	cd frontend && npm test

# ─── Lint ─────────────────────────────────────────────────────────
lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint

# ─── DB ───────────────────────────────────────────────────────────
db-migrate:
	cd backend && alembic upgrade head

db-seed:
	cd backend && python -m app.scripts.seed

backup-db:
	./scripts/backup-postgres.sh

# ─── Clean ────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/dist backend/build
	rm -rf frontend/dist frontend/build
