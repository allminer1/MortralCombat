"""ONNX predictor: named inputs in, log-risk and survival curve out."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import onnxruntime as ort

from app.inference.hazard import CURVE_DAYS, REPORTED_DAYS, BaselineHazard, survival
from app.inference.spec import FeatureSpec, default_model_dir
from app.inference.vector import build_vector, scale

ARTIFACTS = ("deepsurv.onnx", "feature_spec.json", "baseline_hazard.json")


@dataclass(frozen=True)
class Prediction:
    model_version: str
    log_risk: float
    curve: tuple[float, ...]  # S(t) for days 0..100

    @property
    def survival_points(self) -> dict[int, float]:
        """S(t) at the reported days (7, 28, 100)."""
        return {day: self.curve[day] for day in REPORTED_DAYS}


class Predictor:
    """Create once at startup and reuse: holds the single ONNX session."""

    def __init__(self, model_dir: Path | None = None) -> None:
        model_dir = model_dir or default_model_dir()
        card = json.loads((model_dir / "model_card.json").read_text(encoding="utf-8"))
        self.artifact_sha256: dict[str, str] = {}
        for name in ARTIFACTS:
            digest = hashlib.sha256((model_dir / name).read_bytes()).hexdigest()
            if digest != card["artifacts"][name]["sha256"]:
                raise RuntimeError(f"{name}: sha256 differs from model_card.json")
            self.artifact_sha256[name] = digest

        self.spec = FeatureSpec.load(model_dir)
        if self.spec.model_version != card["model_version"]:
            raise RuntimeError("feature_spec.json and model_card.json disagree on model_version")
        self.model_version = self.spec.model_version
        self._h0_curve = BaselineHazard.load(model_dir).h0(CURVE_DAYS)

        self._session = ort.InferenceSession(
            str(model_dir / "deepsurv.onnx"), providers=["CPUExecutionProvider"]
        )
        (model_input,) = self._session.get_inputs()
        self._input_name = model_input.name
        if model_input.shape[-1] != len(self.spec.features):
            raise RuntimeError("ONNX input width differs from the feature spec")

    def log_risk(self, inputs: Mapping[str, bool | int | float]) -> float:
        z = scale(build_vector(inputs, self.spec), self.spec).reshape(1, -1)
        return float(self._session.run(None, {self._input_name: z})[0][0, 0])

    def predict(self, inputs: Mapping[str, bool | int | float]) -> Prediction:
        g = self.log_risk(inputs)
        curve = survival(self._h0_curve, g)
        return Prediction(model_version=self.model_version, log_risk=g, curve=tuple(float(s) for s in curve))
