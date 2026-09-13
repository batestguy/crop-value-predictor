export type PriceType = 'retail' | 'wholesale' | 'modeled_estimate'
export type PriceSuggestion = {
  suggestion_id: string
  crop_id: string
  crop_form_id: string
  mapping_version: string
  canonical_market_id: string
  market_id: string
  market_name: string
  price_type: PriceType
  observation_date: string
  value_ngn_per_kg: number
  source: {
    source_id: string
    attribution: string
    raw_artifact_sha256: string
    commodity_id: string
    commodity_label: string
  }
  freshness: { snapshot_date: string; age_days: number; limit_days: number }
  provenance: { source_row_id?: string; source_row: number; normalized_from_unit: string }
}

export type PriceSuggestionsSnapshot = {
  schema_version: '1.1.0'
  snapshot_id: string
  mapping_version: string
  lane?: string
  warning?: string
  suggestions: PriceSuggestion[]
}

type Manifest = { snapshot_id?: unknown; modeled_estimate_snapshot_id?: unknown; stage_1_approved?: unknown; modeled_estimates_enabled?: unknown; artifacts?: unknown }

const base = import.meta.env.BASE_URL
const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value)
const isDate = (value: unknown) => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
const isSuggestion = (value: unknown): value is PriceSuggestion => {
  if (!isRecord(value) || typeof value.suggestion_id !== 'string' || typeof value.crop_id !== 'string' || typeof value.crop_form_id !== 'string' || typeof value.mapping_version !== 'string' || typeof value.canonical_market_id !== 'string' || typeof value.market_id !== 'string' || value.market_id !== value.canonical_market_id || typeof value.market_name !== 'string' || !['retail', 'wholesale', 'modeled_estimate'].includes(String(value.price_type)) || !isDate(value.observation_date) || typeof value.value_ngn_per_kg !== 'number' || !Number.isFinite(value.value_ngn_per_kg) || value.value_ngn_per_kg <= 0 || !isRecord(value.source) || !isRecord(value.freshness) || !isRecord(value.provenance)) return false
  return typeof value.source.source_id === 'string' && typeof value.source.attribution === 'string' && typeof value.source.raw_artifact_sha256 === 'string' && typeof value.source.commodity_id === 'string' && typeof value.source.commodity_label === 'string' && isDate(value.freshness.snapshot_date) && typeof value.freshness.age_days === 'number' && typeof value.freshness.limit_days === 'number' && value.freshness.age_days >= 0 && value.freshness.age_days <= value.freshness.limit_days && typeof value.provenance.source_row === 'number' && typeof value.provenance.normalized_from_unit === 'string'
}

export function validatePriceSuggestions(value: unknown, snapshotId: string): PriceSuggestionsSnapshot | undefined {
  if (!isRecord(value) || typeof value.schema_version !== 'string' || value.snapshot_id !== snapshotId || typeof value.mapping_version !== 'string' || !Array.isArray(value.suggestions) || !value.suggestions.every((suggestion) => isSuggestion(suggestion) && suggestion.mapping_version === value.mapping_version)) return undefined
  const keys = value.suggestions.map((item) => item.suggestion_id)
  if (new Set(keys).size !== keys.length) return undefined
  return value as PriceSuggestionsSnapshot
}

/** Loads only a reviewed, same-origin release artifact. Upstream APIs never run in the browser. */
export async function loadApprovedPriceSuggestions(fetcher: typeof fetch = fetch): Promise<PriceSuggestionsSnapshot | undefined> {
  try {
    const manifestResponse = await fetcher(`${base}data/v1/manifest.json`, { cache: 'no-store' })
    if (!manifestResponse.ok) return undefined
    const manifest: Manifest = await manifestResponse.json()
    if (!isRecord(manifest) || manifest.stage_1_approved !== true || typeof manifest.snapshot_id !== 'string' || !Array.isArray(manifest.artifacts) || !manifest.artifacts.includes('price_suggestions.json')) return undefined
    const response = await fetcher(`${base}data/v1/price_suggestions.json`, { cache: 'no-store' })
    if (!response.ok) return undefined
    return validatePriceSuggestions(await response.json(), manifest.snapshot_id)
  } catch {
    return undefined
  }
}

/** Loads the separately labelled modeled lane, never as Stage 1 approval. */
export async function loadModeledPriceSuggestions(fetcher: typeof fetch = fetch): Promise<PriceSuggestionsSnapshot | undefined> {
  try {
    const manifestResponse = await fetcher(`${base}data/v1/manifest.json`, { cache: 'no-store' })
    if (!manifestResponse.ok) return undefined
    const manifest: Manifest = await manifestResponse.json()
    if (!isRecord(manifest) || manifest.modeled_estimates_enabled !== true || typeof manifest.modeled_estimate_snapshot_id !== 'string' || !Array.isArray(manifest.artifacts) || !manifest.artifacts.includes('modeled_price_suggestions.json')) return undefined
    const response = await fetcher(`${base}data/v1/modeled_price_suggestions.json`, { cache: 'no-store' })
    if (!response.ok) return undefined
    const document: unknown = await response.json()
    if (!isRecord(document) || typeof document.snapshot_id !== 'string' || document.snapshot_id !== manifest.modeled_estimate_snapshot_id) return undefined
    const validated = validatePriceSuggestions(document, document.snapshot_id)
    return validated?.lane === 'world-bank-modeled-estimates' ? validated : undefined
  } catch {
    return undefined
  }
}

export const suggestionsForCrop = (snapshot: PriceSuggestionsSnapshot | undefined, cropId: string) => snapshot?.suggestions.filter((suggestion) => suggestion.crop_id === cropId) ?? []
