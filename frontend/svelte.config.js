import { vitePreprocess } from '@astrojs/svelte';

export default {
  preprocess: vitePreprocess(),
  compilerOptions: {
    // Enable Svelte 5 runes mode
    runes: true,
  },
};
