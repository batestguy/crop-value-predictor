import { COST_CATEGORIES, type CostCategory } from './calculations'
import type { PriceType } from './priceSuggestions'
export type PriceOrigin = 'sourced_suggestion' | 'online_estimate' | 'user_entered'
export type SavedPriceSuggestion = { snapshotId: string; suggestionId: string; marketId: string; marketName: string; priceType: PriceType; observationDate: string; sourceAttribution: string }
export type SavedOnlineEstimate = { state: string; priceType: 'retail' | 'wholesale'; estimateNgnPerKg: number; lowNgnPerKg?: number; highNgnPerKg?: number; yieldTPerHa?: number; costsPerHa?: Partial<Record<CostCategory, number>>; status: 'local' | 'web_fallback'; confidence?: 'low' | 'medium' | 'high'; sourceCount?: number; observationCount?: number; marketCount?: number; dateFrom?: string; dateTo?: string; publisher?: string; sources?: { title: string; url: string }[]; retrievedAt: string }
export type SavedCustomCrop = { name: string; form: string }
export type SavedScenarioV1 = { schemaVersion: 1; savedAt: string; areaHa: string; selectedCropIds: string[]; customCrops?: Record<string, SavedCustomCrop>; inputsByCropId: Record<string, { yieldTPerHa: string; sellingPriceNgnPerKg: string; lowPriceNgnPerKg?: string; highPriceNgnPerKg?: string; costsPerHa: Record<CostCategory, string>; marketId?: string; priceOrigin?: PriceOrigin; priceSuggestion?: SavedPriceSuggestion; onlineEstimate?: SavedOnlineEstimate }> }
export const STORAGE_KEY = 'fieldmargin.saved-scenario.v1'
const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value)
const isStringRecord = (value: unknown): value is Record<string, string> => isRecord(value) && Object.values(value).every((item) => typeof item === 'string')
const isSavedCrop = (value: unknown): value is SavedScenarioV1['inputsByCropId'][string] => {
  if (!isRecord(value) || typeof value.yieldTPerHa !== 'string' || typeof value.sellingPriceNgnPerKg !== 'string' || !isStringRecord(value.costsPerHa)) return false
  const costs = value.costsPerHa
  if (COST_CATEGORIES.some((key) => typeof costs[key] !== 'string')) return false
  const suggestion = value.priceSuggestion
  const validSuggestion = suggestion === undefined || (isRecord(suggestion) && typeof suggestion.snapshotId === 'string' && typeof suggestion.suggestionId === 'string' && typeof suggestion.marketId === 'string' && typeof suggestion.marketName === 'string' && (suggestion.priceType === 'retail' || suggestion.priceType === 'wholesale' || suggestion.priceType === 'modeled_estimate') && typeof suggestion.observationDate === 'string' && typeof suggestion.sourceAttribution === 'string')
  const online = value.onlineEstimate
  const validCosts = online === undefined || (isRecord(online) && (online.costsPerHa === undefined || (isRecord(online.costsPerHa) && Object.entries(online.costsPerHa).every(([key, cost]) => COST_CATEGORIES.includes(key as CostCategory) && typeof cost === 'number' && Number.isFinite(cost) && cost >= 0))))
  const validOnline = online === undefined || (isRecord(online) && typeof online.state === 'string' && (online.priceType === 'retail' || online.priceType === 'wholesale') && typeof online.estimateNgnPerKg === 'number' && Number.isFinite(online.estimateNgnPerKg) && online.estimateNgnPerKg > 0 && (online.yieldTPerHa === undefined || (typeof online.yieldTPerHa === 'number' && Number.isFinite(online.yieldTPerHa) && online.yieldTPerHa > 0)) && validCosts && (online.status === 'local' || online.status === 'web_fallback') && typeof online.retrievedAt === 'string' && (online.sources === undefined || (Array.isArray(online.sources) && online.sources.every((source) => isRecord(source) && typeof source.title === 'string' && typeof source.url === 'string'))))
  return Object.keys(value).every((key) => ['yieldTPerHa', 'sellingPriceNgnPerKg', 'lowPriceNgnPerKg', 'highPriceNgnPerKg', 'costsPerHa', 'marketId', 'priceOrigin', 'priceSuggestion', 'onlineEstimate'].includes(key)) &&
    (value.lowPriceNgnPerKg === undefined || typeof value.lowPriceNgnPerKg === 'string') &&
    (value.highPriceNgnPerKg === undefined || typeof value.highPriceNgnPerKg === 'string') &&
    (value.marketId === undefined || typeof value.marketId === 'string') &&
    (value.priceOrigin === undefined || value.priceOrigin === 'sourced_suggestion' || value.priceOrigin === 'online_estimate' || value.priceOrigin === 'user_entered') && validSuggestion && validOnline
}
const isSavedDraft = (value: unknown): value is SavedScenarioV1 => isRecord(value) && value.schemaVersion === 1 && typeof value.savedAt === 'string' && typeof value.areaHa === 'string' && Array.isArray(value.selectedCropIds) && value.selectedCropIds.every((id) => typeof id === 'string') && isRecord(value.inputsByCropId) && Object.values(value.inputsByCropId).every(isSavedCrop)
const validCustomCrops = (value: unknown): value is Record<string, SavedCustomCrop> => isRecord(value) && Object.entries(value).every(([id, crop]) => /^custom:[a-z0-9-]{1,100}$/.test(id) && isRecord(crop) && typeof crop.name === 'string' && crop.name.trim().length > 0 && crop.name.length <= 80 && typeof crop.form === 'string' && crop.form.trim().length > 0 && crop.form.length <= 80)
export function loadDraft(): { draft?: SavedScenarioV1; recovered: boolean; storageUnavailable?: boolean } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { recovered: false }
    const value: unknown = JSON.parse(raw)
    if (!isSavedDraft(value) || (value.customCrops !== undefined && !validCustomCrops(value.customCrops))) throw new Error('invalid')
    const selectedCropIds = [...new Set(value.selectedCropIds)].filter((id) => Object.prototype.hasOwnProperty.call(value.inputsByCropId, id))
    return { draft: { ...value, selectedCropIds }, recovered: false }
  } catch {
    try { localStorage.removeItem(STORAGE_KEY) } catch { return { recovered: false, storageUnavailable: true } }
    return { recovered: true }
  }
}
export function saveDraft(draft: Omit<SavedScenarioV1, 'schemaVersion' | 'savedAt'>): boolean { try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...draft, schemaVersion: 1, savedAt: new Date().toISOString() })); return true } catch { return false } }
export function clearDraft(): boolean { try { localStorage.removeItem(STORAGE_KEY); return true } catch { return false } }
