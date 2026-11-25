"use client";

import { useLocale } from "@/lib/i18n";

export default function AboutPage() {
  const { locale, t, meta, num } = useLocale();
  return (
    <div className="shell page prose">
      <h1>{t("about_title")}</h1>
      <p>{meta?.disclaimer[locale]}</p>

      <h2>{t("how_title")}</h2>
      <p>{t("how_body")}</p>

      <h2>{t("definitions")}</h2>
      <dl>
        {Object.entries(meta?.measures ?? {}).map(([k, v]) => (
          <div key={k}>
            <dt>{v[locale]}</dt>
            <dd>{locale === "fa" ? v.def_fa : v.def_en}</dd>
          </div>
        ))}
      </dl>

      <h2>{t("quality_title")}</h2>
      <dl>
        {Object.entries(meta?.data_quality ?? {}).map(([k, v]) => (
          <div key={k}>
            <dt><span className={`q q-${k}`}>{v[locale]}</span></dt>
            <dd>{locale === "fa" ? v.note_fa : v.note_en}</dd>
          </div>
        ))}
      </dl>

      <h2>{t("limits_title")}</h2>
      <p>{t("limits_body")}</p>

      <h2>{t("sources_title")}</h2>
      <ul>
        {(meta?.sources ?? []).map((s) => (
          <li key={s.code}>
            {s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.name}</a> : s.name}
            {s.license ? <span className="muted small"> — {s.license}</span> : null}
            {s.citation ? <p className="muted small">{s.citation}</p> : null}
          </li>
        ))}
      </ul>

      {meta && (
        <p className="muted small">
          {t("counts")}: {num(meta.counts.countries, 0)} / {num(meta.counts.diseases, 0)} / {num(meta.counts.indicators, 0)} / {num(meta.counts.observations, 0)}
        </p>
      )}
    </div>
  );
}
