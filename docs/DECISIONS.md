# Decisions

Newest last. Add to this file; do not silently reverse an entry.

## 2026-11-12 — Canonical repository

`allminer1/MortralCombat` (git remote `github`) is the canonical repository (owner).
The second remote, `origin` → `allminer1/VLBWSurv`, holds an unrelated single commit
(`f57442e`, 2025-07-08) with no shared history. Nothing is pushed to either remote
without an explicit request.

## 2026-11-12 — Branches

- `main`: untouched GitHub state (2 commits).
- `rebuild`: all rebuild work. Legacy files moved to `legacy/` byte-identical.
- `legacy-streamlit`: production server copy as deployed, tag `legacy-server-2026-11`.

## 2026-11-12 — Phase 0 tooling

Gate scripts run with the existing Anaconda interpreter
(`/opt/anaconda3/bin/python3`: Python 3.12.2, torch 2.6.0, scikit-learn 1.5.1,
pycox 0.3.0, numpy 1.26.4, pandas 2.2.2). No `Makefile` yet: its targets belong to
Phases 1–3. `tools/legacy_model.py` builds positional arrays in two orderings on
purpose — it is the gate's comparison harness, not inference code, and is to be
removed or retired once `model/feature_spec.json` exists (Phase 1).

## 2026-11-12 — `legacy/` holds the deployed app

With the owner's approval, `legacy/MortalCombat.py` was replaced by the version that
runs in production after the hot-fix (tag `legacy-hotfix-2026-11-12`, sha256
`47350ccd…fd2e71d`), and the server's `run.sh` was added. This is the one sanctioned
change to `legacy/`; the three model artifacts were not touched (hashes unchanged).
The GitHub copy it replaces remains on `main`; the pre-fix server copy is tag
`legacy-server-2026-11`. Labels for spec 7.5 are taken from this file ("Bad obestric
history" is the server's typo, to be corrected in the rebuild's i18n files).
`APP_ORDER` in `tools/legacy_model.py` documents the pre-fix order and stays as is.

## 2026-11-12 — Feature-order gate (spec Section 3) — OUTCOME: **A**

**The network was trained in the scaler's column order. The app order is wrong.**

```
MODEL_ORDER = BOH, weight, Apgar5, GDW, RF, HR, Saturation, RDS, IVH, DIC, NE
```

Deciding evidence — `tools/gate_cindex.py`, run by the owner on the held-out test set
(`MortalityKidsTest.csv`), output pasted on 2026-11-12:

```
n = 286   events = 83
ordering    C (Antolini)  C (Harrell)
scaler            0.8666       0.8642
app               0.7205       0.7165
```

The scaler order reproduces the published test C-index (0.86, 95 % CI 0.81–0.90);
the app order falls below that interval. n = 286 matches the published test set.

Consequences:

- The rebuild uses `MODEL_ORDER` above, through named fields only (spec 5.2).
- The live Streamlit app (GitHub and server versions) sends IVH → RDS slot,
  DIC → IVH slot, NEC → DIC slot, RDS → NEC slot. Results are affected whenever the
  four diagnosis flags are not all equal. See `docs/ERRATUM_feature_order.md`.
- Hot-fix on `legacy-streamlit` (commit `b1e65ea`), deployed by the owner on
  2026-11-12 15:04 UTC and confirmed on the live site. Informing the co-authors and
  the journal remains the owner's decision.
- The published performance metrics come from the training pipeline, which used the
  correct order; this check reproduces the C-index and gives no reason to doubt them.

### Evidence

1. **Regression cases** (`tools/gate_regression.py`, no patient data, all pass):

   | case | app order | scaler order |
   |---|---|---|
   | RDS = Yes only | −0.681 (93.76 / 86.93 / 64.78 %) | +0.647 (78.39 / 58.93 / 19.41 %) |
   | NEC = Yes only | +1.204 (65.38 / 39.74 / 5.72 %) | −0.681 (93.76 / 86.93 / 64.78 %) |
   | Article Figure 8 | +1.210 (65.22 / 39.52 / 5.63 %) | +1.210 (65.22 / 39.52 / 5.63 %) |

   The app-order column equals what the live site returned on 2026-11-12 (spec 3.2),
   so the live site feeds the model in app order.

2. **Candidate training script** `PythonProject/hh.py` on the owner's machine (outside
   this repository; sha256 `f10c94f4…5b40f2`). The owner is **not sure** it is the
   script that produced the published weights, so it is supporting evidence only.
   Relevant lines (code only):

   ```python
   FEATURE_COLS = ["BOH", "weight", "Apgar5", "GDW", "RF", "HR", "Saturation", "RDS", "IVH", "DIC", "NE"]   # l.16
   scaler = StandardScaler().fit(df_train[FEATURE_COLS])                                                  # l.155
   x_train = scaler.fit_transform(df_train[FEATURE_COLS]).astype('float32')                               # l.156
   joblib.dump(scaler, "scaler1.pkl")                                                                     # l.162
   model.fit(x_train, y_train_pycox, batch_size=128, epochs=100, verbose=True)                            # l.188
   torch.save(net.state_dict(), "survival_model.pth")                                                     # l.190
   ```

   Scaler and network receive the same array, in scaler order. Same architecture and
   optimiser settings as the app. The copies of `survival_model.pth`, `scaler1.pkl`
   and `baseline_hazard.csv` next to that script have the same sha256 as `legacy/`.
   Caveat: the script's modification date is later than the artifacts'.

