# Frontend and UX Strategy

**Document Version:** 1.1
**Date:** January 14, 2026
**Phase:** 3.0 (Post Django 6.0.1 Modernization)
**Status:** Strategic Planning (Revised)

---

## Executive Summary

This document provides a comprehensive frontend and UX strategy for Phase 3 of UnderTheInfluence. The goal is to transform raw political influence data into an accessible, navigable, and journalistically compelling interface that serves both casual browsers and investigative researchers.

**Key Strategic Decisions:**

1. **Islands Architecture over SPA:** Server-render the majority of content for SEO and performance; hydrate specific interactive components (search, filters, visualizations) as React "islands."

2. **Data Cards as the Universal Primitive:** Every entity, metric, and relationship should be expressible as a compact, shareable card component that works in profiles, search results, and CMS embeds.

3. **Signal-to-Complexity Prioritization:** Build the high-signal, low-complexity visualizations first (leaderboards, concentration charts) before attempting complex network graphs.

4. **Editorial Autonomy:** The CMS integration must enable editors to curate topic pages and embed live data without developer intervention.

**Critical User Insight:**

The data analysis reveals extreme concentration: 277 donors (1.3%) control 65% of political donations. The interface must make this inequality *viscerally apparent* while enabling deep exploration of the underlying relationships.

---

## Part 1: UI/UX Architecture

### 1.1 Critique of Current Frontend State

**Current State:**
- Bootstrap 3 + Material Design theme (outdated)
- jQuery-based interactions
- django-bower for asset management (removed as incompatible with Django 2.0+)
- django-compressor for static file handling
- Basic templates with minimal interactivity

**Problems:**

| Issue | Impact |
|-------|--------|
| No modern JS bundler | Cannot use modern frameworks, tree-shaking, or code splitting |
| jQuery dependency | Verbose, hard to maintain, poor state management |
| No component architecture | UI inconsistency, code duplication |
| No client-side routing | Full page reloads for every navigation |
| Missing search/filter UX | Users cannot efficiently explore the dataset |

### 1.2 Recommended Architecture: Islands Model

**Why Islands over SPA:**

| Consideration | SPA | Islands (Recommended) |
|---------------|-----|----------------------|
| **SEO** | Poor (requires SSR complexity) | Excellent (server-rendered by default) |
| **Initial Load** | Heavy (full JS bundle) | Light (only island JS) |
| **Django Integration** | Complex (API-only backend) | Natural (templates + selective hydration) |
| **Wagtail Compatibility** | Difficult (CMS needs custom API layer) | Native (CMS pages render normally) |
| **Development Speed** | Slower (API + Frontend dual work) | Faster (progressive enhancement) |
| **Data Freshness** | Complex (state syncing) | Simple (page reload = fresh data) |

**Architecture Diagram:**

```
+------------------------------------------------------------------+
|                     Django/Wagtail Templates                      |
|  (Server-rendered HTML - SEO friendly, fast initial paint)        |
+------------------------------------------------------------------+
          |                    |                    |
          v                    v                    v
   +--------------+    +--------------+    +--------------+
   |  Search      |    |  Filter      |    | Visualization|
   |  Island      |    |  Island      |    |  Island      |
   |  (React)     |    |  (React)     |    |  (React/D3)  |
   +--------------+    +--------------+    +--------------+
          |                    |                    |
          +--------------------+--------------------+
                               |
                               v
                      +------------------+
                      |  API Layer       |
                      |  (/api/v2/...)   |
                      +------------------+
```

### 1.3 Technical Stack Recommendation

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Build System** | Vite | Fast dev server, native ES modules, excellent Django integration via django-vite |
| **CSS Framework** | Bootstrap 5 | Familiar, well-documented, responsive grid, removes jQuery dependency |
| **JS Framework** | React 18+ | Mature ecosystem, excellent TypeScript support, team familiarity |
| **Lightweight Alternative** | Preact | 3KB alternative if bundle size is critical |
| **Visualization** | D3.js + Recharts | D3 for custom viz, Recharts for standard charts |
| **State Management** | React Query | Server state caching, automatic background refetching |
| **Type Safety** | TypeScript | Catch errors early, better IDE support, API contract enforcement |

### 1.4 Island Hydration Strategy

**Template Integration Pattern:**

```html
<!-- templates/actor/detail.html -->
{% load static %}

<div class="actor-profile">
    <!-- Server-rendered content (SEO) -->
    <h1>{{ actor.name }}</h1>
    <p class="actor-type">{{ actor.classification }}</p>

    <!-- Stats Card (Server-rendered for SEO, hydrates for interactivity) -->
    <div id="actor-stats-island"
         data-island="ActorStats"
         data-actor-id="{{ actor.id }}"
         data-total-donated="{{ stats.total_donated }}"
         data-donation-count="{{ stats.donation_count }}">
        <!-- Fallback static content for no-JS -->
        <div class="stats-fallback">
            <p>Total Donated: {{ stats.total_donated|currency }}</p>
            <p>Donations: {{ stats.donation_count }}</p>
        </div>
    </div>

    <!-- Donations Table (Full Island - complex interaction) -->
    <div id="donations-island"
         data-island="DonationsTable"
         data-actor-id="{{ actor.id }}"
         data-api-url="{% url 'api:actor-donations' actor.id %}">
        <!-- Loading skeleton shown before hydration -->
        <div class="skeleton-table"></div>
    </div>
</div>

{% block extra_js %}
<script type="module" src="{% static 'js/islands.js' %}"></script>
{% endblock %}
```

**Island Loader:**

```typescript
// static/js/islands.ts
import { createRoot } from 'react-dom/client';

// Lazy-load island components
const islands = {
  'ActorStats': () => import('./islands/ActorStats'),
  'DonationsTable': () => import('./islands/DonationsTable'),
  'SearchBar': () => import('./islands/SearchBar'),
  'FilterPanel': () => import('./islands/FilterPanel'),
  'ConcentrationChart': () => import('./islands/ConcentrationChart'),
  'TopDonorsLeaderboard': () => import('./islands/TopDonorsLeaderboard'),
};

// Hydrate all islands on page
document.querySelectorAll('[data-island]').forEach(async (el) => {
  const islandName = el.dataset.island as keyof typeof islands;
  const loader = islands[islandName];

  if (!loader) {
    console.warn(`Unknown island: ${islandName}`);
    return;
  }

  try {
    const { default: Component } = await loader();

    // Extract all data-* attributes as props
    const props = { ...el.dataset };
    delete props.island;

    // Hydrate
    const root = createRoot(el);
    root.render(<Component {...props} />);
  } catch (err) {
    console.error(`Failed to load island ${islandName}:`, err);
  }
});
```

### 1.5 State Management Strategy

**Principle: Server as Source of Truth**

Unlike a traditional SPA where the client maintains all state, the islands model treats the server as the source of truth. Islands fetch data on demand and do not attempt to maintain a global client-side cache.

**React Query for API State:**

```typescript
// hooks/useDonations.ts
import { useQuery } from '@tanstack/react-query';

interface DonationFilters {
  actorId: number;
  dateFrom?: string;
  dateTo?: string;
  minValue?: number;
}

export function useDonations(filters: DonationFilters) {
  return useQuery({
    queryKey: ['donations', filters],
    queryFn: () => fetchDonations(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

async function fetchDonations(filters: DonationFilters) {
  const params = new URLSearchParams();
  if (filters.dateFrom) params.set('date_from', filters.dateFrom);
  if (filters.dateTo) params.set('date_to', filters.dateTo);
  if (filters.minValue) params.set('min_value', String(filters.minValue));

  const response = await fetch(
    `/api/v2/actors/${filters.actorId}/donations/?${params}`
  );
  return response.json();
}
```

**URL-Driven State for Shareability:**

Filters should be reflected in the URL so users can share specific views:

```
/search/?q=sainsbury&type=person&min_donated=100000
/organization/123/?tab=donations&date_from=2020-01-01
```

```typescript
// hooks/useFilterState.ts
import { useSearchParams } from 'react-router-dom';

export function useFilterState() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = {
    dateFrom: searchParams.get('date_from') || undefined,
    dateTo: searchParams.get('date_to') || undefined,
    minValue: searchParams.get('min_value')
      ? Number(searchParams.get('min_value'))
      : undefined,
    donorType: searchParams.get('donor_type') || undefined,
  };

  const setFilters = (newFilters: Partial<typeof filters>) => {
    const params = new URLSearchParams(searchParams);
    Object.entries(newFilters).forEach(([key, value]) => {
      const paramKey = key.replace(/([A-Z])/g, '_$1').toLowerCase();
      if (value !== undefined) {
        params.set(paramKey, String(value));
      } else {
        params.delete(paramKey);
      }
    });
    setSearchParams(params);
  };

  return { filters, setFilters };
}
```

### 1.6 URL-Driven State Management for Island Communication

**Critique Addressed:** With an islands architecture, separate components (Filter Island, Chart Island, Leaderboard Island) need to communicate state changes without a shared runtime context. The solution is to use URL search parameters as the global state mechanism.

**Design Principle:** The URL is the single source of truth. Filter changes update the URL, and all islands observe URL changes to refetch data.

#### 1.6.1 URL Parameter Schema

Define a consistent, typed schema for all filter parameters:

