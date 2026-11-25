"""Surveillance service: loads weekly series, runs outbreak.py, builds fa/en findings."""
from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import outbreak as O
from .insights import fmt, to_fa_digits
from .models import Country, Disease, Source, SurveillanceSeries, SurveillanceWeekly

METRIC_PRIORITY = ["new_cases", "ili_pct", "new_deaths"]
STALE_WEEKS = 3

PHASES = {
    "no_data": dict(en="Insufficient data", fa="داده‌ی ناکافی",
                    desc_en="Fewer than 8 weeks of data in the last 26 weeks.",
                    desc_fa="کمتر از ۸ هفته داده در ۲۶ هفته‌ی اخیر."),
    "inactive": dict(en="No activity", fa="بدون فعالیت",
                     desc_en="No reported events in the last 8 weeks.", desc_fa="در ۸ هفته‌ی اخیر موردی گزارش نشده."),
    "sporadic": dict(en="Sporadic", fa="پراکنده",
                     desc_en="Events reported in fewer than 80% of the last 52 weeks.",
                     desc_fa="در کمتر از ۸۰٪ هفته‌های ۵۲ هفته‌ی اخیر مورد گزارش شده."),
    "endemic": dict(en="Endemic level", fa="سطح اندمیک",
                    desc_en="Continuously present (≥80% of weeks) and within the expected range.",
                    desc_fa="حضور مداوم (≥۸۰٪ هفته‌ها) و در محدوده‌ی مورد انتظار."),
    "watch": dict(en="Watch", fa="تحت نظر",
                  desc_en="One week above the expected range that is rising or clearly high, or fast significant growth.",
                  desc_fa="یک هفته بالاتر از حد انتظار با روند صعودی یا بسیار بالا، یا رشد سریع و معنادار."),
    "epidemic": dict(en="Above expected (epidemic signal)", fa="بالاتر از حد انتظار (سیگنال اپیدمی)",
                     desc_en="At least 2 of the last 3 weeks above the upper expected limit.",
                     desc_fa="دست‌کم ۲ هفته از ۳ هفته‌ی اخیر بالاتر از حد بالای مورد انتظار."),
    "declining": dict(en="Declining after a peak", fa="در حال فروکش پس از اوج",
                      desc_en="Was above expected 4-11 weeks ago, now back within range.",
                      desc_fa="۴ تا ۱۱ هفته پیش بالاتر از حد انتظار بوده و اکنون به محدوده بازگشته."),
}
PATTERNS = {
    "none": dict(en="No alert pattern", fa="بدون الگوی هشدار"),
    "watch": dict(en="Watch", fa="تحت نظر"),
    "single_country": dict(en="Signal in one country", fa="سیگنال در یک کشور"),
    "regional_outbreak": dict(en="Regional outbreak pattern", fa="الگوی شیوع منطقه‌ای"),
    "multi_region_outbreak": dict(en="Multi-region outbreak pattern", fa="الگوی شیوع چندمنطقه‌ای"),
    "novel_spread": dict(en="Novel spread: first cases in several regions", fa="گسترش نوپدید: نخستین موارد در چند منطقه"),
    "pandemic_pattern": dict(en="Pandemic-like spread pattern", fa="الگوی گسترش شبه‌پاندمیک"),
}
PATTERN_NOTE = dict(
    en="A statistical pattern in reported data, not a declaration. Epidemics, PHEICs and pandemics are "
       "declared by WHO and national authorities.",
    fa="این یک الگوی آماری در داده‌های گزارش‌شده است، نه اعلام رسمی. اعلام اپیدمی، PHEIC و پاندمی "
       "بر عهده‌ی WHO و مراجع ملی است.",
)
PATTERN_RULES = dict(
    en="Pandemic-like: ≥20 countries with an epidemic signal, ≥4 WHO regions, most rising. Novel spread: first-ever "
       "cases in ≥5 countries across ≥3 regions within 5 weeks. Multi-region: ≥3 countries in ≥2 regions. "
       "Regional: ≥2 countries.",
    fa="شبه‌پاندمیک: ≥۲۰ کشور با سیگنال اپیدمی، ≥۴ منطقه‌ی WHO و بیشترشان صعودی. گسترش نوپدید: نخستین موارد در ≥۵ کشور "
       "از ≥۳ منطقه در ۵ هفته. چندمنطقه‌ای: ≥۳ کشور در ≥۲ منطقه. منطقه‌ای: ≥۲ کشور.",
)