3. **Server code read** (spec 3.4 step 1, branch `legacy-streamlit`): the production
   app builds an unnamed array from
   `FEATURES = ["BOH", "weight.g.", "Apgar5", "GDW", "RF", "HR", "Saturation", "IVH", "DIC", "NE", "RDS"]`
   (line 86) and passes it to `scaler.transform` — app order, unchanged from GitHub.
   Its three artifacts are byte-identical to `legacy/`.

4. Scaler means and SHAP directions (spec 3.1, 3.2) fit the scaler order.

Items 1–4 pointed to outcome A; the C-index check above decided it.

## 2026-11-13 — Phase 1: tools environment

`tools/` is a `uv` project pinned to the versions in `legacy/requirements.txt`
(torch 2.7.1, scikit-learn 1.7.0, numpy 2.2.6, pandas 2.3.1, joblib 1.5.1; Python 3.12),
i.e. the environment the production app runs with, plus `onnx` and `onnxruntime`
(locked in `tools/uv.lock`). This replaces the unpinned `tools/requirements.txt`. The
Phase 0 gate was run with the Anaconda versions listed above; it gives the same 6 / 6
result in the new environment.

## 2026-11-13 — Phase 1: gate scripts archived, not deleted

`tools/legacy_model.py`, `gate_regression.py` and `gate_cindex.py` moved to
`tools/gate/` (only their paths were edited). They are the record of the gate and
build positional arrays on purpose; nothing else may import them. They are excluded
from linting.

## 2026-11-13 — Phase 1: where the order comes from

`tools/export_model.py` reads the order from the scaler's `feature_names_in_` and
writes it to `model/feature_spec.json`. It is typed nowhere else in the rebuild: not
in the export script, the golden script, the backend or the tests. Protection against
a wrong order is the golden set (anchors of spec 3.2 in the confirmed order), not a
second copy of the list. Per-feature metadata in the export script (API name, type,
hard range from spec 5.1) is a dictionary keyed by scaler name.

## 2026-11-13 — Phase 1: export details

- ONNX opset 17, TorchScript exporter (`dynamo=False`), input `z` (scaled, float32,
  shape batch × 11), output `log_risk`. Scaling is done in the backend in float64 and is
  not part of the ONNX graph (spec 5.2).
- Model version `deepsurv-vlbw-1.0.0` (spec Section 6 example).
- Generated JSON carries no timestamps, so `make export-model` is byte-reproducible.
  `model_card.json` records sha256 of the three legacy sources and the three exported
  files; the backend refuses to start if an exported file does not match the card.
- `baseline_hazard.json` stores the 65 event times as integers and the cumulative
  hazard values exactly as written in the CSV.

## 2026-11-13 — Phase 1: golden set

Reference path: named DataFrame → the original `StandardScaler` object → PyTorch
network → survival from `legacy/baseline_hazard.csv`. It shares no code with the
backend. Booleans are stored as 0 / 1. Random cases draw every field uniformly over
its hard range (so they include weights above 1,500 g and implausible combinations;
the purpose is numerical agreement, not realism). The file is committed and is not
regenerated; `make_golden.py` refuses to overwrite it without `--force`.

## 2026-11-13 — Phase 1: sweep report reference patients

