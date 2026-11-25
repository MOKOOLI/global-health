"""Versioned snapshot for archiving (e.g. Zenodo, which mints a DOI you can cite).

Writes per-indicator CSV + datapackage.json, a package-level datapackage, SHA256SUMS and a README.
Never includes synthetic data. Sources whose licence needs permission for redistribution are skipped unless
--include-restricted is passed (you must then hold that permission).
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import dataset
from app.models import Indicator


def write_snapshot(db: Session, out_dir: str, include_restricted: bool = False) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written, skipped = [], []
    for ind in db.scalars(select(Indicator).order_by(Indicator.code)):
        src = ind.source
        reg = dataset.restriction(src.code)
        why = ("synthetic" if src.is_synthetic else
               "needs permission to redistribute" if reg and reg["commercial"] == "no_without_permission" and not include_restricted
               else None)
        if why:
            skipped.append(dict(indicator=ind.code, reason=why))
            continue
        rows = list(dataset.indicator_csv_rows(db, ind))
        if not rows:
            continue
        with (out / f"{ind.code}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(dataset.CSV_HEADER)
            w.writerows(rows)
        (out / f"{ind.code}.datapackage.json").write_text(
            json.dumps(dataset.datapackage(db, ind), indent=2, ensure_ascii=False), encoding="utf-8")
        written.append(ind.code)
    stamp = datetime.utcnow().strftime("%Y-%m-%d")
    notes = sorted({f"- {i.source.name}: {i.source.license or 'licence not recorded'} {('(see ' + i.source.url + ')') if i.source.url else ''}"
                    for i in db.scalars(select(Indicator)) if i.code in written})
    (out / "README.md").write_text(
        f"# Global Health Atlas data snapshot {stamp}\n\n"
        f"{len(written)} indicators. Each CSV has a matching `.datapackage.json` (licence, source, citation, version hash).\n"
        "Verify files with `sha256sum -c SHA256SUMS`.\n\n"
        "## Licences of the underlying sources (you must follow each one)\n" + "\n".join(notes) + "\n\n"
        "Values keep their data_quality class: reported (counted), estimated, modeled. A model is not a count.\n"
        "These data are for epidemiological information only, not for diagnosis or treatment decisions.\n",
        encoding="utf-8")
    sums = []
    for p in sorted(out.iterdir()):
        if p.name != "SHA256SUMS" and p.is_file():
            sums.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    return dict(dir=str(out), indicators=len(written), skipped=skipped)
