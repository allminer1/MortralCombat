"""Baseline cumulative hazard H0(t) as a step function, and the survival formula."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.inference.spec import default_model_dir

CURVE_DAYS = tuple(range(0, 101))  # integer days 0..100
REPORTED_DAYS = (7, 28, 100)


@dataclass(frozen=True)
class BaselineHazard:
    times: np.ndarray  # strictly increasing event times, days
    cumulative_hazard: np.ndarray

    @classmethod
    def load(cls, model_dir: Path | None = None) -> BaselineHazard:
        path = (model_dir or default_model_dir()) / "baseline_hazard.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        times = np.asarray(raw["times"], dtype=np.float64)
        hazard = np.asarray(raw["cumulative_hazard"], dtype=np.float64)
        if times.shape != hazard.shape or times.size == 0 or np.any(np.diff(times) <= 0):
            raise ValueError("baseline_hazard.json: times must be strictly increasing and match the hazard")
        return cls(times=times, cumulative_hazard=hazard)

    def h0(self, days) -> np.ndarray:
        """H0 at the largest event time <= t; 0 before the first event time."""
        days = np.asarray(days, dtype=np.float64)
        index = np.searchsorted(self.times, days, side="right")  # number of event times <= t
        padded = np.concatenate(([0.0], self.cumulative_hazard))
        return padded[index]


def survival(h0: np.ndarray, log_risk: float) -> np.ndarray:
    """S(t) = exp(-H0(t) * exp(g)), float64."""
    return np.exp(-np.asarray(h0, dtype=np.float64) * np.exp(np.float64(log_risk)))
