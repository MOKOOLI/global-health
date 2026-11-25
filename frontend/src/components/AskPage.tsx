"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { ASK_TXT, type AskResp } from "@/lib/ask";
import { useLocale } from "@/lib/i18n";
import AskAnswer from "./AskAnswer";
import AskBox from "./AskBox";

export default function AskPage() {
  const { locale } = useLocale();
  const L = locale === "fa" ? "fa" : "en";
  const T = ASK_TXT[L];
  const router = useRouter();
  const path = usePathname();
  const sp = useSearchParams();
  const [q, setQ] = useState(sp.get("q") ?? "");
  const [res, setRes] = useState<AskResp | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const last = useRef("");

  const run = useCallback(async (question: string) => {
    last.current = question; setBusy(true); setErr("");
    router.replace(`${path}?q=${encodeURIComponent(question)}`, { scroll: false });
    try { setRes(await api<AskResp>("/ask", { q: question, lang: L })); }
    catch (e) { setRes(null); setErr((e as Error).message); }
    finally { setBusy(false); }
  }, [L, path, router]);

  useEffect(() => { const s = sp.get("q"); if (s && s !== last.current) { setQ(s); run(s); } /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  return (
    <div className="shell page ask-page">
      <h1>{T.title}</h1>
      <p className="lead muted">{T.lead}</p>
      <AskBox locale={L} value={q} onChange={setQ} onSubmit={(s) => { setQ(s); run(s); }} busy={busy} autoFocus />
      <div className="ask-examples">
        <span className="small muted">{T.examples}:</span>
        {T.exs.map((x) => <button key={x} type="button" className="ex" onClick={() => { setQ(x); run(x); }}>{x}</button>)}
      </div>
      {err && <p className="error" role="alert">{err}</p>}
      {res && <AskAnswer r={res} onPick={(_slug, name) => { const nq = `${name} ${q}`; setQ(nq); run(nq); }} />}
    </div>
  );
}
