# Frontend Implementation Plan: Islands Architecture & Modern UI

**Created**: 2026-01-14
**Phase**: 3.3 - Frontend UI & Editorial Integration
**Status**: Ready for Implementation
**Estimated Duration**: 6-8 weeks
**Author**: Claude Code (based on architectural strategy documents)

---

## Executive Summary

This plan transforms the UnderTheInfluence frontend from a traditional server-rendered Django application to a modern **Islands Architecture** application with selective React hydration, while maintaining SEO benefits and progressive enhancement.

**Current State:**
- Traditional Django templates with Bootstrap 3 + Material Design
- jQuery-based interactions (~67 lines of custom JavaScript)
- No build system (django-compressor only)
- API v2 endpoints fully implemented and ready for consumption

**Target State:**
- **Islands Architecture**: Server-rendered HTML with selective React hydration
- **Vite build system**: Modern ES modules, code splitting, TypeScript
- **Bootstrap 5**: Remove jQuery dependency
- **URL-driven state**: Shareable filter states via URL parameters
- **Data Cards**: Universal component primitive for all entities
- **Wagtail integration**: Custom StreamField blocks with live data

**Why Islands Architecture (Not Full SPA)?**
- ✅ SEO-friendly (server-rendered by default)
- ✅ Fast initial load (minimal JavaScript)
- ✅ Progressive enhancement (works without JS)
- ✅ Natural Django integration
- ✅ Wagtail CMS compatibility
- ✅ **Minimal React** - only where needed, not everywhere

---

## Is React Overkill? (Spoiler: No, but Islands Architecture Keeps It Minimal)

**Your Requirements:**
- ✅ **Rich interactivity**: Network graphs, advanced filtering, synchronized views
- ✅ **Long-term maintainability**: Component-based architecture, TypeScript safety
- ✅ **Complex visualizations**: D3.js integration, real-time updates

**Why React Islands (Not HTMX/Alpine.js):**

| Framework | Good For | Not Ideal For |
|-----------|----------|---------------|
| **HTMX** | Server-driven interactions, simple updates | Complex client-side state, real-time charts |
| **Alpine.js** | Simple interactivity, lightweight widgets | Network graphs, complex data synchronization |
| **React Islands** ✅ | Rich visualizations, synchronized filters, maintainable components | Simple static pages (use server rendering) |
| **React SPA** ❌ | Single-page apps | Multi-page Django sites (SEO issues, complexity) |

**What Makes Islands "Minimal React":**
- 🎯 React only loads for interactive components (filters, charts, tables)
- 🎯 95% of the page is server-rendered HTML
- 🎯 JavaScript bundle is ~40-60KB gzipped (not 200KB+ like SPAs)
- 🎯 Progressive enhancement - works without JavaScript
- 🎯 No client-side routing - Django handles all navigation

**The Right Balance:**
- Static content: Django templates (fast, SEO-friendly)
- Interactive widgets: React islands (when needed)
- D3.js visualizations: React wrapper for lifecycle management
- Forms/search: Server-rendered with optional React enhancement

---

## Phase 1: Build System Foundation (Week 1)

### 1.1 Vite Setup

**Goal**: Replace django-compressor with Vite for modern asset pipeline

**Files to Create:**
- `package.json` - NPM dependencies
- `vite.config.js` - Vite configuration
- `tsconfig.json` - TypeScript configuration
- `frontend/` - New directory for all frontend source code
  - `frontend/islands/` - React island components
  - `frontend/components/` - Shared React components
  - `frontend/lib/` - Utility functions
  - `frontend/types/` - TypeScript type definitions
  - `frontend/styles/` - CSS/SCSS files

**Files to Modify:**
- `undertheinfluence/settings.py` - Add django-vite configuration
- `requirements.txt` - Add `django-vite>=3.0.0`
- `undertheinfluence/templates/base.html` - Use `{% vite_asset %}` template tags

**Dependencies to Install:**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.0.0",
    "bootstrap": "^5.3.0",
    "zustand": "^4.5.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.0.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "sass": "^1.70.0"
  }
}
```

**Vite Configuration:**
```javascript
// vite.config.js
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
```

**Django Settings:**
```python
# settings.py additions
INSTALLED_APPS += ['django_vite']

DJANGO_VITE = {
    'default': {
        'dev_mode': DEBUG,
        'dev_server_host': 'vite' if DEBUG else 'localhost',
        'dev_server_port': 5173,
        'manifest_path': BASE_DIR / 'static' / 'dist' / 'manifest.json',
    }
}
```

**Docker Integration:**

Add Vite service to `docker-compose.yml`:
```yaml
# docker-compose.yml additions
services:
  vite:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - .:/app
      - /app/node_modules  # Anonymous volume to prevent host overwrite
    command: npm run dev
    ports:
      - "5173:5173"
    environment:
      - NODE_ENV=development
    depends_on:
      - web

  web:
    # ... existing web service config ...
    environment:
      - DJANGO_VITE_DEV_SERVER_HOST=vite  # Point to vite service
```

**NPM Scripts in package.json:**
```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "type-check": "tsc --noEmit"
  }
}
```

**Docker Development Workflow:**
```bash
# Start all services (Django + Vite)
docker compose up -d

# Vite dev server runs on http://localhost:5173
# Django server proxies Vite assets in development

