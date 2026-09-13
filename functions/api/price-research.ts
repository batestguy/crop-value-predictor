interface Env {
  TAVILY_API_KEY?: string
}

type RequestBody = { cropId?: unknown; state?: unknown; priceType?: unknown; cropName?: unknown; cropForm?: unknown }
type SearchResult = { title?: unknown; url?: unknown }

const SEARCH_TERMS: Record<string, string> = {
  'maize-white': 'white maize',
  rice: 'rice',
  'rice-milled': 'milled rice',
  yam: 'yam',
  sorghum: 'sorghum',
  millet: 'millet',
  'gari-white': 'white gari',
  cassava: 'cassava',
}
const COST_CATEGORIES = ['land_preparation', 'seed', 'fertilizer', 'pesticide', 'labour', 'irrigation', 'transport', 'storage'] as const
const NIGERIAN_STATES = new Set([
  'abia', 'adamawa', 'akwa ibom', 'anambra', 'bauchi', 'bayelsa', 'benue',
  'borno', 'cross river', 'delta', 'ebonyi', 'edo', 'ekiti', 'enugu', 'gombe',
  'imo', 'jigawa', 'kaduna', 'kano', 'katsina', 'kebbi', 'kogi', 'kwara',
  'lagos', 'nasarawa', 'niger', 'ogun', 'ondo', 'osun', 'oyo', 'plateau',
  'rivers', 'sokoto', 'taraba', 'yobe', 'zamfara', 'federal capital territory',
  'fct',
])

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } })
const numberFrom = (value: string) => Number(value.replace(/,/g, ''))

function parseAnswer(answer: unknown, cropId: string, state: string, priceType: 'retail' | 'wholesale', results: unknown[], customCrop = false) {
  if (typeof answer !== 'string') return undefined
  const explicit = answer.match(/ESTIMATE_NGN_PER_KG\s*[:=]\s*(?:NGN|N)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)/i)
  const natural = answer.match(/(?:price|retail(?:s| price)?|estimate|average|cost|around)[^A-Za-z0-9]{0,100}(?:NGN|Naira|N)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:per|\/)\s*(kg|kilogram|metric\s+ton|tonne|ton)/i)
  const match = explicit ?? natural
  if (!match) return undefined
  const rawValue = numberFrom(match[1])
  if (!Number.isFinite(rawValue) || rawValue <= 0) return undefined
  const divisor = !explicit && natural && !['kg', 'kilogram'].includes(natural[2].toLowerCase()) ? 1000 : 1
  const marked = (name: string) => {
    const value = answer.match(new RegExp(`${name}\\s*[:=]\\s*(?:NGN|Naira|N)?\\s*([0-9][0-9,]*(?:\\.[0-9]+)?)`, 'i'))
    if (!value) return undefined
    const number = numberFrom(value[1])
    return Number.isFinite(number) && number > 0 ? number : undefined
  }
  const low = marked('LOW_NGN_PER_KG')
  const high = marked('HIGH_NGN_PER_KG')
  const yieldMatch = customCrop ? answer.match(/YIELD_T_PER_HA\s*[:=]\s*([0-9][0-9,]*(?:\.[0-9]+)?)/i) : null
  const yieldValue = yieldMatch ? numberFrom(yieldMatch[1]) : undefined
  const costs = customCrop ? Object.fromEntries(COST_CATEGORIES.flatMap((category) => {
    const match = answer.match(new RegExp(`COST_${category.toUpperCase()}_NGN_PER_HA\\s*[:=]\\s*(?:NGN|Naira|N)?\\s*([0-9][0-9,]*(?:\\.[0-9]+)?)`, 'i'))
    if (!match) return []
    const value = numberFrom(match[1])
    return Number.isFinite(value) && value >= 0 ? [[category, value]] : []
  })) : {}
  const sources = results.filter((item): item is SearchResult => {
    if (typeof item !== 'object' || item === null || typeof (item as SearchResult).url !== 'string') return false
    try { return new URL((item as SearchResult).url as string).protocol === 'https:' } catch { return false }
  }).map((item) => ({ title: typeof item.title === 'string' ? item.title : '', url: item.url as string })).slice(0, 8)
  return {
    status: 'web_fallback', estimate_ngn_per_kg: Math.round((rawValue / divisor) * 100) / 100,
    ...(low !== undefined ? { low_ngn_per_kg: Math.round((low / divisor) * 100) / 100 } : {}),
    ...(high !== undefined ? { high_ngn_per_kg: Math.round((high / divisor) * 100) / 100 } : {}),
    price_type: priceType, crop_id: cropId, state, confidence: 'low', source_count: sources.length,
    sources, ...(yieldValue && Number.isFinite(yieldValue) && yieldValue > 0 ? { yield_t_per_ha: Math.round(yieldValue * 100) / 100 } : {}), ...(Object.keys(costs).length ? { costs_per_ha: costs } : {}), warnings: ['No usable local observation was found; this is a web-grounded estimate and requires farmer confirmation.', ...(divisor === 1000 ? ['The provider returned a metric-ton value; it was converted to NGN/kg by dividing by 1,000.'] : [])],
  }
}