@dataclass
class SeriesData:
    iso3: str
    name_en: str
    name_fa: str | None
    who_region: str | None
    source_code: str
    source_name: str
    metric: str
    unit: str
    note: str | None
    dates: list[date]
    y: np.ndarray
    base: O.Baseline
    first_event: date | None = None
    smoothed: bool = False   # batch reporting detected: analysis uses a trailing 4-week mean
    raw: np.ndarray | None = None
    cache: dict = field(default_factory=dict)  # index -> Assessment


@dataclass
class Loaded:
    disease: Disease
    series: dict[str, SeriesData]
    gi: tuple[float, float] | None
    ds_start: date | None = None  # earliest date in the whole dataset


_CACHE: dict[int, tuple[tuple, Loaded]] = {}


def _signature(db: Session, disease_id: int):
    return tuple(db.execute(
        select(func.count(SurveillanceWeekly.id), func.max(SurveillanceWeekly.week_start))
        .join(SurveillanceSeries, SurveillanceSeries.id == SurveillanceWeekly.series_id)
        .where(SurveillanceSeries.disease_id == disease_id)
    ).one())


def load_disease(db: Session, disease: Disease) -> Loaded | None:
    sig = _signature(db, disease.id)
    hit = _CACHE.get(disease.id)
    if hit and hit[0] == sig:
        return hit[1]
    rows = db.execute(
        select(SurveillanceSeries, Country, Source)
        .join(Country, Country.iso3 == SurveillanceSeries.country_iso3)
        .join(Source, Source.id == SurveillanceSeries.source_id)
        .where(SurveillanceSeries.disease_id == disease.id)
    ).all()
    if not rows:
        return None
    metrics = {s.metric for s, _, _ in rows}
    metric = next((m for m in METRIC_PRIORITY if m in metrics), sorted(metrics)[0])
    rows = [r for r in rows if r[0].metric == metric]
    weekly: dict[int, list[tuple[date, float]]] = {}
    for sid, wk, v in db.execute(select(SurveillanceWeekly.series_id, SurveillanceWeekly.week_start,
                                        SurveillanceWeekly.value).where(
            SurveillanceWeekly.series_id.in_([s.id for s, _, _ in rows]))):
        weekly.setdefault(sid, []).append((wk, v))
    best: dict[str, tuple[date, SeriesData]] = {}
    for s, c, src in rows:
        pts = weekly.get(s.id)
        if not pts:
            continue
        dates, raw = O.weekly_grid([p[0] for p in pts], [p[1] for p in pts])
        y, smoothed = O.regularize(raw) if s.unit == "count" else (raw, False)
        pos = np.where(np.nan_to_num(raw, nan=0.0) > 0)[0]
        cur = best.get(c.iso3)
        if cur is None or dates[-1] > cur[0]:
            best[c.iso3] = (dates[-1], SeriesData(
                c.iso3, c.name_en, c.name_fa, c.who_region, src.code, src.name, s.metric, s.unit, s.note,
                dates, y, O.compute_baseline(y), dates[int(pos[0])] if len(pos) else None, smoothed, raw))
    ds_start = min((v[1].dates[0] for v in best.values()), default=None)
    loaded = Loaded(disease, {k: v[1] for k, v in best.items()}, O.GENERATION_INTERVALS.get(disease.slug), ds_start)
    _CACHE[disease.id] = (sig, loaded)
    return loaded


def dataset_as_of(loaded: Loaded) -> date:
    return max(sd.dates[-1] for sd in loaded.series.values())


def _index_at(sd: SeriesData, as_of: date) -> int:
    return bisect_right(sd.dates, as_of) - 1


def assess(loaded: Loaded, sd: SeriesData, i: int) -> O.Assessment:
    a = sd.cache.get(i)
    if a is None:
        a = O.assess_at(sd.dates, sd.y, sd.base, i, unit=sd.unit, gi=loaded.gi)
        sd.cache[i] = a
    return a


INTRO_MIN_PRIOR_WEEKS = 3
INTRO_WINDOW_WEEKS = 5


def introduced(loaded: Loaded, sd: SeriesData, d: date) -> bool:
    """First-ever case in this series within the last 5 weeks, after >=3 weeks of dataset history
    in which this country had none. Needs no baseline, so it works for brand-new pathogens."""
    fe, ds = sd.first_event, loaded.ds_start
    if fe is None or ds is None:
        return False
    return (fe - ds).days >= 7 * INTRO_MIN_PRIOR_WEEKS and 0 <= (d - fe).days < 7 * INTRO_WINDOW_WEEKS


