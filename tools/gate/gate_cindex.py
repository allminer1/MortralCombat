"""Feature-order gate, C-index check (docs/REBUILD_SPEC.md, Section 3.4 step 4).

TO BE RUN BY THE PROJECT OWNER. Reads the held-out test set and prints summary
numbers only: number of rows, number of events, and the C-index of the frozen
model when the four diagnosis columns are fed in

  * scaler order  (RDS, IVH, DIC, NE)  - the order the StandardScaler was fitted on
  * app order     (IVH, DIC, NE, RDS)  - the order the legacy Streamlit app sends

No rows and no per-patient values are printed or written anywhere.

    python tools/gate/gate_cindex.py --test-csv /path/to/MortalityKidsTest.csv

Expected: about 0.86 for the ordering the network was trained on, clearly lower
for the other one.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from legacy_model import SCALER_ORDER, LegacyModel

TIME_COL = "Days"
EVENT_COL = "Survival"  # 1 = death (event), 0 = censored, as in the training script
DEFAULT_CSV = Path(__file__).resolve().parents[3] / "PythonProject" / "MortalityKidsTest.csv"


def harrell_c(time: np.ndarray, event: np.ndarray, risk: np.ndarray) -> float:
    """Harrell's C: among comparable pairs, share where the earlier death has higher risk."""
    concordant = 0.0
    comparable = 0
    for i in np.flatnonzero(event == 1):
        later = time > time[i]
        comparable += int(later.sum())
        concordant += float((risk[i] > risk[later]).sum()) + 0.5 * float((risk[i] == risk[later]).sum())
    return concordant / comparable if comparable else float("nan")


def antolini_c(model: LegacyModel, g: np.ndarray, time: np.ndarray, event: np.ndarray) -> float:
    """Time-dependent concordance (Antolini), the metric the training script reports."""
    from pycox.evaluation import EvalSurv

    surv = pd.DataFrame(model.survival_matrix(g), index=model.times)
    return float(EvalSurv(surv, time, event, censor_surv="km").concordance_td("antolini"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--test-csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    if not args.test_csv.is_file():
        print(f"file not found: {args.test_csv}")
        return 2

    df = pd.read_csv(args.test_csv)
    needed = SCALER_ORDER + [TIME_COL, EVENT_COL]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        print(f"missing columns: {missing}")
        return 2

    df = df[needed]
    df = df[df[TIME_COL] > 0]  # same filter as the training script
    try:
        df = df.astype("float64")
    except (TypeError, ValueError):
        bad = [c for c in needed if not pd.api.types.is_numeric_dtype(df[c])]
        print(f"non-numeric columns (expected numbers / 0-1 flags): {bad}")
        return 2
    n_missing = int(df.isna().any(axis=1).sum())
    if n_missing:
        print(f"rows with missing values: {n_missing} (dropped)")
        df = df.dropna()

    time = df[TIME_COL].to_numpy(dtype="float32")
    event = df[EVENT_COL].to_numpy().astype(int)
    columns = {name: df[name].to_numpy() for name in SCALER_ORDER}

    model = LegacyModel()
    print(f"n = {len(df)}   events = {int(event.sum())}")
    print(f"{'ordering':10s} {'C (Antolini)':>13s} {'C (Harrell)':>12s}")
    for order in ("scaler", "app"):
        g = model.log_risk(model.arrange(columns, order))
        try:
            c_td = f"{antolini_c(model, g, time, event):.4f}"
        except ImportError:
            c_td = "pycox n/a"
        print(f"{order:10s} {c_td:>13s} {harrell_c(time, event, g):12.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
