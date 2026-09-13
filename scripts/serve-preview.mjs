import { preview } from 'vite'

const server = await preview({
  preview: {
    host: '127.0.0.1',
    port: Number(process.env.E2E_PORT || 4173),
    strictPort: true,
  },
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
