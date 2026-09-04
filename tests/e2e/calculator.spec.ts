import { test, expect } from '@playwright/test'

const costs = ['Land prep', 'Seed', 'Fertilizer', 'Pesticide', 'Labour', 'Irrigation', 'Transport', 'Storage']
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

test('restarts offline after the service worker is ready', async ({ page, context }) => {
  await page.goto('/')
  await page.waitForFunction(() => navigator.serviceWorker?.controller !== null)
  await page.reload()
  await context.setOffline(true)
  await page.reload()
  await expect(page.getByText('fieldmargin', { exact: true })).toBeVisible()
  await expect(page.getByText('calculator-only · works offline')).toBeVisible()
})
