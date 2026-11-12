# NeoMortalSurv — rebuild specification

Rebuild of the VLBW infant survival calculator from a single-file Streamlit app into a
proper website: FastAPI backend, React frontend, documented API, print report,
EN / RU / KK, optional accounts with saved history.

Save this file as `docs/REBUILD_SPEC.md` in the repository. `CLAUDE.md` (repo root)
holds the short standing rules; this file holds the full plan.

---

## 0. How to work with this document

- Work **one phase per session** (Section 10). Start each session in plan mode, read
  this spec and `docs/PROGRESS.md`, propose a plan for the current phase only, wait for
  approval, then implement.
- Each phase ends with its acceptance checks passing, a commit, and an update to
  `docs/PROGRESS.md` (what was done, what is open, what the next session must know).
- Record every non-obvious choice in `docs/DECISIONS.md` (date, decision, reason).
- Items marked `TODO(owner)` need an answer from the project owner. Do not guess them.
  Ask, or implement the stated default and list it in `docs/PROGRESS.md`.
- Text marked `TODO(clinical-review)` is clinical wording. Draft it, flag it, and never
  treat it as final.
- **Phase 0 contains a blocking gate (Section 3). No inference code is written before
  it is resolved.**

---

## 1. Context

- The tool predicts survival of very-low-birth-weight (VLBW) infants in the NICU with a
  DeepSurv model (PyTorch / pycox). It is described in:
  Bozhbanbayeva N, Abilbayeva A, Tarabayeva A, Isgandarov I, Tolykbayev T, Adilbekova I,
  Yelyubayeva D. *A deep-learning approach to predict mortality in very-low-birth-weight
  infants treated in the intensive care units using DeepSurv.* Front. Pediatr. 2026;
  14:1801840. doi:10.3389/fped.2026.1801840 (CC BY).
- The article publishes the address **https://neomortalsurv.net**. That URL must keep
  working and must open the calculator directly.
- Cohort: 958 VLBW neonates, four perinatal centres in Kazakhstan, Jan 2021 – May 2025;
  672 training / 286 test. Infants above 1,500 g and with severe congenital
  malformations were excluded. 11 predictors selected by Boruta.
- Reported test performance of DeepSurv: C-index 0.86 (95% CI 0.81–0.90), overall AUC
  0.95 (0.91–0.98), IBS 0.071. Calibration was weaker at day 7, mainly at low predicted
  risk. No external validation yet.
- Intended use (from the article): point-of-care estimate at NICU admission, and
  repeated use when the status of RDS / IVH / NEC / DIC changes. Diagnoses are entered
  as "Yes" only when confirmed.
- Current implementation: `MortalCombat.py` (Streamlit), `survival_model.pth`,
  `scaler1.pkl`, `baseline_hazard.csv`. One commit, no tests, no README, no licence.
  **The code on the production server is newer than GitHub** (owner confirmed).

---

## 2. Legacy facts (verified against the GitHub repository)

### 2.1 Network

```
Linear(11,511) → ReLU → BatchNorm1d(511) → Dropout(0.201)
Linear(511,141) → ReLU → BatchNorm1d(141) → Dropout(0.496)
Linear(141,127) → ReLU → BatchNorm1d(127) → Dropout(0.106)
Linear(127,16) → ReLU → BatchNorm1d(16) → Dropout(0.28)
Linear(16,1)                                   # output = log-risk g(x)
```

Weights load with `net.load_state_dict(torch.load(path, map_location="cpu"))`; pycox is
not needed for inference. The network must be in `eval()` mode (BatchNorm uses running
statistics, Dropout off).

### 2.2 Survival function

```
z      = (x − mean) / scale            # StandardScaler, all 11 features incl. binary ones
g      = net(z)                        # log-risk, float32
S(t)   = exp( −H0(t) · exp(g) )
```

`H0(t)` comes from `baseline_hazard.csv`: 65 event times between day 1 and day 101 with
gaps (for example no rows for days 45, 49, 55, 57–62, 83–96, 98–100). It is a **step
function**. The legacy app picks the *nearest* row, which is wrong in principle for a
step function. It gives the same numbers for days 7, 28 and 100 only because of how the
table happens to look (day 100 → row 101, same H0 as row 97).

