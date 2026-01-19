# UnderTheInfluence Frontend

Islands Architecture with React, TypeScript, and Vite.

## Overview

The frontend uses **Islands Architecture** - server-rendered HTML with selective React hydration. This provides:
- ✅ SEO benefits (server-rendered by default)
- ✅ Fast initial load (minimal JavaScript)
- ✅ Progressive enhancement (works without JS)
- ✅ Rich interactivity where needed (React islands)
- ✅ Shareable URLs (filter state in URL parameters)

## Technology Stack

- **Build System**: Vite 5.x
- **Framework**: React 18.x (selective hydration, not SPA)
- **Styling**: Bootstrap 5.x + CSS Modules (SCSS)
- **State**: Zustand (URL-synchronized)
- **Data**: TanStack React Query (5-minute cache)
- **Type Safety**: TypeScript

## Directory Structure

```
frontend/
├── components/         # Shared React components
│   ├── ActorCard.tsx
│   ├── StatCard.tsx
│   └── PartyCard.tsx
├── islands/           # Top-level interactive islands
│   ├── StatsGrid.tsx
│   ├── PartyBreakdown.tsx
│   ├── TopDonorsLeaderboard.tsx
│   ├── FilterPanel.tsx
│   └── ConcentrationChart.tsx
├── hooks/             # Custom React hooks
│   ├── useTopDonors.ts
│   └── useHomepageStats.ts
├── store/             # Zustand stores
│   └── filterStore.ts
├── types/             # TypeScript types
│   ├── actor.ts
│   └── filters.ts
├── styles/            # Global SCSS
├── islands.tsx        # Island loader/registry
├── main.tsx          # Vite entry point
├── package.json      # Dependencies
├── vite.config.ts    # Vite configuration
└── tsconfig.json     # TypeScript config
```

## Quick Start

```bash
# Install dependencies
npm install

# Start dev server (with HMR)
npm run dev

# Build for production
npm run build

# Type check
npm run type-check
```

## How It Works

### 1. Server Renders HTML

Django templates render initial HTML with `[data-island]` markers:

```html
<!-- cms/templates/cms/blocks/stats_grid.html -->
<div data-island="StatsGrid" data-api-url="/api/v2/aggregates/stats/">
    <!-- Server-rendered fallback for SEO/no-JS -->
    <div class="loading">Loading statistics...</div>
</div>
```

### 2. Islands Hydrate on Page Load

`islands.tsx` detects all `[data-island]` elements and hydrates them:

```typescript
// frontend/islands.tsx
const islands = {
  'StatsGrid': () => import('./islands/StatsGrid'),
  'PartyBreakdown': () => import('./islands/PartyBreakdown'),
  // ... more islands
};

// Lazy-load and hydrate
document.addEventListener('DOMContentLoaded', async () => {
  const islandElements = document.querySelectorAll('[data-island]');
  for (const el of islandElements) {
    const islandName = el.getAttribute('data-island');
    const { default: Component } = await islands[islandName]();
    const root = createRoot(el);
    root.render(<Component {...el.dataset} />);
  }
});
```

### 3. Islands Share State via URL

Filter state lives in URL parameters, enabling:
- Shareable links
- Browser back/forward navigation
- Multiple islands synchronized automatically

```typescript
// frontend/store/filterStore.ts
import { create } from 'zustand';

const useFilterStore = create((set) => ({
  dateFrom: undefined,
  dateTo: undefined,
  minValue: undefined,
  donorType: undefined,
  page: 1,
  setFilter: (updates) => {
    // Update URL parameters
    const params = new URLSearchParams(window.location.search);
    Object.entries(updates).forEach(([key, value]) => {
      if (value) params.set(key, value);
      else params.delete(key);
    });
    window.history.pushState({}, '', `?${params}`);

    // Update store
    set(updates);
  }
}));
```

### 4. Components Fetch from API v2

All islands consume `/api/v2/` endpoints:

```typescript
// frontend/islands/StatsGrid.tsx
function useHomepageStats() {
  const filters = useFilterStore();
  const queryParams = new URLSearchParams();
  if (filters.dateFrom) queryParams.set('received_after', ...);

  return useQuery({
    queryKey: ['homepage-stats', queryParams.toString()],
    queryFn: async () => {
      const response = await fetch(`/api/v2/aggregates/stats/?${queryParams}`);
      return response.json();
    }
  });
}
```

## Built Components

### Islands (Top-level containers)

**StatsGrid** - Homepage key metrics
- Displays 4 StatCards with live data from `/api/v2/aggregates/stats/`
- Metrics: Total donations, total value, concentration, dual influence
- Filters: Date range, min value, donor type
- Timestamp provenance

**PartyBreakdown** - Political party breakdown
- Grid of PartyCards with official colors
- Data from `/api/v2/aggregates/party-donations/`
- Shows: Total received, donor count, avg donation
- Filters: Date range, min value, donor type

**TopDonorsLeaderboard** - Ranked donor list
- Paginated leaderboard from `/api/v2/aggregates/top-donors/`
- Rank calculation accounts for current page
- Filters: Date range, min value, donor type

**FilterPanel** - Interactive filter controls
- Date range picker
- Minimum value selector
- Donor type chips
- Updates URL state (syncs all islands)

**ConcentrationChart** - Donor concentration visualization
- D3.js Pareto chart (planned)
- Gini coefficient, HHI, concentration metrics

### Components (Reusable primitives)

**StatCard** - Metric display
- Value, label, optional icon, variant (danger/warning/success)
- Timestamp for data provenance
- Click-through href support

**PartyCard** - Political party card
- Party name with official color accent bar
- Total received, donor count, avg donation
- Responsive layout, compact variant

**ActorCard** - Person/organization card (planned)
- Name, classification, image
- Donation statistics
- Click-through to profile page

