import { defineConfig } from 'vite'

export default defineConfig({
  // GitHub Pages injects its repository base path during the Actions build.
  // Local builds keep using relative paths so the preview still works at `/`.
  base: process.env.VITE_BASE_PATH || './',
  server: {
    host: '127.0.0.1',
    port: 5173,
  },
  preview: {
    host: '127.0.0.1',
    port: 4173,
  },
  build: {
    // Three.js is intentionally bundled as one viewer entry point.
    chunkSizeWarningLimit: 700,
  },
})
