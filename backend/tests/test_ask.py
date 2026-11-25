import os
import tempfile
from datetime import datetime

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/ask.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app import ask as A  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app, limiter  # noqa: E402
from app.models import Disease, Indicator, Observation, Source  # noqa: E402
from etl.reference import seed_all  # noqa: E402


@pytest.fixture(scope="module")
def db():
    init_db()
    with SessionLocal() as s:
        seed_all(s, with_world_bank=False)
        real = Source(code="T_REAL", name="Test Registry", url="https://example.org", license="CC BY 4.0",
                      citation="Test Registry (2024)", is_synthetic=False)
        fake = Source(code="T_DEMO", name="DEMO (synthetic)", is_synthetic=True)
        s.add_all([real, fake])
        s.flush()
        bc = s.scalar(select(Disease).where(Disease.slug == "breast-cancer"))
        inc = Indicator(code="t-bc-inc", disease_id=bc.id, source_id=real.id, measure="incidence", unit="per_100k",
                        name_en="Breast cancer incidence", name_fa="بروز سرطان پستان", higher_is_worse=True)
        mor = Indicator(code="t-bc-mort", disease_id=bc.id, source_id=real.id, measure="mortality", unit="per_100k",
                        name_en="Breast cancer mortality", name_fa="مرگ سرطان پستان", higher_is_worse=True)
        s.add_all([inc, mor])
        s.flush()
        now = datetime(2024, 1, 1)
        for y, v in [(2019, 90.1), (2020, 88.4), (2022, 91.0)]:
            s.add(Observation(indicator_id=inc.id, country_iso3="GBR", year=y, sex="ALL", age_group="ALL", value=v,
                              low=v - 3, high=v + 3, data_quality="estimated", retrieved_at=now))
        s.add(Observation(indicator_id=mor.id, country_iso3="GBR", year=2020, sex="ALL", age_group="ALL", value=19.2,
                          data_quality="modeled", retrieved_at=now))
        tb = s.scalar(select(Disease).where(Disease.slug == "tuberculosis"))
        d = Indicator(code="t-tb-demo", disease_id=tb.id, source_id=fake.id, measure="incidence", unit="per_100k",
                      name_en="TB demo", higher_is_worse=True)
        s.add(d)
        s.flush()
        s.add(Observation(indicator_id=d.id, country_iso3="IRN", year=2020, sex="ALL", age_group="ALL", value=12.0,
                          data_quality="estimated", retrieved_at=now))
        s.commit()
        yield s


def test_the_users_own_question_persian(db):
    r = A.answer(db, "آمار سرطان سینه در انگلیس سال 2020 چقد بوده")
    assert r["status"] == "answered" and r["interpretation"]["country"]["iso3"] == "GBR"
    assert r["interpretation"]["disease"][0]["slug"] == "breast-cancer" and r["interpretation"]["years"] == [2020]
    vals = {i["indicator"]["code"]: i for i in r["items"]}
    assert vals["t-bc-inc"]["value"] == 88.4 and vals["t-bc-mort"]["value"] == 19.2
    assert vals["t-bc-inc"]["indicator"]["source"]["license"] == "CC BY 4.0" and vals["t-bc-inc"]["links"]["csv"]
    assert "88.4" in vals["t-bc-inc"]["text"] and "سال 2020" in vals["t-bc-inc"]["text"]
    assert any(w["code"] == "subnational" and "انگلستان" in w["text"] and "کل بریتانیا" in w["text"] for w in r["warnings"])
    assert any(w["code"] == "modeled" for w in r["warnings"])


def test_english_and_measure_filter(db):
    r = A.answer(db, "What was the breast cancer incidence in the UK in 2020?")
    assert r["status"] == "answered" and [i["indicator"]["measure"] for i in r["items"]] == ["incidence"]
    assert not any(w["code"] == "subnational" for w in r["warnings"])


def test_missing_year_is_labelled_not_hidden(db):
    r = A.answer(db, "breast cancer incidence United Kingdom 2021")
    assert r["status"] == "partial"
    i = r["items"][0]
    assert i["requested_year"] == 2021 and i["year"] in (2020, 2022) and i["year_exact"] is False
    assert "no value for 2021" in i["text"]


def test_year_range_and_latest(db):
    r = A.answer(db, "breast cancer incidence in UK from 2019 to 2022")
    assert [i["year"] for i in r["items"]] == [2019, 2020, 2022]  # 2021 does not exist: not invented
    r2 = A.answer(db, "latest breast cancer incidence in Britain")
    assert r2["items"][0]["year"] == 2022 and not any(w["code"] == "year_defaulted" for w in r2["warnings"])


def test_no_data_says_so(db):
    r = A.answer(db, "breast cancer in France 2020")
    assert r["status"] == "no_data" and r["items"] == [] and "Nothing was estimated" in r["message"]


def test_ambiguity_asks_instead_of_guessing(db):
    r = A.answer(db, "cancer in UK 2020")
    assert r["status"] == "needs_clarification" and len(r["candidates"]["diseases"]) > 5
    assert A.answer(db, "breast cancer 2020")["status"] == "needs_clarification"      # no country
    assert A.answer(db, "UK 2020 statistics")["status"] == "needs_clarification"      # no disease


def test_typos_are_labelled(db):
    r = A.answer(db, "breast cancr incidence in Britian 2020")
    assert r["status"] in ("answered", "partial")
    assert {f["kind"] for f in r["interpretation"]["typo_corrections"]} >= {"disease"}
    assert any(w["code"] == "typo" for w in r["warnings"])


def test_synthetic_is_flagged_critical(db):
    r = A.answer(db, "سل در ایران 2020")
    assert r["status"] == "answered" and r["warnings"][0]["code"] == "synthetic" and r["warnings"][0]["severity"] == "critical"


def test_out_of_scope_and_jalali(db):
    r = A.answer(db, "I have a lump, what is the treatment for breast cancer?")
    assert r["status"] == "out_of_scope" and r["items"] == []
    r = A.answer(db, "آمار سرطان سینه در ایران سال 1399")
    assert r["status"] == "needs_clarification" and "میلادی" in r["message"]


def test_substring_traps(db):
    # "niger" must not match inside "nigeria"; "and" must not become Andorra
    p = A.parse(db, "malaria in nigeria and 2020")
    assert p.country == "NGA"
    p = A.parse(db, "tuberculosis in niger 2020")
    assert p.country == "NER"


def test_endpoint(db):
    limiter.hits.clear()
    with TestClient(app) as c:
        r = c.get("/api/ask", params={"q": "سرطان سینه انگلیس 2020"}).json()
        assert r["status"] == "answered" and r["items"]
        assert c.get("/api/ask", params={"q": ""}).status_code == 422
        assert c.get("/api/ask", params={"q": "x" * 400}).status_code == 422


def test_spoken_persian_years(db):
    assert A.fa_years_to_digits("سال دو هزار و بیست") == "سال 2020"
    assert A.fa_years_to_digits("در سال هزار و نهصد و نود و پنج") == "در سال 1995"
    assert A.fa_years_to_digits("سه نفر و پنج مورد") == "سه نفر و پنج مورد"     # not a year: untouched
    r = A.answer(db, "آمار سرطان سینه در انگلیس سال دو هزار و بیست چقدر بوده")
    assert r["status"] == "answered" and r["interpretation"]["years"] == [2020]
