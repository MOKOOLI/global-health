"""ETL command line.

  python -m etl.run reference            # sources, ICD-10 disease catalogue, countries (+World Bank meta)
  python -m etl.run discover <keyword>   # find WHO GHO indicator codes
  python -m etl.run who [--only slug]    # load WHO GHO indicators (guarded by name check)
  python -m etl.run gbd <file.csv>       # import an IHME GBD Results export
  python -m etl.run alerts               # WHO Disease Outbreak News
  python -m etl.run annual file.csv --disease breast-cancer ...   # any annual indicator CSV, you name the columns
  python -m etl.run snapshot --out dir     # versioned CSV + datapackage.json + SHA256SUMS for Zenodo/DOI
  python -m etl.run live [--only name]   # refresh every feed in etl/live_feeds.json (scheduler entry point)
  python -m etl.run apikey create --owner x@y.org --tier free|academic|pro  (or revoke --prefix gha_xxxx)
  python -m etl.run demo                 # SYNTHETIC data for development only
  python -m etl.run replay <disease>     # back-test: when would the engine have warned?
  python -m etl.run surv <kind> [...]    # weekly surveillance feeds, kind in:
        jhu-covid | owid-mpox | who-covid | delphi-fluview | cdc-inspect | cdc-nndss | csv
"""
from __future__ import annotations

import argparse
import json

from app.db import SessionLocal, init_db


