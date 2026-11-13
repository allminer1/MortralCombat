UV := uv run --project backend

.PHONY: dev dev-api dev-web test test-accounts lint e2e e2e-accounts e2e-local build export-model sweep-report

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

# Accounts tests against a throwaway PostgreSQL in Docker (synthetic data only).
TEST_DB := postgresql://test:test@127.0.0.1:54329/test
test-accounts:
	-docker rm -f nms-test-db >/dev/null 2>&1
	docker run -d --name nms-test-db -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test \
		-p 127.0.0.1:54329:5432 postgres:17-alpine >/dev/null
	until docker exec nms-test-db pg_isready -U test -q; do sleep 1; done; sleep 1
	cd backend && TEST_DATABASE_URL=$(TEST_DB) uv run pytest -q; status=$$?; \
		docker rm -f nms-test-db >/dev/null; exit $$status

lint:
	$(UV) ruff check .
	$(UV) ruff format --check .
	cd frontend && npm run lint && npm run typecheck

COMPOSE_E2E := SITE_NEW=:8080 docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.e2e.yml

# Browser tests against the Docker Compose stack (same images as production, plain HTTP
# on 127.0.0.1:8080). Needs a running Docker (on this workstation: `colima start`).
e2e:
	$(COMPOSE_E2E) up -d --build --wait
	cd frontend && E2E_BASE_URL=http://127.0.0.1:8080 npm run e2e; status=$$?; \
		cd .. && $(COMPOSE_E2E) down; exit $$status

# Browser tests of accounts and history: the compose stack with PostgreSQL and the
# feature switched on, two throwaway users with random passwords, synthetic data only.
COMPOSE_ACC := SITE_NEW=:8080 POSTGRES_PASSWORD=e2e-only-$$PPID docker compose -p neomortalsurv-acc \
	-f deploy/docker-compose.yml -f deploy/docker-compose.accounts.yml \
	-f deploy/docker-compose.e2e.yml -f deploy/docker-compose.e2e-accounts.yml
e2e-accounts:
	$(COMPOSE_ACC) down -v >/dev/null 2>&1 || true
	$(COMPOSE_ACC) build
	$(COMPOSE_ACC) up -d --wait db
	$(COMPOSE_ACC) run --rm api python -m app.cli migrate
	$(COMPOSE_ACC) up -d --wait
	export E2E_PASSWORD_A=$$(openssl rand -hex 12) E2E_PASSWORD_B=$$(openssl rand -hex 12); \
		printf '%s\n' "$$E2E_PASSWORD_A" | $(COMPOSE_ACC) exec -T api python -m app.cli create-user a@example.test --password-stdin && \
		printf '%s\n' "$$E2E_PASSWORD_B" | $(COMPOSE_ACC) exec -T api python -m app.cli create-user b@example.test --password-stdin && \
		cd frontend && E2E_BASE_URL=http://127.0.0.1:8080 E2E_ACCOUNTS=1 npx playwright test accounts; status=$$?; \
		cd .. && $(COMPOSE_ACC) down -v; exit $$status

# Browser tests without Docker: Playwright starts the API and two builds of the frontend
# itself (ports 8010, 4173, 4174). The only run that covers the Kazakh flag.
e2e-local:
	cd frontend && npm run e2e

# Build both production images.
build:
	$(COMPOSE_E2E) build

# Regenerates model/ from legacy/. Output is byte-identical on every run.
export-model:
	cd tools && uv run python export_model.py

# Regenerates docs/MODEL_BEHAVIOUR.md.
sweep-report:
	cd tools && uv run python sweep_report.py