### 2.3 Scaler (read from `scaler1.pkl`, `n_samples_seen_ = 672`)

| # | `feature_names_in_` | mean | scale |
|---|---------------------|------|-------|
| 1 | BOH        | 0.6086   | 0.4881   |
| 2 | weight     | 1121.4375| 304.4714 |
| 3 | Apgar5     | 5.5863   | 1.4745   |
| 4 | GDW        | 28.8988  | 2.7258   |
| 5 | RF         | 2.4345   | 0.5220   |
| 6 | HR         | 113.8988 | 27.4722  |
| 7 | Saturation | 74.9673  | 14.0019  |
| 8 | **RDS**    | 0.8259   | 0.3792   |
| 9 | **IVH**    | 0.5015   | 0.5000   |
| 10| **DIC**    | 0.3929   | 0.4884   |
| 11| **NE**     | 0.1384   | 0.3453   |

### 2.4 Verified anchors

- **Article Figure 8** — BOH = Yes, weight 900 g, Apgar5 = 3, GA 27 w, RF = 3, HR 80,
  SpO2 55, IVH = Yes, DIC = Yes, NEC = Yes, RDS = Yes → log-risk **1.210**, survival
  day 7 **65.22 %**, day 28 **39.52 %**, day 100 **5.63 %**. The repository model,
  scaler and baseline hazard reproduce these numbers exactly, so the server uses the
  same three artifacts.
- **ONNX export** — `torch.onnx.export` of the eval-mode network (dynamic batch axis)
  gives a 399 KB file. Against PyTorch on 2,000 input vectors the maximum absolute
  difference in log-risk was 3e-6, for batched and single-row inference.

---

## 3. BLOCKING GATE — input feature order

### 3.1 The problem

The scaler was fitted on columns in this order:

```
BOH, weight, Apgar5, GDW, RF, HR, Saturation, RDS, IVH, DIC, NE
```

The GitHub version of the app builds an **unnamed** NumPy array in this order:

```
BOH, weight.g., Apgar5, GDW, RF, HR, Saturation, IVH, DIC, NE, RDS
```

Positions 8–11 differ. With an unnamed array scikit-learn cannot detect it. If the
network was trained on the scaler's column order (the normal case: same DataFrame for
`scaler.fit` and model fit), then the legacy app sends

| user enters | value lands in model slot |
|-------------|---------------------------|
| IVH | RDS |
| DIC | IVH |
| NEC | DIC |
| RDS | NEC |

The scaler means support the scaler order: RDS 83 %, IVH 50 %, DIC 39 %, NEC 14 % are
plausible prevalences for a VLBW cohort; read in the app's order they would say
RDS 14 %, which is not.

The result is identical in both orderings only when the four flags are all equal. In a
rough simulation (3,000 synthetic patients drawn independently around the scaler
means; not real data) about half differed by more than 10 percentage points in day-28
survival between the two orderings. Figure 8 of the article has all four flags = Yes,
so it cannot tell the orderings apart, and it stays correct either way. The published
performance metrics come from the training pipeline, not from the web app.

### 3.2 Live-site test (done 2026-11-12 on https://neomortalsurv.net)

All sliders at their defaults (400 g, Apgar 0, GA 20, HR 60, SpO2 40), BOH = No,
RF = 2, one flag set to Yes:

| case | live site | expected, app order | expected, scaler order |
|------|-----------|---------------------|------------------------|
| RDS = Yes only | **−0.681** (93.76 / 86.93 / 64.78 %) | −0.681 | +0.647 |
| NEC = Yes only | **+1.204** (65.38 / 39.74 / 5.72 %) | +1.204 | −0.681 |

**The live site uses the app order.** The server code has not fixed it.

