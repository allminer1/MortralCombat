"""The one place where named inputs become a positional vector (spec 5.2).

The order is read from the feature spec. No other module may index inputs by position.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from app.inference.spec import FeatureSpec


class InputError(ValueError):
    """Inputs do not consist of exactly the spec's fields."""


def build_vector(inputs: Mapping[str, bool | int | float], spec: FeatureSpec) -> np.ndarray:
    """Raw values in MODEL_ORDER, float64, shape (n_features,). Booleans become 0 / 1."""
    expected = set(spec.api_fields)
    missing = sorted(expected - set(inputs))
    unknown = sorted(set(inputs) - expected)
    if missing or unknown:
        raise InputError(f"missing fields: {missing}; unknown fields: {unknown}")
    return np.array([float(inputs[f.api_field]) for f in spec.features], dtype=np.float64)


def scale(x: np.ndarray, spec: FeatureSpec) -> np.ndarray:
    """z = (x - mean) / scale in float64, then cast to float32."""
    return ((np.asarray(x, dtype=np.float64) - spec.mean) / spec.scale).astype(np.float32)
