import { defineConfig, devices } from '@playwright/test'

// Starts the API and the production build of the frontend itself. Switching the target
// to the Docker Compose stack is a Phase 5 task (no Docker on the workstation yet).
const API_PORT = 8010
const WEB_PORT = 4173

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  outputDir: './test-results',
  use: { baseURL: `http://127.0.0.1:${WEB_PORT}`, ...devices['Desktop Chrome'], locale: 'en-GB' },
  webServer: [
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
  ],
})
