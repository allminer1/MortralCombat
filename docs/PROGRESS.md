# Progress

## Current phase: 0 — Freeze, inventory, gate

**Gate resolved: outcome A** (`docs/DECISIONS.md`). The phase's "done when" is met.
Server code, diff, hashes and inventory are recorded below. Phase 0 is complete apart
from the owner decisions listed under "Open". Next: Phase 1, in a new session.

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
- `tools/gate_cindex.py` run by the owner on the test set: n = 286, 83 events;
  C-index 0.8666 (scaler order) vs 0.7205 (app order). **Outcome A.**
- `docs/ERRATUM_feature_order.md` drafted (not published, not sent).
- Hot-fix prepared on `legacy-streamlit`, commit `b1e65ea`: `preprocess_input` passes
  a named row ordered by `scaler.feature_names_in_`. Checked without starting
  Streamlit: the patched function gives +0.647 / −0.681 / +1.210 and the matching
  survival values for the three gate cases.
- **Hot-fix deployed by the owner on 2026-11-12**, `streamlit.service` restarted at
  15:04:16 UTC. Server `MortalCombat.py` sha256 `47350ccd…fd2e71d` (= commit
  `b1e65ea`); previous file kept on the server as `MortalCombat.py.bak-2026-11-12`
  (sha256 `4b447edd…31388c2` = tag `legacy-server-2026-11`).
  Checked on https://neomortalsurv.net after the restart:

  | case | live site after the fix |
  |---|---|
  | RDS = Yes only, defaults | 0.647 → 78.39 / 58.93 / 19.41 % |
  | NEC = Yes only, defaults | −0.681 → 93.76 / 86.93 / 64.78 % |
  | Article Figure 8 | 1.210 → 65.22 / 39.52 / 5.63 % |

  All three equal the scaler-order expectations. Only the English interface was
  checked; the calculation path is the same for Russian.

### Server inventory (owner ran the commands on 2026-11-12; host name and SSH port left out on purpose)

| Item | Finding |
|---|---|
| OS | Ubuntu, kernel 6.8.0-147, x86_64 |
| Memory | 3.8 GiB total, about 1.9 GiB available, **no swap** |
| Disk `/` | 48 GB, 30 GB free |
| Docker | **not installed** |
| Port 443 | Streamlit itself (TLS with the Let's Encrypt files, see `run.sh`) |
| Port 80 | **nothing listening** — plain `http://` requests are not redirected |
| Web servers | none (no nginx, Caddy or Apache) |
| App service | `/etc/systemd/system/streamlit.service`, `User=root`, `ExecStart=sudo bash …/run.sh`, `Restart=on-failure` |
| Certificates | `certbot.timer` active (runs daily), `/etc/cron.d/certbot` present |
| Other | SSH on a non-standard port; three loopback-only listeners owned by a user process (not identified, not public) |

What this means for Phase 5 (to be planned then, nothing changed now):

- Docker has to be installed on the server before the compose stack can run. Memory
  is enough for Caddy + API (ONNX, no torch); with no swap, add the `db` container
  (Phase 6) only after checking headroom.
- Nothing competes for port 80, and only Streamlit holds 443. For the staging
  subdomain Caddy cannot share 443 with Streamlit on the same IP: either Caddy takes
  80/443 and reverse-proxies the main domain to Streamlit moved to a local port
  (`--server.port 8501`, no TLS flags), or staging runs on another port. The first is
  the cleaner cutover and gives the http→https redirect the site lacks today.
- Once Caddy handles TLS, certbot must be switched off for this domain so that two
  ACME clients do not both renew it.
- `TODO(owner)`: how does the renewed certificate reach Streamlit today? Streamlit
  reads the files at start; unless a certbot deploy hook restarts the service, the
  site would keep serving the old certificate until the next restart. To check:
  `ls /etc/letsencrypt/renewal-hooks/deploy` and
  `grep -i hook /etc/letsencrypt/renewal/neomortalsurv.net.conf`.
- The app runs as root. The rebuild's containers run as non-root (spec Section 9).

### Open

1. **Owner decides** on informing co-authors / journal and on any notice on the site
   (`docs/ERRATUM_feature_order.md`). The site shows no notice about the change.
2. `legacy/` on `rebuild` still holds the GitHub copy of `MortalCombat.py`. Owner to
   decide whether it is replaced by the server copy (labels for spec 7.5 come from
   the server version either way).
3. `TODO(clinical-review)` / `TODO(owner)` items in `docs/ERRATUM_feature_order.md`:
   all wording, affected period, who is informed.

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
  history). On 2026-11-12 the owner pushed `rebuild`, `legacy-streamlit` and the
  tags `legacy-server-2026-11`, `legacy-hotfix-2026-11-12` to the public `github`
  repository (owner's decision to publish everything, erratum draft included).
  `legacy-streamlit` was also published to `origin` (`VLBWSurv`) by GitHub Desktop
  by mistake; owner to decide whether to delete it there. Pushes need the owner's
  token; this workstation has no stored GitHub login for command-line git.
- Patient-level files live in `../PythonProject/` and `../kids.dta`, outside the
  repository. They were not opened.
- Workstation lacks `node`/`npx`, `uv`, `docker`, `gh`. Needed from Phase 1 (`uv`),
  Phase 3 (Node; the Playwright MCP cannot start without it) and Phase 5 (Docker).
- No `Makefile` yet (see `docs/DECISIONS.md`).
- `tools/legacy_model.py` is a gate-only harness; retire it in Phase 1.
