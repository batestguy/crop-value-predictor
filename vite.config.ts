import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { spawn } from 'node:child_process'
import { resolve } from 'node:path'

const supportedCrops = new Set(['maize-white', 'rice', 'rice-milled', 'yam', 'sorghum', 'millet', 'gari-white', 'cassava'])

function onlineEstimateApi() {
  return {
    name: 'fieldmargin-online-estimate-api',
    configureServer(server: { middlewares: { use: Function } }) {
      server.middlewares.use('/api/price-research', (request: any, response: any, next: () => void) => {
        if (request.method !== 'POST') return next()
        let body = ''
        request.on('data', (chunk: Buffer) => {
          body += chunk.toString('utf8')
          if (body.length > 4_096) request.destroy()
        })
        request.on('end', () => {
          let input: any
          try { input = JSON.parse(body) } catch { return sendJson(response, 400, { error: 'The research request was not valid JSON.' }) }
          const crop = typeof input?.cropId === 'string' ? input.cropId : ''
          const state = typeof input?.state === 'string' ? input.state.trim() : ''
          const cropName = typeof input?.cropName === 'string' ? input.cropName.trim() : ''
          const cropForm = typeof input?.cropForm === 'string' ? input.cropForm.trim() : ''
          const researchAll = input?.researchAll === true
          const priceType = input?.priceType === 'wholesale' ? 'Wholesale' : input?.priceType === 'retail' ? 'Retail' : ''
          const isCustomCrop = /^custom:[a-z0-9-]{1,100}$/.test(crop)
          const validCustomDetails = /^[A-Za-z0-9][A-Za-z0-9 .()/'-]{1,79}$/.test(cropName) && /^[A-Za-z0-9][A-Za-z0-9 .()/'-]{1,79}$/.test(cropForm)
          if ((!supportedCrops.has(crop) && !isCustomCrop) || (isCustomCrop && !validCustomDetails) || !/^[A-Za-z][A-Za-z .'-]{1,79}$/.test(state) || !priceType) return sendJson(response, 400, { error: 'Choose a supported crop, Nigerian state, and price type.' })
          const args = [resolve(process.cwd(), 'pipeline', 'online_estimate.py'), '--crop', crop, '--state', state, '--price-type', priceType]
          if (isCustomCrop || researchAll) args.push('--crop-name', cropName, '--crop-form', cropForm)
          if (researchAll) args.push('--research-all')
          const child = spawn(process.env.PYTHON || 'python', args, { cwd: process.cwd(), env: process.env })
          let output = ''
          let finished = false
          const finish = (status: number, payload: unknown) => { if (finished) return; finished = true; clearTimeout(timer); sendJson(response, status, payload) }
          const timer = setTimeout(() => { child.kill(); finish(504, { error: 'The lookup timed out. Enter a local price instead.' }) }, 110_000)
          child.stdout.on('data', (chunk: Buffer) => { output += chunk.toString('utf8') })
          child.on('error', () => finish(503, { error: 'The local research service could not start.' }))
          child.on('close', (code) => {
            if (code !== 0) return finish(502, { error: 'The research service could not complete the lookup.' })
            try { finish(200, JSON.parse(output)) } catch { finish(502, { error: 'The research service returned an invalid response.' }) }
          })
        })
      })
    },
  }
}

function sendJson(response: any, status: number, payload: unknown) {
  response.statusCode = status
  response.setHeader('content-type', 'application/json')
  response.end(JSON.stringify(payload))
}

export default defineConfig({
  // GitHub Pages serves this repository below /crop-value-predictor/, while
  // Cloudflare Pages serves the same build at the domain root. Keep the
  // deployment-specific path in the workflow/environment rather than baking
  // a host-specific URL into the app.
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [react(), onlineEstimateApi()],
  build: { target: 'es2020' },
})
