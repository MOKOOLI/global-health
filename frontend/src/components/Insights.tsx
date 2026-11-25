"use client";

import { useState } from "react";
import { api, useApi } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import type { InsightsResp } from "@/lib/types";

export default function Insights({ indicator, iso3, sex }: { indicator: string; iso3: string; sex: string }) {
  const { locale, t } = useLocale();
  const { data, error, loading } = useApi<InsightsResp>("/insights", { indicator, country: iso3, sex, lang: locale });
  const [ai, setAi] = useState<InsightsResp["narrative"] | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  // reset the AI summary when the selection changes
  const key = `${indicator}|${iso3}|${sex}|${locale}`;
  const [aiKey, setAiKey] = useState(key);
  if (aiKey !== key) {
    setAiKey(key);
    setAi(null);
  }

  if (loading && !data) return <p className="muted">{t("loading")}</p>;
  if (error) return <p className="error" role="alert">{t("error")}: {error}</p>;
  if (!data) return null;

  async function summarise() {
    setAiLoading(true);
    try {
      const r = await api<InsightsResp>("/insights", { indicator, country: iso3, sex, lang: locale, narrate: true });
      setAi(r.narrative ?? null);
    } finally {
      setAiLoading(false);
    }
  }

  return (
    <section className="insights" aria-live="polite">
      <h3>{t("insights")}</h3>
      <p className="muted small">{t("insights_note")}</p>
      <ul className="findings">
        {data.findings.map((f, i) => (
          <li key={i} className={`finding sev-${f.severity}`}>
            {locale === "fa" ? f.text_fa : f.text_en}
          </li>
        ))}
      </ul>

      {ai ? (
        <div className="ai-box">
          <p>{ai.text}</p>
          <p className="small muted">{ai.ai_generated ? t("ai_label") : t("ai_fallback")}</p>
        </div>
      ) : (
        <button className="btn-quiet" onClick={summarise} disabled={aiLoading}>
          {aiLoading ? t("loading") : t("summarize_ai")}
        </button>
      )}
      <p className="small muted disclaimer">{data.disclaimer}</p>
    </section>
  );
}
