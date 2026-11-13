"""Regenerate model/ from the frozen artifacts in legacy/ (docs/REBUILD_SPEC.md 5.4).

    make export-model          (= cd tools && uv run python export_model.py)

Writes
    model/deepsurv.onnx          eval-mode network, dynamic batch axis
    model/feature_spec.json      single source of truth: order, names, ranges, scaler
    model/baseline_hazard.json   baseline cumulative hazard, step function
    model/model_card.json        version, sha256 of every artifact, citation, cohort

Nothing in legacy/ is modified. The output contains no timestamps, so running the
script twice gives byte-identical files. After this step the pickle is not needed
by anything except tools/make_golden.py (reference outputs).
"""

from __future__ import annotations

import json
import sys

import numpy as np
import onnx
import onnxruntime as ort
import torch

import legacy_artifacts as la

MODEL_VERSION = "deepsurv-vlbw-1.0.0"
OPSET = 17

# The input order is never typed here: it is read from the scaler's own
# `feature_names_in_` (the order confirmed by the gate, docs/DECISIONS.md, outcome A).
# tools/make_golden.py checks the gate's anchor cases against the result.

# Per-feature metadata, keyed by the scaler's column name (spec 5.1). Hard ranges
# are the legacy slider limits. This dict is keyed by name; its order is irrelevant.
FEATURE_META = {
    "BOH": {"api_field": "bad_obstetric_history", "type": "bool"},
    "weight": {"api_field": "birth_weight_g", "type": "int", "min": 400, "max": 2000, "unit": "g"},
    "Apgar5": {"api_field": "apgar_5min", "type": "int", "min": 0, "max": 10},
    "GDW": {"api_field": "gestational_age_weeks", "type": "int", "min": 20, "max": 42, "unit": "weeks"},
    "RF": {"api_field": "respiratory_failure_grade", "type": "enum", "values": [2, 3]},
    "HR": {"api_field": "heart_rate_bpm", "type": "int", "min": 60, "max": 200, "unit": "bpm"},
    "Saturation": {"api_field": "spo2_percent", "type": "int", "min": 40, "max": 100, "unit": "%"},
    "RDS": {"api_field": "rds", "type": "bool"},
    "IVH": {"api_field": "ivh", "type": "bool"},
    "DIC": {"api_field": "dic", "type": "bool"},
    "NE": {"api_field": "nec", "type": "bool"},
}

CITATION = {
    "authors": "Bozhbanbayeva N, Abilbayeva A, Tarabayeva A, Isgandarov I, Tolykbayev T, "
    "Adilbekova I, Yelyubayeva D.",
    "title": "A deep-learning approach to predict mortality in very-low-birth-weight infants "
    "treated in the intensive care units using DeepSurv.",
    "journal": "Front. Pediatr.",
    "year": 2026,
    "volume": "14",
    "article": "1801840",
    "doi": "10.3389/fped.2026.1801840",
}

# Figures from the article as quoted in docs/REBUILD_SPEC.md Section 1.
COHORT = {
    "n_total": 958,
    "n_train": 672,
    "n_test": 286,
    "centres": 4,
    "country": "Kazakhstan",
    "period": "2021-01 to 2025-05",
    "population": "very-low-birth-weight neonates treated in the NICU",
    "exclusions": ["birth weight above 1500 g", "severe congenital malformations"],
    "feature_selection": "Boruta, 11 predictors",
}
PERFORMANCE = {
    "dataset": "held-out test set, n = 286",
    "c_index": {"value": 0.86, "ci95": [0.81, 0.90]},
    "auc_overall": {"value": 0.95, "ci95": [0.91, 0.98]},
    "integrated_brier_score": 0.071,
    "external_validation": False,
}


