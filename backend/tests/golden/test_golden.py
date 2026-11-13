"""Golden tests: the definition of correct (CLAUDE.md rule 4).

ONNX backend vs the frozen PyTorch model on every golden case. Tolerances are fixed by
docs/REBUILD_SPEC.md 5.4 and are not to be loosened.
"""

import numpy as np

TOL_LOG_RISK = 1e-4
TOL_SURVIVAL = 1e-5


def test_golden_set_is_complete(golden):
    cases = golden["cases"]
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)) == golden["meta"]["n_cases"]
    assert sum(i.startswith("random_") for i in ids) == 500
    assert {"all_min", "all_max", "anchor_figure_8", "anchor_rds_only", "anchor_nec_only"} <= set(ids)
    assert all(len(c["survival"]) == 101 for c in cases)


def test_tolerances_match_the_golden_file(golden):
    assert golden["meta"]["tolerance"] == {"log_risk": TOL_LOG_RISK, "survival": TOL_SURVIVAL}


def test_model_version_matches(golden, predictor):
    assert golden["meta"]["model_version"] == predictor.model_version


def test_onnx_matches_pytorch_on_every_case(golden, predictor):
    worst_g = worst_s = 0.0
    for case in golden["cases"]:
        got = predictor.predict(case["inputs"])
        worst_g = max(worst_g, abs(got.log_risk - case["log_risk"]))
        worst_s = max(worst_s, float(np.abs(np.array(got.curve) - np.array(case["survival"])).max()))
        assert got.curve[0] == 1.0, case["id"]
    print(f"\nmax |log-risk diff| = {worst_g:.2e}, max |S(t) diff| = {worst_s:.2e}")
    assert worst_g <= TOL_LOG_RISK
    assert worst_s <= TOL_SURVIVAL


def test_recorded_anchors(golden, predictor):
    """Published / recorded numbers: log-risk to 3 decimals, survival % to 2 decimals."""
    by_id = {c["id"]: c for c in golden["cases"]}
    for name, expected in golden["meta"]["anchors_percent_day_7_28_100"].items():
        got = predictor.predict(by_id[name]["inputs"])
        assert round(got.log_risk, 3) == expected["log_risk"], name
        percent = [round(100 * got.survival_points[d], 2) for d in (7, 28, 100)]
        assert percent == expected["survival_percent"], name
