import numpy as np

from app import analytics as A
from app.llm import validate


def test_pct_change_and_cagr():
    assert A.pct_change(100, 150) == 50
    assert A.pct_change(0, 10) is None
    assert round(A.cagr(100, 121, 2), 6) == 10.0
    assert A.cagr(100, 50, 0) is None


def test_trend_directions():
    yrs = list(range(2000, 2016))
    down = [100 * 0.95**i for i in range(16)]
    up = [10 + 3 * i for i in range(16)]
    flat = [50 + (i % 2) * 0.1 for i in range(16)]
    assert A.linear_trend(yrs, down).direction == "decreasing"
    assert A.linear_trend(yrs, up).direction == "increasing"
    assert A.linear_trend(yrs, flat).direction == "stable"
    assert A.linear_trend(yrs[:3], down[:3]) is None


def test_change_point_found_on_step_not_on_line():
    yrs = list(range(2000, 2020))
    step = [10.0] * 10 + [25.0] * 10
    cp = A.change_point(yrs, step)
    assert cp and cp["year"] == 2010 and cp["shift_pct"] > 100
    line = [10 + i for i in range(20)]
    assert A.change_point(yrs, line) is None


def test_yoy_anomaly():
    yrs = list(range(2000, 2016))
    v = [100 + i for i in range(16)]
    v[9] = 400  # spike
    years = [a["year"] for a in A.yoy_anomalies(yrs, v)]
    assert 2009 in years


def test_forecast_is_nonnegative_and_ordered():
    yrs = list(range(2000, 2020))
    v = [50 * 0.9**i for i in range(20)]
    fc = A.forecast_holt(yrs, v, 5)
    assert len(fc["points"]) == 5
    for p in fc["points"]:
        assert 0 <= p["low"] <= p["value"] <= p["high"]


def test_percentile_rank():
    assert A.percentile_rank(5, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) == 45.0


def test_llm_number_validation():
    src = "In 2021, Iran had 12.5 per 100,000 (95% UI 10–15). Rank 40 of 180."
    assert validate("Iran had 12.5 per 100,000 in 2021, ranking 40 of 180.", src)
    assert not validate("Iran had 99 per 100,000 in 2021.", src)
    assert validate("ایران در سال ۲۰۲۱ مقدار ۱۲٫۵ داشت.", src)
