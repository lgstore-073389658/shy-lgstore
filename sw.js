/* 尚合雅 LG 月付美好計畫 - Service Worker
 * 策略：
 *  1. App Shell (index.html、manifest、icons) 安裝時預先快取
 *  2. 頁面導覽：網路優先，失敗時回退到快取的 index.html (離線可用)
 *  3. 同源靜態資源與 CDN (Tailwind / FontAwesome / Google Fonts)：Stale-While-Revalidate
 * 更新網站內容時，請把下方 VERSION 改成新的數字，使用者會收到「有新版本」提示。
 */
const VERSION = 'v1.3.0';
const SHELL_CACHE = `lg-shell-${VERSION}`;
const RUNTIME_CACHE = `lg-runtime-${VERSION}`;

const SHELL_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-192.png',
  './icons/icon-maskable-512.png',
  './icons/apple-touch-icon.png',
  './icons/favicon-32.png',
  './icons/favicon.ico',
  './icons/logo.png',
  './icons/logo-white.png',
  './icons/logo-mark.png'
];

// 這些外部網域的資源會在第一次載入後被快取，供離線使用
const CDN_HOSTS = [
  'cdn.tailwindcss.com',
  'cdnjs.cloudflare.com',
  'fonts.googleapis.com',
  'fonts.gstatic.com',
  'img.meepshop.com'            // 尚合雅官方商店的商品照片
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_ASSETS))
    // 不自動 skipWaiting：等使用者在頁面上按「立即更新」
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keep = [SHELL_CACHE, RUNTIME_CACHE];
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => !keep.includes(k)).map((k) => caches.delete(k)));
      if (self.registration.navigationPreload) {
        await self.registration.navigationPreload.enable();
      }
      await self.clients.claim();
    })()
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // 頁面導覽：網路優先 → 快取 → 離線回退 index.html
  if (req.mode === 'navigate') {
    event.respondWith(
      (async () => {
        try {
          const preload = await event.preloadResponse;
          const fresh = preload || (await fetch(req));
          const cache = await caches.open(SHELL_CACHE);
          cache.put('./index.html', fresh.clone());
          return fresh;
        } catch (err) {
          const cache = await caches.open(SHELL_CACHE);
          return (
            (await cache.match(req, { ignoreSearch: true })) ||
            (await cache.match('./index.html')) ||
            new Response('目前離線，且尚無快取內容。', {
              status: 503,
              headers: { 'Content-Type': 'text/plain; charset=utf-8' }
            })
          );
        }
      })()
    );
    return;
  }

  const sameOrigin = url.origin === self.location.origin;
  const isCdn = CDN_HOSTS.includes(url.hostname);
  if (!sameOrigin && !isCdn) return; // 其他外部請求 (如 LG 官網) 不攔截

  // Stale-While-Revalidate
  event.respondWith(
    (async () => {
      const cache = await caches.open(sameOrigin ? SHELL_CACHE : RUNTIME_CACHE);
      const cached = await cache.match(req);
      const network = fetch(req)
        .then((res) => {
          // 允許 opaque (no-cors CDN) 回應被快取
          if (res && (res.ok || res.type === 'opaque')) cache.put(req, res.clone());
          return res;
        })
        .catch(() => null);
      return cached || (await network) || Response.error();
    })()
  );
});
