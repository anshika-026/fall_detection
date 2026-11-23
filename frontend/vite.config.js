import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Port 5190 (SMC's frontend uses 5180). /api and /ws are proxied to the Fall
// Detection backend on 8830, so the browser talks to one origin and needs no CORS.
const BACKEND = process.env.VITE_BACKEND || 'http://127.0.0.1:8830'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5190,
    strictPort: true,
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
      '/ws': { target: BACKEND.replace('http', 'ws'), ws: true, changeOrigin: true },
    },
  },
})
