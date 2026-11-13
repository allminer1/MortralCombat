"""422 cases for every field (Phase 2 acceptance). Field names, types and ranges are read
from GET /api/v1/model, not typed here."""

import pytest

from tests.api.conftest import PREDICT


def errors(client, body) -> list[dict]:
    response = client.post(PREDICT, json=body)
    assert response.status_code == 422
    payload = response.json()
    assert set(payload) == {"errors"}
    return payload["errors"]


def only(items: list[dict]) -> dict:
    assert len(items) == 1, items
    return {k: v for k, v in items[0].items() if v is not None}


def test_spec_has_eleven_fields(api_features):
    assert len(api_features) == 11


def test_missing_each_field(client, valid_body, api_features):
    for f in api_features:
        body = {k: v for k, v in valid_body.items() if k != f["api_field"]}
        assert only(errors(client, body)) == {"field": f["api_field"], "code": "missing"}


def test_null_each_field(client, valid_body, api_features):
    for f in api_features:
        code = only(errors(client, {**valid_body, f["api_field"]: None}))["code"]
        assert code == ("not_boolean" if f["type"] == "bool" else "not_integer")


def test_out_of_range_each_integer_field(client, valid_body, api_features):
    ints = [f for f in api_features if f["type"] == "int"]
    assert len(ints) == 5
    for f in ints:
        expected = {"field": f["api_field"], "code": "out_of_range", "min": f["min"], "max": f["max"]}
        assert only(errors(client, {**valid_body, f["api_field"]: f["min"] - 1})) == expected
        assert only(errors(client, {**valid_body, f["api_field"]: f["max"] + 1})) == expected


def test_range_limits_are_accepted(client, valid_body, api_features):
    for f in (f for f in api_features if f["type"] == "int"):
        for value in (f["min"], f["max"]):
            assert client.post(PREDICT, json={**valid_body, f["api_field"]: value}).status_code == 200


@pytest.mark.parametrize("bad", ["12", 12.0, 12.5, True, [12], {"v": 12}])
def test_wrong_type_each_integer_field(client, valid_body, api_features, bad):
    for f in (f for f in api_features if f["type"] in ("int", "enum")):
        got = only(errors(client, {**valid_body, f["api_field"]: bad}))
        assert got == {"field": f["api_field"], "code": "not_integer"}


@pytest.mark.parametrize("bad", [0, 1, "true", "yes", 1.0, [True]])
def test_wrong_type_each_boolean_field(client, valid_body, api_features, bad):
    bools = [f for f in api_features if f["type"] == "bool"]
    assert len(bools) == 5
    for f in bools:
        got = only(errors(client, {**valid_body, f["api_field"]: bad}))
        assert got == {"field": f["api_field"], "code": "not_boolean"}


def test_enum_field_allows_only_listed_values(client, valid_body, api_features):
    (f,) = [f for f in api_features if f["type"] == "enum"]
    for value in f["values"]:
        assert client.post(PREDICT, json={**valid_body, f["api_field"]: value}).status_code == 200
    for value in (min(f["values"]) - 1, max(f["values"]) + 1, 0):
        got = only(errors(client, {**valid_body, f["api_field"]: value}))
        assert got == {"field": f["api_field"], "code": "not_allowed", "allowed": f["values"]}


def test_unknown_field_rejected(client, valid_body):
    assert only(errors(client, {**valid_body, "patient_name": "x"})) == {
        "field": "patient_name",
        "code": "unknown_field",
    }


def test_several_errors_reported_together(client, valid_body, api_features):
    a, b = [f["api_field"] for f in api_features if f["type"] == "int"][:2]
    body = {k: v for k, v in valid_body.items() if k != a} | {b: "x"}
    got = {(e["field"], e["code"]) for e in errors(client, body)}
    assert got == {(a, "missing"), (b, "not_integer")}


def test_body_must_be_a_json_object(client):
    assert only(errors(client, [1, 2, 3]))["code"] == "invalid_body"
    response = client.post(PREDICT, content=b"{not json", headers={"content-type": "application/json"})
    assert response.status_code == 422
    assert response.json() == {"errors": [{"field": None, "code": "invalid_json"}]}


def test_error_response_never_echoes_input(client, valid_body, api_features):
    name = next(f["api_field"] for f in api_features if f["type"] == "int")
    response = client.post(PREDICT, json={**valid_body, name: "MARKER-ZX81"})
    assert "MARKER-ZX81" not in response.text
    assert "Input should" not in response.text  # no English sentences from the validator