export async function onRequest(context: { request: Request; env: Env }) {
  if (context.request.method !== 'POST') return json({ error: 'Use POST for price research.' }, 405)
  if (!context.env.TAVILY_API_KEY) return json({ error: 'Online research is not configured on this deployment.' }, 503)
  let body: RequestBody
  try {
    const raw = await context.request.text()
    if (raw.length > 4_096) return json({ error: 'The research request was too large.' }, 413)
    body = JSON.parse(raw) as RequestBody
  } catch { return json({ error: 'The research request was not valid JSON.' }, 400) }
  const cropId = typeof body.cropId === 'string' ? body.cropId : ''
  const state = typeof body.state === 'string' ? body.state.trim() : ''
  const cropName = typeof body.cropName === 'string' ? body.cropName.trim() : ''
  const cropForm = typeof body.cropForm === 'string' ? body.cropForm.trim() : ''
  const priceType = body.priceType === 'wholesale' ? 'wholesale' : body.priceType === 'retail' ? 'retail' : ''
  const isCustomCrop = /^custom:[a-z0-9-]{1,100}$/.test(cropId)
  const validCustomDetails = /^[A-Za-z0-9][A-Za-z0-9 .()/'-]{1,79}$/.test(cropName) && /^[A-Za-z0-9][A-Za-z0-9 .()/'-]{1,79}$/.test(cropForm)
  if ((!SEARCH_TERMS[cropId] && !isCustomCrop) || (isCustomCrop && !validCustomDetails) || !NIGERIAN_STATES.has(state.toLowerCase()) || !priceType) return json({ error: 'Choose a supported crop, Nigerian state, and price type.' }, 400)

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 30_000)
  try {
    const query = isCustomCrop
      ? `${state} Nigeria ${cropName} ${cropForm} average farm yield tonnes per hectare ${priceType} market price NGN per kilogram production cost per hectare 2026. Use multiple recent sources and give a practical average, not a single quote. Return labelled values ESTIMATE_NGN_PER_KG, LOW_NGN_PER_KG, HIGH_NGN_PER_KG, YIELD_T_PER_HA, and any available COST_*_NGN_PER_HA values in NGN/kg and NGN/ha.`
      : `${state} ${SEARCH_TERMS[cropId]} market price Nigeria 2026 ${priceType} per kilogram`
    const response = await fetch('https://api.tavily.com/search', { method: 'POST', headers: { authorization: `Bearer ${context.env.TAVILY_API_KEY}`, 'content-type': 'application/json' }, body: JSON.stringify({ query, search_depth: 'basic', max_results: 8, include_answer: true, include_raw_content: false }), signal: controller.signal })
    if (!response.ok) return json({ error: 'The free research provider was unavailable.' }, 502)
    const payload = await response.json() as { answer?: unknown; results?: unknown[] }
    const result = parseAnswer(payload.answer, cropId, state, priceType, Array.isArray(payload.results) ? payload.results : [], isCustomCrop)
    return result ? json(result) : json({ status: 'no_estimate', crop_id: cropId, state, price_type: priceType, warnings: ['The web provider returned no parseable price evidence within the bounded request.'] })
  } catch (error) {
    return json({ error: error instanceof DOMException && error.name === 'AbortError' ? 'The lookup timed out. Enter a local price instead.' : 'The free research provider was unavailable.' }, 504)
  } finally { clearTimeout(timeout) }
}
