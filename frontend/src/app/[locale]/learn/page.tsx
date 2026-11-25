"use client";

import { useEffect, useMemo, useState } from "react";
import ReplayPlayer from "@/components/ReplayPlayer";
import { useLocale } from "@/lib/i18n";
import { LEARN_TXT, LESSONS, TERMS } from "@/lib/learn";

export default function LearnPage() {
  const { locale } = useLocale();
  const L = locale === "fa" ? "fa" : "en";
  const T = LEARN_TXT[L];
  const [slug, setSlug] = useState<(typeof LESSONS)[number]["slug"]>("covid-19");
  const [q, setQ] = useState("");
  const [startWeek, setStartWeek] = useState<string | undefined>();
  useEffect(() => {          // share links: ?lesson=mpox&week=2022-06-06
    const p = new URLSearchParams(window.location.search);
    const l = LESSONS.find((x) => x.slug === p.get("lesson"));
    if (l) setSlug(l.slug);
    const w = p.get("week");
    if (w && /^\d{4}-\d{2}-\d{2}$/.test(w)) setStartWeek(w);
  }, []);
  const lesson = LESSONS.find((l) => l.slug === slug)!;
  const terms = useMemo(() => {
    const s = q.trim().toLowerCase();
    return TERMS.filter((t) => !s || (t.term.fa + t.term.en + t.def.fa + t.def.en).toLowerCase().includes(s));
  }, [q]);

  return (
    <div className="shell page learn">
      <header className="learn-head">
        <h1>{T.title}</h1>
        <p className="lead">{T.lead}</p>
      </header>

      <section aria-labelledby="lessons">
        <h2 id="lessons">{T.lessons}</h2>
        <div className="seg" role="tablist">
          {LESSONS.map((l) => (
            <button key={l.slug} role="tab" aria-selected={l.slug === slug} className={l.slug === slug ? "on" : ""}
              onClick={() => setSlug(l.slug)}>{l.title[L].split(":")[0].split("،")[0]}</button>
          ))}
        </div>
        <div className="lesson">
          <div className="lesson-side">
            <h3>{lesson.title[L]}</h3>
            <p>{lesson.blurb[L]}</p>
            <h4>{T.milestones}</h4>
            <ul className="miles">{lesson.milestones.map((m) => (
              <li key={m.date}><span dir="ltr">{m.date}</span>{m.text[L]}</li>))}</ul>
            <h4>{T.notice}</h4>
            <ul className="bullets">{lesson.notice.map((n, k) => <li key={k}>{n[L]}</li>)}</ul>
            <h4>{T.questions}</h4>
            <ul className="bullets">{lesson.questions.map((n, k) => <li key={k}>{n[L]}</li>)}</ul>
          </div>
          <ReplayPlayer key={slug + L + (startWeek ?? "")} share startWeek={startWeek} slug={slug} locale={L} caption={lesson.title[L]} from={lesson.window.from} to={lesson.window.to} step={lesson.window.step} />
        </div>
      </section>

      <section aria-labelledby="howto" className="howto">
        <h2 id="howto">{T.howto}</h2>
        <ol className="steps">{T.howtoItems.map((x, k) => <li key={k}>{x}</li>)}</ol>
        <p className="muted small">{T.cite}</p>
      </section>

      <section aria-labelledby="gloss">
        <div className="row-between">
          <h2 id="gloss">{T.glossary}</h2>
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={T.filter} aria-label={T.filter} className="gloss-search" />
        </div>
        {(["burden", "outbreak", "data"] as const).map((g) => {
          const items = terms.filter((t) => t.group === g);
          if (!items.length) return null;
          return (
            <div key={g}>
              <h3>{T.groups[g]}</h3>
              <dl className="gloss">
                {items.map((t) => (<div key={t.id} id={t.id}><dt>{t.term[L]}</dt><dd>{t.def[L]}</dd></div>))}
              </dl>
            </div>
          );
        })}
      </section>
    </div>
  );
}
