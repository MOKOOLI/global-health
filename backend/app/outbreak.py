"""Early-warning analytics for weekly surveillance series.

What this module can and cannot do
----------------------------------
* It detects *statistical* signals in reported data: growth, exceedance over a baseline,
  and the multi-country spread pattern. It does NOT predict novel pandemics months ahead and
  it does NOT declare epidemics: that is a public-health decision (WHO, national authorities).
* Forecasts are 1-4 weeks ahead only and always come with a back-test of their own skill
  versus a naive baseline. If the model is not better than naive, the API says so.
* Everything is CAUSAL: the assessment at week t uses only data up to t, so the same code
  can be replayed over history to measure how early (or late) it would have warned.
* Pure numpy, no LLM. Every number shown to a clinician comes from here.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date, timedelta

import numpy as np

# --------------------------------------------------------------------------- series prep
def weekly_grid(dates: list[date], values: list[float]) -> tuple[list[date], np.ndarray]:
    """Continuous 7-day grid from first to last date; gaps become NaN; negatives clip to 0
    (cumulative-count corrections in some feeds produce negative increments)."""
    if not dates:
        return [], np.array([])
    by = {d: v for d, v in zip(dates, values)}
    d0, d1 = min(by), max(by)
    grid, out = [], []
    d = d0
    while d <= d1:
        grid.append(d)
        v = by.get(d)
        out.append(np.nan if v is None else max(float(v), 0.0))
        d += timedelta(days=7)
    return grid, np.asarray(out, float)


def regularize(y: np.ndarray, window: int = 4) -> tuple[np.ndarray, bool]:
    """Detect batch reporting and, if present, return a trailing `window`-week mean instead.

    Some feeds report monthly or irregularly (e.g. [0,0,0,60,0,0,0,0,50,49]); a weekly-threshold method
    reads two batches as a surge. We call a series batched when, after its first event, >=35% of weeks are
    zero although the non-zero weeks are large (mean >= 8): sparse-but-genuine low counts are left alone.
    """
    y = np.asarray(y, float)
    pos = np.where(np.nan_to_num(y, nan=0.0) > 0)[0]
    if len(pos) < 6 or len(y) < 26:
        return y, False
    seg = y[pos[0]:]
    seg = seg[~np.isnan(seg)]
    nz = seg[seg > 0]
    if len(seg) < 20 or len(nz) == 0 or (seg == 0).mean() < 0.35 or nz.mean() < 8:
        return y, False
    out = np.full(len(y), np.nan)
    for i in range(len(y)):
        w = y[max(0, i - window + 1): i + 1]
        w = w[~np.isnan(w)]
        if len(w) >= 2:
            out[i] = w.mean()
    return out, True


# --------------------------------------------------------------------------- growth rate
@dataclass
class Growth:
    r_week: float            # exponential growth rate per week (ln units)
    lo: float                # 95% CI
    hi: float
    significant: bool        # CI excludes 0
    time_days: float | None  # doubling (r>0) or halving (r<0) time in days
    events: float            # total events in the fitting window


def poisson_growth(y: np.ndarray, min_events: float = 20.0) -> Growth | None:
    """Log-linear Poisson (quasi-Poisson SE) growth rate over a short window."""
    y = np.asarray(y, float)
    m = ~np.isnan(y)
    if m.sum() < 4 or y[m].sum() < min_events:
        return None
    t = np.arange(len(y), dtype=float)[m]
    t -= t.mean()
    yy = y[m]
    X = np.column_stack([np.ones_like(t), t])
    beta = np.array([math.log(max(yy.mean(), 0.5)), 0.0])
    for _ in range(40):
        eta = np.clip(X @ beta, -20, 20)
        mu = np.exp(eta)
        z = eta + (yy - mu) / mu
        A = (X.T * mu) @ X
        new = np.linalg.solve(A, (X.T * mu) @ z)
        done = np.max(np.abs(new - beta)) < 1e-9
        beta = new
        if done:
            break
    mu = np.exp(np.clip(X @ beta, -20, 20))
    phi = max(1.0, float(((yy - mu) ** 2 / mu).sum() / max(len(yy) - 2, 1)))
    cov = phi * np.linalg.inv((X.T * mu) @ X)
    r, se = float(beta[1]), math.sqrt(max(cov[1, 1], 0.0))
    lo, hi = r - 1.96 * se, r + 1.96 * se
    td = math.log(2) / abs(r) * 7 if abs(r) > 1e-9 else None
    return Growth(r, lo, hi, bool(lo > 0 or hi < 0), td, float(yy.sum()))


def loglinear_growth(y: np.ndarray, floor: float = 1e-6) -> Growth | None:
    """OLS on log(y) for continuous (percentage) series such as ILI %."""
    y = np.asarray(y, float)
    m = ~np.isnan(y)
    if m.sum() < 4:
        return None
    t = np.arange(len(y), dtype=float)[m]
    ly = np.log(np.maximum(y[m], floor))
    tc = t - t.mean()
    sxx = (tc**2).sum()
    r = float((tc * (ly - ly.mean())).sum() / sxx)
    resid = ly - (ly.mean() + r * tc)
    se = math.sqrt((resid**2).sum() / max(len(t) - 2, 1) / sxx)
    lo, hi = r - 2.0 * se, r + 2.0 * se  # slightly wider than normal: tiny n
    td = math.log(2) / abs(r) * 7 if abs(r) > 1e-9 else None
    return Growth(r, lo, hi, bool(lo > 0 or hi < 0), td, float(np.nansum(y)))


# Generation-interval (mean, sd) in days. INDICATIVE literature values used only to convert a
# growth rate to an approximate R (Wallinga-Lipsitch, gamma distribution). Review and cite
# before relying on them; diseases not listed get no R at all (growth rate and doubling time only).
GENERATION_INTERVALS: dict[str, tuple[float, float]] = {
    "covid-19": (5.2, 1.7),
    "influenza": (2.6, 1.5),
    "measles": (12.0, 3.0),
    "mpox": (9.0, 5.0),
    "ebola": (15.3, 9.3),
}


def reproduction_number(r_week: float, gi_mean: float, gi_sd: float) -> float:
    """R = (1 + r*theta)^k for a gamma generation interval (k = (m/sd)^2, theta = sd^2/m)."""
    r = r_week / 7.0
    k = (gi_mean / gi_sd) ** 2
    theta = gi_sd**2 / gi_mean
    base = 1.0 + r * theta
    return 0.0 if base <= 0 else float(base**k)


# --------------------------------------------------------------------------- baselines
@dataclass
class Baseline:
    expected: np.ndarray
    upper: np.ndarray
    method: np.ndarray  # per index: 'seasonal' | 'recent' | ''


def compute_baseline(
    y: np.ndarray, years_back: int = 5, window: int = 2, min_hist: int = 6,
    z_seasonal: float = 2.5, z_recent: float = 3.0, min_cases: float = 0.0,
) -> Baseline:
    """Causal baseline + upper threshold for every week.

    seasonal: same weeks (+-window) of previous years, upper 20% dropped to limit the pull of
              past outbreaks, quasi-Poisson prediction limit with an expanding dispersion.
    recent:   EARS-C2-like (weeks t-9..t-3) when fewer than ~1 year of history exists.
    """
    n = len(y)
    exp_s = np.full(n, np.nan)
    m_hist = np.zeros(n)
    for i in range(n):
        vals: list[float] = []
        for k in range(1, years_back + 1):
            c = i - 52 * k
            if c - window < 0:
                break
            seg = y[c - window : c + window + 1]
            vals.extend(seg[~np.isnan(seg)].tolist())
        if len(vals) >= min_hist:
            v = np.sort(np.asarray(vals))
            keep = v[: max(int(math.ceil(len(v) * 0.8)), 1)]
            exp_s[i], m_hist[i] = keep.mean(), len(keep)

    # causal over-dispersion (expanding mean of capped squared Pearson residuals)
    pear = np.where(
        ~np.isnan(exp_s) & ~np.isnan(y),
        np.minimum((y - exp_s) ** 2 / np.maximum(exp_s, 1.0), 25.0),
        np.nan,
    )
    phi = np.ones(n)
    s, c = 0.0, 0
    for i in range(n):
        phi[i] = max(1.0, s / c) if c >= 8 else 1.5
        if not np.isnan(pear[i]):
            s += pear[i]
            c += 1

    expected = np.full(n, np.nan)
    upper = np.full(n, np.nan)
    method = np.array([""] * n, dtype=object)
    for i in range(n):
        if not np.isnan(exp_s[i]):
            mu = exp_s[i]
            sd = math.sqrt(max(phi[i] * mu, 1.0) * (1 + 1 / max(m_hist[i], 1)))
            expected[i], upper[i], method[i] = mu, mu + z_seasonal * sd, "seasonal"
        elif i >= 9:
            w = y[i - 9 : i - 2]
            w = w[~np.isnan(w)]
            if len(w) >= 5:
                mu = float(w.mean())
                sd = max(float(w.std(ddof=1)) if len(w) > 1 else 0.0, math.sqrt(max(mu, 0.25)), 0.5)
                expected[i], upper[i], method[i] = mu, mu + z_recent * sd, "recent"
    return Baseline(expected, upper, method)


# --------------------------------------------------------------------------- assessment
@dataclass
class Assessment:
    phase: str          # no_data | inactive | sporadic | endemic | watch | epidemic | declining
    trend: str          # rising | falling | flat | unknown
    last_week: date | None
    last_value: float | None
    expected: float | None
    upper: float | None
    ratio: float | None            # last_value / expected
    exceedances_last3: int
    presence_52w: float | None     # share of last 52 weeks with >0 events
    growth: dict | None
    r_estimate: dict | None
    baseline_method: str
    weeks_available: int
    score: float                   # ranking score (higher = more urgent), not a probability


def assess_at(
    dates: list[date], y: np.ndarray, base: Baseline, i: int, *, unit: str = "count",
    gi: tuple[float, float] | None = None, min_cases: float = 5.0, growth_window: int = 5,
) -> Assessment:
    """Assess the series as it was known at index i (inclusive)."""
    lo26 = max(0, i - 25)
    recent = y[lo26 : i + 1]
    weeks_av = int((~np.isnan(y[: i + 1])).sum())
    last_v = None if np.isnan(y[i]) else float(y[i])
    empty = Assessment("no_data", "unknown", dates[i], last_v, None, None, None, 0, None, None, None, "", weeks_av, 0.0)
    if int((~np.isnan(recent)).sum()) < 8:
        return empty
    if float(np.nansum(y[max(0, i - 7) : i + 1])) == 0:
        return Assessment("inactive", "flat", dates[i], last_v, None, None, None, 0, None, None, None, "", weeks_av, 0.0)

    ex, up = base.expected, base.upper
    flags = 0
    for j in range(max(0, i - 2), i + 1):
        v = y[j]
        if not np.isnan(v) and not np.isnan(up[j]) and v > up[j] and (unit != "count" or v >= min_cases):
            flags += 1
    earlier = 0
    for j in range(max(0, i - 11), max(0, i - 3)):
        v = y[j]
        if not np.isnan(v) and not np.isnan(up[j]) and v > up[j] and (unit != "count" or v >= min_cases):
            earlier += 1

    gw = y[max(0, i - growth_window + 1) : i + 1]
    g = poisson_growth(gw) if unit == "count" else loglinear_growth(gw)
    trend = "unknown"
    if g is not None:
        trend = "rising" if (g.significant and g.r_week > 0) else "falling" if (g.significant and g.r_week < 0) else "flat"

    last_exp = None if np.isnan(ex[i]) else float(ex[i])
    last_up = None if np.isnan(up[i]) else float(up[i])
    ratio = (last_v / last_exp) if (last_v is not None and last_exp and last_exp > 0) else None
    y52 = y[max(0, i - 51) : i + 1]
    y52 = y52[~np.isnan(y52)]
    presence = float((y52 > 0).mean()) if len(y52) else None

    big_growth = g is not None and g.significant and g.r_week >= math.log(1.25) and g.events >= 30
    # a single exceedance is only worth a "watch" if it is also rising or clearly above baseline,
    # otherwise ordinary noise would put ~1 in 10 normal country-weeks on the watch list.
    single_flag = flags == 1 and (trend == "rising" or (ratio is not None and ratio >= 1.5))
    if flags >= 2:
        phase = "epidemic"
    elif single_flag or big_growth:
        phase = "watch"
    elif earlier >= 3:
        phase = "declining"
    elif presence is not None and presence >= 0.8:
        phase = "endemic"
    else:
        phase = "sporadic"

    r_est = None
    if g is not None and gi is not None and unit == "count":
        r_est = dict(
            mean=reproduction_number(g.r_week, *gi),
            lo=reproduction_number(g.lo, *gi),
            hi=reproduction_number(g.hi, *gi),
            gi_mean=gi[0], gi_sd=gi[1],
        )
    score = 0.0
    if phase in ("epidemic", "watch"):
        score = (2.0 if phase == "epidemic" else 1.0) + min(math.log1p(ratio or 0.0), 4.0) + (max(g.r_week, 0.0) * 3 if g else 0.0)
    return Assessment(
        phase, trend, dates[i], last_v, last_exp, last_up, ratio, flags, presence,
        asdict(g) if g else None, r_est, str(base.method[i]), weeks_av, float(score),
    )


def assess_latest(dates, y, *, unit="count", gi=None, min_cases=5.0) -> tuple[Assessment, Baseline]:
    base = compute_baseline(y)
    return assess_at(dates, y, base, len(y) - 1, unit=unit, gi=gi, min_cases=min_cases), base


# --------------------------------------------------------------------------- global pattern
def global_pattern(rows: list[dict], n_reporting: int) -> dict:
    """Multi-country spread pattern for ONE disease.

    rows: [{iso3, region, phase, trend, intro}] (latest assessment per country).
    This describes a statistical pattern; declaring a pandemic or PHEIC is WHO's decision.
    """
    epi = [r for r in rows if r["phase"] == "epidemic"]
    watch = [r for r in rows if r["phase"] == "watch"]
    intro = [r for r in rows if r.get("intro")]
    intro_regions = {r["region"] for r in intro if r.get("region")}
    regions = {r["region"] for r in epi if r.get("region")}
    rising = [r for r in epi if r["trend"] == "rising"]
    share_rising = (len(rising) / len(epi)) if epi else 0.0
    if len(epi) >= 20 and len(regions) >= 4 and share_rising >= 0.5:
        level = "pandemic_pattern"
    elif len(intro) >= 5 and len(intro_regions) >= 3:
        level = "novel_spread"  # first-ever cases appearing in many regions within weeks
    elif len(epi) >= 3 and len(regions) >= 2:
        level = "multi_region_outbreak"
    elif len(epi) >= 2:
        level = "regional_outbreak"
    elif len(epi) == 1:
        level = "single_country"
    elif watch:
        level = "watch"
    else:
        level = "none"
    return dict(
        level=level, n_epidemic=len(epi), n_watch=len(watch), n_regions=len(regions),
        n_rising=len(rising), n_reporting=n_reporting, n_intro=len(intro), n_intro_regions=len(intro_regions),
        share_epidemic=(len(epi) / n_reporting) if n_reporting else 0.0,
        regions=sorted(regions),
    )


# --------------------------------------------------------------------------- forecasting
HORIZON = 4


def _f_naive(train: np.ndarray, h: int) -> np.ndarray:
    v = train[-4:]
    v = v[~np.isnan(v)]
    lvl = float(v.mean()) if len(v) else 0.0
    return np.full(h, lvl)


def _f_growth(train: np.ndarray, h: int, phi: float = 0.7) -> np.ndarray:
    g = poisson_growth(train[-6:], min_events=15)
    base = _f_naive(train, h)
    if g is None:
        return base
    # level = fitted value at last point; growth damped geometrically
    w = train[-6:]
    t = np.arange(len(w), dtype=float)
    m = ~np.isnan(w)
    lvl_fit = float(np.exp(np.log(max(w[m].mean(), 0.5)) + g.r_week * (t[-1] - t[m].mean())))
    steps = np.cumsum([phi ** (k + 1) for k in range(h)])
    return lvl_fit * np.exp(g.r_week * steps)


def _f_holt_log(train: np.ndarray, h: int, alpha: float = 0.5, beta: float = 0.2, phi: float = 0.8) -> np.ndarray:
    z = np.log1p(np.nan_to_num(train, nan=0.0))
    if len(z) < 4:
        return _f_naive(train, h)
    lvl, tr = z[0], z[1] - z[0]
    for v in z[1:]:
        new = alpha * v + (1 - alpha) * (lvl + phi * tr)
        tr = beta * (new - lvl) + (1 - beta) * phi * tr
        lvl = new
    steps = np.cumsum([phi ** (k + 1) for k in range(h)])
    return np.expm1(lvl + steps * tr)


MODELS = {"naive": _f_naive, "damped_growth": _f_growth, "holt_log": _f_holt_log}


def _backtest(y: np.ndarray, h: int, min_train: int = 20, last_origins: int = 60):
    """Rolling-origin errors on log1p scale: errs[model][k] = list of (origin, err) for horizon k+1."""
    n = len(y)
    origins = [t for t in range(max(min_train, n - h - last_origins), n - h + 1) if t >= min_train]
    errs = {m: [[] for _ in range(h)] for m in MODELS}
    for t in origins:
        train = y[:t]
        if np.isnan(train[-4:]).all():
            continue
        for name, f in MODELS.items():
            pred = np.maximum(f(train, h), 0.0)
            for k in range(h):
                actual = y[t + k]
                if not np.isnan(actual):
                    errs[name][k].append((t, float(np.log1p(actual) - np.log1p(pred[k]))))
    return errs


def forecast(dates: list[date], y: np.ndarray, h: int = HORIZON) -> dict | None:
    """h-week forecast with empirical (back-test) 80% interval and honest skill metrics."""
    y = np.asarray(y, float)
    if len(y) < 30 or np.isnan(y[-8:]).all() or np.nansum(y[-8:]) == 0:
        return None
    errs = _backtest(y, h)
    mae = {}
    for m in MODELS:
        flat = [abs(e) for k in range(h) for _, e in errs[m][k]]
        mae[m] = float(np.mean(flat)) if flat else float("inf")
    n_orig = len(errs["naive"][0])
    if n_orig < 12:
        return None
    best = min(mae, key=lambda m: mae[m])
    skill = 1.0 - mae[best] / mae["naive"] if mae["naive"] > 0 else 0.0

    # interval half-widths per horizon from the first 60% of errors; check coverage on the last 40%
    q_lo, q_hi, cover_hits, cover_n = [], [], 0, 0
    for k in range(h):
        e = sorted(errs[best][k], key=lambda x: x[0])
        vals = np.array([v for _, v in e])
        cut = max(int(len(vals) * 0.6), 5)
        lo_q, hi_q = (np.quantile(vals[:cut], [0.10, 0.90]) if len(vals) >= 8 else (-0.7, 0.7))
        for v in vals[cut:]:
            cover_n += 1
            cover_hits += int(lo_q <= v <= hi_q)
        full = vals if len(vals) >= 8 else None
        q_lo.append(float(np.quantile(full, 0.10)) if full is not None else -0.7)
        q_hi.append(float(np.quantile(full, 0.90)) if full is not None else 0.7)
    point = np.maximum(MODELS[best](y, h), 0.0)
    last = dates[-1]
    pts = []
    for k in range(h):
        lo = max(float(np.expm1(np.log1p(point[k]) + q_lo[k])), 0.0)
        hi = float(np.expm1(np.log1p(point[k]) + q_hi[k]))
        pts.append(dict(week_start=(last + timedelta(days=7 * (k + 1))).isoformat(),
                        value=float(point[k]), low=lo, high=hi))
    cov = (cover_hits / cover_n) if cover_n >= 10 else None
    reliable = bool(skill > 0.05 and n_orig >= 20 and (cov is None or 0.6 <= cov <= 0.95))
    return dict(
        model=best, horizon_weeks=h, points=pts,
        metrics=dict(mae_log=mae, skill_vs_naive=float(skill), coverage80_out_of_sample=cov,
                     n_backtest_origins=n_orig),
        reliable=reliable,
    )
