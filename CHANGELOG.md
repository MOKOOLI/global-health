# Changelog

## Unreleased
- Country clinical briefing (printable), command palette, dark mode, home signal strip, official-guidance links.
- Map disclaimer under every map; ranking caveat; reviewer self-assessment (docs/REVIEW_FOR_HEALTH_AUTHORITIES.md).
- Age-standardised rate calculator, dataset versioning/datapackage/snapshot, Atom/JSON signal feeds, annual CSV loader, Redis rate limiting, PWA/lite mode/print styles, trust pages.
- ETL: observations inserted in 500-row chunks, committed per chunk; Postgres TCP keepalives (fixes "server closed the connection" on remote DBs).
- ETL: WHO loader downloads first, then writes with automatic reconnect-and-retry if the database dropped the connection.
- WHO: +13 verified indicators (diabetes, hypertension, hepatitis B/C, suicide, maternal and neonatal mortality, road deaths, breast/colorectal/liver/oesophageal cancer death rates, polio); DTP3 code fixed (WHS4_100); units per 100,000 / 1,000 live births.
- Performance: question parsing 217 ms → 2.5 ms; cached early-warning board.
- 126 diseases in the catalogue.
- Coverage line (countries and share of world population) and SVG map export with embedded caption.
