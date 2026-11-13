"""Read-only access to the frozen artifacts in legacy/ for the scripts in tools/.

Nothing here builds a positional input vector. Column order always comes from the
scaler's own `feature_names_in_` (export) or from `model/feature_spec.json`
(everything after the export).
"""

from __future__ import annotations

import csv
import hashlib
import warnings
from pathlib import Path

import joblib
import torch
import torch.nn as nn

REPO = Path(__file__).resolve().parent.parent
LEGACY = REPO / "legacy"
MODEL_DIR = REPO / "model"

WEIGHTS = LEGACY / "survival_model.pth"
SCALER = LEGACY / "scaler1.pkl"
BASELINE = LEGACY / "baseline_hazard.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_network() -> nn.Sequential:
    """Architecture of docs/REBUILD_SPEC.md Section 2.1."""
    return nn.Sequential(
        nn.Linear(11, 511), nn.ReLU(), nn.BatchNorm1d(511), nn.Dropout(0.201),
        nn.Linear(511, 141), nn.ReLU(), nn.BatchNorm1d(141), nn.Dropout(0.496),
        nn.Linear(141, 127), nn.ReLU(), nn.BatchNorm1d(127), nn.Dropout(0.106),
        nn.Linear(127, 16), nn.ReLU(), nn.BatchNorm1d(16), nn.Dropout(0.28),
        nn.Linear(16, 1),
    )  # fmt: skip


def load_network() -> nn.Sequential:
    net = build_network()
    net.load_state_dict(torch.load(WEIGHTS, map_location="cpu"))
    net.eval()
    return net


def load_scaler():
    """The fitted StandardScaler. Only export_model.py and make_golden.py unpickle it."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # scikit-learn version notice on unpickle
        return joblib.load(SCALER)


def load_baseline() -> tuple[list[float], list[float]]:
    """(event times in days, baseline cumulative hazard), as written in the CSV."""
    with open(BASELINE, newline="") as fh:
        rows = list(csv.reader(fh))[1:]
    return [float(r[0]) for r in rows], [float(r[1]) for r in rows]
