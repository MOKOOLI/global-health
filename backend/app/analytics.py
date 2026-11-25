"""Pure numerical analysis. NO LLM is involved here - every number shown to a clinician
comes from these functions. The LLM (if enabled) only rephrases the resulting facts.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def pct_change(first: float, last: float) -> float | None:
    if first is None or last is None or first == 0:
        return None
    return (last - first) / abs(first) * 100.0


def cagr(first: float, last: float, years: int) -> float | None:
    if years <= 0 or first is None or last is None or first <= 0 or last <= 0:
        return None
    return ((last / first) ** (1.0 / years) - 1.0) * 100.0


@dataclass
class Trend:
    slope: float            # absolute units / year
    slope_pct: float | None  # % of mean per year
    r2: float
    p_approx: float         # two-sided approx p-value for slope != 0
    direction: str          # increasing | decreasing | stable


def linear_trend(years: list[int], values: list[float], min_points: int = 5) -> Trend | None:
    if len(years) < min_points:
        return None
    x, y = np.asarray(years, float), np.asarray(values, float)
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    if sxx == 0:
        return None
    slope = ((x - xm) * (y - ym)).sum() / sxx
    intercept = ym - slope * xm
    resid = y - (intercept + slope * x)
    sst = ((y - ym) ** 2).sum()
    r2 = 1 - (resid**2).sum() / sst if sst > 0 else 0.0
    dof = len(x) - 2
    se = math.sqrt((resid**2).sum() / dof / sxx) if dof > 0 and sxx > 0 else float("inf")
    if se == float("inf"):
        t = 0.0
    elif se == 0:  # perfect fit: any non-zero slope is certain
        t = float("inf") if slope != 0 else 0.0
    else:
        t = slope / se
    # normal approximation to the t distribution (adequate for n >= 8; conservative otherwise)
    p = math.erfc(abs(t) / math.sqrt(2))
    slope_pct = slope / ym * 100 if ym else None
    if p > 0.05 or (slope_pct is not None and abs(slope_pct) < 0.5):
        direction = "stable"
    else:
        direction = "increasing" if slope > 0 else "decreasing"
    return Trend(float(slope), None if slope_pct is None else float(slope_pct), float(r2), float(p), direction)


def robust_z(values: np.ndarray) -> np.ndarray:
    med = np.median(values)
    mad = np.median(np.abs(values - med))
    if mad == 0:
        return np.zeros_like(values)
    return 0.6745 * (values - med) / mad


def yoy_anomalies(years: list[int], values: list[float], z_threshold: float = 4.0) -> list[dict]:
    """Years whose year-over-year relative change is an outlier vs the series' own history."""
    if len(values) < 8:
        return []
    v = np.asarray(values, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = np.diff(v) / np.where(v[:-1] == 0, np.nan, np.abs(v[:-1]))
    ok = ~np.isnan(rel)
    if ok.sum() < 6:
        return []
    z = np.full_like(rel, 0.0)
    z[ok] = robust_z(rel[ok])
    out = []
    for i in np.where(np.abs(z) >= z_threshold)[0]:
        if abs(rel[i]) >= 0.25:  # also require a clinically meaningful change (>=25 %)
            out.append(
                dict(year=int(years[i + 1]), change_pct=float(rel[i] * 100), z=float(z[i]))
            )
    return out


def change_point(years: list[int], values: list[float], min_seg: int = 4) -> dict | None:
    """Single best level-shift (piecewise-constant, least squares). Returns None if weak."""
    n = len(values)
    if n < 2 * min_seg + 2:
        return None
    y = np.asarray(values, float)
    total_sse = ((y - y.mean()) ** 2).sum()
    if total_sse == 0:
        return None
    best = None
    for k in range(min_seg, n - min_seg + 1):
        a, b = y[:k], y[k:]
        sse = ((a - a.mean()) ** 2).sum() + ((b - b.mean()) ** 2).sum()
        if best is None or sse < best[0]:
            best = (sse, k)
    sse, k = best  # type: ignore[misc]
    explained = 1 - sse / total_sse
    before, after = float(y[:k].mean()), float(y[k:].mean())
    shift = pct_change(before, after)
    # require the step model to explain much more than a straight line would
    t = linear_trend(years, values, 3)
    if explained < 0.6 or shift is None or abs(shift) < 30 or (t and t.r2 > explained - 0.1):
        return None
    return dict(year=int(years[k]), mean_before=before, mean_after=after, shift_pct=float(shift))


def forecast_holt(years: list[int], values: list[float], horizon: int = 5) -> dict | None:
    """Damped-trend exponential smoothing (Holt). Deliberately simple and labelled indicative."""
    if len(values) < 10:
        return None
    y = np.asarray(values, float)
    best = None
    for alpha in (0.3, 0.5, 0.8):
        for beta in (0.1, 0.3):
            phi = 0.9
            level, trend = y[0], y[1] - y[0]
            sse = 0.0
            for t in range(1, len(y)):
                pred = level + phi * trend
                sse += (y[t] - pred) ** 2
                new_level = alpha * y[t] + (1 - alpha) * (level + phi * trend)
                trend = beta * (new_level - level) + (1 - beta) * phi * trend
                level = new_level
            if best is None or sse < best[0]:
                best = (sse, level, trend, phi)
    sse, level, trend, phi = best  # type: ignore[misc]
    sigma = math.sqrt(sse / max(len(y) - 1, 1))
    out = []
    damp = 0.0
    for h in range(1, horizon + 1):
        damp += phi**h
        mean = max(level + damp * trend, 0.0)
        width = 1.96 * sigma * math.sqrt(h)
        out.append(
            dict(year=int(years[-1]) + h, value=float(mean),
                 low=float(max(mean - width, 0.0)), high=float(mean + width))
        )
    return dict(method="damped Holt", points=out)


def percentile_rank(value: float, population: list[float]) -> float:
    arr = np.asarray(population, float)
    return float((arr < value).sum() + 0.5 * (arr == value).sum()) / len(arr) * 100.0


def quantiles(values: list[float], qs=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0)) -> list[float]:
    if not values:
        return []
    return [float(x) for x in np.quantile(np.asarray(values, float), qs)]
