"use client";

import { useEffect, useState } from "react";

type Params = Record<string, string | number | boolean | null | undefined>;

/** Free hosts sleep when idle (Render, Neon): the first request can fail with 502/503/504 or hang for ~1 minute.
 *  Retry those, and tell the UI (WarmupNote) when a request is slow so people wait instead of leaving. */
let pending = 0;
const listeners = new Set<(slow: boolean) => void>();
let slow = false;
function setSlow(v: boolean) { if (v !== slow) { slow = v; listeners.forEach((f) => f(v)); } }
export function onSlowChange(f: (slow: boolean) => void) { listeners.add(f); f(slow); return () => { listeners.delete(f); }; }

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function api<T>(path: string, params?: Params): Promise<T> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  const url = `/api${path}${qs.size ? `?${qs}` : ""}`;
  pending++;
  const timer = setTimeout(() => { if (pending > 0) setSlow(true); }, 4000);
  try {
    let res: Response | null = null;
    for (let attempt = 0; attempt < 4; attempt++) {
      try {
        res = await fetch(url);
        if (![502, 503, 504].includes(res.status)) break;
      } catch {
        res = null; // network error while the host wakes up
      }
      if (attempt < 3) await sleep(3000 * (attempt + 1));
    }
    if (!res) throw new Error("Network error: the server did not respond");
    if (!res.ok) {
      let detail = res.statusText;
      try {
        detail = (await res.json()).detail ?? detail;
      } catch {
        /* ignore */
      }
      throw new Error(`${res.status}: ${detail}`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
    pending--;
    if (pending === 0) setSlow(false);
  }
}

export interface ApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/** Fetch `path` (null = skip). Re-fetches whenever path or params change. */
export function useApi<T>(path: string | null, params?: Params): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({ data: null, error: null, loading: !!path });
  const key = path ? path + JSON.stringify(params ?? {}) : "";

  useEffect(() => {
    if (!path) {
      setState({ data: null, error: null, loading: false });
      return;
    }
    let cancelled = false;
    setState((s) => ({ data: s.data, error: null, loading: true }));
    api<T>(path, params)
      .then((data) => !cancelled && setState({ data, error: null, loading: false }))
      .catch((e: Error) => !cancelled && setState({ data: null, error: e.message, loading: false }));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return state;
}
