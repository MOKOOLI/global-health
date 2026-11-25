"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import AskBox from "./AskBox";
import SignalStrip from "./SignalStrip";
import ReplayPlayer from "./ReplayPlayer";
import { useLocale } from "@/lib/i18n";

const C = {
  fa: {
    h1: "هر کشور، هر بیماری، در یک نگاه.",
    lead: "اطلس سلامت جهانی داده‌ی بروز، شیوع و مرگ‌ومیر را از منابع رسمی کنار هم می‌گذارد و هر هفته می‌گوید کجا چیزی غیرعادی است. برای پزشکان و دانشجویان، رایگان و دوزبانه.",
    a1: "کاوش در نقشه", a2: "درس بازپخش شیوع",
    replayTitle: "COVID-19، از ۲۰۲۰ تا ۲۰۲۳، هفته به هفته",
    replayNote: "هر هفته فقط با داده‌ی همان زمان محاسبه شده؛ همان کاری که امروز هم برای هشدار انجام می‌شود.",
    paths: [
      { href: "explore", t: "کاوش", d: "نقشه‌ی بروز، شیوع و مرگ‌ومیر برای بیش از ۱۲۰ بیماری و همه‌ی کشورها، با روند، پیش‌بینی و توضیح." },
      { href: "surveillance", t: "هشدار زودهنگام", d: "وضعیت هفتگی هر کشور: اندمیک، تحت نظر یا بالاتر از حد انتظار؛ الگوی چندکشوری و ماشین زمان." },
      { href: "learn", t: "آموزش", d: "واژه‌نامه، نحوه‌ی خواندن نمودار و بازپخش شیوع‌های واقعی برای کلاس و مطالعه." },
    ],
    trustTitle: "چرا می‌شود به آن اتکا کرد، و کجا نباید",
    trust: [
      ["هر عدد برچسب دارد", "گزارش‌شده، برآوردی یا مدل‌سازی‌شده؛ با منبع و مجوز."],
      ["هشدار، اعلام رسمی نیست", "اپیدمی و پاندمی را WHO و مراجع ملی اعلام می‌کنند. اینجا فقط سیگنال آماری است."],
      ["روش باز و محدودیت‌ها روشن", "همه‌ی فرمول‌ها و آزمون‌های گذشته‌نگر مستندند؛ پیش‌بینی‌ای که از روش ساده بهتر نیست، همین را می‌گوید."],
    ],
    notDiag: "این سایت ابزار تشخیص یا درمان نیست.",
  },
  en: {
    h1: "Every country, every disease, at a glance.",
    lead: "Global Health Atlas puts incidence, prevalence and mortality from official sources side by side, and each week shows where something looks unusual. For clinicians and students; free and bilingual.",
    a1: "Explore the map", a2: "Replay an outbreak",
    replayTitle: "COVID-19, 2020 to 2023, week by week",
    replayNote: "Each week is computed using only the data known at that time, exactly as the live warning works today.",
    paths: [
      { href: "explore", t: "Explore", d: "Maps of incidence, prevalence and mortality for over 120 diseases and every country, with trends, forecasts and plain-language findings." },
      { href: "surveillance", t: "Early warning", d: "Weekly status for each country: endemic, watch or above expected; multi-country patterns and a time machine." },
      { href: "learn", t: "Learn", d: "Glossary, how to read a chart, and replays of real outbreaks for class and self-study." },
    ],
    trustTitle: "Why you can rely on it, and where not to",
    trust: [
      ["Every number is labelled", "Reported, estimated or modelled, with its source and licence."],
      ["A signal is not a declaration", "Epidemics and pandemics are declared by WHO and national authorities. Here you only get a statistical signal."],
      ["Open method, stated limits", "Formulas and back-tests are documented; a forecast that does not beat a simple method says so."],
    ],
    notDiag: "This site is not a diagnostic or treatment tool.",
  },
};

export default function Landing() {
  const { locale, meta, num } = useLocale();
  const L = locale === "fa" ? "fa" : "en";
  const t = C[L];
  const router = useRouter();
  const [q, setQ] = useState("");
  return (
    <>
      <section className="hero">
        <div className="shell hero-grid">
          <div className="hero-copy">
            <h1>{t.h1}</h1>
            <p className="lead">{t.lead}</p>
            <div className="hero-ask">
              <AskBox locale={L} value={q} onChange={setQ} compact
                onSubmit={(s) => router.push(`/${locale}/ask?q=${encodeURIComponent(s)}`)} />
            </div>
            <div className="hero-actions">
              <Link className="btn-solid" href={`/${locale}/explore`}>{t.a1}</Link>
              <Link className="btn-ghost" href={`/${locale}/learn`}>{t.a2}</Link>
            </div>
            {meta && (
              <p className="hero-stats">
                {num(meta.counts.countries, 0)} {L === "fa" ? "کشور" : "countries"} · {num(meta.counts.diseases, 0)} {L === "fa" ? "بیماری" : "diseases"}
              </p>
            )}
          </div>
          <div className="hero-player">
            <h2 className="hero-replay-title">{t.replayTitle}</h2>
            <ReplayPlayer slug="covid-19" locale={L} autoplay dark caption={t.replayTitle} />
            <p className="small hero-note">{t.replayNote}</p>
          </div>
        </div>
      </section>

      <SignalStrip />

      <section className="shell paths" aria-label="sections">
        {t.paths.map((p) => (
          <Link key={p.href} href={`/${locale}/${p.href}`} className="path">
            <h2>{p.t}</h2>
            <p>{p.d}</p>
          </Link>
        ))}
      </section>

      <section className="shell trust">
        <h2>{t.trustTitle}</h2>
        <div className="trust-grid">
          {t.trust.map(([h, d]) => (<div key={h}><h3>{h}</h3><p>{d}</p></div>))}
        </div>
        <p className="muted small">{t.notDiag}</p>
      </section>
    </>
  );
}
