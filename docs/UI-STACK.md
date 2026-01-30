# Technical Migration Guide: UnderTheInfluence 2026

This document outlines the transition from the current manual **React Islands + Django Template** architecture to a modern, decoupled **Astro + Svelte 5** stack.

---

## 1. The New Modern Stack

The 2026 stack focuses on "Zero-JS" delivery for editorial content and high-performance "Runes-based" reactivity for data visualizations.

### Frontend Layer

* **Orchestrator**: **Astro 5.x** (Hybrid SSG/SSR).
* **Component Framework**: **Svelte 5** (utilizing Runes for fine-grained reactivity).
* **UI Primitives**: **shadcn-svelte** (Bits UI) for accessible, copy-paste components.
* **Styling**: **Tailwind CSS** (replacing Bootstrap 5/SCSS).

### Typography

| Role | Font | Weight Range | Source |
|------|------|--------------|--------|
| **Headlines/Display** | Zodiak | 400-700 (variable) | [Fontshare](https://www.fontshare.com/fonts/zodiak) |
| **Body/UI/Labels** | Satoshi | 400-700 (variable) | [Fontshare](https://www.fontshare.com/fonts/satoshi) |
| **Monospace** | JetBrains Mono | 400-700 | Google Fonts |

Both Zodiak and Satoshi are self-hosted variable fonts from Fontshare. This pairing provides a modern editorial aesthetic with full weight flexibility for data-heavy UI.

### Data & State

* **Data Visualization**: **D3.js** (math-only; Svelte handles rendering).
* **State Management**: **Nano Stores** (multi-island state) + URL Parameters.
* **Data Fetching**: Native **Fetch API** + Astro `Astro.props` for server-side data.

### Backend (Headless)

* **CMS**: **Wagtail 7.2** (Headless API v2).
* **Data API**: **Django REST Framework** (Existing v2 endpoints).

### Dual-API Architecture

The frontend acts as a "Data Orchestrator," pulling from two distinct sources:

1. **Wagtail API (Content)**: Serves editorial text, politician biographies, and article content. Fetched at build-time (SSG) for maximum SEO and speed.

2. **Custom Data API (Statistics)**: Serves relationship nodes, donation amounts, and real-time statistics. Fetched either:
   - In Astro (SSR): To pre-render the initial state of charts
   - In Svelte (Client-side): To power interactive filters and real-time updates

---

## 2. Core Architectural Shift

| Feature | Current Architecture | Astro + Svelte Architecture |
| --- | --- | --- |
| **Page Rendering** | Django Templates (`.html`) | Astro Components (`.astro`) |
| **Hydration** | Manual logic in `islands.tsx` | Declarative directives (`client:visible`) |
| **Interactivity** | React 18 (Virtual DOM) | Svelte 5 (Signals/Runes) |
| **Styling** | Bootstrap 5 + SCSS Modules | Tailwind Utility Classes |
| **CSS Scope** | CSS Modules | Svelte Scoped Styles |

---

## 3. Migration Roadmap

### Phase 1: Environment & Tooling

1. **Initialize Astro**: Scaffold a new Astro project alongside your `datafetch` Django app.
2. **Tailwind Integration**: Configure Tailwind with the **Editorial Edition** palette (Influence Blue, Action Blue, etc.) and typography (Zodiak, Satoshi).
3. **shadcn-svelte Setup**: Initialize the component registry to replace Bootstrap's generic UI elements.

### Phase 2: Component Conversion

Convert existing React components to Svelte 5.

* **Logic**: Replace `useState` with `$state()` and `useEffect` with `$effect()`.
* **Visuals**: Implement the refined **20px radius** and layered shadows defined in the Editorial Edition.
* **Example (StatCard Conversion)**:
* *React (Current)*: Uses `styles.card` and Bootstrap classes.
* *Svelte (New)*: Uses Tailwind classes like `rounded-[20px]`, `shadow-xl`, and `font-serif` for headings.



### Phase 3: State & URL Sync

1. **Replace Zustand**: Move `filterStore.ts` logic to a **Nano Store**.
2. **URL Sync**: Preserve the current logic of keeping filter state in the URL for shareable links, but handle it through Astro's server-side logic and client-side store updates.

### Phase 4: Wagtail API Integration

1. **Enable Headless**: Ensure Wagtail `API_V2` is fully exposed.
2. **Astro Fetching**: Use Astro's top-level `await fetch()` to pull page content from Wagtail.
3. **Block Mapping**: Map Wagtail StreamField blocks directly to Astro components (e.g., `StatsGridBlock` -> `<StatsGrid />`).

---

## 4. Migration Example: StatCard Component

### Before (React + Bootstrap)

```tsx
// frontend/components/StatCard.tsx
import styles from './StatCard.module.scss';
export const StatCard = ({ value, label }) => (
  <div className="card shadow-sm p-3">
    <h3 className={styles.value}>{value}</h3>
    <p className="text-muted">{label}</p>
  </div>
);

```

### After (Svelte + Tailwind + Editorial Styles)

```svelte
<script lang="ts">
  let { value, label } = $props(); // Svelte 5 Runes
</script>

<div class="rounded-[20px] bg-white p-8 border border-slate-900/5 shadow-[0_10px_15px_-3px_rgba(15,23,42,0.05)] transition-all hover:-translate-y-1 hover:shadow-2xl">
  <h3 class="font-display text-3xl font-bold text-influence-blue tabular-nums leading-tight">
    {value}
  </h3>
  <p class="font-body text-sm font-medium text-slate-500 uppercase tracking-wider mt-2">
    {label}
  </p>
</div>
```

**Tailwind font config:**
```js
// tailwind.config.mjs
fontFamily: {
  display: ['Zodiak', 'serif'],
  body: ['Satoshi', 'sans-serif'],
  mono: ['JetBrains Mono', 'monospace'],
}
```

---

## 5. Summary of Benefits

* **Editorial Authority**: Instant, high-performance typography and layout rendering via Astro.
* **Data Depth**: Superior handling of complex D3-based network and Sankey visualizations using Svelte's direct DOM control.
* **Developer Experience**: Replaces manual "Island Registry" boilerplate with Astro’s automated hydration directives.
* **Performance**: Drastically reduced bundle sizes (40-60KB reduced further by removing React runtime).

---

## 6. Infrastructure & Docker

The Astro frontend reuses the existing `web` container slot, replacing Vite:

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:15

  redis:
    image: redis:7

  api:  # Django - serves APIs only
    build: ./api
    ports:
      - "8000:8000"

  web:  # Astro (replaces Vite)
    build: ./frontend
    command: npm run dev
    ports:
      - "4321:4321"
    environment:
      - WAGTAIL_API_URL=http://api:8000/api/v2
      - DATA_API_URL=http://api:8000/api/v2
```

**Key points:**
- Internal Docker network = no CORS configuration needed
- Single `docker compose up` still works
- Django becomes a pure API server
- For production: Nginx reverse proxy routes `/api/*` and `/admin/*` to Django, everything else to Astro

---

## 7. D3.js + Svelte Integration

Svelte has a significant advantage over React for D3 visualizations: no Virtual DOM conflicts.

**Pattern: D3 for Math, Svelte for Rendering**

```svelte
<script>
  import { forceSimulation, forceLink, forceManyBody } from 'd3-force';

  let nodes = $state([...]); // Network data from API

  $effect(() => {
    const simulation = forceSimulation(nodes)
      .force('charge', forceManyBody().strength(-100))
      .on('tick', () => {
        nodes = [...nodes]; // Trigger Svelte reactivity
      });

    return () => simulation.stop();
  });
</script>

<svg>
  {#each nodes as node}
    <circle cx={node.x} cy={node.y} r={node.radius} />
  {/each}
</svg>
```

**Why this matters:**
- D3 calculates force positions, Sankey paths, etc.
- Svelte's native `$state` and transitions handle rendering
- Svelte 5 Runes enable fine-grained updates (individual node positions) without re-rendering entire charts
- Declarative SVG in `.svelte` files keeps code readable

---

## 8. Build Triggers & SSG

For editorial content served as static HTML, use **webhooks** triggered by Wagtail's `after_publish` signal.

**How it works:**
1. Editor publishes an article in Wagtail
2. Wagtail fires a POST request to the build hook URL (Netlify, Vercel, or CI/CD runner)
3. Astro rebuilds affected pages and deploys

**Hybrid safety net:** For large sites, implement **On-demand ISR** via Astro middleware to revalidate specific pages without full rebuilds.

---

## 9. Wagtail Preview

Editors must see the exact Svelte-rendered output during preview.

**Implementation:**
1. Install `wagtail-headless-preview` in Django backend
2. Configure Wagtail's `preview_url` to point to `/preview?id={page_id}&token={token}`
3. Create an SSR route in Astro that:
   - Validates the preview token
   - Fetches draft JSON from Wagtail API
   - Renders using production Svelte components

**Result:** True WYSIWYG preview with actual Zodiak typography and Svelte visualizations.

---

## 10. Authentication Surface

| Role | Access Point | Auth Mechanism |
|------|--------------|----------------|
| **Public Visitor** | Astro Frontend | None (Static/Public) |
| **Editor** | Wagtail Admin (`/admin/`) | Django Session |
| **Preview Bot** | Astro Preview Route | Temporary Token |
| **Data Island** | Custom API v2 | Token/CORS (if needed) |

**Simplification:** All public-facing data and editorial content are unauthenticated. Editors remain entirely within Django-rendered admin. Astro does not handle user sessions.

---

## 11. File Structure

```
frontend/
├── astro.config.mjs
├── package.json
├── tailwind.config.mjs
├── tsconfig.json
├── src/
│   ├── layouts/
│   │   └── BaseLayout.astro
│   ├── pages/
│   │   ├── index.astro
│   │   └── preview.astro          # SSR preview route
│   ├── components/
│   │   ├── StatCard.svelte
│   │   ├── InfluenceGraph.svelte  # D3 force network
│   │   └── SankeyDiagram.svelte   # D3 Sankey
│   ├── stores/
│   │   └── filters.ts             # Nano Stores
│   └── styles/
│       ├── fonts.css              # Zodiak + Satoshi
│       └── tailwind.css
└── public/
    └── fonts/                     # Self-hosted Fontshare fonts
```

---

## 12. Implementation Order

1. **Archive**: Move `frontend/` → `frontend-react-archive/`
2. **Scaffold**: New Astro 5 + Svelte 5 project in `frontend/`
3. **Tailwind**: Configure with color tokens
4. **Fonts**: Self-host Zodiak + Satoshi from Fontshare
5. **Docker**: Update `web` service for Astro dev server
6. **API Connection**: Verify Astro can fetch from Django API
7. **First Component**: StatCard to validate the pipeline
8. **Influence Graph**: Homepage hero visualization