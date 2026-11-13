import json
from pathlib import Path

import pytest

from app.inference import BaselineHazard, FeatureSpec, Predictor

GOLDEN = Path(__file__).parent / "golden" / "golden.json"


@pytest.fixture(scope="session")
def predictor() -> Predictor:
    return Predictor()


@pytest.fixture(scope="session")
def spec() -> FeatureSpec:
    return FeatureSpec.load()


@pytest.fixture(scope="session")
def hazard() -> BaselineHazard:
    return BaselineHazard.load()


@pytest.fixture(scope="session")
def golden() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def figure_8(golden) -> dict:
    """Inputs of the article's Figure 8 case, by name."""
    return next(c for c in golden["cases"] if c["id"] == "anchor_figure_8")["inputs"]
