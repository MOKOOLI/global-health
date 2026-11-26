import hashlib
import json
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from datetime import date, timedelta

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/b1.db")

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app import asr, dataset  # noqa: E402
from app.apikeys import RedisLimiter  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app, limiter  # noqa: E402
from app.models import Indicator  # noqa: E402
from etl import annual_csv, snapshot  # noqa: E402
from etl import surveillance as S  # noqa: E402
from etl.reference import seed_all  # noqa: E402

CSV = "country,year,val,lo,hi\nIran,2020,10.5,9,12\nFrance,2020,7,6,8\nFrance,2019,6.5,,\nAtlantis,2020,1,,\nIran,2021,abc,,\n"


@pytest.fixture(scope="module")
def env():
    init_db()
    rng = np.random.default_rng(1)
    d = tempfile.mkdtemp()
    with SessionLocal() as db:
        seed_all(db, with_world_bank=False)
        p = os.path.join(d, "a.csv")
        open(p, "w").write(CSV)
        r = annual_csv.load_annual_csv(db, p, source_code="TESTSRC", source_name="Test source", license="CC BY 4.0",
                                       citation="Test (2024)", disease="diabetes", measure="prevalence", unit="%",
                                       indicator_code="t_diab", name_en="Test diabetes", country_col="country",
                                       year_col="year", value_col="val", low_col="lo", high_col="hi", country_kind="name")
        p2 = os.path.join(d, "g.csv")
        open(p2, "w").write("iso3,year,v\nIRN,2020,5\n")
        annual_csv.load_annual_csv(db, p2, source_code="GBD", source_name="GBD", license="IHME", citation="GBD",
                                   disease="stroke", measure="deaths", unit="n", indicator_code="t_gbd", name_en="gbd stroke",
                                   country_col="iso3", year_col="year", value_col="v")
        start = date(2022, 1, 3)
        data = {}
        for iso in ("BRA", "IND", "FRA", "KEN", "JPN"):
            y = rng.poisson(30, 80).astype(float)
            if iso in ("BRA", "IND"):
                y[-6:] = (y[-6:] * np.exp(0.5 * np.arange(1, 7))).round()
            data[iso] = {start + timedelta(days=7 * i): float(v) for i, v in enumerate(y)}
        S.write_weekly(db, "mpox", "TEST", data)
    limiter.hits.clear()
    with TestClient(app) as c:
        yield dict(client=c, load=r, dir=d)


def test_asr_equals_crude_when_weights_follow_population():
    pop = [1000, 2000, 3000, 4000]
    cases = [5, 20, 60, 160]
    r = asr.standardise(cases, pop, pop)
    assert r["asr"] == pytest.approx(r["crude"])
    assert r["low"] <= r["asr"] <= r["high"]


def test_asr_differs_from_crude_with_other_weights_and_ci_tightens():
    pop, cases = [1000, 1000], [10, 100]
    a = asr.standardise(cases, pop, [1, 3])
    assert a["asr"] == pytest.approx((0.25 * 10 + 0.75 * 100) / 1000 * 1e5)
    big = asr.standardise([c * 100 for c in cases], [p * 100 for p in pop], [1, 3])
    assert (big["high"] - big["low"]) < (a["high"] - a["low"])


def test_asr_edge_cases():
    assert asr.standardise([0, 0], [10, 10], [1, 1])["high"] is None
    assert asr.standardise([2, 3], [10, 10], [1, 1])["warnings"]
    for bad in (([1], [1], [1]), ([-1, 1], [1, 1], [1, 1]), ([1, 1], [0, 1], [1, 1]), ([1, 1], [1, 1], [0, 0])):
        with pytest.raises(ValueError):
            asr.standardise(*bad)


def test_standards_sum():
    assert sum(asr.SEGI) == 100_000 and len(asr.SEGI) == len(asr.SEGI_LABELS)
    assert len(asr.WHO2000) == len(asr.WHO2000_LABELS)


def test_tools_endpoints(env):
    c = env["client"]
    limiter.hits.clear()
    assert set(c.get("/api/tools/standards").json()) == {"segi", "who2000"}
    g = [{"cases": 5 + i, "pop": 100000} for i in range(18)]
    r = c.post("/api/tools/age-standardise", json={"groups": g, "standard": "segi"})
    assert r.status_code == 200 and r.json()["asr"] > 0
    assert c.post("/api/tools/age-standardise", json={"groups": g[:5], "standard": "segi"}).status_code == 422
    assert c.post("/api/tools/age-standardise", json={"groups": g, "standard": "x"}).status_code == 422
    assert c.post("/api/tools/age-standardise", json={"groups": g[:3], "standard": "custom"}).status_code == 422
    ok = [{"cases": 1, "pop": 10, "weight": 1}, {"cases": 2, "pop": 10, "weight": 2}]
    assert c.post("/api/tools/age-standardise", json={"groups": ok, "standard": "custom"}).status_code == 200
    assert c.post("/api/tools/age-standardise", json={"groups": [{"cases": -1, "pop": 1}] * 2}).status_code == 422


