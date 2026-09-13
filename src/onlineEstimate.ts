export type OnlineEstimateRequest = {
  cropId: string
  state: string
  priceType?: 'retail' | 'wholesale'
}

export type OnlineEstimateSource = { title: string; url: string }

export type OnlineEstimate = {
  status: 'local' | 'web_fallback' | 'no_estimate'
  crop_id: string
  state: string
  price_type: 'retail' | 'wholesale'
  estimate_ngn_per_kg?: number
  low_ngn_per_kg?: number
  high_ngn_per_kg?: number
  observation_count?: number
  market_count?: number
  date_from?: string
  date_to?: string
  source_count?: number
  source?: { source_id: string; publisher: string; artifact: string }
  sources?: OnlineEstimateSource[]
  answer?: string
  confidence?: 'low' | 'medium' | 'high'
  warnings: string[]
}

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value)

function isEstimate(value: unknown): value is OnlineEstimate {
  if (!isRecord(value) || typeof value.status !== 'string' || typeof value.crop_id !== 'string' || typeof value.state !== 'string' || typeof value.price_type !== 'string' || !Array.isArray(value.warnings)) return false
  if (!['local', 'web_fallback', 'no_estimate'].includes(value.status) || !['retail', 'wholesale'].includes(value.price_type)) return false
  if (!value.warnings.every((warning) => typeof warning === 'string')) return false
  if (value.status !== 'no_estimate' && (typeof value.estimate_ngn_per_kg !== 'number' || !Number.isFinite(value.estimate_ngn_per_kg) || value.estimate_ngn_per_kg <= 0)) return false
  if (value.sources !== undefined && (!Array.isArray(value.sources) || !value.sources.every((source) => isRecord(source) && typeof source.title === 'string' && typeof source.url === 'string'))) return false
  return true
}

export async function requestOnlineEstimate(request: OnlineEstimateRequest, fetcher: typeof fetch = fetch, timeoutMs = 115_000): Promise<OnlineEstimate> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetcher('/api/price-research', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ ...request, priceType: request.priceType ?? 'retail', requestedAt: new Date().toISOString() }),
      signal: controller.signal,
    })
    const raw = await response.text()
    let payload: unknown
    try { payload = raw ? JSON.parse(raw) : undefined } catch { payload = undefined }
    if (!response.ok) throw new Error(isRecord(payload) && typeof payload.error === 'string' ? payload.error : 'Online lookup is unavailable right now. Enter a local price instead.')
    if (payload === undefined) throw new Error('Online lookup is unavailable right now. Enter a local price instead.')
    if (!isEstimate(payload)) throw new Error('The research service returned an invalid response.')
    return payload
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('The lookup took too long. You can enter a local price instead.')
    throw error instanceof Error ? error : new Error('The online lookup was unavailable.')
  } finally {
    window.clearTimeout(timer)
  }
}
