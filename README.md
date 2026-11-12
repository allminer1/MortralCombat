# NeoMortalSurv

Web calculator that estimates the survival of very-low-birth-weight (VLBW) infants in
the neonatal intensive care unit with a published DeepSurv model.

- Live: https://neomortalsurv.net
- Article: Bozhbanbayeva N, Abilbayeva A, Tarabayeva A, Isgandarov I, Tolykbayev T,
  Adilbekova I, Yelyubayeva D. *A deep-learning approach to predict mortality in
  very-low-birth-weight infants treated in the intensive care units using DeepSurv.*
  Front. Pediatr. 2026;14:1801840. doi:10.3389/fped.2026.1801840

**Research use.** The model was developed on a single retrospective cohort and has not
been externally validated. It is not a substitute for clinical judgement.

## Status

The calculator is being rebuilt from a single-file Streamlit app into a FastAPI
backend and a React frontend. The model itself is frozen and is not changed.

- `docs/REBUILD_SPEC.md` — plan, phases, acceptance criteria
- `docs/PROGRESS.md` — current state
- `docs/DECISIONS.md` — decisions taken

## Layout

| Path | Content |
|---|---|
| `legacy/` | original Streamlit app and model artifacts — frozen, read-only |
| `tools/` | one-off scripts (own Python environment, see `tools/requirements.txt`) |
| `docs/` | specification, progress, decisions |

## Data

This repository contains no patient-level data and must never contain any.

## Licence

Copyright © the authors. All rights reserved. No licence is granted to use, copy,
modify or distribute this software. <!-- TODO(owner): confirm licence text -->
