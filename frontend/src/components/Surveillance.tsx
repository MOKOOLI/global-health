"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { useApi } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import { PHASE_COLOR, PHASE_ORDER, S_TXT, type BoardRow, type SeriesResp, type StatusResp, type SurvDisease, type SurvMeta } from "@/lib/surv";
import CiteDownload from "./CiteDownload";
import PhaseMap from "./PhaseMap";

const SurvChart = dynamic(() => import("./SurvChart"), { ssr: false, loading: () => <div style={{ height: 300 }} /> });

export default function Surveillance() {
  const { locale, num } = useLocale();
  const T = S_TXT[locale === "fa" ? "fa" : "en"];
  const L = locale === "fa" ? "fa" : "en";
  const meta = useApi<SurvMeta>("/surveillance/meta");
  const diseases = useApi<SurvDisease[]>("/surveillance/diseases", { lang: locale });
  const board = useApi<BoardRow[]>("/surveillance/board", { lang: locale });
  const [slug, setSlug] = useState<string | null>(null);
  const [week, setWeek] = useState<number | null>(null); // offset from newest, in weeks (<=0)
  const [iso, setIso] = useState<string | null>(null);

  useEffect(() => {
    if (slug || !diseases.data?.length) return;
    const want = new URLSearchParams(window.location.search).get("d");   // deep link from the home page strip
    setSlug(diseases.data.find((d) => d.slug === want)?.slug ?? diseases.data[0].slug);
  }, [diseases.data, slug]);
  const cur = diseases.data?.find((d) => d.slug === slug);
  const totalWeeks = useMemo(() => {
    if (!cur?.start) return 0;
    return Math.round((+new Date(cur.end) - +new Date(cur.start)) / (7 * 864e5));
  }, [cur]);
  const asOf = useMemo(() => {
    if (!cur || week === null || week === 0) return undefined;
    return new Date(+new Date(cur.end) + week * 7 * 864e5).toISOString().slice(0, 10);
  }, [cur, week]);

  const status = useApi<StatusResp>(slug ? `/surveillance/${slug}/status` : null, { as_of: asOf, lang: locale });
  const series = useApi<SeriesResp>(slug && iso ? `/surveillance/${slug}/series/${iso}` : null, { as_of: asOf, lang: locale });
  useEffect(() => { setIso(null); setWeek(null); }, [slug]);

  const st = status.data;
  const fmtN = (v: number | null | undefined) => (v == null ? "–" : num(v, v < 10 ? 1 : 0));
  const phaseName = (p: keyof SurvMeta["phases"]) => meta.data?.phases[p]?.[L] ?? p;
  const trendName = (t: string) => (T as Record<string, string>)[t] ?? t;
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    st?.rows.forEach((r) => { const k = r.stale ? "no_data" : r.phase; c[k] = (c[k] ?? 0) + 1; });
    return c;
  }, [st]);

  if (diseases.loading && !diseases.data) return <div className="shell page">{T.loading}</div>;
  if (!diseases.data?.length) return <div className="shell page"><h1>{T.title}</h1><p className="muted">{T.empty}</p></div>;

  const pat = st?.pattern;
  const behind = st?.weeks_behind_today ?? 0;
  return (
    <div className="shell page surv">
      <h1>{T.title}</h1>
      {meta.data && <p className="muted small">{meta.data.pattern_note[L]}</p>}

      <section aria-label={T.board} className="board">
        {board.data?.map((b) => (
          <button key={b.slug} className={`board-card${b.slug === slug ? " active" : ""}`} onClick={() => setSlug(b.slug)}>
            <strong>{b.name}</strong>
            <span className={`lvl lvl-${b.pattern.level}`}>{b.pattern.label[L]}</span>
            <span className="small muted">{b.top.slice(0, 3).map((t) => t.name).join("، ")}</span>
          </button>
        ))}
      </section>

      <div className="controls">
        <label>{T.disease}
          <select value={slug ?? ""} onChange={(e) => setSlug(e.target.value)}>
            {diseases.data.map((d) => <option key={d.slug} value={d.slug}>{d.name}</option>)}
          </select>
        </label>
        <label className="year">{T.timeMachine}: <b>{st?.as_of}</b>
          <input type="range" min={-Math.max(totalWeeks - 8, 0)} max={0} value={week ?? 0}
            onChange={(e) => setWeek(Number(e.target.value))} aria-label={T.timeMachine} />
          <span className="small muted">{T.timeNote}</span>
        </label>
      </div>

      {behind > 3 && !asOf && <p className="warn-box">{T.stale.replace("{n}", num(behind, 0))}</p>}

      {pat && (
        <section className={`pattern lvl-${pat.level}`} aria-live="polite">
          <h2>{pat.label[L]}</h2>
          <p className="small">
            {num(pat.n_epidemic, 0)} {T.epi} · {num(pat.n_regions, 0)} {T.regions} · {num(pat.n_reporting, 0)} {T.reporting}
          </p>
          <details><summary>{T.rules}</summary><p className="small">{meta.data?.pattern_rules[L]}</p></details>
        </section>
      )}

      <div className="surv-grid">
        <div>
          {st && <PhaseMap rows={st.rows} selected={iso} onSelect={setIso} ariaLabel={T.mapLabel}
            phaseLabel={(r) => `${r.stale ? phaseName("no_data") : phaseName(r.phase)} · ${trendName(r.trend)}`} />}
          <ul className="legend">
            {PHASE_ORDER.map((p) => counts[p] ? (
              <li key={p} title={meta.data?.phases[p]?.[locale === "fa" ? "desc_fa" : "desc_en"]}>
                <i style={{ background: PHASE_COLOR[p] }} /><span>{phaseName(p)} ({num(counts[p], 0)})</span>
              </li>) : null)}
          </ul>
        </div>

        <div className="surv-detail">
          {!iso && <p className="muted">{T.pick}</p>}
          {iso && series.data && (
            <>
              <h3>{series.data.name} <span className="muted small">{series.data.source.name}</span></h3>
              <p><b>{phaseName(series.data.assessment.phase)}</b> · {trendName(series.data.assessment.trend)}</p>
              <SurvChart points={series.data.points} upto={series.data.as_of} forecast={series.data.forecast}
                labels={{ observed: T.observed, expected: T.expected, upper: T.upper, forecast: T.forecast }} />
              {series.data.forecast && (
                <p className={`small ${series.data.forecast.reliable ? "muted" : "warn-text"}`}>
                  {series.data.forecast.reliable ? T.reliable : T.unreliable}
                </p>
              )}
              {series.data.smoothed && <p className="small muted">{T.batch}</p>}
              <CiteDownload csvPath={`/export/surveillance/${slug}/${iso}.csv`} kind="surveillance" keyId={slug ?? ""} locale={L} />
              <ul className="findings">
                {series.data.findings.map((f, i) => <li key={i} className={`sev-${f.severity}`}>{L === "fa" ? f.text_fa : f.text_en}</li>)}
              </ul>
            </>
          )}
          {iso && series.loading && !series.data && <p className="muted">{T.loading}</p>}
          {iso && series.error && <p className="error">{series.error}</p>}
        </div>
      </div>

      {st && (
        <>
          <h2>{T.table}</h2>
          <div className="table-scroll">
            <table className="data">
              <thead><tr><th>{T.countries}</th><th>{T.phase}</th><th>{T.trend}</th><th>{T.ratio}</th><th>{T.last}</th></tr></thead>
              <tbody>
                {st.rows.filter((r) => r.phase !== "no_data" || r.intro).slice(0, 60).map((r) => (
                  <tr key={r.iso3} onClick={() => setIso(r.iso3)} className={r.iso3 === iso ? "sel" : ""}>
                    <td><button className="linklike" onClick={() => setIso(r.iso3)}>{r.name}</button>{r.intro ? ` · ${T.intro}` : ""}</td>
                    <td><i className="dot" style={{ background: PHASE_COLOR[r.stale ? "no_data" : r.phase] }} />{r.stale ? phaseName("no_data") : phaseName(r.phase)}</td>
                    <td>{trendName(r.trend)}</td>
                    <td>{r.ratio == null ? "–" : `${fmtN(r.ratio)}×`}</td>
                    <td>{r.last_week}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
