// Service Worker — portal Bigotes y Paticas (app).
//
// 8-nov-2026: el anterior NUNCA llegó a instalarse. Precargaba /icons/icon-192x192.png
// y /icons/icon-512x512.png, que no existen; `cache.addAll` falla entero si un archivo
// da 404, y la instalación se cae. Sin service worker el portal no es una app instalable
// de verdad (ni para Android ni para Play Store vía TWA). Y si se hubiera instalado,
// servía TODO "primero de caché", incluido el HTML: después de cada despliegue el cliente
// habría visto la versión vieja con JS nuevo. Ahora:
//   · páginas (navegación): primero red; sin red, la última copia o la página offline
//   · /_next/static (con hash, nunca cambian): primero caché
//   · imágenes: caché y se refresca por detrás
//   · /api: solo red
const VERSION = 'bp-portal-v3';
const ESTATICOS = `${VERSION}-static`;
const PAGINAS = `${VERSION}-paginas`;
const IMAGENES = `${VERSION}-img`;
const PRECARGA = ['/offline.html', '/manifest.json', '/icon-192.png', '/icon-512.png'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(ESTATICOS).then((c) => c.addAll(PRECARGA)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);

  if (url.pathname.startsWith('/api/')) return; // red, sin intermediarios

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok && url.origin === self.location.origin) {
            const copia = res.clone();
            caches.open(PAGINAS).then((c) => c.put(request, copia));
          }
          return res;
        })
        .catch(async () => (await caches.match(request)) || (await caches.match('/offline.html'))),
    );
    return;
  }

  if (url.origin === self.location.origin && url.pathname.startsWith('/_next/static/')) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request).then((res) => {
            if (res.ok) {
              const copia = res.clone();
              caches.open(ESTATICOS).then((c) => c.put(request, copia));
            }
            return res;
          }),
      ),
    );
    return;
  }

  if (request.destination === 'image') {
    event.respondWith(
      caches.open(IMAGENES).then(async (c) => {
        const hit = await c.match(request);
        const red = fetch(request)
          .then((res) => {
            if (res.ok || res.type === 'opaque') c.put(request, res.clone());
            return res;
          })
          .catch(() => hit);
        return hit || red;
      }),
    );
  }
});

// Notificaciones push
self.addEventListener('push', (event) => {
  const data = event.data?.json() ?? {};
  event.waitUntil(
    self.registration.showNotification(data.title || 'Bigotes y Paticas', {
      body: data.body || '',
      icon: '/icon-192.png',
      badge: '/icon-maskable-192.png',
      data: data.url ? { url: data.url } : undefined,
      vibrate: [100, 50, 100],
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/dashboard';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((ws) => {
      const abierta = ws.find((w) => new URL(w.url).origin === self.location.origin);
      if (abierta) return abierta.focus().then(() => abierta.navigate(url));
      return clients.openWindow(url);
    }),
  );
});