# For production build inside container
docker compose exec web npm run build
docker compose exec web python manage.py collectstatic --noinput
```

**Success Criteria:**
- `npm install` completes successfully (in Docker or locally)
- `docker compose up` starts both Django and Vite services
- Vite dev server accessible at http://localhost:5173
- Django templates load Vite assets via `{% vite_asset 'main' %}`
- Hot module replacement (HMR) works when editing React components
- Production build generates manifest.json in static/dist/

---

### 1.2 Bootstrap 5 Migration

**Goal**: Remove jQuery dependency, upgrade to Bootstrap 5

**Files to Modify:**
- `undertheinfluence/templates/base.html` - Remove Bootstrap 3 CDN links
- `datafetch/templates/person.html` - Update Bootstrap classes
- `datafetch/templates/organization.html` - Update Bootstrap classes
- Remove Material Design theme dependencies

**Bootstrap 5 Changes:**
- `.panel` → `.card`
- `.panel-body` → `.card-body`
- `.panel-heading` → `.card-header`
- Remove `.glyphicon-*` (use Bootstrap Icons instead)
- Data attributes: `data-toggle` → `data-bs-toggle`

**New Base Template Structure:**
```html
<!-- base.html -->
{% load django_vite %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}UnderTheInfluence{% endblock %}</title>
    {% vite_asset 'main.css' %}
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <!-- Navigation -->
    </nav>

    <main class="container my-4">
        {% block content %}{% endblock %}
    </main>

    <footer class="bg-light py-4 mt-5">
        <!-- Footer -->
    </footer>

    {% vite_asset 'main.js' %}
    {% block extra_js %}{% endblock %}
</body>
</html>
```

**Success Criteria:**
- No jQuery dependencies remaining
- Bootstrap 5 loads correctly
- Existing pages render without layout breaks
- Responsive behavior works on mobile

---

## Phase 2: Islands Architecture Core (Week 2-3)

### 2.1 Island Loader System

**Goal**: Create the hydration system for React islands

**Files to Create:**
- `frontend/islands.tsx` - Island registration and hydration
- `frontend/types/islands.ts` - TypeScript interfaces

**Island Loader Implementation:**
```typescript
// frontend/islands.tsx
import { createRoot } from 'react-dom/client';

// Island registry (lazy-loaded)
const islands = {
  'SearchBar': () => import('./islands/SearchBar'),
  'FilterPanel': () => import('./islands/FilterPanel'),
  'ActorCard': () => import('./islands/ActorCard'),
  'TopDonorsLeaderboard': () => import('./islands/TopDonorsLeaderboard'),
  'ConcentrationChart': () => import('./islands/ConcentrationChart'),
};

// Hydrate all islands on page
document.addEventListener('DOMContentLoaded', async () => {
  const islandElements = document.querySelectorAll('[data-island]');

  for (const el of islandElements) {
    const islandName = el.getAttribute('data-island');
    const loader = islands[islandName];

    if (!loader) {
      console.warn(`Unknown island: ${islandName}`);
      continue;
    }

    try {
      const { default: Component } = await loader();

      // Extract data-* attributes as props
      const props = { ...el.dataset };
      delete props.island;

      // Hydrate
      const root = createRoot(el);
      root.render(<Component {...props} />);
    } catch (err) {
      console.error(`Failed to load island ${islandName}:`, err);
    }
  }
});
```

**Template Usage Pattern:**
```html
<!-- Server-rendered fallback -->
<div id="search-island"
     data-island="SearchBar"
     data-api-url="/api/v2/actors/"
     data-placeholder="Search donors, MPs, organizations...">
    <!-- Static HTML for SEO/no-JS -->
    <form action="/search/" method="GET">
        <input type="search" name="q" placeholder="Search...">
        <button type="submit">Search</button>
    </form>
</div>
```

**Success Criteria:**
- Island loader detects and hydrates all `[data-island]` elements
- Lazy loading works (only loads islands present on page)
- Graceful degradation (server-rendered content shows if JS fails)

---

### 2.2 URL-Driven State Management (Zustand)

**Goal**: Implement URL parameter synchronization for filter state using Zustand

**Why Zustand over Custom Events:**
- Prevents "event soup" and race conditions as islands grow
- Provides predictable state update ordering
- Better TypeScript support and DevTools integration
- Lightweight (1KB gzipped) with no boilerplate

**Files to Create:**
- `frontend/store/filterStore.ts` - Zustand store for filter state
- `frontend/types/filters.ts` - Filter state TypeScript types

**Implementation:**
```typescript
// frontend/types/filters.ts
export type PartialDate = {
  value: string; // YYYY, YYYY-MM, or YYYY-MM-DD
  precision: 'year' | 'month' | 'day';
};

export interface FilterState {
  dateFrom?: PartialDate;
  dateTo?: PartialDate;
  minValue?: number;
  maxValue?: number;
  donorType?: 'individual' | 'organization' | 'trade-union' | 'company';
  recipientType?: 'person' | 'party' | 'organization';
  hasLobbying?: boolean;
  page: number;
  limit: number;
  query?: string;
}

// frontend/store/filterStore.ts
import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

interface FilterStore extends FilterState {
  setFilter: (updates: Partial<FilterState>, resetPage?: boolean) => void;
  resetFilters: () => void;
  loadFromUrl: () => void;
}

const DEFAULT_STATE: FilterState = {
  page: 1,
  limit: 20,
};

// Parse URL params to filter state
function parseUrlParams(): Partial<FilterState> {
  const params = new URLSearchParams(window.location.search);
  return {
    dateFrom: params.get('date_from')
      ? parsePartialDate(params.get('date_from')!)
      : undefined,
    dateTo: params.get('date_to')
      ? parsePartialDate(params.get('date_to')!)
      : undefined,
    minValue: params.get('min_value') ? Number(params.get('min_value')) : undefined,
    donorType: params.get('donor_type') as FilterState['donorType'],
    hasLobbying: params.get('has_lobbying') === 'true' ? true : undefined,
    page: Number(params.get('page')) || 1,
    limit: Number(params.get('limit')) || 20,
    query: params.get('q') || undefined,
  };
}

// Serialize filter state to URL
function syncToUrl(state: FilterState, replace = false) {
  const params = new URLSearchParams();

  if (state.dateFrom) params.set('date_from', state.dateFrom.value);
  if (state.dateTo) params.set('date_to', state.dateTo.value);
  if (state.minValue) params.set('min_value', String(state.minValue));
  if (state.donorType) params.set('donor_type', state.donorType);
  if (state.hasLobbying) params.set('has_lobbying', 'true');
  if (state.page > 1) params.set('page', String(state.page));
  if (state.limit !== 20) params.set('limit', String(state.limit));
  if (state.query) params.set('q', state.query);

  const url = `${window.location.pathname}?${params.toString()}`;

  if (replace) {
    window.history.replaceState({}, '', url);
  } else {
    window.history.pushState({}, '', url);
  }
}

