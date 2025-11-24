import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173, // 设置前端端口号: 所有前端的请求都会通过这个端口号转发到后端
    proxy: {
      '/api': {
        target: 'http://localhost:8000', // 设置后端地址: 所有前端的请求都会转发到这个地址
        changeOrigin: true, // 修改请求头中的 Origin，将端口改为与后端一致(否则浏览器会拒绝请求)
      }
    }
  }
})
