/* 오프라인 지원: 앱 화면은 캐시에서 바로, 자료(data.enc)는 새것 우선·실패하면 마지막 것 */
const VERSION = "__BUILD__";
const SHELL = "shell-" + VERSION;
const DATA = "data-v1";
const FILES = ["./", "index.html", "app.js", "manifest.webmanifest",
  "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png", "icons/favicon.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(
    ks.filter((k) => k.startsWith("shell-") && k !== SHELL).map((k) => caches.delete(k))
  )).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.endsWith("/data.enc")) {
    e.respondWith(fetch(e.request).then((r) => {
      if (r.ok) { const copy = r.clone(); caches.open(DATA).then((c) => c.put("data.enc", copy)); }
      return r;
    }).catch(() => caches.open(DATA).then((c) => c.match("data.enc")).then((r) => r || Response.error())));
    return;
  }
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then((r) => r || fetch(e.request)));
});
