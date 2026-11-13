# Cutover step 6 — comparison of old and new calculator (partial)

Record supplied by the owner on 2026-11-13. The comparison was done in a browser by
another Claude session on the owner's behalf. **It is not the clinical co-author's
comparison and not a sign-off.**

- Old app: https://neomortalsurv.net (two decimals)
- New calculator: https://neomortalsurv.net:8443 (one decimal under "Details", whole
  percent in the headline)
- Model version on the new site: `deepsurv-vlbw-1.0.0`

## Cases 1–3 (entered by hand on both sites)

| # | Case | Old app: log-risk; day 7 / 28 / 100, % | New calculator: log-risk; day 7 / 28 / 100, % (headline) | Expected | Match |
|---|---|---|---|---|---|
| 1 | Article Figure 8: BOH yes, 900 g, Apgar 3, GA 27, RF III, HR 80, SpO2 55, all four diagnoses yes | 1.210; 65.22 / 39.52 / 5.63 | 1.210; 65.2 / 39.5 / 5.6 (65 / 40 / 6) | 1.210; 65.22 / 39.52 / 5.63 | yes |
| 2 | 400 g, Apgar 0, GA 20, HR 60, SpO2 40, BOH no, RF II, RDS yes only | 0.647; 78.39 / 58.93 / 19.41 | 0.647; 78.4 / 58.9 / 19.4 (78 / 59 / 19) | 0.647; 78.39 / 58.93 / 19.41 | yes |
| 3 | same as 2, NEC yes only | −0.681; 93.76 / 86.93 / 64.78 | −0.681; 93.8 / 86.9 / 64.8 (94 / 87 / 65) | −0.681; 93.76 / 86.93 / 64.78 | yes |
| 4–10 | `TODO(clinical-review)`: seven realistic cases chosen by the clinical co-author | | | | not done |

Warnings field on the new site: "None" in all three cases.

Note from the operator: the first attempt at case 1 on the old app returned 0.572
because the "Bad obstetric history = Yes" click had not registered. After correcting
the input the result was 1.210.

## Other checks on the new calculator

- Russian interface: works; case 3 shows 93,8 / 86,9 / 64,8 % and log-risk −0,681
  (decimal comma, space before %).
- English interface: checked for cases 1–3.
- Report page (`/report`): opens from "Print report"; shows inputs, probabilities,
  log-risk, model version, limitations, citation and the blank case-code line. Checked
  on screen only; not sent to a printer.

## Not done

- Cases 4–10 (need the co-author's cases).
- Phone, ward PC, hospital network and whether `:8443` is reachable from there.
- Printed output.
- Sign-off by the clinical co-author (name, date).
