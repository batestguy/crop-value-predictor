const CACHE = 'fieldmargin-shell-v1'
const APP_SHELL = ['/', '/index.html', '/manifest.webmanifest', '/data/v1/manifest.json', '/data/v1/catalog.json', '/data/v1/defaults.json', '/data/v1/forecasts.json', '/data/v1/quality.json']

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request).then((response) => {
    const copy = response.clone()
    caches.open(CACHE).then((cache) => cache.put(event.request, copy))
    return response
  }).catch(() => caches.match('/index.html'))))
})