def main() -> None:
    p = argparse.ArgumentParser(prog="etl.run")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("reference")
    r.add_argument("--no-worldbank", action="store_true")
    d = sub.add_parser("discover")
    d.add_argument("keyword")
    w = sub.add_parser("who")
    w.add_argument("--only")
    g = sub.add_parser("gbd")
    g.add_argument("csv")
    sub.add_parser("alerts")
    sv = sub.add_parser("surv")
    sv.add_argument("kind", choices=["jhu-covid", "owid-mpox", "who-covid", "delphi-fluview",
                                     "cdc-inspect", "cdc-nndss", "csv"])
    sv.add_argument("--source", help="URL or local path (default: the provider's public URL)")
    sv.add_argument("--disease", help="disease slug (cdc-nndss, csv)")
    sv.add_argument("--label", help="NNDSS disease label exactly as in the dataset")
    sv.add_argument("--geo", action="append", default=[], help="NNDSS 'states' value(s) to sum (repeatable)")
    sv.add_argument("--dataset", default="x9gk-5huc")
    sv.add_argument("--date-col"); sv.add_argument("--value-col"); sv.add_argument("--country-col")
    sv.add_argument("--country-kind", choices=["iso3", "iso2", "name"], default="iso3")
    sv.add_argument("--date-format"); sv.add_argument("--cumulative", action="store_true")
    rp = sub.add_parser("replay")
    rp.add_argument("disease")
    rp.add_argument("--timeline", action="store_true", help="print every level change")
    an = sub.add_parser("annual", help="load an annual indicator CSV (you name the columns)")
    an.add_argument("csv"); an.add_argument("--disease", required=True); an.add_argument("--measure", required=True)
    an.add_argument("--unit", required=True); an.add_argument("--code", required=True, help="indicator code")
    an.add_argument("--name-en", required=True); an.add_argument("--name-fa")
    an.add_argument("--source-code", required=True); an.add_argument("--source-name", required=True)
    an.add_argument("--license", required=True); an.add_argument("--citation", required=True); an.add_argument("--source-url")
    an.add_argument("--country-col", required=True); an.add_argument("--year-col", required=True); an.add_argument("--value-col", required=True)
    an.add_argument("--country-kind", choices=["iso3", "iso2", "name"], default="iso3")
    an.add_argument("--low-col"); an.add_argument("--high-col"); an.add_argument("--sex-col")
    an.add_argument("--filter", action="append", default=[], help="COL=VALUE (repeatable), keep only matching rows")
    an.add_argument("--quality", choices=["reported", "estimated", "modeled"], default="estimated")
    an.add_argument("--age-standardized", action="store_true")
    sn = sub.add_parser("snapshot", help="write a citable, versioned data snapshot (CSV + datapackage + checksums)")
    sn.add_argument("--out", required=True); sn.add_argument("--include-restricted", action="store_true")
    lv = sub.add_parser("live")
    lv.add_argument("--only", action="append", default=[], help="feed name (repeatable)")
    ak = sub.add_parser("apikey")
    ak.add_argument("action", choices=["create", "revoke"])
    ak.add_argument("--owner"); ak.add_argument("--tier", default="free"); ak.add_argument("--prefix")
    sub.add_parser("demo")
    args = p.parse_args()

    init_db()
    if args.cmd == "surv" and args.kind == "cdc-inspect":
        from etl.surveillance import inspect_socrata

        print(json.dumps(inspect_socrata(args.dataset), indent=2, ensure_ascii=False))
        return
    if args.cmd == "discover":
        from etl.who_gho import discover

        for code, name in discover(args.keyword):
            print(f"{code:28s} {name}")
        return

    with SessionLocal() as db:
        if args.cmd == "reference":
            from etl.reference import seed_all

            out = seed_all(db, with_world_bank=not args.no_worldbank)
        elif args.cmd == "who":
            from etl.who_gho import load_who

            out = load_who(db, args.only)
        elif args.cmd == "gbd":
            from etl.gbd_import import import_gbd_csv

            out = import_gbd_csv(db, args.csv)
        elif args.cmd == "surv":
            from etl import surveillance as S

            k, src = args.kind, args.source
            if k == "jhu-covid":
                out = S.load_jhu_covid(db, src or S.JHU_URL)
            elif k == "owid-mpox":
                out = S.load_owid_mpox(db, src or S.OWID_MPOX_URL)
            elif k == "who-covid":
                out = S.load_who_covid(db, src or S.WHO_COVID_URL)
            elif k == "delphi-fluview":
                out = S.load_delphi_fluview(db)
            elif k == "cdc-nndss":
                if not (args.disease and args.label and args.geo):
                    p.error("cdc-nndss needs --disease, --label and --geo (run cdc-inspect first)")
                out = S.load_cdc_nndss(db, args.disease, args.label, args.geo, args.dataset)
            else:
                need = (src, args.disease, args.date_col, args.value_col, args.country_col)
                if not all(need):
                    p.error("csv needs --source --disease --date-col --value-col --country-col")
                out = S.load_csv_weekly(db, src, args.disease, date_col=args.date_col,
                                        value_col=args.value_col, country_col=args.country_col,
                                        country_kind=args.country_kind, cumulative=args.cumulative,
                                        date_format=args.date_format)
        elif args.cmd == "replay":
            from etl.replay import replay_report

            out = replay_report(db, args.disease)
            tl = out.pop("timeline")
            if args.timeline:
                prev = None
                for r in tl:
                    if r["level"] != prev:
                        print(r["week_start"], r["level"], r["n_epidemic"], r["n_watch"], r["n_regions"])
                        prev = r["level"]
        elif args.cmd == "annual":
            from etl.annual_csv import load_annual_csv

            out = load_annual_csv(
                db, args.csv, source_code=args.source_code, source_name=args.source_name, license=args.license,
                citation=args.citation, source_url=args.source_url, disease=args.disease, measure=args.measure,
                unit=args.unit, indicator_code=args.code, name_en=args.name_en, name_fa=args.name_fa,
                age_standardized=args.age_standardized, country_col=args.country_col, year_col=args.year_col,
                value_col=args.value_col, country_kind=args.country_kind, low_col=args.low_col, high_col=args.high_col,
                sex_col=args.sex_col, filters=dict(f.split("=", 1) for f in args.filter), data_quality=args.quality)
        elif args.cmd == "snapshot":
            from etl.snapshot import write_snapshot

            out = write_snapshot(db, args.out, include_restricted=args.include_restricted)
        elif args.cmd == "live":
            from etl.live import run_live

            out = run_live(db, args.only or None)
            print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
            if any(v["status"] == "failed" for v in out.values()):
                raise SystemExit(1)
            return
        elif args.cmd == "apikey":
            from app import apikeys

            if args.action == "create":
                if not args.owner:
                    p.error("apikey create needs --owner")
                key = apikeys.create_key(db, args.owner, args.tier)
                print("Store this key now; it cannot be shown again:\n" + key)
                return
            if not args.prefix:
                p.error("apikey revoke needs --prefix (first 8 chars of the key)")
            out = {"revoked": apikeys.revoke_key(db, args.prefix)}
        elif args.cmd == "alerts":
            from etl.alerts import load_alerts

            out = load_alerts(db)
        else:
            from etl.demo import load_demo

            out = load_demo(db)
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
