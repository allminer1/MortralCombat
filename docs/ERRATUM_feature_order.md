# Erratum (DRAFT) — input order of four diagnosis fields in the web calculator

Status: **draft for the owner and co-authors.** Not published, not sent to anyone.
All wording is `TODO(clinical-review)`. How and whether this is communicated is the
owner's decision together with the co-authors.

## What was wrong

The web calculator at https://neomortalsurv.net passed its 11 inputs to the model as
an unnamed list. The last four positions were in a different order from the one the
model was trained on:

| position | model expects | calculator sent |
|---|---|---|
| 8 | RDS | IVH |
| 9 | IVH | DIC |
| 10 | DIC | NEC |
| 11 | NEC | RDS |

So the value entered for IVH was used as RDS, DIC as IVH, NEC as DIC, and RDS as NEC.
The other seven inputs were not affected.

## What was not affected

- The model, its weights, the scaler and the baseline hazard. They are unchanged.
- The performance reported in the article (doi:10.3389/fped.2026.1801840). Those
  metrics come from the training pipeline, which used the correct order. Re-running
  the frozen model on the held-out test set (n = 286, 83 events) gives a C-index of
  0.867 in the correct order, in line with the published 0.86.
- Figure 8 of the article (all four diagnoses = Yes): identical in both orders.
- Any calculation in which RDS, IVH, DIC and NEC were all "No" or all "Yes".

## What was affected

Every calculation on the website in which the four diagnosis answers were not all
equal. The size and direction of the error depend on the combination. Two examples
with all other inputs at the calculator's default values:

| entered | shown by the calculator (day 7 / 28 / 100) | correct |
|---|---|---|
| RDS = Yes only | 93.76 / 86.93 / 64.78 % | 78.39 / 58.93 / 19.41 % |
| NEC = Yes only | 65.38 / 39.74 / 5.72 % | 93.76 / 86.93 / 64.78 % |

(The default values describe an implausible patient; the examples show the mechanism,
not typical magnitudes.) Fed in the calculator's order, the same model reaches a
C-index of 0.72 on the test set instead of 0.87.

`TODO(owner)`: decide whether a table of typical clinical input patterns should be
added here (it can be produced from synthetic inputs, without patient data).

## Period

- From: `TODO(owner)` — date the calculator first went online. The earliest version in
  git (2025-07-08) already has the wrong order.
- To: 2026-11-12, 15:04 UTC — fix deployed by the owner and confirmed on the live site.

## Fix

The calculator now passes inputs by name, in the order stored with the model. On-screen
order and labels are unchanged. Commit `b1e65ea` on branch `legacy-streamlit`,
deployed 2026-11-12. After the deploy the live site returns the correct values for
both examples above and still reproduces Figure 8 of the article.

## Open questions for the owner and co-authors

- `TODO(owner)`: whether results from the website were used in clinical decisions,
  teaching or further publications, and who needs to be told.
- `TODO(owner)`: whether the journal should be informed (the article gives the URL).
- `TODO(clinical-review)`: wording of any notice shown on the website.
