import { preview } from 'vite'

const server = await preview({
  preview: {
    host: '127.0.0.1',
    port: Number(process.env.E2E_PORT || 4173),
    strictPort: true,
  },
  plugins: [{
    // Mirror Cloudflare Pages, which redirects .../index.html to the directory
    // URL. The service worker must still serve navigations from that setup.
    name: 'fieldmargin-pages-index-redirect',
    configurePreviewServer(server) {
      server.middlewares.use((request, response, next) => {
        const [path, query] = request.url.split('?')
        if (!path.endsWith('/index.html')) return next()
        response.statusCode = 308
        response.setHeader('Location', path.slice(0, -'index.html'.length) + (query ? `?${query}` : ''))
        response.end()
      })
    },
  }],
})

let closing = false
const close = async () => {
  if (closing) return
  closing = true
  await server.httpServer?.close()
  process.exit(0)
}

process.once('SIGINT', close)
process.once('SIGTERM', close)
