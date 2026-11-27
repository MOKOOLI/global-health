"""Direct age standardisation (age-standardised rate, ASR) with a Fay-Feuer gamma confidence interval.

Why: crude rates mislead when comparing a young population with an old one. The ASR re-weights each
country's age-specific rates to one common standard population.

Standard populations:
* `segi`  - Segi world standard (as used by GLOBOCAN "world (Segi-Doll)"), 18 groups, sums to 100,000 (checked).
* `who2000` - WHO World Standard Population 2000-2025, 21 groups. Weights were checked against the published
  table (Ahmad et al. 2001; identical to the SEER copy, total 100.035 per 100) and are NORMALISED to sum to 1.
* `custom` - caller supplies weights.

The chi-square quantiles use the Wilson-Hilferty approximation (no SciPy dependency); intervals are
unreliable when the total number of cases is below ~10, and the result says so.
"""
from __future__ import annotations

import math
from statistics import NormalDist

SEGI = [12000, 10000, 9000, 9000, 8000, 8000, 6000, 6000, 6000, 6000, 5000, 4000, 4000, 3000, 2000, 1000, 500, 500]
SEGI_LABELS = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54",
               "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85+"]
WHO2000 = [8860, 8690, 8600, 8470, 8220, 7930, 7610, 7150, 6590, 6040, 5370, 4550, 3720, 2960, 2210, 1520, 910, 440,
           150, 40, 5]
WHO2000_LABELS = SEGI_LABELS[:-1] + ["85-89", "90-94", "95-99", "100+"]

STANDARDS = {"segi": (SEGI_LABELS, SEGI), "who2000": (WHO2000_LABELS, WHO2000)}


def _chi2_quantile(p: float, k: float) -> float:
    """Wilson-Hilferty approximation to the chi-square quantile."""
    z = NormalDist().inv_cdf(p)
    return k * (1 - 2 / (9 * k) + z * math.sqrt(2 / (9 * k))) ** 3


def standardise(cases: list[float], pop: list[float], weights: list[float], per: float = 100_000.0,
                confidence: float = 0.95) -> dict:
    n = len(cases)
    if not (n == len(pop) == len(weights)) or n < 2:
        raise ValueError("cases, pop and weights need the same length (>= 2 age groups)")
    if any(c < 0 for c in cases) or any(p <= 0 for p in pop) or any(w < 0 for w in weights):
        raise ValueError("cases must be >= 0, populations > 0, weights >= 0")
    tw = sum(weights)
    if tw <= 0:
        raise ValueError("weights sum to zero")
    w = [x / tw for x in weights]
    rates = [c / p for c, p in zip(cases, pop)]
    asr = sum(wi * r for wi, r in zip(w, rates))
    crude = sum(cases) / sum(pop)
    total_cases = sum(cases)
    out = dict(asr=asr * per, crude=crude * per, per=per, total_cases=total_cases,
               age_specific=[r * per for r in rates], weights=w, warnings=[])
    v = sum((wi / p) ** 2 * c for wi, p, c in zip(w, pop, cases))
    if asr <= 0 or v <= 0:
        out.update(low=0.0, high=None)
        out["warnings"].append("No cases: the interval cannot be computed.")
        return out
    wm = max(wi / p for wi, p in zip(w, pop))
    a = 1 - confidence
    low = (v / (2 * asr)) * _chi2_quantile(a / 2, 2 * asr * asr / v)
    high = ((v + wm * wm) / (2 * (asr + wm))) * _chi2_quantile(1 - a / 2, 2 * (asr + wm) ** 2 / (v + wm * wm))
    out.update(low=max(low, 0.0) * per, high=high * per, confidence=confidence)
    if total_cases < 10:
        out["warnings"].append("Fewer than 10 cases in total: the interval is unreliable.")
    return out
