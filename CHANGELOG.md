# Changelog

## Unreleased
- Pulse tab (`/{locale}/viz`, default): weekly surveillance cards, latest WHO alerts, and a burden table with the latest year of every indicator (filter by text, group, measure, age; per-country view with rank among countries; CSV export; optional 5-minute auto-refresh). Every number carries a freshness class suited to its clock (weekly 14/45 days, alerts 7/30 days, annual 2/4 years); annual estimates are never labelled live. API: `/api/pulse`, `/api/pulse/country/{iso3}`.
- Live charts (`/{locale}/viz`): animated Gapminder-style bubbles (any two indicators, year playback, pinned trails), country similarity network (percentile-rank distance, k-nearest links, label-propagation groups; explicitly not transmission), and a zoomable story generated from the loaded data. API: `/api/viz/options`, `/api/viz/bubbles`, `/api/viz/similarity`.
- Frontend: automatic retry on 502/503/504 and network errors, plus a "server is waking up" notice (free Render/Neon hosts sleep when idle).
- WHO 2000 standard population weights verified against the published table (total 100.035, normalised); "from memory" warnings removed.
- Home page shows diseases that actually have data and the number of observations; empty disease pages link to diseases with data.
- Country clinical briefing (printable), command palette, dark mode, home signal strip, official-guidance links.
- Map disclaimer under every map; ranking caveat; reviewer self-assessment (docs/REVIEW_FOR_HEALTH_AUTHORITIES.md).
- Age-standardised rate calculator, dataset versioning/datapackage/snapshot, Atom/JSON signal feeds, annual CSV loader, Redis rate limiting, PWA/lite mode/print styles, trust pages.
- ETL: observations inserted in 500-row chunks, committed per chunk; Postgres TCP keepalives (fixes "server closed the connection" on remote DBs).
- ETL: WHO loader downloads first, then writes with automatic reconnect-and-retry if the database dropped the connection.
- WHO: +11 verified indicators (diabetes 18+, hypertension, suicide, maternal and neonatal mortality, road deaths, breast/colorectal/liver/oesophageal cancer death rates, polio); DTP3 code fixed (WHS4_100); units per 100,000 / 1,000 live births.
- Performance: question parsing 217 ms → 2.5 ms; cached early-warning board.
- 126 diseases in the catalogue.
- Coverage line (countries and share of world population) and SVG map export with embedded caption.
- Hepatitis B/C prevalence dropped: WHO publishes only regional (not country) estimates for them.
