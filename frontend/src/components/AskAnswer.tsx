"use client";

import Link from "next/link";
import { ASK_TXT, type AskResp } from "@/lib/ask";
import { useLocale } from "@/lib/i18n";
import CiteDownload from "./CiteDownload";
import QualityBadge from "./QualityBadge";

export default function AskAnswer({ r, onPick }: { r: AskResp; onPick: (slug: string, name: string) => void }) {
  const { locale, num, label } = useLocale();
  const L = locale === "fa" ? "fa" : "en";
  const T = ASK_TXT[L];
  const I = r.interpretation;
  const crit = r.warnings.filter((w) => w.severity === "critical");
  const rest = r.warnings.filter((w) => w.severity !== "critical");
  return (
    <section className="answer" aria-live="polite">
      {(I.disease?.length || I.country) && (
        <p className="understood">
          <span className="muted">{T.understood}:</span>{" "}
          {I.disease?.length === 1 && <b>{I.disease[0].name}</b>}
          {I.country && <> · <b>{I.country.name}</b></>}
          {I.years && I.years.length > 0 && <> · <b dir="ltr">{I.years.length > 2 && I.years[I.years.length - 1] - I.years[0] === I.years.length - 1 ? `${I.years[0]}–${I.years[I.years.length - 1]}` : I.years.join(", ")}</b></>}
          {I.latest && <> · <b>{T.latest}</b></>}
        </p>
      )}
      {crit.map((w, i) => <p key={i} className="warn-crit" role="alert">{w.text}</p>)}

      {r.status === "out_of_scope" && <p className="warn-box">{r.message}</p>}
      {(r.status === "needs_clarification" || r.status === "no_data" || r.status === "not_understood") && <p className="notice">{r.message || T.none}</p>}
      {r.candidates.diseases && (
        <div>
          <p className="small muted">{T.pick}</p>
          <ul className="chips-pick">
            {r.candidates.diseases.map((d) => (
              <li key={d.slug}><button type="button" onClick={() => onPick(d.slug, d.name)}>{d.name}</button></li>
            ))}
          </ul>
        </div>
      )}

      {r.items.map((it, k) => {
        const cn = L === "fa" ? it.country.name_fa || it.country.name : it.country.name;
        const ind = L === "fa" && it.indicator.name_fa ? it.indicator.name_fa : it.indicator.name_en;
        return (
          <article key={k} className={`fact${it.year_exact ? "" : " inexact"}${it.indicator.source.is_synthetic ? " synthetic-fact" : ""}`}>
            <header>
              <h3>{ind}</h3>
              <span className="muted small">{cn} · <span dir="ltr">{it.year}</span>{!it.year_exact && <b className="warn-text"> · {T.year_ne} ({it.requested_year})</b>}</span>
            </header>
            <p className="fact-value">
              <span dir="ltr">{num(it.value)}</span>
              <small>{label("units", it.indicator.unit)}</small>
              {it.low != null && it.high != null && <small className="fact-range"> {T.range} <span dir="ltr">{num(it.low)} – {num(it.high)}</span></small>}
              <QualityBadge quality={it.quality} />
            </p>
            <p className="fact-sentence">{it.text}</p>
            <dl className="evidence">
              <div><dt>{T.source}</dt><dd>{it.indicator.source.url ? <a href={it.indicator.source.url} target="_blank" rel="noreferrer">{it.indicator.source.name}</a> : it.indicator.source.name}</dd></div>
              <div><dt>{T.license}</dt><dd>{it.indicator.source.license ?? "—"}</dd></div>
              <div><dt>{T.indicator}</dt><dd dir="ltr">{it.indicator.code}{it.indicator.external_code ? ` · ${it.indicator.external_code}` : ""}</dd></div>
              {it.retrieved_at && <div><dt>{T.retrieved}</dt><dd dir="ltr">{it.retrieved_at.slice(0, 10)}</dd></div>}
            </dl>
            {it.indicator.source.citation && <p className="small muted">{it.indicator.source.citation}</p>}
            <div className="fact-actions">
              <Link className="btn-quiet" href={it.links.disease}>{T.openPage}</Link>
              <CiteDownload csvPath={it.links.csv.replace(/^\/api/, "")} kind="indicator" keyId={it.links.cite.key} locale={L} />
            </div>
          </article>
        );
      })}

      {rest.length > 0 && <ul className="notes">{rest.map((w, i) => <li key={i}>{w.text}</li>)}</ul>}
      <details className="how"><summary>{T.how}</summary>
        <p className="small">{r.method}</p>
        <pre dir="ltr">{JSON.stringify({ status: r.status, ...r.interpretation }, null, 2)}</pre>
      </details>
    </section>
  );
}
