import { test, expect, devices } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const costs = ['Land prep', 'Seed', 'Fertilizer', 'Pesticide', 'Labour', 'Irrigation', 'Transport', 'Storage']
const { defaultBrowserType: _iphoneBrowser, ...iphone13 } = devices['iPhone 13']
const basePath = process.env.E2E_BASE_PATH || '/'
const serverOrigin = `http://127.0.0.1:${process.env.E2E_PORT || 4173}`

// This profile is applied after the initial local app load. The calculator is
// deliberately local-only, so the result measurement demonstrates that the
// final interaction remains responsive even when the connection is constrained.
const slow4G = {
  name: 'Slow 4G (emulated)',
  offline: false,
  latency: 150,
  downloadThroughput: Math.round(1.6 * 1024 * 1024 / 8),
  uploadThroughput: Math.round(750 * 1024 / 8),
}

async function expectNoCriticalAxeViolations(page: import('@playwright/test').Page) {
  const results = await new AxeBuilder({ page }).analyze()
  const critical = results.violations.filter((violation) => violation.impact === 'critical')
  expect(critical, `Critical axe violations: ${critical.map((violation) => violation.id).join(', ')}`).toEqual([])
}

async function emulateSlow4G(page: import('@playwright/test').Page) {
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('Network.enable')
  await cdp.send('Network.emulateNetworkConditions', slow4G)
  return cdp
}

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

