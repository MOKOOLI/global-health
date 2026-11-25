"""Live outbreak alerts from WHO Disease Outbreak News."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Country, Disease, OutbreakAlert
from etl.common import Run, http_get_json

DON_API = "https://www.who.int/api/news/diseaseoutbreaknews"
DON_BASE = "https://www.who.int/emergencies/disease-outbreak-news/item"


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def load_alerts(db: Session, top: int = 60) -> dict:
    data = http_get_json(
        DON_API,
        {"sf_culture": "en", "$orderby": "PublicationDateAndTime desc", "$top": top},
    )
    countries = sorted(db.scalars(select(Country)), key=lambda c: -len(c.name_en))
    diseases = sorted(db.scalars(select(Disease)), key=lambda d: -len(d.name_en))
    known = set(db.scalars(select(OutbreakAlert.url)))
    added = 0
    with Run(db, "who_don") as run:
        for item in data.get("value", []):
            title = (item.get("Title") or item.get("OverrideTitle") or "").strip()
            path = item.get("ItemDefaultUrl") or item.get("UrlName") or ""
            if not title or not path:
                continue
            url = DON_BASE + (path if path.startswith("/") else "/" + path)
            if url in known:
                continue
            tl = title.lower()
            country = next((c for c in countries if c.name_en.lower() in tl), None)
            disease = next((d for d in diseases if d.name_en.lower() in tl), None)
            db.add(
                OutbreakAlert(
                    title=title,
                    url=url,
                    source="WHO DON",
                    published_at=_parse_dt(item.get("PublicationDateAndTime")),
                    country_iso3=country.iso3 if country else None,
                    disease_id=disease.id if disease else None,
                    summary=(item.get("Summary") or "")[:1500] or None,
                )
            )
            known.add(url)
            added += 1
        run.rows = added
    return {"added": added}
