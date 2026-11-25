"""Force an isolated throw-away database BEFORE any app module is imported.

Default: a temporary SQLite file. To run the suite on PostgreSQL set TEST_DATABASE_URL to an EMPTY
throw-away database (never a real one), e.g.
    TEST_DATABASE_URL=postgresql://gh:gh@localhost:5432/gh_test python -m pytest
"""
import os
import tempfile

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tempfile.mkdtemp()}/test.db"
