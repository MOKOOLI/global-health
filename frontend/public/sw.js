// Minimal offline support: cache the app shell and the two replay lessons so classrooms with poor internet still work.
// Bump VERSION to invalidate old caches. API responses are never cached (data must not go stale silently).
const VERSION = "gha-v1";
const SHELL = ["/fa", "/en", "/demo/covid-19-replay.json", "/demo/mpox-replay.json", "/countries-110m.json", "/icon.svg"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin || u.pathname.startsWith("/api/")) return;
  e.respondWith(
    fetch(e.request).then((r) => {
      if (r.ok && (u.pathname.startsWith("/_next/static/") || u.pathname.startsWith("/demo/") || SHELL.includes(u.pathname))) {
        const copy = r.clone(); caches.open(VERSION).then((c) => c.put(e.request, copy));
      }
      return r;
    }).catch(() => caches.match(e.request).then((m) => m || caches.match("/en")))
  );
});
