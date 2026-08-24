import { StrictMode, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

type Crop = { crop_id: string; name: string; form: string }
type Forecast = { crop_id: string; location_id?: string; price_type: string; point: number; lower_80: number; upper_80: number; target_month: string; status: string; validation: { wape: number } }
type YieldDefault = { crop_id: string; yield_t_per_ha: number; source_id: string; as_of: string }
type CostDefault = { crop_id: string; items: Record<string, number>; source_id: string; as_of: string; stale: boolean }

const crops: Crop[] = [
  { crop_id: 'maize-white', name: 'White maize', form: 'dry grain' },
  { crop_id: 'rice', name: 'Rice', form: 'paddy' },
  { crop_id: 'cassava', name: 'Cassava', form: 'fresh roots' },
  { crop_id: 'yam', name: 'Yam', form: 'fresh tuber' },
  { crop_id: 'sorghum', name: 'Sorghum', form: 'dry grain' },
]
const forecasts: Forecast[] = [
  { crop_id: 'maize-white', price_type: 'wholesale', point: 825, lower_80: 690, upper_80: 970, target_month: '2026-11', status: 'baseline', validation: { wape: .146 } },
  { crop_id: 'rice', price_type: 'wholesale', point: 1180, lower_80: 990, upper_80: 1430, target_month: '2026-11', status: 'baseline', validation: { wape: .179 } },
  { crop_id: 'cassava', price_type: 'farmgate', point: 310, lower_80: 240, upper_80: 390, target_month: '2026-11', status: 'baseline', validation: { wape: .201 } },
  { crop_id: 'yam', price_type: 'wholesale', point: 710, lower_80: 520, upper_80: 920, target_month: '2026-11', status: 'baseline', validation: { wape: .237 } },
  { crop_id: 'sorghum', price_type: 'wholesale', point: 625, lower_80: 520, upper_80: 760, target_month: '2026-11', status: 'baseline', validation: { wape: .158 } },
]
const yields: YieldDefault[] = [
  { crop_id: 'maize-white', yield_t_per_ha: 2.1, source_id: 'FAOSTAT QCL', as_of: '2024' },
  { crop_id: 'rice', yield_t_per_ha: 2.0, source_id: 'FAOSTAT QCL', as_of: '2024' },
  { crop_id: 'cassava', yield_t_per_ha: 8.2, source_id: 'FAOSTAT QCL', as_of: '2024' },
  { crop_id: 'yam', yield_t_per_ha: 9.0, source_id: 'FAOSTAT QCL', as_of: '2024' },
  { crop_id: 'sorghum', yield_t_per_ha: 1.3, source_id: 'FAOSTAT QCL', as_of: '2024' },
]
const costs: CostDefault[] = [
  { crop_id: 'maize-white', items: { land_preparation: 80000, seed: 45000, fertilizer: 120000, pesticide: 35000, labour: 90000, irrigation: 0, transport: 55000, storage: 25000 }, source_id: 'NBS NASS 2023', as_of: '2023', stale: true },
  { crop_id: 'rice', items: { land_preparation: 95000, seed: 55000, fertilizer: 145000, pesticide: 45000, labour: 120000, irrigation: 80000, transport: 65000, storage: 30000 }, source_id: 'NBS NASS 2023', as_of: '2023', stale: true },
  { crop_id: 'cassava', items: { land_preparation: 75000, seed: 70000, fertilizer: 85000, pesticide: 25000, labour: 110000, irrigation: 0, transport: 70000, storage: 20000 }, source_id: 'NBS NASS 2023', as_of: '2023', stale: true },
  { crop_id: 'yam', items: { land_preparation: 100000, seed: 150000, fertilizer: 90000, pesticide: 30000, labour: 130000, irrigation: 0, transport: 85000, storage: 35000 }, source_id: 'NBS NASS 2023', as_of: '2023', stale: true },
  { crop_id: 'sorghum', items: { land_preparation: 70000, seed: 40000, fertilizer: 95000, pesticide: 25000, labour: 80000, irrigation: 0, transport: 50000, storage: 22000 }, source_id: 'NBS NASS 2023', as_of: '2023', stale: true },
]
const labels: Record<string, string> = { land_preparation: 'Land prep', seed: 'Seed', fertilizer: 'Fertilizer', pesticide: 'Pesticide', labour: 'Labour', irrigation: 'Irrigation', transport: 'Transport', storage: 'Storage' }
const money = (value: number) => new Intl.NumberFormat('en-NG', { style: 'currency', currency: 'NGN', maximumFractionDigits: 0 }).format(value)

function App() {
  const [area, setArea] = useState(1)
  const [selected, setSelected] = useState<string[]>(['maize-white', 'rice', 'cassava'])
  const [location, setLocation] = useState('nigeria-national-median')
  const [yieldOverrides, setYieldOverrides] = useState<Record<string, string>>({})
  const [costOverrides, setCostOverrides] = useState<Record<string, Record<string, string>>>({})
  const [activeCrop, setActiveCrop] = useState('maize-white')

  const results = useMemo(() => selected.map((id) => {
    const crop = crops.find((item) => item.crop_id === id)!
    const forecast = forecasts.find((item) => item.crop_id === id && item.location_id === location) ?? forecasts.find((item) => item.crop_id === id)!
    const yieldDefault = yields.find((item) => item.crop_id === id)!
    const costDefault = costs.find((item) => item.crop_id === id)!
    const yieldPerHa = Number(yieldOverrides[id] || yieldDefault.yield_t_per_ha)
    const edited = costOverrides[id] || {}
    const totalPerHa = Object.entries(costDefault.items).reduce((sum, [key, value]) => sum + Number(edited[key] ?? value), 0)
    const totalCost = totalPerHa * area
    const kilograms = yieldPerHa * 1000 * area
    return { crop, forecast, yieldPerHa, totalCost, revenue: forecast.point * kilograms, low: forecast.lower_80 * kilograms - totalCost, high: forecast.upper_80 * kilograms - totalCost, profit: forecast.point * kilograms - totalCost, volatility: Math.round((forecast.upper_80 - forecast.lower_80) / forecast.point * 100), fallback: location !== 'nigeria-national-median' && !forecast.location_id }
  }).sort((a, b) => b.profit - a.profit), [area, location, selected, yieldOverrides, costOverrides])
  const winner = results[0]
  const toggleCrop = (id: string) => { setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]); if (!selected.includes(id)) setActiveCrop(id) }
  const updateCost = (cropId: string, key: string, value: string) => setCostOverrides((current) => ({ ...current, [cropId]: { ...current[cropId], [key]: value } }))

  return <div className="app-shell">
    <header className="topbar"><div className="wordmark"><span className="leaf-mark">✳</span><span>fieldmargin</span></div><div className="status-chip"><span className="pulse" /> cached pilot snapshot · 24 Aug 2026</div><button className="icon-button" aria-label="Open help">?</button></header>
    <main>
      <section className="hero"><div><p className="eyebrow">A calmer way to plan a season</p><h1>Know your margin<br /><em>before</em> you plant.</h1><p className="hero-copy">Compare a few crops with the numbers you can trust today — and keep working when the signal drops.</p></div><div className="hero-note"><span className="note-label">FIELD NOTE 01</span><strong>Profit is a scenario,<br />not a promise.</strong><span>Use your own yield, costs, and selling point before you decide.</span></div></section>
      <div className="notice"><span className="notice-icon">◒</span><span><strong>Pilot seed data.</strong> Price forecasts and cost defaults are illustrative until the source audit is complete.</span><button onClick={() => window.open('https://microdata.worldbank.org/catalog/4503', '_blank')}>View source →</button></div>
      <section className="workspace-grid">
        <aside className="control-panel">
          <div className="step-head"><span className="step-number">01</span><div><p className="eyebrow">Your field</p><h2>Set the scene</h2></div></div>
          <label className="field-label">Where will you sell?</label><select value={location} onChange={(event) => setLocation(event.target.value)}><option value="nigeria-national-median">Nigeria national median</option><option value="market-lagos">Lagos market basket</option><option value="market-kano">Kano market basket</option></select><p className="field-hint">Market coverage is limited to this pilot snapshot.</p>
          <label className="field-label">How much land?</label><div className="input-with-unit"><input type="number" min="0.1" step="0.1" value={area} onChange={(event) => setArea(Math.max(.1, Number(event.target.value)))} /><span>hectares</span></div>
          <div className="step-head crop-step"><span className="step-number">02</span><div><p className="eyebrow">Your shortlist</p><h2>Pick crops to compare</h2></div></div>
          <div className="crop-list">{crops.map((crop) => <label className={`crop-option ${selected.includes(crop.crop_id) ? 'is-selected' : ''}`} key={crop.crop_id}><input type="checkbox" checked={selected.includes(crop.crop_id)} onChange={() => toggleCrop(crop.crop_id)} /><span className="crop-dot" /><span><strong>{crop.name}</strong><small>{crop.form}</small></span><span className="checkmark">✓</span></label>)}</div>
          <p className="selection-hint">{selected.length} selected · compare at least 2</p>
        </aside>
        <section className="results-panel">
          <div className="results-head"><div><p className="eyebrow">03 / Decision view</p><h2>Your field margin</h2></div><button className="outline-button" onClick={() => window.print()}>Print report <span>↗</span></button></div>
          {winner && <div className="recommendation"><div className="recommendation-tag">RECOMMENDED SCENARIO</div><div className="recommendation-main"><div><h3>{winner.crop.name}</h3><p>{money(winner.profit)} estimated net profit on {area} ha</p></div><div className="recommendation-orbit"><span>₦</span></div></div><div className="recommendation-meta"><span>3-month price · {winner.forecast.price_type}{winner.fallback ? ' · national fallback' : ''}</span><span>range {money(winner.low)} – {money(winner.high)}</span></div></div>}
          <div className="result-toolbar"><div><h3>Compare your shortlist</h3><p>Point estimate, using cached forecast and your editable costs.</p></div><span className="horizon-pill">NOV 2026 <span>⌄</span></span></div>
          <div className="comparison-list">{results.map((result, index) => <article className={`result-card ${index === 0 ? 'top-result' : ''}`} key={result.crop.crop_id}><div className="rank">{String(index + 1).padStart(2, '0')}</div><div className="result-name"><strong>{result.crop.name}</strong><span>{result.forecast.price_type} · ±{result.volatility}% range</span></div><div className="result-numbers"><span><small>NET PROFIT</small><strong>{money(result.profit)}</strong></span><span><small>REVENUE</small><strong>{money(result.revenue)}</strong></span><span><small>ALL-IN COST</small><strong>{money(result.totalCost)}</strong></span></div><div className="profit-bar"><span style={{ width: `${winner ? Math.max(8, Math.min(100, result.profit / Math.max(1, winner.profit) * 100)) : 8}%` }} /></div><button className="edit-button" onClick={() => setActiveCrop(result.crop.crop_id)} aria-label={`Edit ${result.crop.name}`}>edit</button></article>)}</div>
          <div className="assumptions"><div><span className="assumption-icon">⌁</span><span><strong>How to read this</strong><br />Net profit is ranked on the point estimate. The shaded range is price uncertainty, not a yield guarantee.</span></div><div className="assumption-source">Source: <a href="https://data.fao.org/catalog/iso/d24a448b-3b62-4c09-8c1d-4a39bb599876" target="_blank">FAOSTAT</a> · costs: NBS NASS 2023</div></div>
        </section>
      </section>
      <section className="editor-card"><div className="editor-head"><div><p className="eyebrow">Make it yours</p><h2>Edit assumptions</h2></div><select value={activeCrop} onChange={(event) => setActiveCrop(event.target.value)}>{selected.map((id) => <option key={id} value={id}>{crops.find((crop) => crop.crop_id === id)?.name}</option>)}</select></div><div className="editor-grid"><div><label className="field-label">Yield override <span>tonnes / ha</span></label><input className="line-input" type="number" min="0" step="0.1" value={yieldOverrides[activeCrop] ?? yields.find((item) => item.crop_id === activeCrop)?.yield_t_per_ha ?? ''} onChange={(event) => setYieldOverrides((current) => ({ ...current, [activeCrop]: event.target.value }))} /><p className="field-hint">Default: {yields.find((item) => item.crop_id === activeCrop)?.yield_t_per_ha} t/ha · sourced reference</p></div><div className="cost-editor"><label className="field-label">Production costs <span>NGN / ha</span></label><div className="cost-grid">{Object.entries(costs.find((item) => item.crop_id === activeCrop)?.items ?? {}).map(([key, value]) => <label key={key}><span>{labels[key]}</span><input type="number" min="0" value={costOverrides[activeCrop]?.[key] ?? value} onChange={(event) => updateCost(activeCrop, key, event.target.value)} /></label>)}</div><p className="field-hint">Defaults are dated and stale. Replace them with your local quotes before planting.</p></div></div></section>
    </main>
    <footer><span>fieldmargin · offline-first crop planning for Nigeria</span><a href="https://deerflow.tech" target="_blank" rel="noreferrer">Created By Deerflow</a><span>Snapshot pilot-seed-2026-08-24</span></footer>
  </div>
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => undefined))
}