```typescript
// types/filters.ts

/**
 * URL parameter schema for filter state.
 * All values are strings in the URL; parsing happens in hooks.
 */
export interface FilterParams {
  // Date range
  date_from?: string;        // YYYY-MM-DD
  date_to?: string;          // YYYY-MM-DD
  at_date?: string;          // YYYY-MM-DD (point-in-time, overrides range)

  // Value filters
  min_value?: string;        // Number as string
  max_value?: string;        // Number as string

  // Entity type filters
  donor_type?: 'individual' | 'organization' | 'trade-union' | 'company';
  recipient_type?: 'person' | 'party' | 'organization';

  // Relationship filters
  has_lobbying?: 'true' | 'false';
  party_id?: string;         // Filter by specific party

  // Temporal options
  use_historical_party?: 'true' | 'false';

  // Pagination
  page?: string;
  limit?: string;

  // Search
  q?: string;
}

/**
 * Parsed filter state with proper types.
 */
export interface FilterState {
  dateFrom?: Date;
  dateTo?: Date;
  atDate?: Date;
  minValue?: number;
  maxValue?: number;
  donorType?: 'individual' | 'organization' | 'trade-union' | 'company';
  recipientType?: 'person' | 'party' | 'organization';
  hasLobbying?: boolean;
  partyId?: number;
  useHistoricalParty: boolean;
  page: number;
  limit: number;
  query?: string;
}

/**
 * Parse URL params to typed filter state.
 */
export function parseFilterParams(params: URLSearchParams): FilterState {
  return {
    dateFrom: params.get('date_from') ? new Date(params.get('date_from')!) : undefined,
    dateTo: params.get('date_to') ? new Date(params.get('date_to')!) : undefined,
    atDate: params.get('at_date') ? new Date(params.get('at_date')!) : undefined,
    minValue: params.get('min_value') ? Number(params.get('min_value')) : undefined,
    maxValue: params.get('max_value') ? Number(params.get('max_value')) : undefined,
    donorType: params.get('donor_type') as FilterState['donorType'],
    recipientType: params.get('recipient_type') as FilterState['recipientType'],
    hasLobbying: params.get('has_lobbying') === 'true' ? true :
                 params.get('has_lobbying') === 'false' ? false : undefined,
    partyId: params.get('party_id') ? Number(params.get('party_id')) : undefined,
    useHistoricalParty: params.get('use_historical_party') !== 'false', // Default true
    page: Number(params.get('page')) || 1,
    limit: Number(params.get('limit')) || 20,
    query: params.get('q') || undefined,
  };
}

/**
 * Serialize filter state to URL params.
 */
export function serializeFilterState(state: Partial<FilterState>): URLSearchParams {
  const params = new URLSearchParams();

  if (state.dateFrom) params.set('date_from', state.dateFrom.toISOString().split('T')[0]);
  if (state.dateTo) params.set('date_to', state.dateTo.toISOString().split('T')[0]);
  if (state.atDate) params.set('at_date', state.atDate.toISOString().split('T')[0]);
  if (state.minValue !== undefined) params.set('min_value', String(state.minValue));
  if (state.maxValue !== undefined) params.set('max_value', String(state.maxValue));
  if (state.donorType) params.set('donor_type', state.donorType);
  if (state.recipientType) params.set('recipient_type', state.recipientType);
  if (state.hasLobbying !== undefined) params.set('has_lobbying', String(state.hasLobbying));
  if (state.partyId) params.set('party_id', String(state.partyId));
  if (state.useHistoricalParty === false) params.set('use_historical_party', 'false');
  if (state.page && state.page > 1) params.set('page', String(state.page));
  if (state.limit && state.limit !== 20) params.set('limit', String(state.limit));
  if (state.query) params.set('q', state.query);

  return params;
}
```

#### 1.6.2 Island Communication Pattern

**Problem:** Filter Island changes filters; Chart Island and Leaderboard Island need to refetch data.

**Solution:** All islands observe `window.location.search` changes via a custom event system.

```typescript
// lib/urlState.ts

import { parseFilterParams, serializeFilterState, FilterState } from '../types/filters';

// Custom event for URL state changes
const URL_STATE_CHANGE = 'uti:url-state-change';

/**
 * Get current filter state from URL.
 */
export function getUrlState(): FilterState {
  return parseFilterParams(new URLSearchParams(window.location.search));
}

/**
 * Update URL with new filter state.
 * Merges with existing params and dispatches change event.
 *
 * @param updates Partial filter state to merge
 * @param options.replace Use replaceState instead of pushState (no history entry)
 * @param options.resetPage Reset pagination when filters change
 */
export function setUrlState(
  updates: Partial<FilterState>,
  options: { replace?: boolean; resetPage?: boolean } = {}
): void {
  const current = getUrlState();

  // Reset page when filters change (common UX pattern)
  if (options.resetPage && Object.keys(updates).some(k => k !== 'page')) {
    updates.page = 1;
  }

  const merged = { ...current, ...updates };
  const params = serializeFilterState(merged);

  const url = `${window.location.pathname}?${params.toString()}`;

  if (options.replace) {
    window.history.replaceState({}, '', url);
  } else {
    window.history.pushState({}, '', url);
  }

  // Dispatch custom event for island communication
  window.dispatchEvent(new CustomEvent(URL_STATE_CHANGE, {
    detail: { state: merged, updates }
  }));
}

/**
 * Clear specific filter params (or all if none specified).
 */
export function clearUrlState(keys?: (keyof FilterState)[]): void {
  const current = getUrlState();
  const cleared: Partial<FilterState> = {};

  if (keys) {
    keys.forEach(key => { cleared[key] = undefined; });
    setUrlState(cleared, { resetPage: true });
  } else {
    // Clear all, preserve only essential defaults
    window.history.pushState({}, '', window.location.pathname);
    window.dispatchEvent(new CustomEvent(URL_STATE_CHANGE, {
      detail: { state: parseFilterParams(new URLSearchParams()), updates: {} }
    }));
  }
}

/**
 * React hook to observe URL state changes.
 * Returns current state and automatically updates on URL changes.
 */
export function useUrlState(): FilterState {
  const [state, setState] = React.useState(getUrlState);

  React.useEffect(() => {
    // Handle our custom event
    const handleCustomChange = (e: CustomEvent) => {
      setState(e.detail.state);
    };

    // Handle browser back/forward navigation
    const handlePopState = () => {
      setState(getUrlState());
      // Re-dispatch for other islands
      window.dispatchEvent(new CustomEvent(URL_STATE_CHANGE, {
        detail: { state: getUrlState(), updates: {} }
      }));
    };

    window.addEventListener(URL_STATE_CHANGE, handleCustomChange as EventListener);
    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener(URL_STATE_CHANGE, handleCustomChange as EventListener);
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  return state;
}
```

#### 1.6.3 Debounced URL Updates

Prevent excessive history entries when users type in search or adjust sliders:

```typescript
// hooks/useDebouncedUrlState.ts

import { useCallback, useRef } from 'react';
import { setUrlState, FilterState } from '../lib/urlState';

/**
 * Debounced URL state updates for high-frequency changes.
 * Uses replaceState during debounce period, pushState on final update.
 */
export function useDebouncedUrlState(debounceMs: number = 300) {
  const timeoutRef = useRef<number | null>(null);
  const pendingRef = useRef<Partial<FilterState>>({});

  const updateUrlState = useCallback((updates: Partial<FilterState>) => {
    // Merge with pending updates
    pendingRef.current = { ...pendingRef.current, ...updates };

    // Clear existing timeout
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current);
    }

    // Immediate update with replaceState (no history entry)
    setUrlState(pendingRef.current, { replace: true, resetPage: true });

    // Schedule final update with pushState (creates history entry)
    timeoutRef.current = window.setTimeout(() => {
      setUrlState(pendingRef.current, { replace: false, resetPage: true });
      pendingRef.current = {};
      timeoutRef.current = null;
    }, debounceMs);
  }, [debounceMs]);

  // Immediate update (bypasses debounce)
  const updateUrlStateImmediate = useCallback((updates: Partial<FilterState>) => {
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    pendingRef.current = {};
    setUrlState(updates, { resetPage: true });
  }, []);

  return { updateUrlState, updateUrlStateImmediate };
}
```

#### 1.6.4 Island Implementation Examples

**Filter Island (updates URL):**

