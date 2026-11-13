# NeoMortalSurv API image. Build from the repository root (the image needs model/):
#
#     docker build -f backend/Dockerfile -t neomortalsurv-api .
#
# Runtime dependencies only (uv.lock, --no-dev): no torch, scikit-learn or pandas.
# Built and checked on 2026-11-13: 22 packages, no torch (docs/PROGRESS.md).
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /srv/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
RUN useradd --system --uid 10001 --no-create-home api
WORKDIR /srv/backend
COPY --from=build /srv/backend/.venv ./.venv
COPY backend/app ./app
# Database migrations, used only when accounts are enabled (python -m app.cli migrate).
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini
COPY model /srv/model
ENV PATH="/srv/backend/.venv/bin:$PATH" \
    MODEL_DIR=/srv/model \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
USER api
EXPOSE 8000
# One process: the rate limiter keeps its counters in memory. No uvicorn access log
# (it would print query strings); the app writes its own body-free access line.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
