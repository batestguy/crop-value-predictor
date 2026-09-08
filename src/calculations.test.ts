import assert from 'node:assert/strict'
import test from 'node:test'
import { COST_CATEGORIES, calculateScenario, calculateScenarios, type UserScenarioInput } from './calculations.ts'
const crop = { crop_id: 'maize-white', name: 'White maize', form: 'dry grain' }
const input = (overrides: Partial<UserScenarioInput> = {}): UserScenarioInput => ({ crop, areaHa: 2, yieldTPerHa: 2, sellingPriceNgnPerKg: 800, costsPerHa: Object.fromEntries(COST_CATEGORIES.map((key) => [key, key === 'seed' ? 100 : 0])) as UserScenarioInput['costsPerHa'], ...overrides })
test('calculates area-scaled production, revenue, cost, and range profit', () => { const result = calculateScenario(input({ priceRangeNgnPerKg: { low: 700, high: 900 } })); assert.equal('message' in result, false); if ('message' in result) return; assert.deepEqual({ productionKg: result.productionKg, totalCost: result.totalCost, revenue: result.revenue, lowProfit: result.lowProfit, highProfit: result.highProfit }, { productionKg: 4000, totalCost: 200, revenue: 3200000, lowProfit: 2799800, highProfit: 3599800 }) })
test('requires every cost and rejects invalid inputs', () => { const result = calculateScenario({ ...input(), costsPerHa: { ...input().costsPerHa, storage: Number.NaN } }); assert.equal('message' in result, true); assert.equal(calculateScenarios([input()]).status, 'incomplete') })
test('ranking is deterministic on profit ties', () => { const second = input({ crop: { crop_id: 'rice', name: 'Rice', form: 'paddy' } }); assert.deepEqual(calculateScenarios([second, input()]).results.map((r) => r.crop.crop_id), ['maize-white', 'rice']) })
test('rejects an incomplete price range and negative costs', () => {
  const rangeResult = calculateScenario(input({ priceRangeNgnPerKg: { low: 900, high: 1000 } }))
  assert.equal('message' in rangeResult, true)
  const costResult = calculateScenario({ ...input(), costsPerHa: { ...input().costsPerHa, transport: -1 } })
  assert.equal('message' in costResult, true)
})
