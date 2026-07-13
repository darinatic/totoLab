import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// In dev, proxy /api -> the FastAPI backend (which serves the API under /api).
// In production a single container serves both the SPA and /api from one origin,
// so the frontend always calls the relative '/api' base.
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8010',
        changeOrigin: true,
      },
    },
  },
})
