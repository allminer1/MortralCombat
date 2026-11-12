# Progress

## Current phase: 0 — Freeze, inventory, gate (NOT finished)

Last session: 2026-11-12.

### Done

- Branch `rebuild` created from `main`. Legacy files moved to `legacy/`, `.idea/`
  removed from git, `.gitignore` (with a deny-list for tabular data files),
  `CLAUDE.md`, `README.md`, `docs/` added.
- Artifact sha256, identical in `main`, in `legacy/` after the move, and in the
  owner's `PythonProject/` folder:

  | file | sha256 |
  |---|---|
  | `survival_model.pth` | `257272b6e17f6870d15c23ff5104437ee8a9421584b66b6dd8415ed2edd41fd2` |
  | `scaler1.pkl` | `8d2555e654183f7afdfb87b07b271362fcaddd221a528679f1ba9709926d1918` |
  | `baseline_hazard.csv` | `3f06ba6cf50709de656755ba88168852d8c63befb6b44fd8d80b97ee6d019f35` |

  Server hashes: **not compared yet** (server copy not provided).
- `tools/gate_regression.py`: 6 / 6 checks pass (two Section 3.2 cases and Figure 8,
  both orderings). Legacy nearest-row lookup and the step-function lookup give the
  same values at days 7, 28 and 100.
- `tools/gate_cindex.py` written; smoke-tested on random synthetic data only.
- Gate evidence written to `docs/DECISIONS.md`. Outcome still pending.

### Open — blocks the end of Phase 0

1. **Owner runs the C-index check** and pastes the output:
   `/opt/anaconda3/bin/python3 tools/gate_cindex.py`
   (default input: `../PythonProject/MortalityKidsTest.csv`; expected n = 286).
2. **Server code** → `legacy-streamlit` branch + tag, diff against `github/main`,
   server sha256 of the three artifacts. Owner copies it; nobody connects to the
   server from this workstation.
3. **Gate outcome** A / B / C in `docs/DECISIONS.md`.
4. If A: `docs/ERRATUM_feature_order.md` (draft, `TODO(clinical-review)`) and the
   hot-fix patch for the Streamlit app (prepared on `legacy-streamlit`; owner deploys).
5. **Server inventory** (spec Section 9 commands), owner runs and pastes.

### Open — owner items, defaults in force

| Item | Status |
|---|---|
| Training script / notebook | `PythonProject/hh.py` found; owner not sure it is the one |
| First go-live date of the calculator (for the erratum) | unknown |
| Licence | default "All rights reserved" notice in `README.md` |
| Repository rename (`neomortalsurv`) | not done |
| Hot-fix of the live app, informing co-authors | owner's decision after the gate |
| Spec Section 11 items 3–12 | untouched, defaults apply |

### Notes for the next session

- Known differences GitHub copy vs. the probable server copy (`PythonProject/ref.py`,
  unconfirmed): BOH label "Bad obstetric history" instead of "Chorioamnionitis";
  `ref.py` lacks the instruction paragraph about confirmed diagnoses. Both use the
  app order. To be replaced by the real diff once the server copy arrives.
- Remotes: `github` (canonical) and `origin` (`VLBWSurv`, unrelated one-commit
  history). Nothing has been pushed.
- Patient-level files live in `../PythonProject/` and `../kids.dta`, outside the
  repository. They were not opened.
- Workstation lacks `node`/`npx`, `uv`, `docker`, `gh`. Needed from Phase 1 (`uv`),
  Phase 3 (Node; the Playwright MCP cannot start without it) and Phase 5 (Docker).
- No `Makefile` yet (see `docs/DECISIONS.md`).
- `tools/legacy_model.py` is a gate-only harness; retire it in Phase 1.
