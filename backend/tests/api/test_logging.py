"""Request bodies must not reach the logs (CLAUDE.md rule 5, Phase 2 acceptance).

Everything written through `logging` (all loggers) and everything written to stdout /
stderr during a request is captured and searched for the submitted values.
"""

import logging
import re

import pytest

from tests.api.conftest import PREDICT

MARKER = "MARKER-ZX81-9f3a"
# Distinctive values within range. Two-digit inputs are left out: they would collide with
# timestamps and latencies by chance. The field-name and marker checks cover the rest.
VALUES = {"birth_weight_g": 1483, "heart_rate_bpm": 173}


# The test client is an HTTP client library running inside the test process; it logs the
# URL it calls. That is the caller's log, not the server's, and does not exist in production.
CLIENT_SIDE_LOGGERS = ("httpx", "httpx2", "httpcore")


@pytest.fixture()
def captured(caplog, capsys):
    """Returns a function giving all server-side log and console output produced so far."""
    caplog.set_level(logging.DEBUG)  # root logger: every logger propagates here

    def text() -> str:
        records = [r for r in caplog.records if not r.name.startswith(CLIENT_SIDE_LOGGERS)]
        return "\n".join(f"{r.name} {r.getMessage()}" for r in records) + "".join(capsys.readouterr())

    return text


def test_valid_request_logs_metadata_only(client, valid_body, api_features, captured):
    body = {**valid_body, **VALUES}
    assert client.post(f"{PREDICT}?note={MARKER}", json=body).status_code == 200
    text = captured()

    assert "method=POST path=/api/v1/predict status=200" in text
    assert "model_version=deepsurv-vlbw-1.0.0" in text
    assert "latency_ms=" in text
    assert "warnings=-" in text
    for f in api_features:
        assert not re.search(rf"\b{f['api_field']}\b", text), f["api_field"]  # "dic" is inside "predict"
    for value in VALUES.values():
        assert str(value) not in text.replace("latency_ms=", "")
    assert MARKER not in text  # the query string is not logged either
    assert "testclient" not in text  # no client address


def test_warning_codes_are_logged(client, valid_body, captured):
    assert client.post(PREDICT, json={**valid_body, "birth_weight_g": 1777}).status_code == 200
    text = captured()
    assert "warnings=WEIGHT_ABOVE_COHORT" in text
    assert "1777" not in text


def test_range_warning_logs_the_code_not_the_field_or_value(client, valid_body, captured):
    assert client.post(PREDICT, json={**valid_body, "gestational_age_weeks": 41}).status_code == 200
    text = captured()
    assert "warnings=OUTSIDE_TRAINING_RANGE" in text
    assert "gestational_age_weeks" not in text


def test_invalid_request_logs_codes_only(client, valid_body, captured):
    body = {**valid_body, "birth_weight_g": MARKER, f"field_{MARKER}": MARKER, "heart_rate_bpm": 9173}
    assert client.post(PREDICT, json=body).status_code == 422
    text = captured()

    assert "status=422" in text
    assert "errors=not_integer,out_of_range,unknown_field" in text
    assert MARKER not in text
    assert "9173" not in text
    assert "birth_weight_g" not in text


def test_malformed_json_is_not_logged(client, captured):
    raw = ('{"birth_weight_g": 1483, "note": "' + MARKER + '"').encode()
    response = client.post(PREDICT, content=raw, headers={"content-type": "application/json"})
    assert response.status_code == 422
    assert MARKER not in response.text
    text = captured()
    assert "errors=invalid_json" in text
    assert MARKER not in text and "1483" not in text


def test_access_logger_receives_exactly_one_line_per_request(client, valid_body, captured, caplog):
    client.post(PREDICT, json=valid_body)
    lines = [r for r in caplog.records if r.name == "neomortalsurv.access"]
    assert len(lines) == 1
    assert set(lines[0].getMessage().split()) >= {"method=POST", "path=/api/v1/predict", "status=200"}
