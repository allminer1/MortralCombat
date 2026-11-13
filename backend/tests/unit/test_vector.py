import json

import numpy as np
import pytest

from app.inference import InputError, build_vector, default_model_dir, scale


@pytest.fixture(scope="module")
def raw_spec() -> dict:
    return json.loads((default_model_dir() / "feature_spec.json").read_text(encoding="utf-8"))


def test_order_equals_feature_names_in_spec(spec, raw_spec):
    """Spec 5.2: the vector order is the `feature_names` stored in the spec."""
    assert list(spec.feature_names) == raw_spec["feature_names"]
    assert [f.scaler_name for f in spec.features] == raw_spec["feature_names"]
    by_scaler_name = {f["scaler_name"]: f["api_field"] for f in raw_spec["features"]}
    assert list(spec.api_fields) == [by_scaler_name[n] for n in raw_spec["feature_names"]]


def test_each_value_lands_in_its_own_slot(spec):
    """Distinct value per field: slot i must hold the value of the i-th feature name."""
    inputs = {f.api_field: 1000 + f.position for f in spec.features}
    vector = build_vector(inputs, spec)
    for i, name in enumerate(spec.feature_names):
        feature = next(f for f in spec.features if f.scaler_name == name)
        assert vector[i] == inputs[feature.api_field]


def test_dict_order_does_not_matter(spec, figure_8):
    reversed_inputs = dict(reversed(list(figure_8.items())))
    assert np.array_equal(build_vector(figure_8, spec), build_vector(reversed_inputs, spec))


def test_booleans_become_zero_and_one(spec, figure_8):
    as_bool = {
        f.api_field: bool(figure_8[f.api_field]) if f.type == "bool" else figure_8[f.api_field]
        for f in spec.features
    }
    assert np.array_equal(build_vector(as_bool, spec), build_vector(figure_8, spec))


def test_missing_and_unknown_fields_are_rejected(spec, figure_8):
    some_field = spec.api_fields[0]
    with pytest.raises(InputError):
        build_vector({k: v for k, v in figure_8.items() if k != some_field}, spec)
    with pytest.raises(InputError):
        build_vector({**figure_8, "patient_name": 1}, spec)


def test_scaling_is_float64_then_float32(spec, raw_spec, figure_8):
    x = build_vector(figure_8, spec)
    assert x.dtype == np.float64
    z = scale(x, spec)
    assert z.dtype == np.float32
    mean = np.array([f["mean"] for f in raw_spec["features"]])
    sd = np.array([f["scale"] for f in raw_spec["features"]])
    assert np.array_equal(z, ((x - mean) / sd).astype(np.float32))


def test_swapping_two_fields_changes_the_output(spec, predictor, golden):
    """Spec 5.2: permuting two fields changes the output. Checked for every pair of the
    boolean diagnosis-type fields, where a silent swap is possible (the legacy bug)."""
    bools = [f.api_field for f in spec.features if f.type == "bool"]
    base = next(c for c in golden["cases"] if c["id"] == "all_min")["inputs"]
    for i, a in enumerate(bools):
        for b in bools[i + 1 :]:
            only_a = predictor.log_risk({**base, a: 1})
            only_b = predictor.log_risk({**base, b: 1})
            assert abs(only_a - only_b) > 1e-3, (a, b)
