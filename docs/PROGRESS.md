# Progress

## Current phase: 6 — Accounts and history — built and tested; OFF in production

Last session: 2026-11-13 (same session as Phases 1–5, at the owner's request).
The Phase 6 code reached the server on 2026-11-13 with the warning deploy (commit
`587f959`), with `ENABLE_ACCOUNTS` unset: accounts are **off** and their endpoints do
not exist on the live site (checked).

### After the phases: clinical review packet (2026-11-13)

`make review-packet` writes `docs/CLINICAL_REVIEW.md` from the translation files: all
144 interface texts in EN / RU / KK side by side with a correction column, nine
questions for the reviewer, the 19 Kazakh clinical terms, and the model-behaviour
tables. A Word and an HTML copy go to `docs/out/` (not committed) for a reviewer who
works in Word or on paper.

**Result (2026-11-13, reported by the owner): the clinical co-authors have no
corrections; English and Russian are approved as they are.** Recorded in
`docs/DECISIONS.md`. No text changed, so nothing needs redeploying. This closes the
`TODO(clinical-review)` items for English and Russian listed under Phases 3, 4 and 6
below, and spec Section 11 item 5 (no tooltip for "bad obstetric history").

Still open after the review:
- Kazakh: unreviewed draft, stays hidden (spec Section 11 item 8).
- `TODO(owner)`: reviewer's name and review date for the record.
- Whether the co-authors want anything done about the model behaviour in Part B
  (odd outputs far from the cohort), and the training ranges (item 3).
- Case comparison of old and new site by a clinical co-author (cases 4–10).
- Erratum decision; server restart; Cloudflare access; uptime check; retiring the old
  app after 2026-12-13; institutional sign-off before accounts can be enabled.

### After the phases: typo fix for the old app (2026-11-13) — applied by the owner

Spec 7.5 asks for the label "Bad obestric history" on the old Streamlit app to be
fixed. Prepared on branch `legacy-streamlit` (commit `c9428af`, tag
`legacy-typo-fix-2026-11-13`): one label changed, nothing else; the file compiles.
The old app now lives on `https://neomortalsurv.net:8444` and is due to be retired
after 2026-12-13, so this is cosmetic. To apply on the server (owner):

    sudo sed -i 's/"BOH": "Bad obestric history"/"BOH": "Bad obstetric history"/' /home/AuE/MortralCombat/MortalCombat.py
    sudo systemctl restart streamlit

Applied by the owner on the server on 2026-11-13 and Streamlit restarted. Checked in
a browser afterwards: `https://neomortalsurv.net:8444` shows "Bad obstetric history"
and the misspelling is gone; the main site was not affected. This closes the
"fix the typo on the live site" item of spec 7.5.

The server file then has sha256 `fdaa47b9…82c6c780` if it was identical to the hot-fix
version before. `legacy/` on the `rebuild` branch is frozen and is not changed.

### After the phases: training-range script (2026-11-13)

`tools/training_ranges.py` is ready for the owner to run on the training file (spec
Section 11 item 3). It first confirms the file is the training set (672 rows, column
means equal the scaler's) and then prints only n, minimum, 1st and 99th percentile and
maximum of the five continuous inputs. Tested on random synthetic data, including the
three refusal cases.

**Run by the owner on 2026-11-13 on `MortalityKidsTrain.csv`** (outside the repository;
Claude did not open it). The script confirmed the file: 672 rows, all 11 column means
match the scaler. Output, summary numbers only:

| input | n | min | 1st pct | 99th pct | max | form accepts |
|---|---|---|---|---|---|---|
| `birth_weight_g` | 672 | 430 | 509.71 | 1498 | 1803 | 400–2000 |
| `apgar_5min` | 672 | 2 | 2 | 8 | 9 | 0–10 |
| `gestational_age_weeks` | 672 | 22 | 23 | 36 | 38 | 20–42 |
| `heart_rate_bpm` | 672 | 36 | 56 | 177 | 188 | 60–200 |
| `spo2_percent` | 672 | 35 | 45 | 96 | 98 | 40–100 |

What the numbers show (facts, no interpretation of their clinical meaning):
- The form accepts values the model never saw: Apgar 0, 1 and 10; gestational age
  20–21 and 39–42 weeks; weight below 430 g and above 1,803 g; heart rate above 188;
  SpO2 above 98. The implausible outputs in `docs/MODEL_BEHAVIOUR.md` (for example
  survival near 0 % at 39–42 weeks) are in these never-seen regions.
- The form **refuses** values that did occur in training: heart rate 36–59 and SpO2
  35–39 (the form's minimums are the old sliders' 60 and 40).
- The training set contains birth weights above 1,500 g (maximum 1,803 g; the 99th
  percentile is 1,498 g), although the article states that infants above 1,500 g were
  excluded. `TODO(owner)`: check with the co-authors; the site's weight warning and the
  About page repeat the article's statement.

**`OUTSIDE_TRAINING_RANGE` warning built and deployed on 2026-11-13.** Owner's
decisions: warn outside min–max; deploy before the co-authors review the new wording.

Deployed by the owner (`git pull`, `deploy/deploy.sh`) at commit `587f959`, which also
brought the Phase 6 code (switched off) and the phone layout fixes to the server.
Checked from outside right after: health ok with unchanged model hashes; `/model`
serves the five training ranges; gestational age 40 returns `OUTSIDE_TRAINING_RANGE`
for that input; Figure 8 still gives 1.210 → 65.22 / 39.52 / 5.63 % with no warning;
`/features` says accounts off and `/auth/me` does not exist (404); the old app still
answers on `:8444`.

- Ranges live in `backend/app/data/training_ranges.json` (not in the frozen `model/`;
  see `docs/DECISIONS.md`) and are served by `GET /api/v1/model` as `training_ranges`.
- `/predict` and saved calculations return the code `OUTSIDE_TRAINING_RANGE` once, plus
  `outside_training_range`: the names of the inputs concerned. The estimate itself is
  unchanged; a warning is never a refusal.
- Result panel: every warning (this one and the weight one) is now also shown in a
  notice above the headline numbers, not only under "Details"; the report shows them
  too. The sentence names each input with its study range.
- Tests: `make test` 78 backend + 21 unit; `make test-accounts` 121; `make e2e` 37;
  `make e2e-accounts` 13; `make e2e-local` 42. `make lint` passes.

Open:
- `TODO(clinical-review)`: the two new texts `warnings.OUTSIDE_TRAINING_RANGE` and
  `warnings.rangeItem` (EN, RU; KK draft). They were written after the co-authors'
  review; both translation files say so, and the review packet lists them as unreviewed.
- (Decided 2026-11-13, built, **not yet deployed**.) The form and API accept heart rate
  from 36 bpm and SpO2 from 35 %, the smallest values in training; two numbers in
  `model/feature_spec.json` changed with the owner's go-ahead, network and hazard
  files byte-identical (`docs/DECISIONS.md`). All suites pass: `make test` 78 + 21,
  `make test-accounts` 121, `make e2e` 37, `make e2e-accounts` 13, `make e2e-local` 42.
  Deploy: `cd ~/neomortalsurv && git pull && sudo deploy/deploy.sh`; `/health` will
  then report the new `feature_spec.json` hash `4af968e1…`.
- (Decided 2026-11-13.) Gestational age outside the training range: keep warning, do
  not refuse.
- `TODO(owner)`: the 1,500 g exclusion statement versus the training maximum of 1,803 g.

    cd tools && uv run python training_ranges.py --train-csv /path/to/training-file.csv

Once the owner pastes the output and says where to warn (min / max, or 1st / 99th
percentile), the ranges go into `model/feature_spec.json` through
`tools/export_model.py`, and the API and the form show the warning. That adds new
warning text, which needs clinical review.

### Done in Phase 6

- Backend (`backend/app/api/accounts.py`, `app/accounts/`, `app/db/`, `app/cli.py`,
  `backend/alembic/`): PostgreSQL through SQLAlchemy 2 / psycopg 3, one Alembic
  migration (`users`, `sessions`, `calculations`), argon2id passwords, server-side
  sessions, CSRF token + same-origin check, idle and absolute session limits, login
  rate limit, saved calculations (server recomputes the outputs), list / open / delete
  / CSV export, admin command line. `GET /api/v1/features` tells the frontend whether
  accounts are on.
- Frontend: `/login`, `/history`, `/history/:id` (same sheet as the print report),
  "Save this calculation" with the optional case code under an up-to-date result,
  sign in / out and History in the header. All of it is absent when the server says
  the feature is off. EN, RU and the hidden KK draft.
- Deployment files: `deploy/docker-compose.accounts.yml` (database not published, used
  only when `ENABLE_ACCOUNTS=true`), `deploy/backup.sh` (dump, verify, 14 days, and
  `--restore`), `deploy.sh` runs the migration when accounts are on.
- `docs/ACCOUNTS.md`: what exists, security properties, how to enable, backup / restore.
- Make targets: `test-accounts` (backend tests with a throwaway PostgreSQL),
  `e2e-accounts` (browser tests against the stack with the database). CI runs both.

### Phase 6 acceptance

| Check | Result |
|---|---|
| Isolation tests pass | pass — backend: another user's item cannot be read, deleted, listed, filtered or exported, a foreign id and a missing id answer identically, `admin` sees nothing extra; browser: second user sees an empty history, "does not exist" at the first user's address, header-only export |
| Backup and restore rehearsed once | done **locally** with synthetic data on 2026-11-13 (`docs/ACCOUNTS.md`); not on the server |
| Feature stays off in production until the owner records the sign-off | off; `deploy/.env.example` ships `ENABLE_ACCOUNTS=false`; no sign-off recorded |

Test counts: `make test` 70 backend (43 database tests skipped without a database) +
21 frontend unit; `make test-accounts` 113 backend; `make e2e` 36; `make e2e-accounts`
13 (7 behaviour + 6 screenshot / layout checks at 375, 768, 1366 px in EN and RU);
`make e2e-local` 41. Screenshots of the new pages reviewed by Claude; found and fixed
there: header and history table too wide on a phone. `make lint` passes.

### Open after Phase 6

1. **Institutional sign-off** (spec Section 8, `TODO(owner)`): blocks enabling.
2. Before enabling on the server: deploy the newer commit there (`git pull`,
   `deploy/deploy.sh`), check memory headroom for the database container, set up the
   backup cron line, decide on the off-server copy, rehearse a restore there.
3. Owner decisions listed at the end of `docs/ACCOUNTS.md` (retention, invite-only).
4. `TODO(clinical-review)`: the new texts under `auth`, `save`, `history` in
   `frontend/src/i18n/*.json`, in particular the case-code warning.
5. Everything still open from Phases 1–5 (below).

## Phase 5 — Deploy and cutover — done on 2026-11-13, with two recorded deviations

The new calculator is live on https://neomortalsurv.net. Last session: 2026-11-13.

### Phase 5 acceptance

| Spec condition | Result |
|---|---|
| Staging subdomain serves the new stack over HTTPS | met in substance — staging ran on `https://neomortalsurv.net:8443`, a port instead of a subdomain (no DNS access; `docs/DECISIONS.md`) |
| Owner signs off the case comparison | **deviation** — cases 1–3 matched on both sites; the owner decided to cut over without the clinical co-author's comparison (`docs/DECISIONS.md`). Cases 4–10 and the co-author's review are still open |
| Main domain switched | done 2026-11-13, verified from outside the server |
| Legacy subdomain live | met in substance — old app on `https://neomortalsurv.net:8444` until at least 2026-12-13 |
| Rollback rehearsed once | done 2026-11-13: main address back to the old app, verified, then cut over again, verified |

Next: nothing is scheduled. Phase 6 (accounts) needs a new session, a plan, and stays
off in production until the institutional sign-off (spec Section 8).

### Done in Phase 5, part A (workstation only)

- Colima 0.10 + Docker 29.5 + compose 5.7 installed with Homebrew (`colima start`
  before `make e2e`; `colima stop` frees the memory).
- **API image built for the first time; closes the open Phase 2 check.** 22 packages,
  no torch / scikit-learn / pandas / pycox; runs as uid 10001; 422 MB.
- `deploy/web.Dockerfile`: Caddy 2 with the built frontend, uid 10002.
- `deploy/Caddyfile`: site address from `.env`; HSTS, `X-Content-Type-Options`,
  `Referrer-Policy`, `X-Frame-Options`, strict CSP (`default-src 'self'`, no inline
  anything, `frame-ancestors 'none'`) with a separate same-origin policy for
  `/api/docs`; gzip / zstd; single-page fallback; long cache for hashed files; access
  log without query strings, client addresses or headers.
- `deploy/docker-compose.yml` (`caddy`, `api`; both read-only root file system, all
  capabilities dropped except port binding for Caddy, memory limits, health check,
  `TRUSTED_PROXY=true`), `docker-compose.legacy.yml` + `legacy.caddy` (old Streamlit
  app as a second site), `docker-compose.e2e.yml` (local test on 127.0.0.1:8080),
  `.env.example`, `deploy.sh` (asks for confirmation; owner runs it).
- `make e2e` now builds the images, starts the compose stack and runs the browser
  tests against it: 35 pass. `make e2e-local` is the previous mode and the only one
  that covers the Kazakh flag: 40 pass. `make build` builds both images.
- New browser checks: no console errors or CSP violations anywhere in the app; the API
  docs page loads only its own files. Found and fixed through them: zod probed
  `new Function`, which the CSP reports (now `jitless`); fonts are never inlined as
  `data:` URLs.
- Checked by hand on the local stack: a request body and a query string sent through
  Caddy appear in neither container's log; the legacy override proxies to a process on
  the host.
- `.github/workflows/ci.yml` written; first run on 2026-11-13 passed (see below).
- `docs/CUTOVER.md`: step-by-step runbook for part B with rollback and the case list.

### Not done / not verified

1. **Everything on the server** (`docs/CUTOVER.md`): DNS, Docker, moving Streamlit to a
   local port, certbot, staging, comparison, cutover, rollback rehearsal.
2. Never tested: real certificates, Streamlit behind Caddy (only a dummy upstream was
   proxied), Streamlit bound to the Docker bridge address, image builds on the server.
3. (Closed 2026-11-13.) The owner pushed `rebuild` (`97d8de2`) to `github`; the CI
   workflow ran for the first time and all three jobs passed (backend, frontend, e2e
   including the compose stack and the image check). The push needed a token with the
   `workflow` permission.
4. Certificate-hook question answered 2026-11-13 (owner ran the check on the server):
   `/etc/letsencrypt/renewal-hooks/deploy` is empty and the renewal file has no hook
   lines. So nothing restarts Streamlit after a renewal; it serves a renewed certificate
   only after its next restart. Nothing to remove in runbook step 5. The server also
   reports "System restart required" and 97 pending updates (2 security).
   Still `TODO(owner)`: seven realistic
   comparison cases (step 6), uptime check, erratum notice, ACME contact e-mail.
5. Carried over: `docs/MODEL_BEHAVIOUR.md` to the co-authors; training ranges;
   clinical review of all wording; Kazakh review.

### Part B log (owner on the server)

- 2026-11-13: branch pushed, CI green. Certificate hooks checked: none.
- 2026-11-13: an attempt to connect from the workstation at the owner's request was
  refused (key not authorised); the owner logs in and Claude reads the terminal panel.
  Read-only so far; nothing on the server has been changed for this project.
- 2026-11-13: the owner cannot log in to Cloudflare (DNS), so staging and legacy use
  ports 8443 / 8444 instead of subdomains (`docs/DECISIONS.md`, `docs/CUTOVER.md`).
  Recovering the Cloudflare account is an open owner item.
- 2026-11-13, runbook steps 1–4 done by the owner (Claude read the terminal panel and
  typed nothing on the server):
  - ufw inactive; Docker 29.9.3 + compose 5.7.1 installed; `docker0` = 172.17.0.1;
    2 GB swap added; repository cloned to `~/neomortalsurv` at `65dc7c3`; images
    built on the server in about 70 s.
  - Streamlit moved to `172.17.0.1:8501` (plain HTTP, CORS and XSRF checks off),
    service now starts after Docker. Backups on the server:
    `run.sh.bak-2026-11-13`, `streamlit.service.bak-2026-11-13`.
  - Stack started with `deploy/deploy.sh`. Checked from outside the server:
    `https://neomortalsurv.net` → old app through Caddy, one calculation run by the
    owner (live connection works); `http://` redirects to `https://`; new certificate
    from Let's Encrypt, valid to 2027-02-11;
    `https://neomortalsurv.net:8443` → new calculator, health ok, artifact hashes equal
    to the repository's, Figure 8 through the API = 1.210 → 65.22 / 39.52 / 5.63 %.
    Ports 8443 is reachable from outside (no panel firewall in the way).
- 2026-11-13, step 5: certbot's timer disabled and its cron file renamed; the old
  certificate files are kept as the fallback for a full undo (deleted in step 9).
- **State now: staging is live.** Old app on the main address, new calculator on
  `:8443`. The three reference cases give the expected numbers through the staging
  API.
- 2026-11-13, step 6 partly: cases 1–3 entered by hand on both sites (browser session
  for the owner) and they match; record in `docs/COMPARISON_2026-11-13.md`.
  **Not yet done:** cases 4–10 from the clinical co-author, phone / ward PC / hospital
  network, printed output, and the sign-off; then step 7 (cutover) and step 8
  (rollback rehearsal).
- The server still reports "System restart required" (kernel, security updates).

- **2026-11-13, step 7: CUTOVER DONE** by the owner, on the owner's decision recorded
  in `docs/DECISIONS.md` (without the co-author's sign-off). Checked from outside the
  server right after: `https://neomortalsurv.net` serves the new calculator (health
  ok, security headers, `/about` opens directly, `http://` redirects, Figure 8 through
  the API = 1.210 → 65.22 / 39.52 / 5.63 %); the old Streamlit app answers on
  `https://neomortalsurv.net:8444`; port 8443 no longer answers. Settings before the
  switch are kept on the server as `deploy/.env.before-cutover`.
- 2026-11-13, step 8: rollback rehearsed by the owner. After the swap back the main
  address showed the Streamlit app and `:8443` the new API; after the second cutover
  the main address shows the new calculator and `:8444` the old app (confirmed from
  outside the server). On the server: `deploy/.env.before-cutover` and
  `deploy/.env.after-cutover`; the active `.env` is the after-cutover one.
- Not yet done: step 9 (retire the old app after 30 days, i.e. not before 2026-12-13;
  includes deleting certbot's old certificate and closing ports 8443 / 8444). Open after cutover: co-author's cases 4–10,
  phone / ward PC / hospital network, printed output, clinical review of all wording.

### Notes for the next session

- Part B needs the owner at the server. Claude can help read command output and adjust
  the files, but runs nothing against production unless asked in that session.
- Phase 6 (accounts) stays off in production until the institutional sign-off
  (spec Section 8).

## Phase 4 — Report, About page, Kazakh — complete, wording awaits review

Session of 2026-11-13.

### Done in Phase 4

- `react-router`: `/` (calculator), `/about`, `/report`; unknown paths go to `/`. Header
  has links to the calculator and About.
- **Report (`/report`)**: "Print report" appears on an up-to-date result. One A4 page
  through print CSS (`@page` A4, 12 mm): date and time of the calculation, the 11
  inputs, three estimates with one decimal, log-risk, model version, warnings, the
  curve, limitations, intended-use line, citation. "Case code" is a blank line to fill
  in by hand; the page has no input of any kind.
- The last inputs and result are kept in memory only (`frontend/src/lib/session.tsx`):
  not in the URL, not in localStorage or sessionStorage. Opening `/report` directly, or
  reloading it, shows "calculate first". Going back to the calculator in the same tab
  restores the form and result.
- **About (`/about`)**: what the model is, cohort, reported performance, intended use,
  limitations, citation. Every number is read from the model card served by
  `GET /api/v1/model`.
- **Kazakh**: `frontend/src/i18n/kk.json`, a full draft. Build flag
  `VITE_ENABLE_KK=true`; without it Kazakh is not in the switch, `?lang=kk` falls back,
  and the Kazakh text is not in the built files at all. Review markers: the file-level
  `_todo_clinical_review` note and `_clinical_terms`, which lists every field label and
  eight further clinical terms, each key prefixed `TODO(clinical-review)`.
- Kazakh numbers use the Russian rules (decimal comma); dates use Kazakh month names
  when the browser has them and Russian ones otherwise.
- Tests: `make test` 65 backend + 19 frontend unit; `make e2e` 39 browser tests in two
  builds (default, and one with the Kazakh flag). `make lint` passes.

### Phase 4 acceptance

| Check | Result |
|---|---|
| Report prints on one A4 page in all languages | pass — PDF rendered by Chromium has exactly 1 page in EN, RU and KK, also with the weight warning shown (EN, RU) |
| `kk` exists behind its flag with review markers | pass — absent from the default build (checked in the built scripts), present and working in the flagged build |
| `/about` numbers match spec Section 1 exactly | pass — 958; 4 centres; January 2021 – May 2025; 672 / 286; 11 predictors; C-index 0.86 (0.81–0.90); AUC 0.95 (0.91–0.98); IBS 0.071 |

Also checked: accessibility scan (axe, WCAG 2.1 A + AA) of report and About in EN, RU
and of the report in KK, zero violations; the nine Kazakh-specific letters, upper and
lower case, are covered by the bundled font in all four weights; nothing is wider than
the screen at 375, 768, 1366 px. Screenshots reviewed by Claude
(`frontend/screenshots/`); **the owner has not looked yet**. Printing was checked as
Chromium PDF output, not on a physical printer or in other browsers.

### Open after Phase 4

1. **`TODO(clinical-review)`**, added in this phase: report labels, all About-page text
   (EN, RU), and the whole Kazakh file. The Kazakh draft was written by Claude, which
   is not a native speaker; abbreviations in it (ЖЖЖ, ТШҚҰ, ТБС, ҚІҚҚ, НЭК) and the
   term for "bad obstetric history" in particular need a clinician.
2. `kk` stays off until the owner confirms the review (spec Section 11 item 8); then
   build with `VITE_ENABLE_KK=true`.
3. Spec 7.5 "fix the typo on the live site" ("Bad obestric history"): not done —
   production is off limits. The rebuild spells it correctly. A patch on
   `legacy-streamlit` can be prepared if the owner wants the old site fixed before
   cutover.
4. Phase 5: the web server must answer `/about` and `/report` with `index.html`
   (single-page app fallback), and the Docker build of the frontend decides the
   Kazakh flag.
5. Still open from earlier phases: `docs/MODEL_BEHAVIOUR.md` to the co-authors;
   training ranges (Section 11 item 3); the API image has never been built.

## Phase 3 — Frontend calculator (EN + RU) — complete, wording awaits review

Session of 2026-11-13.

### Done in Phase 3

- Node 26.13.1 / npm 11.20 installed (Homebrew); Playwright's Chromium downloaded.
- `frontend/`: Vite 8, React 19, TypeScript 7, Tailwind 4, react-hook-form + zod,
  react-i18next, IBM Plex Sans self-hosted through `@fontsource` (Latin, Cyrillic,
  Cyrillic Extended). Versions locked in `frontend/package-lock.json`.
- Calculator page at `/`:
  - field names, types, ranges and units are read from `GET /api/v1/model`; the form
    refuses to work if the server serves other fields than it knows how to lay out;
  - two groups (spec 7.2), empty numeric inputs with steppers (steppers stay disabled
    until a value is typed, so they cannot invent one), unselected No / Yes and II / III
    controls, "Calculate" disabled until all 11 fields are valid, inline validation;
  - result: day 7 and day 28 in whole percent, day 100 secondary; SVG step curve for
    days 0–100, drawn dashed over a hatched area from day 56 with a one-line reason;
    a slider under the curve reads any day (mouse, touch, keyboard); the curve as a
    table; details with one decimal, log-risk, model version, warnings; limitations box;
  - if an input is changed after a calculation the result is dimmed and marked as out
    of date until "Calculate" is pressed again (not in the spec; added so that the
    numbers on screen can never silently belong to other inputs);
  - no risk categories or verdict colours; Reset; no Print yet (Phase 4);
  - header language switch EN / RU, remembered in localStorage, first visit follows
    the browser, `?lang=` overrides; footer with intended-use notice, model version,
    citation with DOI, link to `/api/docs`.
- `make dev` starts API and frontend; `make lint` adds oxlint and `tsc`; `make test`
  adds 13 frontend unit tests (78 in total); `make e2e` runs 16 Playwright tests.

### Phase 3 acceptance

| Check | Result |
|---|---|
| e2e: Figure 8 reads 65 % / 40 % / 6 % and 1.210 in details | pass (EN; RU reads 65 % / 1,210) |
| Empty form cannot be submitted | pass — button disabled, Enter sends no request, also with 10 of 11 fields or an out-of-range value |
| Screenshots at 375, 768, 1366 px reviewed | done by Claude in both languages (`frontend/screenshots/`, regenerated by `make e2e`, not committed); **owner has not looked yet** |
| Accessibility check, no serious issues | pass — axe-core, WCAG 2.1 A + AA, zero violations in EN and RU, in three states (empty, validation error, result with table) |

Also tested: no request leaves the page's own host; nothing is wider than the screen
at any of the three widths.

### Open after Phase 3

1. **`TODO(clinical-review)` — all interface wording, EN and RU**
   (`frontend/src/i18n/en.json`, `ru.json`; both files carry the marker):
   group titles and help texts, field labels, the sentence under the curve about day
   56, the weight warning, the four limitation sentences, the intended-use line.
   Russian field labels are carried over from the legacy app; everything else in
   Russian is a new draft.
2. Owner defaults in force (spec Section 11): no tooltip for "bad obstetric history"
   (item 5), whole-percent headline (6), curve de-emphasised from day 56 (7), no
   contact shown (12).
3. `make e2e` does not yet run against the Docker Compose stack (Phase 5).
4. Deviations from the stack named in `CLAUDE.md` / the spec, see `docs/DECISIONS.md`:
   no shadcn/ui components; oxlint instead of ESLint; the built-in browser and
   Playwright were used instead of the Playwright MCP.
5. Kazakh letters: the Cyrillic Extended font files are bundled, but rendering was not
   checked — there is no Kazakh text until Phase 4.

### Notes for Phase 4

- No router yet: `/about` and `/report` need one (`react-router`), and the report needs
  the last inputs and result, which live in `Calculator.tsx` state.
- `kk` goes into `src/i18n/index.ts` (`LANGUAGES`) behind a build flag.
- After a calculation focus moves to the result heading; e2e tests that use the
  keyboard must wait for that (see `e2e/calculator.spec.ts`).

## Phase 2 — Backend API — complete apart from the image build

Session of 2026-11-13.

### Done in Phase 2

- `backend/` gained FastAPI 0.162, Pydantic 2.14, uvicorn 0.54 and `swagger-ui-bundle`
  (exact versions in `backend/uv.lock`); tests use `httpx2`.
- Endpoints under `/api/v1` (`backend/app/api/v1.py`, app factory in `app/main.py`):
  `GET /health`, `GET /model`, `POST /predict`. OpenAPI at `/api/openapi.json`, Swagger
  UI at `/api/docs` served from local files (checked in a browser: only requests to
  the API host itself).
- The `/predict` request model is generated from `model/feature_spec.json`
  (`app/schemas/predict.py`): 11 required fields, unknown fields rejected, strict
  integers and strict JSON booleans.
- 422 responses are `{"errors": [{"field", "code", …}]}` with codes `missing`,
  `unknown_field`, `not_integer`, `not_boolean`, `out_of_range` (+ `min`, `max`),
  `not_allowed` (+ `allowed`), `invalid_json`, `invalid_body`. No English sentences, no
  echo of submitted values. 404 / 405 / 429 use the same shape (`not_found`,
  `method_not_allowed`, `rate_limited`).
- Warning `WEIGHT_ABOVE_COHORT` above 1,500 g. `OUTSIDE_TRAINING_RANGE` not built
  (training ranges still missing, spec Section 11 item 3).
- Rate limit on `/predict`: 60 / minute per client address, in-process sliding window
  (`app/core/ratelimit.py`), 429 with `Retry-After`. Settings by environment variable:
  `RATE_LIMIT_PER_MINUTE` (0 = off), `TRUSTED_PROXY`, `MODEL_DIR`, `LOG_LEVEL`.
- Access log (`app/core/logging.py`): one line per request with method, path, status,
  latency, model version, warning codes, error codes. The middleware never reads the
  body, query string, headers or client address.
- `make dev` runs the API with reload on `127.0.0.1:8000`.
- `backend/Dockerfile` and `.dockerignore` written (non-root, runtime dependencies
  only). **Not built — no Docker on the workstation.**
- Tests: 65 pass (`make test`); `make lint` passes.

### Phase 2 acceptance

| Check | Result |
|---|---|
| Golden tests pass through the HTTP layer | pass — 527 cases, max log-risk diff 4.4e-6, max S(t) diff 1.0e-6 |
| 422 cases tested for every field | pass — missing, null, wrong type for all 11; below / above range for the 5 integer fields; disallowed values for the grade; unknown field |
| A test proves request bodies do not reach the logs | pass — valid, invalid and malformed requests, all loggers and stdout / stderr captured |
| Image has no torch | pass — lock file tested, and the image itself built and inspected in Phase 5 (22 packages, no torch) |

### Open after Phase 2

1. **Build the image once Docker is available** (Phase 5 or CI) and confirm
   `pip list` in it shows no torch. Until then this acceptance item is not closed.
2. Phase 5: when Caddy is in front, set `TRUSTED_PROXY=true`, otherwise every user
   shares one rate-limit bucket (Caddy's address). Without Caddy leave it off.
3. Phase 5: the strict CSP (`default-src 'self'`) will block the inline script of the
   Swagger UI page at `/api/docs`; that path needs its own policy or a hash.
4. Defaults in force, owner may override: warn (not reject) above 1,500 g; same-origin
   only, no CORS; booleans must be JSON `true` / `false`.

### Notes for Phase 3

- The frontend gets names, types, ranges and units from `GET /api/v1/model`
  (`feature_spec.features`), and translates error and warning codes itself.
- `backend/app/api/v1.py` must not get `from __future__ import annotations`: FastAPI
  then no longer recognises the generated request model as the JSON body.
- The preview pane of the Claude desktop app could not start `make dev` from this
  folder (sandbox, "getcwd: Operation not permitted"); the server was started from
  the shell instead and opened in the built-in browser.

## Phase 1 — Model package — complete, report awaits the owner

Session of 2026-11-13.

### Done in Phase 1

- `uv` 0.13.7 installed on the workstation (Homebrew).
- `tools/` has its own `uv` project (`tools/pyproject.toml`, `tools/uv.lock`) pinned to
  the versions in `legacy/requirements.txt`. The Phase 0 gate scripts moved to
  `tools/gate/` (archived, see `docs/DECISIONS.md`); gate regression still 6 / 6.
- `make export-model` (`tools/export_model.py`) writes `model/`. Two runs give
  byte-identical files:

  | file | sha256 |
  |---|---|
  | `deepsurv.onnx` | `0673cc55b19029b5fa9d7febb1f86a3abbc80127d8fac048a8cc02cee136af9f` |
  | `feature_spec.json` | `fd9081e51659161ff80bd0e5389193218c6099da72ad948b3a13aa6f369a6dad` |
  | `baseline_hazard.json` | `96dd4de5312f99c913ce49445c40f0e7dae38c8e51a384724060aec7316e769a` |
  | `model_card.json` | `ae6a99093f72762c6b8e107ba95b0e02019b0a19bf3bb7808911a1fd8ee4cbbe` |

  ONNX vs PyTorch at export, 2,000 random vectors, batched and single-row:
  max |diff| 2.9e-6. `legacy/` untouched (hashes in `model_card.json` equal Phase 0).
- `tools/make_golden.py` wrote `backend/tests/golden/golden.json`: 527 cases (3 anchors,
  all-min, all-max, 22 single-field toggles, 500 random; seed 20261113), from the
  PyTorch network through the original scaler with a named DataFrame. Anchors checked
  before writing: Figure 8 1.210 → 65.22 / 39.52 / 5.63 %; RDS only 0.647 → 78.39 /
  58.93 / 19.41 %; NEC only −0.681 → 93.76 / 86.93 / 64.78 %. The script refuses to
  overwrite the file without `--force`.
- `backend/` (`uv` project: numpy, onnxruntime; dev: pytest, ruff; no torch).
  `backend/app/inference/`: `spec.py` (loads `feature_spec.json`), `vector.py` (the one
  place a positional vector is built), `hazard.py` (step-function `H0`, survival
  formula), `predictor.py` (one ONNX session, checks artifact sha256 against the model
  card, returns log-risk and the day 0–100 curve). No FastAPI yet.
- Tests, 24 pass (`make test`): golden set through the ONNX backend — max |log-risk
  diff| 4.4e-6 (limit 1e-4), max |S(t) diff| 1.0e-6 (limit 1e-5); recorded anchors;
  formula test without the network; order test and field-swap test (spec 5.2);
  step-function tests including gap days; tampered artifact refused; no torch /
  pycox / scikit-learn / pandas importable in the backend environment.
- `make lint` passes (ruff check + format check; config in `ruff.toml`).
- `docs/MODEL_BEHAVIOUR.md` generated by `make sweep-report`.

### Phase 1 acceptance

| Check | Result |
|---|---|
| ONNX vs PyTorch within tolerance on the golden set | pass |
| Anchors pass | pass |
| `docs/MODEL_BEHAVIOUR.md` exists | yes |
| … and has been sent to the owner | **handed over in the session of 2026-11-13; owner to forward to the clinical co-authors** |

### For the owner from Phase 1

1. **Read `docs/MODEL_BEHAVIOUR.md` and pass it to the clinical co-authors.** It shows
   what the frozen model computes; nothing was changed because of it. Things in it that
   the co-authors may want to look at (model output, not clinical statements —
   `TODO(clinical-review)`):
   - gestational age: for all three reference patients day-28 survival falls towards
     0 % at 39–42 weeks (the cohort is VLBW; such combinations are far from the
     training data, but the form accepts them);
   - SpO2: higher values give lower survival for the two "training mean" patients;
   - RDS = Yes gives higher survival than RDS = No for all three reference patients;
   - birth weight, Apgar and several diagnoses change direction between reference
     patients.
   Whether any of this needs a narrower input range or a warning is the owner's call
   (spec 5.3, Section 11 items 3–4).
2. Spec Section 11 item 3 (training ranges of the five continuous inputs) is still
   open. Default in force: only the weight > 1,500 g warning (to be built in Phase 2).
   The report above makes this item more relevant than it looked.

### Notes for Phase 2

- Build Pydantic request models from `FeatureSpec` (`backend/app/inference/spec.py`);
  do not retype fields or ranges. `Predictor` accepts a mapping of API field names;
  booleans may be `True` / `False` or 0 / 1. `build_vector` checks only that the 11
  fields are present and no others; range validation belongs to the API layer.
- `Predictor.artifact_sha256` is there for `/health`.
- `MODEL_DIR` environment variable overrides the model directory (for the container).
- `make dev` and `make e2e` are stubs that exit with a message until Phases 2–3.
- `ruff format` rewrites code blocks in Markdown; `*.md` is excluded in `ruff.toml`.
- Still missing on the workstation: `node` / `npx` (Phase 3), `docker` (Phase 5), `gh`.

## Phase 0 — Freeze, inventory, gate (complete apart from owner decisions)

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

- `legacy/` now holds the app as deployed after the hot-fix, plus `run.sh` (owner
  approved; see `docs/DECISIONS.md`). Model artifacts unchanged; gate regression
  still 6 / 6.

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
2. `TODO(clinical-review)` / `TODO(owner)` items in `docs/ERRATUM_feature_order.md`:
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
- (Superseded by the Phase 1 section above: `uv` installed, `Makefile` exists,
  `tools/legacy_model.py` archived under `tools/gate/`.)
