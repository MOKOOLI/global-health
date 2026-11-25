"use client";

import Link from "next/link";
import { useState } from "react";
import QualityBadge from "@/components/QualityBadge";
import { useLocale } from "@/lib/i18n";
import type { ProfileItem, ProfileResp } from "@/lib/types";

const T = {
  fa: { brief: "خلاصه‌ی بالینی کشور", print: "چاپ / PDF", copy: "کپی خلاصه متنی", copied: "کپی شد",
    cond: "بیماری با داده", higher: "بالاتر از میانه‌ی جهانی", highH: "بیشترین نسبت به میانه‌ی جهانی",
    highNote: "فقط شاخص‌های سرانه مقایسه می‌شوند. نسبت بالا یعنی «بیشتر از میانه‌ی کشورهای دارای داده»، نه لزوماً بار واقعی بیشتر؛ کشورهای کم‌گزارش‌دهی ممکن است کمتر دیده شوند.",
    mix: "ترکیب نوع داده", synth: "این صفحه شامل داده‌ی ساختگی (نمایشی) است و برای هیچ تصمیمی قابل‌استفاده نیست.",
    sources: "منابع و مجوزها", generated: "تاریخ تولید", ratio: "نسبت به میانه", median: "میانه‌ی جهانی",
    caveat: "برای آگاهی اپیدمیولوژیک است، نه تشخیص یا درمان. بسیاری از ارقام برآورد مدل‌اند.",
    none: "برای این کشور داده‌ای با این فیلتر بارگذاری نشده است.",
    reported: "گزارش‌شده", estimated: "برآوردی", modeled: "مدل‌سازی‌شده", synthetic: "ساختگی" },
  en: { brief: "Country clinical briefing", print: "Print / PDF", copy: "Copy text summary", copied: "Copied",
    cond: "conditions with data", higher: "above the global median", highH: "Highest relative to the global median",
    highNote: "Per-capita indicators only. A high ratio means “more than the median of countries with data”, not necessarily higher true burden; low-reporting countries can look better than they are.",
    mix: "Data-type mix", synth: "This page includes synthetic (demo) data and must not be used for any decision.",
    sources: "Sources and licences", generated: "Generated", ratio: "vs median", median: "global median",
    caveat: "For epidemiological orientation, not diagnosis or treatment. Many figures are model estimates.",
    none: "No data loaded for this country with this filter.",
    reported: "reported", estimated: "estimated", modeled: "modeled", synthetic: "synthetic" },
};

