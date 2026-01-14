import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/static/',
  build: {
    manifest: true,
    outDir: './static/dist',
    rollupOptions: {
      input: {
        main: './frontend/main.tsx',
        islands: './frontend/islands.tsx'
      }
    }
  },
  server: {
    origin: 'http://localhost:5173',
    host: '0.0.0.0', // Allow Docker access
    port: 5173,
    watch: {
      usePolling: true // Required for Docker file watching
    }
  },
  css: {
    modules: {
      localsConvention: 'camelCase',
      scopeBehaviour: 'local'
    },
    preprocessorOptions: {
      scss: {
        additionalData: `@import "./frontend/styles/_variables.scss";`
      }
    }
  }
});
