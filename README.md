# Global Health Atlas · اطلس سلامت جهانی

An open, bilingual (فارسی / English, RTL/LTR) web atlas of disease incidence, prevalence, mortality and
burden for every country, built for clinicians. Map, trends, country comparison, automatic analysis,
travel-medicine style country profiles and live outbreak alerts.

> **Not a clinical decision tool.** Many figures are modelled estimates, not counts. The UI says so on every
> page, labels each number as *reported / estimated / modelled*, and shows its source.

## Architecture

```
WHO GHO API ─┐
GBD CSV ─────┼─► etl/ (Python) ─► PostgreSQL ─► FastAPI ─► Next.js (map: d3-geo, charts: ECharts)
WHO DON ─────┘   (n8n can schedule)               │
World Bank ──────────────────────────────────────┘ └─► optional Ollama (rewrites findings only)
```

| Path | What |
|---|---|
| `backend/app` | FastAPI: meta, countries, diseases, map/trend/ranking, country profile, insights, search, alerts |
| `backend/app/analytics.py` | All statistics (trend, change-point, anomalies, Holt extrapolation). **No LLM.** |
| `backend/app/insights.py` | Turns analytics into structured findings with fa/en templates |
| `backend/app/llm.py` | Optional Ollama summary; output rejected if it contains any number not in the findings |
| `backend/etl` | `reference` (ICD-10 catalogue, ISO countries, World Bank meta), `who`, `gbd`, `alerts`, `demo` |
| `backend/etl/catalogue.py` | **63 diseases anchored on ICD-10** with Persian names and GBD cause names — review this with colleagues |
| `backend/etl/indicators_config.py` | WHO GHO indicators to load (each guarded by a name check) |
| `frontend` | Next.js 15, Persian-first, logical CSS (RTL/LTR), Vazirmatn font |
| `db/schema.sql` | PostgreSQL DDL generated from the models (the API also creates tables on start) |

## Run it locally (no Docker, no Postgres)

```bash
# backend (SQLite by default)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m etl.run reference          # sources, diseases, countries (+ World Bank region/income/population)
python -m etl.run demo               # SYNTHETIC data, development only (shows a red banner in the UI)
uvicorn app.main:app --port 8000
pytest                               # 15 tests

# frontend (second terminal)
cd frontend
npm install
API_URL=http://localhost:8000 npm run dev      # http://localhost:3000  (redirects to /fa)
```

`/api/*` is proxied by Next.js to the backend (`API_URL`), so there is no CORS setup to do.

## Run with Docker

```bash
cp .env.example .env
docker compose up -d --build                         # db + backend + web
docker compose --profile etl run --rm etl python -m etl.run reference
docker compose --profile etl run --rm etl python -m etl.run who
docker compose --profile ai up -d                    # optional: Ollama for the "AI summary" button
docker compose exec ollama ollama pull qwen2.5:7b
```

## Loading real data

1. **Reference:** `python -m etl.run reference`
2. **WHO GHO:** `python -m etl.run who`
   Indicator codes are *verified at load time*: the ETL fetches each code's official name and requires the
   expected keywords in `indicators_config.py`; mismatches are **skipped and reported**, never loaded.
   Find or confirm codes with `python -m etl.run discover tuberculosis`, then add them to the config.
