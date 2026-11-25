"""Automatic analysis of one (indicator, country) series.

Output is a list of *structured findings* (key + params). Text in fa/en is produced from
fixed templates, so every number is computed by code in analytics.py. An LLM may optionally
rephrase the findings (see llm.py) but is never the source of a number.
"""
from __future__ import annotations

import re
import statistics

from sqlalchemy.orm import Session

from . import analytics as A
from .measures import DATA_QUALITY, UNITS
from .models import Country, Indicator
from .queries import latest_year, series, year_slice

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_fa_digits(s: str) -> str:
    """Persian digits; '.'/',' only become decimal/thousands marks when between digits."""
    s = re.sub(r"(?<=\d)\.(?=\d)", "٫", s)
    s = re.sub(r"(?<=\d),(?=\d)", "٬", s)
    return s.translate(_FA_DIGITS)


def fmt(v: float | None) -> str:
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1000:
        return f"{v:,.0f}"
    if a >= 100:
        return f"{v:.0f}"
    if a >= 10:
        return f"{v:.1f}"
    if a >= 1:
        return f"{v:.2f}"
    return f"{v:.3g}"


TEMPLATES = {
    "latest": (
        "In {year}, {country} had {value} {unit}{ui}.",
        "در سال {year}، مقدار برای {country} برابر با {value} {unit}{ui} بوده است.",
    ),
    "rank": (
        "Rank {rank} of {n} countries with data (rank 1 = highest value; {pct}th percentile). "
        "This is {ratio}× the global median.",
        "رتبه‌ی {rank} از {n} کشور دارای داده (رتبه‌ی ۱ = بالاترین مقدار؛ صدک {pct}). "
        "این مقدار {ratio} برابر میانه‌ی جهانی است.",
    ),
    "region": (
        "Compared with other countries in {region}, the value is {ratio}× the regional median.",
        "در مقایسه با سایر کشورهای منطقه‌ی «{region}»، مقدار {ratio} برابر میانه‌ی منطقه است.",
    ),
    "trend_up": (
        "Between {y0} and {y1} the value rose by {pct}% ({cagr}% per year); the trend is "
        "statistically distinguishable from flat.",
        "بین سال‌های {y0} و {y1} مقدار {pct}٪ افزایش یافته ({cagr}٪ در سال)؛ روند از نظر آماری "
        "با «بدون تغییر» تفاوت دارد.",
    ),
    "trend_down": (
        "Between {y0} and {y1} the value fell by {pct}% ({cagr}% per year); the trend is "
        "statistically distinguishable from flat.",
        "بین سال‌های {y0} و {y1} مقدار {pct}٪ کاهش یافته ({cagr}٪ در سال)؛ روند از نظر آماری "
        "با «بدون تغییر» تفاوت دارد.",
    ),
    "trend_flat": (
        "Between {y0} and {y1} there is no statistically meaningful trend.",
        "بین سال‌های {y0} و {y1} روند معناداری از نظر آماری دیده نمی‌شود.",
    ),
    "change_point": (
        "A level shift is detected around {year}: mean {before} → {after} ({shift}%). "
        "Check for a real outbreak/programme change versus a reporting or definition change.",
        "حدود سال {year} یک جهش سطحی دیده می‌شود: میانگین {before} ← {after} ({shift}٪). "
        "بررسی کنید که آیا اپیدمی یا تغییر برنامه‌ی واقعی بوده یا تغییر در گزارش‌دهی/تعریف.",
    ),
    "anomaly": (
        "Unusual year-over-year change in {year}: {change}%.",
        "تغییر غیرمعمول نسبت به سال قبل در {year}: {change}٪.",
    ),
    "forecast": (
        "Indicative statistical extrapolation for {year}: {value} (range {low}–{high}). "
        "This is not a forecast of outbreaks or of the effect of future interventions.",
        "برون‌یابی آماری تقریبی برای {year}: {value} (دامنه {low}–{high}). "
        "این پیش‌بینی وقوع اپیدمی یا اثر مداخلات آینده نیست.",
    ),
    "caveat_count": (
        "Values are absolute counts and scale with population size; compare countries using rates.",
        "مقادیر، تعداد مطلق هستند و با اندازه‌ی جمعیت تغییر می‌کنند؛ برای مقایسه‌ی کشورها از نرخ استفاده کنید.",
    ),
    "caveat_quality": ("{note}", "{note}"),
    "caveat_sparse": (
        "Only {n} data points are available; trend statements are unreliable.",
        "فقط {n} نقطه‌ی داده در دسترس است؛ نتیجه‌گیری درباره‌ی روند قابل اعتماد نیست.",
    ),
}


def render(key: str, params: dict, lang: str) -> str:
    tpl = TEMPLATES[key][1 if lang == "fa" else 0]
    text = tpl.format(**params)
    return to_fa_digits(text) if lang == "fa" else text


def _finding(key: str, params: dict, severity: str = "info") -> dict:
    return dict(
        key=key,
        severity=severity,
        params=params,
        text_en=render(key, params, "en"),
        text_fa=render(key, params, "fa"),
    )


