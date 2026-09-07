import { test, expect, devices } from '@playwright/test'

const costs = ['Land prep', 'Seed', 'Fertilizer', 'Pesticide', 'Labour', 'Irrigation', 'Transport', 'Storage']
const { defaultBrowserType: _iphoneBrowser, ...iphone13 } = devices['iPhone 13']
const basePath = process.env.E2E_BASE_PATH || '/'
const serverOrigin = `http://127.0.0.1:${process.env.E2E_PORT || 4173}`
async function completeCrop(page: import('@playwright/test').Page, crop: string, yieldValue: string, price: string) {
  await page.getByLabel('Crop being edited').selectOption({ label: crop })
  await page.getByLabel('Yield tonnes per hectare').fill(yieldValue)
  await page.getByLabel('Selling price NGN per kg').fill(price)
  for (const label of costs) await page.getByLabel(label).fill('0')
}

async function completeRange(page: import('@playwright/test').Page, low: string, high: string) {
  await page.getByLabel('Low price').fill(low)
  await page.getByLabel('High price').fill(high)
}

async function waitForActiveServiceWorker(page: import('@playwright/test').Page, scopePath = '/') {
  await page.waitForFunction(async (path) => {
    const expectedScope = new URL(path, location.origin).href
    const registration = await navigator.serviceWorker.getRegistration(expectedScope)
    return registration?.scope === expectedScope
      && registration.active?.state === 'activated'
      && navigator.serviceWorker.controller?.scriptURL === registration.active.scriptURL
  }, scopePath)
}

test('suppresses ranking until two complete scenarios exist', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Print report' })).toBeDisabled()
  await expect(page.getByText('Ranking appears only when every selected crop is complete.')).toBeVisible()
  await completeCrop(page, 'White maize', '2', '800')
  await expect(page.getByRole('button', { name: 'Print report' })).toBeDisabled()
})

test('ranks complete scenarios and restores drafts after reload', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Area in hectares').fill('1')
  await completeCrop(page, 'White maize', '2', '800')
  await completeCrop(page, 'Rice', '3', '1000')
  await expect(page.getByRole('button', { name: 'Print report' })).toBeEnabled()
  await page.reload()
  await expect(page.getByLabel('Area in hectares')).toHaveValue('1')
  await expect(page.getByRole('button', { name: 'Print report' })).toBeEnabled()
})

test('clear saved draft returns to blank calculator', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Area in hectares').fill('4')
  await page.getByRole('button', { name: 'Clear saved draft' }).click()
  await expect(page.getByLabel('Area in hectares')).toHaveValue('')
  await expect.poll(() => page.evaluate(() => localStorage.getItem('fieldmargin.saved-scenario.v1'))).toBeNull()
})

test('preserves ranges and prints the same assumptions and results', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Area in hectares').fill('2')
  await completeCrop(page, 'White maize', '2', '800')
  await completeRange(page, '700', '900')
  await page.getByLabel('Land prep').fill('10')
  await page.getByLabel('Seed').fill('20')
  await completeCrop(page, 'Rice', '3', '1000')
  await expect(page.getByRole('button', { name: 'Print report' })).toBeEnabled()
  await page.emulateMedia({ media: 'print' })
  const report = page.locator('.print-report')
  await expect(report).toContainText('Area: 2 ha')
  await expect(report).toContainText('Yield: 2 t/ha')
  await expect(report).toContainText('Price range: ₦700–₦900/kg')
  await expect(report).toContainText('Land prep ₦10')
  await expect(report).toContainText('Seed ₦20')
  await expect(report).toContainText('Fertilizer ₦0')
  await expect(report).toContainText('Storage ₦0')
  await expect(report).toContainText('Disclaimer: These are user-entered scenarios')
})

test('recovers and removes malformed or unsupported saved drafts', async ({ page }) => {
  for (const value of ['{broken', JSON.stringify({ schemaVersion: 99 })]) {
    await page.addInitScript((draft) => localStorage.setItem('fieldmargin.saved-scenario.v1', draft), value)
    await page.goto('/')
    await expect(page.getByText('blank calculator was opened')).toBeVisible()
    await expect.poll(() => page.evaluate(() => localStorage.getItem('fieldmargin.saved-scenario.v1'))).toBeNull()
    await page.evaluate(() => localStorage.clear())
  }
})

test('opens a safe empty state when a saved draft has no active crops', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('fieldmargin.saved-scenario.v1', JSON.stringify({
    schemaVersion: 1, savedAt: new Date().toISOString(), areaHa: '', selectedCropIds: [], inputsByCropId: {},
  })))
  await page.goto('/')
  await expect(page.getByText('Select a crop above to enter assumptions.')).toBeVisible()
  await expect(page.getByLabel('Crop being edited')).toHaveCount(0)
})

