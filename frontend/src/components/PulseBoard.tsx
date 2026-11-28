"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useApi } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import { PULSE_TXT, type Fresh, type PulseBurden, type PulseCountryItem, type PulseCountryResp, type PulseResp } from "@/lib/pulse";

type SortKey = "disease" | "name" | "year" | "n" | "median" | "age";

function Badge({ f, text }: { f: Fresh; text: string }) {
  const { locale } = useLocale();
  const T = PULSE_TXT[locale];
  return <span className={`pulse-badge pulse-${f}`} title={T[f]}><i className="pulse-dot" aria-hidden="true" /> {text}</span>;
}

export default function PulseBoard() {
  const { locale, num, label } = useLocale();
  const T = PULSE_TXT[locale];
  const fa = locale === "fa";
  const [tick, setTick] = useState(0);
  const [auto, setAuto] = useState(true);
  const res = useApi<PulseResp>("/pulse", { lang: locale, _t: tick });
  const d = res.data;

  useEffect(() => {
    if (!auto) return;
    const id = window.setInterval(() => { if (document.visibilityState === "visible") setTick((t) => t + 1); }, 5 * 60 * 1000);
    return () => window.clearInterval(id);
  }, [auto]);

  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [measure, setMeasure] = useState("");
  const [fresh, setFresh] = useState<"" | Fresh>("");
  const [iso, setIso] = useState("");
  const [sort, setSort] = useState<{ k: SortKey; dir: 1 | -1 }>({ k: "disease", dir: 1 });
  const cres = useApi<PulseCountryResp>(iso ? `/pulse/country/${iso}` : null, { lang: locale });

  const countries = useApi<{ iso3: string; name: string }[]>("/countries", { lang: locale });

  const cats = useMemo(() => Array.from(new Set((d?.burden ?? []).map((b) => b.category).filter(Boolean) as string[])).sort(), [d]);
  const measures = useMemo(() => Array.from(new Set((d?.burden ?? []).map((b) => b.measure))).sort(), [d]);

  const match = (disease: string | null, name: string, m: string, f: Fresh) => {
    const hay = `${disease ?? ""} ${name}`.toLowerCase();
    return (!q || hay.includes(q.trim().toLowerCase())) && (!measure || m === measure) && (!fresh || f === fresh);
  };

  const world = useMemo(() => {
    const rows = (d?.burden ?? []).filter((b) => match(b.disease, b.name, b.measure, b.freshness) && (!cat || b.category === cat));
    const val = (b: PulseBurden): string | number => ({ disease: b.disease ?? "", name: b.name, year: b.year, n: b.n, median: b.median, age: b.age_years }[sort.k]);
    return [...rows].sort((a, b) => {
      const x = val(a), y = val(b);
      const c = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), locale);
      return c * sort.dir || a.name.localeCompare(b.name, locale);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [d, q, cat, measure, fresh, sort, locale]);

  const cRows = useMemo(() => (cres.data?.items ?? []).filter((b) => match(b.disease, b.name, b.measure, b.freshness)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [cres.data, q, measure, fresh]);

  const fmt = (v: number) => num(v, Math.abs(v) >= 1000 ? 0 : Math.abs(v) >= 100 ? 1 : Math.abs(v) >= 1 ? 2 : 3);
  const yr = (y: number) => num(y, 0).replace(/[,٬]/g, "");
  const setSortKey = (k: SortKey) => setSort((s) => (s.k === k ? { k, dir: (-s.dir) as 1 | -1 } : { k, dir: 1 }));
  const th = (k: SortKey, text: string) => (
    <th aria-sort={sort.k === k ? (sort.dir === 1 ? "ascending" : "descending") : "none"}>
      <button type="button" className="linklike" onClick={() => setSortKey(k)} title={T.sort}>{text}{sort.k === k ? (sort.dir === 1 ? " ▲" : " ▼") : ""}</button>
    </th>
  );

  const csv = () => {
    const esc = (s: string | number | null | undefined) => `"${String(s ?? "").replace(/"/g, '""')}"`;
    const lines = iso && cres.data
      ? [["disease", "indicator", "measure", "unit", "year", "value", "low", "high", "rank_worst", "of", "median"].join(","),
        ...cRows.map((r) => [r.disease, r.name, r.measure, r.unit, r.year, r.value, r.low, r.high, r.rank_worst, r.of, r.median].map(esc).join(","))]
      : [["disease", "indicator", "measure", "unit", "year", "countries", "median", "sum_if_count", "worst_country", "worst_value", "source"].join(","),
        ...world.map((r) => [r.disease, r.name, r.measure, r.unit, r.year, r.n, r.median, r.total, r.extreme.name, r.extreme.value, r.source?.name].map(esc).join(","))];
    const url = URL.createObjectURL(new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url; a.download = `pulse-${iso || "world"}-${d?.today ?? ""}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  if (res.loading && !d) return <p className="muted">{T.loading}</p>;
  if (res.error && !d) return <p className="notice">{T.failed}: {res.error}</p>;
  if (!d) return null;

  const when = new Date(d.generated_at + "Z");
  const cShown = iso ? cRows.length : world.length;
  const dlist = (days: number | null) => (days === null ? "—" : `${num(days, 0)} ${T.daysAgo}`);

  return (
    <section aria-label={T.tab}>
      <div className="pulse-bar">
        <span className="muted small">{T.updated}: {when.toLocaleString(locale === "fa" ? "fa-IR" : "en-GB", { dateStyle: "medium", timeStyle: "short" })}</span>
        <button type="button" className="btn-solid" onClick={() => setTick((t) => t + 1)} disabled={res.loading}>{T.refresh}</button>
        <label className="viz-check small"><input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} /> {T.auto}</label>
      </div>
      <p>{T.lead}</p>
      <details className="pulse-legend">
        <summary>{T.legendTitle}</summary>
        <p><Badge f="fresh" text={T.fresh} /> <Badge f="aging" text={T.aging} /> <Badge f="old" text={T.old} /></p>
        <ul className="small"><li>{T.legendWeekly}</li><li>{T.legendAlert}</li><li>{T.legendAnnual}</li></ul>
      </details>

      <h2>{T.weeklyTitle}</h2>
      <p className="small muted">{T.weeklyNote}</p>
      {d.weekly.length === 0 ? <p className="muted">{T.weeklyEmpty}</p> : (
        <div className="pulse-cards">
          {d.weekly.map((w) => (
            <article key={w.slug} className="pulse-card">
              <h3><Link href={`/${locale}/surveillance?d=${w.slug}`}>{w.name}</Link></h3>
              <p className="pulse-pattern">{fa ? w.pattern.label.fa : w.pattern.label.en}</p>
              <p className="small muted">{T.asOf} {w.as_of} · <Badge f={w.freshness} text={dlist(w.age_days)} /></p>
              {w.top.length > 0 && (
                <p className="small">{T.topCountries}: {w.top.slice(0, 3).map((c, i) => (
                  <span key={c.iso3}>{i ? ", " : ""}<Link href={`/${locale}/country/${c.iso3}`}>{c.name}</Link></span>
                ))}</p>
              )}
            </article>
          ))}
        </div>
      )}

      <h2>{T.alertsTitle}</h2>
      {d.alerts.length === 0 ? <p className="muted">{T.alertsEmpty}</p> : (
        <ul className="pulse-alerts">
          {d.alerts.map((a) => (
            <li key={a.url}>
              <Badge f={a.freshness} text={dlist(a.age_days)} />{" "}
              <a href={a.url} target="_blank" rel="noopener noreferrer">{a.title}</a>
              <span className="small muted"> — {a.source}{a.country ? ` · ${a.country}` : ""}{a.disease ? ` · ${a.disease}` : ""}</span>
            </li>
          ))}
        </ul>
      )}

      <h2>{T.burdenTitle}</h2>
      <p className="small muted">{T.burdenNote}</p>
      <div className="viz-controls">
        <label>{T.search}<input type="search" value={q} onChange={(e) => setQ(e.target.value)} /></label>
        <label>{T.country}
          <select value={iso} onChange={(e) => setIso(e.target.value)}>
            <option value="">{T.worldwide}</option>
            {(countries.data ?? []).map((c) => <option key={c.iso3} value={c.iso3}>{c.name}</option>)}
          </select>
        </label>
        {!iso && (
          <label>{T.allCats}
            <select value={cat} onChange={(e) => setCat(e.target.value)}>
              <option value="">{T.allCats}</option>
              {cats.map((c) => <option key={c} value={c}>{label("categories", c)}</option>)}
            </select>
          </label>
        )}
        <label>{T.allMeasures}
          <select value={measure} onChange={(e) => setMeasure(e.target.value)}>
            <option value="">{T.allMeasures}</option>
            {measures.map((m) => <option key={m} value={m}>{label("measures", m)}</option>)}
          </select>
        </label>
        <label>{T.colAge}
          <select value={fresh} onChange={(e) => setFresh(e.target.value as "" | Fresh)}>
            <option value="">{T.allFresh}</option>
            <option value="fresh">{T.fresh}</option><option value="aging">{T.aging}</option><option value="old">{T.old}</option>
          </select>
        </label>
        <button type="button" className="btn-solid" onClick={csv} disabled={!cShown}>{T.csv}</button>
        <span className="muted small" role="status">{num(cShown, 0)} {T.nRows}</span>
      </div>

      {iso && cres.loading && <p className="muted">{T.loading}</p>}
      {iso && cres.data && cres.data.alerts.length > 0 && (
        <div className="viz-card">
          <h3>{T.countryAlerts}: {cres.data.country.name}</h3>
          <ul className="small">{cres.data.alerts.map((a) => <li key={a.url}><a href={a.url} target="_blank" rel="noopener noreferrer">{a.title}</a></li>)}</ul>
        </div>
      )}

      <div className="table-scroll">
        {!iso ? (
          <table className="pulse-table">
            <thead><tr>
              {th("disease", T.colDisease)}{th("name", T.colIndicator)}{th("year", T.colYear)}{th("n", T.colN)}{th("median", T.colMedian)}
              <th>{T.colExtreme}</th>{th("age", T.colAge)}<th>{T.colSource}</th>
            </tr></thead>
            <tbody>
              {world.map((b) => (
                <tr key={b.code}>
                  <td>{b.disease_slug ? <Link href={`/${locale}/disease/${b.disease_slug}`}>{b.disease}</Link> : (b.disease ?? "—")}</td>
                  <td>{b.name}<span className="small muted"> · {label("measures", b.measure)}, {label("units", b.unit)}{b.age_standardized ? (fa ? "، استانداردشده با سن" : ", age-standardised") : ""}</span></td>
                  <td>{yr(b.year)}</td>
                  <td>{num(b.n, 0)}</td>
                  <td>{fmt(b.median)}{b.total !== null && <span className="small muted"> · Σ {fmt(b.total)}</span>}</td>
                  <td><Link href={`/${locale}/country/${b.extreme.iso3}`}>{b.extreme.name}</Link> <span className="small muted">{fmt(b.extreme.value)}</span></td>
                  <td><Badge f={b.freshness} text={`${yr(b.year)} · ${num(b.age_years, 0)} ${T.yearsAgo}`} /></td>
                  <td className="small">{b.source?.name ?? "—"}{b.source?.synthetic && <strong> ({T.synthetic})</strong>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : cres.data ? (
          <table className="pulse-table">
            <thead><tr><th>{T.colDisease}</th><th>{T.colIndicator}</th><th>{T.colYear}</th><th>{T.colValue}</th><th>{T.colRange}</th><th>{T.colRank}</th><th>{T.colWorld}</th><th>{T.colAge}</th></tr></thead>
            <tbody>
              {cRows.map((r: PulseCountryItem) => (
                <tr key={r.code}>
                  <td>{r.disease_slug ? <Link href={`/${locale}/disease/${r.disease_slug}`}>{r.disease}</Link> : (r.disease ?? "—")}</td>
                  <td>{r.name}<span className="small muted"> · {label("measures", r.measure)}, {label("units", r.unit)}</span></td>
                  <td>{yr(r.year)}</td>
                  <td><strong>{fmt(r.value)}</strong></td>
                  <td className="small">{r.low != null && r.high != null ? `${fmt(r.low)} – ${fmt(r.high)}` : "—"}</td>
                  <td>{num(r.rank_worst, 0)} {T.ofN} {num(r.of, 0)}</td>
                  <td>{fmt(r.median)}</td>
                  <td><Badge f={r.freshness} text={`${yr(r.year)} · ${num(r.age_years, 0)} ${T.yearsAgo}`} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        {cShown === 0 && !res.loading && !(iso && cres.loading) && <p className="muted">{T.none}</p>}
      </div>

      <h2>{T.sourcesTitle}</h2>
      <ul className="small pulse-jobs">
        {d.sources.map((j) => (
          <li key={j.job}>
            <code>{j.job}</code>{" "}
            {j.last_status === "failed" ? <strong className="pulse-bad">{T.failedRun}</strong> : <span>{T.ok}</span>}
            {" · "}{T.lastOk}: {j.age_hours === null ? T.never : `${num(Math.round(j.age_hours), 0)} ${T.hoursAgo}`}
            {j.last_ok_rows != null ? ` · ${num(j.last_ok_rows, 0)} ${T.nRows}` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}
