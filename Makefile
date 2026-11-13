UV := uv run --project backend

.PHONY: dev test lint e2e export-model sweep-report

# API on http://127.0.0.1:8000 with reload (docs: /api/docs). The frontend joins in Phase 3.
# uvicorn's own access log is off: it would print query strings. The app logs one
# body-free line per request instead (backend/app/core/logging.py).
dev:
	cd backend && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log

test:
	cd backend && uv run pytest -q

lint:
	$(UV) ruff check .
	$(UV) ruff format --check .

e2e:
	@echo "make e2e: Playwright arrives in Phase 3 (docs/REBUILD_SPEC.md)"; exit 1

# Regenerates model/ from legacy/. Output is byte-identical on every run.
export-model:
	cd tools && uv run python export_model.py

# Regenerates docs/MODEL_BEHAVIOUR.md.
sweep-report:
	cd tools && uv run python sweep_report.py