A = article Figure 8; B / C = each input at its training mean rounded to a valid
value (taken from `feature_spec.json`), with the four diagnoses all No / all Yes.
No patient data. Continuous inputs are varied on at most 9 evenly spaced values.

## 2026-11-13 — Phase 2 run in the same session as Phase 1

The owner asked to start Phase 2 directly after Phase 1 ("one phase per session" is the
default, not kept here at the owner's request). Plan was approved before implementation.

## 2026-11-13 — Phase 2: request validation

- The request model is generated with `pydantic.create_model` from the feature spec, so
  the API cannot drift from `model/feature_spec.json`.
- Strict types: `900.0`, `"900"` and `true` are not integers; `0` / `1` and `"yes"` are
  not booleans. The form sends exact JSON types; lenient parsing would hide client bugs
  in a clinical tool.
- Error codes instead of messages (spec Section 6). Submitted values are never echoed
  in a response.

## 2026-11-13 — Phase 2: rate limit

Own in-process sliding-window limiter instead of a library: the API is one uvicorn
process, the rule is one line (60 / minute on one path), and it avoids a dependency and
a shared store. Counters are lost on restart, which is acceptable. Invalid requests
count towards the limit. Behind a reverse proxy the client address is the **last**
`X-Forwarded-For` entry and only when `TRUSTED_PROXY` is on; earlier entries are
client-supplied.

## 2026-11-13 — Phase 2: logging

Own ASGI access-log middleware; uvicorn's access log is switched off (`make dev`,
Dockerfile) because it prints the query string. The client address is not logged
either: it is not needed for operation and is personal data.

## 2026-11-13 — Phase 2: API docs without a CDN

FastAPI's default `/docs` loads Swagger UI from jsdelivr, which the spec forbids. The
page is served from the `swagger-ui-bundle` Python package (Swagger UI 4.15.5) mounted
at `/api/docs/assets`. That version cannot read OpenAPI 3.1, so the schema is emitted as
3.0.3 (`app.openapi_version`); our schema uses nothing 3.1-specific and renders
correctly. If Phase 3 brings Node, a current `swagger-ui-dist` from npm can replace the
package and the version override can go.

## 2026-11-13 — Phase 2: warnings

`WEIGHT_ABOVE_COHORT` only (owner default: warn, not reject). The 1,500 g cohort limit
is a constant in `app/api/v1.py` and in the model card's exclusion text; it is a cohort
fact from the article, not a feature range.

## 2026-11-13 — Phase 3 run in the same session

At the owner's request, as for Phase 2. Plan approved before implementation, including
installing Node and Playwright's Chromium.

## 2026-11-13 — Phase 3: visual direction

Cool near-white page, white result panel, blue-black text, one petrol accent
(`#0e5a6b`) used for actions, selection and the curve; no gradients, images or shadows.
One typeface, IBM Plex Sans (Latin, Cyrillic, Cyrillic Extended), light weight for the
large numerals. The survival step curve is the one prominent element. Amber is used
only for notices (out-of-date result, weight warning) and red only for input errors;
neither is tied to the size of the estimate, so there is no colour-coded verdict.

## 2026-11-13 — Phase 3: no shadcn/ui (deviation from the stack list)

The page needs a button, a text input with steppers and a two-option choice. They are
written as small components on native `<input>` / `<button>` elements with Tailwind,
which gives keyboard and screen-reader behaviour for free and no extra dependencies.
shadcn/ui (Radix) can still be added in Phase 4 or 6 if dialogs, menus or tables need
it. Owner may ask to reverse this.

## 2026-11-13 — Phase 3: tooling

- Linter is oxlint (what the current Vite template ships) with its React, TypeScript
  and jsx-a11y rules; warnings fail `make lint`.
- e2e: Playwright starts uvicorn (port 8010, rate limit off) and `vite preview` of the
  production build (port 4173) itself. Compose stack in Phase 5.
- Browser review used Playwright screenshots and the Claude app's built-in browser; the
  Playwright MCP named in `CLAUDE.md` is not available in this environment.

## 2026-11-13 — Phase 3: form behaviour

- Validation rules are generated from the served feature spec (zod schema built at
  run time); error texts are i18n keys.
- On-screen grouping and order are a presentation list of field names in
  `frontend/src/lib/fields.ts`; the model order never reaches the frontend logic, and
  requests are objects of named fields.
