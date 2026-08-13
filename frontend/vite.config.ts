import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'
import fs from 'fs'
import path from 'path'

// HTTPS local para probar la PWA desde el teléfono (Chrome exige secure context).
// Los certs se generan con mkcert (ver .certs/) y no se versionan. Si no existen,
// el dev server arranca en HTTP normal — sólo la instalación PWA por IP requiere HTTPS.
const certPath = path.resolve(__dirname, '.certs/dev-cert.pem')
const keyPath = path.resolve(__dirname, '.certs/dev-key.pem')
const httpsConfig =
  fs.existsSync(certPath) && fs.existsSync(keyPath)
    ? { cert: fs.readFileSync(certPath), key: fs.readFileSync(keyPath) }
    : undefined

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      // Habilita la PWA también en `vite dev` para poder probar la instalación.
      devOptions: { enabled: true },
      includeAssets: ['favicon.png', 'favicon-32.png', 'apple-touch-icon.png'],
      manifest: {
        name: 'Municipalidad de San Jerónimo — Transparencia',
        short_name: 'MDSJ',
        description:
          'Portal de transparencia de la Municipalidad Distrital de San Jerónimo (Cusco): obras públicas y ejecución del presupuesto.',
        lang: 'es',
        // standalone: se abre como app, sin barra de direcciones del navegador.
        display: 'standalone',
        orientation: 'portrait-primary',
        start_url: '/',
        scope: '/',
        background_color: '#ffffff',
        theme_color: '#3484A5',
        icons: [
          { src: 'pwa-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'pwa-maskable-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        // No cachear el backend: las respuestas de /api deben ir siempre a la red.
        navigateFallbackDenylist: [/^\/api/],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: true,
    // 5173 (default de Vite) cae en el rango 5141-5240 que Windows reserva
    // (Hyper-V/WSL/Docker) → EACCES al arrancar. 5180 tambien cae ahi. Usamos
    // 3000, confirmado libre y fuera de todos los rangos excluidos.
    // Ver: netsh interface ipv4 show excludedportrange protocol=tcp
    port: 3000,
    strictPort: true,
    https: httpsConfig,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
