// @ts-check
import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';
import tailwind from '@astrojs/tailwind';

// https://astro.build/config
export default defineConfig({
  integrations: [
    svelte(),
    tailwind(),
  ],
  server: {
    host: true,  // Allow external connections (Docker)
    port: 4321,
  },
  vite: {
    server: {
      watch: {
        usePolling: true,  // Better file watching in Docker
      },
    },
  },
});
