// Production supplies an immutable, base-scoped cache configuration.
const { cacheName, cachePrefix, base, files } = self.__SEASONMARGIN_BUILD
// The app shipped as "Fieldmargin" until 2026-10-27. Caches written under the old
// prefix are no longer reused, so they are deleted here rather than left in storage.
const LEGACY_CACHE_PREFIX = 'fieldmargin-'
// Hosts such as Cloudflare Pages answer /index.html with a redirect to the
// directory URL. Browsers reject a redirected response for a navigation with
// ERR_FAILED, so rebuild any redirected response before it is cached.
async function unredirected(response) {
  if (!response.redirected) return response
  return new Response(await response.blob(), { status: response.status, statusText: response.statusText, headers: response.headers })
}
self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    try {
      const cache = await caches.open(cacheName)
      await Promise.all(files.map(async (url) => {
        const response = await fetch(new Request(url, { cache: 'reload' }))
        if (!response.ok) throw new Error(`Precache failed for ${url}: ${response.status}`)
        await cache.put(url, await unredirected(response))
      }))
    } catch (error) {
      await caches.delete(cacheName)
      throw error
    }
    // Activate immediately so a broken older worker cannot keep failing pages.
    await self.skipWaiting()
  })())
})
self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      const superseded = name.startsWith(cachePrefix) || name.startsWith(LEGACY_CACHE_PREFIX)
      if (superseded && name !== cacheName) await caches.delete(name)
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
  // Never serve a cached worker script. Browser update checks must reach the
  // deployment so an older installed worker cannot pin a stale app shell.
  if (url.pathname === `${base}sw.js`) return
  event.respondWith((async () => {
    const cache = await caches.open(cacheName)
    const key = request.mode === 'navigate' ? base : url.pathname
    const cached = await cache.match(key)
    if (cached) return unredirected(cached)
    const response = await fetch(request)
    // Crop photography is deliberately not precached. Cache it the first time it is
    // actually viewed, so the offline experience is unchanged after that visit.
    if (response.ok && url.pathname.includes('/crops/')) {
      // unredirected() is async: it must be awaited before cache.put, otherwise
      // cache.put receives a Promise and rejects, which fails the whole image request.
      try {
        await cache.put(key, await unredirected(response.clone()))
      } catch { /* a cache write must never break the image itself */ }
    }
    return response
  })())
})