3. **GBD (full "all diseases × all countries" coverage):** IHME has no public bulk API.
   In the [GBD Results tool](https://vizhub.healthdata.org/gbd-results/) export Incidence / Prevalence /
   Deaths / DALYs (Rate and Number; All ages + Age-standardized; Both/Male/Female; all years) for the
   causes in `catalogue.py`, then `python -m etl.run gbd data/file.csv`.
   **Read IHME's current licence terms and cite them** before publishing.
4. **Outbreak alerts:** `python -m etl.run alerts`
5. **Scheduling with n8n:** `docker compose --profile automation up -d`, then use a *Schedule Trigger* →
   *Execute Command* node running `docker compose --profile etl run --rm etl python -m etl.run who`
   (and `alerts` daily).

All loaders are idempotent (re-running updates rows in place).

## Early-warning engine (epidemic / endemic / pandemic-pattern signals)

Page `/{fa,en}/surveillance`, API `/api/surveillance/*`, code in `backend/app/outbreak.py`.

**What it is:** a statistical surveillance engine over *weekly* reported counts. Per country it classifies the
current state (no data / inactive / sporadic / endemic level / watch / above expected = epidemic signal /
declining), estimates growth, doubling time and an *indicative* reproduction number, and produces a 4-week
forecast with back-tested skill. Across countries it flags a multi-country *pattern* (single country, regional,
multi-region, novel spread, pandemic-like). A "time machine" slider replays any past week using only the data
known then. All logic is causal (no future leakage) and unit-tested.

**What it is not:** it does not predict novel pandemics months ahead, and it never declares anything.
Epidemics, PHEICs and pandemics are declared by WHO and national authorities. Output is a signal for a clinician
to look at, not a diagnosis or a declaration.

Weekly sources (`python -m etl.run surv <kind>`):

| kind | source | status |
|---|---|---|
| `jhu-covid` | JHU CSSE COVID-19 (CC BY 4.0; archived, ends 2023-03-10) | run on real data |
| `owid-mpox` | Our World in Data mpox | run on real data |
| `who-covid` | WHO COVID-19 CSV | parser tested on fixtures only |
| `delphi-fluview` | CDC FluView ILI via Delphi Epidata (MMWR weeks) | parser tested on fixtures only |
| `cdc-inspect` / `cdc-nndss` | CDC NNDSS weekly tables (Socrata `x9gk-5huc`); run `cdc-inspect` first to choose `--label` / `--geo` | parser tested on fixtures only |
| `csv` | any CSV (UKHSA, ECDC, national dashboards): `--source --disease --date-col --value-col --country-col` | parser tested on fixtures only |

Back-test: `python -m etl.run replay covid-19 --timeline`. On the real data the engine flagged first cases
spreading across regions for COVID-19 in the week of 2020-02-24 and a pandemic-like pattern in the week of
2020-04-06 (WHO characterised COVID-19 as a pandemic on 11 March 2020; PHEIC 30 January 2020 - verify these
dates against WHO). For mpox it flagged novel spread in the week of 2022-05-16, the week of WHO's first
outbreak notice. These are two retrospective examples, not a performance guarantee.

Known limits: reporting changes (batch reporting, backlogs, definition changes) can mimic outbreaks (batch
reporting is detected and smoothed, not eliminated); forecasts have no seasonality model and often do not beat
a naive forecast (the page says so per series); generation intervals are indicative literature values; mpox
shows level flicker; a country with a near-zero baseline can show a huge "ratio"; CDC/Delphi/WHO connectors
have not been run against the live services from the development sandbox; the Delphi connector uses the legacy
endpoint and may need migrating.

**Upgrading an existing SQLite DB:** the new `country.who_region` column is not added automatically
(`create_all` does not alter tables). Delete the DB file and rerun `reference`, or `ALTER TABLE country ADD COLUMN who_region VARCHAR(8)`
and rerun `reference`.

## Smart search (`/{locale}/ask`, `GET /api/ask?q=`)

Text or voice ("breast cancer in the UK 2020?" / «آمار سرطان سینه در انگلیس سال ۲۰۲۰ چقدر بوده؟») -> a sourced answer.

- The question is parsed **deterministically** (catalogue names in fa/en, aliases, typo tolerance, spoken Persian years such as
  «دو هزار و بیست») into disease + country + year(s) + measure + sex. Every number is copied from a database row and shown with
  indicator, source, licence, citation, data-quality class and retrieval date, plus CSV/cite buttons. No AI text is generated.
- Safe failure: missing data -> "no data, nothing estimated"; a different year is labelled as such; ambiguity (e.g. just "cancer",
  or no country) -> asks; typo matches are labelled; "England" answers are flagged as UK-wide; Persian-calendar years are refused
  rather than guessed; synthetic demo data gets a red critical warning; personal diagnosis/treatment questions are declined.
- Voice uses the browser's Web Speech API (Chrome/Edge/Safari; not Firefox). Audio may go to the browser vendor's service; the UI says so.
  It has **not** been tested with real microphone audio (only the UI and the text path were).
- Optional: `ASK_USE_LLM=true` lets Ollama extract the fields when parsing fails; its output must still resolve to real catalogue entries.
- The answer is only as good as the loaded data: with no WHO GHO / GBD data loaded, real questions return "no data".

## Verification status

- 61 backend tests pass on SQLite **and on PostgreSQL 16** (`TEST_DATABASE_URL=postgresql://... python -m pytest`, use an empty throw-away DB).
- `db/schema.sql` applies cleanly to an empty PostgreSQL 16 database; reference + demo + JHU COVID loads, the replay and the API were run on it.
- `docker compose config` is valid. **The container images were not built or run** (Docker Hub was unreachable from the dev sandbox);
  run `docker compose up --build` yourself and report any failure.

## Learn mode, exports and live refresh

- **Home** (`/fa`, `/en`): animated replay of COVID-19 on the map. **Explore** moved to `/{locale}/explore`.
- **Learn** (`/{locale}/learn`): glossary (burden, outbreak, data-quality terms), "how to read a chart", and replay lessons
  for COVID-19 (2020) and mpox (2022). Replays use `/api/surveillance/{disease}/frames`; if the API has no data the page falls
  back to the bundled `frontend/public/demo/*-replay.json` (generated from JHU CSSE / OWID, CC BY 4.0). Official dates shown in
  lessons are from memory: verify against WHO before using them in teaching.
- **Live charts** (`/{locale}/viz`): animated bubbles (`/api/viz/bubbles?x=&y=`), similarity network (`/api/viz/similarity`) and a zoomable story. Frames use only real (country, year) pairs where both indicators are measured; the network shows statistical similarity of reported burden, not disease spread. Respects reduced-motion; every chart has a table or list alternative.
- **CSV and citation**: `/api/export/indicator/{code}.csv`, `/api/export/surveillance/{disease}/{iso3}.csv`, `/api/cite`
  (APA + BibTeX). Cite the original provider too. Set `PUBLIC_URL` so citations carry your real domain.
- **Live refresh**: `python -m etl.run live` runs every feed in `backend/etl/live_feeds.json` (WHO GHO, WHO DON, OWID mpox,
  WHO COVID, CDC FluView via Delphi; CDC NNDSS ships disabled until you pick its label). A failing feed is retried, recorded and
  does not block others. `/api/health/sources` shows last success/failure per feed.
  **None of the live feeds has been run against the real services from the development sandbox**: run the first refresh by hand
  and read the report.
- **Deploying** (GitHub + Vercel + Postgres + scheduled refresh): see `DEPLOY.md`. CI and a daily refresh workflow are in `.github/workflows/`.

## API keys, rate limits and data licences

- Every `/api/` call is rate-limited: anonymous per IP, or per key via the `X-API-Key` header
  (tiers anonymous 120, free 240, academic 600, pro 2400 requests/min; headers `X-RateLimit-*`, `429` + `Retry-After`).
- Operator creates keys: `python -m etl.run apikey create --owner you@org --tier academic` (shown once, stored only as a hash);
  revoke with `apikey revoke --prefix gha_xxxx`. There is intentionally no public signup endpoint yet.
- The limiter is in-process (one worker). Use a shared store such as Redis before running several workers/replicas.
- Behind a proxy set `TRUST_PROXY=true` (docker-compose does) so the real client IP is used; only do so when the backend
  port is not publicly reachable, otherwise clients can spoof `X-Forwarded-For`.
- `/api/licenses` and the site page *Data & API* list every source's licence and whether commercial use is allowed.
  **All entries are `verified: false`**: they are my working notes, not legal advice. Read each provider's current terms
  and record the check before any paid tier. In particular IHME GBD free use is non-commercial, and WHO data terms may
  be non-commercial too: keep the free tier open and get written permission before charging for features built on them.

## Safety design

- Every observation stores `data_quality` (reported / estimated / modelled); shown as a badge with explanation.
- Counts are never compared across countries (only per-capita indicators are ranked).
- Numbers in the analysis come from code only; the LLM may rephrase and is validated.
- Forecasts are labelled indicative extrapolations, not predictions of outbreaks; early-warning output is a statistical signal, never an official declaration.
- Synthetic data raises a site-wide red banner. **Never deploy a public instance with `etl.run demo` loaded.**

## Known gaps / next steps

- Age-standardised vs crude rates are stored separately (`age_group = ASR`) but the UI age selector is not built yet.
- Sub-national data, vaccine schedules, treatment guidelines links (WHO/national) per disease.
- Text-to-SQL chat over the data (deliberately not included: needs a read-only role and query allow-listing).
- Authentication/admin endpoints for triggering ETL from n8n via HTTP.

## Added for clinicians and postgraduate users

- **Tools** (`/tools`): age-standardised rate calculator (Segi, WHO 2000, custom weights; Fay–Feuer interval) and a browser-only CSV viewer. API: `POST /api/tools/age-standardise`.
- **Reproducibility**: every indicator has a data-version hash (`X-Data-Version`, included in `/api/cite`), a Frictionless-style `datapackage.json`, and `python -m etl.run snapshot` writes CSVs + checksums for archiving (Zenodo DOI minting is up to you; restricted/synthetic sources are skipped).
- **Own data**: `python -m etl.run annual …` loads any annual CSV (country, year, value columns) as a new source with a licence you declare. This is the route for GLOBOCAN-style exports; no GLOBOCAN-specific connector exists.
- **Feeds**: `/api/feeds/signals.atom` and `.json` (see `docs/n8n.md`).
- **Share/embed**: replay lessons have copy-link, iframe embed code (`/embed/<slug>`) and SVG download. Print stylesheet, installable PWA with offline shell, "lite mode" for slow connections.
- **Trust page** (`/trust`): terms, privacy, accessibility, data-equity and governance placeholders. Fill the `[brackets]` before launch.
- **Clients**: `clients/python/ghatlas.py` (tested), `clients/r/ghatlas.R` (NOT tested: no R here).
- **Ops**: `scripts/backup.sh` (pg_dump), `.github/workflows/uptime.yml` (set repo variable `SITE_URL`), Redis in docker-compose for shared rate limits.

### Measured on a laptop-class sandbox (SQLite, one worker, 20 concurrent clients, not production figures)
`/api/ask` ≈ 285 req/s (p95 77 ms); cached `/api/surveillance/board` ≈ 254 req/s (cold build 1.2 s); `/api/meta` ≈ 238 req/s.

### Known gaps
`npm audit` reports a PostCSS advisory pulled in by Next 15 (build-time only; the fix needs Next 16). Licence register is unverified. UI is Persian/English only.

### Interface additions
Command palette (Ctrl/⌘+K or `/`: disease, country, page, or a plain-language question), dark mode (follows the system, remembered locally), and a live "what the data show now" strip on the home page that always states how old the loaded data are. Dark mode was checked on the early-warning page only; other pages have not been reviewed in dark.

### Country clinical briefing and official-guidance links
`/country/<ISO3>` is now a printable one-page briefing: counts, conditions highest relative to the global median (per-capita indicators only), data-type mix, sources and licences, a copy-as-text summary, and an explicit warning if any synthetic data are present. Each disease page links to WHO / CDC / ECDC / PubMed search for that disease; links open the authority's own search and assert no specific document. Note: `etl.run demo` needs `etl.run reference` to have been run first on a fresh database.

Dark mode was reviewed on the disease, compare, ask, learn, tools, data and country pages (demo data) and contrast problems were fixed. Header fits one row at ≥1280 px and wraps to two rows below that.

### For papers and equity
Each map shows how many countries/territories have data and, when population figures are loaded, the share of world population covered (uncovered populations are not "healthy", just unreported). "Download map (SVG)" exports the current map with title, source and boundary disclaimer embedded, ready for a manuscript or slide.