Further support that the network expects the scaler order: averaged over random
inputs, slot 9 is the only one of the four with a negative effect and slot 10 has the
strongest positive effect. In the article's SHAP figure IVH is the only one of the four
with a negative direction and DIC is the strongest positive. That fits
slot 9 = IVH, slot 10 = DIC (scaler order), not slot 9 = DIC (app order).

### 3.3 What is still not known

- The actual column order used when the network was trained. It is inferred from the
  scaler, the prevalences and the SHAP figure; the training code has not been seen.

### 3.4 Resolution procedure (Phase 0)

1. Get the server version of the code into git (Section 10, Phase 0) and read how it
   builds the input vector.
2. `TODO(owner)`: provide the training script / notebook, or at least the lines that
   define the feature columns for `scaler.fit` and for model training.
3. Keep the two cases of Section 3.2 as regression tests for the legacy behaviour and
   for the corrected behaviour.
4. If the held-out test set is available on the owner's machine: write a script that
   computes the C-index under both orderings and prints only the two numbers. Expected
   ≈ 0.86 for the correct ordering. The owner runs it. Do not open, print or copy the
   data file.
5. Write the outcome to `docs/DECISIONS.md`:
   - **A. Trained in scaler order, app order wrong (expected).** The rebuild uses the
     scaler order via named fields. Write `docs/ERRATUM_feature_order.md` (what was
     wrong, which input patterns were affected, from when to when). The owner decides
     with the co-authors how to communicate it.
   - **B. Trained in app order** (the scaler was then fitted on differently ordered
     columns than the network saw). Stop. This needs the owner and co-authors.
   - **C. Anything else.** Stop and report.
6. If the outcome is A, the live Streamlit app should not wait for the rebuild. The
   fix there is to build the input vector in the scaler's order
   (`BOH, weight.g., Apgar5, GDW, RF, HR, Saturation, RDS, IVH, DIC, NE`) while leaving
   the on-screen order as it is. Prepare that patch on the `legacy-streamlit` branch;
   the owner deploys it.

From here on, `MODEL_ORDER` means the order confirmed by this gate.

---

## 4. Target architecture

```
Browser ──HTTPS──> Caddy ──> /            static React build
                         └─> /api/*       FastAPI (uvicorn) ──> ONNX Runtime
                                                          └──> PostgreSQL (accounts phase only)
```

- **Backend:** Python, FastAPI, Pydantic v2, onnxruntime, NumPy. No torch, pycox,
  scikit-learn, pandas or matplotlib at runtime. `uv` for dependencies, `ruff`, `pytest`.
- **Frontend:** React + TypeScript + Vite, Tailwind CSS, shadcn/ui components,
  react-hook-form + zod, react-i18next, a small SVG chart (Recharts or hand-written SVG).
- **Database (Phase 6 only):** PostgreSQL, SQLAlchemy 2, Alembic.
- **Infra:** Docker Compose on the existing Linux VPS, Caddy for TLS and static files,
  GitHub Actions for CI.
- Use current stable versions. Check the libraries' current documentation instead of
  relying on memory, and pin exact versions in lock files.
- **No third-party requests from the browser**: no CDN fonts, no analytics, no external
  scripts. Everything is self-hosted. Hospital networks are restrictive and the inputs
  are clinical data.

### 4.1 Repository layout

```
CLAUDE.md
README.md
Makefile                      # dev, test, lint, e2e, export-model, build
docs/                         # REBUILD_SPEC, PROGRESS, DECISIONS, ERRATUM, MODEL_BEHAVIOUR
legacy/                       # Streamlit app + original artifacts, frozen, read-only
model/
  deepsurv.onnx
  feature_spec.json           # single source of truth: order, names, ranges, scaler
  baseline_hazard.json
  model_card.json             # version, sha256 of artifacts, citation, cohort summary
tools/                        # one-off scripts; own requirements (torch, sklearn, joblib)
  export_model.py
  make_golden.py
  sweep_report.py
backend/
  app/  (main.py, api/, core/, inference/, schemas/, db/ …)
  tests/ (unit/, golden/, api/)
frontend/
  src/ (pages/, components/, i18n/{en,ru,kk}.json, lib/api.ts …)
  e2e/
deploy/
  docker-compose.yml, Caddyfile, .env.example, deploy.sh, backup.sh
.github/workflows/ci.yml
```

