"""Subscribable feeds (no personal data, no accounts): Atom for readers, JSON for n8n / scripts."""
from __future__ import annotations

from datetime import datetime, timezone
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import OutbreakAlert
from .routes_surv import board

router = APIRouter(prefix="/api/feeds")
ORDER = ["none", "watch", "single_country", "regional_outbreak", "novel_spread", "multi_region_outbreak", "pandemic_pattern"]
NOTE = {"en": "A statistical signal from reported counts, not an official declaration by WHO or any authority.",
        "fa": "یک سیگنال آماری از شمارش‌های گزارش‌شده است، نه اعلام رسمی WHO یا هیچ مرجع دیگری."}


def _entries(db: Session, min_level: str, disease: str | None, lang: str, with_alerts: bool) -> list[dict]:
    if min_level not in ORDER:
        raise HTTPException(422, f"min_level must be one of {ORDER}")
    out = []
    base = settings.public_url.rstrip("/")
    for b in board(lang, db):
        if disease and b["slug"] != disease:
            continue
        lvl = b["pattern"]["level"]
        if ORDER.index(lvl) < ORDER.index(min_level) or lvl == "none":
            continue
        p = b["pattern"]
        stale = b["weeks_behind_today"] > 3
        text = (f"{p['n_epidemic']} countries above expected, {p['n_regions']} WHO regions. " if lang == "en"
                else f"{p['n_epidemic']} کشور بالاتر از حد انتظار، {p['n_regions']} منطقه‌ی WHO. ")
        if stale:
            text += (f"Data are {b['weeks_behind_today']} weeks old. " if lang == "en"
                     else f"داده {b['weeks_behind_today']} هفته قدیمی است. ")
        out.append(dict(
            id=f"tag:globalhealthatlas:signal:{b['slug']}:{lvl}:{b['as_of']}", kind="signal", disease=b["slug"], level=lvl,
            title=f"{b['name']}: {p['label'][lang] if isinstance(p['label'], dict) else p['label']}",
            summary=text + NOTE[lang], updated=f"{b['as_of']}T00:00:00Z", url=f"{base}/{lang}/surveillance", stale=stale))
    if with_alerts:
        for a in db.scalars(select(OutbreakAlert).order_by(OutbreakAlert.published_at.desc()).limit(30)):
            out.append(dict(id=f"tag:globalhealthatlas:alert:{a.id}", kind="who_don", disease=None, level=None, title=a.title,
                            summary=(a.summary or "")[:500] + (" " if a.summary else "") + f"Source: {a.source}.",
                            updated=(a.published_at or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            url=a.url, stale=False))
    return out


@router.get("/signals.json")
def signals_json(min_level: str = "watch", disease: str | None = None, lang: str = "en", alerts: bool = True,
                 db: Session = Depends(get_db)):
    lang = lang if lang in ("fa", "en") else "en"
    return dict(generated=datetime.now(timezone.utc).isoformat(timespec="seconds"), note=NOTE[lang],
                entries=_entries(db, min_level, disease, lang, alerts))


@router.get("/signals.atom")
def signals_atom(min_level: str = "watch", disease: str | None = None, lang: str = "en", alerts: bool = True,
                 db: Session = Depends(get_db)):
    lang = lang if lang in ("fa", "en") else "en"
    items = _entries(db, min_level, disease, lang, alerts)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updated = max([i["updated"] for i in items], default=now)
    body = "".join(
        f"<entry><id>{escape(i['id'])}</id><title>{escape(i['title'])}</title><updated>{i['updated']}</updated>"
        f"<link href=\"{escape(i['url'])}\"/><summary>{escape(i['summary'])}</summary></entry>" for i in items)
    xml = (f"<?xml version=\"1.0\" encoding=\"utf-8\"?><feed xmlns=\"http://www.w3.org/2005/Atom\" xml:lang=\"{lang}\">"
           f"<id>tag:globalhealthatlas:signals</id><title>Global Health Atlas: outbreak signals</title>"
           f"<subtitle>{escape(NOTE[lang])}</subtitle><updated>{updated}</updated>{body}</feed>")
    return Response(xml, media_type="application/atom+xml; charset=utf-8")
