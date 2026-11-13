import json

import numpy as np
import pytest

from app.inference import default_model_dir, survival
from app.inference.hazard import CURVE_DAYS


@pytest.fixture(scope="module")
def table() -> dict[int, float]:
    raw = json.loads((default_model_dir() / "baseline_hazard.json").read_text(encoding="utf-8"))
    return dict(zip(raw["times"], raw["cumulative_hazard"], strict=True))


def test_formula_without_network(hazard):
    """Spec 5.4: log-risk 1.210 -> 65.22 % / 39.52 % / 5.63 %."""
    s = 100 * survival(hazard.h0([7, 28, 100]), 1.210)
    assert [round(float(v), 2) for v in s] == [65.22, 39.52, 5.63]


def test_zero_before_first_event(hazard, table):
    first = min(table)
    assert hazard.h0(0) == 0.0
    assert hazard.h0(first - 0.5) == 0.0
    assert hazard.h0(first) == table[first]


def test_event_days_return_their_own_value(hazard, table):
    for day, value in table.items():
        assert hazard.h0(day) == value


def test_gap_days_take_the_previous_event_time(hazard, table):
    """Step function, not nearest row: a day without events keeps the last value before it."""
    days = sorted(table)
    gaps = [d for d in range(days[0], 101) if d not in table]
    assert gaps, "the table is expected to have gaps"
    for day in gaps:
        previous = max(d for d in days if d < day)
        assert hazard.h0(day) == table[previous], day


def test_gap_day_differs_from_nearest_row_lookup(hazard, table):
    """At least one gap day sits closer to the next event time than to the previous one;
    the legacy nearest-row lookup would return the later (wrong) value there."""
    days = sorted(table)
    found = False
    for day in (d for d in range(days[0], 101) if d not in table):
        previous = max(d for d in days if d < day)
        following = min((d for d in days if d > day), default=None)
        if following is not None and following - day < day - previous and table[following] != table[previous]:
            assert hazard.h0(day) == table[previous]
            found = True
    assert found


def test_non_decreasing_and_constant_after_last_event(hazard, table):
    curve = hazard.h0(CURVE_DAYS)
    assert np.all(np.diff(curve) >= 0)
    assert hazard.h0(10_000) == table[max(table)]


def test_survival_at_day_zero_is_one(hazard):
    assert survival(hazard.h0(0), 3.0) == 1.0
