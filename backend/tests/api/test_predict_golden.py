"""Golden tests through the HTTP layer (Phase 2 acceptance). Same fixed tolerances as
tests/golden/test_golden.py; never to be loosened."""

import numpy as np

from tests.api.conftest import PREDICT

TOL_LOG_RISK = 1e-4
TOL_SURVIVAL = 1e-5


def test_every_golden_case_through_http(client, golden, to_body):
    assert golden["meta"]["tolerance"] == {"log_risk": TOL_LOG_RISK, "survival": TOL_SURVIVAL}
    worst_g = worst_s = 0.0
    for case in golden["cases"]:
        response = client.post(PREDICT, json=to_body(case["inputs"]))
        assert response.status_code == 200, case["id"]
        body = response.json()
        assert [p["day"] for p in body["curve"]] == list(range(101)), case["id"]
        curve = np.array([p["survival"] for p in body["curve"]])
        expected = np.array(case["survival"])
        worst_g = max(worst_g, abs(body["log_risk"] - case["log_risk"]))
        worst_s = max(worst_s, float(np.abs(curve - expected).max()))
        for day in (7, 28, 100):
            assert body["survival"][f"day_{day}"] == body["curve"][day]["survival"], case["id"]
    print(f"\nHTTP: max |log-risk diff| = {worst_g:.2e}, max |S(t) diff| = {worst_s:.2e}")
    assert worst_g <= TOL_LOG_RISK
    assert worst_s <= TOL_SURVIVAL


def test_figure_8_response_shape(client, valid_body):
    body = client.post(PREDICT, json=valid_body).json()
    assert set(body) == {"model_version", "log_risk", "survival", "curve", "warnings", "intended_use"}
    assert body["model_version"] == "deepsurv-vlbw-1.0.0"
    assert round(body["log_risk"], 3) == 1.210
    assert [round(100 * body["survival"][k], 2) for k in ("day_7", "day_28", "day_100")] == [
        65.22,
        39.52,
        5.63,
    ]
    assert body["curve"][0] == {"day": 0, "survival": 1.0}
    assert body["warnings"] == []
    assert body["intended_use"] == "research"
