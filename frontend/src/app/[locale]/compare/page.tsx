"use client";

import { useEffect, useState } from "react";
import TrendChart from "@/components/TrendChart";
import { useApi } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import type { CountryItem, DiseaseDetail, DiseaseItem, TrendResp } from "@/lib/types";

export default function ComparePage() {
  const { locale, t, num, label } = useLocale();
  const [slug, setSlug] = useState("");
  const [indicator, setIndicator] = useState("");
  const [isos, setIsos] = useState<string[]>(["IRN", "DEU", "IND"]);

  const diseases = useApi<DiseaseItem[]>("/diseases", { lang: locale, only_with_data: true });
  const countries = useApi<CountryItem[]>("/countries", { lang: locale });
  const detail = useApi<DiseaseDetail>(slug ? `/diseases/${slug}` : null, { lang: locale });

  useEffect(() => {
    if (!slug && diseases.data?.length) setSlug(diseases.data[0].slug);
  }, [slug, diseases.data]);
  useEffect(() => {
    if (detail.data) setIndicator(detail.data.default_indicator ?? "");
  }, [detail.data]);

  const trend = useApi<TrendResp>(indicator && isos.length ? `/indicators/${indicator}/trend` : null, {
    countries: isos.join(","), lang: locale,
  });

  const nameOf = (iso: string) => countries.data?.find((c) => c.iso3 === iso)?.name ?? iso;
  const unitLabel = trend.data ? label("units", trend.data.indicator.unit) : "";

  return (
    <div className="shell page">
      <h1>{t("compare_title")}</h1>
      <div className="controls">
        <label>
          <span>{t("pick_disease")}</span>
          <select value={slug} onChange={(e) => setSlug(e.target.value)}>
            {(diseases.data ?? []).map((d) => (<option key={d.slug} value={d.slug}>{d.name}</option>))}
          </select>
        </label>
        {detail.data && detail.data.indicators.length > 1 && (
          <label>
            <span>{t("indicator")}</span>
            <select value={indicator} onChange={(e) => setIndicator(e.target.value)}>
              {detail.data.indicators.map((i) => (<option key={i.code} value={i.code}>{i.name}</option>))}
            </select>
          </label>
        )}
        <label>
          <span>{t("add_country")}</span>
          <select
            value="" disabled={isos.length >= 6}
            onChange={(e) => e.target.value && setIsos((p) => (p.includes(e.target.value) ? p : [...p, e.target.value]))}
          >
            <option value="" />
            {(countries.data ?? []).map((c) => (<option key={c.iso3} value={c.iso3}>{c.name}</option>))}
          </select>
        </label>
      </div>

      <ul className="chips">
        {isos.map((iso) => (
          <li key={iso}>
            {nameOf(iso)}
            <button onClick={() => setIsos((p) => p.filter((x) => x !== iso))} aria-label={`${t("remove")} ${nameOf(iso)}`}>×</button>
          </li>
        ))}
      </ul>

      {trend.error && <p className="error" role="alert">{t("error")}: {trend.error}</p>}
      {trend.data && (
        <>
          <p className="muted small">{trend.data.indicator.name} · {t("source")}: {trend.data.indicator.source.name}</p>
          <TrendChart
            series={trend.data.series} unitLabel={unitLabel} forecastLabel={t("forecast_label")} height={380}
            fontFamily="Vazirmatn Variable, system-ui, sans-serif"
          />
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th /><th className="num">{t("latest")}</th><th className="num">{t("value")}</th></tr>
              </thead>
              <tbody>
                {trend.data.series.map((s) => {
                  const last = s.points[s.points.length - 1];
                  return (
                    <tr key={s.iso3}>
                      <td>{s.name}</td>
                      <td className="num">{last ? num(last.year, 0).replace(/[,٬]/g, "") : "—"}</td>
                      <td className="num">{last ? num(last.value) : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
