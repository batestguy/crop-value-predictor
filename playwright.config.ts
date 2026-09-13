import { defineConfig, devices } from '@playwright/test'

const basePath = process.env.E2E_BASE_PATH || '/'
if (!/^\/(?:[a-zA-Z0-9_-]+\/)*$/.test(basePath)) {
  throw new Error('E2E_BASE_PATH must be an absolute directory path ending in /')
}
const port = Number(process.env.E2E_PORT || 4173)
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('E2E_PORT must be a valid TCP port')
}

export default defineConfig({
  testDir: './tests/e2e',
  use: { baseURL: `http://127.0.0.1:${port}` },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
