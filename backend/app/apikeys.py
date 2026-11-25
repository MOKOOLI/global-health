"""API keys and rate limiting.

* Anonymous callers are limited per IP; callers with a valid `X-API-Key` get their tier's limit.
* The limiter is an in-process sliding window: correct for one worker. With several workers or
  replicas each keeps its own counters, so use a shared store (e.g. Redis) before scaling out.
* Keys are created by an operator (`python -m etl.run apikey create ...`); there is deliberately no
  public self-signup endpoint to abuse.
"""
from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ApiKey

TIERS = {  # requests per minute
    "anonymous": 120,
    "free": 240,
    "academic": 600,
    "pro": 2400,
}
PREFIX = "gha_"


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def create_key(db: Session, owner: str, tier: str = "free") -> str:
    if tier not in TIERS or tier == "anonymous":
        raise ValueError(f"tier must be one of {[t for t in TIERS if t != 'anonymous']}")
    key = PREFIX + secrets.token_urlsafe(32)
    db.add(ApiKey(key_hash=hash_key(key), prefix=key[:8], owner=owner, tier=tier))
    db.commit()
    return key


def revoke_key(db: Session, prefix: str) -> int:
    rows = list(db.scalars(select(ApiKey).where(ApiKey.prefix == prefix, ApiKey.revoked.is_(False))))
    for r in rows:
        r.revoked = True
    db.commit()
    return len(rows)


_CACHE: dict[str, tuple[float, str | None]] = {}  # hash -> (expires, tier or None if invalid)
CACHE_TTL = 60.0


def lookup_tier(db: Session, key: str) -> str | None:
    h = hash_key(key)
    hit = _CACHE.get(h)
    now = time.monotonic()
    if hit and hit[0] > now:
        return hit[1]
    row = db.scalar(select(ApiKey).where(ApiKey.key_hash == h))
    tier = row.tier if row and not row.revoked else None
    if row and tier:
        row.last_used_at = datetime.utcnow()
        db.commit()
    _CACHE[h] = (now + CACHE_TTL, tier)
    return tier


def clear_cache() -> None:
    _CACHE.clear()


class Limiter:
    def __init__(self, window: float = 60.0):
        self.window = window
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, ident: str, limit: int, now: float | None = None) -> tuple[bool, int, int]:
        """Return (allowed, remaining, retry_after_seconds)."""
        now = time.monotonic() if now is None else now
        q = self.hits[ident]
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= limit:
            return False, 0, max(1, int(q[0] + self.window - now) + 1)
        q.append(now)
        if len(self.hits) > 50_000:  # bound memory under many distinct IPs
            for k in [k for k, v in self.hits.items() if not v or v[-1] <= now - self.window][:10_000]:
                self.hits.pop(k, None)
        return True, limit - len(q), 0


class RedisLimiter:
    """Fixed-window limiter shared by all workers/replicas (set REDIS_URL). Fails OPEN if Redis is down,
    so an outage of the limiter never takes the API down; that choice is logged once per outage."""

    def __init__(self, url: str, window: int = 60):
        import redis  # imported lazily: only needed when REDIS_URL is set

        self.r = redis.Redis.from_url(url, socket_timeout=0.3, socket_connect_timeout=0.3)
        self.window = window
        self._warned = False

    def check(self, ident: str, limit: int, now: float | None = None) -> tuple[bool, int, int]:
        t = time.time() if now is None else now
        slot = int(t // self.window)
        key = f"rl:{ident}:{slot}"
        try:
            pipe = self.r.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.window + 5)
            n = int(pipe.execute()[0])
            self._warned = False
        except Exception:  # noqa: BLE001
            if not self._warned:
                import logging
                logging.getLogger(__name__).warning("rate limiter: Redis unavailable, allowing requests")
                self._warned = True
            return True, limit, 0
        if n > limit:
            return False, 0, int(self.window - (t % self.window)) + 1
        return True, limit - n, 0


def make_limiter(redis_url: str | None):
    return RedisLimiter(redis_url) if redis_url else Limiter()
