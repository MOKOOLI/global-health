"use client";

import { useEffect, useRef, useState } from "react";
import { ASK_TXT } from "@/lib/ask";

/* Minimal typing for the (vendor-prefixed) Web Speech API */
interface SR {
  lang: string; interimResults: boolean; continuous: boolean; maxAlternatives: number;
  start(): void; stop(): void; abort(): void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null; onend: (() => void) | null;
}
type SRCtor = new () => SR;

export default function AskBox({ locale, value, onChange, onSubmit, busy, autoFocus, compact }: {
  locale: "fa" | "en"; value: string; onChange: (v: string) => void; onSubmit: (q: string) => void;
  busy?: boolean; autoFocus?: boolean; compact?: boolean;
}) {
  const T = ASK_TXT[locale];
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceLang, setVoiceLang] = useState<"fa-IR" | "en-US">(locale === "fa" ? "fa-IR" : "en-US");
  const [err, setErr] = useState("");
  const rec = useRef<SR | null>(null);
  const finalText = useRef("");

  useEffect(() => {
    const w = window as unknown as { SpeechRecognition?: SRCtor; webkitSpeechRecognition?: SRCtor };
    setSupported(!!(w.SpeechRecognition || w.webkitSpeechRecognition));
    return () => rec.current?.abort();
  }, []);

  function start() {
    const w = window as unknown as { SpeechRecognition?: SRCtor; webkitSpeechRecognition?: SRCtor };
    const Ctor = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!Ctor) return;
    setErr(""); finalText.current = "";
    const r = new Ctor();
    r.lang = voiceLang; r.interimResults = true; r.continuous = false; r.maxAlternatives = 1;
    r.onresult = (e) => {
      let interim = "";
      let fin = "";
      for (let i = 0; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) fin += t; else interim += t;
      }
      if (fin) finalText.current = fin;
      onChange((fin || interim).trim());
    };
    r.onerror = (e) => { setErr(e.error === "not-allowed" || e.error === "service-not-allowed" ? T.micDenied : e.error); setListening(false); };
    r.onend = () => {
      setListening(false);
      const q = finalText.current.trim();
      if (q) onSubmit(q); // a finished utterance is submitted; the user can still edit and resubmit
    };
    rec.current = r;
    try { r.start(); setListening(true); } catch { setListening(false); }
  }
  const stop = () => rec.current?.stop();

  return (
    <form className={`askbox${compact ? " compact" : ""}`} onSubmit={(e) => { e.preventDefault(); if (value.trim()) onSubmit(value.trim()); }} role="search">
      <div className="ask-row">
        <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={T.placeholder}
          aria-label={T.placeholder} maxLength={300} autoFocus={autoFocus} lang={locale} />
        <button type="button" className={`ask-mic${listening ? " on" : ""}`} onClick={listening ? stop : start}
          disabled={!supported} aria-pressed={listening} aria-label={listening ? T.stop : T.mic} title={supported ? T.mic : T.unsupported}>
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
          </svg>
        </button>
        <button type="submit" className="ask-go" disabled={busy || !value.trim()}>{busy ? T.thinking : T.ask}</button>
      </div>
      {!compact && (
        <div className="ask-meta small">
          {supported && (
            <label>{T.voiceLang}{" "}
              <select value={voiceLang} onChange={(e) => setVoiceLang(e.target.value as "fa-IR" | "en-US")}>
                <option value="fa-IR">فارسی</option><option value="en-US">English</option>
              </select>
            </label>
          )}
          <span role="status" aria-live="polite">{listening ? T.listening : err || (!supported ? T.unsupported : "")}</span>
        </div>
      )}
      {!compact && <p className="small muted ask-note">{T.privacy} {supported ? T.micPrivacy : ""}</p>}
    </form>
  );
}
