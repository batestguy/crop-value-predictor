import { readdir, readFile, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { join } from 'node:path'

const base = process.env.VITE_BASE_PATH || '/'
if (!/^\/(?:[a-zA-Z0-9_-]+\/)*$/.test(base)) throw new Error('VITE_BASE_PATH must be an absolute directory path ending in /')
async function walk(directory) {
  const files = []
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name)
    files.push(...(entry.isDirectory() ? await walk(path) : [path]))
  }
  return files
}
const manifest = JSON.parse(await readFile('public/manifest.webmanifest', 'utf8'))
manifest.id = manifest.scope = manifest.start_url = base
manifest.icons = manifest.icons.map((icon) => ({ ...icon, src: base + icon.src.replace(/^\.\//, '') }))
await writeFile('dist/manifest.webmanifest', JSON.stringify(manifest, null, 2) + '\n')
const paths = (await walk('dist')).map((path) => path.replaceAll('\\', '/').slice(5))
  .filter((path) => !['sw.js', 'precache.json'].includes(path)).sort()
const worker = await readFile('public/sw.js', 'utf8')
const hash = createHash('sha256').update(base).update(worker)
for (const path of paths) hash.update(path).update(await readFile(join('dist', path)))
const cachePrefix = `fieldmargin-${encodeURIComponent(base)}-`
const config = { cacheName: cachePrefix + hash.digest('hex').slice(0, 20), cachePrefix, base, files: paths.map((path) => base + path) }
await writeFile('dist/sw.js', `self.__FIELDMARGIN_BUILD=${JSON.stringify(config)};\n${worker}`)
await writeFile('dist/precache.json', JSON.stringify(config, null, 2) + '\n')