---

## 5. Model contract

### 5.1 `model/feature_spec.json`

Single source of truth for both backend and frontend (the frontend imports the ranges
from the `/api/v1/model` endpoint or from a generated TypeScript file; never retype them).

| MODEL_ORDER | scaler name | API field | type | hard range |
|---|---|---|---|---|
| 1 | BOH | `bad_obstetric_history` | bool | — |
| 2 | weight | `birth_weight_g` | int | 400–2000 |
| 3 | Apgar5 | `apgar_5min` | int | 0–10 |
| 4 | GDW | `gestational_age_weeks` | int | 20–42 |
| 5 | RF | `respiratory_failure_grade` | enum {2, 3} | — |
| 6 | HR | `heart_rate_bpm` | int | 60–200 |
| 7 | Saturation | `spo2_percent` | int | 40–100 |
| 8 | RDS | `rds` | bool | — |
| 9 | IVH | `ivh` | bool | — |
| 10 | DIC | `dic` | bool | — |
| 11 | NE | `nec` | bool | — |

(Rows 8–11 as confirmed by the Section 3 gate.) Hard ranges are the legacy slider
limits. RF is the severity grade: II or III. The model has never seen other values.

### 5.2 Inference rules

- Inputs travel as **named fields** end to end. The only place a positional vector is
  built is one function that reads `MODEL_ORDER` from `feature_spec.json`. A unit test
  asserts that this order equals the `feature_names` stored in the spec and that
  permuting two fields changes the output.
- Scaling: `z = (x − mean) / scale` in float64, then cast to float32.
- `H0(t)` = value at the largest event time ≤ t; `H0(t) = 0` for t < first event time.
- Curve returned for integer days 0…100, `S(0) = 1`.
- Reported points: day 7, day 28, day 100.
- One ONNX session created at startup and reused.

### 5.3 Soft warnings (returned as codes, not errors)

- `WEIGHT_ABOVE_COHORT` when `birth_weight_g > 1500` (infants above 1,500 g were
  excluded from model development).
- `OUTSIDE_TRAINING_RANGE` per continuous field once the owner provides observed
  training ranges — `TODO(owner)`: min / max (or 1st–99th percentile) of weight, GA,
  Apgar5, HR, SpO2 in the training set.
- `TODO(owner)`: decide whether weight above 1,500 g should be rejected instead of
  warned. Default: warn.

### 5.4 Export and golden tests (`tools/`)

- `export_model.py`: load the legacy weights, `eval()`, export ONNX with a dynamic
  batch axis; write `feature_spec.json` (order from the gate, mean / scale from the
  scaler), `baseline_hazard.json`, `model_card.json` with sha256 of every artifact.
  After this step the pickle is never loaded again.
- `make_golden.py`: reference outputs from the **PyTorch** network with inputs passed
  as a named DataFrame in `MODEL_ORDER`: 500 random valid vectors + all-min, all-max,
  each field toggled alone, and the anchors from Sections 2.4 and 3.2. Stored in
  `backend/tests/golden/golden.json`.
- Backend golden test: log-risk within 1e-4, every S(t) within 1e-5.
- Formula test without the network: log-risk 1.210 → 65.22 % / 39.52 % / 5.63 %.
- `sweep_report.py`: for a few reference patients, vary each input over its range and
  write `docs/MODEL_BEHAVIOUR.md` (tables of day-28 survival). This is for the clinical
  co-authors: a clearer interface makes the model's behaviour more visible, including
  directions the article's SHAP figure already shows (for example IVH). No code
  changes follow from this report without the owner.

---

## 6. API

