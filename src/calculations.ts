/** Pure, deterministic arithmetic for the calculator-only fallback. */
export type CropInput = { crop_id: string; name: string; form: string }
export const COST_CATEGORIES = ['land_preparation', 'seed', 'fertilizer', 'pesticide', 'labour', 'irrigation', 'transport', 'storage'] as const
export type CostCategory = typeof COST_CATEGORIES[number]
export type UserScenarioInput = { crop: CropInput; areaHa: number; yieldTPerHa: number; sellingPriceNgnPerKg: number; priceRangeNgnPerKg?: { low: number; high: number }; costsPerHa: Record<CostCategory, number> }
export type ScenarioResult = { crop: CropInput; productionKg: number; costPerHa: number; totalCost: number; revenue: number; profit: number; lowProfit?: number; highProfit?: number; inputSource: 'user'; assumptions: UserScenarioInput }
export type ScenarioError = { cropId: string; field?: string; message: string }
export type ScenarioBatch = { status: 'ready' | 'incomplete'; results: ScenarioResult[]; errors: ScenarioError[] }
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)
const positive = (v: unknown): v is number => finite(v) && v > 0
const nonNegative = (v: unknown): v is number => finite(v) && v >= 0
export function calculateScenario(input: UserScenarioInput): ScenarioResult | ScenarioError {
  const id = input.crop.crop_id
  if (!positive(input.areaHa)) return { cropId: id, field: 'areaHa', message: 'Area must be greater than zero.' }
  if (!positive(input.yieldTPerHa)) return { cropId: id, field: 'yieldTPerHa', message: 'Yield must be greater than zero.' }
  if (!positive(input.sellingPriceNgnPerKg)) return { cropId: id, field: 'sellingPriceNgnPerKg', message: 'Selling price must be greater than zero.' }
  for (const category of COST_CATEGORIES) if (!nonNegative(input.costsPerHa?.[category])) return { cropId: id, field: category, message: `${category.replace(/_/g, ' ')} is required and cannot be negative.` }
  const range = input.priceRangeNgnPerKg
  if (range && (!nonNegative(range.low) || !nonNegative(range.high) || range.low > input.sellingPriceNgnPerKg || input.sellingPriceNgnPerKg > range.high)) return { cropId: id, field: 'priceRangeNgnPerKg', message: 'Price range must satisfy 0 ≤ low ≤ point ≤ high.' }
  const costPerHa = COST_CATEGORIES.reduce((sum, category) => sum + input.costsPerHa[category], 0)
  const productionKg = input.yieldTPerHa * 1000 * input.areaHa; const totalCost = costPerHa * input.areaHa; const revenue = input.sellingPriceNgnPerKg * productionKg
  return { crop: input.crop, productionKg, costPerHa, totalCost, revenue, profit: revenue - totalCost, ...(range ? { lowProfit: range.low * productionKg - totalCost, highProfit: range.high * productionKg - totalCost } : {}), inputSource: 'user', assumptions: input }
}
export function calculateScenarios(inputs: UserScenarioInput[]): ScenarioBatch {
  const results: ScenarioResult[] = []; const errors: ScenarioError[] = []
  for (const input of inputs) { const result = calculateScenario(input); 'message' in result ? errors.push(result) : results.push(result) }
  results.sort((a, b) => b.profit - a.profit || a.crop.crop_id.localeCompare(b.crop.crop_id))
  if (inputs.length < 2) errors.unshift({ cropId: '', field: 'selectedCropIds', message: 'Select at least two crops to compare.' })
  return { status: errors.length === 0 ? 'ready' : 'incomplete', results, errors }
}
