/* ソラ先生 PWA Service Worker（手書き最小版）。docs/75 §2-1 のフォールバック採用理由:
 * ビルドツール(@serwist/next)を本環境で検証できないため、依存ゼロで確実に動く手書きSWにする。
 * 役割: アプリシェルのキャッシュ（オフラインでUIが開く）＋ Web Push 受信 → 通知表示。
 * 解析APIはキャッシュしない（オンライン必須。docs/73 §3.2 / AC-04）。
 */
/* v2: v1はRSCペイロードやdevチャンクまでCacheFirstで抱え込み、デプロイ後も
 * 古いUIを配り続けた。名前を上げて activate 時に汚染キャッシュを一掃する。 */
const CACHE = "sora-shell-v2";
const OFFLINE_URL = "/offline.html";
// 事前キャッシュする最小アセット（Nextのハッシュ付きJSは実行時にNetworkFirstで拾う）。
const PRECACHE = [OFFLINE_URL, "/manifest.webmanifest", "/icons/icon-192.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  // 解析・API はキャッシュしない（常にネットワーク。オフライン時はUI側で明示する）。
  if (url.pathname.startsWith("/api/")) return;

  // App Router のソフトナビゲーション（RSCペイロード）はキャッシュ厳禁。
  // mode は "navigate" にならないため、素通しにしないと古いページ内容が
  // デプロイ後も返り続ける（フルリロードでしか直らない）。
  if (url.searchParams.has("_rsc") || request.headers.get("RSC") === "1") return;

  // ページ遷移: NetworkFirst → 失敗時キャッシュ → 最後にオフラインページ。
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(request, copy));
          }
          return res;
        })
        .catch(() => caches.match(request).then((cached) => cached || caches.match(OFFLINE_URL)))
    );
    return;
  }

  // CacheFirst は「URLが変われば中身も変わる」不変アセットに限定する。
  // _next/static はコンテンツハッシュ付き、icons は実質不変。
  // それ以外の同一オリジンGETは素通し（ネットワーク直行）にして鮮度を守る。
  const isImmutable =
    url.origin === self.location.origin &&
    (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/"));
  if (isImmutable) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((res) => {
            if (res.ok) {
              const copy = res.clone();
              caches.open(CACHE).then((c) => c.put(request, copy));
            }
            return res;
          })
      )
    );
  }
});

// Web Push 受信 → 通知表示（docs/74 SCR-05）。
self.addEventListener("push", (event) => {
  let data = { title: "ソラ先生", body: "練習の時間だよ🎤", url: "/coach" };
  try {
    if (event.data) data = { ...data, ...event.data.json() };
  } catch (_e) {
    /* payloadが無い/壊れていても既定文言で出す */
  }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      data: { url: data.url },
    })
  );
});

// 通知クリック → 既存タブがあればフォーカス、なければ開く。
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/coach";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if (client.url.includes(target) && "focus" in client) return client.focus();
      }
      return self.clients.openWindow(target);
    })
  );
});
