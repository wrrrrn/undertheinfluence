/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Zodiak', 'serif'],
        body: ['Satoshi', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        // Natural history / organic palette
        'accent': {
          DEFAULT: '#C54B3C',  // Muted terracotta (Economist red)
          dark: '#8B3A2F',
          light: '#E07B6C',
        },
        'ink': {
          DEFAULT: '#1a1a1a',  // Near black for text
          light: '#4a4a4a',
          muted: '#6b6b6b',
        },
        'paper': {
          DEFAULT: '#FAF9F6',  // Warm parchment
          cream: '#F4F1EB',
          warm: '#EDE8E0',
        },
        // Network visualization node colors (top-level for opacity modifiers)
        'minister': '#B85450',   // Warm red
        'donor': '#5B7355',      // Botanical green
        'director': '#4A7BA7',   // Steel blue
        'psc': '#B87333',        // Copper
        // Organic data visualization colors (grouped)
        'data': {
          minister: '#B85450',    // Warm red
          donor: '#5B7355',       // Botanical green
          director: '#4A7BA7',    // Steel blue
          organization: '#6B5B4F', // Warm brown
          highlight: '#DAA520',   // Goldenrod (bridge nodes)
          muted: '#9A9285',       // Stone grey
        },
      },
      fontSize: {
        // Editorial type scale
        'headline-xl': ['4rem', { lineHeight: '1.1', letterSpacing: '-0.02em' }],
        'headline-lg': ['2.5rem', { lineHeight: '1.15', letterSpacing: '-0.01em' }],
        'headline-md': ['1.75rem', { lineHeight: '1.2' }],
        'headline-sm': ['1.25rem', { lineHeight: '1.3' }],
        'body-lg': ['1.125rem', { lineHeight: '1.6' }],
        'body': ['1rem', { lineHeight: '1.6' }],
        'caption': ['0.875rem', { lineHeight: '1.4' }],
        'label': ['0.75rem', { lineHeight: '1.3', letterSpacing: '0.05em' }],
      },
      spacing: {
        'editorial': '2rem',
        'editorial-lg': '4rem',
      },
    },
  },
  plugins: [],
};