def write_json(path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def export_onnx(path) -> float:
    """Export the network and return max |onnx - torch| on random scaled inputs."""
    net = la.load_network()
    torch.onnx.export(
        net,
        (torch.zeros(1, 11, dtype=torch.float32),),
        str(path),
        input_names=["z"],
        output_names=["log_risk"],
        dynamic_axes={"z": {0: "batch"}, "log_risk": {0: "batch"}},
        opset_version=OPSET,
        dynamo=False,
    )
    onnx.checker.check_model(onnx.load(str(path)))

    z = np.random.default_rng(0).normal(size=(2000, 11)).astype(np.float32)
    with torch.no_grad():
        ref = net(torch.from_numpy(z)).numpy()
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    batched = session.run(None, {"z": z})[0]
    single = np.vstack([session.run(None, {"z": z[i : i + 1]})[0] for i in range(200)])
    return float(max(np.abs(batched - ref).max(), np.abs(single - ref[:200]).max()))


def feature_spec() -> dict:
    scaler = la.load_scaler()
    names = [str(n) for n in scaler.feature_names_in_]
    if set(names) != set(FEATURE_META):
        raise SystemExit("FEATURE_META does not cover exactly the scaler's columns; stop.")
    features = []
    for position, (name, mean, scale) in enumerate(zip(names, scaler.mean_, scaler.scale_), start=1):
        features.append(
            {"position": position, "scaler_name": name, **FEATURE_META[name], "mean": float(mean), "scale": float(scale)}
        )
    return {
        "model_version": MODEL_VERSION,
        "description": "Single source of truth for input order, names, ranges and scaling. "
        "Generated by tools/export_model.py; do not edit by hand.",
        "feature_names": names,
        "scaling": "z = (x - mean) / scale in float64, then cast to float32",
        "scaler_n_samples_seen": int(scaler.n_samples_seen_),
        "features": features,
    }


def baseline_hazard() -> dict:
    times, hazard = la.load_baseline()
    if times != sorted(times) or len(set(times)) != len(times):
        raise SystemExit("baseline hazard times are not strictly increasing; stop.")
    if any(t != int(t) for t in times):
        raise SystemExit("baseline hazard times are not whole days; stop.")
    return {
        "model_version": MODEL_VERSION,
        "description": "Baseline cumulative hazard H0(t). Step function: H0(t) is the value at "
        "the largest event time <= t, and 0 before the first event time.",
        "time_unit": "day",
        "times": [int(t) for t in times],
        "cumulative_hazard": hazard,
    }


def main() -> int:
    la.MODEL_DIR.mkdir(exist_ok=True)
    onnx_path = la.MODEL_DIR / "deepsurv.onnx"
    spec_path = la.MODEL_DIR / "feature_spec.json"
    hazard_path = la.MODEL_DIR / "baseline_hazard.json"
    card_path = la.MODEL_DIR / "model_card.json"

    max_diff = export_onnx(onnx_path)
    if max_diff > 1e-5:
        raise SystemExit(f"ONNX differs from PyTorch by {max_diff:.2e}; stop.")
    write_json(spec_path, feature_spec())
    write_json(hazard_path, baseline_hazard())
    write_json(
        card_path,
        {
            "model_version": MODEL_VERSION,
            "model_type": "DeepSurv (Cox proportional hazards with a neural-network log-risk)",
            "intended_use": "research",
            "output": "S(t) = exp(-H0(t) * exp(g(z))), t in days",
            "artifacts": {p.name: {"sha256": la.sha256(p)} for p in (onnx_path, spec_path, hazard_path)},
            "source_artifacts": {
                f"legacy/{p.name}": {"sha256": la.sha256(p)} for p in (la.WEIGHTS, la.SCALER, la.BASELINE)
            },
            "export": {
                "tool": "tools/export_model.py",
                "onnx_opset": OPSET,
                "torch": torch.__version__,
                "onnx": onnx.__version__,
            },
            "citation": CITATION,
            "cohort": COHORT,
            "reported_performance": PERFORMANCE,
        },
    )

    print(f"ONNX vs PyTorch, 2000 random vectors (batched and single-row): max |diff| = {max_diff:.1e}")
    for p in (onnx_path, spec_path, hazard_path, card_path):
        print(f"{la.sha256(p)}  model/{p.name}  ({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
