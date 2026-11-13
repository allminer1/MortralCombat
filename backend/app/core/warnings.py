"""Soft warnings (spec 5.3): returned as codes with a result, never as errors."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.inference import FeatureSpec

RANGES_FILE = Path(__file__).resolve().parents[1] / "data" / "training_ranges.json"
WEIGHT_FIELD = "birth_weight_g"
COHORT_MAX_WEIGHT_G = 1500  # the article: infants above 1,500 g were excluded from model development

WEIGHT_ABOVE_COHORT = "WEIGHT_ABOVE_COHORT"
OUTSIDE_TRAINING_RANGE = "OUTSIDE_TRAINING_RANGE"


@dataclass(frozen=True)
class Warnings:
    codes: list[str]
    outside_training_range: list[str]  # API field names, in the spec's order


class WarningRules:
    """`training_ranges`: {api_field: {"min": .., "max": ..}} for the continuous inputs."""

    def __init__(self, spec: FeatureSpec, ranges_file: Path = RANGES_FILE) -> None:
        self.training_ranges: dict[str, dict[str, int]] = json.loads(ranges_file.read_text(encoding="utf-8"))[
            "ranges"
        ]
        continuous = [f.api_field for f in spec.features if f.type == "int"]
        if sorted(self.training_ranges) != sorted(continuous):
            raise RuntimeError(
                "training_ranges.json must list exactly the continuous inputs of the feature spec"
            )
        self._order = continuous

    def check(self, inputs: Mapping[str, bool | int | float]) -> Warnings:
        codes = []
        if inputs[WEIGHT_FIELD] > COHORT_MAX_WEIGHT_G:
            codes.append(WEIGHT_ABOVE_COHORT)
        outside = [
            name
            for name in self._order
            if not self.training_ranges[name]["min"] <= inputs[name] <= self.training_ranges[name]["max"]
        ]
        if outside:
            codes.append(OUTSIDE_TRAINING_RANGE)
        return Warnings(codes=codes, outside_training_range=outside)
