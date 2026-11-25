# Deploy: GitHub + Vercel (site) + managed Postgres + API host

```
Browser ──> Vercel (Next.js)  ──/api/* rewrite──>  API (Render/Fly/Railway/VPS) ──> Postgres (Neon/Supabase)
                                                          ▲
GitHub Actions (daily cron) ── etl.run live ──────────────┘ (writes to the same Postgres)
```

Vercel only hosts the front end. The FastAPI backend and database must live elsewhere.

## 1. Push to GitHub
```bash
cd global-health
git init -b main && git add . && git commit -m "Global Health Atlas"
git remote add origin https://github.com/MOKOOLI/global-health-atlas.git
git push -u origin main
```
CI (`.github/workflows/ci.yml`) runs the backend tests and the front-end type-check + build on every push.

## 2. Database
Create a Postgres database (Neon and Supabase both have free tiers). Copy its connection string; `postgres://` and
`postgresql://` forms are accepted (they are rewritten to the psycopg driver automatically).

## 3. API
Deploy `backend/` as a Docker service (Render: `render.yaml` Blueprint; Fly.io/Railway/any VPS also work).
Environment variables:

| name | value |
|---|---|
| `DATABASE_URL` | your Postgres URL |
| `CORS_ORIGINS` | `https://<your-site>.vercel.app` |
| `PUBLIC_URL` | same, used in citations |
| `TRUST_PROXY` | `true` (client IP comes from `X-Forwarded-For`) |
| `OLLAMA_URL` | optional, only if you run Ollama somewhere reachable |

Check: `https://<api-host>/api/health` returns `{"status":"ok",...}`.
Free API tiers sleep when idle, so the first request can take tens of seconds.

## 4. First data load (once, from your machine or the host's shell)
```bash
cd backend && pip install -r requirements.txt
export DATABASE_URL='postgresql://...'
python -m etl.run reference
python -m etl.run live          # all feeds; a failing feed does not stop the others
python -m etl.run surv jhu-covid && python -m etl.run surv owid-mpox   # history for the replay lessons
```
Annual burden data (WHO GHO is loaded by `live`; IHME GBD needs your own export: `python -m etl.run gbd file.csv`,
subject to IHME's terms).

CDC NNDSS: run `python -m etl.run surv cdc-inspect`, copy the exact disease label and `states` value(s) into the
`cdc-nndss-measles` entry of `backend/etl/live_feeds.json`, set `"enabled": true`.

## 5. Vercel (front end)
1. Import the GitHub repo. **Root Directory: `frontend`**. Framework: Next.js.
2. Environment variable (Production **and** Preview): `API_URL = https://<api-host>`. It is read at **build time**
   (it is baked into the `/api/*` rewrite), so redeploy after changing it.
3. Deploy. The site calls `/api/...` on its own domain and Vercel forwards it to your API (no CORS problems).

## 6. Scheduled refresh (GitHub Actions)
Repo → Settings → Secrets and variables → Actions → new secret `DATABASE_URL`.
`.github/workflows/refresh-data.yml` then runs daily at 03:17 UTC; run it by hand from the Actions tab to test.
Open `https://<site>/api/health/sources` to see the last success/failure per feed. A failed feed makes the run red.

## 7. API keys
```bash
python -m etl.run apikey create --owner someone@hospital.org --tier academic   # shown once
python -m etl.run apikey revoke --prefix gha_xxxx
```

## Known limits of this setup
* The rate limiter is per process. With several API instances use a shared store (Redis) first.
* If the API URL is public, a caller can send a fake `X-Forwarded-For` and dodge the per-IP limit.
  API keys are the reliable control; consider a platform-level firewall/rate limit as well.
* If the Vercel rewrite is used, all site traffic reaches the API through Vercel; the per-IP limit then applies to the real
  client only if the host forwards the client IP (check `X-Forwarded-For` on your host).
* Nothing here has been run on Vercel/Render/Neon from the development sandbox. Treat the first deploy as a test.
