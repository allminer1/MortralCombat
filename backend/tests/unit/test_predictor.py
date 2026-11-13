import json

import pytest

from app.inference import Predictor, default_model_dir
from app.inference.predictor import ARTIFACTS


def test_curve_shape(predictor, figure_8):
    result = predictor.predict(figure_8)
    assert len(result.curve) == 101
    assert result.curve[0] == 1.0
    assert all(a >= b for a, b in zip(result.curve, result.curve[1:], strict=False))
    assert all(0.0 <= s <= 1.0 for s in result.curve)
    assert set(result.survival_points) == {7, 28, 100}


def test_same_input_same_output(predictor, figure_8):
    assert predictor.predict(figure_8) == predictor.predict(figure_8)


def test_artifact_hashes_match_model_card(predictor):
    card = json.loads((default_model_dir() / "model_card.json").read_text(encoding="utf-8"))
    assert predictor.artifact_sha256 == {n: card["artifacts"][n]["sha256"] for n in ARTIFACTS}


def test_tampered_artifact_is_refused(tmp_path):
    for path in default_model_dir().iterdir():
        (tmp_path / path.name).write_bytes(path.read_bytes())
    with open(tmp_path / "baseline_hazard.json", "a", encoding="utf-8") as fh:
        fh.write(" ")
    with pytest.raises(RuntimeError):
        Predictor(tmp_path)


def test_runtime_has_no_training_libraries():
    """Spec Section 4: no torch, pycox, scikit-learn or pandas in the backend environment."""
    import importlib.util

    for name in ("torch", "pycox", "sklearn", "pandas"):
        assert importlib.util.find_spec(name) is None, name
