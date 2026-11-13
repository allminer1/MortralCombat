# NeoMortalSurv API image. Build from the repository root (the image needs model/):
#
#     docker build -f backend/Dockerfile -t neomortalsurv-api .
#
# Runtime dependencies only (uv.lock, --no-dev): no torch, scikit-learn or pandas.
# NOT YET BUILT: the workstation has no Docker (docs/PROGRESS.md). First build is due in
# Phase 5 / CI, where `pip list` in the image must show no torch.
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
