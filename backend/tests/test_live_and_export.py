import json
import os
import tempfile
from datetime import date, timedelta

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/live.db")

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import apikeys  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app, limiter  # noqa: E402
from etl import live  # noqa: E402
from etl import surveillance as S  # noqa: E402
from etl.reference import seed_all  # noqa: E402

START = date(2022, 1, 3)


@pytest.fixture(scope="module")
def client():
    init_db()
    rng = np.random.default_rng(5)
    with SessionLocal() as db:
        seed_all(db, with_world_bank=False)
        data = {}
        for iso in ("BRA", "IND", "FRA", "KEN", "JPN"):
            y = rng.poisson(30, 80).astype(float)
            if iso in ("BRA", "IND"):
                y[-6:] = (y[-6:] * np.exp(0.5 * np.arange(1, 7))).round()
            data[iso] = {START + timedelta(days=7 * i): float(v) for i, v in enumerate(y)}
        S.write_weekly(db, "mpox", "TEST", data)
    limiter.hits.clear()
    with TestClient(app) as c:
        yield c


def test_frames_shape(client):
    limiter.hits.clear()
    f = client.get("/api/surveillance/mpox/frames?step=4").json()
    assert len(f["weeks"]) == len(f["codes"]) == len(f["levels"]) and len(f["codes"][0]) == len(f["countries"])
    assert f["weeks"][-1] == max(f["weeks"]) and f["phase_codes"][5] == "epidemic"
    last = dict(zip(f["countries"], f["codes"][-1]))
    assert last["BRA"] in (4, 5) and all(0 <= c < 7 for c in f["codes"][-1])
    assert len(f["numeric"]) == len(f["countries"]) == len(f["names"])


def test_csv_export_and_cite(client):
    limiter.hits.clear()
    r = client.get("/api/export/surveillance/mpox/BRA.csv")
    assert r.status_code == 200 and r.text.startswith("﻿iso3,week_start") and r.text.count("\n") > 70
    assert client.get("/api/export/surveillance/mpox/ZZZ.csv").status_code == 404
    assert client.get("/api/export/indicator/nope.csv").status_code == 404
    c = client.get("/api/cite?kind=surveillance&key=mpox").json()
    assert "Global Health Atlas" in c["apa"] and c["bibtex"].startswith("@misc{")
    assert client.get("/api/cite?kind=zzz&key=x").status_code == 422


def test_live_isolates_failures_and_reports_health(client, tmp_path, monkeypatch):
    feeds = tmp_path / "f.json"
    feeds.write_text(json.dumps([
        {"name": "bad", "kind": "owid-mpox", "source": "/definitely/not/here.csv"},
        {"name": "off", "kind": "cdc-nndss", "enabled": False, "hint": "fill me"},
        {"name": "good", "kind": "csv", "source": str(tmp_path / "g.csv"), "disease": "mpox",
         "date_col": "d", "value_col": "v", "country_col": "c"},
    ]))
    (tmp_path / "g.csv").write_text("d,c,v\n" + "\n".join(
        f"{(START + timedelta(days=7 * i)).isoformat()},FRA,{5 + i}" for i in range(12)) + "\n")
    monkeypatch.setattr(live.time, "sleep", lambda s: None)
    with SessionLocal() as db:
        rep = live.run_live(db, feeds_path=feeds, retries=1)
    assert rep["bad"]["status"] == "failed" and rep["good"]["status"] == "ok" and rep["off"]["status"] == "disabled"
    limiter.hits.clear()
    jobs = {j["job"]: j for j in client.get("/api/health/sources").json()["jobs"]}
    assert jobs["live:bad"]["last_status"] == "failed" and jobs["live:bad"]["last_failure_message"]
