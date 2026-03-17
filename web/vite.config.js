import { resolve } from 'node:path'

import react from '@vitejs/plugin-react-swc'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': resolve(import.meta.dirname, 'src'),
    },
  },
  server: {
    forwardConsole: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9999', // 使用 127.0.0.1 避免 IPv6 问题
        changeOrigin: true,
        rewrite: (urlPath) => urlPath.replace(/^\/api/, '/api/v1'),
      },
      '/static': {
        target: 'http://127.0.0.1:9999',
        changeOrigin: true,
      },
    },
  },
})
