"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface Cite { apa: string; bibtex: string; notice: string }
const T = {
  fa: { csv: "دانلود CSV", svg: "دانلود نقشه (SVG)", cite: "ارجاع", apa: "APA", bib: "BibTeX", copy: "کپی", copied: "کپی شد", close: "بستن", err: "ساخت متن ارجاع ممکن نشد." },
  en: { csv: "Download CSV", svg: "Download map (SVG)", cite: "Cite", apa: "APA", bib: "BibTeX", copy: "Copy", copied: "Copied", close: "Close", err: "Could not build the citation." },
};

export default function CiteDownload({ csvPath, kind, keyId, locale, svgCaption }: {
  /** When set, a button downloads the map as an SVG with this caption (title, source, disclaimer) embedded. */
  svgCaption?: string;
  csvPath: string; kind: "indicator" | "surveillance"; keyId: string; locale: "fa" | "en";
}) {
  const t = T[locale];
  const [open, setOpen] = useState(false);
  const [c, setC] = useState<Cite | null>(null);
  const [err, setErr] = useState(false);
  const [done, setDone] = useState("");

  async function show() {
    setOpen(true); setErr(false);
    try { setC(await api<Cite>("/cite", { kind, key: keyId, lang: locale })); } catch { setErr(true); }
  }
  async function copy(label: string, text: string) {
    try { await navigator.clipboard.writeText(text); setDone(label); setTimeout(() => setDone(""), 1500); } catch { /* clipboard blocked */ }
  }
  return (
    <div className="cite-bar">
      <a className="btn-quiet" href={`/api${csvPath}`} download>{t.csv}</a>
      {svgCaption && (
        <button className="btn-quiet" type="button" onClick={() => {
          const el = document.querySelector<SVGSVGElement>(".map-wrap .map-svg"); if (!el) return;
          const c = el.cloneNode(true) as SVGSVGElement;
          const vb = (c.getAttribute("viewBox") ?? "0 0 960 500").split(/\s+/).map(Number);
          c.setAttribute("xmlns", "http://www.w3.org/2000/svg");
          c.setAttribute("viewBox", `0 0 ${vb[2]} ${vb[3] + 34}`);
          c.querySelectorAll("[style]").forEach((n) => { const f = getComputedStyle(n as Element).fill; if (f) (n as SVGElement).setAttribute("fill", f); n.removeAttribute("style"); });
          c.querySelectorAll(".country").forEach((n) => { n.setAttribute("stroke", "#fff"); n.setAttribute("stroke-width", "0.5"); });   // class CSS is not carried into a standalone file
          const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
          t.setAttribute("x", "8"); t.setAttribute("y", String(vb[3] + 22)); t.setAttribute("font-size", "11"); t.setAttribute("font-family", "sans-serif"); t.setAttribute("fill", "#333");
          t.textContent = svgCaption; c.appendChild(t);
          const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(c)], { type: "image/svg+xml" }));
          const a = document.createElement("a"); a.href = url; a.download = `${keyId}-map.svg`; a.click(); URL.revokeObjectURL(url);
        }}>{t.svg}</button>
      )}
      <button className="btn-quiet" onClick={open ? () => setOpen(false) : show} aria-expanded={open}>{open ? t.close : t.cite}</button>
      {open && (
        <div className="cite-panel" dir="ltr">
          {err && <p className="error">{t.err}</p>}
          {c && (
            <>
              {([[t.apa, c.apa], [t.bib, c.bibtex]] as const).map(([lab, txt]) => (
                <div key={lab}>
                  <div className="row-between"><strong>{lab}</strong>
                    <button className="linklike" onClick={() => copy(lab, txt)}>{done === lab ? t.copied : t.copy}</button></div>
                  <pre>{txt}</pre>
                </div>
              ))}
              <p className="small muted">{c.notice}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