def statuses(loaded: Loaded, as_of: date, lang: str = "en") -> list[dict]:
    out = []
    for sd in loaded.series.values():
        i = _index_at(sd, as_of)
        if i < 0:
            continue
        a = assess(loaded, sd, i)
        stale = (as_of - sd.dates[i]).days > 7 * STALE_WEEKS
        out.append(dict(
            iso3=sd.iso3, name=(sd.name_fa or sd.name_en) if lang == "fa" else sd.name_en,
            who_region=sd.who_region, phase=a.phase, trend=a.trend, stale=stale,
            last_week=a.last_week.isoformat() if a.last_week else None, last_value=a.last_value,
            expected=a.expected, upper=a.upper, ratio=a.ratio, score=a.score,
            growth=a.growth, r_estimate=a.r_estimate, baseline_method=a.baseline_method,
            source=sd.source_code, intro=introduced(loaded, sd, sd.dates[i]), smoothed=sd.smoothed,
        ))
    return out


def pattern(rows: list[dict]) -> dict:
    live = [r for r in rows if not r["stale"] and (r["phase"] != "no_data" or r.get("intro"))]
    return O.global_pattern(
        [dict(iso3=r["iso3"], region=r["who_region"], phase=r["phase"], trend=r["trend"], intro=r.get("intro", False))
         for r in live],
        len(live),
    )


def replay(loaded: Loaded) -> list[dict]:
    """Pattern timeline over the whole history, each week using only data known at that week."""
    all_dates = sorted({d for sd in loaded.series.values() for d in sd.dates})
    idx = {iso: {d: i for i, d in enumerate(sd.dates)} for iso, sd in loaded.series.items()}
    out = []
    for d in all_dates:
        rows = []
        for iso, sd in loaded.series.items():
            i = idx[iso].get(d)
            if i is None:
                continue
            a = assess(loaded, sd, i)
            rows.append(dict(iso3=iso, who_region=sd.who_region, phase=a.phase, trend=a.trend, stale=False,
                             intro=introduced(loaded, sd, d)))
        p = pattern(rows)
        out.append(dict(week_start=d.isoformat(), **{k: p[k] for k in
                    ("level", "n_epidemic", "n_watch", "n_regions", "n_rising", "n_reporting")}))
    return out


# ------------------------------------------------------------------------------- findings
def _pct_week(r: float) -> float:
    return (math.exp(r) - 1.0) * 100.0


T = {
    "phase": ("As of the week of {week}: {phase}. Reported {last} vs {expected} expected (upper limit {upper}).",
              "تا هفته‌ی {week}: «{phase}». {last} مورد گزارش‌شده در برابر {expected} مورد مورد انتظار (حد بالا {upper})."),
    "phase_basic": ("As of the week of {week}: {phase}. Reported {last} in the latest week.",
                    "تا هفته‌ی {week}: «{phase}». {last} مورد در آخرین هفته گزارش شده است."),
    "growth": ("Over the last {n} weeks cases changed by {pct}% per week (95% CI {lo}% to {hi}%); "
               "{kind} time ≈ {days} days.",
               "در {n} هفته‌ی اخیر موارد به‌طور متوسط {pct}٪ در هفته تغییر کرده‌اند (بازه‌ی ۹۵٪: {lo}٪ تا {hi}٪)؛ "
               "زمان {kind} ≈ {days} روز."),
    "growth_flat": ("No statistically significant growth or decline over the last {n} weeks.",
                    "در {n} هفته‌ی اخیر رشد یا کاهش معنادار آماری دیده نمی‌شود."),
    "r": ("Approximate reproduction number R ≈ {r} (range {lo}–{hi}), assuming a generation interval of "
          "{gm} ± {gs} days. Indicative only.",
          "عدد تولید مثل تقریبی R ≈ {r} (دامنه {lo}–{hi}) با فرض فاصله‌ی نسل {gm} ± {gs} روز. فقط راهنما."),
    "forecast": ("Indicative forecast for the week of {week}: {value} (80% interval {lo}–{hi}).",
                 "پیش‌بینی تقریبی برای هفته‌ی {week}: {value} (بازه‌ی ۸۰٪: {lo}–{hi})."),
    "forecast_skill": ("Back-test ({n} past forecasts): the '{model}' model's error was {skill}% {cmp} than a "
                       "naive forecast; its 80% interval contained the truth {cov} of the time out of sample.",
                       "بک‌تست ({n} پیش‌بینی گذشته): خطای مدل «{model}» {skill}٪ {cmp} از پیش‌بینی ساده بود؛ "
                       "بازه‌ی ۸۰٪ آن در {cov} موارد خارج از نمونه حاوی مقدار واقعی بود."),
    "forecast_unreliable": ("The forecast did not meet the reliability criteria in back-testing "
                            "(skill over naive >5% and calibrated interval). Treat it as illustrative.",
                            "پیش‌بینی معیارهای اعتبار را در بک‌تست برآورده نکرد (برتری >۵٪ نسبت به پیش‌بینی ساده و "
                            "بازه‌ی کالیبره). آن را صرفاً تصویری در نظر بگیرید."),
    "caveat_reporting": ("Counts depend on testing and reporting practices; changes in either can look like "
                         "changes in disease activity.",
                         "شمارش‌ها به آزمایش و شیوه‌ی گزارش‌دهی وابسته‌اند؛ تغییر در آن‌ها می‌تواند شبیه تغییر در "
                         "فعالیت بیماری باشد."),
    "caveat_baseline": ("Less than a year of history: the expected level is taken from the last few weeks only, "
                        "so slow, sustained increases may be absorbed into the baseline.",
                        "کمتر از یک سال سابقه موجود است: سطح مورد انتظار فقط از چند هفته‌ی اخیر گرفته شده و "
                        "افزایش‌های آهسته و پایدار ممکن است در خط پایه جذب شوند."),
    "caveat_stale": ("The latest data point is {n} weeks older than the newest data in this dataset.",
                     "آخرین داده {n} هفته قدیمی‌تر از جدیدترین داده‌ی این مجموعه است."),
}


