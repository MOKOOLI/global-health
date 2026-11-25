import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/keys.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import apikeys  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app, limiter  # noqa: E402


def test_limiter_window():
    L = apikeys.Limiter(window=60)
    assert [L.check("a", 3, now=t)[0] for t in (0, 1, 2, 3)] == [True, True, True, False]
    ok, rem, retry = L.check("a", 3, now=4)
    assert not ok and 50 <= retry <= 61
    assert L.check("a", 3, now=61)[0] is True      # first hit expired
    assert L.check("b", 3, now=4)[0] is True       # separate identity


@pytest.fixture()
def client():
    init_db()
    limiter.hits.clear()
    apikeys.clear_cache()
    with TestClient(app) as c:
        yield c


def test_anonymous_gets_limit_headers_and_429(client):
    r = client.get("/api/licenses")
    assert r.status_code == 200 and r.headers["x-ratelimit-limit"] == str(apikeys.TIERS["anonymous"])
    for _ in range(apikeys.TIERS["anonymous"]):
        last = client.get("/api/licenses")
    assert last.status_code == 429 and "retry-after" in last.headers


def test_key_lifecycle(client):
    with SessionLocal() as db:
        key = apikeys.create_key(db, "me@example.org", "academic")
    r = client.get("/api/licenses", headers={"X-API-Key": key})
    assert r.status_code == 200 and r.headers["x-ratelimit-limit"] == str(apikeys.TIERS["academic"])
    assert client.get("/api/licenses", headers={"X-API-Key": "gha_bogus"}).status_code == 401
    with SessionLocal() as db:
        assert apikeys.revoke_key(db, key[:8]) == 1
    apikeys.clear_cache()
    assert client.get("/api/licenses", headers={"X-API-Key": key}).status_code == 401


def test_key_stored_hashed_and_bad_tier_rejected():
    with SessionLocal() as db:
        with pytest.raises(ValueError):
            apikeys.create_key(db, "x", "anonymous")
        key = apikeys.create_key(db, "h@example.org")
        from sqlalchemy import select
        from app.models import ApiKey
        row = db.scalar(select(ApiKey).where(ApiKey.owner == "h@example.org"))
        assert row.key_hash != key and key not in row.key_hash


def test_licenses_register_is_honest(client):
    d = client.get("/api/licenses").json()
    gbd = next(s for s in d["sources"] if s["code"] == "IHME_GBD")
    assert gbd["commercial"] == "no_without_permission"
    assert all(s["verified"] is False for s in d["sources"])


def test_database_url_driver_normalised():
    from app.config import Settings

    assert Settings(database_url="postgres://u:p@h/db").database_url == "postgresql+psycopg://u:p@h/db"
    assert Settings(database_url="postgresql://u:p@h/db?sslmode=require").database_url.startswith("postgresql+psycopg://")
    assert Settings(database_url="sqlite:///x.db").database_url == "sqlite:///x.db"
