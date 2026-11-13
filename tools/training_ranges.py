"""Observed ranges of the continuous inputs in the training set (spec 5.3, Section 11 item 3).

TO BE RUN BY THE PROJECT OWNER. Reads the training data file and prints summary numbers
only: for each continuous input the number of values, minimum, 1st percentile, 99th
percentile and maximum. No rows and no per-patient records are printed or written
anywhere. Claude does not open the data file.

    cd tools && uv run python training_ranges.py --train-csv /path/to/training-file.csv

Which columns to read comes from model/feature_spec.json (the inputs of type "int"). The
script first checks that the file really is the training set: the number of rows and the
column means must equal what the frozen scaler recorded. If they do not, it says so and
prints nothing else.

Paste the output into the conversation (or docs/PROGRESS.md). The numbers are what the
`OUTSIDE_TRAINING_RANGE` warning needs; whether to warn at min / max or at the 1st / 99th
percentile is the owner's and co-authors' decision.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

SPEC = Path(__file__).resolve().parent.parent / "model" / "feature_spec.json"
MEAN_TOLERANCE = 1e-6  # relative; the scaler's means were computed from this very file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--train-csv", required=True, type=Path, help="the training set (672 rows)")
    parser.add_argument("--spec", type=Path, default=SPEC, help=argparse.SUPPRESS)  # for the self-test
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    features = spec["features"]
    expected_rows = spec["scaler_n_samples_seen"]

    frame = pd.read_csv(args.train_csv)
    missing = [f["scaler_name"] for f in features if f["scaler_name"] not in frame.columns]
    if missing:
        print(f"Not the expected file: columns missing: {missing}")
        return 1
    if len(frame) != expected_rows:
        print(f"Not the training set: {len(frame)} rows, the scaler was fitted on {expected_rows}.")
        return 1
    off = []
    for f in features:
        mean = float(frame[f["scaler_name"]].mean())
        if abs(mean - f["mean"]) > MEAN_TOLERANCE * max(1.0, abs(f["mean"])):
            off.append(f["scaler_name"])
    if off:
        print(f"Not the training set: column means differ from the scaler's for {off}.")
        return 1

    print(f"Training set confirmed: {expected_rows} rows; all {len(features)} column means equal the scaler's.")
    print()
    print(f"{'input':<24}{'n':>5}{'min':>9}{'p1':>9}{'p99':>9}{'max':>9}   form accepts")
    for f in features:
        if f["type"] != "int":
            continue
        column = frame[f["scaler_name"]].dropna()
        low, p1, p99, high = (column.min(), column.quantile(0.01), column.quantile(0.99), column.max())
        print(
            f"{f['api_field']:<24}{len(column):>5}{low:>9.5g}{p1:>9.5g}{p99:>9.5g}{high:>9.5g}"
            f"   {f['min']}–{f['max']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