test('uses an approved same-origin suggestion as an editable, persisted prefill', async ({ page }) => {
  const snapshotId = 'price-suggestions-test-2026-08-25'
  const snapshot = { schema_version: '1.1.0', snapshot_id: snapshotId, mapping_version: '1.0.0', suggestions: [{ suggestion_id: 'fews:maize:kano:retail:2026-07-15', crop_id: 'maize-white', crop_form_id: 'maize-grain-white', mapping_version: '1.0.0', canonical_market_id: 'kano', market_id: 'kano', market_name: 'Kano', price_type: 'retail', observation_date: '2026-07-15', value_ngn_per_kg: 650, source: { source_id: 'fews-net', attribution: 'FEWS NET test attribution', raw_artifact_sha256: 'a'.repeat(64), commodity_id: 'maize-white', commodity_label: 'Maize grain (white)' }, freshness: { snapshot_date: '2026-08-25', age_days: 41, limit_days: 75 }, provenance: { source_row: 1, normalized_from_unit: 'kg' } }] }
  snapshot.suggestions.push({ ...snapshot.suggestions[0], suggestion_id: 'fews:maize:kano:wholesale:2026-07-15', price_type: 'wholesale', value_ngn_per_kg: 600 })
  await page.addInitScript(({ id, priceSnapshot }) => {
    const nativeFetch = window.fetch.bind(window)
    window.fetch = async (input, init) => {
      const url = typeof input === 'string' ? input : input.url
      if (url.endsWith('/data/v1/manifest.json')) return new Response(JSON.stringify({ snapshot_id: id, stage_1_approved: true, artifacts: ['price_suggestions.json'] }), { status: 200, headers: { 'content-type': 'application/json' } })
      if (url.endsWith('/data/v1/price_suggestions.json')) return new Response(JSON.stringify(priceSnapshot), { status: 200, headers: { 'content-type': 'application/json' } })
      return nativeFetch(input, init)
    }
  }, { id: snapshotId, priceSnapshot: snapshot })
  await page.goto('/')
  await expect(page.getByLabel('Covered market')).toBeEnabled()
  await page.getByLabel('Covered market').selectOption('fews:maize:kano:wholesale:2026-07-15')
  await expect(page.getByLabel('Selling price NGN per kg')).toHaveValue('600')
  await page.getByLabel('Covered market').selectOption('fews:maize:kano:retail:2026-07-15')
  await expect(page.getByLabel('Selling price NGN per kg')).toHaveValue('650')
  await expect(page.getByText('Sourced suggestion · Kano · retail')).toBeVisible()
  await page.getByLabel('Selling price NGN per kg').fill('700')
  await expect(page.getByText('User-entered value', { exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByLabel('Selling price NGN per kg')).toHaveValue('700')
  await expect(page.getByText('User-entered value', { exact: true })).toBeVisible()
})

test('has no critical accessibility violations before and after a ranked result', async ({ page }) => {
  await page.goto('/')
  await expectNoCriticalAxeViolations(page)

  await page.getByLabel('Area in hectares').fill('1')
  await completeCrop(page, 'White maize', '2', '800')
  await completeCrop(page, 'Rice', '3', '1000')
  await expect(page.getByText('Highest point scenario', { exact: false })).toBeVisible()
  await expectNoCriticalAxeViolations(page)
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
  await expectNoCriticalAxeViolations(page)

  await page.evaluate(() => {
    const original = (window as Window & { fieldmarginStorage: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'> }).fieldmarginStorage
    Storage.prototype.getItem = original.getItem
    Storage.prototype.setItem = original.setItem
    Storage.prototype.removeItem = () => { throw new DOMException('blocked', 'SecurityError') }
  })
  await page.getByRole('button', { name: 'Clear saved draft' }).click()
  await expect(page.getByText(/could not clear the saved draft|screen was reset, but saved data may remain/i)).toBeVisible()
})

test('completes a two-crop comparison using the keyboard', async ({ page }) => {
  const typeInto = async (label: string, value: string) => {
    await page.getByLabel(label).focus()
    await page.keyboard.type(value)
  }

  await page.goto('/')
  await typeInto('Area in hectares', '1')
  await typeInto('Yield tonnes per hectare', '2')
  await typeInto('Selling price NGN per kg', '800')
  for (const label of costs) await typeInto(label, '0')

  await page.getByLabel('Crop being edited').focus()
  await page.keyboard.press('ArrowDown')
  await expect(page.getByLabel('Crop being edited')).toHaveValue('rice')
  await typeInto('Yield tonnes per hectare', '3')
  await typeInto('Selling price NGN per kg', '1000')
  for (const label of costs) await typeInto(label, '0')

  await expect(page.getByText('Highest point scenario', { exact: false })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Print report' })).toBeEnabled()
})

test('keeps the final-input-to-result time within five seconds on emulated Slow 4G', async ({ page }, testInfo) => {
  await page.goto('/')
  const cdp = await emulateSlow4G(page)
  try {
    await page.getByLabel('Area in hectares').fill('1')
    await completeCrop(page, 'White maize', '2', '800')
    await page.getByLabel('Crop being edited').selectOption({ label: 'Rice' })
    await page.getByLabel('Yield tonnes per hectare').fill('3')
    await page.getByLabel('Selling price NGN per kg').fill('1000')
    for (const label of costs.slice(0, -1)) await page.getByLabel(label).fill('0')

    const startedAt = performance.now()
    await page.getByLabel('Storage').fill('0')
    await expect(page.getByText('Highest point scenario', { exact: false })).toBeVisible()
    const elapsedMs = performance.now() - startedAt
    const evidence = {
      profile: slow4G,
      browser: await page.context().browser()!.version(),
      viewport: page.viewportSize(),
      finalInput: 'Storage cost for Rice',
      elapsedMs: Math.round(elapsedMs),
      thresholdMs: 5_000,
    }
    await testInfo.attach('emulated-first-result-evidence.json', {
      body: JSON.stringify(evidence, null, 2), contentType: 'application/json',
    })
    console.log(`First result evidence: ${JSON.stringify(evidence)}`)
    expect(elapsedMs).toBeLessThanOrEqual(5_000)
  } finally {
    await cdp.detach()
  }
})

test('does not make third-party requests after the calculator has loaded', async ({ page }) => {
  await page.addInitScript(() => {
    window.print = () => { document.documentElement.dataset.printCalled = 'true' }
  })
  await page.goto('/')
  const thirdPartyRequests: string[] = []
  page.on('request', (request) => {
    if (new URL(request.url()).origin !== serverOrigin) thirdPartyRequests.push(request.url())
  })

  await page.getByLabel('Area in hectares').fill('1')
  await completeCrop(page, 'White maize', '2', '800')
  await completeCrop(page, 'Rice', '3', '1000')
  await expect(page.getByRole('button', { name: 'Print report' })).toBeEnabled()
  await page.getByRole('button', { name: 'Print report' }).click()
  await expect.poll(() => page.locator('html').getAttribute('data-print-called')).toBe('true')
  await page.emulateMedia({ media: 'print' })
  await expect(page.locator('.print-report')).toBeVisible()
  expect(thirdPartyRequests).toEqual([])
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
    await expectNoCriticalAxeViolations(page)
  })
})
