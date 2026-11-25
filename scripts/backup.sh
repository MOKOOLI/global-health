#!/usr/bin/env bash
# Dump the PostgreSQL database. Usage: DATABASE_URL=postgresql://user:pw@host/db scripts/backup.sh [outdir]
set -euo pipefail
out="${1:-backups}"; mkdir -p "$out"
url="${DATABASE_URL:?set DATABASE_URL}"; url="${url/postgresql+psycopg:/postgresql:}"
f="$out/gh-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
pg_dump --no-owner --no-privileges "$url" | gzip > "$f"
gzip -t "$f" && echo "wrote $f ($(du -h "$f" | cut -f1))"
ls -1t "$out"/gh-*.sql.gz | tail -n +15 | xargs -r rm -f   # keep the 14 newest
