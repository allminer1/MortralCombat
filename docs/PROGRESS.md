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

  The server copy has the same three hashes (computed on the copy the owner
  downloaded, not on the server itself).
- **Server code imported**: branch `legacy-streamlit` (commit `4faeef9`), tag
  `legacy-server-2026-11`. Source: the owner's copy of `/home/AuE/MortralCombat`
  (`~/Downloads/MortralCombat`). `myenv/` and `.idea/` not imported.
  Diff server vs `github/main` (`git diff main legacy-streamlit`):
  - `MortalCombat.py`: BOH label "Chorioamnionitis" → "Bad obestric history" (typo
    is on the server), RU "Хориоамнионит" → "Отягощенный акушерский анамнез";
    sidebar instructions rewritten (initial vs dynamic assessment, input rules,
    interpretation, timepoints day 7 and 28). **No change to `FEATURES`, the network,
    preprocessing or the survival lookup** — the server builds the input vector in
    app order (line 86), exactly like the GitHub copy.
  - `run.sh` (new): Streamlit serves HTTPS itself on port 443 with the Let's Encrypt
    certificate for `neomortalsurv.net`; no reverse proxy in that script.
  - `requirements.txt`: identical.
  - The server checkout is at `d8d88ed` (one commit behind GitHub) with uncommitted
    edits, so the server's wording is newer than GitHub's but GitHub's
    confirmed-diagnosis paragraph (commit `2eb2f3e`) is not on the server.
- `tools/gate_regression.py`: 6 / 6 checks pass (two Section 3.2 cases and Figure 8,
  both orderings). Legacy nearest-row lookup and the step-function lookup give the
  same values at days 7, 28 and 100.
- `tools/gate_cindex.py` written; smoke-tested on random synthetic data only.
- Gate evidence written to `docs/DECISIONS.md`. Outcome still pending.

### Open — blocks the end of Phase 0

1. **Owner runs the C-index check** and pastes the output:
   `/opt/anaconda3/bin/python3 tools/gate_cindex.py`
   (default input: `../PythonProject/MortalityKidsTest.csv`; expected n = 286).
2. `legacy/` on `rebuild` still holds the GitHub copy of `MortalCombat.py`. Owner to
   decide whether it is replaced by the server copy (labels for spec 7.5 come from
   the server version either way).
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

- Deployment fact for Phase 5: Streamlit itself holds port 443 (see `run.sh` on
  `legacy-streamlit`); the inventory should confirm what, if anything, holds port 80
  and how the certificate is renewed.
- Remotes: `github` (canonical) and `origin` (`VLBWSurv`, unrelated one-commit
  history). Nothing has been pushed.
- Patient-level files live in `../PythonProject/` and `../kids.dta`, outside the
  repository. They were not opened.
- Workstation lacks `node`/`npx`, `uv`, `docker`, `gh`. Needed from Phase 1 (`uv`),
  Phase 3 (Node; the Playwright MCP cannot start without it) and Phase 5 (Docker).
- No `Makefile` yet (see `docs/DECISIONS.md`).
- `tools/legacy_model.py` is a gate-only harness; retire it in Phase 1.
