"use client";

import { Suspense } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import BubbleChart from "@/components/BubbleChart";
import SimilarityNet from "@/components/SimilarityNet";
import StoryMode from "@/components/StoryMode";
import { useLocale } from "@/lib/i18n";
import { VIZ_TXT } from "@/lib/viz";

const TABS = ["bubbles", "network", "story"] as const;

function Inner() {
  const { locale } = useLocale();
  const T = VIZ_TXT[locale];
  const sp = useSearchParams();
  const router = useRouter();
  const path = usePathname();
  const cur = (TABS as readonly string[]).includes(sp.get("v") ?? "") ? (sp.get("v") as (typeof TABS)[number]) : "bubbles";
  return (
    <div className="shell page viz">
      <h1>{T.title}</h1>
      <p className="muted">{T.lead}</p>
      <div className="viz-tabs" role="tablist" aria-label={T.title}>
        {TABS.map((k) => (
          <button key={k} type="button" role="tab" aria-selected={cur === k} className={cur === k ? "on" : ""}
            onClick={() => router.replace(`${path}?v=${k}`, { scroll: false })}>{T.tabs[k]}</button>
        ))}
      </div>
      {cur === "bubbles" && <BubbleChart />}
      {cur === "network" && <SimilarityNet />}
      {cur === "story" && <StoryMode />}
    </div>
  );
}

export default function VizPage() {
  return <Suspense fallback={null}><Inner /></Suspense>;
}
