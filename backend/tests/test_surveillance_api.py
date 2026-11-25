import os
import tempfile
from datetime import date, timedelta

import numpy as np
import pytest

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/surv.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from etl import surveillance as S  # noqa: E402
from etl.reference import seed_all  # noqa: E402

START = date(2022, 1, 3)  # a Monday
N = 90


def _series(outbreak=False, seed=0):
    rng = np.random.default_rng(seed)
    y = rng.poisson(40, N).astype(float)
    if outbreak:
        y[-6:] = (y[-6:] * np.exp(0.5 * np.arange(1, 7))).round()
    return {START + timedelta(days=7 * i): float(v) for i, v in enumerate(y)}


@pytest.fixture(scope="module")
def client():
    init_db()
    with SessionLocal() as db:
        seed_all(db, with_world_bank=False)
        data = {"BRA": _series(True, 1), "IND": _series(True, 2), "FRA": _series(False, 3),
                "KEN": _series(False, 4)}
        S.write_weekly(db, "mpox", "TEST", data)
    with TestClient(app) as c:
        yield c


def test_meta_and_diseases(client):
    m = client.get("/api/surveillance/meta").json()
    assert "pandemic_pattern" in m["patterns"] and m["pattern_note"]
    ds = client.get("/api/surveillance/diseases").json()
    m = next(d for d in ds if d["slug"] == "mpox")
    assert m["n_countries"] >= 4


def test_status_flags_outbreak_countries(client):
    r = client.get("/api/surveillance/mpox/status").json()
    ph = {x["iso3"]: x["phase"] for x in r["rows"]}
    assert ph["BRA"] in ("epidemic", "watch") and ph["FRA"] not in ("epidemic",)
    assert r["pattern"]["level"] != "none"
    assert r["weeks_behind_today"] > 0  # fixture data is old: UI must warn


def test_as_of_time_machine_uses_only_past_data(client):
    early = (START + timedelta(days=7 * 40)).isoformat()
    r = client.get(f"/api/surveillance/mpox/status?as_of={early}").json()
    assert r["as_of"] == early
    assert all(x["phase"] != "epidemic" for x in r["rows"])


def test_series_detail_and_errors(client):
    r = client.get("/api/surveillance/mpox/series/bra?lang=fa").json()
    assert r["assessment"]["phase"] in ("epidemic", "watch") and r["points"] and r["findings"]
    assert client.get("/api/surveillance/mpox/series/ZZZ").status_code == 404
    assert client.get("/api/surveillance/nope/status").status_code == 404
    assert client.get("/api/surveillance/mpox/status?as_of=garbage").status_code == 422


def test_board_and_replay(client):
    b = client.get("/api/surveillance/board").json()
    assert b and b[0]["pattern"]["label"]
    rp = client.get("/api/surveillance/mpox/replay").json()
    assert rp["timeline"]


# ---- connector parsers (offline fixtures; live endpoints are NOT exercised) ----

def test_mmwr_week_start_is_sunday():
    assert S.mmwr_week_start(2024, 1) == date(2023, 12, 31)
    assert S.mmwr_week_start(2024, 10).weekday() == 6


def test_to_weeks_drops_partial_weeks():
    daily = {date(2024, 1, 1) + timedelta(days=i): 1.0 for i in range(17)}  # 2 full weeks + 3 days
    w = S.to_weeks(daily)
    assert list(w.values()) == [7.0, 7.0]


def test_parse_owid_and_csv():
    owid = "date,iso_code,new_cases\n2024-01-01,BRA,5\n2024-01-08,BRA,7\n2024-01-15,BRA,9\n2024-01-08,OWID_WRL,99\n"
    w = S.parse_owid_mpox(owid, {"BRA"})
    assert set(w) == {"BRA"} and len(w["BRA"]) == 2  # last (incomplete) week dropped
    assert w["BRA"][date(2024, 1, 8)] == 7.0


def test_parse_nndss_rows():
    rows = [dict(states="US RESIDENTS", year="2024", week="3", label="Measles", m1="4"),
            dict(states="US RESIDENTS", year="2024", week="4", label="Measles", m1="6"),
            dict(states="OHIO", year="2024", week="4", label="Measles", m1="1")]
    w = S.parse_nndss_rows(rows, "Measles", ["US RESIDENTS"])
    assert sorted(w["USA"].values()) == [4.0, 6.0]
    with pytest.raises(ValueError):
        S.parse_nndss_rows([dict(a=1)], "Measles", ["X"])


def test_parse_delphi_rejects_error_payload():
    with pytest.raises(ValueError):
        S.parse_delphi_fluview(dict(result=-2, message="no results"))
