"use client";

import Link from "next/link";
import CiteDownload from "./CiteDownload";
import { useEffect, useMemo, useState } from "react";
import { useApi } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import type { DiseaseDetail, DiseaseItem, MapResp, TrendResp } from "@/lib/types";
import Insights from "./Insights";
import QualityBadge from "./QualityBadge";
import TrendChart from "./TrendChart";
import WorldMap, { RAMP_BURDEN, RAMP_GOOD } from "./WorldMap";

interface Props {
  fixedDisease?: string;
  initialCountry?: string;
}

export default function Explorer({ fixedDisease, initialCountry }: Props) {
  const { locale, t, num, label, meta } = useLocale();
  const [slug, setSlug] = useState<string | null>(fixedDisease ?? null);
  const [indicator, setIndicator] = useState<string | null>(null);
  const [year, setYear] = useState<number | null>(null);
  const [sex, setSex] = useState("ALL");
  const [iso, setIso] = useState<string | null>(initialCountry ?? null);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");

  const diseases = useApi<DiseaseItem[]>("/diseases", { lang: locale, only_with_data: true });
  const list = diseases.data ?? [];

  useEffect(() => {
    if (!slug && list.length) setSlug(list[0].slug);
  }, [slug, list]);

  const detail = useApi<DiseaseDetail>(slug ? `/diseases/${slug}` : null, { lang: locale });
  const detailSlug = detail.data?.slug;
  const defaultInd = detail.data?.default_indicator ?? null;
  useEffect(() => {
    if (detailSlug) {
      setIndicator(defaultInd);
      setYear(null);
      setSex("ALL");
    }
  }, [detailSlug, defaultInd]);

  const map = useApi<MapResp>(indicator ? `/indicators/${indicator}/map` : null, { year, sex, lang: locale });
  const trend = useApi<TrendResp>(iso && indicator ? `/indicators/${indicator}/trend` : null, {
    countries: iso, sex, forecast: true, lang: locale,
  });

  const m = map.data;
  const ind = m?.indicator;
  const ramp = ind && !ind.higher_is_worse ? RAMP_GOOD : RAMP_BURDEN;
  const unitLabel = ind ? label("units", ind.unit) : "";
  const selectedRow = m?.data.find((r) => r.iso3 === iso) ?? null;
  const top = useMemo(() => [...(m?.data ?? [])].sort((a, b) => b.value - a.value).slice(0, 10), [m]);
  const maxTop = top[0]?.value || 1;

  const visible = list.filter((d) => {
    if (cat && d.category !== cat) return false;
    const s = q.trim().toLowerCase();
    return !s || d.name_en.toLowerCase().includes(s) || d.name_fa.includes(s) || (d.icd10 ?? "").toLowerCase().includes(s);
  });
  const cats = [...new Set(list.map((d) => d.category))];
  const grouped = cats.map((c) => ({ c, items: visible.filter((d) => d.category === c) })).filter((g) => g.items.length);

  if (diseases.loading && !diseases.data) return <p className="shell pad muted">{t("loading")}</p>;
  if (diseases.error) return <p className="shell pad error" role="alert">{t("error")}: {diseases.error}</p>;
  if (!list.length) {
    return (
      <div className="shell pad empty">
        <h2>{t("no_data")}</h2>
        <p>{t("no_data_hint")}</p>
      </div>
    );
  }

  const current = list.find((d) => d.slug === slug) ?? detail.data;
  const measureDef = ind && meta?.measures[ind.measure]?.[locale === "fa" ? "def_fa" : "def_en"];

  return (
    <div className="shell explorer">
      {!fixedDisease && (
        <aside className="picker" aria-label={t("pick_disease")}>
          <input
            type="search" value={q} onChange={(e) => setQ(e.target.value)}
            placeholder={t("filter_diseases")} aria-label={t("filter_diseases")}
          />
          <select value={cat} onChange={(e) => setCat(e.target.value)} aria-label={t("all_categories")}>
            <option value="">{t("all_categories")}</option>
            {cats.map((c) => (
              <option key={c} value={c}>{label("categories", c)}</option>
            ))}
          </select>
          <div className="disease-list">
            {grouped.map((g) => (
              <div key={g.c}>
                <h4>{label("categories", g.c)}</h4>
                <ul>
                  {g.items.map((d) => (
                    <li key={d.slug}>
                      <button
                        className={d.slug === slug ? "active" : ""}
                        aria-pressed={d.slug === slug}
                        onClick={() => { setSlug(d.slug); }}
                      >
                        {d.name}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </aside>
      )}

      <section className="stage">
        <div className="stage-head">
          <h1>{current?.name}</h1>
          {current && (
            <p className="muted small">
              {t("icd10")}: <bdi dir="ltr">{current.icd10 ?? "—"}</bdi>
              {current.notifiable ? ` · ${t("notifiable")}` : ""}
              {" · "}
              <Link href={`/${locale}/disease/${current.slug}`}>{t("open_disease")}</Link>
            </p>
          )}
          {current && (() => {
            const q = encodeURIComponent(current.slug.replace(/-/g, " "));   // English slug works in every authority's search
            const fa = locale === "fa";
            return (
              <p className="small muted ext-links no-print">
                {fa ? "راهنمای رسمی (جست‌وجو در سایت مرجع): " : "Official guidance (opens each authority's own search): "}
                <a href={`https://www.who.int/search?query=${q}`} target="_blank" rel="noopener noreferrer">WHO</a>{" · "}
                <a href={`https://search.cdc.gov/search/?query=${q}`} target="_blank" rel="noopener noreferrer">CDC</a>{" · "}
                <a href={`https://www.ecdc.europa.eu/en/search?s=${q}`} target="_blank" rel="noopener noreferrer">ECDC</a>{" · "}
                <a href={`https://pubmed.ncbi.nlm.nih.gov/?term=${q}`} target="_blank" rel="noopener noreferrer">PubMed</a>
              </p>
            );
          })()}
        </div>

        {detail.data && detail.data.indicators.length === 0 && <p className="muted">{t("no_data_for_disease")}</p>}

        {detail.data && detail.data.indicators.length > 0 && (
          <div className="controls">
            <label>
              <span>{t("indicator")}</span>
              <select value={indicator ?? ""} onChange={(e) => { setIndicator(e.target.value); setYear(null); }}>
                {detail.data.indicators.map((i) => (
                  <option key={i.code} value={i.code}>{i.name} — {i.source.code}</option>
                ))}
              </select>
            </label>
            {m && m.sexes.length > 1 && (
              <label>
                <span>{t("sex")}</span>
                <select value={sex} onChange={(e) => setSex(e.target.value)}>
                  {m.sexes.map((s) => (
                    <option key={s} value={s}>{label("sexes", s)}</option>
                  ))}
                </select>
              </label>
            )}
            {m && m.years.length > 1 && (
              <label className="year">
                <span>{t("year")}: <b>{num(m.year, 0).replace(/[,٬]/g, "")}</b></span>
                <input
                  type="range" min={m.years[0]} max={m.years[m.years.length - 1]} value={m.year}
                  onChange={(e) => setYear(Number(e.target.value))}
                />
              </label>
            )}
          </div>
        )}

        {map.error && <p className="error" role="alert">{t("error")}: {map.error}</p>}
        {m && ind && (
          <>
            <WorldMap
              rows={m.data} breaks={m.breaks} ramp={ramp} selected={iso} onSelect={setIso}
              format={(v) => num(v)} unitLabel={unitLabel} noDataLabel={t("no_value")}
              ariaLabel={`${ind.name}, ${m.year}`}
            />
            <p className="small muted source-line">
              {t("source")}: {ind.source.url ? <a href={ind.source.url} target="_blank" rel="noreferrer">{ind.source.name}</a> : ind.source.name}
              {" · "}{m.n}{m.n_total ? ` / ${m.n_total}` : ""} {locale === "fa" ? "کشور و سرزمین دارای داده" : "countries and territories with data"}
              {m.population_share != null && ` · ${locale === "fa" ? "پوشش جمعیت جهان" : "covers"} ${Math.round(m.population_share * 100)}%${locale === "fa" ? "" : " of world population"}`}
            </p>
            <CiteDownload csvPath={`/export/indicator/${ind.code}.csv`} kind="indicator" keyId={ind.code} locale={locale === "fa" ? "fa" : "en"}
              svgCaption={`${ind.name}, ${m.year}. ${locale === "fa" ? "منبع" : "Source"}: ${ind.source.name}. ${locale === "fa" ? "مرزها تقریبی‌اند؛ بیانگر هیچ دیدگاه حقوقی نیستند." : "Boundaries approximate; no opinion on legal status implied."} Global Health Atlas`} />
            {measureDef && (
              <p className="definition">
                <b>{label("measures", ind.measure)}:</b> {measureDef}
              </p>
            )}

            <h3>{t("top_countries")}</h3>
            <p className="small muted">{locale === "fa" ? "این فهرست رتبه‌بندی کیفیت نظام سلامت نیست: کشورهایی با ثبت و گزارش‌دهی بهتر معمولاً مقدار بالاتری نشان می‌دهند، و بسیاری از مقادیر برآورد مدل‌اند." : "This is not a ranking of health-system quality: countries with better registration and reporting often show higher values, and many values are model estimates."}</p>
            <ol className="bars">
              {top.map((r) => (
                <li key={r.iso3}>
                  <button onClick={() => setIso(r.iso3)} className={r.iso3 === iso ? "active" : ""}>
                    <span className="bar-name">{r.name}</span>
                    <span className="bar-track"><span style={{ inlineSize: `${(r.value / maxTop) * 100}%` }} /></span>
                    <span className="bar-val">{num(r.value)}</span>
                  </button>
                </li>
              ))}
            </ol>
          </>
        )}
      </section>

      <aside className="detail" aria-label={t("insights")}>
        {!iso && <p className="muted">{t("click_country")}</p>}
        {iso && ind && (
          <>
            <h2>{selectedRow?.name ?? iso}</h2>
            {selectedRow ? (
              <p className="big-value">
                <span>{num(selectedRow.value)}</span> <small>{unitLabel}</small>
              </p>
            ) : (
              <p className="muted">{t("no_value")}</p>
            )}
            {selectedRow && (
              <p className="small">
                <QualityBadge quality={selectedRow.quality} />{" "}
                {selectedRow.low != null && selectedRow.high != null && (
                  <span className="muted">[{num(selectedRow.low)}–{num(selectedRow.high)}]</span>
                )}
              </p>
            )}
            <p className="small"><Link href={`/${locale}/country/${iso}`}>{t("open_country")}</Link></p>

            {trend.data && trend.data.series.length > 0 && (
              <>
                <h3>{t("trend")}</h3>
                <TrendChart
                  series={trend.data.series} unitLabel={unitLabel} forecastLabel={t("forecast_label")}
                  fontFamily="Vazirmatn Variable, system-ui, sans-serif"
                />
              </>
            )}
            <Insights indicator={ind.code} iso3={iso} sex={sex} />
          </>
        )}
      </aside>
    </div>
  );
}