## Adding New Islands

1. **Create the component**:
```typescript
// frontend/islands/MyIsland.tsx
export default function MyIsland({ apiUrl }: { apiUrl: string }) {
  const { data } = useQuery({
    queryKey: ['my-data'],
    queryFn: () => fetch(apiUrl).then(r => r.json())
  });

  return <div>{/* ... */}</div>;
}
```

2. **Register in islands.tsx**:
```typescript
const islands = {
  // ... existing
  'MyIsland': () => import('./islands/MyIsland'),
};
```

3. **Create Wagtail block** (optional):
```python
# cms/blocks.py
class MyIslandBlock(blocks.StructBlock):
    api_url = blocks.CharBlock(default="/api/v2/my-data/")

    class Meta:
        icon = 'snippet'
        label = 'My Island'
        template = 'cms/blocks/my_island.html'
```

4. **Create template** (optional):
```html
<!-- cms/templates/cms/blocks/my_island.html -->
<div data-island="MyIsland" data-api-url="{{ value.api_url }}">
    <!-- Server-rendered fallback -->
</div>
```

5. **Use in templates**:
```html
<div data-island="MyIsland" data-api-url="/api/v2/my-data/">
    Loading...
</div>
```

## Wagtail Integration

Editors can embed islands via custom StreamField blocks:

```python
# cms/blocks.py
class DataVisualizationBlock(blocks.StreamBlock):
    stats_grid = StatsGridBlock()
    party_breakdown = PartyBreakdownBlock()
    leaderboard = TopDonorsLeaderboardBlock()
    filter_panel = FilterPanelBlock()
```

In Wagtail admin:
1. Edit page → Add "Data Visualization" block
2. Choose island type (StatsGrid, PartyBreakdown, etc.)
3. Configure options (title, limit, filters)
4. Publish

## Development Workflow

### Local Development

```bash
# Terminal 1: Start Django API server
docker compose up -d

# Terminal 2: Start Vite dev server
cd frontend && npm run dev
```

Visit http://localhost:8000/ - Vite HMR will auto-reload on changes.

### Building for Production

```bash
# Build static assets
cd frontend && npm run build

# Django serves from static/dist/
docker compose restart api
```

### Type Checking

```bash
# Check types without emitting files
npm run type-check

# Watch mode
npm run type-check -- --watch
```

## API Endpoints

All islands consume `/api/v2/` endpoints:

| Endpoint | Used By | Filters |
|----------|---------|---------|
| `/api/v2/aggregates/stats/` | StatsGrid | date_range, value_min, donor_type |
| `/api/v2/aggregates/party-donations/` | PartyBreakdown | date_range, value_min, donor_type |
| `/api/v2/aggregates/top-donors/` | TopDonorsLeaderboard | date_range, value_min, donor_type, page |
| `/api/v2/aggregates/donor-concentration/` | ConcentrationChart | date_range, recipient |

## State Management

### URL State (Primary)

Filter state lives in URL parameters:
- **dateFrom** → `?date_from=2020-01-01`
- **dateTo** → `?date_to=2025-12-31`
- **minValue** → `?value_min=10000`
- **donorType** → `?donor_type=organization`
- **page** → `?page=2`

Benefits:
- Shareable links
- Browser back/forward works
- Deep linking support
- No client-side routing needed

### Zustand Store

`filterStore.ts` syncs with URL:

```typescript
const filters = useFilterStore();  // Read from URL
setFilter({ dateFrom: new Date('2020-01-01') });  // Update URL
```

All islands using `useFilterStore()` automatically refetch when filters change.

## Styling

### CSS Modules

All components use CSS Modules for scoped styling:

```typescript
import styles from './MyComponent.module.scss';

<div className={styles.container}>...</div>
```

### Bootstrap 5

Global Bootstrap classes available everywhere:

```html
<div className="container">
  <div className="row g-3">
    <div className="col-md-4">...</div>
  </div>
</div>
```

### Responsive Breakpoints

Bootstrap 5 breakpoints:
- **xs**: < 576px
- **sm**: ≥ 576px
- **md**: ≥ 768px
- **lg**: ≥ 992px
- **xl**: ≥ 1200px
- **xxl**: ≥ 1400px

## Performance

### Code Splitting

Islands are lazy-loaded:
- Only islands present on page are downloaded
- Each island is a separate chunk
- Total bundle ~40-60KB gzipped (vs 200KB+ for SPAs)

### Caching

React Query caches API responses:
- **staleTime**: 5 minutes (data is "fresh")
- **cacheTime**: 10 minutes (data stays in memory)
- No redundant API calls when navigating

### Progressive Enhancement

Without JavaScript:
- Server-rendered HTML shows immediately
- Forms submit to Django endpoints
- Links work normally
- Static content fully accessible

## Testing

```bash
# Run tests (when implemented)
npm test

# Coverage
npm run test:coverage
```

## Troubleshooting

### Islands not hydrating

1. Check console for errors
2. Verify island is registered in `islands.tsx`
3. Check `data-island` attribute matches exactly
4. Ensure Vite dev server is running

### Filters not working

1. Check `filterStore.ts` is initialized
2. Verify URL parameters are updating
3. Check React Query cache keys include filter state
4. Look for API errors in network tab

### Styles not applying

1. CSS Modules: Import as `import styles from './File.module.scss'`
2. Bootstrap: Use `className="container"` not `class=`
3. Check Vite is serving .scss files correctly

## Further Reading

- [Islands Architecture](https://jasonformat.com/islands-architecture/)
- [React Query Docs](https://tanstack.com/query/latest/docs/react/overview)
- [Vite Guide](https://vitejs.dev/guide/)
- [Zustand](https://github.com/pmndrs/zustand)
