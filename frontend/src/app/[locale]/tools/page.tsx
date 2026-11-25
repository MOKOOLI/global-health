"use client";

import { useState } from "react";
import { useLocale } from "@/lib/i18n";
import CsvOverlay from "@/components/CsvOverlay";

const T = {
  fa: { title: "ابزارهای پژوهشی", intro: "محاسبه در سرور ما انجام می‌شود ولی هیچ داده‌ای ذخیره نمی‌شود. برای شمارش‌های کوچک (کمتر از ۱۰ مورد) بازه‌ی اطمینان معتبر نیست.",
    asrH: "نرخ استاندارد‌شده‌ی سنی (ASR)", asrP: "برای مقایسه‌ی دو کشور یا دو دوره با ساختار سنی متفاوت. موارد و جمعیت هر گروه سنی را وارد کنید.",
    std: "جمعیت استاندارد", segi: "Segi (۱۸ گروه)", who: "WHO 2000 (۲۱ گروه، وزن‌ها از حافظه؛ پیش از انتشار بررسی کنید)", per: "به ازای",
    age: "گروه سنی", cases: "موارد", pop: "جمعیت", calc: "محاسبه", asr: "نرخ استاندارد‌شده", crude: "نرخ خام", ci: "بازه‌ی اطمینان ۹۵٪",
    fill: "نمونه‌ی عددی (ساختگی) را پر کن", err: "خطا", method: "روش: استانداردسازی مستقیم با بازه‌ی Fay–Feuer (گاما). کران‌های کای‌دو با تقریب Wilson–Hilferty محاسبه می‌شوند." },
  en: { title: "Research tools", intro: "Calculation runs on our server but nothing is stored. With fewer than 10 cases in total the interval is unreliable.",
    asrH: "Age-standardised rate (ASR)", asrP: "Compare two countries or periods with different age structures. Enter cases and population for each age group.",
    std: "Standard population", segi: "Segi (18 groups)", who: "WHO 2000 (21 groups; weights entered from memory, verify before publishing)", per: "per",
    age: "Age group", cases: "Cases", pop: "Population", calc: "Calculate", asr: "Age-standardised rate", crude: "Crude rate", ci: "95% interval",
    fill: "Fill with example numbers (made up)", err: "Error", method: "Method: direct standardisation with a Fay–Feuer gamma interval. Chi-square bounds use the Wilson–Hilferty approximation." },
};
const SEGI = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85+"];
const WHO = [...SEGI.slice(0, 17), "85-89", "90-94", "95-99", "100+"];

interface Res { asr: number; crude: number; low: number; high: number | null; total_cases: number; warnings: string[]; per: number }

export default function ToolsPage() {
  const { locale } = useLocale();
  const t = T[locale === "fa" ? "fa" : "en"];
  const [std, setStd] = useState<"segi" | "who2000">("segi");
  const labels = std === "segi" ? SEGI : WHO;
  const [cases, setCases] = useState<string[]>(Array(21).fill(""));
  const [pop, setPop] = useState<string[]>(Array(21).fill(""));
  const [per, setPer] = useState(100000);
  const [res, setRes] = useState<Res | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fmt = (x: number) => x.toLocaleString(locale === "fa" ? "fa" : "en", { maximumFractionDigits: 2 });

  async function go() {
    setBusy(true); setErr(null); setRes(null);
    try {
      const groups = labels.map((_, i) => ({ cases: Number(cases[i] || 0), pop: Number(pop[i]) }));
      const r = await fetch("/api/tools/age-standardise", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ groups, standard: std, per }) });
      const j = await r.json();
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : "check the numbers (population must be > 0 in every group)");
      setRes(j);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  function example() {
    setCases(labels.map((_, i) => String(Math.round(2 + i * i * 0.6))));
    setPop(labels.map((_, i) => String(Math.round(900000 - i * 30000))));
  }

  return (
    <div className="shell page prose tools">
      <h1>{t.title}</h1>
      <p className="muted">{t.intro}</p>
      <h2>{t.asrH}</h2>
      <p>{t.asrP}</p>
      <div className="tool-row">
        <label>{t.std}{" "}
          <select value={std} onChange={(e) => { setStd(e.target.value as "segi" | "who2000"); setRes(null); }}>
            <option value="segi">{t.segi}</option><option value="who2000">{t.who}</option>
          </select></label>
        <label>{t.per}{" "}
          <select value={per} onChange={(e) => setPer(Number(e.target.value))}>
            {[1000, 10000, 100000, 1000000].map((v) => <option key={v} value={v}>{v.toLocaleString("en")}</option>)}
          </select></label>
        <button className="btn-quiet" type="button" onClick={example}>{t.fill}</button>
      </div>
      <table className="asr-table">
        <thead><tr><th>{t.age}</th><th>{t.cases}</th><th>{t.pop}</th></tr></thead>
        <tbody>
          {labels.map((l, i) => (
            <tr key={l}><th scope="row" dir="ltr">{l}</th>
              <td><input inputMode="numeric" aria-label={`${t.cases} ${l}`} value={cases[i]} onChange={(e) => setCases(cases.map((v, k) => k === i ? e.target.value : v))} /></td>
              <td><input inputMode="numeric" aria-label={`${t.pop} ${l}`} value={pop[i]} onChange={(e) => setPop(pop.map((v, k) => k === i ? e.target.value : v))} /></td></tr>
          ))}
        </tbody>
      </table>
      <p><button className="btn-solid asr-go" type="button" disabled={busy} onClick={go}>{t.calc}</button></p>
      {err && <p className="warn-box" role="alert">{t.err}: {err}</p>}
      {res && (
        <div className="asr-result" role="status">
          <p><strong>{t.asr}:</strong> {fmt(res.asr)} / {res.per.toLocaleString("en")}</p>
          <p><strong>{t.ci}:</strong> {fmt(res.low)} – {res.high === null ? "—" : fmt(res.high)}</p>
          <p className="muted"><strong>{t.crude}:</strong> {fmt(res.crude)}</p>
          {res.warnings.map((w) => <p key={w} className="warn-box">{w}</p>)}
          <p className="muted small">{t.method}</p>
        </div>
      )}
      <CsvOverlay />
    </div>
  );
}
