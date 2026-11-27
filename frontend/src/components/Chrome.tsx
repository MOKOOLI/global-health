"use client";

import { useEffect, useState } from "react";
import WarmupNote from "./WarmupNote";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLocale } from "@/lib/i18n";
import CommandPalette from "./CommandPalette";
import Header from "./Header";

export function SyntheticBanner() {
  const { meta, t } = useLocale();
  if (!meta?.has_synthetic) return null;
  return (
    <div className="synthetic" role="alert">
      <div className="shell">{t("synthetic_banner")}</div>
    </div>
  );
}

export function Footer() {
  const { meta, t, locale, num } = useLocale();
  return (
    <footer className="site-footer">
      <div className="shell">
        <p>{meta ? meta.disclaimer[locale] : ""}</p>
        <p className="muted small">
          {t("footer_license")}
          {meta && (
            <>
              {" · "}{t("counts")}: {num(meta.counts.countries, 0)} / {num(meta.counts.diseases, 0)} / {num(meta.counts.observations, 0)}
            </>
          )}
        </p>
      </div>
    </footer>
  );
}

function Utility() {
  const { locale } = useLocale();
  const [lite, setLite] = useState(false);
  useEffect(() => {
    try {
      const on = localStorage.getItem("lite") === "1";
      setLite(on);
      document.documentElement.dataset.lite = on ? "1" : "0";
    } catch { /* storage blocked: stay in normal mode */ }
    if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
      navigator.serviceWorker?.register("/sw.js").catch(() => undefined);
    }
  }, []);
  const fa = locale === "fa";
  return (
    <div className="utility no-print">
      <div className="shell">
        <button type="button" onClick={() => window.print()}>{fa ? "چاپ / PDF" : "Print / PDF"}</button>
        <button type="button" aria-pressed={lite} onClick={() => {
          const on = !lite; setLite(on); document.documentElement.dataset.lite = on ? "1" : "0";
          try { localStorage.setItem("lite", on ? "1" : "0"); } catch { /* ignore */ }
        }}>{fa ? "حالت سبک (اینترنت ضعیف)" : "Lite mode (slow connection)"}</button>
        <Link href={`/${locale}/trust`}>{fa ? "اعتماد، حریم خصوصی و گزارش خطا" : "Trust, privacy & report an error"}</Link>
      </div>
    </div>
  );
}

export default function Chrome({ children }: { children: React.ReactNode }) {
  const path = usePathname() ?? "";
  if (/^\/(fa|en)\/embed\//.test(path)) return <main>{children}</main>;
  return (
    <>
      <SyntheticBanner />
      <Header />
      <WarmupNote />
      <main>{children}</main>
      <CommandPalette />
      <Utility />
      <Footer />
    </>
  );
}
