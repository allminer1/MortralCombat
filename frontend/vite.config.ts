import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Public address of the site, used in canonical links and link previews (index.html and
// DocumentHead.tsx). Set here, not in an .env file, because .env files are not committed.
process.env.VITE_SITE_URL ??= 'https://neomortalsurv.net'

// The API runs separately (make dev). In production Caddy routes /api to it.
const api = process.env.API_ORIGIN ?? 'http://127.0.0.1:8000'
const proxy = { '/api': { target: api, changeOrigin: false } }

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true, proxy },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true, proxy },
  // No data: URLs: every font and image is a real file, so the strict
  // Content-Security-Policy (deploy/Caddyfile) needs no exceptions.
  build: { assetsInlineLimit: 0 },
  test: { include: ['src/**/*.test.ts'], environment: 'node' },
})
