"""Tiny client for the Global Health Atlas API (needs `requests` or falls back to urllib).

    from ghatlas import Atlas
    a = Atlas("https://your-host", api_key=None)
    a.ask("breast cancer incidence in the UK in 2020")
    df = a.indicator_df("who_tb_incidence")      # pandas optional
"""
from __future__ import annotations

import csv
import io
import json
import urllib.parse
import urllib.request


class Atlas:
    def __init__(self, base: str = "http://localhost:8000", api_key: str | None = None, timeout: int = 60):
        self.base, self.key, self.timeout = base.rstrip("/"), api_key, timeout

    def _get(self, path: str, **params) -> bytes:
        qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        req = urllib.request.Request(f"{self.base}{path}{'?' + qs if qs else ''}")
        if self.key:
            req.add_header("X-API-Key", self.key)
        with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310
            return r.read()

    def json(self, path: str, **params):
        return json.loads(self._get(path, **params))

    def ask(self, q: str, lang: str | None = None) -> dict:
        return self.json("/api/ask", q=q, lang=lang)

    def indicator_rows(self, code: str) -> list[dict]:
        text = self._get(f"/api/export/indicator/{code}.csv").decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(text)))

    def indicator_df(self, code: str):
        import pandas as pd  # optional dependency

        return pd.DataFrame(self.indicator_rows(code))

    def cite(self, kind: str, key: str) -> dict:
        return self.json("/api/cite", kind=kind, key=key)

    def signals(self, min_level: str = "watch", lang: str = "en") -> dict:
        return self.json("/api/feeds/signals.json", min_level=min_level, lang=lang)

    def age_standardise(self, groups: list[dict], standard: str = "segi", per: int = 100000) -> dict:
        req = urllib.request.Request(f"{self.base}/api/tools/age-standardise", method="POST",
                                     data=json.dumps(dict(groups=groups, standard=standard, per=per)).encode(),
                                     headers={"Content-Type": "application/json", **({"X-API-Key": self.key} if self.key else {})})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310
            return json.loads(r.read())