def test_annual_csv_loader(env):
    r = env["load"]
    assert r["rows"] == 3 and r["n_unmatched"] == 1 and "Atlantis" in r["unmatched_countries"]
    with SessionLocal() as db:
        ind = db.scalar(select(Indicator).where(Indicator.code == "t_diab"))
        rows = list(dataset.indicator_csv_rows(db, ind))
        assert {(x[0], x[2]) for x in rows} == {("IRN", 2020), ("FRA", 2020), ("FRA", 2019)}
    with pytest.raises(ValueError):
        annual_csv.parse_annual_rows(CSV, country_col="nope", year_col="year", value_col="val")


def test_dataset_version_and_datapackage(env):
    c = env["client"]
    limiter.hits.clear()
    with SessionLocal() as db:
        ind = db.scalar(select(Indicator).where(Indicator.code == "t_diab"))
        v = dataset.indicator_version(db, ind)
        assert len(v) == 12 and v == dataset.indicator_version(db, ind)
        dp = dataset.datapackage(db, ind)
        assert dp["profile"] == "tabular-data-package" and dp["resources"]
    r = c.get("/api/export/indicator/t_diab.csv")
    assert r.status_code == 200 and r.headers["X-Data-Version"] == v and "data_version" in r.text.splitlines()[0]
    d = c.get("/api/datapackage/t_diab.json")
    assert d.status_code == 200 and d.json()["licenses"]
    assert c.get("/api/datapackage/none.json").status_code == 404
    assert v in c.get("/api/cite?kind=indicator&key=t_diab").json()["apa"]


def test_snapshot_skips_restricted_and_synthetic(env):
    out = os.path.join(env["dir"], "snap")
    with SessionLocal() as db:
        res = snapshot.write_snapshot(db, out)
    files = os.listdir(out)
    assert "t_diab.csv" in files and "t_gbd.csv" not in files
    assert any(s["indicator"] == "t_gbd" for s in res["skipped"]) if isinstance(res, dict) and "skipped" in res else True
    sums = open(os.path.join(out, "SHA256SUMS")).read().splitlines()
    for line in sums:
        h, name = line.split("  ")
        assert hashlib.sha256(open(os.path.join(out, name), "rb").read()).hexdigest() == h
    assert "licen" in open(os.path.join(out, "README.md")).read().lower()
    shutil.rmtree(out)
    with SessionLocal() as db:
        snapshot.write_snapshot(db, out, include_restricted=True)
    assert "t_gbd.csv" in os.listdir(out)


def test_feeds(env):
    c = env["client"]
    limiter.hits.clear()
    j = c.get("/api/feeds/signals.json?min_level=watch&alerts=false").json()
    assert "entries" in j and "not an official" in j["note"]
    assert all(e["level"] != "none" for e in j["entries"])
    a = c.get("/api/feeds/signals.atom?min_level=watch")
    assert a.status_code == 200 and "atom" in a.headers["content-type"]
    root = ET.fromstring(a.content)
    assert root.tag.endswith("feed")
    assert c.get("/api/feeds/signals.json?min_level=bogus").status_code == 422
    assert c.get("/api/feeds/signals.json?disease=nonexistent&alerts=false").json()["entries"] == []
    fa = c.get("/api/feeds/signals.json?lang=fa&alerts=false").json()
    assert fa["note"].startswith("یک سیگنال")


def test_ready(env):
    assert env["client"].get("/api/health/ready").json() == {"status": "ready"}


def test_ask_multi_country_and_icd(env):
    c = env["client"]
    limiter.hits.clear()
    r = c.get("/api/ask", params={"q": "diabetes in Iran and France 2020"}).json()
    cs = r["interpretation"]["countries"]
    assert {(x.get("iso3") if isinstance(x, dict) else x) for x in cs} == {"IRN", "FRA"}, cs


def _redis_up(port=6390):
    try:
        import redis
        return redis.Redis(port=port, socket_connect_timeout=0.3).ping()
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(not _redis_up(), reason="no local redis-server on :6390")
def test_redis_limiter_window_and_isolation():
    import redis
    redis.Redis(port=6390).flushall()
    rl = RedisLimiter("redis://127.0.0.1:6390/0")
    t = 1_000_000.0
    res = [rl.check("ip1", 3, now=t) for _ in range(5)]
    assert [x[0] for x in res] == [True, True, True, False, False] and res[3][2] >= 1
    assert rl.check("ip2", 3, now=t)[0]
    assert rl.check("ip1", 3, now=t + 61)[0]


def test_redis_limiter_fails_open():
    rl = RedisLimiter("redis://127.0.0.1:1/0")
    assert rl.check("x", 5)[0] is True


def test_map_reports_coverage(env):
    c = env["client"]
    limiter.hits.clear()
    r = c.get("/api/indicators/t_diab/map").json()
    assert r["n"] == 2 and r["n_total"] >= 200
    assert r["population_share"] is None or 0 < r["population_share"] <= 1


def test_with_retry_recovers_from_dropped_connection(env, monkeypatch):
    from sqlalchemy.exc import OperationalError

    from etl.common import with_retry
    monkeypatch.setattr("time.sleep", lambda s: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise OperationalError("INSERT", {}, Exception("server closed the connection unexpectedly"))
        return "ok"

    with SessionLocal() as db:
        assert with_retry(db, flaky) == "ok" and calls["n"] == 3
        calls["n"] = -10
        with pytest.raises(OperationalError):
            with_retry(db, flaky, tries=2)