```tsx
// islands/FilterIsland.tsx

import React from 'react';
import { useUrlState, setUrlState, clearUrlState } from '../lib/urlState';
import { useDebouncedUrlState } from '../hooks/useDebouncedUrlState';
import { FilterState } from '../types/filters';

export function FilterIsland() {
  const state = useUrlState();
  const { updateUrlState, updateUrlStateImmediate } = useDebouncedUrlState(300);

  return (
    <div className="filter-island">
      {/* Date Range - immediate update on blur */}
      <div className="filter-group">
        <label>Date Range</label>
        <input
          type="date"
          value={state.dateFrom?.toISOString().split('T')[0] || ''}
          onChange={(e) => updateUrlStateImmediate({
            dateFrom: e.target.value ? new Date(e.target.value) : undefined
          })}
        />
        <span>to</span>
        <input
          type="date"
          value={state.dateTo?.toISOString().split('T')[0] || ''}
          onChange={(e) => updateUrlStateImmediate({
            dateTo: e.target.value ? new Date(e.target.value) : undefined
          })}
        />
      </div>

      {/* Min Value - debounced update */}
      <div className="filter-group">
        <label>Minimum Value</label>
        <select
          value={state.minValue?.toString() || ''}
          onChange={(e) => updateUrlStateImmediate({
            minValue: e.target.value ? Number(e.target.value) : undefined
          })}
        >
          <option value="">Any amount</option>
          <option value="1000">1,000+</option>
          <option value="10000">10,000+</option>
          <option value="100000">100,000+</option>
          <option value="1000000">1,000,000+</option>
        </select>
      </div>

      {/* Donor Type - chip selection */}
      <div className="filter-group">
        <label>Donor Type</label>
        <div className="filter-chips">
          {(['individual', 'organization', 'trade-union', 'company'] as const).map(type => (
            <button
              key={type}
              className={`chip ${state.donorType === type ? 'active' : ''}`}
              onClick={() => updateUrlStateImmediate({
                donorType: state.donorType === type ? undefined : type
              })}
            >
              {type.replace('-', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Lobbying filter */}
      <div className="filter-group">
        <label>
          <input
            type="checkbox"
            checked={state.hasLobbying === true}
            onChange={(e) => updateUrlStateImmediate({
              hasLobbying: e.target.checked ? true : undefined
            })}
          />
          Only lobbying clients
        </label>
      </div>

      {/* Historical party toggle */}
      <div className="filter-group">
        <label>
          <input
            type="checkbox"
            checked={state.useHistoricalParty}
            onChange={(e) => updateUrlStateImmediate({
              useHistoricalParty: e.target.checked
            })}
          />
          Use historical party affiliation
        </label>
        <small>Attribute donations to party at time of donation</small>
      </div>

      {/* Clear all */}
      <button
        className="clear-filters"
        onClick={() => clearUrlState()}
        disabled={Object.values(state).every(v => v === undefined || v === true || v === 1 || v === 20)}
      >
        Clear all filters
      </button>
    </div>
  );
}
```

**Chart Island (observes URL):**

```tsx
// islands/ConcentrationChartIsland.tsx

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useUrlState } from '../lib/urlState';
import { ConcentrationChart } from '../components/ConcentrationChart';

export function ConcentrationChartIsland() {
  // Automatically re-renders when URL changes
  const filters = useUrlState();

  // Build API query params from URL state
  const queryParams = new URLSearchParams();
  if (filters.dateFrom) queryParams.set('date_from', filters.dateFrom.toISOString().split('T')[0]);
  if (filters.dateTo) queryParams.set('date_to', filters.dateTo.toISOString().split('T')[0]);
  if (filters.donorType) queryParams.set('donor_type', filters.donorType);
  if (filters.hasLobbying) queryParams.set('has_lobbying', 'true');

  const { data, isLoading, error } = useQuery({
    queryKey: ['concentration', queryParams.toString()],
    queryFn: async () => {
      const response = await fetch(`/api/v2/aggregates/concentration/?${queryParams}`);
      if (!response.ok) throw new Error('Failed to fetch concentration data');
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) return <div className="chart-skeleton" />;
  if (error) return <div className="chart-error">Failed to load chart</div>;

  return <ConcentrationChart data={data} />;
}
```

**Leaderboard Island (also observes URL):**

```tsx
// islands/TopDonorsLeaderboardIsland.tsx

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useUrlState } from '../lib/urlState';
import { ActorCard } from '../components/ActorCard';
import { formatCurrency } from '../utils/format';

export function TopDonorsLeaderboardIsland() {
  const filters = useUrlState();

  // Build API query params from URL state
  const queryParams = new URLSearchParams();
  if (filters.dateFrom) queryParams.set('date_from', filters.dateFrom.toISOString().split('T')[0]);
  if (filters.dateTo) queryParams.set('date_to', filters.dateTo.toISOString().split('T')[0]);
  if (filters.minValue) queryParams.set('min_value', String(filters.minValue));
  if (filters.donorType) queryParams.set('donor_type', filters.donorType);
  if (filters.hasLobbying) queryParams.set('has_lobbying', 'true');
  queryParams.set('limit', '20');

  const { data, isLoading, error } = useQuery({
    queryKey: ['top-donors', queryParams.toString()],
    queryFn: async () => {
      const response = await fetch(`/api/v2/aggregates/top-donors/?${queryParams}`);
      if (!response.ok) throw new Error('Failed to fetch top donors');
      return response.json();
    },
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) return <div className="leaderboard-skeleton" />;
  if (error) return <div className="leaderboard-error">Failed to load leaderboard</div>;

  return (
    <div className="leaderboard">
      <h2>Top Donors</h2>
      <ol className="leaderboard-list">
        {data.results.map((donor: any, index: number) => (
          <li key={donor.donor_id} className="leaderboard-item">
            <span className="rank">{index + 1}</span>
            <ActorCard
              id={donor.donor_id}
              name={donor.donor_name}
              type={donor.donor_type === 'Individual' ? 'Person' : 'Organization'}
              classification={donor.donor_type}
              stats={{ totalDonated: donor.total_donated }}
              compact
            />
            <span className="total">{formatCurrency(donor.total_donated)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
```

#### 1.6.5 Trade-off Analysis

| Approach | Pros | Cons |
|----------|------|------|
| Shared React context | Simple, typed, React-native | Requires single React tree, breaks islands |
| Custom event bus | Decoupled, any framework | Custom implementation, no typing |
| URL params (recommended) | Shareable, works with SSR, survives refresh | Limited data types, visible to user |
| localStorage | Persistent across sessions | Not shareable, sync issues |

**Implementation Priority:** Phase 3.1 (Weeks 1-2) - Must be implemented before any islands that need filtering.

---

## Part 2: Key User Journeys

### 2.1 User Personas

**Persona 1: Casual Browser ("The Concerned Citizen")**
- **Goal:** Understand "who is funding UK politics?"
- **Behavior:** Arrives from news article or social media, spends 2-5 minutes
- **Needs:** Clear headlines, scannable summaries, shareable takeaways
- **Key Journey:** Homepage -> Top Donors -> Individual Donor Profile -> Share

**Persona 2: Investigative Researcher ("The Journalist")**
- **Goal:** Find specific connections for a story
- **Behavior:** Has a hypothesis, searches for specific names/organizations
- **Needs:** Powerful search, filtering by date/value, downloadable data
- **Key Journey:** Search -> Filter Results -> Entity Profile -> Download/Cite

**Persona 3: Policy Analyst ("The Wonk")**
- **Goal:** Analyze patterns across sectors or parties
- **Behavior:** Explores aggregates, compares trends over time
- **Needs:** Time series data, sector breakdowns, party comparisons
- **Key Journey:** Aggregates Dashboard -> Filter by Sector -> Compare Parties -> Export

### 2.2 Journey 1: Discovering Concentration

**Entry Point:** Homepage or "Explore Donors" landing page

**Story Arc:**
1. **Hook:** "1.3% of donors control 65% of political donations"
2. **Explore:** Interactive Pareto chart showing distribution
3. **Drill Down:** Click on "1M+ bracket" to see the 277 whale donors
4. **Personalize:** Filter by party, time period, donor type
5. **Deep Dive:** Click individual donor for full profile
6. **Share:** Generate shareable card or link

**Wireframe:**

```
+---------------------------------------------------------------+
|  POWER CONCENTRATION                                           |
|  How political money is distributed                            |
+---------------------------------------------------------------+
|                                                                |
|  +---------------------------+  +--------------------------+   |
|  |  [PARETO CHART]           |  |  KEY STATS              |   |
|  |                           |  |                          |   |
|  |  65%                      |  |  277 Whale Donors        |   |
|  |  |||||||||||||||          |  |  (1M+ each)              |   |
|  |  |||||||||                |  |                          |   |
|  |  ||||                     |  |  Control: $1.36B         |   |
|  |  ||                       |  |  (65% of total)          |   |
|  |  1.3% of donors           |  |                          |   |
|  +---------------------------+  +--------------------------+   |
|                                                                |
|  FILTER: [All Time v] [All Types v] [All Parties v]           |
|                                                                |
|  TOP WHALE DONORS:                                             |
|  +----------------------------------------------------------+ |
|  | Unite the Union     | Trade Union | $67.2M | 1,138 donations|
|  | David Sainsbury     | Individual  | $47.9M | 238 donations  |
|  | UNISON             | Trade Union | $63.0M | 2,756 donations |
|  +----------------------------------------------------------+ |
+---------------------------------------------------------------+
```

### 2.3 Journey 2: Researching a Specific Entity

**Entry Point:** Search bar (always visible in header)

