import { COST_CATEGORIES, type CostCategory } from './calculations'
export type SavedScenarioV1 = { schemaVersion: 1; savedAt: string; areaHa: string; selectedCropIds: string[]; inputsByCropId: Record<string, { yieldTPerHa: string; sellingPriceNgnPerKg: string; lowPriceNgnPerKg?: string; highPriceNgnPerKg?: string; costsPerHa: Record<CostCategory, string> }> }
export const STORAGE_KEY = 'fieldmargin.saved-scenario.v1'
const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value)
const isStringRecord = (value: unknown): value is Record<string, string> => isRecord(value) && Object.values(value).every((item) => typeof item === 'string')
const isSavedCrop = (value: unknown): value is SavedScenarioV1['inputsByCropId'][string] => {
  if (!isRecord(value) || typeof value.yieldTPerHa !== 'string' || typeof value.sellingPriceNgnPerKg !== 'string' || !isStringRecord(value.costsPerHa)) return false
  const costs = value.costsPerHa
  if (COST_CATEGORIES.some((key) => typeof costs[key] !== 'string')) return false
  return Object.keys(value).every((key) => ['yieldTPerHa', 'sellingPriceNgnPerKg', 'lowPriceNgnPerKg', 'highPriceNgnPerKg', 'costsPerHa'].includes(key)) &&
    (value.lowPriceNgnPerKg === undefined || typeof value.lowPriceNgnPerKg === 'string') &&
    (value.highPriceNgnPerKg === undefined || typeof value.highPriceNgnPerKg === 'string')
}
const isSavedDraft = (value: unknown): value is SavedScenarioV1 => isRecord(value) && value.schemaVersion === 1 && typeof value.savedAt === 'string' && typeof value.areaHa === 'string' && Array.isArray(value.selectedCropIds) && value.selectedCropIds.every((id) => typeof id === 'string') && isRecord(value.inputsByCropId) && Object.values(value.inputsByCropId).every(isSavedCrop)
export function loadDraft(): { draft?: SavedScenarioV1; recovered: boolean; storageUnavailable?: boolean } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { recovered: false }
    const value: unknown = JSON.parse(raw)
    if (!isSavedDraft(value)) throw new Error('invalid')
    const selectedCropIds = [...new Set(value.selectedCropIds)].filter((id) => Object.prototype.hasOwnProperty.call(value.inputsByCropId, id))
    return { draft: { ...value, selectedCropIds }, recovered: false }
  } catch {
    try { localStorage.removeItem(STORAGE_KEY) } catch { return { recovered: false, storageUnavailable: true } }
    return { recovered: true }
  }
}
export function saveDraft(draft: Omit<SavedScenarioV1, 'schemaVersion' | 'savedAt'>): boolean { try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...draft, schemaVersion: 1, savedAt: new Date().toISOString() })); return true } catch { return false } }
export function clearDraft(): boolean { try { localStorage.removeItem(STORAGE_KEY); return true } catch { return false } }
