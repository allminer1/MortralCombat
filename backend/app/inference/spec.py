"""Loader for model/feature_spec.json, the single source of truth for input order,
names, ranges and scaling. Nothing in the backend retypes any of these."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np


def default_model_dir() -> Path:
    """`MODEL_DIR` if set, else the repository's model/ directory."""
    env = os.environ.get("MODEL_DIR")
    return Path(env) if env else Path(__file__).resolve().parents[3] / "model"


@dataclass(frozen=True)
class Feature:
    position: int  # 1-based position in MODEL_ORDER
    scaler_name: str
    api_field: str
    type: str  # "bool" | "int" | "enum"
    mean: float
    scale: float
    min: int | None = None
    max: int | None = None
    values: tuple[int, ...] | None = None
    unit: str | None = None


@dataclass(frozen=True)
class FeatureSpec:
    model_version: str
    feature_names: tuple[str, ...]  # scaler names in MODEL_ORDER
    features: tuple[Feature, ...]  # in MODEL_ORDER

    @property
    def api_fields(self) -> tuple[str, ...]:
        """API field names in MODEL_ORDER."""
        return tuple(f.api_field for f in self.features)

    @property
    def mean(self) -> np.ndarray:
        return np.array([f.mean for f in self.features], dtype=np.float64)

    @property
    def scale(self) -> np.ndarray:
        return np.array([f.scale for f in self.features], dtype=np.float64)

    @classmethod
    def load(cls, model_dir: Path | None = None) -> FeatureSpec:
        path = (model_dir or default_model_dir()) / "feature_spec.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        features = tuple(
            Feature(
                position=f["position"],
                scaler_name=f["scaler_name"],
                api_field=f["api_field"],
                type=f["type"],
                mean=f["mean"],
                scale=f["scale"],
                min=f.get("min"),
                max=f.get("max"),
                values=tuple(f["values"]) if "values" in f else None,
                unit=f.get("unit"),
            )
            for f in sorted(raw["features"], key=lambda f: f["position"])
        )
        spec = cls(
            model_version=raw["model_version"], feature_names=tuple(raw["feature_names"]), features=features
        )
        spec._check()
        return spec

    def _check(self) -> None:
        if tuple(f.scaler_name for f in self.features) != self.feature_names:
            raise ValueError("feature_spec.json: features do not follow feature_names")
        if [f.position for f in self.features] != list(range(1, len(self.features) + 1)):
            raise ValueError("feature_spec.json: positions are not 1..n")
        if len(set(self.api_fields)) != len(self.features):
            raise ValueError("feature_spec.json: duplicate api_field")
        if any(f.scale <= 0 for f in self.features):
            raise ValueError("feature_spec.json: non-positive scale")
