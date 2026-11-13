"""Write backend/tests/golden/golden.json: reference outputs of the frozen PyTorch model
(docs/REBUILD_SPEC.md 5.4).

    cd tools && uv run python make_golden.py

The reference path is independent of the backend and of the ONNX file:

    named DataFrame (columns = feature_names of model/feature_spec.json)
      -> the original StandardScaler (legacy/scaler1.pkl; it checks the column names)
      -> the PyTorch network in eval mode
      -> S(t) = exp(-H0(t) * exp(g)) with H0 read from legacy/baseline_hazard.csv

Golden data define what is correct (CLAUDE.md rule 4). The file is generated once and
committed. Do not regenerate it to make a failing test pass; the script refuses to
overwrite an existing file unless called with --force, and the recorded anchors of the
spec (Sections 2.4 and 3.2) are checked before anything is written.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pandas as pd
import torch

import legacy_artifacts as la

OUT = la.REPO / "backend" / "tests" / "golden" / "golden.json"
SEED = 20261113
N_RANDOM = 500
DAYS = range(0, 101)

# Recorded anchors: (log-risk to 3 decimals, survival % at day 7 / 28 / 100 to 2 decimals).
# Sources: article Figure 8 (spec 2.4); spec 3.2 cases in the confirmed order
# (docs/DECISIONS.md), equal to the live site after the hot-fix (docs/PROGRESS.md).
ANCHOR_EXPECTED = {
    "anchor_figure_8": (1.210, (65.22, 39.52, 5.63)),
    "anchor_rds_only": (0.647, (78.39, 58.93, 19.41)),
    "anchor_nec_only": (-0.681, (93.76, 86.93, 64.78)),
}


def load_spec() -> dict:
    return json.loads((la.MODEL_DIR / "feature_spec.json").read_text(encoding="utf-8"))


def low(f: dict) -> int:
    return {"bool": 0, "int": f.get("min"), "enum": min(f.get("values", [0]))}[f["type"]]


def high(f: dict) -> int:
    return {"bool": 1, "int": f.get("max"), "enum": max(f.get("values", [0]))}[f["type"]]


def random_value(f: dict, rng: np.random.Generator) -> int:
    if f["type"] == "enum":
        return int(rng.choice(f["values"]))
    return int(rng.integers(low(f), high(f) + 1))


def build_cases(spec: dict) -> list[dict]:
    """Each case: {"id": ..., "inputs": {api_field: int}}. Booleans are stored as 0 / 1."""
    feats = spec["features"]
    all_min = {f["api_field"]: low(f) for f in feats}
    all_max = {f["api_field"]: high(f) for f in feats}

    cases = [
        {
            "id": "anchor_figure_8",
            "inputs": dict(
                bad_obstetric_history=1, birth_weight_g=900, apgar_5min=3, gestational_age_weeks=27,
                respiratory_failure_grade=3, heart_rate_bpm=80, spo2_percent=55, rds=1, ivh=1, dic=1, nec=1,
            ),
        },  # fmt: skip
        {"id": "anchor_rds_only", "inputs": {**all_min, "rds": 1}},
        {"id": "anchor_nec_only", "inputs": {**all_min, "nec": 1}},
        {"id": "all_min", "inputs": all_min},
        {"id": "all_max", "inputs": all_max},
    ]
    for f in feats:  # each field toggled alone, from both corners
        name = f["api_field"]
        cases.append({"id": f"min_but_{name}_max", "inputs": {**all_min, name: all_max[name]}})
        cases.append({"id": f"max_but_{name}_min", "inputs": {**all_max, name: all_min[name]}})

    rng = np.random.default_rng(SEED)
    for i in range(N_RANDOM):
        cases.append({"id": f"random_{i:03d}", "inputs": {f["api_field"]: random_value(f, rng) for f in feats}})

    for case in cases:
        if set(case["inputs"]) != {f["api_field"] for f in feats}:
            raise SystemExit(f"case {case['id']} does not have exactly the 11 fields")
    return cases


def reference_outputs(spec: dict, cases: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    by_api = {f["api_field"]: f["scaler_name"] for f in spec["features"]}
    frame = pd.DataFrame([{by_api[k]: float(v) for k, v in c["inputs"].items()} for c in cases])
    frame = frame[spec["feature_names"]]  # named columns; the scaler validates the names

    scaler = la.load_scaler()
    z = scaler.transform(frame).astype(np.float32)
    with torch.no_grad():
        g = la.load_network()(torch.from_numpy(z)).numpy().reshape(-1)

    times, hazard = (np.asarray(a, dtype=np.float64) for a in la.load_baseline())
    h0 = np.array([hazard[times <= d][-1] if (times <= d).any() else 0.0 for d in DAYS])
    survival = np.exp(-np.outer(np.exp(g.astype(np.float64)), h0))  # (n_cases, 101)
    return g, survival


def check_anchors(cases: list[dict], g: np.ndarray, survival: np.ndarray) -> None:
    index = {c["id"]: i for i, c in enumerate(cases)}
    for name, (exp_g, exp_s) in ANCHOR_EXPECTED.items():
        i = index[name]
        got_s = [100 * survival[i, d] for d in (7, 28, 100)]
        ok = abs(float(g[i]) - exp_g) <= 5e-4 and all(abs(a - b) <= 5e-3 for a, b in zip(got_s, exp_s))
        shown = " / ".join(f"{v:.2f}" for v in got_s)
        print(f"{'PASS' if ok else 'FAIL'}  {name:16s} log-risk {g[i]:+.3f}  S(7/28/100) {shown} %")
        if not ok:
            raise SystemExit("anchor mismatch: nothing written")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="overwrite an existing golden.json")
    args = parser.parse_args()
    if OUT.exists() and not args.force:
        raise SystemExit(f"{OUT} exists. Golden data are not regenerated to fix a test (CLAUDE.md rule 4).")

    spec = load_spec()
    cases = build_cases(spec)
    g, survival = reference_outputs(spec, cases)
    check_anchors(cases, g, survival)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "description": "Reference outputs of the frozen PyTorch model. Generated by "
            "tools/make_golden.py. Never edit or regenerate to make a test pass.",
            "model_version": spec["model_version"],
            "source_sha256": {p.name: la.sha256(p) for p in (la.WEIGHTS, la.SCALER, la.BASELINE)},
            "seed": SEED,
            "n_cases": len(cases),
            "survival": "S(t) for integer days 0..100",
            "tolerance": {"log_risk": 1e-4, "survival": 1e-5},
            "anchors_percent_day_7_28_100": {
                k: {"log_risk": v[0], "survival_percent": list(v[1])} for k, v in ANCHOR_EXPECTED.items()
            },
        },
        "cases": [
            {**c, "log_risk": float(g[i]), "survival": [float(s) for s in survival[i]]}
            for i, c in enumerate(cases)
        ],
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} cases to {OUT.relative_to(la.REPO)}  sha256 {la.sha256(OUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
