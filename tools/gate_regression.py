"""Feature-order gate, regression cases (docs/REBUILD_SPEC.md, Sections 2.4 and 3.2).

Scores three fixed, synthetic input cases with the frozen legacy artifacts under
both feature orderings and checks them against the recorded numbers. Uses no
patient data.

    python tools/gate_regression.py

Exit code 0 when every check passes.
"""

from __future__ import annotations

import sys

import numpy as np

from legacy_model import LegacyModel

DAYS = (7, 28, 100)
TOL_LOG_RISK = 5e-4   # recorded values have three decimals
TOL_PERCENT = 5e-3    # recorded values have two decimals

# Legacy slider defaults (all at minimum), BOH = No, RF = 2, no diagnoses.
BASE = dict(BOH=0, weight=400, Apgar5=0, GDW=20, RF=2, HR=60, Saturation=40, RDS=0, IVH=0, DIC=0, NE=0)

CASES = {
    "RDS = Yes only": {**BASE, "RDS": 1},
    "NEC = Yes only": {**BASE, "NE": 1},
    "Article Figure 8": dict(
        BOH=1, weight=900, Apgar5=3, GDW=27, RF=3, HR=80, Saturation=55, RDS=1, IVH=1, DIC=1, NE=1
    ),
}

# (log-risk, survival % at day 7 / 28 / 100)
EXPECTED = {
    # app order = what https://neomortalsurv.net returned on 2026-11-12
    ("RDS = Yes only", "app"): (-0.681, (93.76, 86.93, 64.78)),
    ("NEC = Yes only", "app"): (1.204, (65.38, 39.74, 5.72)),
    ("Article Figure 8", "app"): (1.210, (65.22, 39.52, 5.63)),
    ("RDS = Yes only", "scaler"): (0.647, (78.39, 58.93, 19.41)),
    ("NEC = Yes only", "scaler"): (-0.681, (93.76, 86.93, 64.78)),
    ("Article Figure 8", "scaler"): (1.210, (65.22, 39.52, 5.63)),
}


def main() -> int:
    model = LegacyModel()
    print(f"scaler columns: {model.scaler_names}  (n_samples_seen = {model.n_train})")
    failures = 0

    for (case, order), (exp_g, exp_s) in EXPECTED.items():
        columns = {k: np.array([v]) for k, v in CASES[case].items()}
        g = float(model.log_risk(model.arrange(columns, order))[0])
        nearest = [100 * np.exp(-model.h0_nearest(d) * np.exp(g)) for d in DAYS]
        step = [100 * np.exp(-model.h0_step(d) * np.exp(g)) for d in DAYS]

        ok = abs(g - exp_g) <= TOL_LOG_RISK
        ok &= all(abs(a - b) <= TOL_PERCENT for a, b in zip(nearest, exp_s))
        # The legacy nearest-row lookup and the correct step lookup must agree on these days.
        ok &= all(abs(a - b) <= 1e-9 for a, b in zip(nearest, step))
        failures += not ok

        shown = " / ".join(f"{v:.2f}" for v in nearest)
        print(f"{'PASS' if ok else 'FAIL'}  {case:17s} {order:6s} order  log-risk {g:+.3f}  S(7/28/100) {shown} %")

    print("all checks passed" if not failures else f"{failures} check(s) FAILED")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
