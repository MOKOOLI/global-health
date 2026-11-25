# Contributing

Thanks for helping. Clinical accuracy matters more than speed here.

- **Data errors** are the highest priority: open an issue with the page, indicator, year and a reference.
- **New data source**: add an ETL module under `backend/etl/`, record the licence in `backend/app/licenses.py` (set `verified: false` until you have read the provider's terms), and keep `data_quality` honest (reported / estimated / modeled).
- **Never** present modeled or synthetic numbers as counts. The Q&A engine only quotes numbers that exist in the database.
- **Translations** (medical text) must be reviewed by a clinician fluent in the language.
- Run `cd backend && pytest` (SQLite) and, for database changes, `TEST_DATABASE_URL=postgresql://... pytest`. Frontend: `cd frontend && npx tsc --noEmit && npm run build`.