test('drops unavailable saved crops and selects an available crop to edit', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('fieldmargin.saved-scenario.v1', JSON.stringify({
    schemaVersion: 1,
    savedAt: new Date().toISOString(),
    areaHa: '1',
    selectedCropIds: ['retired-crop', 'rice'],
    inputsByCropId: {
      'retired-crop': { yieldTPerHa: '2', sellingPriceNgnPerKg: '5', costsPerHa: { land_preparation: '0', seed: '0', fertilizer: '0', pesticide: '0', labour: '0', irrigation: '0', transport: '0', storage: '0' } },
      rice: { yieldTPerHa: '', sellingPriceNgnPerKg: '', costsPerHa: { land_preparation: '', seed: '', fertilizer: '', pesticide: '', labour: '', irrigation: '', transport: '', storage: '' } },
    },
  })))
  await page.goto('/')
  await expect(page.getByLabel('Crop being edited')).toHaveValue('rice')
  await expect(page.getByLabel('Crop being edited').locator('option')).toHaveCount(1)
})

test('warns when browser storage is blocked or a reset cannot clear it', async ({ page }) => {
  await page.addInitScript(() => {
    const original = Storage.prototype
    ;(window as Window & { fieldmarginStorage?: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'> }).fieldmarginStorage = {
      getItem: original.getItem, setItem: original.setItem, removeItem: original.removeItem,
    }
    Storage.prototype.getItem = () => { throw new DOMException('blocked', 'SecurityError') }
    Storage.prototype.removeItem = () => { throw new DOMException('blocked', 'SecurityError') }
    Storage.prototype.setItem = () => { throw new DOMException('blocked', 'SecurityError') }
  })
  await page.goto('/')
  await expect(page.getByText('This browser blocked local storage.')).toBeVisible()

  await page.evaluate(() => {
    const original = (window as Window & { fieldmarginStorage: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'> }).fieldmarginStorage
    Storage.prototype.getItem = original.getItem
    Storage.prototype.setItem = original.setItem
    Storage.prototype.removeItem = () => { throw new DOMException('blocked', 'SecurityError') }
  })
  await page.getByRole('button', { name: 'Clear saved draft' }).click()
  await expect(page.getByText(/could not clear the saved draft|screen was reset, but saved data may remain/i)).toBeVisible()
})

test('publishes a base-scoped manifest and clears only superseded Fieldmargin caches', async ({ page }) => {
  await page.goto('/')
  const manifest = await page.evaluate(async () => (await fetch(document.querySelector<HTMLLinkElement>('link[rel="manifest"]')!.href)).json())
  expect(manifest).toMatchObject({ id: '/', scope: '/', start_url: '/' })
  expect(manifest.icons[0].src).toBe('/fieldmargin-icon.svg')

  await waitForActiveServiceWorker(page)
  await page.evaluate(async () => {
    await (await caches.open('fieldmargin-%2F-obsolete')).put('/obsolete', new Response('old'))
    await (await caches.open('unrelated-cache')).put('/keep', new Response('keep'))
    await (await navigator.serviceWorker.getRegistration())?.unregister()
  })
  await page.reload()
  await waitForActiveServiceWorker(page)
  await expect.poll(() => page.evaluate(async () => !(await caches.keys()).includes('fieldmargin-%2F-obsolete'))).toBe(true)
  await expect.poll(() => page.evaluate(async () => (await caches.keys()).includes('unrelated-cache'))).toBe(true)
})

test('restarts offline after the service worker is ready', async ({ page, context }) => {
  await page.goto('/')
  await page.waitForFunction(() => navigator.serviceWorker?.controller !== null)
  await page.reload()
  await context.setOffline(true)
  await page.reload()
  await expect(page.getByText('fieldmargin', { exact: true })).toBeVisible()
  await expect(page.getByText('calculator-only · works offline')).toBeVisible()
})

test('supports a /fieldmargin/ base path with scoped PWA assets and offline reload', async ({ page, context }) => {
  test.skip(basePath !== '/fieldmargin/', 'Run with E2E_BASE_PATH=/fieldmargin/.')
  await page.goto('/fieldmargin/')

  const manifest = await page.evaluate(async () => (await fetch(document.querySelector<HTMLLinkElement>('link[rel="manifest"]')!.href)).json())
  expect(manifest).toMatchObject({ id: '/fieldmargin/', scope: '/fieldmargin/', start_url: '/fieldmargin/' })
  expect(manifest.icons[0].src).toBe('/fieldmargin/fieldmargin-icon.svg')

  await waitForActiveServiceWorker(page, '/fieldmargin/')
  await expect.poll(() => page.evaluate(async () => {
    const registration = await navigator.serviceWorker.getRegistration('/fieldmargin/')
    return {
      scope: registration?.scope,
      controlled: navigator.serviceWorker.controller?.scriptURL === registration?.active?.scriptURL,
    }
  })).toEqual({ scope: `${serverOrigin}/fieldmargin/`, controlled: true })

  await page.reload()
  await context.setOffline(true)
  try {
    await page.reload()
    await expect(page.getByText('fieldmargin', { exact: true })).toBeVisible()
  } finally {
    await context.setOffline(false)
  }
})

test.describe('emulated mobile', () => {
  test.use(iphone13)

  test('keeps the essential calculator flow usable', async ({ page }) => {
    await page.goto('/')
    await page.getByLabel('Area in hectares').fill('1')
    await completeCrop(page, 'White maize', '2', '800')
    await completeCrop(page, 'Rice', '3', '1000')
    await expect(page.getByRole('button', { name: 'Print report' })).toBeEnabled()
    await expect(page.getByText('Highest point scenario', { exact: false })).toBeVisible()
    await expect(page.getByLabel('Yield tonnes per hectare')).toBeVisible()
  })
})
