# UnderTheInfluence Frontend

**Stack**: Astro 5 + Svelte 5 + D3.js + Tailwind CSS

A modern, server-rendered frontend with selective client-side hydration for interactive visualizations.

## Architecture

### Astro 5 + Svelte 5

The frontend uses **Astro** for server-side rendering with **Svelte 5** components for interactivity:

```
┌─────────────────────────────────────────────────────────────┐
│                    Astro Page (.astro)                       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Server-Rendered HTML (Static Content)                │  │
│  │ - Hero section, typography, stats                    │  │
│  │ - SEO-friendly, fast initial load                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Svelte Component (client:visible)                    │  │
│  │ - MinisterNetwork visualization                      │  │
│  │ - D3.js force simulation                             │  │
│  │ - Interactive hover/click behavior                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Server-Rendered HTML (Methodology, Footer)           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Principles**:
- Server-rendered by default for SEO and fast initial load
- Components hydrate only when visible (`client:visible`)
- Svelte 5 Runes (`$state`, `$props`, `$derived`) for reactive state
- D3.js for data visualization

### Design System

**Typography** (Natural History / Editorial):
- Headlines: Zodiak (serif)
- Body: Satoshi (sans-serif)
- Data: Tabular figures for alignment

**Color Palette** (Organic / Natural History):
```
Ministers:     #C54B3C (Terracotta red)
Donors:        #4A6741 (Forest green)
Organizations: #6B5B4F (Warm brown)
Meetings:      #7B9E87 (Sage green)
Paper:         #FAF8F5 (Warm white)
Ink:           #2C2C2C (Dark gray)
```

## Components

### MinisterNetwork (`src/components/MinisterNetwork.svelte`)

Interactive D3.js force-directed network visualization showing:

**Nodes**:
- Ministers (terracotta) - Current UK government ministers
- Donors (forest green) - People/organizations who donated
- Meeting Attendees (sage green) - Organizations who met with ministers

**Links**:
- Donation connections (solid brown lines)
- Meeting connections (dashed sage lines)

**Interactions**:
- Hover: Preview node details
- Click: Pin node detail card
- Close button: Unpin

**Props**:
```typescript
interface Props {
  apiUrl?: string;       // API endpoint (default: /api/v2/aggregates/minister-network/)
  width?: number;        // SVG width (default: 1200)
  height?: number;       // SVG height (default: 800)
  limit?: number;        // Max ministers (default: 30)
  minValue?: number;     // Min donation value (default: 10000)
  minMeetings?: number;  // Min meetings to include attendee (default: 5)
  currentOnly?: boolean; // Only current ministers (default: true)
}
```

## Pages

### Homepage (`src/pages/index.astro`)

Editorial-style investigation page with:
- Masthead with investigation label
- Hero section with headline and deck
- Stats strip (donations tracked, total value, dual-influence)
- Full-width minister network visualization
- Pull quote / insight section
- Methodology section
- Footer

## Development

### Commands

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:4321)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### API Integration

The frontend fetches data from the Django API (port 8000):

**Stats Endpoint**:
```
GET /api/v2/aggregates/stats/
```

**Minister Network Endpoint**:
```
GET /api/v2/aggregates/minister-network/
  ?limit=30
  &min_value=5000
  &min_meetings=5
  &current_only=true
```

**CORS**: The Django API allows requests from `http://localhost:4321` (Astro dev server).

## File Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── MinisterNetwork.svelte  # D3.js network visualization
│   ├── layouts/
│   │   └── BaseLayout.astro        # Base HTML layout
│   ├── pages/
│   │   └── index.astro             # Homepage
│   └── styles/
│       └── global.css              # Global styles + Tailwind
├── public/                         # Static assets
├── astro.config.mjs               # Astro configuration
├── tailwind.config.mjs            # Tailwind configuration
├── package.json                   # Dependencies
└── tsconfig.json                  # TypeScript configuration
```

## Configuration

### Astro Config (`astro.config.mjs`)

```javascript
import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  integrations: [svelte(), tailwind()],
});
```

### Tailwind Config (`tailwind.config.mjs`)

Custom theme with:
- Natural history color palette
- Editorial typography (Zodiak, Satoshi)
- Custom spacing and border styles

## Dependencies

**Core**:
- `astro` 5.x - Static site generator with partial hydration
- `@astrojs/svelte` - Svelte integration for Astro
- `svelte` 5.x - Reactive UI framework with Runes
- `d3` 7.x - Data visualization library

**Styling**:
- `@astrojs/tailwind` - Tailwind CSS integration
- `tailwindcss` 3.x - Utility-first CSS framework

## Migration Notes

This frontend replaced the previous React Islands + Vite architecture:

| Before | After |
|--------|-------|
| Vite 5 + React 18 | Astro 5 + Svelte 5 |
| Islands Architecture (custom) | Astro partial hydration |
| Zustand state | Svelte 5 Runes |
| Bootstrap 5 | Tailwind CSS |
| CSS Modules | Tailwind + scoped styles |
| Port 5173 | Port 4321 |

**Why Astro + Svelte?**
- Simpler partial hydration (built-in `client:*` directives)
- Smaller bundle size (Svelte compiles away the framework)
- Better DX for content-heavy pages
- Native support for server-rendered content
- Svelte 5 Runes are more intuitive than React hooks
