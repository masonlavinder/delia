import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The Flask server (web_app/server) serves `dist/` at the root of its own
// origin on the Pi, so the API needs no CORS. `base: '/'` (not './') matters:
// the server falls back to index.html for unknown paths, and relative asset
// URLs would resolve against a nested path and silently re-serve the shell.
//
// In dev, `npm run dev` proxies /api to a Flask instance so the real daemon
// answers. Point it elsewhere with PANEL_API=http://localhost:8080 npm run dev.
export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    host: true, // reachable from a phone on the same WiFi
    proxy: {
      '/api': {
        target: process.env.PANEL_API ?? 'http://delia-pi.local:8080',
        changeOrigin: true,
      },
    },
  },
})
