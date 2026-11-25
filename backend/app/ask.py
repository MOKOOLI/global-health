"""Question answering over the database: "breast cancer in the UK in 2020, how much?" -> a sourced answer.

Design (clinical-facing, so the rules are strict):
* The question is turned into a STRUCTURED QUERY (disease, country, year(s), measure, sex) by deterministic
  matching against the catalogue (names, translations, aliases, typo-tolerant). Nothing is generated.
* Every number in the answer is copied from a database row and returned together with its evidence: indicator,
  source, licence, citation, data-quality class (reported / estimated / modelled), retrieval time and links.
* If the data are missing, the answer says so. It never fills gaps, never answers from memory and never
  "rounds" a missing year to a nearby one silently (a different year is labelled as such).
* Ambiguity -> the system asks (candidates), it does not guess. Typo matches are labelled.
* Personal medical questions (diagnosis, treatment, doses) are refused: this is a statistics tool.
* An LLM (Ollama) is optional and only used to extract the structured fields when the deterministic
  parser fails; every field it returns must still resolve to a real catalogue entry.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .measures import MEASURES
from .models import Country, Disease, Indicator, Observation, Source

# ------------------------------------------------------------------------------------ normalisation
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).translate(_DIGITS)
    s = s.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه").replace("‌", " ").replace("ـ", "")
    s = re.sub(r"[ً-ٟ]", "", s)  # Arabic diacritics
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def is_persian(s: str) -> bool:
    return bool(re.search(r"[؀-ۿ]", s))


# Spoken Persian years: speech recognisers often return "دو هزار و بیست" instead of 2020.
_FA_NUM = {**{w: v for w, v in zip("یک دو سه چهار پنج شش هفت هشت نه ده یازده دوازده سیزده چهارده پانزده شانزده هفده هجده نوزده".split(), list(range(1, 20)))},
           **{w: v for w, v in zip("بیست سی چهل پنجاه شصت هفتاد هشتاد نود".split(), range(20, 100, 10))},
           **{w: v for w, v in zip("صد دویست سیصد چهارصد پانصد ششصد هفتصد هشتصد نهصد".split(), [100, 200, 300, 400, 500, 600, 700, 800, 900])}}


def fa_years_to_digits(text: str) -> str:
    """Replace runs of Persian number words that spell a year (1900-2049) with digits. Other runs are left alone."""
    toks = text.split(" ")
    out, i = [], 0
    while i < len(toks):
        j, run = i, []
        while j < len(toks):
            t = toks[j]
            if t in _FA_NUM or t == "هزار":
                run.append(t)
                j += 1
            elif t == "و" and run and j + 1 < len(toks) and (toks[j + 1] in _FA_NUM or toks[j + 1] == "هزار"):
                j += 1
            else:
                break
        if run:
            total = cur = 0
            for t in run:
                if t == "هزار":
                    total += (cur or 1) * 1000
                    cur = 0
                else:
                    cur += _FA_NUM[t]
            val = total + cur
            out.append(str(val) if 1900 <= val <= 2049 else " ".join(toks[i:j]))
            i = j
        else:
            out.append(toks[i])
            i += 1
    return " ".join(out)


# ------------------------------------------------------------------------------------ aliases
# alias -> disease slug(s). Only used where the catalogue name differs from how people actually say it.
DISEASE_ALIASES: dict[str, list[str]] = {
    "سرطان سینه": ["breast-cancer"], "breast ca": ["breast-cancer"], "کانسر سینه": ["breast-cancer"],
    "tb": ["tuberculosis"], "سل ریوی": ["tuberculosis"],
    "aids": ["hiv-aids"], "hiv": ["hiv-aids"], "ایدز": ["hiv-aids"], "اچ آی وی": ["hiv-aids"],
    "کرونا": ["covid-19"], "کووید": ["covid-19"], "کوید": ["covid-19"], "covid": ["covid-19"], "coronavirus": ["covid-19"],
    "flu": ["influenza"], "سرماخوردگی فصلی": ["influenza"], "فلو": ["influenza"],
    "cancer": ["lung-cancer", "breast-cancer", "colorectal-cancer", "stomach-cancer", "oesophageal-cancer",
               "liver-cancer", "pancreatic-cancer", "prostate-cancer", "cervical-cancer", "bladder-cancer", "leukaemia"],
    "سرطان": ["lung-cancer", "breast-cancer", "colorectal-cancer", "stomach-cancer", "oesophageal-cancer",
              "liver-cancer", "pancreatic-cancer", "prostate-cancer", "cervical-cancer", "bladder-cancer", "leukaemia"],
    "colon cancer": ["colorectal-cancer"], "bowel cancer": ["colorectal-cancer"], "سرطان روده": ["colorectal-cancer"],
    "سرطان کولون": ["colorectal-cancer"], "gastric cancer": ["stomach-cancer"], "سرطان شکم": ["stomach-cancer"],
    "heart attack": ["ischaemic-heart-disease"], "سکته قلبی": ["ischaemic-heart-disease"], "coronary heart disease": ["ischaemic-heart-disease"],
    "heart disease": ["ischaemic-heart-disease"], "بیماری قلبی": ["ischaemic-heart-disease"], "بیماری عروق کرونر": ["ischaemic-heart-disease"],
    "سکته مغزی": ["stroke"], "سکته": ["stroke", "ischaemic-heart-disease"],
    "high blood pressure": ["hypertension"], "فشار خون": ["hypertension"], "فشارخون": ["hypertension"],
    "sugar": ["diabetes"], "diabetes": ["diabetes"], "قند خون": ["diabetes"],
    "dementia": ["alzheimer-dementia"], "alzheimer": ["alzheimer-dementia"], "آلزایمر": ["alzheimer-dementia"],
    "depression": ["depressive-disorders"], "افسردگی": ["depressive-disorders"], "anxiety": ["anxiety-disorders"], "اضطراب": ["anxiety-disorders"],
    "pneumonia": ["lower-respiratory-infections"], "ذات الریه": ["lower-respiratory-infections"], "ذات‌الریه": ["lower-respiratory-infections"],
    "diarrhea": ["diarrhoeal-diseases"], "diarrhoea": ["diarrhoeal-diseases"], "اسهال": ["diarrhoeal-diseases"],
    "typhoid": ["typhoid-fever"], "تیفوئید": ["typhoid-fever"], "whooping cough": ["pertussis"],
    "monkeypox": ["mpox"], "آبله میمون": ["mpox"], "ام پاکس": ["mpox"],
    "malnutrition": ["protein-energy-malnutrition"], "سوء تغذیه": ["protein-energy-malnutrition"], "anemia": ["iron-deficiency-anaemia"],
    "anaemia": ["iron-deficiency-anaemia"], "کم خونی": ["iron-deficiency-anaemia"], "car accidents": ["road-injuries"],
    "تصادف": ["road-injuries"], "تصادفات": ["road-injuries"], "road traffic": ["road-injuries"],
    "kidney disease": ["chronic-kidney-disease"], "نارسایی کلیه": ["chronic-kidney-disease"], "liver disease": ["cirrhosis"],
    "lung cancer": ["lung-cancer"], "سرطان ریه": ["lung-cancer"], "سرطان خون": ["leukaemia"], "leukemia": ["leukaemia"],
    "chd": ["ischaemic-heart-disease"], "ckd": ["chronic-kidney-disease"], "cchf": ["cchf"], "تب کریمه کنگو": ["cchf"],
}

# alias -> (iso3, subnational note)
COUNTRY_ALIASES: dict[str, tuple[str, str | None]] = {
    "uk": ("GBR", None), "u k": ("GBR", None), "united kingdom": ("GBR", None), "britain": ("GBR", None),
    "great britain": ("GBR", None), "بریتانیا": ("GBR", None), "انگلستان": ("GBR", "England"), "انگلیس": ("GBR", "England"),
    "england": ("GBR", "England"), "scotland": ("GBR", "Scotland"), "wales": ("GBR", "Wales"),
    "northern ireland": ("GBR", "Northern Ireland"), "اسکاتلند": ("GBR", "Scotland"), "ولز": ("GBR", "Wales"),
    "usa": ("USA", None), "u s a": ("USA", None), "america": ("USA", None), "united states": ("USA", None),
    "آمریکا": ("USA", None), "امریکا": ("USA", None), "ایالات متحده": ("USA", None), "ایالات متحده آمریکا": ("USA", None),
    "iran": ("IRN", None), "ایران": ("IRN", None), "persia": ("IRN", None),
    "south korea": ("KOR", None), "کره جنوبی": ("KOR", None), "north korea": ("PRK", None), "کره شمالی": ("PRK", None),
    "russia": ("RUS", None), "روسیه": ("RUS", None), "turkey": ("TUR", None), "turkiye": ("TUR", None), "ترکیه": ("TUR", None),
    "uae": ("ARE", None), "emirates": ("ARE", None), "امارات": ("ARE", None), "vietnam": ("VNM", None), "ویتنام": ("VNM", None),
    "syria": ("SYR", None), "سوریه": ("SYR", None), "tanzania": ("TZA", None), "laos": ("LAO", None),
    "drc": ("COD", None), "dr congo": ("COD", None), "democratic republic of the congo": ("COD", None),
    "republic of the congo": ("COG", None), "congo brazzaville": ("COG", None), "congo kinshasa": ("COD", None), "czechia": ("CZE", None), "czech republic": ("CZE", None),
    "هلند": ("NLD", None), "holland": ("NLD", None), "swiss": ("CHE", None), "سوئیس": ("CHE", None),
    "عربستان": ("SAU", None), "عراق": ("IRQ", None), "افغانستان": ("AFG", None), "پاکستان": ("PAK", None),
    "هند": ("IND", None), "چین": ("CHN", None), "ژاپن": ("JPN", None), "آلمان": ("DEU", None), "فرانسه": ("FRA", None),
    "ایتالیا": ("ITA", None), "اسپانیا": ("ESP", None), "کانادا": ("CAN", None), "برزیل": ("BRA", None), "مصر": ("EGY", None),
}

# (measure key in MEASURES, words). Order matters only for readability.
MEASURE_WORDS: list[tuple[str, list[str]]] = [
    ("incidence", ["incidence", "new cases", "newly diagnosed", "بروز", "موارد جدید", "مبتلایان جدید", "تازه"]),
    ("prevalence", ["prevalence", "prevalent", "شیوع", "شایع"]),
    ("mortality", ["mortality rate", "death rate", "mortality", "نرخ مرگ", "مرگ و میر", "مرگ ومیر", "میزان مرگ"]),
    ("deaths", ["deaths", "death", "died", "die", "fatalities", "مرگ", "فوت", "کشته", "جان باخت"]),
    ("daly", ["daly", "dalys", "disability adjusted", "burden"]),
    ("cases", ["cases", "case count", "how many people", "تعداد موارد", "موارد", "تعداد مبتلا", "مبتلا"]),
]

OUT_OF_SCOPE = [
    r"\b(do i have|am i sick|diagnos\w*|symptom\w*|treat\w*|cure|dose|dosage|medication|prescri\w*|should i take)\b",
    r"(تشخیص|علائم|درمان|دارو|دوز|نسخه|آیا من|من .*دارم|مصرف)",
]

SEX_WORDS = {"F": ["women", "woman", "female", "females", "girls", "زنان", "زن", "خانم"],
             "M": ["men", "man", "male", "males", "boys", "مردان", "مرد", "آقایان"]}

LATEST_WORDS = ["latest", "most recent", "recent", "current", "now", "آخرین", "اخیر", "امسال", "جدیدترین", "فعلی", "الان"]


@dataclass
class Match:
    kind: str                 # disease | country
    keys: list[str]           # slugs or iso3
    term: str                 # matched text (normalised)
    start: int
    end: int
    fuzzy: float | None = None
    note: str | None = None   # e.g. subnational: "England"


@dataclass
class Lexicon:
    disease: list[tuple[str, list[str]]] = field(default_factory=list)   # (norm term, slugs)
    country: list[tuple[str, tuple[str, str | None]]] = field(default_factory=list)


_LEX_CACHE: dict[tuple, Lexicon] = {}


def _parts(name: str) -> list[str]:
    out = {name}
    for piece in re.split(r"[()/&،,]| و ", name):
        piece = piece.strip()
        if len(piece) >= 3:
            out.add(piece)
    return [n for n in (norm(x) for x in out) if len(n) >= 2]


AMBIGUOUS_COUNTRY_WORDS = ("congo", "korea")


def build_lexicon(db: Session) -> Lexicon:
    sig = (db.scalar(select(func.count()).select_from(Disease)), db.scalar(select(func.count()).select_from(Country)))
    if sig in _LEX_CACHE:
        return _LEX_CACHE[sig]
    lex = Lexicon()
    seen: dict[str, set[str]] = {}
    for d in db.scalars(select(Disease)):
        terms = _parts(d.name_en) + _parts(d.name_fa) + [norm(d.slug.replace("-", " "))]
        for tok in re.split(r"[,\s]+", d.icd10 or ""):
            m = re.match(r"^([A-Z])(\d\d)(?:-([A-Z])(\d\d))?$", tok)   # "C33-C34" -> c33, c34
            if m:
                lo = int(m.group(2))
                hi = int(m.group(4)) if m.group(4) and m.group(3) == m.group(1) else lo
                terms += [f"{m.group(1).lower()}{n:02d}" for n in range(lo, min(hi, lo + 12) + 1)]
        for t in terms:
            seen.setdefault(t, set()).add(d.slug)
    for alias, slugs in DISEASE_ALIASES.items():
        seen.setdefault(norm(alias), set()).update(slugs)
    existing = {d.slug for d in db.scalars(select(Disease))}
    lex.disease = [(t, sorted(s & existing)) for t, s in seen.items() if s & existing]
    cseen: dict[str, tuple[str, str | None]] = {}
    shorts: dict[str, set[str]] = {}
    for c in db.scalars(select(Country)):
        for n in (c.name_en, c.name_fa):
            if n:
                cseen.setdefault(norm(n), (c.iso3, None))
                short = re.split(r",| \(", n)[0]
                if len(short) >= 4:
                    shorts.setdefault(norm(short), set()).add(c.iso3)
    for term, isos in shorts.items():       # "Korea" (two countries), "Congo" (two) stay ambiguous: never guessed
        if len(isos) == 1 and term not in cseen:
            cseen[term] = (next(iter(isos)), None)
    isos = {c.iso3 for c in db.scalars(select(Country))}
    for alias, (iso, note) in COUNTRY_ALIASES.items():
        if iso in isos:
            cseen[norm(alias)] = (iso, note)
    for amb in AMBIGUOUS_COUNTRY_WORDS:      # bare "Congo"/"Korea" name two countries: ask, never guess
        cseen.pop(amb, None)
    lex.country = list(cseen.items())
    _LEX_CACHE.clear()
    _LEX_CACHE[sig] = lex
    return lex


def _find(text: str, terms: list[tuple[str, object]], kind: str) -> list[Match]:
    """Longest-first, non-overlapping, whole-word matches."""
    spans: list[Match] = []
    taken = [False] * len(text)
    for term, payload in sorted(terms, key=lambda t: -len(t[0])):
        if term not in text:          # cheap prefilter: avoids compiling ~1000 regexes per question
            continue
        for m in re.finditer(r"(?<![\w])" + re.escape(term) + r"(?![\w])", text):
            if any(taken[m.start():m.end()]):
                continue
            for i in range(m.start(), m.end()):
                taken[i] = True
            if kind == "disease":
                spans.append(Match(kind, list(payload), term, m.start(), m.end()))  # type: ignore[arg-type]
            else:
                iso, note = payload  # type: ignore[misc]
                spans.append(Match(kind, [iso], term, m.start(), m.end(), note=note))
    return sorted(spans, key=lambda s: s.start)


def _fuzzy(text: str, terms: list[tuple[str, object]], kind: str, blocked: list[tuple[int, int]]) -> Match | None:
    tokens = [(m.group(), m.start(), m.end()) for m in re.finditer(r"\w+", text)]
    best: Match | None = None
    for n in (1, 2, 3):
        for i in range(len(tokens) - n + 1):
            s, e = tokens[i][1], tokens[i + n - 1][2]
            if any(not (e <= b0 or s >= b1) for b0, b1 in blocked):
                continue
            gram = text[s:e]
            if len(gram) < 5:
                continue
            for term, payload in terms:
                if abs(len(term) - len(gram)) > 2 or len(term) < 5:
                    continue
                r = SequenceMatcher(None, gram, term).ratio()
                if r >= 0.84 and (best is None or r > (best.fuzzy or 0)):
                    if kind == "disease":
                        best = Match(kind, list(payload), term, s, e, fuzzy=round(r, 2))  # type: ignore[arg-type]
                    else:
                        best = Match(kind, [payload[0]], term, s, e, fuzzy=round(r, 2), note=payload[1])  # type: ignore[index]
    return best


# ------------------------------------------------------------------------------------ parsing
@dataclass
class Parsed:
    diseases: list[str] = field(default_factory=list)
    country: str | None = None
    countries: list[str] = field(default_factory=list)
    country_note: str | None = None
    years: list[int] = field(default_factory=list)
    year_range: bool = False
    latest: bool = False
    measures: list[str] = field(default_factory=list)
    sex: str = "ALL"
    fuzzy: list[dict] = field(default_factory=list)
    jalali_year: int | None = None
    out_of_scope: bool = False
    lang: str = "en"


def parse(db: Session, question: str) -> Parsed:
    p = Parsed(lang="fa" if is_persian(question) else "en")
    raw = question.strip()
    text = fa_years_to_digits(norm(raw))
    if any(re.search(rx, text, re.I) for rx in OUT_OF_SCOPE):
        p.out_of_scope = True
    lex = build_lexicon(db)

    dm = _find(text, lex.disease, "disease")
    cm = _find(text, lex.country, "country")
    blocked = [(m.start, m.end) for m in dm + cm]
    if not dm:
        f = _fuzzy(text, lex.disease, "disease", blocked)
        if f:
            dm.append(f)
            blocked.append((f.start, f.end))
    if not cm:
        f = _fuzzy(text, lex.country, "country", blocked)
        if f:
            cm.append(f)
    for m in dm + cm:
        if m.fuzzy:
            p.fuzzy.append(dict(kind=m.kind, heard=text[m.start:m.end], matched=m.term, score=m.fuzzy))
    slugs: list[str] = []
    for m in dm:
        for k in m.keys:
            if k not in slugs:
                slugs.append(k)
    p.diseases = slugs
    for m in cm:
        if m.keys[0] not in p.countries and len(p.countries) < 4:
            p.countries.append(m.keys[0])
        if m.note and not p.country_note:
            p.country_note = m.note
    if p.countries:
        p.country = p.countries[0]

    # years (Gregorian); Persian-calendar years are detected and NOT silently converted
    ys = [int(y) for y in re.findall(r"(?<!\d)(19[5-9]\d|20[0-4]\d)(?!\d)", text)]
    jal = re.findall(r"(?<!\d)(13\d\d|14[0-4]\d)(?!\d)", text)
    if jal and not ys:
        p.jalali_year = int(jal[0])
    if len(ys) >= 2 and re.search(r"\b(to|until|through|from|between)\b|تا|الی|از|بین", text):
        lo, hi = min(ys), max(ys)
        p.years, p.year_range = list(range(lo, min(hi, lo + 14) + 1)), True
    else:
        p.years = sorted(set(ys))[:12]
    p.latest = any(re.search(r"(?<!\w)" + re.escape(norm(w)) + r"(?!\w)", text) for w in LATEST_WORDS)

    for key, words in MEASURE_WORDS:
        if any(re.search(r"(?<!\w)" + re.escape(norm(w)) + r"(?!\w)", text) for w in words):
            p.measures.append(key)
    if "mortality" in p.measures and "deaths" in p.measures:
        p.measures.remove("deaths")
    for code, words in SEX_WORDS.items():
        if any(re.search(r"(?<!\w)" + re.escape(norm(w)) + r"(?!\w)", text) for w in words):
            p.sex = code
            break
    return p


# ------------------------------------------------------------------------------------ answering
UNIT_TXT = {
    "per_100k": ("per 100,000 population", "به‌ازای هر ۱۰۰٬۰۰۰ نفر جمعیت"),
    "per_1000": ("per 1,000 population", "به‌ازای هر ۱۰۰۰ نفر جمعیت"),
    "count": ("persons / events", "نفر / مورد"),
    "percent": ("%", "٪"),
    "years": ("years", "سال"),
}
QUALITY_TXT = {
    "reported": ("officially reported (counted)", "گزارش‌رسمی (شمارش‌شده)"),
    "estimated": ("estimated by WHO/UN from partial data", "برآورد WHO/UN از داده‌ی ناقص"),
    "modeled": ("output of a statistical model (not a count)", "خروجی مدل آماری (نه شمارش)"),
}


def _fmt(v: float, unit: str) -> str:
    if unit == "count" or abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:,.1f}" if abs(v) >= 10 else f"{v:,.2f}"


def _sentence(lang: str, d: Disease, c: Country, ind: Indicator, o: Observation, requested: int | None, exact: bool) -> str:
    L = 0 if lang == "en" else 1
    dn = d.name_fa if lang == "fa" else d.name_en
    cn = (c.name_fa or c.name_en) if lang == "fa" else c.name_en
    meas = MEASURES.get(ind.measure, {}).get(lang, ind.measure)
    unit = UNIT_TXT.get(ind.unit, (ind.unit, ind.unit))[L]
    val = _fmt(o.value, ind.unit)
    rng = f" ({_fmt(o.low, ind.unit)} – {_fmt(o.high, ind.unit)})" if o.low is not None and o.high is not None else ""
    q = QUALITY_TXT.get(o.data_quality, (o.data_quality, o.data_quality))[L]
    if lang == "fa":
        base = f"{meas} {dn} در {cn}، سال {o.year}: {val}{rng} {unit}. نوع داده: {q}."
        if requested and not exact:
            base = f"برای سال {requested} داده‌ای در این منبع نیست. نزدیک‌ترین سال موجود: " + base
    else:
        base = f"{meas} of {dn} in {cn}, {o.year}: {val}{rng} {unit}. Data type: {q}."
        if requested and not exact:
            base = f"This source has no value for {requested}. Closest available year: " + base
    return base


def _clean(db: Session, indicator: Indicator) -> dict:
    s: Source = indicator.source
    return dict(code=indicator.code, name_en=indicator.name_en, name_fa=indicator.name_fa, measure=indicator.measure,
                unit=indicator.unit, external_code=indicator.external_code,
                source=dict(code=s.code, name=s.name, url=s.url, license=s.license, citation=s.citation,
                            is_synthetic=s.is_synthetic))


def answer(db: Session, question: str, lang: str | None = None, parsed: Parsed | None = None) -> dict:
    question = (question or "").strip()[:300]
    p = parsed or parse(db, question)
    lang = lang or p.lang
    L = 0 if lang == "en" else 1
    out: dict = dict(question=question, lang=lang, status="not_understood", interpretation={}, items=[], warnings=[],
                     candidates={}, message="", method=(
        "Deterministic matching of your question to the catalogue; every number is copied from the database with its source. "
        "No text is generated by an AI model and nothing is estimated here.",
        "تطبیق قطعی پرسش با فهرست بیماری‌ها و کشورها؛ هر عدد مستقیم از پایگاه داده با منبعش آمده است. هیچ متنی با هوش مصنوعی تولید یا چیزی تخمین زده نشده است.")[L])

    if p.out_of_scope:
        out.update(status="out_of_scope", message=(
            "This tool answers population statistics only. It cannot diagnose, advise on treatment or dosing for an individual. "
            "Please consult a clinician.",
            "این ابزار فقط آمار جمعیتی پاسخ می‌دهد. نمی‌تواند برای یک فرد تشخیص، درمان یا دوز دارو توصیه کند. لطفاً به پزشک مراجعه کنید.")[L])
        return out
    if p.jalali_year:
        out.update(status="needs_clarification", message=(
            f"{p.jalali_year} looks like a Persian-calendar year. Sources use Gregorian years; please give the Gregorian year (for example 2020).",
            f"{p.jalali_year} سال شمسی به نظر می‌رسد. منابع از سال میلادی استفاده می‌کنند؛ لطفاً سال میلادی را بنویسید (مثلاً 2020).")[L])
        return out

    diseases = {d.slug: d for d in db.scalars(select(Disease).where(Disease.slug.in_(p.diseases)))} if p.diseases else {}
    countries = [c for c in (db.get(Country, i) for i in p.countries) if c]
    country = countries[0] if countries else None
    out["interpretation"] = dict(
        disease=[dict(slug=s, name=(diseases[s].name_fa if lang == "fa" else diseases[s].name_en)) for s in p.diseases if s in diseases],
        country=dict(iso3=country.iso3, name=(country.name_fa or country.name_en) if lang == "fa" else country.name_en) if country else None,
        countries=[dict(iso3=c.iso3, name=(c.name_fa or c.name_en) if lang == "fa" else c.name_en) for c in countries],
        years=p.years, latest=p.latest, measures=p.measures, sex=p.sex, typo_corrections=p.fuzzy)

    if p.country_note:
        fa_note = {"England": "انگلستان", "Scotland": "اسکاتلند", "Wales": "ولز", "Northern Ireland": "ایرلند شمالی"}.get(p.country_note, p.country_note)
        out["warnings"].append(dict(code="subnational", text=(
            f"You asked about {p.country_note}; national sources report the United Kingdom as a whole, so the numbers below are for the UK, not {p.country_note} alone.",
            f"شما درباره‌ی {fa_note} پرسیدید؛ منابع ملی کل بریتانیا را گزارش می‌کنند، پس اعداد زیر برای کل بریتانیاست، نه فقط {fa_note}.")[L]))
    for f in p.fuzzy:
        out["warnings"].append(dict(code="typo", text=(
            f"I read “{f['heard']}” as “{f['matched']}”. Check that this is what you meant.",
            f"«{f['heard']}» را «{f['matched']}» فهمیدم. بررسی کنید همین منظور شما بوده باشد.")[L]))

    if not p.diseases:
        out.update(status="needs_clarification", message=(
            "Which disease do you mean? Name a disease, for example “breast cancer”, “tuberculosis” or “diabetes”.",
            "کدام بیماری مدنظر شماست؟ نام بیماری را بنویسید، مثلاً «سرطان پستان»، «سل» یا «دیابت».")[L])
        return out
    if len(p.diseases) > 1:
        out.update(status="needs_clarification", candidates=dict(diseases=[
            dict(slug=s, name=(diseases[s].name_fa if lang == "fa" else diseases[s].name_en)) for s in p.diseases if s in diseases]),
            message=("That could mean several diseases. Please choose one.", "این می‌تواند چند بیماری باشد. لطفاً یکی را انتخاب کنید.")[L])
        return out
    d = diseases[p.diseases[0]]
    if country is None:
        out.update(status="needs_clarification", message=(
            f"Which country? (for {d.name_en})", f"کدام کشور؟ (برای {d.name_fa})")[L])
        return out

    inds = list(db.scalars(select(Indicator).where(Indicator.disease_id == d.id)))
    # keep indicators that match the asked measure(s); if none match, say so and fall back to everything
    wanted = set(p.measures)
    if "cases" in wanted:
        wanted |= {"incidence"}
    chosen = [i for i in inds if i.measure in wanted] if wanted else inds
    if wanted and not chosen:
        out["warnings"].append(dict(code="measure_missing", text=(
            "No indicator of the type you asked for is loaded for this disease; showing what is available.",
            "برای این بیماری شاخصی از نوعی که پرسیدید بارگذاری نشده؛ آنچه موجود است نمایش داده می‌شود.")[L]))
        chosen = inds
    sex = p.sex
    items = []
    for country in countries:
        for ind in sorted(chosen, key=lambda i: (i.measure not in wanted, i.measure, i.code)):
            rows = list(db.scalars(select(Observation).where(
                Observation.indicator_id == ind.id, Observation.country_iso3 == country.iso3,
                Observation.sex == sex, Observation.age_group == "ALL").order_by(Observation.year)))
            if not rows and sex != "ALL":
                out["warnings"].append(dict(code="sex_missing", text=(
                    "No sex-specific values for this indicator; the total is not shown for a different group.",
                    "برای این شاخص مقدار جداگانه‌ی این جنس نیست؛ مقدار کل جای آن نمایش داده نمی‌شود.")[L]))
                continue
            if not rows:
                continue
            by_year = {r.year: r for r in rows}
            targets: list[int | None] = list(p.years) if p.years else [None]
            for y in targets:
                if y is None:
                    o, exact = rows[-1], True
                    if not p.latest:
                        out["warnings"].append(dict(code="year_defaulted", text=(
                            f"You did not name a year; showing the latest available ({o.year}).",
                            f"سالی نگفتید؛ آخرین سال موجود ({o.year}) نمایش داده شد.")[L]))
                        out["warnings"] = _dedupe(out["warnings"])
                elif y in by_year:
                    o, exact = by_year[y], True
                else:
                    near = min(rows, key=lambda r: (abs(r.year - y), r.year))
                    if p.year_range:
                        continue  # ranges only show years that exist
                    o, exact = near, False
                items.append(dict(
                    indicator=_clean(db, ind), country=dict(iso3=country.iso3, name=country.name_en, name_fa=country.name_fa),
                    requested_year=y, year=o.year, year_exact=exact, sex=o.sex, value=o.value, low=o.low, high=o.high,
                    quality=o.data_quality, retrieved_at=o.retrieved_at.isoformat() if o.retrieved_at else None,
                    text=_sentence(lang, d, country, ind, o, y, exact),
                    links=dict(disease=f"/{lang}/disease/{d.slug}?country={country.iso3}",
                               csv=f"/api/export/indicator/{ind.code}.csv", cite=dict(kind="indicator", key=ind.code))))
    for c in countries:
        if not any(i["country"]["iso3"] == c.iso3 for i in items) and items:
            out["warnings"].append(dict(code="country_no_data", text=(
                f"No data for {c.name_en} in this database; nothing was estimated.",
                f"برای {c.name_fa or c.name_en} در این پایگاه داده‌ای نیست؛ چیزی تخمین زده نشد.")[L]))
    out["items"] = items
    if not items:
        have = db.execute(select(Indicator.code, Source.name).join(Source, Source.id == Indicator.source_id)
                          .where(Indicator.disease_id == d.id)).all()
        out.update(status="no_data", message=(
            (f"No data for {d.name_en} in {', '.join(c.name_en for c in countries)} is loaded in this database"
             + (f" (indicators exist from: {', '.join(sorted({n for _, n in have}))})." if have else " (no indicators are loaded for this disease yet)."))
            + " Nothing was estimated.",
            (f"داده‌ای برای {d.name_fa} در {'، '.join((c.name_fa or c.name_en) for c in countries)} در این پایگاه بارگذاری نشده"
             + (f" (شاخص‌ها از این منابع هست: {', '.join(sorted({n for _, n in have}))})." if have else " (هنوز شاخصی برای این بیماری بارگذاری نشده)."))
            + " چیزی تخمین زده نشد.")[L])
        return out

    # caveats that protect the reader
    if any(i["indicator"]["source"]["is_synthetic"] for i in items):
        out["warnings"].insert(0, dict(code="synthetic", severity="critical", text=(
            "These values come from SYNTHETIC demo data, not real statistics. Do not use them.",
            "این مقادیر از داده‌ی «ساختگی نمایشی» هستند، نه آمار واقعی. از آن‌ها استفاده نکنید.")[L]))
    if any(i["quality"] == "modeled" for i in items):
        out["warnings"].append(dict(code="modeled", text=(
            "Some values are model outputs, not counts of registered cases.",
            "بخشی از مقادیر خروجی مدل‌اند، نه شمار موارد ثبت‌شده.")[L]))
    meas_vals: dict[str, list[float]] = {}
    for i in items:
        if i["year_exact"]:
            meas_vals.setdefault(f"{i['country']['iso3']}:{i['indicator']['measure']}:{i['year']}", []).append(i["value"])
    if any(len(v) > 1 and max(v) > 0 and (max(v) - min(v)) / max(v) > 0.2 for v in meas_vals.values()):
        out["warnings"].append(dict(code="sources_disagree", text=(
            "Sources differ by more than 20% for the same measure and year; compare their methods before choosing.",
            "منابع برای یک شاخص و سال بیش از ۲۰٪ اختلاف دارند؛ پیش از انتخاب، روش آن‌ها را مقایسه کنید.")[L]))
    out["status"] = "answered" if all(i["year_exact"] for i in items) or not p.years else "partial"
    if len({i["requested_year"] for i in items if i["requested_year"]} - {i["year"] for i in items}) and p.years:
        out["status"] = "partial"
    out["message"] = ("Answer from the database, with sources:", "پاسخ از پایگاه داده، همراه با منبع:")[L]
    return out


def _dedupe(ws: list[dict]) -> list[dict]:
    seen, res = set(), []
    for w in ws:
        k = (w["code"], w["text"])
        if k not in seen:
            seen.add(k)
            res.append(w)
    return res


# ------------------------------------------------------------------------------------ optional LLM extraction
EXTRACT_PROMPT = (
    "Extract fields from the user's question about disease statistics. Reply with ONLY compact JSON: "
    '{"disease": string|null, "country": string|null, "year": integer|null, "measure": '
    '"incidence"|"prevalence"|"deaths"|"mortality"|"daly"|"cases"|null}. '
    "Use English names. Do not answer the question.\nQuestion: "
)


async def llm_extract(db: Session, question: str) -> Parsed | None:
    """Last resort when deterministic parsing found nothing. Fields must still resolve to catalogue entries."""
    if not settings.ask_use_llm:
        return None
    try:
        async with httpx.AsyncClient(timeout=min(settings.ollama_timeout_s, 20)) as client:
            r = await client.post(f"{settings.ollama_url}/api/generate", json=dict(
                model=settings.ollama_model, prompt=EXTRACT_PROMPT + question, stream=False, format="json",
                options=dict(temperature=0)))
            r.raise_for_status()
            import json
            data = json.loads(r.json().get("response", "{}"))
    except Exception:  # noqa: BLE001
        return None
    parts = " ".join(str(data.get(k) or "") for k in ("disease", "country"))
    if not parts.strip():
        return None
    p = parse(db, f"{data.get('disease') or ''} {data.get('country') or ''} {data.get('year') or ''} {data.get('measure') or ''}")
    p.lang = "fa" if is_persian(question) else "en"
    return p if p.diseases else None
