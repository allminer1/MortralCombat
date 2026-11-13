"""Phase 0 helper: load the frozen legacy artifacts and score inputs under either
feature ordering. Used only by the gate scripts in this directory.

This is NOT the rebuild's inference code. It exists to compare the two orderings
described in docs/REBUILD_SPEC.md, Section 3. Nothing in legacy/ is modified.
"""

from __future__ import annotations

import csv
import warnings
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn as nn

LEGACY = Path(__file__).resolve().parents[2] / "legacy"

# Order of the columns the StandardScaler was fitted on (scaler1.pkl feature_names_in_).
SCALER_ORDER = ["BOH", "weight", "Apgar5", "GDW", "RF", "HR", "Saturation", "RDS", "IVH", "DIC", "NE"]
# Order in which the legacy Streamlit app builds its unnamed input array
# (legacy/MortalCombat.py, FEATURES; "weight.g." there is "weight" here).
APP_ORDER = ["BOH", "weight", "Apgar5", "GDW", "RF", "HR", "Saturation", "IVH", "DIC", "NE", "RDS"]

ORDERS = {"scaler": SCALER_ORDER, "app": APP_ORDER}


def build_network() -> nn.Sequential:
    return nn.Sequential(
        nn.Linear(11, 511), nn.ReLU(), nn.BatchNorm1d(511), nn.Dropout(0.201),
        nn.Linear(511, 141), nn.ReLU(), nn.BatchNorm1d(141), nn.Dropout(0.496),
        nn.Linear(141, 127), nn.ReLU(), nn.BatchNorm1d(127), nn.Dropout(0.106),
        nn.Linear(127, 16), nn.ReLU(), nn.BatchNorm1d(16), nn.Dropout(0.28),
        nn.Linear(16, 1),
    )


class LegacyModel:
    def __init__(self, legacy_dir: Path = LEGACY) -> None:
        self.net = build_network()
        state = torch.load(legacy_dir / "survival_model.pth", map_location="cpu")
        self.net.load_state_dict(state)
        self.net.eval()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # scikit-learn version notice on unpickle
            scaler = joblib.load(legacy_dir / "scaler1.pkl")
        self.scaler_names = [str(n) for n in scaler.feature_names_in_]
        self.n_train = int(scaler.n_samples_seen_)
        self.mean = np.asarray(scaler.mean_, dtype=np.float64)
        self.scale = np.asarray(scaler.scale_, dtype=np.float64)
        if self.scaler_names != SCALER_ORDER:
            raise RuntimeError(f"scaler column order is not the expected one: {self.scaler_names}")

        with open(legacy_dir / "baseline_hazard.csv", newline="") as fh:
            rows = list(csv.reader(fh))[1:]
        self.times = np.array([float(r[0]) for r in rows])
        self.h0 = np.array([float(r[1]) for r in rows])

    def log_risk(self, x: np.ndarray) -> np.ndarray:
        """x: (n, 11) raw values, already arranged in the positional order to test."""
        z = (np.asarray(x, dtype=np.float64) - self.mean) / self.scale
        with torch.no_grad():
            g = self.net(torch.tensor(z, dtype=torch.float32))
        return g.numpy().reshape(-1)

    def arrange(self, columns: dict[str, np.ndarray], order: str) -> np.ndarray:
        """Place named columns into positions following `order` ("scaler" or "app")."""
        return np.column_stack([np.asarray(columns[name], dtype=np.float64) for name in ORDERS[order]])

    def h0_nearest(self, day: float) -> float:
        """Legacy app behaviour: baseline hazard of the nearest tabulated day."""
        return float(self.h0[np.argmin(np.abs(self.times - day))])

    def h0_step(self, day: float) -> float:
        """Step function: value at the largest event time <= day, 0 before the first."""
        mask = self.times <= day
        return float(self.h0[mask][-1]) if mask.any() else 0.0

    def survival_matrix(self, g: np.ndarray) -> np.ndarray:
        """S(t) at every tabulated time, shape (len(times), n)."""
        return np.exp(-np.outer(self.h0, np.exp(g)))
