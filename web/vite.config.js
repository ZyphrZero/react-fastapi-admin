import { resolve } from 'node:path'

import react from '@vitejs/plugin-react'
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
    host: '127.0.0.1',
    forwardConsole: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9999', // Use 127.0.0.1 to avoid IPv6 issues.
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
