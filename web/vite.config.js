import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// Same relative routes as the Nginx container (web/nginx/default.conf), so the app code
// never knows where the API lives. Override the target with API_TARGET=http://host:port.
const API_TARGET = process.env.API_TARGET || 'http://localhost:8080';
const proxied = { target: API_TARGET, changeOrigin: false, xfwd: true };

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { '/api': proxied, '/health': proxied, '/ready': proxied },
  },
  preview: { port: 4173 },
  // assetsInlineLimit 0: never inline fonts/images as data: URIs (the Nginx CSP allows font-src 'self' only).
  build: { sourcemap: false, chunkSizeWarningLimit: 800, assetsInlineLimit: 0 },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.js'],
    css: false,
    include: ['src/**/*.test.{js,jsx}'],
  },
});
