import { test, expect } from '@playwright/test'

const costs = ['Land prep', 'Seed', 'Fertilizer', 'Pesticide', 'Labour', 'Irrigation', 'Transport', 'Storage']
async function completeCrop(page: import('@playwright/test').Page, crop: string, yieldValue: string, price: string) {
  await page.getByLabel('Crop being edited').selectOption({ label: crop })
  await page.getByLabel('Yield tonnes per hectare').fill(yieldValue)
  await page.getByLabel('Selling price NGN per kg').fill(price)
  for (const label of costs) await page.getByLabel(label).fill('0')
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
  await expect(page.getByText('Rice', { exact: true }).last()).toBeVisible()
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
})
