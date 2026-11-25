import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from etl.demo import load_demo  # noqa: E402
from etl.reference import seed_all  # noqa: E402


@pytest.fixture(scope="module")
def client():
    init_db()
    with SessionLocal() as db:
        seed_all(db, with_world_bank=False)
        load_demo(db, max_countries=60)
    with TestClient(app) as c:
        yield c


def test_meta_flags_synthetic(client):
    m = client.get("/api/meta").json()
    assert m["has_synthetic"] is True
    assert m["counts"]["diseases"] >= 60
    assert "incidence" in m["measures"]


def test_search_persian_and_icd(client):
    assert any(d["slug"] == "tuberculosis" for d in client.get("/api/search", params={"q": "سل"}).json()["diseases"])
    assert any(d["slug"] == "tuberculosis" for d in client.get("/api/search", params={"q": "A15"}).json()["diseases"])


def test_disease_detail_default_indicator(client):
    d = client.get("/api/diseases/tuberculosis").json()
    assert d["default_indicator"] == "demo-tuberculosis-incidence"
    assert d["indicators"][0]["source"]["is_synthetic"] is True


def test_map_trend_ranking(client):
    code = "demo-tuberculosis-incidence"
    m = client.get(f"/api/indicators/{code}/map").json()
    assert m["year"] == 2022 and m["n"] == 60 and len(m["breaks"]) == 6
    iso = m["data"][0]["iso3"]
    t = client.get(f"/api/indicators/{code}/trend", params={"countries": f"{iso},ZZZ", "forecast": True}).json()
    assert len(t["series"]) == 1 and len(t["series"][0]["points"]) == 23
    assert len(t["series"][0]["forecast"]["points"]) == 5
    r = client.get(f"/api/indicators/{code}/ranking", params={"limit": 5}).json()
    assert [x["rank"] for x in r["rows"]] == [1, 2, 3, 4, 5]
    assert r["rows"][0]["value"] >= r["rows"][1]["value"]


def test_unknown_indicator_404(client):
    assert client.get("/api/indicators/nope/map").status_code == 404


def test_country_profile_sorted(client):
    p = client.get("/api/countries/DEU/profile", params={"lang": "fa"}).json()
    ratios = [i.get("ratio_to_median") or 0 for i in p["items"]]
    assert ratios == sorted(ratios, reverse=True) and p["items"]


def test_insights_templates_and_caveats(client):
    i = client.get("/api/insights", params={"indicator": "demo-malaria-incidence", "country": "DEU", "lang": "fa"}).json()
    keys = [f["key"] for f in i["findings"]]
    assert "latest" in keys and "caveat_quality" in keys and i["synthetic"] is True
    assert all(f["text_fa"] and f["text_en"] for f in i["findings"])


def test_insights_narrate_falls_back_without_ollama(client):
    i = client.get("/api/insights", params={"indicator": "demo-malaria-incidence", "country": "DEU", "narrate": True}).json()
    assert i["narrative"]["ai_generated"] is False and i["narrative"]["text"]