Base path `/api/v1`. JSON only. OpenAPI docs served at `/api/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness + model sha256 loaded |
| GET | `/model` | model card, feature spec (names, ranges, units), citation |
| POST | `/predict` | one prediction |

`POST /predict` request:

```json
{
  "bad_obstetric_history": true,
  "birth_weight_g": 900,
  "apgar_5min": 3,
  "gestational_age_weeks": 27,
  "respiratory_failure_grade": 3,
  "heart_rate_bpm": 80,
  "spo2_percent": 55,
  "rds": true, "ivh": true, "dic": true, "nec": true
}
```

Response:

```json
{
  "model_version": "deepsurv-vlbw-1.0.0",
  "log_risk": 1.210,
  "survival": { "day_7": 0.6522, "day_28": 0.3952, "day_100": 0.0563 },
  "curve": [ { "day": 0, "survival": 1.0 }, { "day": 1, "survival": 0.975 } ],
  "warnings": [],
  "intended_use": "research"
}
```

- All 11 fields required. Unknown fields rejected. Out-of-range → 422 with field-level
  errors that the frontend can translate (error codes, not English sentences).
- Probabilities are fractions 0–1 with full precision; formatting is the client's job.
- Rate limit per IP (default 60 requests / minute on `/predict`).
- **Never log request bodies.** Log method, path, status, latency, model version and
  warning codes only.
- CORS: same origin only by default. `TODO(owner)`: list of external origins or API
  keys when EHR integration becomes concrete. Not built now; the versioned path and
  stable schema are what keeps that door open.

---

## 7. Frontend

### 7.1 Pages

| Route | Content |
|---|---|
| `/` | the calculator (must be the landing page — published URL) |
| `/about` | what the model is, cohort, performance, limitations, how to cite |
| `/report` | print view of the current result |
| `/login`, `/history` | Phase 6 |
| footer | intended-use notice, model version, citation with DOI, link to API docs |

### 7.2 Calculator form

- Two groups: **At birth / NICU admission** (gestational age, birth weight, Apgar at
  5 min, heart rate, SpO2, bad obstetric history) and **Confirmed diagnoses — update
  as they change** (respiratory failure grade II / III, RDS, IVH, DIC, NEC).
- **No pre-filled values.** The legacy sliders start at the minimum (400 g, Apgar 0,
  GA 20, HR 60, SpO2 40), so an untouched form produces a result for an impossible
  patient. Use empty numeric inputs with steppers and unselected No / Yes segmented
  controls. "Calculate" stays disabled until all 11 fields are valid.
- Inline validation with the ranges from the feature spec; integer inputs only.
- Field help from the article: heart rate and SpO2 are single values taken right after
  birth at NICU admission; a diagnosis is "Yes" only when confirmed; recalculate when
  a diagnosis changes.
- `TODO(owner)` / `TODO(clinical-review)`: one-line definition of "bad obstetric
  history" for the tooltip.

### 7.3 Result panel

- Headline: survival probability at **day 7** and **day 28**; day 100 secondary.
- Step curve, days 0–100, y from 0 to 1, hover / tap shows day and value, also
  available as a table for screen readers.
- De-emphasise the late part of the curve where the baseline table becomes sparse and
  say why (few infants still under observation). Default boundary: day 56.
  `TODO(owner)`: confirm the boundary.
- Headline numbers rounded to whole percent; one decimal in the details. The legacy
  two decimals suggest precision the model does not have. `TODO(owner)` may override.
- Details section: log-risk, model version, warnings.
- Limitations box, always visible with a result: estimates come from a single
  retrospective cohort; no external validation; calibration is weaker at day 7,
  especially at low predicted risk; not a substitute for clinical judgement.
  `TODO(clinical-review)` for the final wording in all three languages.
- **No risk categories, traffic-light colours or "high / low risk" labels.** The
  article used a median split for analysis only; no clinical thresholds were validated.
- Actions: Print report, Reset, and (Phase 6, when signed in) Save.

### 7.4 Print report (`/report`)

One A4 page via print CSS (browser "Save as PDF"; no server-side PDF engine): date and
time, the 11 inputs, the three survival estimates, the curve, warnings, model version,
limitations text, citation. Optional free "case code" line. No patient name field.

### 7.5 Languages

- `en`, `ru`, `kk`; all strings in `frontend/src/i18n/*.json`, none hard-coded.
- Carry the Russian wording over from the legacy app. Use the **server** version's
  labels: BOH is "Bad obstetric history", not "Chorioamnionitis" as in the GitHub copy.
  Fix the typo on the live site ("Bad obestric history").
- Kazakh: draft the translation, mark every clinical term `TODO(clinical-review)`, and
  keep `kk` hidden behind a build flag until the owner confirms a native-speaking
  clinician has reviewed it.
- Language switch in the header; remember the choice (localStorage in try / catch),
  first visit follows the browser language, `?lang=` overrides.

### 7.6 Design and accessibility

- Use the `frontend-design` skill for the visual direction. Brief: calm, clinical,
  typographic; large clear numerals; plenty of white space; one restrained accent
  colour; no emoji, no stock medical imagery, no gradients-for-decoration.
- Must work on a ward PC at 1366×768 and on a phone held in one hand. Form and result
  side by side on wide screens, stacked on narrow ones.
- WCAG 2.1 AA: labels on every control, full keyboard operation, visible focus,
  contrast ≥ 4.5:1, errors announced, no information carried by colour alone.
- Cyrillic and Kazakh-specific letters (ә, ғ, қ, ң, ө, ұ, ү, һ, і) must render in the
  chosen self-hosted font.
- Verify the UI in a real browser (Playwright MCP): screenshots at 375, 768 and 1366 px
  in all languages before a frontend phase is called done.

---

## 8. Accounts and saved history (Phase 6, behind `ENABLE_ACCOUNTS`)

The calculator stays fully usable without an account.

- **Default: invite-only.** An admin CLI creates users and resets passwords. No e-mail
  infrastructure in the first version. `TODO(owner)`: confirm, or ask for open sign-up.
- E-mail + password; argon2id hashes; server-side sessions in PostgreSQL; cookie
  `HttpOnly`, `Secure`, `SameSite=Lax`; CSRF protection on state-changing requests;
  idle timeout; rate limit on login.
- Roles: `user`, `admin`.
- Table `calculations`: `id` (uuid), `user_id`, `created_at`, `case_code` (optional,
  ≤ 32 chars), `inputs` (JSONB), `outputs` (JSONB), `model_version`.
- `case_code` is a pseudonym the clinician chooses. The UI says: no names, no national
  ID numbers, no medical record numbers. **No free-text notes field.**
- `/history`: list of own calculations; grouping by `case_code` gives a timeline of
  reassessments for one infant (the use the article describes). Open a saved item to
  see or print it. Delete own items. Export own items as CSV.
- Users see only their own records. Test this explicitly (user A cannot read, delete
  or export user B's items by guessing ids).
- Nightly `pg_dump` (`deploy/backup.sh`), retention 14 days. `TODO(owner)`: off-server
  copy.
- **Sign-off before enabling in production:** stored inputs are patient-level clinical
  data linked to a clinician account. `TODO(owner)`: confirm with the institution /
  ethics committee and the applicable personal-data rules (including where the server
  must be located) that this is allowed. Until then `ENABLE_ACCOUNTS=false` in
  production.

---

## 9. Deployment

- Develop and run Claude Code on a workstation, **not on the production server**.
- Phase 0 server inventory: give the owner read-only commands to run and paste back
  (`uname -a`, `free -h`, `df -h`, `docker --version`, `ss -tlnp`,
  `systemctl list-units --type=service | grep -Ei 'streamlit|nginx|caddy|apache'`).
  Decide from the answers how Caddy coexists with whatever holds ports 80 / 443 now.
- Compose services: `caddy`, `api`; `db` only in the `accounts` profile. Containers run
  as non-root; `api` has a read-only root filesystem; secrets only through `.env` on
  the server (never in git; commit `.env.example`).
- Caddy: automatic TLS, HSTS, strict Content-Security-Policy (`default-src 'self'`),
  `X-Content-Type-Options`, `Referrer-Policy`, `frame-ancestors 'none'`, gzip / zstd.
- CI on every push: ruff, pytest (golden tests included), frontend lint + type-check +
  unit tests, Playwright e2e against the compose stack, image build.
- Deploy is a manual `deploy/deploy.sh` run by the owner. Never run it, or any SSH
  command against production, without an explicit request in that session.
- **Cutover:** new stack first on a staging subdomain next to the running Streamlit
  app → owner and a clinical co-author compare a list of cases → switch the main domain
  → keep the Streamlit app reachable on a `legacy.` subdomain for 30 days → remove.
  Rollback = point the main domain back.
- `TODO(owner)`: external uptime check on `/api/v1/health`.

---

## 10. Phases and acceptance criteria

### Phase 0 — Freeze, inventory, gate
- Server code committed to a `legacy-streamlit` branch and tagged; diff against GitHub
  `main` written to `docs/PROGRESS.md`; sha256 of the three artifacts compared.
- Legacy files moved to `legacy/`; `.idea/` removed; `.gitignore`, `README.md` added.
- Server inventory collected.
- Section 3 gate resolved and written to `docs/DECISIONS.md`.
- `TODO(owner)`: licence decision. The tool is patented; default is an explicit
  "All rights reserved" notice, no open-source licence.
- `TODO(owner)`: rename the repository (default `neomortalsurv`); GitHub redirects the
  old address.
- **Done when:** the gate has a written outcome A, B or C.

### Phase 1 — Model package
- `tools/` scripts, `model/` artifacts, golden set, sweep report (Section 5).
- **Done when:** ONNX vs PyTorch within tolerance on the golden set; anchors pass;
  `docs/MODEL_BEHAVIOUR.md` exists and has been sent to the owner.

### Phase 2 — Backend API
- Section 6 endpoints, validation, warnings, rate limit, logging rules, OpenAPI.
- **Done when:** golden tests pass through the HTTP layer; 422 cases tested for every
  field; a test proves request bodies do not reach the logs; image has no torch.

### Phase 3 — Frontend calculator (EN + RU)
- Sections 7.1–7.3, 7.6.
- **Done when:** e2e test enters the Figure 8 case and reads 65 % / 40 % / 6 %
  (rounded) and 1.210 in details; empty form cannot be submitted; screenshots at three
  widths reviewed; accessibility check passes with no serious issues.

### Phase 4 — Report, About page, Kazakh
- Sections 7.4, 7.5, `/about`.
- **Done when:** the report prints on one A4 page in all languages; `kk` exists behind
  its flag with review markers; `/about` numbers match Section 1 exactly.

### Phase 5 — Deploy and cutover
- Section 9.
- **Done when:** staging subdomain serves the new stack over HTTPS; owner signs off the
  case comparison; main domain switched; legacy subdomain live; rollback rehearsed once.

### Phase 6 — Accounts and history
- Section 8.
- **Done when:** isolation tests pass; backup and restore rehearsed once; feature stays
  off in production until the owner records the sign-off in `docs/DECISIONS.md`.

---

## 11. Open items for the owner

| # | Item | Default if unanswered |
|---|---|---|
| 1 | Training column order / notebook (Section 3) | none — blocking |
| 2 | Decision on hot-fixing the live Streamlit app and informing co-authors | none — owner's call |
| 3 | Training ranges of the 5 continuous inputs | warn only for weight > 1,500 g |
| 4 | Reject or warn above 1,500 g | warn |
| 5 | Definition of "bad obstetric history" | tooltip omitted |
| 6 | Rounding of headline numbers | whole percent |
| 7 | Day from which the curve is de-emphasised | day 56 |
| 8 | Kazakh clinical review | `kk` stays hidden |
| 9 | Invite-only vs open sign-up | invite-only |
| 10 | Institutional sign-off for stored data | accounts off in production |
| 11 | Licence text, repository name | all rights reserved; `neomortalsurv` |
| 12 | Contact shown on the site | none shown |

---

## 12. Out of scope

- Retraining, recalibrating or otherwise changing the model.
- EHR (Damumed) integration itself; only the stable API is prepared.
- Server-side PDF generation, e-mail sending, mobile apps, analytics.
- Risk categories or treatment recommendations.
