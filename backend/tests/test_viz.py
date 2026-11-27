import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/viz.db")

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Country, Indicator, Observation, Source  # noqa: E402
from etl.reference import seed_all  # noqa: E402


@pytest.fixture(scope="module")
def client():
    init_db()
    rng = np.random.default_rng(7)
    with SessionLocal() as db:
        seed_all(db, with_world_bank=False)
        src = Source(code="VIZ", name="Viz test", license="CC BY 4.0", is_synthetic=True)
        db.add(src)
        db.flush()
        isos = [c for c in db.scalars(select(Country.iso3).order_by(Country.iso3))][:80]
        inds = []
        for n in range(6):
            i = Indicator(code=f"viz_{n}", source_id=src.id, measure="incidence", unit="per_100k",
                          name_en=f"Viz indicator {n}", higher_is_worse=True)
            db.add(i)
            inds.append(i)
        db.flush()
        for idx, iso in enumerate(isos):
            grp = idx % 2                       # two planted groups: low vs high burden on every indicator
            for i in inds:
                for yr in (2018, 2019, 2020):
                    base = (10 if grp == 0 else 100) + rng.normal(0, 2) + (yr - 2018)
                    db.add(Observation(country_iso3=iso, indicator_id=i.id, year=yr, value=float(base)))
        # a sparse indicator that must be excluded from options
        sp = Indicator(code="viz_sparse", source_id=src.id, measure="incidence", unit="per_100k", name_en="Sparse")
        db.add(sp)
        db.flush()
        for iso in isos[:5]:
            db.add(Observation(country_iso3=iso, indicator_id=sp.id, year=2020, value=1.0))
        db.commit()
    return TestClient(app)


def test_options_excludes_sparse_and_gives_default(client):
    r = client.get("/api/viz/options").json()
    codes = {i["code"] for i in r["indicators"]}
    assert "viz_0" in codes and "viz_sparse" not in codes
    assert r["default"]["x"] != r["default"]["y"]


def test_bubbles_frames_and_ranges(client):
    r = client.get("/api/viz/bubbles", params={"x": "viz_0", "y": "viz_1"}).json()
    assert r["years"] == [2018, 2019, 2020]
    assert len(r["countries"]) == 80
    c = r["countries"][0]
    assert [p[0] for p in c["points"]] == [2018, 2019, 2020]
    assert r["x_range"][0] <= min(p[1] for c in r["countries"] for p in c["points"])


def test_bubbles_errors(client):
    assert client.get("/api/viz/bubbles", params={"x": "viz_0", "y": "viz_0"}).status_code == 422
    assert client.get("/api/viz/bubbles", params={"x": "nope", "y": "viz_0"}).status_code == 404
    assert client.get("/api/viz/bubbles", params={"x": "viz_0", "y": "viz_sparse"}).status_code == 404


def test_similarity_recovers_planted_groups(client):
    r = client.get("/api/viz/similarity", params={"k": 4}).json()
    assert len(r["nodes"]) == 80 and r["edges"]
    isos = sorted(n["iso3"] for n in r["nodes"])
    group = {iso: i % 2 for i, iso in enumerate(isos)}
    # the planted high/low groups must never share a cluster
    mixed = {}
    for n in r["nodes"]:
        mixed.setdefault(n["cluster"], set()).add(group[n["iso3"]])
    assert all(len(g) == 1 for g in mixed.values())
    assert len(mixed) >= 2
    assert "not disease transmission" in r["method"]
    top = r["clusters"][0]["features"][0]
    assert top["direction"] in ("high", "low")


def test_similarity_needs_enough_indicators(client):
    # other test modules share this database, so assert the rule instead of a fixed count
    r = client.get("/api/viz/similarity", params={"min_shared": 12})
    if r.status_code == 200:
        assert len(r.json()["indicators"]) >= 12
    else:
        assert r.status_code == 404
