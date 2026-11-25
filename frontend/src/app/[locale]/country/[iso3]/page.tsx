"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import Briefing from "@/components/Briefing";
import { useApi } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import type { Alert, ProfileResp } from "@/lib/types";

export default function CountryPage() {
  const { iso3 } = useParams<{ iso3: string }>();
  const { locale, t } = useLocale();
  const [measure, setMeasure] = useState("");
  const { data, error, loading } = useApi<ProfileResp>(`/countries/${iso3}/profile`, { measure, lang: locale });
  const alerts = useApi<Alert[]>("/alerts", { country: iso3, limit: 10 });

  if (error) return <p className="shell pad error" role="alert">{t("error")}: {error}</p>;
  if (!data) return <p className="shell pad muted">{loading ? t("loading") : ""}</p>;

  return (
    <Briefing data={data} measure={measure} setMeasure={setMeasure} alertsSlot={
      <>
        <h2>{t("alerts")}</h2>
        {alerts.data && alerts.data.length === 0 && <p className="muted">{t("no_alerts")}</p>}
        <ul className="alerts">
          {(alerts.data ?? []).map((a) => (
            <li key={a.url}>
              <a href={a.url} target="_blank" rel="noreferrer">{a.title}</a>
              <span className="muted small">
                {a.source}{a.published_at ? ` · ${new Date(a.published_at).toLocaleDateString(locale === "fa" ? "fa-IR" : "en-GB")}` : ""}
              </span>
            </li>
          ))}
        </ul>
      </>
    } />
  );
}
