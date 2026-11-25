"use client";

import { useEffect, useState } from "react";
import { useLocale } from "@/lib/i18n";

export default function ThemeToggle() {
  const { locale } = useLocale();
  const [dark, setDark] = useState(false);
  useEffect(() => {
    let t: string | null = null;
    try { t = localStorage.getItem("theme"); } catch { /* storage blocked */ }
    const on = t ? t === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    setDark(on); document.documentElement.dataset.theme = on ? "dark" : "light";
  }, []);
  const fa = locale === "fa";
  return (
    <button type="button" className="theme-btn" aria-pressed={dark} title={fa ? "حالت تیره" : "Dark mode"}
      aria-label={fa ? "حالت تیره" : "Dark mode"}
      onClick={() => { const on = !dark; setDark(on); document.documentElement.dataset.theme = on ? "dark" : "light"; try { localStorage.setItem("theme", on ? "dark" : "light"); } catch { /* ignore */ } }}>
      {dark ? "☀" : "☾"}
    </button>
  );
}
