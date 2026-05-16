import { copyFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

const rootDir = dirname(fileURLToPath(import.meta.url))
const workletSrc = resolve(
  rootDir,
  'node_modules/@speechmatics/browser-audio-input/dist/pcm-audio-worklet.min.js',
)
const workletDest = resolve(rootDir, 'public/js/pcm-audio-worklet.min.js')

function copySpeechmaticsWorklet(): Plugin {
  return {
    name: 'copy-speechmatics-worklet',
    buildStart() {
      mkdirSync(dirname(workletDest), { recursive: true })
      copyFileSync(workletSrc, workletDest)
    },
  }
}

export default defineConfig({
  plugins: [copySpeechmaticsWorklet(), react(), tailwindcss()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/query': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/speechmatics': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
