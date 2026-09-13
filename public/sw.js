// Production supplies an immutable, base-scoped cache configuration.
const { cacheName, cachePrefix, base, files } = self.__FIELDMARGIN_BUILD
self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    try {
      const cache = await caches.open(cacheName)
      await cache.addAll(files.map((url) => new Request(url, { cache: 'reload' })))
    } catch (error) {
      await caches.delete(cacheName)
      throw error
    }
  })())
})
self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (name.startsWith(cachePrefix) && name !== cacheName) await caches.delete(name)
    }
    await self.clients.claim()
  })())
})
self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting()
})
self.addEventListener('fetch', (event) => {
  const request = event.request
  const url = new URL(request.url)
  if (request.method !== 'GET' || url.origin !== self.location.origin || !url.pathname.startsWith(base)) return
  event.respondWith((async () => {
    const cache = await caches.open(cacheName)
    const key = request.mode === 'navigate' ? `${base}index.html` : url.pathname
    const cached = await cache.match(key)
    return cached || fetch(request)
  })())
})
