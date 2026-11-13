# NeoMortalSurv

Web calculator that estimates survival of very-low-birth-weight infants in the NICU
with a published DeepSurv model (doi:10.3389/fped.2026.1801840). Live at
https://neomortalsurv.net. We are rebuilding it from Streamlit into FastAPI + React.

## Read first

- `docs/REBUILD_SPEC.md` — the full plan, phases and acceptance criteria.
- `docs/PROGRESS.md` — where the last session stopped. Update it before you finish.
- `docs/DECISIONS.md` — choices already made. Add to it; do not silently reverse it.

## Stack

- Backend: Python, FastAPI, Pydantic v2, onnxruntime, NumPy; `uv`, `ruff`, `pytest`.
- Frontend: React, TypeScript, Vite, Tailwind, shadcn/ui, react-i18next.
- Accounts phase only: PostgreSQL, SQLAlchemy 2, Alembic.
- Infra: Docker Compose, Caddy, GitHub Actions.

## Commands

Keep these Makefile targets working and add new ones here when you create them.

- `make dev` — backend + frontend with reload (stub until Phases 2–3)
- `make test` — backend tests, including golden tests
- `make lint` — ruff + frontend lint + type-check
- `make e2e` — Playwright against the compose stack (stub until Phase 3)
- `make export-model` — regenerate `model/` from `legacy/` (needs `tools/` env)
- `make sweep-report` — regenerate `docs/MODEL_BEHAVIOUR.md` (needs `tools/` env)

## Rules that are not negotiable

1. **The model is frozen.** Never edit, retrain, re-export with changes, or "improve"
   anything in `model/` or `legacy/`. `make export-model` must be reproducible.
2. **Feature order lives in one place:** `model/feature_spec.json`. Inputs are named
   fields everywhere. Never build a positional array by hand, never retype the order,
   ranges, means or scales anywhere else.
3. **The feature-order gate (spec Section 3) comes before any inference code.**
4. **Golden tests are the definition of correct.** If one fails, the code is wrong.
   Never loosen a tolerance or regenerate golden data to make a test pass.
5. **Clinical data:** never log request bodies, never add analytics or third-party
   scripts, fonts or CDNs, never add a patient-name or free-text notes field.
6. **Clinical wording is not yours to finalise.** Draft it, mark it
   `TODO(clinical-review)`, list it in `docs/PROGRESS.md`.
7. **No risk categories, colour-coded verdicts or treatment advice** in the UI.
8. **All UI text goes through i18n** (`en`, `ru`, `kk`). No hard-coded strings.
9. **Patient-level data files are never opened, printed, committed or uploaded.** If a
   check needs them, write a script that prints only summary numbers; the owner runs it.
10. **Production is off limits** unless the owner asks in this session: no SSH, no
    `deploy.sh`, no DNS changes. Secrets never go into git.

## How to work

- One phase per session. Plan first, get approval, then implement.
- If the spec is ambiguous or an item says `TODO(owner)`: ask, or use the stated
  default and record it in `docs/PROGRESS.md`. Do not invent clinical facts, ranges or
  numbers.
- Check current library documentation before using an API you are not sure about.
- Small commits, conventional messages (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- Frontend work: use the `frontend-design` skill for visual decisions, and look at the
  result in a real browser (Playwright MCP) at 375, 768 and 1366 px before saying it
  is done.
- A task is done when `make lint` and `make test` pass, the phase's acceptance checks
  in the spec pass, and `docs/PROGRESS.md` is updated.
