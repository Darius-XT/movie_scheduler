import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // 本地开发默认转发到宿主机后端，Docker 开发环境则通过环境变量改为 backend 服务。
        target: apiProxyTarget,
        changeOrigin: true
      }
    }
  }
})