**Story Arc:**
1. **Search:** Type "Sainsbury" in search bar
2. **Disambiguate:** See grouped results (David Sainsbury, John Sainsbury, Sainsbury's Ltd)
3. **Select:** Click "David Sainsbury" person result
4. **Profile Overview:** See summary stats, key relationships, timeline
5. **Explore Relationships:** Switch to "Donations Made" tab, filter by recipient
6. **Cross-Reference:** Notice link to "David Sainsbury of Turville" (potential duplicate)
7. **Export:** Download CSV of all donations for reporting

**Search Results Wireframe:**

```
+---------------------------------------------------------------+
|  SEARCH: [sainsbury________________________] [Search]          |
+---------------------------------------------------------------+
|                                                                |
|  PEOPLE (3 results)                                            |
|  +----------------------------------------------------------+ |
|  | [img] David Sainsbury                                     | |
|  |       Individual Donor | Total: $47.9M | 238 donations    | |
|  +----------------------------------------------------------+ |
|  | [img] David Sainsbury of Turville                         | |
|  |       Individual Donor | Total: $19.1M | 34 donations     | |
|  +----------------------------------------------------------+ |
|  | [img] John Sainsbury                                      | |
|  |       Individual Donor | Total: $11.8M | 19 donations     | |
|  +----------------------------------------------------------+ |
|                                                                |
|  ORGANIZATIONS (1 result)                                      |
|  +----------------------------------------------------------+ |
|  | [img] Sainsbury's Supermarkets Ltd                        | |
|  |       Company | Total: $125K | 12 donations               | |
|  +----------------------------------------------------------+ |
|                                                                |
|  TIP: "David Sainsbury" and "David Sainsbury of Turville"     |
|       may be the same person. [View comparison]                |
+---------------------------------------------------------------+
```

### 2.4 Journey 3: Exploring Dual-Channel Influence

**Entry Point:** "Lobbying & Donations" section or linked from homepage stat

**Story Arc:**
1. **Overview:** "61 organizations use both lobbying and donations"
2. **Leaderboard:** See top dual-channel influencers ranked by combined activity
3. **Select:** Click "Unite the Union"
4. **Profile:** See unified view of lobbying relationships AND donations
5. **Timeline:** Visualize when lobbying relationships overlap with donation spikes
6. **Triangle View:** See which MPs received donations AND are lobbied

**Dual-Channel Profile Wireframe:**

```
+---------------------------------------------------------------+
|  UNITE THE UNION                                               |
|  Trade Union | Dual-Channel Influencer                         |
+---------------------------------------------------------------+
|                                                                |
|  +-------------------+  +-------------------+  +-------------+ |
|  | DONATIONS         |  | LOBBYING          |  | OVERLAP     | |
|  | $67.2M total      |  | 4 agencies        |  | 12 MPs      | |
|  | 1,138 donations   |  | 24 consultancies  |  | received    | |
|  | 115 recipients    |  | since 2019        |  | both        | |
|  +-------------------+  +-------------------+  +-------------+ |
|                                                                |
|  [TIMELINE VISUALIZATION]                                      |
|  2019 |=====|  (Agency A engaged)                              |
|  2020 |===========|  (Donations spike)                         |
|  2021 |=======|                                                |
|  2022 |============|  (Agency B engaged)                       |
|  2023 |=========|                                              |
|                                                                |
|  TABS: [Overview] [Donations (1,138)] [Lobbying (4)] [MPs (115)]|
+---------------------------------------------------------------+
```

### 2.5 Journey 4: Party-Level Analysis

**Entry Point:** "Party Funding" section or navigation

**Story Arc:**
1. **Overview:** See all major parties with total funding received
2. **Compare:** Side-by-side comparison of Labour vs Conservative funding sources
3. **Breakdown:** Pie chart of funding by source type (unions, companies, individuals)
4. **Drill Down:** Click "Trade Unions" slice to see all union donors to Labour
5. **Time Series:** Toggle to see how funding sources have changed over time
6. **Export:** Download party funding comparison data

**Note:** This journey depends on the Party Affiliation architecture from the backend strategy. Until `current_party` is populated on Person records, party-level aggregation will be incomplete.

---

## Part 3: Component Architecture

### 3.1 Data Card: The Universal Primitive

**Design Principle:** Every entity and metric should be expressible as a compact card that:
- Renders consistently across contexts (search results, profiles, CMS embeds)
- Contains enough information to understand at a glance
- Links to full detail view
- Is shareable (generates preview image/metadata)

**Card Variants:**

```typescript
// types/cards.ts

interface ActorCardProps {
  id: number;
  name: string;
  type: 'Person' | 'Organization';
  classification?: string;
  imageUrl?: string;
  stats: {
    totalDonated?: number;
    totalReceived?: number;
    donationCount?: number;
    isLobbyingClient?: boolean;
  };
  compact?: boolean; // Smaller version for lists
}

interface StatCardProps {
  label: string;
  value: number | string;
  change?: {
    value: number;
    direction: 'up' | 'down' | 'flat';
    period: string;
  };
  context?: string; // e.g., "of total donations"
}

interface RelationshipCardProps {
  fromActor: ActorCardProps;
  toActor: ActorCardProps;
  relationshipType: 'donation' | 'consultancy';
  value?: number;
  count?: number;
  dateRange?: { from: string; to: string };
}
```

**ActorCard Component:**

```tsx
// components/ActorCard.tsx
import { formatCurrency, formatNumber } from '../utils/format';

export function ActorCard({
  id,
  name,
  type,
  classification,
  imageUrl,
  stats,
  compact = false,
}: ActorCardProps) {
  const profileUrl = type === 'Person'
    ? `/person/${id}/`
    : `/organization/${id}/`;

  if (compact) {
    return (
      <a href={profileUrl} className="actor-card actor-card--compact">
        <img
          src={imageUrl || '/static/img/default-avatar.svg'}
          alt=""
          className="actor-card__image"
        />
        <div className="actor-card__content">
          <h3 className="actor-card__name">{name}</h3>
          <p className="actor-card__type">{classification || type}</p>
        </div>
        {stats.totalDonated && (
          <span className="actor-card__stat">
            {formatCurrency(stats.totalDonated)}
          </span>
        )}
      </a>
    );
  }

  return (
    <a href={profileUrl} className="actor-card">
      <div className="actor-card__header">
        <img
          src={imageUrl || '/static/img/default-avatar.svg'}
          alt=""
          className="actor-card__image"
        />
        <div>
          <h3 className="actor-card__name">{name}</h3>
          <p className="actor-card__type">{classification || type}</p>
          {stats.isLobbyingClient && (
            <span className="actor-card__badge">Lobbying Client</span>
          )}
        </div>
      </div>
      <div className="actor-card__stats">
        {stats.totalDonated && (
          <div className="actor-card__stat">
            <span className="actor-card__stat-value">
              {formatCurrency(stats.totalDonated)}
            </span>
            <span className="actor-card__stat-label">Total Donated</span>
          </div>
        )}
        {stats.totalReceived && (
          <div className="actor-card__stat">
            <span className="actor-card__stat-value">
              {formatCurrency(stats.totalReceived)}
            </span>
            <span className="actor-card__stat-label">Total Received</span>
          </div>
        )}
        {stats.donationCount && (
          <div className="actor-card__stat">
            <span className="actor-card__stat-value">
              {formatNumber(stats.donationCount)}
            </span>
            <span className="actor-card__stat-label">Donations</span>
          </div>
        )}
      </div>
    </a>
  );
}
```

### 3.2 State Management Pattern for Island Communication

**Critique Addressed:** Islands architecture requires a clear pattern for how components communicate without sharing a React tree.

**Solution:** All filtering islands share state through URL parameters (see Section 1.6). This section documents the component-level patterns.

#### 3.2.1 TypeScript Interfaces for Filter State

```typescript
// types/components.ts

/**
 * Props passed to filtering components via data attributes.
 * These are serialized as strings in HTML and parsed on hydration.
 */
export interface FilterIslandProps {
  // Initial state (from server)
  initialFilters?: string;  // JSON-serialized FilterState

  // Feature flags
  showDateRange?: boolean;
  showValueRange?: boolean;
  showDonorType?: boolean;
  showRecipientType?: boolean;
  showLobbyingFilter?: boolean;
  showHistoricalPartyToggle?: boolean;

  // API configuration
  apiBaseUrl?: string;
}

export interface DataIslandProps {
  // Entity context
  actorId?: number;
  actorType?: 'Person' | 'Organization';

  // API endpoint
  apiEndpoint: string;

  // Rendering options
  limit?: number;
  compact?: boolean;
}

/**
 * Shared types for API responses.
 */
export interface AggregateResponse<T> {
  meta: {
    from_date?: string;
    to_date?: string;
    use_historical_party?: boolean;
    total_count?: number;
  };
  results: T[];
}

export interface DonorAggregate {
  donor_id: number;
  donor_name: string;
  donor_type: 'Individual' | 'Trade Union' | 'Company' | 'Other';
  total_donated: number;
  donation_count: number;
  distinct_recipients: number;
  latest_donation: string;
  is_lobbying_client: boolean;
}

export interface PartyAggregate {
  party_id: number;
  party_name: string;
  direct_donations: { total: number; count: number };
  mp_donations: { total: number; count: number; mp_count: number };
  combined_total: number;
}
```

#### 3.2.2 Shared Data Fetching Hook

```typescript
// hooks/useFilteredData.ts

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { useUrlState } from '../lib/urlState';
import { FilterState, serializeFilterState } from '../types/filters';

/**
 * Generic hook for fetching data with current URL filter state.
 * Automatically refetches when URL filters change.
 */
export function useFilteredData<T>(
  endpoint: string,
  options: {
    additionalParams?: Record<string, string>;
    enabled?: boolean;
    staleTime?: number;
  } = {}
): UseQueryResult<T> {
  const filters = useUrlState();
  const { additionalParams = {}, enabled = true, staleTime = 5 * 60 * 1000 } = options;

  // Build query params from filter state
  const filterParams = serializeFilterState(filters);

  // Add any additional params
  Object.entries(additionalParams).forEach(([key, value]) => {
    filterParams.set(key, value);
  });

  const queryString = filterParams.toString();

  return useQuery<T>({
    queryKey: [endpoint, queryString],
    queryFn: async () => {
      const url = queryString ? `${endpoint}?${queryString}` : endpoint;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      return response.json();
    },
    enabled,
    staleTime,
  });
}

/**
 * Specialized hook for top donors leaderboard.
 */
export function useTopDonors(limit: number = 20) {
  return useFilteredData<AggregateResponse<DonorAggregate>>(
    '/api/v2/aggregates/top-donors/',
    { additionalParams: { limit: String(limit) } }
  );
}

/**
 * Specialized hook for party aggregates with historical option.
 */
export function usePartyDonations() {
  const filters = useUrlState();

  return useFilteredData<{ meta: object; parties: PartyAggregate[] }>(
    '/api/v2/aggregates/party-donations/',
    {
      additionalParams: {
        use_historical_party: String(filters.useHistoricalParty)
      }
    }
  );
}
```

#### 3.2.3 Progressive Enhancement Pattern

All islands must work without JavaScript for SEO and accessibility:

```html
<!-- Template pattern for progressive enhancement -->
<div id="top-donors-island"
     data-island="TopDonorsLeaderboard"
     data-api-endpoint="/api/v2/aggregates/top-donors/"
     data-limit="10">

    <!-- Server-rendered fallback content -->
    <noscript>
        <p>Enable JavaScript to see interactive leaderboard with filtering.</p>
    </noscript>

    <!-- Static content for SEO (replaced by React on hydration) -->
    <ol class="leaderboard-fallback">
        {% for donor in top_donors %}
        <li>
            <a href="{{ donor.url }}">{{ donor.name }}</a>
            <span>{{ donor.total_donated|currency }}</span>
        </li>
        {% endfor %}
    </ol>
</div>
```

```typescript
// Island hydration with fallback preservation
async function hydrateIsland(el: HTMLElement) {
  const islandName = el.dataset.island;
  const loader = islands[islandName];

  if (!loader) return;

  try {
    const { default: Component } = await loader();
    const props = parseDataAttributes(el.dataset);

    // Check if we should preserve server content as initial data
    const serverContent = el.querySelector('.leaderboard-fallback');
    if (serverContent) {
      props.serverRenderedContent = serverContent.innerHTML;
    }

    const root = createRoot(el);
    root.render(<Component {...props} />);
  } catch (err) {
    console.error(`Failed to hydrate island ${islandName}:`, err);
    // Leave server-rendered content in place on failure
  }
}
```

### 3.3 Filter Panel Component

**Design Principle:** Filters should be:
- Visible and discoverable (not hidden in a dropdown)
- Applied immediately (no "Apply" button)
- Reflected in URL for shareability
- Consistent across all data views

```tsx
// components/FilterPanel.tsx
import { useFilterState } from '../hooks/useFilterState';

interface FilterPanelProps {
  showDonorType?: boolean;
  showRecipientType?: boolean;
  showDateRange?: boolean;
  showValueRange?: boolean;
  showLobbyingFilter?: boolean;
}

export function FilterPanel({
  showDonorType = true,
  showRecipientType = true,
  showDateRange = true,
  showValueRange = true,
  showLobbyingFilter = true,
}: FilterPanelProps) {
  const { filters, setFilters } = useFilterState();

  return (
    <div className="filter-panel">
      {showDateRange && (
        <div className="filter-panel__group">
          <label className="filter-panel__label">Date Range</label>
          <div className="filter-panel__row">
            <input
              type="date"
              value={filters.dateFrom || ''}
              onChange={(e) => setFilters({ dateFrom: e.target.value || undefined })}
              className="filter-panel__input"
            />
            <span className="filter-panel__separator">to</span>
            <input
              type="date"
              value={filters.dateTo || ''}
              onChange={(e) => setFilters({ dateTo: e.target.value || undefined })}
              className="filter-panel__input"
            />
          </div>
        </div>
      )}

      {showValueRange && (
        <div className="filter-panel__group">
          <label className="filter-panel__label">Minimum Value</label>
          <select
            value={filters.minValue || ''}
            onChange={(e) => setFilters({
              minValue: e.target.value ? Number(e.target.value) : undefined
            })}
            className="filter-panel__select"
          >
            <option value="">Any amount</option>
            <option value="1000">$1,000+</option>
            <option value="10000">$10,000+</option>
            <option value="50000">$50,000+</option>
            <option value="100000">$100,000+</option>
            <option value="500000">$500,000+</option>
            <option value="1000000">$1,000,000+</option>
          </select>
        </div>
      )}

      {showDonorType && (
        <div className="filter-panel__group">
          <label className="filter-panel__label">Donor Type</label>
          <div className="filter-panel__chips">
            {['all', 'individual', 'organization', 'trade-union', 'company'].map(
              (type) => (
                <button
                  key={type}
                  className={`filter-panel__chip ${
                    (filters.donorType || 'all') === type
                      ? 'filter-panel__chip--active'
                      : ''
                  }`}
                  onClick={() =>
                    setFilters({ donorType: type === 'all' ? undefined : type })
                  }
                >
                  {type === 'all' ? 'All' : type.replace('-', ' ')}
                </button>
              )
            )}
          </div>
        </div>
      )}

      {showLobbyingFilter && (
        <div className="filter-panel__group">
          <label className="filter-panel__toggle">
            <input
              type="checkbox"
              checked={filters.hasLobbying || false}
              onChange={(e) =>
                setFilters({ hasLobbying: e.target.checked || undefined })
              }
            />
            <span>Only show lobbying clients</span>
          </label>
        </div>
      )}

      {/* Active filters display */}
      {Object.values(filters).some(Boolean) && (
        <div className="filter-panel__active">
          <span className="filter-panel__active-label">Active filters:</span>
          {Object.entries(filters)
            .filter(([_, v]) => v)
            .map(([key, value]) => (
              <span key={key} className="filter-panel__active-chip">
                {key}: {String(value)}
                <button
                  onClick={() => setFilters({ [key]: undefined })}
                  className="filter-panel__remove"
                >
                  x
                </button>
              </span>
            ))}
          <button
            onClick={() =>
              setFilters({
                dateFrom: undefined,
                dateTo: undefined,
                minValue: undefined,
                donorType: undefined,
                hasLobbying: undefined,
              })
            }
            className="filter-panel__clear"
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  );
}
```

### 3.3 Search Component

**Design Principle:**
- Instant results as user types (debounced)
- Grouped by entity type
- Shows preview stats inline
- Keyboard navigable

```tsx
// components/SearchBar.tsx
import { useState, useEffect, useRef } from 'react';
import { useDebounce } from '../hooks/useDebounce';
import { ActorCard } from './ActorCard';

export function SearchBar() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResults | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);

  const debouncedQuery = useDebounce(query, 300);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (debouncedQuery.length < 2) {
      setResults(null);
      return;
    }

    fetch(`/api/v2/search/?q=${encodeURIComponent(debouncedQuery)}`)
      .then((r) => r.json())
      .then(setResults);
  }, [debouncedQuery]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!results) return;

    const totalResults = results.persons.length + results.organizations.length;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, totalResults - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, -1));
        break;
      case 'Enter':
        if (selectedIndex >= 0) {
          // Navigate to selected result
          const allResults = [...results.persons, ...results.organizations];
          const selected = allResults[selectedIndex];
          window.location.href = selected.url;
        }
        break;
      case 'Escape':
        setIsOpen(false);
        break;
    }
  };

  return (
    <div
      ref={containerRef}
      className="search-bar"
      onKeyDown={handleKeyDown}
    >
      <input
        type="search"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setIsOpen(true);
        }}
        onFocus={() => setIsOpen(true)}
        placeholder="Search donors, MPs, organizations..."
        className="search-bar__input"
        aria-label="Search"
        aria-expanded={isOpen && results !== null}
        aria-controls="search-results"
      />

      {isOpen && results && (
        <div id="search-results" className="search-bar__results">
          {results.persons.length > 0 && (
            <div className="search-bar__group">
              <h3 className="search-bar__group-title">
                People ({results.persons.length})
              </h3>
              {results.persons.map((person, i) => (
                <ActorCard
                  key={person.id}
                  {...person}
                  compact
                  className={selectedIndex === i ? 'selected' : ''}
                />
              ))}
            </div>
          )}

          {results.organizations.length > 0 && (
            <div className="search-bar__group">
              <h3 className="search-bar__group-title">
                Organizations ({results.organizations.length})
              </h3>
              {results.organizations.map((org, i) => (
                <ActorCard
                  key={org.id}
                  {...org}
                  compact
                  className={
                    selectedIndex === results.persons.length + i
                      ? 'selected'
                      : ''
                  }
                />
              ))}
            </div>
          )}

          {results.persons.length === 0 &&
            results.organizations.length === 0 && (
              <p className="search-bar__no-results">
                No results for "{query}"
              </p>
            )}
        </div>
      )}
    </div>
  );
}
```

---

## Part 4: Visualization Strategy

### 4.1 Prioritization Framework

**Signal vs. Complexity Matrix:**

| Visualization | Signal Strength | Implementation Complexity | Data Dependency | Priority |
|---------------|-----------------|---------------------------|-----------------|----------|
| Concentration Bar Chart | Very High | Low | Aggregate API | P1 |
| Top Donors Leaderboard | Very High | Low | Aggregate API | P1 |
| Donation Timeline | High | Medium | Time series data | P2 |
| Party Comparison | High | Medium | Party affiliation fix | P2 |
| Flow Matrix (Sankey) | Medium | High | Complex joins | P3 |
| Network Graph | Medium | Very High | Graph preprocessing | P4 |
| Geographic Map | Low | High | Constituency data | P4 |

### 4.2 Priority 1 Visualizations

**4.2.1 Concentration Chart (Pareto)**

**Purpose:** Make the 65/1.3 split viscerally apparent

**Technical Approach:**
- Stacked horizontal bar chart
- D3.js for custom rendering
- Animate transitions when filters change

```tsx
// components/ConcentrationChart.tsx
import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { useConcentrationData } from '../hooks/useConcentrationData';
import { formatCurrency, formatPercent } from '../utils/format';

interface ConcentrationChartProps {
  filters?: {
    dateFrom?: string;
    dateTo?: string;
  };
}

export function ConcentrationChart({ filters }: ConcentrationChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const { data, isLoading } = useConcentrationData(filters);

  useEffect(() => {
    if (!data || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const width = 600;
    const height = 300;
    const margin = { top: 20, right: 120, bottom: 40, left: 80 };

    // Clear previous
    svg.selectAll('*').remove();

    // Scales
    const y = d3.scaleBand()
      .domain(data.brackets.map(d => d.label))
      .range([margin.top, height - margin.bottom])
      .padding(0.2);

    const x = d3.scaleLinear()
      .domain([0, 100])
      .range([margin.left, width - margin.right]);

    // Bars
    svg.selectAll('rect')
      .data(data.brackets)
      .join('rect')
      .attr('y', d => y(d.label)!)
      .attr('x', margin.left)
      .attr('height', y.bandwidth())
      .attr('width', 0)
      .attr('fill', d => d.label === '1M+' ? '#dc3545' : '#6c757d')
      .transition()
      .duration(750)
      .attr('width', d => x(d.pctOfTotal) - margin.left);

    // Labels
    svg.selectAll('.label-left')
      .data(data.brackets)
      .join('text')
      .attr('class', 'label-left')
      .attr('x', margin.left - 10)
      .attr('y', d => y(d.label)! + y.bandwidth() / 2)
      .attr('text-anchor', 'end')
      .attr('dominant-baseline', 'middle')
      .text(d => d.label);

    svg.selectAll('.label-right')
      .data(data.brackets)
      .join('text')
      .attr('class', 'label-right')
      .attr('x', d => x(d.pctOfTotal) + 10)
      .attr('y', d => y(d.label)! + y.bandwidth() / 2)
      .attr('dominant-baseline', 'middle')
      .text(d => `${formatPercent(d.pctOfTotal)} (${d.donorCount} donors)`);

  }, [data]);

  if (isLoading) {
    return <div className="chart-skeleton" />;
  }

  return (
    <div className="concentration-chart">
      <h3 className="concentration-chart__title">
        Donation Concentration by Donor Size
      </h3>
      <svg ref={svgRef} width={600} height={300} />
      <p className="concentration-chart__insight">
        <strong>Key Finding:</strong> Just {data?.brackets[0]?.donorCount || 277} donors
        ({formatPercent(1.3)}) control {formatPercent(data?.brackets[0]?.pctOfTotal || 65)} of all political donations.
      </p>
    </div>
  );
}
```

**4.2.2 Top Donors Leaderboard**

**Purpose:** Scannable list of major donors with interactive filtering

**Technical Approach:**
- Server-side rendering of initial list
- React hydration for filtering/sorting
- Virtualized list for performance

```tsx
// components/TopDonorsLeaderboard.tsx
import { useMemo } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useTopDonors } from '../hooks/useTopDonors';
import { ActorCard } from './ActorCard';
import { FilterPanel } from './FilterPanel';
import { formatCurrency, formatNumber } from '../utils/format';

export function TopDonorsLeaderboard() {
  const { filters, setFilters } = useFilterState();
  const { data, isLoading } = useTopDonors(filters);

  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: data?.results.length || 0,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80,
  });

  return (
    <div className="leaderboard">
      <div className="leaderboard__header">
        <h2>Top Donors</h2>
        <FilterPanel
          showDateRange
          showDonorType
          showLobbyingFilter
        />
      </div>

      <div
        ref={parentRef}
        className="leaderboard__list"
        style={{ height: '600px', overflow: 'auto' }}
      >
        <div
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            position: 'relative',
          }}
        >
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const donor = data!.results[virtualRow.index];
            return (
              <div
                key={donor.donorId}
                className="leaderboard__row"
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                <span className="leaderboard__rank">
                  {virtualRow.index + 1}
                </span>
                <ActorCard
                  id={donor.donorId}
                  name={donor.donorName}
                  type={donor.donorType === 'Individual' ? 'Person' : 'Organization'}
                  classification={donor.donorType}
                  stats={{
                    totalDonated: donor.totalDonated,
                    donationCount: donor.donationCount,
                    isLobbyingClient: donor.isLobbyingClient,
                  }}
                  compact
                />
                <span className="leaderboard__total">
                  {formatCurrency(donor.totalDonated)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
```

### 4.3 Priority 2 Visualizations

**4.3.1 Donation Timeline**

**Purpose:** Show how donation patterns change over time

**Technical Approach:**
- Recharts line/area chart
- Aggregated by quarter or year
- Optional comparison overlay (e.g., party vs party)

**4.3.2 Party Funding Comparison**

**Purpose:** Compare funding sources across parties

**Technical Approach:**
- Stacked bar chart per party
- Color-coded by donor type (unions, companies, individuals)
- Depends on Party Affiliation backend fix

### 4.4 Priority 3+ Visualizations (Deferred)

**Flow Matrix (Sankey Diagram)**
- High complexity
- Requires careful constraint (top N flows only)
- Risk of misleading visualization if not properly filtered
- Recommendation: Defer until core features stable

**Network Graph**
- Very high complexity
- Requires graph preprocessing pipeline
- Performance challenges with large datasets
- Recommendation: Defer to Phase 4; consider specialized tooling (Neo4j, Gephi export)

---

## Part 5: Editorial Integration (Wagtail)

### 5.1 Critique of Current CMS Integration

**Current State:**
- Basic page models (MyPage, DataPage)
- Snippets for Profile, Analysis, Quote
- No integration with political data models
- StreamField limited to heading/paragraph/image

**Problems:**

| Issue | Impact |
|-------|--------|
| No data-aware blocks | Editors cannot embed live stats or entity cards |
| No topic organization | No way to curate pages around themes (e.g., "Property Lobby") |
| CMS and data are disconnected | Editorial insights cannot reference actual data |

### 5.2 Data-Aware StreamField Blocks

**Design Principle:** Editorial content should be able to embed live data that updates automatically, while maintaining editorial control over presentation.

**Recommended Block Types:**

```python
# cms/blocks.py
from wagtail import blocks
from wagtail.snippets.blocks import SnippetChooserBlock

class ActorChooserBlock(blocks.StructBlock):
    """Embed an actor card in editorial content."""
    actor_id = blocks.IntegerBlock(help_text="Actor ID from the political database")
    display_mode = blocks.ChoiceBlock(choices=[
        ('card', 'Full Card'),
        ('inline', 'Inline Mention'),
        ('stats', 'Stats Only'),
    ], default='card')

    class Meta:
        icon = 'user'
        label = 'Actor Card'
        template = 'cms/blocks/actor_card.html'


class LiveStatBlock(blocks.StructBlock):
    """Display a live statistic from the database."""
    stat_type = blocks.ChoiceBlock(choices=[
        ('top_donor_total', 'Top Donor Total'),
        ('total_donations', 'Total Donations'),
        ('lobbying_overlap_count', 'Lobbying-Donation Overlap Count'),
        ('concentration_pct', 'Top 1% Concentration'),
        ('custom', 'Custom Query'),
    ])
    custom_query = blocks.CharBlock(
        required=False,
        help_text="For custom stats, specify the API endpoint"
    )
    label = blocks.CharBlock(
        required=False,
        help_text="Override the default label"
    )
    context = blocks.CharBlock(
        required=False,
        help_text="Additional context (e.g., 'since 2020')"
    )
    cached_value = blocks.CharBlock(
        required=False,
        help_text="Fallback value if API is unavailable"
    )
    last_updated = blocks.DateTimeBlock(
        required=False,
        help_text="When the cached value was last updated"
    )

    class Meta:
        icon = 'doc-full'
        label = 'Live Statistic'
        template = 'cms/blocks/live_stat.html'


class LeaderboardBlock(blocks.StructBlock):
    """Embed a leaderboard in editorial content."""
    leaderboard_type = blocks.ChoiceBlock(choices=[
        ('top_donors', 'Top Donors'),
        ('top_recipients', 'Top Recipients'),
        ('lobbying_overlap', 'Lobbying-Donation Overlap'),
    ])
    limit = blocks.IntegerBlock(default=10)
    filters = blocks.CharBlock(
        required=False,
        help_text="JSON filter object (e.g., {\"donor_type\": \"individual\"})"
    )
    show_filters = blocks.BooleanBlock(
        default=False,
        help_text="Allow readers to adjust filters"
    )

    class Meta:
        icon = 'list-ol'
        label = 'Leaderboard'
        template = 'cms/blocks/leaderboard.html'


class FactCalloutBlock(blocks.StructBlock):
    """
    Editorial fact callout with provenance.
    Includes query metadata for journalist-proof verification.
    """
    headline = blocks.CharBlock(
        help_text="The main fact (e.g., '277 donors control 65% of donations')"
    )
    body = blocks.RichTextBlock(
        required=False,
        help_text="Additional context or explanation"
    )
    source_query = blocks.CharBlock(
        required=False,
        help_text="API endpoint or SQL query that generated this fact"
    )
    data_as_of = blocks.DateBlock(
        required=False,
        help_text="Date when the underlying data was computed"
    )
    style = blocks.ChoiceBlock(choices=[
        ('info', 'Informational'),
        ('warning', 'Warning/Caution'),
        ('highlight', 'Key Finding'),
    ], default='info')

    class Meta:
        icon = 'warning'
        label = 'Fact Callout'
        template = 'cms/blocks/fact_callout.html'
```

**Block Templates:**

```html
<!-- cms/templates/cms/blocks/live_stat.html -->
<div class="live-stat live-stat--{{ self.stat_type }}"
     data-island="LiveStat"
     data-stat-type="{{ self.stat_type }}"
     data-custom-query="{{ self.custom_query }}"
     data-fallback="{{ self.cached_value }}">
    <div class="live-stat__value">
        {{ self.cached_value|default:"Loading..." }}
    </div>
    {% if self.label %}
    <div class="live-stat__label">{{ self.label }}</div>
    {% endif %}
    {% if self.context %}
    <div class="live-stat__context">{{ self.context }}</div>
    {% endif %}
    {% if self.last_updated %}
    <div class="live-stat__updated">
        Data as of {{ self.last_updated|date:"M j, Y" }}
    </div>
    {% endif %}
</div>
```

### 5.3 Neutral Join Model: ActorMention

**Design Principle:** Keep the Popolo data models clean by placing CMS relationships in a separate app.

```python
# editorial/models.py
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from wagtail.models import Page

class ActorMention(models.Model):
    """
    Links a Wagtail page to a political actor.
    Enables "Related Articles" on actor profiles without contaminating datafetch.
    """
    RELATIONSHIP_TYPES = [
        ('mentioned', 'Mentioned'),
        ('profiled', 'Primary Subject'),
        ('cited', 'Data Source'),
        ('compared', 'Comparison Subject'),
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

    def __str__(self):
        return f"{self.page.title} -> {self.actor}"


class TopicHub(Page):
    """
    Curated topic page that aggregates content and actors.
    Example: "The Property Lobby", "Trade Union Funding"
    """
    description = models.TextField(blank=True)

    # Automatic inclusion rules
    include_classifications = models.JSONField(
        default=list,
        help_text="Org classifications to auto-include (e.g., ['Trade Union'])"
    )
    include_keywords = models.JSONField(
        default=list,
        help_text="Name keywords for auto-matching"
    )

    # Manual curation overrides
    pinned_actors = models.JSONField(
        default=list,
        help_text="Actor IDs to always show at top"
    )
    excluded_actors = models.JSONField(
        default=list,
        help_text="Actor IDs to never show"
    )

    content_panels = Page.content_panels + [
        FieldPanel('description'),
        FieldPanel('include_classifications'),
        FieldPanel('include_keywords'),
        FieldPanel('pinned_actors'),
        FieldPanel('excluded_actors'),
    ]

    def get_actors(self):
        """Get actors for this topic, respecting curation rules."""
        from datafetch.models import Organization

        # Start with pinned actors
        actors = list(
            Organization.objects.filter(id__in=self.pinned_actors)
        )

        # Add auto-matched by classification
        if self.include_classifications:
            auto_matched = Organization.objects.filter(
                classification__in=self.include_classifications
            ).exclude(
                id__in=self.excluded_actors
            ).exclude(
                id__in=self.pinned_actors  # Don't duplicate pinned
            )
            actors.extend(auto_matched)

        return actors
```

### 5.4 Django Signals for ActorMention Lifecycle

**Critique Addressed:** The `ActorMention` join model requires Django signals to maintain referential integrity when Wagtail pages are deleted, updated, or have their revisions changed.

**Design Principle:** Signals should be defensive and handle edge cases (bulk deletes, page revisions, unpublishing).

#### 5.4.1 Signal Registration

Register signals in the editorial app's `apps.py`:

```python
# editorial/apps.py

from django.apps import AppConfig


class EditorialConfig(AppConfig):
    name = 'editorial'
    verbose_name = 'Editorial Integration'

    def ready(self):
        # Import signals to register them
        from . import signals  # noqa: F401
```

#### 5.4.2 Signal Handlers

```python
# editorial/signals.py

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver
from wagtail.signals import page_published, page_unpublished
from wagtail.models import Page

from .models import ActorMention
from .utils import extract_actor_mentions_from_page


@receiver(post_delete, sender=Page)
def handle_page_delete(sender, instance, **kwargs):
    """
    Clean up ActorMention records when a page is deleted.

    This handles:
    - Single page deletion via admin
    - Cascade deletions from parent pages
    - Bulk deletions

    Note: We use sender=Page (base class) to catch all page types.
    """
    # Delete all mentions for this page
    # Using filter + delete for efficiency (no per-object signals)
    ActorMention.objects.filter(page_id=instance.pk).delete()


@receiver(pre_delete, sender=Page)
def handle_page_pre_delete(sender, instance, **kwargs):
    """
    For bulk delete operations, we need to collect all descendant page IDs
    before they're deleted, as the tree structure will be lost after deletion.
    """
    # Store descendant IDs on the instance for post_delete cleanup
    # This handles deleting a parent page with many children
    instance._descendant_ids_for_cleanup = list(
        instance.get_descendants().values_list('pk', flat=True)
    )


@receiver(page_published)
def handle_page_published(sender, instance, **kwargs):
    """
    Update ActorMention records when a page is published.

    This:
    1. Extracts all actor references from the page's StreamField content
    2. Creates/updates ActorMention records
    3. Removes stale mentions that are no longer in the content

    Works with:
    - DataPage with ActorChooserBlock
    - Any page type with actor references
    """
    with transaction.atomic():
        # Extract current actor mentions from the page content
        current_mentions = extract_actor_mentions_from_page(instance)

        # Get existing mentions for this page
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
                ActorMention.objects.create(
                    page=instance,
                    actor_content_type_id=mention_data['actor_content_type_id'],
                    actor_id=mention_data['actor_id'],
                    relationship_type=mention_data['relationship_type'],
                    weight=mention_data.get('weight', 1)
                )

        # Remove stale mentions (actors no longer referenced in content)
        current_keys = {
            (m['actor_content_type_id'], m['actor_id'], m['relationship_type'])
            for m in current_mentions
        }
        stale_keys = existing_mentions - current_keys

        if stale_keys:
            # Build Q objects for efficient deletion
            from django.db.models import Q
            stale_filter = Q()
            for ct_id, actor_id, rel_type in stale_keys:
                stale_filter |= Q(
                    actor_content_type_id=ct_id,
                    actor_id=actor_id,
                    relationship_type=rel_type
                )

            ActorMention.objects.filter(page=instance).filter(stale_filter).delete()


@receiver(page_unpublished)
def handle_page_unpublished(sender, instance, **kwargs):
    """
    Optionally remove or mark mentions when a page is unpublished.

    Design decision: Keep mentions but mark them as from unpublished content,
    so "Related Articles" doesn't show draft/unpublished pages.
    """
    # Option 1: Delete mentions (strictest)
    # ActorMention.objects.filter(page=instance).delete()

    # Option 2: Mark as unpublished (keeps history)
    # This requires adding an 'is_published' field to ActorMention
    ActorMention.objects.filter(page=instance).update(
        # If you add this field:
        # is_page_published=False
    )


# --- Utility for extracting mentions from page content ---

def extract_actor_mentions_from_page(page) -> list[dict]:
    """
    Extract all actor mentions from a page's StreamField content.

    Scans all StreamField blocks for ActorChooserBlock instances
    and returns a list of mention data.

    Returns:
        List of dicts with keys:
        - actor_content_type_id
        - actor_id
        - relationship_type
        - weight (optional)
    """
    from django.contrib.contenttypes.models import ContentType
    from wagtail.fields import StreamField

    mentions = []

    # Get all StreamField fields on the page model
    for field in page._meta.get_fields():
        if not hasattr(field, 'stream_block'):
            continue

        # Get the StreamField value
        stream_value = getattr(page, field.name, None)
        if not stream_value:
            continue

        # Recursively extract actor references from blocks
        mentions.extend(_extract_mentions_from_stream(stream_value))

    return mentions


def _extract_mentions_from_stream(stream_value) -> list[dict]:
    """Recursively extract actor mentions from StreamField blocks."""
    from django.contrib.contenttypes.models import ContentType

    mentions = []

    for block in stream_value:
        block_type = block.block_type

        if block_type == 'actor_card':
            # ActorChooserBlock - direct actor reference
            actor_id = block.value.get('actor_id')
            display_mode = block.value.get('display_mode', 'card')

            if actor_id:
                # Determine content type (Person or Organization)
                # This requires a lookup - could be optimized with caching
                from datafetch.models import Actor
                try:
                    actor = Actor.objects.get(pk=actor_id)
                    ct = ContentType.objects.get_for_model(actor.__class__)

                    relationship_type = 'profiled' if display_mode == 'card' else 'mentioned'

                    mentions.append({
                        'actor_content_type_id': ct.id,
                        'actor_id': actor_id,
                        'relationship_type': relationship_type,
                        'weight': 2 if display_mode == 'card' else 1
                    })
                except Actor.DoesNotExist:
                    pass  # Actor was deleted, skip

        elif block_type == 'leaderboard':
            # LeaderboardBlock - might reference specific actors via filters
            filters = block.value.get('filters', {})
            # Mark any filtered party as "cited"
            if 'party_id' in filters:
                from datafetch.models import Organization
                ct = ContentType.objects.get_for_model(Organization)
                mentions.append({
                    'actor_content_type_id': ct.id,
                    'actor_id': filters['party_id'],
                    'relationship_type': 'cited',
                    'weight': 1
                })

        elif hasattr(block.value, '__iter__') and not isinstance(block.value, (str, dict)):
            # Nested StreamField (e.g., StructBlock with child StreamField)
            mentions.extend(_extract_mentions_from_stream(block.value))

    return mentions
```

#### 5.4.3 Edge Cases Handled

| Edge Case | Handling |
|-----------|----------|
| Page deleted | `post_delete` removes all mentions |
| Parent page with children deleted | `pre_delete` collects descendant IDs |
| Page content updated | `page_published` diffs and updates mentions |
| Page unpublished | Optionally marks mentions (keeps history) |
| Page revision created | No action - mentions only update on publish |
| Bulk page deletion | Uses efficient `filter().delete()` |
| Actor deleted | `ActorMention.actor` uses GenericFK - manual cleanup needed |

#### 5.4.4 Actor Deletion Handling

When an Actor is deleted, we need to clean up mentions that reference it:

```python
# datafetch/signals.py (add to existing signals)

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_delete
from django.dispatch import receiver

from datafetch.models import Actor


@receiver(post_delete, sender=Actor)
def handle_actor_delete(sender, instance, **kwargs):
    """
    Clean up ActorMention records when an Actor is deleted.

    Note: This catches deletions of both Person and Organization
    since they inherit from Actor.
    """
    from editorial.models import ActorMention

    ct = ContentType.objects.get_for_model(instance.__class__)
    ActorMention.objects.filter(
        actor_content_type=ct,
        actor_id=instance.pk
    ).delete()
```

#### 5.4.5 Trade-off Analysis

| Approach | Pros | Cons |
|----------|------|------|
| Signals (recommended) | Automatic, decoupled | Hidden behavior, debugging harder |
| Manual in views | Explicit, easy to debug | Easy to forget, code duplication |
| Celery tasks | Async, handles failures | Infrastructure overhead, eventual consistency |
| Database triggers | Fast, guaranteed | DB-specific, hard to maintain |

**Implementation Priority:** Phase 3.3 (Weeks 5-6) - Implement after ActorMention model is created.

### 5.5 Editorial Workflow

**Workflow for Creating a Topic Hub:**

1. Editor creates new TopicHub page in Wagtail
2. Sets `include_classifications: ["Trade Union"]`
3. System auto-populates with matching organizations
4. Editor reviews, pins the most important ones
5. Editor excludes any false positives
6. Page renders with live data from API

**Workflow for Writing an Article:**

1. Editor creates DataPage
2. Uses ActorChooserBlock to embed relevant actors
3. Uses LiveStatBlock for key statistics
4. Uses FactCalloutBlock for "key findings" with provenance
5. **System automatically creates ActorMention records via signals**
6. Actor profiles show "Related Articles" section
7. **When page is deleted, ActorMention records are automatically cleaned up**

---

## Part 6: Implementation Priorities

### Phase 3.1: Frontend Foundation (Weeks 1-2)

**Must Have:**

| Task | Effort | Dependencies |
|------|--------|--------------|
| Vite + django-vite integration | 3 days | None |
| Bootstrap 5 migration | 2 days | Vite |
| Island loader implementation | 1 day | Vite |
| SearchBar island | 3 days | API v2 search endpoint |
| FilterPanel component | 2 days | django-filter API |

**Should Have:**

| Task | Effort | Dependencies |
|------|--------|--------------|
| TypeScript configuration | 1 day | Vite |
| React Query setup | 1 day | None |
| CSS design tokens | 1 day | Bootstrap |

### Phase 3.2: Core Components (Weeks 3-4)

**Must Have:**

| Task | Effort | Dependencies |
|------|--------|--------------|
| ActorCard component | 2 days | None |
| StatCard component | 1 day | None |
| ConcentrationChart | 3 days | Aggregate API |
| TopDonorsLeaderboard | 3 days | Aggregate API |
| Actor profile page redesign | 3 days | ActorCard, StatCard |

**Should Have:**

| Task | Effort | Dependencies |
|------|--------|--------------|
| DonationsTable with virtual scroll | 2 days | React Query |
| RelationshipCard component | 1 day | None |
| Share functionality | 2 days | None |

### Phase 3.3: Editorial Integration (Weeks 5-6)

**Must Have:**

| Task | Effort | Dependencies |
|------|--------|--------------|
| ActorChooserBlock | 2 days | None |
| LiveStatBlock | 2 days | Aggregate API |
| FactCalloutBlock | 1 day | None |
| ActorMention model | 1 day | None |

**Should Have:**

| Task | Effort | Dependencies |
|------|--------|--------------|
| LeaderboardBlock | 2 days | Leaderboard component |
| TopicHub page type | 3 days | ActorMention |
| "Related Articles" on actor profiles | 1 day | ActorMention |

### Phase 3.4: Polish and Performance (Weeks 7-8)

**Should Have:**

| Task | Effort | Dependencies |
|------|--------|--------------|
| Donation timeline chart | 3 days | Time series API |
| Party comparison (if backend ready) | 2 days | Party affiliation |
| Performance optimization | 2 days | All components |
| Accessibility audit | 2 days | All components |
| Mobile responsive refinement | 2 days | All components |

### Deferred (Phase 4+)

- Network graph visualization
- Geographic constituency mapping
- Export functionality (CSV, PDF)
- User accounts and saved searches
- Email alerts for tracked entities

---

## Appendix A: Component Library Summary

| Component | Type | Status | Dependencies |
|-----------|------|--------|--------------|
| SearchBar | Island | Priority 1 | Search API |
| FilterPanel | Island | Priority 1 | django-filter |
| ActorCard | Component | Priority 1 | None |
| StatCard | Component | Priority 1 | None |
| ConcentrationChart | Island | Priority 1 | D3.js, Aggregate API |
| TopDonorsLeaderboard | Island | Priority 1 | React Query |
| DonationsTable | Island | Priority 2 | React Virtual |
| DonationTimeline | Island | Priority 2 | Recharts |
| PartyComparison | Island | Priority 2 | Party API |
| FlowMatrix | Island | Priority 3 | D3.js Sankey |
| NetworkGraph | Island | Deferred | Force-directed layout |

---

## Appendix B: Design Tokens

```css
/* static/css/tokens.css */

:root {
  /* Colors - Political Palette */
  --color-labour: #dc241f;
  --color-conservative: #0087dc;
  --color-libdem: #fdbb30;
  --color-snp: #fff95d;
  --color-green: #6ab023;
  --color-neutral: #6c757d;

  /* Semantic Colors */
  --color-donor: #198754;
  --color-recipient: #0d6efd;
  --color-lobbying: #fd7e14;
  --color-overlap: #dc3545;

  /* Typography */
  --font-family-base: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-family-mono: SFMono-Regular, Menlo, Monaco, monospace;
  --font-size-base: 1rem;
  --font-size-sm: 0.875rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.5rem;
  --font-size-2xl: 2rem;

  /* Spacing */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;

  /* Card Styles */
  --card-border-radius: 0.5rem;
  --card-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  --card-shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.15);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-base: 250ms ease;
}
```

---

## Appendix C: Accessibility Requirements

| Requirement | Implementation |
|-------------|----------------|
| Keyboard navigation | All interactive elements focusable, logical tab order |
| Screen reader support | ARIA labels on islands, live regions for dynamic content |
| Color contrast | WCAG AA minimum (4.5:1 for text, 3:1 for UI) |
| Focus indicators | Visible focus rings on all interactive elements |
| Motion preferences | Respect prefers-reduced-motion for animations |
| Text scaling | UI functional at 200% zoom |
| Alternative text | All images and charts have descriptive alt text |

---

## Appendix D: Performance Budget

| Metric | Target | Current (Estimated) |
|--------|--------|---------------------|
| First Contentful Paint | < 1.5s | Unknown |
| Largest Contentful Paint | < 2.5s | Unknown |
| Time to Interactive | < 3.5s | Unknown |
| Cumulative Layout Shift | < 0.1 | Unknown |
| Total Bundle Size (gzipped) | < 150KB | Unknown |
| Island JS per island | < 50KB | N/A |

**Performance Strategy:**
1. Server-render critical content (no JS required for initial view)
2. Lazy-load islands below the fold
3. Use React Query for intelligent caching
4. Virtualize long lists (donations table)
5. Prefetch likely navigation targets

---

*Document End*
