import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => ({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  },
  build: {
    // 生产优化配置 (Issue #1248)
    minify: 'terser',
    sourcemap: false,
    terserOptions: {
      compress: {
        drop_console: mode === 'production',
        drop_debugger: mode === 'production'
      }
    },
    rollupOptions: {
      output: {
        // Gzip 压缩文件
        manualChunks: {
          vendor: ['vue'],
          echarts: ['echarts'],
          markdown: ['marked'],
          d3: ['d3']
        }
      }
    },
    // 开启 CSS code splitting
    cssCodeSplit: true,
    // 启用源码映射用于调试
    sourceMap: false,
    // 块大小警告阈值
    chunkSizeWarningLimit: 1000
  },
  // 开发环境配置
  optimizeDeps: {
    include: ['vue', 'echarts', 'd3', 'marked']
  }
}))