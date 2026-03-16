import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return undefined
          }

          if (
            id.includes('/node_modules/react/') ||
            id.includes('/node_modules/react-dom/') ||
            id.includes('/node_modules/react-router/') ||
            id.includes('/node_modules/react-router-dom/')
          ) {
            return 'react-vendor'
          }

          if (id.includes('@iconify/react')) {
            return 'icon-vendor'
          }

          if (id.includes('@ant-design/icons')) {
            return 'ant-icons-vendor'
          }

          if (
            id.includes('/rc-') ||
            id.includes('@ant-design/') ||
            id.includes('/dayjs/')
          ) {
            return 'antd-ecosystem-vendor'
          }

          if (
            id.includes('/antd/es/app/') ||
            id.includes('/antd/es/config-provider/') ||
            id.includes('/antd/es/layout/') ||
            id.includes('/antd/es/menu/') ||
            id.includes('/antd/es/dropdown/') ||
            id.includes('/antd/es/avatar/') ||
            id.includes('/antd/es/breadcrumb/') ||
            id.includes('/antd/es/spin/')
          ) {
            return 'antd-shell-vendor'
          }

          if (
            id.includes('/antd/es/form/') ||
            id.includes('/antd/es/input/') ||
            id.includes('/antd/es/select/') ||
            id.includes('/antd/es/button/') ||
            id.includes('/antd/es/modal/') ||
            id.includes('/antd/es/tabs/')
          ) {
            return 'antd-form-vendor'
          }

          if (
            id.includes('/antd/es/table/') ||
            id.includes('/antd/es/pagination/') ||
            id.includes('/antd/es/tag/') ||
            id.includes('/antd/es/descriptions/') ||
            id.includes('/antd/es/progress/') ||
            id.includes('/antd/es/statistic/')
          ) {
            return 'antd-data-vendor'
          }

          if (id.includes('/antd/')) {
            return 'antd-base-vendor'
          }

          if (id.includes('/axios/')) {
            return 'http-vendor'
          }

          return undefined
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9999', // 使用 127.0.0.1 避免 IPv6 问题
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api/v1')
      }
    }
  }
})