export const useFilterStore = create<FilterStore>()(
  subscribeWithSelector((set, get) => ({
    ...DEFAULT_STATE,

    setFilter: (updates, resetPage = false) => {
      set((state) => {
        const newState = {
          ...state,
          ...updates,
          page: resetPage ? 1 : (updates.page ?? state.page)
        };
        syncToUrl(newState);
        return newState;
      });
    },

    resetFilters: () => {
      set(DEFAULT_STATE);
      syncToUrl(DEFAULT_STATE);
    },

    loadFromUrl: () => {
      const urlState = parseUrlParams();
      set((state) => ({ ...state, ...urlState }));
    },
  }))
);

// Initialize from URL on page load
if (typeof window !== 'undefined') {
  useFilterStore.getState().loadFromUrl();

  // Handle browser back/forward
  window.addEventListener('popstate', () => {
    useFilterStore.getState().loadFromUrl();
  });
}

// Helper to parse partial dates
function parsePartialDate(value: string): PartialDate {
  const parts = value.split('-');
  if (parts.length === 1) {
    return { value, precision: 'year' };
  } else if (parts.length === 2) {
    return { value, precision: 'month' };
  } else {
    return { value, precision: 'day' };
  }
}
```

**Usage in Islands:**
```typescript
// In any island component
import { useFilterStore } from '../store/filterStore';

export function FilterPanel() {
  const { dateFrom, dateTo, minValue, donorType, setFilter, resetFilters } = useFilterStore();

  return (
    <div className="filter-panel">
      <PartialDateInput
        value={dateFrom}
        onChange={(date) => setFilter({ dateFrom: date }, true)}
      />
      {/* ... other filters ... */}
      <button onClick={resetFilters}>Clear Filters</button>
    </div>
  );
}
```

**Success Criteria:**
- URL parameters update when filters change
- Browser back/forward navigation works correctly
- Multiple islands stay synchronized via Zustand store
- URLs are shareable (same state restored from URL)
- No race conditions between island updates

---

## Phase 3: Core Components (Week 3-4)

### 3.1 Partial Date Input Component

**Goal**: Create custom date input supporting Popolo partial dates (YYYY, YYYY-MM, YYYY-MM-DD)

**Why This Is Critical:**
- Backend data uses partial dates extensively (birth dates, start/end dates)
- Standard HTML `<input type="date">` requires full YYYY-MM-DD format
- Users need to filter by year-only or month-only precision

**Files to Create:**
- `frontend/components/PartialDateInput.tsx`
- `frontend/components/PartialDateInput.module.scss`

**Implementation:**
```typescript
// frontend/components/PartialDateInput.tsx
import { useState } from 'react';
import type { PartialDate } from '../types/filters';
import styles from './PartialDateInput.module.scss';

interface PartialDateInputProps {
  value?: PartialDate;
  onChange: (date?: PartialDate) => void;
  label?: string;
  placeholder?: string;
}

export function PartialDateInput({ value, onChange, label, placeholder }: PartialDateInputProps) {
  const [precision, setPrecision] = useState<'year' | 'month' | 'day'>(
    value?.precision ?? 'day'
  );

  const parts = value?.value.split('-') ?? [];
  const [year, setYear] = useState(parts[0] ?? '');
  const [month, setMonth] = useState(parts[1] ?? '');
  const [day, setDay] = useState(parts[2] ?? '');

  const handleChange = (newYear: string, newMonth: string, newDay: string, newPrecision: typeof precision) => {
    let dateValue: string;

    if (newPrecision === 'year') {
      dateValue = newYear;
    } else if (newPrecision === 'month') {
      dateValue = `${newYear}-${newMonth.padStart(2, '0')}`;
    } else {
      dateValue = `${newYear}-${newMonth.padStart(2, '0')}-${newDay.padStart(2, '0')}`;
    }

    if (!newYear) {
      onChange(undefined);
      return;
    }

    onChange({ value: dateValue, precision: newPrecision });
  };

  return (
    <div className={styles.partialDateInput}>
      {label && <label className={styles.label}>{label}</label>}

      <div className={styles.precisionToggle}>
        <button
          type="button"
          className={precision === 'year' ? styles.active : ''}
          onClick={() => {
            setPrecision('year');
            handleChange(year, month, day, 'year');
          }}
        >
          Year
        </button>
        <button
          type="button"
          className={precision === 'month' ? styles.active : ''}
          onClick={() => {
            setPrecision('month');
            handleChange(year, month, day, 'month');
          }}
        >
          Month
        </button>
        <button
          type="button"
          className={precision === 'day' ? styles.active : ''}
          onClick={() => {
            setPrecision('day');
            handleChange(year, month, day, 'day');
          }}
        >
          Day
        </button>
      </div>

      <div className={styles.inputs}>
        <input
          type="number"
          placeholder="YYYY"
          value={year}
          onChange={(e) => {
            setYear(e.target.value);
            handleChange(e.target.value, month, day, precision);
          }}
          min="1900"
          max="2100"
          className={styles.yearInput}
        />

        {(precision === 'month' || precision === 'day') && (
          <input
            type="number"
            placeholder="MM"
            value={month}
            onChange={(e) => {
              setMonth(e.target.value);
              handleChange(year, e.target.value, day, precision);
            }}
            min="1"
            max="12"
            className={styles.monthInput}
          />
        )}

        {precision === 'day' && (
          <input
            type="number"
            placeholder="DD"
            value={day}
            onChange={(e) => {
              setDay(e.target.value);
              handleChange(year, month, e.target.value, precision);
            }}
            min="1"
            max="31"
            className={styles.dayInput}
          />
        )}
      </div>
    </div>
  );
}
```

**Scoped Styles (CSS Modules):**
```scss
// frontend/components/PartialDateInput.module.scss
.partialDateInput {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;

  .label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--bs-body-color);
  }

  .precisionToggle {
    display: flex;
    gap: 0.25rem;

    button {
      padding: 0.375rem 0.75rem;
      border: 1px solid var(--bs-border-color);
      background: white;
      border-radius: 0.25rem;
      cursor: pointer;
      font-size: 0.875rem;
      transition: all 0.15s ease;

      &:hover {
        background: var(--bs-light);
      }

      &.active {
        background: var(--bs-primary);
        color: white;
        border-color: var(--bs-primary);
      }
    }
  }

  .inputs {
    display: flex;
    gap: 0.5rem;

    input {
      padding: 0.5rem;
      border: 1px solid var(--bs-border-color);
      border-radius: 0.25rem;
      font-size: 1rem;

      &.yearInput {
        width: 5rem;
      }

      &.monthInput,
      &.dayInput {
        width: 3.5rem;
      }

      &:focus {
        outline: none;
        border-color: var(--bs-primary);
        box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25);
      }
    }
  }
}
```

**Success Criteria:**
- Component supports year-only precision (e.g., "2020")
- Component supports month precision (e.g., "2020-06")
- Component supports full date precision (e.g., "2020-06-15")
- Switching precision maintains entered values where possible
- CSS Modules prevent style conflicts with server-rendered content
- Compatible with backend partial date format

---

### 3.2 Data Card Component

**Goal**: Create universal ActorCard component used everywhere

**Files to Create:**
- `frontend/components/ActorCard.tsx`
- `frontend/types/actor.ts`

**Implementation:**
```typescript
// frontend/types/actor.ts
export interface Actor {
  id: number;
  name: string;
  actor_type: 'person' | 'organization';
  classification?: string;
  image?: string;
}

