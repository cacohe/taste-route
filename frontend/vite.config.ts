/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  // MapLibre is isolated behind the lazy result route. Its minified source is
  // ~1.1 MB (~300 KB gzip), so the threshold reflects that audited dependency.
  build: {
    chunkSizeWarningLimit: 1150,
  },
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
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  test: {
    environment: 'happy-dom',
    include: ['src/**/*.test.ts'],
  },
})

