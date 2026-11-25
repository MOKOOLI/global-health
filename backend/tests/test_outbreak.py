from datetime import date, timedelta

import numpy as np
import pytest

from app import outbreak as O

RNG = np.random.default_rng(42)


def weeks(n, start=date(2018, 1, 1)):
    return [start + timedelta(days=7 * i) for i in range(n)]


def seasonal_counts(n=6 * 52, base=60, amp=0.5, rng=RNG):
    t = np.arange(n)
    mu = base * (1 + amp * np.sin(2 * np.pi * t / 52))
    return rng.poisson(mu).astype(float)


def test_weekly_grid_fills_gaps_and_clips_negatives():
    d = [date(2024, 1, 1), date(2024, 1, 15), date(2024, 1, 22)]
    grid, v = O.weekly_grid(d, [5, 3, -2])
    assert len(grid) == 4 and np.isnan(v[1]) and v[3] == 0 and v[0] == 5


def test_poisson_growth_recovers_known_rate():
    r = 0.35
    y = RNG.poisson(40 * np.exp(r * np.arange(6))).astype(float)
    g = O.poisson_growth(y)
    assert g is not None and abs(g.r_week - r) < 0.2 and g.significant
    assert 8 < g.time_days < 30  # doubling time ~ ln2/r*7 = 13.9 days


def test_poisson_growth_needs_enough_events():
    assert O.poisson_growth(np.array([0, 1, 0, 2, 1.0])) is None


def test_poisson_growth_flat_is_not_significant():
    g = O.poisson_growth(RNG.poisson(200, 6).astype(float))
    assert g is not None and not g.significant


def test_reproduction_number_formula():
    assert O.reproduction_number(0.0, 5.2, 1.7) == pytest.approx(1.0)
    assert O.reproduction_number(0.4, 5.2, 1.7) == pytest.approx(1.34, abs=0.03)
    assert O.reproduction_number(-0.4, 5.2, 1.7) < 1.0
    assert O.reproduction_number(-50, 5.2, 1.7) == 0.0  # base <= 0 guard


def test_baseline_is_causal():
    y = seasonal_counts()
    b1 = O.compute_baseline(y)
    y2 = y.copy()
    y2[-30:] *= 10  # change the future
    b2 = O.compute_baseline(y2)
    i = len(y) - 40
    assert b1.expected[i] == b2.expected[i] and b1.upper[i] == b2.upper[i]


def test_endemic_seasonal_series_is_endemic_not_epidemic():
    y = seasonal_counts(base=80)
    d = weeks(len(y))
    phases = []
    base = O.compute_baseline(y)
    for i in range(3 * 52, len(y)):
        phases.append(O.assess_at(d, y, base, i).phase)
    assert phases.count("epidemic") / len(phases) < 0.03   # few false alarms
    assert phases[-1] in ("endemic", "watch")


def test_injected_outbreak_is_flagged_epidemic_and_rising():
    y = seasonal_counts(base=60)
    y[-5:] = (y[-5:] * np.exp(0.45 * np.arange(1, 6))).round()
    d = weeks(len(y))
    a, _ = O.assess_latest(d, y, gi=O.GENERATION_INTERVALS["influenza"])
    assert a.phase == "epidemic" and a.trend == "rising"
    assert a.growth["r_week"] > 0.2 and a.r_estimate["mean"] > 1.0
    assert a.score > 3


def test_new_disease_without_history_uses_recent_baseline():
    y = np.concatenate([RNG.poisson(5, 20), np.round(5 * np.exp(0.5 * np.arange(1, 8)))]).astype(float)
    a, base = O.assess_latest(weeks(len(y)), y)
    assert a.baseline_method == "recent" and a.phase in ("epidemic", "watch")


def test_inactive_and_no_data():
    d = weeks(30)
    assert O.assess_latest(d, np.zeros(30))[0].phase == "inactive"
    y = np.full(30, np.nan)
    y[0] = 3
    assert O.assess_latest(d, y)[0].phase == "no_data"


def test_declining_after_outbreak():
    y = np.concatenate([RNG.poisson(10, 30), [60, 90, 120, 110, 80, 50, 30, 18, 12, 11, 10, 9]]).astype(float)
    a, _ = O.assess_latest(weeks(len(y)), y)
    assert a.phase in ("declining", "endemic", "sporadic", "watch")
    assert a.exceedances_last3 == 0


def row(iso, region, phase, trend="rising"):
    return dict(iso3=iso, region=region, phase=phase, trend=trend)


def test_global_pattern_levels():
    regs = ["A", "B", "C", "D"]
    many = [row(f"X{i}", regs[i % 4], "epidemic") for i in range(24)]
    assert O.global_pattern(many, 100)["level"] == "pandemic_pattern"
    flat = [row(f"X{i}", regs[i % 4], "epidemic", trend="falling") for i in range(24)]
    assert O.global_pattern([row(f"Y{i}", regs[i % 4], "epidemic") for i in range(12)], 100)["level"] == "multi_region_outbreak"
    assert O.global_pattern(flat, 100)["level"] == "multi_region_outbreak"
    assert O.global_pattern([row("A1", "A", "epidemic"), row("A2", "A", "epidemic")], 50)["level"] == "regional_outbreak"
    assert O.global_pattern([row("A1", "A", "epidemic")], 50)["level"] == "single_country"
    assert O.global_pattern([row("A1", "A", "watch")], 50)["level"] == "watch"
    assert O.global_pattern([], 0)["level"] == "none"
    intro = [dict(iso3=f"N{i}", region=regs[i % 4], phase="no_data", trend="unknown", intro=True) for i in range(6)]
    assert O.global_pattern(intro, 50)["level"] == "novel_spread"
    assert O.global_pattern(intro[:4], 50)["level"] != "novel_spread"


def test_forecast_shape_and_interval_order():
    t = np.arange(120)
    y = RNG.poisson(30 + 25 * np.sin(t / 8) ** 2 + 0.3 * t).astype(float)
    f = O.forecast(weeks(len(y)), y)
    assert f and len(f["points"]) == 4
    for p in f["points"]:
        assert 0 <= p["low"] <= p["value"] <= p["high"]
    m = f["metrics"]
    assert set(m["mae_log"]) == set(O.MODELS) and m["n_backtest_origins"] >= 12


def test_forecast_reports_when_not_better_than_naive():
    y = RNG.poisson(100, 140).astype(float)  # pure noise around a constant: nothing beats naive
    f = O.forecast(weeks(len(y)), y)
    assert f is not None and f["reliable"] is False


def test_forecast_refuses_short_or_dead_series():
    assert O.forecast(weeks(20), np.ones(20)) is None
    assert O.forecast(weeks(60), np.zeros(60)) is None


def test_regularize_detects_batch_reporting_but_not_sparse_counts():
    batched = np.array([0, 0, 0, 60, 0, 0, 0, 0, 50, 0, 0, 0, 0, 55, 0, 0, 0, 0, 52, 0, 0, 0, 0, 58, 0, 0, 0, 0, 61.0])
    eff, sm = O.regularize(batched)
    assert sm and np.nanmax(eff) < 20
    sparse = RNG.poisson(1.2, 60).astype(float)  # genuinely rare: many zeros but tiny counts
    assert O.regularize(sparse)[1] is False
    steady = RNG.poisson(50, 60).astype(float)
    assert O.regularize(steady)[1] is False
