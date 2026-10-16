import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// 开发期通过代理转发 /api 到后端，避免跨域配置；
// 部署时把 VITE_API_BASE 指向后端完整地址即可（见 .env.production）。
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
    watch: {
      // 某些编辑器 / 工具（含 DSH 的写文件实现）采用「先写临时文件再原子重命名」的策略，
      // 会在源码目录里产生形如 .filter.ts.<pid>.<rand>.tmpdir/filter.ts.tmp 的临时目录。
      // Vite 的文件监听器一旦盯上它们就会抛 EBUSY 并让整个 dev server 崩溃，
      // 因此这里显式忽略所有临时文件与临时目录。
      ignored: [/\.tmpdir[\\/]/, /\.tmp$/, /[\\/]\.~/, /~$/],
    },
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        // 用函数形式按模块路径分包：没有用到的库不会产生空 chunk
        manualChunks(id) {
          if (id.includes('node_modules/echarts') || id.includes('node_modules/zrender')) {
            return 'echarts'
          }
          if (id.includes('node_modules')) {
            return 'vendor'
          }
          return undefined
        },
      },
    },
  },
})
