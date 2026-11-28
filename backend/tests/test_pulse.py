import os
import tempfile
from datetime import datetime, timedelta

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/pulse.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Country, Disease, Indicator, Observation, OutbreakAlert, Source  # noqa: E402
from etl.reference import seed_all  # noqa: E402


@pytest.fixture(scope="module")
def client():
    init_db()
    with SessionLocal() as db:
        seed_all(db, with_world_bank=False)
        src = Source(code="PULSE", name="Pulse test", license="CC BY 4.0", is_synthetic=True)
        db.add(src)
        db.flush()
        dz = db.scalar(select(Disease).order_by(Disease.id))
        isos = list(db.scalars(select(Country.iso3).order_by(Country.iso3)))[:10]
        rate = Indicator(code="p_rate", source_id=src.id, disease_id=dz.id, measure="mortality", unit="per_100k",
                         name_en="Pulse rate", higher_is_worse=True)
        cnt = Indicator(code="p_cnt", source_id=src.id, disease_id=dz.id, measure="incidence", unit="count",
                        name_en="Pulse cases", higher_is_worse=True)
        good = Indicator(code="p_good", source_id=src.id, disease_id=None, measure="coverage", unit="percent",
                         name_en="Pulse coverage", higher_is_worse=False)
        db.add_all([rate, cnt, good])
        db.flush()
        for i, iso in enumerate(isos):
            for yr, v in ((2018, 50), (2020, 10 + i)):          # latest year differs from an older one
                db.add(Observation(country_iso3=iso, indicator_id=rate.id, year=yr, value=float(v)))
            db.add(Observation(country_iso3=iso, indicator_id=cnt.id, year=2020, value=100.0))
            db.add(Observation(country_iso3=iso, indicator_id=good.id, year=2020, value=float(50 + i)))
        db.add(OutbreakAlert(title="Test alert", url="http://x/a1", source="WHO-DON",
                             published_at=datetime.utcnow() - timedelta(days=2), country_iso3=isos[0],
                             disease_id=dz.id))
        db.commit()
    return TestClient(app)


def test_burden_uses_latest_year_and_right_summaries(client):
    r = client.get("/api/pulse").json()
    b = {x["code"]: x for x in r["burden"]}
    assert b["p_rate"]["year"] == 2020 and b["p_rate"]["n"] == 10          # not the older 2018 values
    assert b["p_rate"]["median"] == 14.5                                     # median of 10..19
    assert b["p_rate"]["extreme"]["value"] == 19                             # higher is worse -> max
    assert b["p_good"]["extreme"]["value"] == 50                             # lower is worse -> min
    assert b["p_cnt"]["total"] == 1000 and b["p_rate"]["total"] is None      # sums only for counts
    assert b["p_rate"]["freshness"] in ("fresh", "aging", "old")


def test_freshness_classes_follow_each_clock(client):
    from app.routes_pulse import _age
    assert _age("weekly", 10) == "fresh" and _age("weekly", 30) == "aging" and _age("weekly", 90) == "old"
    assert _age("alert", 3) == "fresh" and _age("alert", 40) == "old"
    assert _age("annual", 1) == "fresh" and _age("annual", 3) == "aging" and _age("annual", 6) == "old"


def test_alerts_and_sources_present(client):
    r = client.get("/api/pulse").json()
    a = next(x for x in r["alerts"] if x["title"] == "Test alert")
    assert a["age_days"] == 2 and a["freshness"] == "fresh" and a["country"]
    assert isinstance(r["sources"], list) and r["thresholds"]["annual_years"] == [2, 4]


def test_country_pulse_rank(client):
    with SessionLocal() as db:
        iso = list(db.scalars(select(Country.iso3).order_by(Country.iso3)))[:10][9]   # highest rate (19)
    r = client.get(f"/api/pulse/country/{iso}").json()
    it = {x["code"]: x for x in r["items"]}
    assert it["p_rate"]["rank_worst"] == 1 and it["p_rate"]["of"] == 10
    assert it["p_good"]["rank_worst"] == 10                                   # best coverage = least bad = last
    assert client.get("/api/pulse/country/ZZZ").status_code == 404


def test_country_pulse_empty_country(client):
    with SessionLocal() as db:
        iso = list(db.scalars(select(Country.iso3).order_by(Country.iso3)))[-1]
    r = client.get(f"/api/pulse/country/{iso}").json()
    assert r["items"] == [] or all(i["of"] >= 1 for i in r["items"])