- Steppers are disabled while a field is empty: "no pre-filled values" (spec 7.2)
  would be undone by a "+" that jumps to the minimum.
- A result whose inputs have since been edited is marked out of date (see PROGRESS).
- Percent and decimal formatting follows the interface language (`65%` / `65 %`,
  `1.210` / `1,210`).
- The chart is sized in container pixels (ResizeObserver) so axis labels stay
  readable on a phone, and sits out of the layout flow so it cannot widen the page.

## 2026-11-13 — Phase 4 run in the same session

At the owner's request, as for Phases 2–3. Plan approved before implementation.

## 2026-11-13 — Phase 4: case code is a handwritten line

Spec 7.4 allows an "optional free case code line"; `CLAUDE.md` rule 5 forbids free-text
fields. The report prints a blank line labelled "Case code (optional; no names or
record numbers)". Nothing is typed, so nothing identifying can enter the browser.
Phase 6 (accounts) has its own stored `case_code`; that decision is separate.

## 2026-11-13 — Phase 4: report data lives in memory only

The last calculation is held in React state above the router. It is not put in the URL
(URLs end up in history and logs) or in browser storage (shared ward PCs). Cost: a
reload of `/report` loses it; the page then says to calculate first.

## 2026-11-13 — Phase 4: About numbers come from the model card

`/about` shows cohort and performance figures from `model/model_card.json` through the
API instead of typing them into three translation files; an e2e test pins them to spec
Section 1. Exclusion criteria and the calibration note are sentences and live in the
translations (`TODO(clinical-review)`).

## 2026-11-13 — Phase 4: Kazakh build flag

`VITE_ENABLE_KK=true` at build time. The Kazakh file is loaded with a conditional
dynamic import that the bundler removes when the flag is off, so unreviewed clinical
wording is not shipped at all, not merely hidden. e2e builds the frontend twice to test
both states. JSON has no comments, so review markers are data: `_todo_clinical_review`
and `_clinical_terms` (keys starting with `TODO(clinical-review)`); keys starting with
`_` are ignored by the key-parity test.

## 2026-11-13 — Phase 4: number and date formats for Kazakh

Numbers in Kazakh always use the Russian formatting rules (decimal comma, space before
%), because some browsers claim Kazakh support and print English forms (seen in
Playwright's Chromium). Dates use Kazakh month names when the browser really has them,
else Russian.

## 2026-11-13 — Phase 5 part A run in the same session

At the owner's request. Only the workstation part was approved and done; the server
part is the owner's (`docs/CUTOVER.md`).

## 2026-11-13 — Phase 5: local container runtime

Colima with the Docker CLI instead of Docker Desktop: command-line only, no licence
terms to accept, no admin password.

## 2026-11-13 — Phase 5: how Caddy and Streamlit share the server

Caddy takes ports 80 / 443 and serves two sites from one `.env`: `SITE_NEW` (the new
stack) and `SITE_LEGACY` (reverse proxy to Streamlit on a local port). Staging,
cutover and rollback are all the same operation: change which name is on which line
and run `deploy/deploy.sh`. No DNS change at cutover or rollback, so both are immediate.
Streamlit listens on the Docker bridge address (`172.17.0.1:8501`) rather than
`127.0.0.1`, because a container cannot reach the host's loopback; the alternative,
running Caddy with host networking, would take it out of the compose network.
This follows the option recorded in the Phase 0 inventory.

## 2026-11-13 — Phase 5: images are built on the server

`deploy.sh` builds from the checkout instead of pulling from a registry: one fewer
account and secret. Cost: the build needs memory, hence the swap step in the runbook.
A registry can replace this later without changing the compose file's shape.

## 2026-11-13 — Phase 5: security headers

- Application: `default-src 'self'` with nothing inline. Consequences kept in code:
  zod runs `jitless`, Vite never inlines assets as `data:` URLs.
- `/api/docs` only: inline script and style allowed, because Swagger UI's page needs
  them; still same-origin only.
- HSTS one year, without `includeSubDomains` or preload.
- Caddy's access log drops query strings, client addresses and all headers, matching
  the API's own logging rule; the admin API is off.

## 2026-11-13 — Phase 5: e2e targets

`make e2e` tests the compose stack (spec Section 9). `make e2e-local` keeps the
Docker-free mode because it is the only one that builds with the Kazakh flag. CI runs
both.
