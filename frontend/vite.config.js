import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  const proxyTarget = env.VITE_PROXY_TARGET || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api/v2/chat': {
          target: proxyTarget,
          changeOrigin: true,
        },
        '/models': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
