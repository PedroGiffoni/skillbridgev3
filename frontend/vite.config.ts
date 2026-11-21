import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
export default defineConfig(({ mode }) => ({
  plugins: [react(), ...(mode === 'test' ? [] : [tailwindcss()])],
  build: { rollupOptions: { input: { app: 'index.html', personagens: 'personagens.html' } } },
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  test: { environment: 'jsdom', setupFiles: './src/test-setup.ts' },
}))
