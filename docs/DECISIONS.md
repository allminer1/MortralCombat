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
