import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        entryFileNames: `balam-widget.js`,
        chunkFileNames: `balam-widget.js`,
        assetFileNames: `balam-widget.[ext]`
      }
    }
  }
})