export interface ActorCardProps {
  actor: Actor;
  stats?: {
    totalDonated?: number;
    totalReceived?: number;
    donationCount?: number;
    isLobbyingClient?: boolean;
  };
  compact?: boolean;
  onClick?: () => void;
}

// frontend/components/ActorCard.tsx
export function ActorCard({
  actor,
  stats,
  compact = false,
  onClick
}: ActorCardProps) {
  const profileUrl = actor.actor_type === 'person'
    ? `/person/${actor.id}/`
    : `/organization/${actor.id}/`;

  if (compact) {
    return (
      <a href={profileUrl} className="actor-card actor-card--compact">
        {actor.image && (
          <img src={actor.image} alt="" className="actor-card__image" />
        )}
        <div className="actor-card__content">
          <h3 className="actor-card__name">{actor.name}</h3>
          <p className="actor-card__type">{actor.classification || actor.actor_type}</p>
        </div>
        {stats?.totalDonated && (
          <span className="actor-card__stat">
            {formatCurrency(stats.totalDonated)}
          </span>
        )}
      </a>
    );
  }

  // Full card version with stats...
}
```

**Usage in Templates:**
```html
<!-- Server-rendered fallback -->
<div data-island="ActorCard"
     data-actor-id="123"
     data-actor-name="David Sainsbury"
     data-actor-type="person"
     data-total-donated="47900000">
    <!-- Static HTML for SEO -->
    <a href="/person/123/">
        <h3>David Sainsbury</h3>
        <p>Individual Donor | £47.9M</p>
    </a>
</div>
```

**Success Criteria:**
- ActorCard renders correctly in both compact and full modes
- Works in lists (search results, leaderboards)
- Works standalone (profile page headers)
- Server-rendered fallback works without JavaScript

---

### 3.3 Filter Panel Island

**Goal**: Create universal filter interface for all data views

**Files to Create:**
- `frontend/islands/FilterPanel.tsx`
- `frontend/islands/FilterPanel.module.scss`

**Implementation:**
```typescript
// frontend/islands/FilterPanel.tsx
import { useFilterStore } from '../store/filterStore';
import { PartialDateInput } from '../components/PartialDateInput';
import styles from './FilterPanel.module.scss';

