"use client";

import { Suspense, use } from "react";
import { useSearchParams } from "next/navigation";
import { useLocale } from "@/lib/i18n";
import ReplayPlayer from "@/components/ReplayPlayer";

/** Chrome-free page meant for <iframe>. Query: from, to, step, dark=1, week=YYYY-MM-DD */
function Inner({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const { locale } = useLocale();
  const q = useSearchParams();
  return (
    <div className="embed">
      <ReplayPlayer slug={slug} locale={locale} dark={q.get("dark") === "1"} from={q.get("from") ?? undefined}
        to={q.get("to") ?? undefined} step={Number(q.get("step")) || 3} startWeek={q.get("week") ?? undefined} />
      <p className="small muted embed-credit">
        <a href={`/${locale}/surveillance`} target="_blank" rel="noopener noreferrer">Global Health Atlas</a>
        {locale === "fa" ? " · سیگنال آماری، نه اعلام رسمی" : " · statistical signal, not an official declaration"}
      </p>
    </div>
  );
}

export default function Embed(props: { params: Promise<{ slug: string }> }) {
  return <Suspense fallback={null}><Inner {...props} /></Suspense>;
}