def _f(key: str, severity: str = "info", **p) -> dict:
    en, fa = T[key]
    return dict(key=key, severity=severity, text_en=en.format(**p), text_fa=to_fa_digits(fa.format(**p)))


def series_findings(loaded: Loaded, sd: SeriesData, i: int, fc: dict | None, newest: date) -> list[dict]:
    a = assess(loaded, sd, i)
    out: list[dict] = []
    ph = PHASES[a.phase]
    wk = a.last_week.isoformat() if a.last_week else "—"
    sev = "warning" if a.phase == "epidemic" else "notable" if a.phase == "watch" else "info"
    if a.expected is not None:
        f = _f("phase", sev, week=wk, phase=ph["en"], last=fmt(a.last_value), expected=fmt(a.expected), upper=fmt(a.upper))
        f["text_fa"] = to_fa_digits(T["phase"][1].format(week=wk, phase=ph["fa"], last=fmt(a.last_value),
                                                         expected=fmt(a.expected), upper=fmt(a.upper)))
    else:
        f = _f("phase_basic", sev, week=wk, phase=ph["en"], last=fmt(a.last_value))
        f["text_fa"] = to_fa_digits(T["phase_basic"][1].format(week=wk, phase=ph["fa"], last=fmt(a.last_value)))
    out.append(f)
    g = a.growth
    if g and g["significant"]:
        kind_en, kind_fa = ("doubling", "دو برابر شدن") if g["r_week"] > 0 else ("halving", "نصف شدن")
        base = dict(n=5, pct=f"{_pct_week(g['r_week']):+.0f}", lo=f"{_pct_week(g['lo']):+.0f}",
                    hi=f"{_pct_week(g['hi']):+.0f}", days=fmt(g["time_days"]))
        f = _f("growth", "warning" if g["r_week"] > 0 else "info", kind=kind_en, **base)
        f["text_fa"] = to_fa_digits(T["growth"][1].format(kind=kind_fa, **base))
        out.append(f)
    elif g:
        out.append(_f("growth_flat", n=5))
    if a.r_estimate:
        r = a.r_estimate
        out.append(_f("r", r=f"{r['mean']:.2f}", lo=f"{r['lo']:.2f}", hi=f"{r['hi']:.2f}",
                      gm=f"{r['gi_mean']:g}", gs=f"{r['gi_sd']:g}"))
    if fc:
        p = fc["points"][-1]
        out.append(_f("forecast", week=p["week_start"], value=fmt(p["value"]), lo=fmt(p["low"]), hi=fmt(p["high"])))
        m = fc["metrics"]
        skill = m["skill_vs_naive"] * 100
        cov = m["coverage80_out_of_sample"]
        f = _f("forecast_skill", n=m["n_backtest_origins"], model=fc["model"], skill=f"{abs(skill):.0f}",
               cmp="lower" if skill >= 0 else "higher", cov=("n/a" if cov is None else f"{cov:.0%}"))
        f["text_fa"] = to_fa_digits(T["forecast_skill"][1].format(
            n=m["n_backtest_origins"], model=fc["model"], skill=f"{abs(skill):.0f}",
            cmp="کمتر" if skill >= 0 else "بیشتر", cov=("نامشخص" if cov is None else f"{cov:.0%}")))
        out.append(f)
        if not fc["reliable"]:
            out.append(_f("forecast_unreliable", "warning"))
    if a.baseline_method == "recent":
        out.append(_f("caveat_baseline", "warning"))
    behind = (newest - sd.dates[i]).days // 7
    if behind > STALE_WEEKS:
        out.append(_f("caveat_stale", "warning", n=behind))
    if sd.unit == "count":
        out.append(_f("caveat_reporting", "warning"))
    return out


