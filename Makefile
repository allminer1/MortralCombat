UV := uv run --project backend

.PHONY: dev test lint e2e export-model sweep-report

dev:
	@echo "make dev: backend arrives in Phase 2, frontend in Phase 3 (docs/REBUILD_SPEC.md)"; exit 1

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