def analyze(
    db: Session, ind: Indicator, country: Country, sex: str = "ALL", age: str = "ALL",
    window: int = 15,
) -> dict:
    obs = series(db, ind.id, country.iso3, sex, age)
    if not obs:
        return dict(findings=[], facts={}, points=0)

    years = [o.year for o in obs]
    values = [o.value for o in obs]
    last = obs[-1]
    unit_en = UNITS.get(ind.unit, {}).get("en", ind.unit)
    unit_fa = UNITS.get(ind.unit, {}).get("fa", ind.unit)
    findings: list[dict] = []
    facts: dict = dict(year=last.year, value=last.value, low=last.low, high=last.high)

    ui = f" (95% UI {fmt(last.low)}–{fmt(last.high)})" if last.low is not None and last.high is not None else ""
    ui_fa = f" (بازه‌ی عدم‌قطعیت {fmt(last.low)}–{fmt(last.high)})" if ui else ""
    f = _finding("latest", dict(year=last.year, country=country.name_en, value=fmt(last.value),
                                unit=unit_en, ui=ui))
    # Persian variant uses Persian country name/unit
    params_fa = dict(year=last.year, country=country.name_fa or country.name_en,
                     value=fmt(last.value), unit=unit_fa, ui=ui_fa)
    f["text_fa"] = render("latest", params_fa, "fa")
    findings.append(f)

    # --- ranking vs world / region (latest year) -------------------------------------------
    yr = latest_year(db, ind.id, sex, age)
    if yr is not None and ind.unit != "count":
        rows = year_slice(db, ind.id, yr, sex, age)
        peers = [(o.value, c) for o, c in rows]
        if len(peers) >= 20:
            all_vals = [v for v, _ in peers]
            mine = next((o.value for o, c in rows if c.iso3 == country.iso3), None)
            if mine is not None:
                rank = 1 + sum(1 for v in all_vals if v > mine)
                med = statistics.median(all_vals)
                ratio = mine / med if med else None
                if ratio is not None:
                    facts.update(rank=rank, n_countries=len(all_vals), global_median=med)
                    findings.append(_finding("rank", dict(
                        rank=rank, n=len(all_vals), ratio=fmt(ratio),
                        pct=f"{A.percentile_rank(mine, all_vals):.0f}")))
                reg_vals = [v for v, c in peers if c.region and c.region == country.region]
                if country.region and len(reg_vals) >= 5:
                    rmed = statistics.median(reg_vals)
                    if rmed:
                        findings.append(_finding("region", dict(region=country.region,
                                                                ratio=fmt(mine / rmed))))

    # --- trend ---------------------------------------------------------------------------------
    w_years, w_vals = years[-window:], values[-window:]
    if len(w_years) < 5:
        findings.append(_finding("caveat_sparse", dict(n=len(w_years)), "warning"))
    else:
        t = A.linear_trend(w_years, w_vals)
        if t:
            pc = A.pct_change(w_vals[0], w_vals[-1])
            cg = A.cagr(w_vals[0], w_vals[-1], w_years[-1] - w_years[0])
            facts.update(trend=t.direction, trend_slope=t.slope, trend_p=t.p_approx)
            base = dict(y0=w_years[0], y1=w_years[-1],
                        pct=fmt(abs(pc)) if pc is not None else "—",
                        cagr=fmt(abs(cg)) if cg is not None else "—")
            if t.direction == "increasing":
                findings.append(_finding("trend_up", base, "notable"))
            elif t.direction == "decreasing":
                findings.append(_finding("trend_down", base))
            else:
                findings.append(_finding("trend_flat", base))

    # --- structural changes ------------------------------------------------------------------
    cp = A.change_point(years, values)
    if cp:
        facts["change_point"] = cp
        findings.append(_finding("change_point", dict(
            year=cp["year"], before=fmt(cp["mean_before"]), after=fmt(cp["mean_after"]),
            shift=f"{cp['shift_pct']:+.0f}"), "warning"))
    for a in A.yoy_anomalies(years, values)[-3:]:
        findings.append(_finding("anomaly", dict(year=a["year"], change=f"{a['change_pct']:+.0f}"),
                                 "warning"))

    # --- indicative forecast ----------------------------------------------------------------
    fc = A.forecast_holt(years, values, 5)
    if fc:
        p = fc["points"][-1]
        facts["forecast"] = p
        findings.append(_finding("forecast", dict(year=p["year"], value=fmt(p["value"]),
                                                  low=fmt(p["low"]), high=fmt(p["high"]))))

    # --- caveats (always shown) ---------------------------------------------------------------
    q = DATA_QUALITY.get(last.data_quality)
    if q:
        f = _finding("caveat_quality", dict(note=q["note_en"]), "warning")
        f["text_fa"] = render("caveat_quality", dict(note=q["note_fa"]), "fa")
        findings.append(f)
    if ind.unit == "count":
        findings.append(_finding("caveat_count", {}, "warning"))

    return dict(findings=findings, facts=facts, points=len(obs))