def series_detail(loaded: Loaded, iso3: str, as_of: date | None, with_forecast: bool, lang: str) -> dict | None:
    sd = loaded.series.get(iso3)
    if sd is None:
        return None
    newest = dataset_as_of(loaded)
    as_of = as_of or sd.dates[-1]
    i = _index_at(sd, as_of)
    if i < 0:
        return None
    a = assess(loaded, sd, i)
    fc = O.forecast(sd.dates[: i + 1], sd.y[: i + 1]) if with_forecast else None
    pts = []
    for k, d in enumerate(sd.dates):
        v = sd.y[k]
        pts.append(dict(
            week_start=d.isoformat(), value=None if np.isnan(v) else float(v),
            expected=None if np.isnan(sd.base.expected[k]) else float(sd.base.expected[k]),
            upper=None if np.isnan(sd.base.upper[k]) else float(sd.base.upper[k]),
        ))
    return dict(
        iso3=iso3, name=(sd.name_fa or sd.name_en) if lang == "fa" else sd.name_en, metric=sd.metric, unit=sd.unit,
        source=dict(code=sd.source_code, name=sd.source_name), note=sd.note, as_of_index=i,
        as_of=sd.dates[i].isoformat(),
        assessment=dict(phase=a.phase, trend=a.trend, ratio=a.ratio, score=a.score, growth=a.growth,
                        r_estimate=a.r_estimate, baseline_method=a.baseline_method,
                        exceedances_last3=a.exceedances_last3, presence_52w=a.presence_52w),
        points=pts, forecast=fc, findings=series_findings(loaded, sd, i, fc, newest),
    )


def diseases_with_series(db: Session) -> list[Disease]:
    ids = set(db.scalars(select(SurveillanceSeries.disease_id).distinct()))
    return list(db.scalars(select(Disease).where(Disease.id.in_(ids)).order_by(Disease.name_en))) if ids else []


def today() -> date:
    return date.today()


def weeks_behind_today(d: date) -> int:
    return max((today() - d).days // 7, 0)


PHASE_CODES = ["no_data", "inactive", "sporadic", "endemic", "watch", "epidemic", "declining"]


def frames(loaded: Loaded, step: int = 1) -> dict:
    """Compact replay for animation: per week, one phase code per country (index into PHASE_CODES).

    Same causal logic as `replay`: each week uses only data known at that week.
    """
    step = max(1, int(step))
    all_dates = sorted({d for sd in loaded.series.values() for d in sd.dates})
    isos = sorted(loaded.series)
    idx = {iso: {d: i for i, d in enumerate(loaded.series[iso].dates)} for iso in isos}
    weeks, codes, levels = [], [], []
    for k, d in enumerate(all_dates):
        if not (k % step == 0 or k == len(all_dates) - 1):
            continue
        rows, row_codes = [], []
        for iso in isos:
            sd = loaded.series[iso]
            i = idx[iso].get(d)
            if i is None:
                row_codes.append(0)
                continue
            a = assess(loaded, sd, i)
            row_codes.append(PHASE_CODES.index(a.phase))
            rows.append(dict(iso3=iso, who_region=sd.who_region, phase=a.phase, trend=a.trend, stale=False,
                             intro=introduced(loaded, sd, d)))
        p = pattern(rows)
        weeks.append(d.isoformat())
        codes.append(row_codes)
        levels.append(dict(level=p["level"], n_epidemic=p["n_epidemic"], n_regions=p["n_regions"],
                           n_reporting=p["n_reporting"]))
    return dict(phase_codes=PHASE_CODES, countries=isos, weeks=weeks, codes=codes, levels=levels)