export function FilterPanel() {
  const { dateFrom, dateTo, minValue, donorType, hasLobbying, setFilter, resetFilters } = useFilterStore();

  return (
    <div className={`${styles.filterPanel} card`}>
      <div className="card-body">
        {/* Date Range with Partial Date Support */}
        <div className="mb-4">
          <h6 className={styles.sectionTitle}>Date Range</h6>
          <div className="row g-3">
            <div className="col-md-6">
              <PartialDateInput
                label="From"
                value={dateFrom}
                onChange={(date) => setFilter({ dateFrom: date }, true)}
              />
            </div>
            <div className="col-md-6">
              <PartialDateInput
                label="To"
                value={dateTo}
                onChange={(date) => setFilter({ dateTo: date }, true)}
              />
            </div>
          </div>
        </div>

        {/* Minimum Value */}
        <div className="mb-4">
          <label className="form-label">Minimum Value</label>
          <select
            className="form-select"
            value={minValue || ''}
            onChange={(e) => setFilter({
              minValue: e.target.value ? Number(e.target.value) : undefined
            }, true)}
          >
            <option value="">Any amount</option>
            <option value="1000">£1,000+</option>
            <option value="10000">£10,000+</option>
            <option value="100000">£100,000+</option>
            <option value="1000000">£1,000,000+</option>
          </select>
        </div>

        {/* Donor Type Chips */}
        <div className="mb-4">
          <label className="form-label">Donor Type</label>
          <div className={styles.chipGroup}>
            {['individual', 'organization', 'trade-union', 'company'].map(type => (
              <button
                key={type}
                type="button"
                className={`${styles.chip} ${donorType === type ? styles.active : ''}`}
                onClick={() => setFilter({
                  donorType: donorType === type ? undefined : type as any
                }, true)}
              >
                {type.replace('-', ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Lobbying Overlap Toggle */}
        <div className="mb-4">
          <div className="form-check">
            <input
              className="form-check-input"
              type="checkbox"
              id="hasLobbying"
              checked={hasLobbying || false}
              onChange={(e) => setFilter({
                hasLobbying: e.target.checked || undefined
              }, true)}
            />
            <label className="form-check-label" htmlFor="hasLobbying">
              Only show donors with lobbying activity
            </label>
          </div>
        </div>

        {/* Clear Filters */}
        <button
          className="btn btn-outline-secondary btn-sm w-100"
          onClick={resetFilters}
        >
          Clear All Filters
        </button>
      </div>
    </div>
  );
}
```

**Scoped Styles:**
```scss
// frontend/islands/FilterPanel.module.scss
.filterPanel {
  .sectionTitle {
    font-size: 0.875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--bs-secondary);
    margin-bottom: 0.75rem;
  }

  .chipGroup {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;

    .chip {
      padding: 0.5rem 1rem;
      border: 1px solid var(--bs-border-color);
      background: white;
      border-radius: 1.5rem;
      cursor: pointer;
      font-size: 0.875rem;
      transition: all 0.2s ease;
      text-transform: capitalize;

      &:hover {
        background: var(--bs-light);
        border-color: var(--bs-primary);
      }

      &.active {
        background: var(--bs-primary);
        color: white;
        border-color: var(--bs-primary);
      }
    }
  }
}
```

**Template Integration:**
```html
<!-- In search.html or any data listing page -->
<div class="row">
  <div class="col-md-3">
    <div data-island="FilterPanel"></div>
  </div>
  <div class="col-md-9">
    <div data-island="TopDonorsLeaderboard" data-api-url="/api/v2/aggregates/top-donors/"></div>
  </div>
</div>
```

**Success Criteria:**
- Filter changes update URL immediately
- Other islands (charts, tables) react to filter changes
- Browser back button restores previous filter state
- Shareable URLs preserve filter selections

---

### 3.4 Top Donors Leaderboard Island

**Goal**: Interactive leaderboard consuming API v2 top-donors endpoint

**Files to Create:**
- `frontend/islands/TopDonorsLeaderboard.tsx`
- `frontend/hooks/useTopDonors.ts`

**Implementation:**
```typescript
// frontend/hooks/useTopDonors.ts
import { useQuery } from '@tanstack/react-query';
import { useFilterStore } from '../store/filterStore';

export function useTopDonors(limit: number = 20) {
  const { dateFrom, dateTo, minValue, donorType, hasLobbying, page } = useFilterStore();

  const queryParams = new URLSearchParams();

  // Handle partial dates - send only the value string to backend
  if (dateFrom) queryParams.set('received_after', dateFrom.value);
  if (dateTo) queryParams.set('received_before', dateTo.value);

  if (minValue) queryParams.set('value_min', String(minValue));
  if (donorType) queryParams.set('donor_type', donorType);
  if (hasLobbying) queryParams.set('has_lobbying', 'true');
  queryParams.set('limit', String(limit));
  queryParams.set('offset', String((page - 1) * limit));

  return useQuery({
    queryKey: ['top-donors', queryParams.toString()],
    queryFn: async () => {
      const response = await fetch(`/api/v2/aggregates/top-donors/?${queryParams}`);
      if (!response.ok) throw new Error('Failed to fetch donors');
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// frontend/islands/TopDonorsLeaderboard.tsx
export function TopDonorsLeaderboard({ limit = 20 }) {
  const { data, isLoading, error } = useTopDonors(limit);

  if (isLoading) return <div className="spinner-border" />;
  if (error) return <div className="alert alert-danger">Failed to load leaderboard</div>;

  return (
    <div className="leaderboard">
      <h2>Top Donors</h2>
      <ol className="list-group list-group-numbered">
        {data.results.map((donor, index) => (
          <li key={donor.actor.id} className="list-group-item d-flex justify-content-between align-items-start">
            <div className="ms-2 me-auto">
              <div className="fw-bold">{donor.actor.name}</div>
              <small>{donor.actor.classification || donor.actor.actor_type}</small>
              <small className="text-muted"> • {donor.donation_count} donations</small>
            </div>
            <span className="badge bg-primary rounded-pill">
              {formatCurrency(donor.total_donated)}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
```

**Success Criteria:**
- Leaderboard loads from API v2 /aggregates/top-donors/
- Updates automatically when FilterPanel changes
- Pagination works (page parameter in URL)
- Shows loading state during fetch
- Error handling displays user-friendly message

---

## Phase 4: Visualization Components (Week 5)

### 4.1 Concentration Chart (Pareto Distribution)

**Goal**: Visualize donor concentration (whale donors vs long tail)

**Files to Create:**
- `frontend/islands/ConcentrationChart.tsx`
- `frontend/hooks/useConcentration.ts`

**Dependencies:**
```bash
npm install d3 @types/d3
```

**Implementation:**
```typescript
// frontend/hooks/useConcentration.ts
export function useConcentration() {
  const filters = useUrlState();

  return useQuery({
    queryKey: ['concentration', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.dateFrom) params.set('received_after', filters.dateFrom.toISOString().split('T')[0]);
      if (filters.dateTo) params.set('received_before', filters.dateTo.toISOString().split('T')[0]);

      const response = await fetch(`/api/v2/aggregates/donor-concentration/?${params}`);
      return response.json();
    },
  });
}

// frontend/islands/ConcentrationChart.tsx
import * as d3 from 'd3';

export function ConcentrationChart() {
  const svgRef = useRef<SVGSVGElement>(null);
  const { data, isLoading } = useConcentration();

  useEffect(() => {
    if (!data || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const width = 600;
    const height = 300;

    // Create Pareto chart visualization
    // Show top 10% vs bottom 90% concentration
    // Highlight inequality metrics (Gini, HHI)

  }, [data]);

  if (isLoading) return <div className="spinner-border" />;

  return (
    <div className="concentration-chart card">
      <div className="card-body">
        <h3>Donor Concentration</h3>
        <svg ref={svgRef} width={600} height={300} />
        {data && (
          <div className="metrics mt-3">
            <div className="row">
              <div className="col">
                <strong>Gini Coefficient:</strong> {data.gini_coefficient.toFixed(2)}
              </div>
              <div className="col">
                <strong>Top 10% Share:</strong> {(data.top_10_percent_share * 100).toFixed(1)}%
              </div>
              <div className="col">
                <strong>Category:</strong> {data.concentration_category}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

**Success Criteria:**
- D3.js chart renders concentration data
- Visual distinction between top 10% and bottom 90%
- Displays Gini coefficient, HHI, and concentration category
- Updates when filters change

---

## Phase 5: Wagtail Editorial Integration (Week 6)

### 5.1 Custom StreamField Blocks

**Goal**: Create data-aware blocks for editorial content

**Files to Create:**
- `cms/blocks.py` - Custom Wagtail blocks
- `cms/templates/cms/blocks/` - Block templates

**Implementation:**
```python
# cms/blocks.py
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

class ActorChooserBlock(blocks.StructBlock):
    """Embed an actor card in editorial content."""
    actor_id = blocks.IntegerBlock(help_text="Actor ID from the political database")
    display_mode = blocks.ChoiceBlock(
        choices=[
            ('card', 'Full Card'),
            ('inline', 'Inline Mention'),
            ('stats', 'Stats Only'),
        ],
        default='card'
    )
    custom_description = blocks.RichTextBlock(
        required=False,
        help_text="Optional editorial override of actor description"
    )

    class Meta:
        icon = 'user'
        label = 'Actor Card'
        template = 'cms/blocks/actor_card.html'


class LiveStatBlock(blocks.StructBlock):
    """Display a live statistic from the database."""
    stat_type = blocks.ChoiceBlock(
        choices=[
            ('top_donor_total', 'Top Donor Total'),
            ('total_donations', 'Total Donations'),
            ('lobbying_overlap_count', 'Lobbying-Donation Overlap Count'),
            ('concentration_pct', 'Top 1% Concentration'),
        ]
    )
    label = blocks.CharBlock(
        required=False,
        help_text="Override the default label"
    )
    cached_value = blocks.CharBlock(
        required=False,
        help_text="Fallback value if API is unavailable"
    )

    class Meta:
        icon = 'doc-full'
        label = 'Live Statistic'
        template = 'cms/blocks/live_stat.html'


class LeaderboardBlock(blocks.StructBlock):
    """Embed a leaderboard in editorial content."""
    leaderboard_type = blocks.ChoiceBlock(
        choices=[
            ('top_donors', 'Top Donors'),
            ('top_recipients', 'Top Recipients'),
            ('dual_influence', 'Lobbying-Donation Overlap'),
        ]
    )
    limit = blocks.IntegerBlock(default=10, min_value=5, max_value=50)
    filters = blocks.CharBlock(
        required=False,
        help_text='JSON filter object (e.g., {"donor_type": "trade-union"})'
    )

    class Meta:
        icon = 'list-ol'
        label = 'Leaderboard'
        template = 'cms/blocks/leaderboard.html'
```

**Block Templates:**
```html
<!-- cms/templates/cms/blocks/actor_card.html -->
<div data-island="ActorCard"
     data-actor-id="{{ self.actor_id }}"
     data-display-mode="{{ self.display_mode }}">
    <!-- Server-rendered fallback from Django -->
    {% with actor=self.get_actor %}
    <a href="{% if actor.actor_type == 'person' %}/person/{{ actor.id }}/{% else %}/organization/{{ actor.id }}/{% endif %}">
        <h3>{{ actor.name }}</h3>
        <p>{{ actor.classification }}</p>
    </a>
    {% endwith %}
</div>

<!-- cms/templates/cms/blocks/leaderboard.html -->
<div data-island="TopDonorsLeaderboard"
     data-leaderboard-type="{{ self.leaderboard_type }}"
     data-limit="{{ self.limit }}"
     data-filters="{{ self.filters }}">
    <!-- Server-rendered fallback -->
    <h3>{{ self.get_title }}</h3>
    <p>Loading leaderboard...</p>
</div>
```

**Success Criteria:**
- Editors can add ActorChooserBlock to pages
- Actor cards render with live data from API
- LiveStatBlock shows current statistics
- LeaderboardBlock embeds interactive leaderboards
- All blocks have server-rendered fallbacks for SEO

---

### 5.2 ActorMention Model & Signals

**Goal**: Track relationships between editorial pages and actors

**Files to Create:**
- `editorial/` - New app for CMS-data relationships
- `editorial/models.py` - ActorMention model
- `editorial/signals.py` - Django signals for lifecycle management

**Implementation:**
```python
# editorial/models.py
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from wagtail.models import Page

class ActorMention(models.Model):
    """
    Links a Wagtail page to a political actor.
    Enables "Related Articles" on actor profiles.
    """
    RELATIONSHIP_TYPES = [
        ('mentioned', 'Mentioned'),
        ('profiled', 'Primary Subject'),
        ('cited', 'Data Source'),
    ]

    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name='actor_mentions'
    )
    actor_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'app_label': 'datafetch', 'model__in': ['person', 'organization']}
    )
    actor_id = models.PositiveIntegerField()
    actor = GenericForeignKey('actor_content_type', 'actor_id')

    relationship_type = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_TYPES,
        default='mentioned'
    )
    weight = models.PositiveSmallIntegerField(
        default=1,
        help_text="Editorial importance (higher = more prominent)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['page', 'actor_content_type', 'actor_id']
        ordering = ['-weight', '-created_at']
        indexes = [
            models.Index(fields=['actor_content_type', 'actor_id']),
        ]


# editorial/signals.py
from django.db.models.signals import post_delete
from django.dispatch import receiver
from wagtail.signals import page_published
from .models import ActorMention

@receiver(post_delete, sender=Page)
def cleanup_actor_mentions(sender, instance, **kwargs):
    """Clean up ActorMention records when a page is deleted."""
    ActorMention.objects.filter(page_id=instance.pk).delete()


@receiver(page_published)
def sync_actor_mentions(sender, instance, **kwargs):
    """
    Update ActorMention records when a page is published.
    Extracts all actor references from StreamField content.
    """
    from .utils import extract_actor_mentions_from_page

    current_mentions = extract_actor_mentions_from_page(instance)
    existing_mentions = set(
        ActorMention.objects.filter(page=instance)
        .values_list('actor_content_type_id', 'actor_id', 'relationship_type')
    )

    # Create new mentions
    for mention_data in current_mentions:
        key = (
            mention_data['actor_content_type_id'],
            mention_data['actor_id'],
            mention_data['relationship_type']
        )
        if key not in existing_mentions:
            ActorMention.objects.create(page=instance, **mention_data)

    # Remove stale mentions
    # (Implementation details...)
```

**Success Criteria:**
- ActorMention records created automatically when pages published
- Actor profile pages show "Related Articles" section
- Page deletion cleans up orphaned mentions
- Signals handle page unpublishing correctly

---

## Phase 6: Testing & Documentation (Week 7-8)

### 6.1 Component Testing

**Files to Create:**
- `frontend/__tests__/` - Jest test directory
- `vitest.config.ts` - Vitest configuration (faster than Jest)

**Test Coverage:**
- ActorCard rendering with various props
- FilterPanel state management
- URL parameter parsing/serialization
- Island hydration
- API fetch mocking with React Query

**Example Test:**
```typescript
// frontend/__tests__/ActorCard.test.tsx
import { render, screen } from '@testing-library/react';
import { ActorCard } from '../components/ActorCard';

describe('ActorCard', () => {
  it('renders person card correctly', () => {
    const actor = {
      id: 123,
      name: 'David Sainsbury',
      actor_type: 'person',
    };

    render(<ActorCard actor={actor} />);

    expect(screen.getByText('David Sainsbury')).toBeInTheDocument();
    expect(screen.getByRole('link')).toHaveAttribute('href', '/person/123/');
  });

  it('displays donation stats when provided', () => {
    const actor = { id: 123, name: 'Test', actor_type: 'person' };
    const stats = { totalDonated: 47900000 };

    render(<ActorCard actor={actor} stats={stats} />);

    expect(screen.getByText('£47.9M')).toBeInTheDocument();
  });
});
```

---

### 6.2 Documentation

**Files to Create:**
- `frontend/README.md` - Frontend architecture documentation
- `docs/UI_COMPONENTS.md` - Component usage guide
- Update `CLAUDE.md` with new frontend patterns

**Documentation Sections:**
- Islands Architecture overview
- How to create new islands
- URL state management guide
- Component library reference
- Wagtail block development guide
- Testing patterns

---

## Implementation Sequence

### Week 1: Foundation
1. Set up Vite + django-vite
2. Migrate to Bootstrap 5
3. Create island loader system
4. Test basic hydration

### Week 2-3: Core Islands
1. Implement URL state management
2. Create ActorCard component
3. Build FilterPanel island
4. Build TopDonorsLeaderboard island
5. Test island communication

### Week 4: API Integration
1. React Query setup
2. API hooks for all endpoints
3. Error handling and loading states
4. Pagination support

### Week 5: Visualizations
1. ConcentrationChart with D3.js
2. Additional charts (time series, party comparison)
3. Chart responsiveness

### Week 6: Wagtail Integration
1. Create editorial app
2. Custom StreamField blocks
3. ActorMention model
4. Django signals
5. Template integration

### Week 7-8: Testing & Polish
1. Component tests (Vitest + React Testing Library)
2. Integration tests
3. Accessibility audit (WCAG 2.1 AA)
4. Documentation
5. Performance optimization

---

## Critical Files Reference

### Files to Create:
- `package.json`
- `vite.config.js`
- `tsconfig.json`
- `frontend/islands.tsx`
- `frontend/lib/urlState.ts`
- `frontend/types/filters.ts`
- `frontend/types/actor.ts`
- `frontend/components/ActorCard.tsx`
- `frontend/islands/FilterPanel.tsx`
- `frontend/islands/TopDonorsLeaderboard.tsx`
- `frontend/islands/ConcentrationChart.tsx`
- `frontend/hooks/useTopDonors.ts`
- `frontend/hooks/useConcentration.ts`
- `editorial/` (new app)
- `editorial/models.py`
- `editorial/signals.py`
- `cms/blocks.py`
- `cms/templates/cms/blocks/actor_card.html`
- `cms/templates/cms/blocks/leaderboard.html`

### Files to Modify:
- `undertheinfluence/settings.py` - Add django-vite, editorial app
- `requirements.txt` - Add django-vite
- `undertheinfluence/templates/base.html` - Vite assets, Bootstrap 5
- `datafetch/templates/person.html` - Add island hydration points
- `datafetch/templates/organization.html` - Add island hydration points
- `datafetch/templates/search.html` - Add FilterPanel + results islands
- `cms/models.py` - Add custom blocks to StreamField

### Files to Remove:
- `undertheinfluence/static/bootstrap-material-design/` (replaced by Bootstrap 5)
- `datafetch/static/datafetch/js/actor.js` (replaced by React islands)
- jQuery dependencies

---

## Verification & Testing

### Manual Testing Checklist:
1. **Build System**:
   - `npm run dev` starts Vite dev server
   - `npm run build` generates production assets
   - Django serves Vite assets correctly

2. **Islands Architecture**:
   - Islands hydrate on page load
   - Server-rendered fallback shows before hydration
   - Graceful degradation without JavaScript

3. **URL State**:
   - Filter changes update URL
   - Browser back/forward works
   - Shared URLs restore same filter state

4. **Components**:
   - ActorCard renders in compact and full modes
   - FilterPanel updates URL on change
   - Leaderboard fetches from API v2
   - Charts visualize data correctly

5. **Wagtail Integration**:
   - Custom blocks appear in Wagtail admin
   - Actor cards embed in pages
   - Leaderboards embed in pages
   - ActorMention records created on publish

6. **Accessibility**:
   - Keyboard navigation works
   - Screen reader announces changes
   - Color contrast meets WCAG AA
   - Focus indicators visible

### Automated Tests:
- Run `npm test` for component tests
- Run `pytest tests/` for Django integration tests
- Check coverage with `npm run test:coverage`

---

## Success Criteria

**Phase 1 Complete:**
- ✅ Vite builds successfully
- ✅ Bootstrap 5 loads without errors
- ✅ No jQuery dependencies remain

**Phase 2 Complete:**
- ✅ Island hydration works
- ✅ URL state synchronization works
- ✅ Multiple islands communicate via URL

**Phase 3 Complete:**
- ✅ ActorCard component functional
- ✅ FilterPanel updates URL
- ✅ Leaderboard fetches from API

**Phase 4 Complete:**
- ✅ Concentration chart visualizes data
- ✅ Charts update when filters change

**Phase 5 Complete:**
- ✅ Custom StreamField blocks work
- ✅ ActorMention model tracks relationships
- ✅ Signals maintain data integrity

**Phase 6 Complete:**
- ✅ 70%+ test coverage for frontend
- ✅ Documentation complete
- ✅ Accessibility audit passes

---

## Dependencies on Backend

**Already Available:**
- ✅ API v2 aggregate endpoints
- ✅ Actor detail endpoints
- ✅ Temporal querying (`?at_date=`)
- ✅ django-filter integration
- ✅ OpenAPI documentation

**Still Needed (Optional):**
- Materialized views for performance (can defer)
- Redis caching for aggregates (can defer)
- Additional aggregate endpoints (add as needed)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Vite build complexity | Start with minimal config, iterate |
| Island hydration bugs | Extensive testing, fallback content |
| URL state edge cases | Debouncing, validation, unit tests |
| D3.js learning curve | Start with simple charts, use Recharts alternative |
| Wagtail block complexity | Begin with simple blocks, add features incrementally |
| Performance regression | Lazy loading, code splitting, monitoring |

---

## Post-Implementation

After completing this plan:
1. **Monitor** Lighthouse scores (Performance, Accessibility, SEO)
2. **Measure** API response times and cache hit rates
3. **Gather** user feedback on filtering UX
4. **Iterate** on visualizations based on usage
5. **Expand** Wagtail blocks based on editorial needs

---

## Critical Critiques Addressed

This plan was updated based on architectural review feedback. Here's how each concern was mitigated:

### Critique #1: State Synchronization "Event Soup"

**Problem**: Custom window events (`uti:url-state-change`) can lead to race conditions and unpredictable update ordering as the number of islands grows.

**Solution**: Replaced custom event system with **Zustand** state management (Section 2.2):
- Lightweight (1KB gzipped) centralized store
- Predictable state update ordering
- Built-in DevTools support
- Type-safe with TypeScript
- No event listener cleanup concerns

**Impact**: Eliminates race conditions, simplifies debugging, scales to dozens of islands without coordination issues.

---

### Critique #2: Partial Date Handling in UI

**Problem**: HTML `<input type="date">` requires full YYYY-MM-DD format, but backend supports Popolo partial dates (YYYY, YYYY-MM, YYYY-MM-DD).

**Solution**: Created custom **PartialDateInput** component (Section 3.1):
- Precision toggle (Year / Month / Day buttons)
- Separate inputs for year, month, day components
- Maintains partial date format compatible with backend
- CSS Modules for scoped styling

**Impact**: Full fidelity with backend data model, allows users to filter by year-only or month-only ranges matching database precision.

---

### Critique #3: CSS Bloat and Scope

**Problem**: Migrating from Bootstrap 3 to 5 creates "zombie CSS" and global Bootstrap styles may clash with scoped React component styles.

**Solution**: Implemented **CSS Modules** with Sass preprocessing (Section 1.1):
- Component-specific `.module.scss` files automatically scoped
- Vite configuration enables CSS Modules for all `*.module.scss` files
- Bootstrap 5 loaded globally for layout/grid only
- Island components use scoped styles (e.g., `styles.partialDateInput`)

**Impact**: Prevents style bleeding, allows gradual Bootstrap 3 → 5 migration without global conflicts, enables component reusability.

---

### Critique #4: Build Pipeline & Docker Integration

**Problem**: Plan lacked Docker integration details. Vite-generated manifest.json with hashed filenames requires proper container orchestration.

**Solution**: Added comprehensive **Docker Compose configuration** (Section 1.1):
- Dedicated `vite` service running `node:20-alpine`
- Anonymous volume for `node_modules` to prevent host overwrite
- File watching with polling enabled for Docker compatibility
- Django `DJANGO_VITE_DEV_SERVER_HOST` points to `vite` service hostname
- Production build workflow documented

**Development Workflow**:
```bash
docker compose up -d  # Starts Django + Vite + PostgreSQL + Redis
# Vite HMR works across container boundary
# Django proxies Vite assets in development
```

**Production Build**:
```bash
docker compose exec web npm run build
docker compose exec web python manage.py collectstatic
# manifest.json generated inside container, accessible to Django
```

**Impact**: Seamless development experience with HMR, production builds work in containerized environment, no manual file copying required.

---

## Summary of Improvements

| Original Plan | Updated Plan | Benefit |
|---------------|--------------|---------|
| Custom events | Zustand store | No race conditions, predictable ordering |
| HTML `<input type="date">` | PartialDateInput component | Backend data fidelity, user flexibility |
| Global CSS only | CSS Modules + Sass | Scoped styles, no conflicts |
| Local-only Vite config | Docker Compose integration | Container-native development/production |

These updates ensure the implementation is **production-ready** and **architecturally sound** from day one.

---

## References

This plan is based on the following strategic documents:
- `docs/BACKEND_ARCHITECTURE_STRATEGY.md` - Entity resolution, API design, party affiliation
- `docs/FRONTEND_UX_STRATEGY.md` - Islands Architecture, component design, Wagtail integration
- `docs/PHASE_3_ROADMAP.md` - Project roadmap and current status

**Architectural Review**: Plan updated 2026-01-14 based on critical feedback addressing state management, partial dates, CSS scoping, and Docker integration.

**Next Steps**: Begin Phase 1 (Build System Foundation) when ready to proceed with implementation.