export default function Briefing({ data, measure, setMeasure, alertsSlot }: {
  data: ProfileResp; measure: string; setMeasure: (m: string) => void; alertsSlot: React.ReactNode;
}) {
  const { locale, t, num, label, meta } = useLocale();
  const L = locale === "fa" ? "fa" : "en";
  const x = T[L];
  const [note, setNote] = useState("");
  const c = data.country;
  const items = data.items;
  const top = items.filter((i) => (i.ratio_to_median ?? 0) > 1.0 && i.higher_is_worse).slice(0, 5);
  const above = items.filter((i) => (i.ratio_to_median ?? 0) > 1.5).length;
  const mix = items.reduce<Record<string, number>>((m, i) => ({ ...m, [i.quality]: (m[i.quality] ?? 0) + 1 }), {});
  const anySynth = items.some((i) => i.synthetic);
  const sources = Array.from(new Map(items.filter((i) => i.source).map((i) => [i.source!.code, i.source!])).values());
  const maxRatio = Math.max(2, ...items.map((i) => i.ratio_to_median ?? 0));
  const yr = (i: ProfileItem) => String(i.year);

  const text = () => [
    `${c.name} — ${x.brief} (${x.generated}: ${data.generated ?? ""})`,
    ...top.map((i) => `• ${i.disease.name}: ${label("measures", i.measure)} ${num(i.value)} ${label("units", i.unit)} (${yr(i)}), ×${num(i.ratio_to_median ?? 0)} ${x.median}${i.synthetic ? " [SYNTHETIC]" : ""}`),
    x.highNote, x.caveat, `${x.sources}: ${sources.map((s) => s.name + (s.license ? ` (${s.license})` : "")).join("; ")}`,
  ].join("\n");

  return (
    <div className="shell page briefing">
      <header className="brief-head">
        <div>
          <p className="small muted brief-kicker">{x.brief}</p>
          <h1>{c.name}</h1>
          <dl className="facts">
            {c.region && (<div><dt>{t("region")}</dt><dd>{c.region}</dd></div>)}
            {c.income_group && (<div><dt>{t("income")}</dt><dd>{c.income_group}</dd></div>)}
            {c.population != null && (<div><dt>{t("population")}</dt><dd>{num(c.population, 0)}</dd></div>)}
          </dl>
        </div>
        <div className="brief-actions no-print">
          <button className="btn-quiet" type="button" onClick={() => window.print()}>{x.print}</button>
          <button className="btn-quiet" type="button" onClick={() => navigator.clipboard?.writeText(text()).then(() => { setNote(x.copied); setTimeout(() => setNote(""), 1800); })}>{x.copy}</button>
          <span role="status" className="small muted">{note}</span>
        </div>
      </header>

      {anySynth && <p className="warn-box synth-warn" role="alert">{x.synth}</p>}

      <section className="brief-stats" aria-label="summary">
        <div><strong>{num(items.length, 0)}</strong><span>{x.cond}</span></div>
        <div><strong>{num(above, 0)}</strong><span>{x.higher} (×1.5)</span></div>
        <div className="mixcell"><span>{x.mix}</span>
          <div className="mixbar" role="img" aria-label={Object.entries(mix).map(([k, v]) => `${k} ${v}`).join(", ")}>
            {Object.entries(mix).map(([k, v]) => <i key={k} className={`mix-${k}`} style={{ flexGrow: v }} title={`${(x as Record<string, string>)[k] ?? k}: ${v}`} />)}
          </div>
          <span className="small muted">{Object.entries(mix).map(([k, v]) => `${(x as Record<string, string>)[k] ?? k} ${v}`).join(" · ")}</span>
        </div>
      </section>

      {top.length > 0 && (
        <section className="brief-top">
          <h2>{x.highH}</h2>
          <ol>
            {top.map((i) => (
              <li key={i.indicator}>
                <Link href={`/${locale}/disease/${i.disease.slug}?country=${c.iso3}`}>{i.disease.name}</Link>
                <bdi dir="ltr" className="ratio-chip">×{num(i.ratio_to_median ?? 0)}</bdi>
                <span className="small muted">{label("measures", i.measure)} · {yr(i)}</span>
              </li>
            ))}
          </ol>
          <p className="small muted">{x.highNote}</p>
        </section>
      )}

      <div className="split">
        <section>
          <div className="row-between no-print">
            <h2>{t("disease")}</h2>
            <select value={measure} onChange={(e) => setMeasure(e.target.value)} aria-label={t("measure")}>
              <option value="">{t("all_measures")}</option>
              {Object.keys(meta?.measures ?? {}).map((m) => (<option key={m} value={m}>{label("measures", m)}</option>))}
            </select>
          </div>
          {items.length === 0 ? <p className="muted">{x.none}</p> : (
            <div className="table-wrap">
              <table>
                <thead><tr>
                  <th>{t("disease")}</th><th>{t("measure")}</th><th className="num">{t("value")}</th>
                  <th>{x.ratio}</th><th className="num">{t("rank")}</th><th>{t("quality")}</th>
                </tr></thead>
                <tbody>
                  {items.map((it) => (
                    <tr key={it.indicator}>
                      <td><Link href={`/${locale}/disease/${it.disease.slug}?country=${c.iso3}`}>{it.disease.name}</Link></td>
                      <td>{label("measures", it.measure)} <span className="muted small">({label("units", it.unit)}, {yr(it)})</span></td>
                      <td className="num">{num(it.value)}</td>
                      <td className="ratio-cell">
                        {it.ratio_to_median != null ? (
                          <span className="ratio-bar" role="img" aria-label={`×${num(it.ratio_to_median)}`}>
                            <i style={{ inlineSize: `${Math.min(100, (it.ratio_to_median / maxRatio) * 100)}%` }} className={it.ratio_to_median > 1 ? "hi" : "lo"} />
                            <b className="mid" style={{ insetInlineStart: `${(1 / maxRatio) * 100}%` }} />
                            <bdi dir="ltr">×{num(it.ratio_to_median)}</bdi>
                          </span>
                        ) : "—"}
                      </td>
                      <td className="num">{it.rank != null ? `${num(it.rank, 0)}/${num(it.n, 0)}` : "—"}</td>
                      <td><QualityBadge quality={it.quality} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        <aside>{alertsSlot}</aside>
      </div>

      <footer className="brief-foot">
        <h2>{x.sources}</h2>
        <ul>{sources.map((s) => <li key={s.code}>{s.name}{s.license ? <span className="muted"> — {s.license}</span> : null}</li>)}</ul>
        <p className="small muted">{x.caveat} {x.generated}: {data.generated}</p>
      </footer>
    </div>
  );
}
