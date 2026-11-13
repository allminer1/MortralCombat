import { defineConfig, devices } from '@playwright/test'

// Two modes:
//   E2E_BASE_URL set (make e2e): test the running Docker Compose stack at that address.
//   not set (make e2e-local):    start the API and two builds of the frontend here; the
//                                second build has the Kazakh flag on (project "kk-flag").
const STACK_URL = process.env.E2E_BASE_URL
const API_PORT = 8010
const WEB_PORT = 4173
const KK_PORT = 4174
const WEB_URL = STACK_URL ?? `http://127.0.0.1:${WEB_PORT}`

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  outputDir: './test-results',
  use: { ...devices['Desktop Chrome'], locale: 'en-GB' },
  projects: [
    // accounts.spec.ts needs the stack with the database (make e2e-accounts sets E2E_ACCOUNTS).
    {
      name: 'default',
      testIgnore: process.env.E2E_ACCOUNTS ? /kk\.spec\.ts/ : /(kk|accounts)\.spec\.ts/,
      use: { baseURL: WEB_URL },
    },
    ...(STACK_URL ? [] : [{ name: 'kk-flag', testMatch: /kk\.spec\.ts/, use: { baseURL: `http://127.0.0.1:${KK_PORT}` } }]),
  ],
  webServer: STACK_URL ? [] : [
    {
      command: `uv run uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT} --no-access-log`,
      cwd: '../backend',
      url: `http://127.0.0.1:${API_PORT}/api/v1/health`,
      env: { RATE_LIMIT_PER_MINUTE: '0' },
      reuseExistingServer: false,
    },
    {
      command: 'npm run build && npm run preview',
      url: `http://127.0.0.1:${WEB_PORT}/`,
      env: { API_ORIGIN: `http://127.0.0.1:${API_PORT}` },
      reuseExistingServer: false,
    },
    {
      command: `npx vite build --outDir dist-kk && npx vite preview --outDir dist-kk --port ${KK_PORT}`,
      url: `http://127.0.0.1:${KK_PORT}/`,
      env: { API_ORIGIN: `http://127.0.0.1:${API_PORT}`, VITE_ENABLE_KK: 'true' },
      reuseExistingServer: false,
    },
  ],
})
