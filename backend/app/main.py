from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from . import apikeys
from .db import SessionLocal, init_db
from .routes import router
from .routes_extra import router as extra_router
from .routes_feeds import router as feeds_router
from .routes_tools import router as tools_router
from .routes_viz import router as viz_router
from .routes_surv import router as surveillance_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Global Health Atlas API",
    description="Open epidemiological data for clinicians worldwide. Not a diagnostic tool.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
)
limiter = apikeys.make_limiter(settings.redis_url)


def _client_ip(request: Request) -> str:
    if settings.trust_proxy:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if not request.url.path.startswith("/api/") or request.method == "OPTIONS":
        return await call_next(request)
    key = request.headers.get("x-api-key")
    tier = "anonymous"
    ident = "ip:" + _client_ip(request)
    if key:
        with SessionLocal() as db:
            found = apikeys.lookup_tier(db, key)
        if found is None:
            return JSONResponse({"detail": "Invalid or revoked API key"}, status_code=401)
        tier, ident = found, "key:" + apikeys.hash_key(key)
    limit = apikeys.TIERS[tier]
    ok, remaining, retry = limiter.check(ident, limit)
    if not ok:
        return JSONResponse({"detail": f"Rate limit exceeded ({limit}/min for tier {tier})"}, status_code=429,
                            headers={"Retry-After": str(retry), "X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": "0"})
    resp = await call_next(request)
    resp.headers["X-RateLimit-Limit"] = str(limit)
    resp.headers["X-RateLimit-Remaining"] = str(remaining)
    return resp

app.include_router(router)
app.include_router(surveillance_router)
app.include_router(extra_router)
app.include_router(feeds_router)
app.include_router(tools_router)
app.include_router(viz_router)


@app.get("/api/ask")
async def ask(q: str, lang: str | None = None):
    """Natural-language question -> sourced answer (see app/ask.py for the safety rules)."""
    from . import ask as A

    if not q.strip() or len(q) > 300:
        raise HTTPException(422, "q must be 1-300 characters")
    with SessionLocal() as db:
        p = A.parse(db, q)
        if not p.diseases and not p.out_of_scope:
            alt = await A.llm_extract(db, q)
            if alt is not None:
                p = alt
        return A.answer(db, q, lang if lang in ("fa", "en") else None, parsed=p)


@app.get("/api/licenses")
def licenses():
    from .licenses import LICENSES, METHOD

    return dict(sources=LICENSES, method=METHOD, tiers={k: v for k, v in apikeys.TIERS.items()},
                disclaimer="Working register, not legal advice; entries with verified=false have not been checked against the provider's current terms.")
