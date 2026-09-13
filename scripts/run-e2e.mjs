import { spawn, spawnSync } from 'node:child_process'
import { access } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'

const root = fileURLToPath(new URL('..', import.meta.url))
const port = Number(process.env.E2E_PORT || 4173)
const basePath = process.env.E2E_BASE_PATH || '/'
const baseUrl = `http://127.0.0.1:${port}${basePath}`
const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm'

const terminateTree = (pid) => {
  if (process.platform === 'win32') {
    const killer = spawn('taskkill', ['/PID', String(pid), '/T', '/F'], {
      stdio: 'ignore',
      windowsHide: true,
    })
    killer.unref()
  }
}

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error(`E2E_PORT must be a valid TCP port: ${port}`)
}

const buildCommand = process.platform === 'win32' ? (process.env.ComSpec || 'cmd.exe') : npmCommand
const buildArgs = process.platform === 'win32'
  ? ['/d', '/s', '/c', `${npmCommand} run build`]
  : ['run', 'build']
const build = spawnSync(buildCommand, buildArgs, {
  cwd: root,
  env: process.env,
  stdio: 'inherit',
  windowsHide: true,
})
if (build.status !== 0) process.exit(build.status ?? 1)

const server = spawn(process.execPath, [resolve(root, 'scripts/serve-preview.mjs')], {
  cwd: root,
  env: { ...process.env, E2E_PORT: String(port) },
  stdio: 'inherit',
  windowsHide: true,
})

const stopServer = async () => {
  if (server.exitCode !== null) return
  if (process.platform === 'win32') {
    server.kill()
    terminateTree(server.pid)
  } else {
    server.kill('SIGTERM')
  }
}

const waitForServer = async () => {
  const deadline = Date.now() + 30_000
  while (Date.now() < deadline) {
    if (server.exitCode !== null) throw new Error(`Preview server exited with code ${server.exitCode}`)
    try {
      const response = await fetch(baseUrl)
      if (response.ok) return
    } catch {
      // The preview server is still starting.
    }
    await new Promise((done) => setTimeout(done, 250))
  }
  throw new Error(`Preview server did not become ready at ${baseUrl}`)
}

const runTests = () => new Promise((resolveRun, rejectRun) => {
  let output = ''
  let summaryTimer
  let hardTimer
  let settled = false
  const finish = (code) => {
    if (settled) return
    settled = true
    clearTimeout(summaryTimer)
    clearTimeout(hardTimer)
    resolveRun(code)
  }
  const test = spawn(process.execPath, [resolve(root, 'node_modules/@playwright/test/cli.js'), 'test', ...process.argv.slice(2)], {
    cwd: root,
    env: process.env,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  })
  const forward = (chunk, stream) => {
    const text = chunk.toString()
    output += text
    stream.write(text)
    if (!summaryTimer && /\d+ passed/.test(output)) {
      summaryTimer = setTimeout(() => {
        if (test.exitCode === null) {
          test.kill()
          terminateTree(test.pid)
        }
        finish(/\d+ failed/.test(output) ? 1 : 0)
      }, 2_000)
    }
  }
  test.stdout.on('data', (chunk) => forward(chunk, process.stdout))
  test.stderr.on('data', (chunk) => forward(chunk, process.stderr))
  hardTimer = setTimeout(() => {
    if (test.exitCode === null) {
      test.kill()
      terminateTree(test.pid)
    }
    finish(1)
  }, 120_000)
  test.once('error', rejectRun)
  test.once('exit', (code, signal) => finish(code ?? (signal ? 1 : 0)))
})

try {
  await access(resolve(root, 'dist/index.html'))
  await waitForServer()
  process.exitCode = await runTests()
} finally {
  await stopServer()
}
