import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: '../build',
    assetsDir: 'static',
    emptyOutDir: true,
  },
  define: mode === 'test' ? { 'import.meta.env.VITE_API_BASE_URL': JSON.stringify('') } : {},
  server: {
    port: 5556,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:5555',
        changeOrigin: true,
        rewrite: path => path,
      },
    },
  },
}))
