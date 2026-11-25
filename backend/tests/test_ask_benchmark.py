"""Parse-level benchmark for the question parser: ~55 realistic questions in English and Persian.

Each row: question, diseases, countries (in order), years, measure(s) that must be detected, sex.
`None` means "do not check". These pin down parser behaviour so improvements cannot silently regress it.
"""
import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/bench.db")

import pytest  # noqa: E402

from app import ask as A  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from etl.reference import seed_all  # noqa: E402

CASES = [
    # English
    ("breast cancer incidence in the UK in 2020", ["breast-cancer"], ["GBR"], [2020], {"incidence"}, "ALL"),
    ("How many people died of tuberculosis in India in 2019?", ["tuberculosis"], ["IND"], [2019], {"deaths"}, "ALL"),
    ("diabetes prevalence Iran 2021", ["diabetes"], ["IRN"], [2021], {"prevalence"}, "ALL"),
    ("malaria deaths in Nigeria 2018", ["malaria"], ["NGA"], [2018], {"deaths"}, "ALL"),
    ("lung cancer mortality rate in the United States 2017", ["lung-cancer"], ["USA"], [2017], {"mortality"}, "ALL"),
    ("HIV prevalence South Africa 2020", ["hiv-aids"], ["ZAF"], [2020], {"prevalence"}, "ALL"),
    ("TB incidence Pakistan 2015", ["tuberculosis"], ["PAK"], [2015], {"incidence"}, "ALL"),
    ("stroke mortality Japan latest", ["stroke"], ["JPN"], [], {"mortality"}, "ALL"),
    ("cholera cases in Yemen 2017", ["cholera"], ["YEM"], [2017], {"cases"}, "ALL"),
    ("colon cancer in Germany 2020", ["colorectal-cancer"], ["DEU"], [2020], None, "ALL"),
    ("heart attack deaths in France 2019", ["ischaemic-heart-disease"], ["FRA"], [2019], {"deaths"}, "ALL"),
    ("UK vs France breast cancer 2020", ["breast-cancer"], ["GBR", "FRA"], [2020], None, "ALL"),
    ("compare diabetes in Brazil and Mexico 2019", ["diabetes"], ["BRA", "MEX"], [2019], None, "ALL"),
    ("measles in the Democratic Republic of the Congo 2019", ["measles"], ["COD"], [2019], None, "ALL"),
    ("tuberculosis in niger 2020", ["tuberculosis"], ["NER"], [2020], None, "ALL"),
    ("malaria in nigeria 2020", ["malaria"], ["NGA"], [2020], None, "ALL"),
    ("malaria in Guinea-Bissau 2019", ["malaria"], ["GNB"], [2019], None, "ALL"),
    ("dengue in Brazil 2022", ["dengue"], ["BRA"], [2022], None, "ALL"),
    ("dementia in Japan 2019", ["alzheimer-dementia"], ["JPN"], [2019], None, "ALL"),
    ("depression among women in Canada 2019", ["depressive-disorders"], ["CAN"], [2019], None, "F"),
    ("suicide in men in South Korea 2018", ["suicide"], ["KOR"], [2018], None, "M"),
    ("covid deaths in Italy 2020", ["covid-19"], ["ITA"], [2020], {"deaths"}, "ALL"),
    ("ICD C50 in Australia 2018", ["breast-cancer"], ["AUS"], [2018], None, "ALL"),
    ("C34 USA 2019", ["lung-cancer"], ["USA"], [2019], None, "ALL"),
    ("asthma in Turkey 2016", ["asthma"], ["TUR"], [2016], None, "ALL"),
    ("road injuries in Thailand 2019", ["road-injuries"], ["THA"], [2019], None, "ALL"),
    ("cervical cancer incidence in Kenya 2020", ["cervical-cancer"], ["KEN"], [2020], {"incidence"}, "ALL"),
    ("prostate cancer in men in Nigeria 2020", ["prostate-cancer"], ["NGA"], [2020], None, "M"),
    ("hepatitis B in China 2019", ["hepatitis-b"], ["CHN"], [2019], None, "ALL"),
    ("hepatitis C Egypt 2015", ["hepatitis-c"], ["EGY"], [2015], None, "ALL"),
    ("What was breast cancer prevalence in Iran in 2018?", ["breast-cancer"], ["IRN"], [2018], {"prevalence"}, "ALL"),
    ("latest TB deaths in Brazil", ["tuberculosis"], ["BRA"], [], {"deaths"}, "ALL"),
    ("Parkinson's disease in Norway 2019", ["parkinsons-disease"], ["NOR"], [2019], None, "ALL"),
    ("multiple sclerosis in Canada 2019", ["multiple-sclerosis"], ["CAN"], [2019], None, "ALL"),
    ("melanoma in Australia 2020", ["melanoma"], ["AUS"], [2020], None, "ALL"),
    ("thalassaemia in Iran 2019", ["thalassaemia"], ["IRN"], [2019], None, "ALL"),
    ("breast cancer in UK from 2015 to 2019", ["breast-cancer"], ["GBR"], [2015, 2016, 2017, 2018, 2019], None, "ALL"),
    # typos (must still resolve, and be labelled)
    ("pnuemonia deaths in India 2019", ["lower-respiratory-infections"], ["IND"], [2019], {"deaths"}, "ALL"),
    ("dibetes in Iran 2020", ["diabetes"], ["IRN"], [2020], None, "ALL"),
    # Persian
    ("شیوع دیابت در ایران ۲۰۲۰", ["diabetes"], ["IRN"], [2020], {"prevalence"}, "ALL"),
    ("مرگ ناشی از سکته مغزی در ژاپن سال 2019", ["stroke"], ["JPN"], [2019], {"deaths"}, "ALL"),
    ("بروز سل در هند 2019", ["tuberculosis"], ["IND"], [2019], {"incidence"}, "ALL"),
    ("آمار مالاریا در نیجریه", ["malaria"], ["NGA"], [], None, "ALL"),
    ("سرطان ریه در آمریکا 2018", ["lung-cancer"], ["USA"], [2018], None, "ALL"),
    ("سرطان سینه در انگلیس سال دو هزار و بیست", ["breast-cancer"], ["GBR"], [2020], None, "ALL"),
    ("کووید در ایتالیا 2020", ["covid-19"], ["ITA"], [2020], None, "ALL"),
    ("ایدز در آفریقای جنوبی ۲۰۱۹", ["hiv-aids"], ["ZAF"], [2019], None, "ALL"),
    ("سرطان معده در ژاپن و کره جنوبی 2020", ["stomach-cancer"], ["JPN", "KOR"], [2020], None, "ALL"),
    ("فشار خون در آلمان ۲۰۲۱", ["hypertension"], ["DEU"], [2021], None, "ALL"),
    ("افسردگی در زنان ایران", ["depressive-disorders"], ["IRN"], [], None, "F"),
    ("سرخک در پاکستان 2019", ["measles"], ["PAK"], [2019], None, "ALL"),
    ("سل در هند و چین", ["tuberculosis"], ["IND", "CHN"], [], None, "ALL"),
    ("تصادفات در ترکیه 2018", ["road-injuries"], ["TUR"], [2018], None, "ALL"),
    ("آنفلوانزا در فرانسه 2019", ["influenza"], ["FRA"], [2019], None, "ALL"),
    ("مرگ و میر سرطان پستان در ایران 2019", ["breast-cancer"], ["IRN"], [2019], {"mortality"}, "ALL"),
    ("سرطان خون در هند 2019", ["leukaemia"], ["IND"], [2019], None, "ALL"),
]


@pytest.fixture(scope="module")
def db():
    init_db()
    with SessionLocal() as s:
        seed_all(s, with_world_bank=False)
        yield s


@pytest.mark.parametrize("q,diseases,countries,years,measures,sex", CASES, ids=[c[0][:50] for c in CASES])
def test_parse(db, q, diseases, countries, years, measures, sex):
    p = A.parse(db, q)
    assert p.diseases == diseases, (p.diseases, p.fuzzy)
    assert p.countries == countries
    if years or "latest" not in q:
        assert p.years == years
    if "latest" in q:
        assert p.latest
    if measures:
        assert measures <= set(p.measures), p.measures
    assert p.sex == sex


def test_ambiguous_and_out_of_scope(db):
    assert len(A.parse(db, "cancer in UK 2020").diseases) > 5
    assert len(A.parse(db, "سرطان در ایران 2020").diseases) > 5
    assert A.parse(db, "I have a lump, what treatment should I take?").out_of_scope
    assert A.parse(db, "علائم سرطان سینه چیست").out_of_scope
    assert A.parse(db, "Korea breast cancer 2020").countries == []      # "Korea" alone is ambiguous: never guessed
    assert A.parse(db, "Congo malaria 2020").countries == []
