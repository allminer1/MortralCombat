UV := uv run --project backend

.PHONY: dev dev-api dev-web test lint e2e export-model sweep-report

# API on http://127.0.0.1:8000 (docs: /api/docs) and the frontend on http://127.0.0.1:5173,
# both with reload. uvicorn's own access log is off: it would print query strings. The
# app logs one body-free line per request instead (backend/app/core/logging.py).
dev:
	$(MAKE) -j2 dev-api dev-web

dev-api:
	cd backend && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log

dev-web:
	cd frontend && npm run dev

# Backend tests (golden tests included) and frontend unit tests.
test:
	cd backend && uv run pytest -q
	cd frontend && npm test

lint:
	$(UV) ruff check .
	$(UV) ruff format --check .
	cd frontend && npm run lint && npm run typecheck

# Playwright starts the API and the built frontend itself (ports 8010 and 4173).
# Running it against the Docker Compose stack is a Phase 5 task.
e2e:
	cd frontend && npm run e2e

# Regenerates model/ from legacy/. Output is byte-identical on every run.
export-model:
	cd tools && uv run python export_model.py

# Regenerates docs/MODEL_BEHAVIOUR.md.
sweep-report:
	cd tools && uv run python sweep_report.py
