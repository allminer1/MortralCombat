"""OUTSIDE_TRAINING_RANGE: warn when a continuous input is below the smallest or above
the largest value in the training set (owner's decision of 2026-11-13). The numbers are
read from GET /api/v1/model, not typed here."""

import json

import pytest

from app.core.warnings import RANGES_FILE
from tests.api.conftest import PREDICT

CODE = "OUTSIDE_TRAINING_RANGE"


@pytest.fixture(scope="module")
def ranges(client) -> dict:
    return client.get("/api/v1/model").json()["training_ranges"]


def result(client, body) -> dict:
    response = client.post(PREDICT, json=body)
    assert response.status_code == 200, response.text  # a warning is never an error
    return response.json()


def test_ranges_cover_exactly_the_continuous_inputs(ranges, api_features):
    assert sorted(ranges) == sorted(f["api_field"] for f in api_features if f["type"] == "int")
    for limits in ranges.values():
        assert limits["min"] < limits["max"]


def test_served_ranges_are_the_recorded_ones(ranges):
    assert ranges == json.loads(RANGES_FILE.read_text(encoding="utf-8"))["ranges"]


def test_figure_8_is_inside_every_range(client, valid_body):
    body = result(client, valid_body)
    assert body["warnings"] == [] and body["outside_training_range"] == []


def test_each_limit_is_inside_and_one_step_beyond_is_outside(client, valid_body, ranges, api_features):
    hard = {f["api_field"]: f for f in api_features if f["type"] == "int"}
    checked_outside = 0
    for name, limits in ranges.items():
        for edge, step in ((limits["min"], -1), (limits["max"], +1)):
            # the edge itself occurred in training: no range warning (clamped to what the form accepts)
            inside = min(max(edge, hard[name]["min"]), hard[name]["max"])
            assert name not in result(client, {**valid_body, name: inside})["outside_training_range"], name
            beyond = edge + step
            if hard[name]["min"] <= beyond <= hard[name]["max"]:
                body = result(client, {**valid_body, name: beyond})
                assert body["outside_training_range"] == [name]
                assert CODE in body["warnings"]
                checked_outside += 1
    assert checked_outside >= 8  # below-minimum cases for heart rate and SpO2 cannot be entered at all


def test_several_fields_are_reported_once_in_spec_order(client, valid_body, ranges, api_features):
    order = [f["api_field"] for f in api_features if f["type"] == "int"]
    body = result(
        client,
        {
            **valid_body,
            "gestational_age_weeks": ranges["gestational_age_weeks"]["max"] + 2,
            "apgar_5min": ranges["apgar_5min"]["max"] + 1,
        },
    )
    assert body["warnings"].count(CODE) == 1
    assert body["outside_training_range"] == [
        n for n in order if n in ("apgar_5min", "gestational_age_weeks")
    ]


def test_weight_warnings_are_independent(client, valid_body, ranges):
    """Above 1,500 g but within what training contained: only the cohort warning.
    Above the largest training weight: both."""
    top = ranges["birth_weight_g"]["max"]
    assert 1500 < top
    assert result(client, {**valid_body, "birth_weight_g": top})["warnings"] == ["WEIGHT_ABOVE_COHORT"]
    assert result(client, {**valid_body, "birth_weight_g": top + 1})["warnings"] == [
        "WEIGHT_ABOVE_COHORT",
        CODE,
    ]


def test_the_estimate_itself_is_not_changed_by_the_warning(client, valid_body, ranges, predictor):
    body_in = {**valid_body, "gestational_age_weeks": ranges["gestational_age_weeks"]["max"] + 1}
    assert result(client, body_in)["log_risk"] == predictor.log_risk(body_in)
