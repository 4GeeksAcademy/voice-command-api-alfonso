import { defineConfig } from 'vite'

const apiTarget = 'http://127.0.0.1:8000'

export default defineConfig({
  server: {
    proxy: {
      '/instruction': apiTarget,
      '/tasks': apiTarget,
      '/transcribe': apiTarget,
    },
  },
})