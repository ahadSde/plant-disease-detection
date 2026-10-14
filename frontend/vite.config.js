import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8080',
      '/images': {
        target: 'http://localhost:8080',
        rewrite: path => path.replace(/^\/images/, '/api/images'),
      },
    },
  },
})
