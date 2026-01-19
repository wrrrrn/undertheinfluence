# UnderTheInfluence Systems Architecture

**Version:** 4.0 (Islands Architecture Edition)
**Last Updated:** January 19, 2026
**Status:** Living Document

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture Diagrams](#architecture-diagrams)
4. [Component Overview](#component-overview)
5. [Data Flow](#data-flow)
6. [Frontend Architecture (Islands)](#frontend-architecture-islands)
7. [API Architecture](#api-architecture)
8. [Data Model Architecture](#data-model-architecture)
9. [Deployment Architecture](#deployment-architecture)
10. [Key Design Decisions](#key-design-decisions)

---

## System Overview

UnderTheInfluence is a Django-based web application that tracks lobbying influence in UK politics by aggregating data from multiple authoritative sources into a unified database following the Popolo open government data specification.

### Primary Functions

1. **Data Aggregation**: Import and normalize political data from diverse external sources
2. **Data Analysis**: Provide aggregate statistics, network analysis, and concentration metrics
3. **Data Presentation**: Server-rendered pages with selective interactive components
4. **API Access**: RESTful API for programmatic data consumption

### Current Status (January 2026)

**Working Features**:
- ✅ Full Django 6.0.1 + Wagtail 7.2.x stack
- ✅ Islands Architecture frontend with React 18 + Vite 5
- ✅ API v2 with aggregate endpoints and filtering
- ✅ Docker-based development environment
- ✅ Basic UI with homepage dashboard components
- ✅ Data import from ParlParse (MPs/Lords) and Ministers

**See `docs/CURRENT_STATE.md` for detailed feature inventory.**

---

## Technology Stack

### Backend

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Framework** | Django | 6.0.1 | Web framework, ORM, admin |
| **CMS** | Wagtail | 7.2.x | Content management, StreamFields |
| **API** | Django REST Framework | 3.15.x | RESTful API, serialization |
| **Database** | PostgreSQL | 15 | Primary data store (Docker) |
| **Cache** | Redis | 7 | Session cache, future API cache (Docker) |
| **Python** | Python | 3.12 | Runtime environment |
| **Polymorphism** | django-polymorphic | 4.2.x | Actor model inheritance |
| **Configuration** | python-decouple | 3.8 | Environment variables |

### Frontend

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Build System** | Vite | 5.x | Modern ES module bundler, HMR |
| **Framework** | React | 18.x | Selective hydration (islands only) |
| **Type Safety** | TypeScript | 5.x | Static typing, IDE support |
| **Styling** | Bootstrap 5 | 5.3.x | Layout/grid system |
| **Scoped Styles** | CSS Modules | (Vite) | Component-scoped SCSS |
| **State Management** | Zustand | 4.5.x | Lightweight store (URL-synchronized) |
| **Data Fetching** | TanStack Query | 5.x | API client with caching |
| **Django Integration** | django-vite | 3.0+ | Asset loading in templates |

### Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Containers** | Docker + Docker Compose | Development environment orchestration |
| **WSGI Server** | Gunicorn | Production application server (future) |
| **Reverse Proxy** | Nginx | Static files, SSL termination (future) |

---

## Architecture Diagrams

### High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      External Data Sources                      │
│  (ParlParse, Electoral Commission, APPC, TheyWorkForYou)       │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│             Management Commands (Data Import Layer)             │
│  import_parlparse | import_ministers | import_mpsinterests     │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│                    Django Application Layer                     │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  datafetch   │  │   api/v2     │  │     cms      │        │
│  │              │  │              │  │              │        │
│  │ • Models     │◄─┤ • ViewSets   │  │ • Wagtail    │        │
│  │ • Views      │  │ • Serializers│  │   Pages      │        │
│  │ • Admin      │  │ • Filters    │  │ • StreamField│        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                  │                  │                 │
│         └──────────────────┴──────────────────┘                 │
│                            ▼                                    │
│                  ┌──────────────────┐                          │
│                  │   PostgreSQL 15   │                          │
│                  └──────────────────┘                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│                   Frontend Layer (Hybrid)                       │
│                                                                 │
│  Django Templates (Server-Rendered)                            │
│  ┌─────────────────────────────────────────────────┐          │
│  │  <div class="container">                         │          │
│  │    <h1>Political Donations</h1>                  │          │
│  │                                                   │          │
│  │    <!-- React Island (Hydrated) -->              │          │
│  │    <div data-island="StatsGrid"                  │          │
│  │         data-api-url="/api/v2/aggregates/stats/">│          │
│  │      [Interactive Component]                     │          │
│  │    </div>                                        │          │
│  │                                                   │          │
│  │    <p>Static server-rendered content...</p>      │          │
│  │  </div>                                          │          │
│  └─────────────────────────────────────────────────┘          │
│                                                                 │
│  Vite Build System                                             │
│  ┌─────────────────────────────────────────────────┐          │
│  │ islands.tsx → Detects [data-island] markers     │          │
│  │ StatsGrid.tsx → Lazy-loads & hydrates           │          │
│  │ filterStore.ts → Syncs state to URL params      │          │
│  └─────────────────────────────────────────────────┘          │
└────────────────────────────────────────────────────────────────┘
```

### Request/Response Flow (Hybrid Architecture)

```
Browser Request
     │
     ▼
┌─────────────────┐
│  Django URLs    │ ← URL routing
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Django View    │ ← Server-side logic
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Django ORM     │ ← Database queries
│  (Polymorphic)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Django Template                    │
│  • Renders server-side HTML         │
│  • Includes [data-island] markers   │
│  • Loads Vite assets ({% vite %})   │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  HTML Response (to Browser)         │
│  • SEO-friendly content             │
│  • Works without JavaScript         │
│  • Island markers for hydration     │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Islands Hydration (Client-Side)   │
│  • islands.tsx detects markers      │
│  • Lazy-loads React components      │
│  • Hydrates with data-* props       │
│  • useQuery() fetches from API v2   │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  API v2 Request (AJAX)              │
│  • GET /api/v2/aggregates/stats/    │
│  • Includes filter params from URL  │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  DRF ViewSet                        │
│  • Applies django-filter filters    │
│  • Serializes aggregated data       │
│  • Returns JSON response            │
└─────────────────────────────────────┘
```

### Docker Compose Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  Docker Compose                          │
└──────────────────┬────────────────────┬──────────────────┘
                   │                    │
         ┌─────────┴────────┐  ┌───────┴────────┐
         │                  │  │                 │
         ▼                  ▼  ▼                 ▼
    ┌────────┐      ┌────────────┐      ┌──────────┐
    │  web   │      │   vite     │      │    db    │
    │ Django │      │  Node 20   │      │ Postgres │
    │  6.0   │      │  Vite HMR  │      │    15    │
    │ :8000  │      │   :5173    │      │  :5432   │
    └────┬───┘      └─────┬──────┘      └────┬─────┘
         │                │                   │
         │                │                   │
         │     ┌──────────┘                   │
         │     │                              │
         ▼     ▼                              ▼
    ┌────────────────────────────────────────────┐
    │         Persistent Volumes                 │
    │  • postgres_data (DB persistence)          │
    │  • node_modules (anonymous, prevents sync) │
    └────────────────────────────────────────────┘
```

**Key Docker Services**:
- **web**: Django 6.0 application (port 8000)
  - Serves API endpoints
  - Renders Django templates
  - Proxies Vite assets in dev mode
- **vite**: Node 20 development server (port 5173)
  - Hot Module Replacement (HMR)
  - TypeScript compilation
  - SCSS preprocessing
- **db**: PostgreSQL 15 database (port 5432)
  - Persistent data storage
  - Full-text search (pg_trgm)
- **redis**: Redis 7 cache (port 6379)
  - Session storage
  - Future API caching

---

## Component Overview

### 1. datafetch App (Core Data Layer)

**Purpose**: Popolo-based data models, data import, and public-facing views.

**Directory Structure**:
```
datafetch/
├── models/
│   ├── models.py               # Core Popolo models (Actor, Person, Org)
│   ├── influence_mapping.py    # Donation, Consultancy
│   └── popolo/
│       ├── behaviors.py        # Timestampable, Dateframeable
│       └── querysets.py        # DateframeableQuerySet
├── management/commands/        # Data import
│   ├── import_parlparse.py     # ✅ Working
│   ├── import_ministers.py     # ✅ Working
│   ├── import_mpsinterests.py  # ✅ Working
│   ├── import_ec.py            # ⚠️ Needs update
│   └── import_appc.py          # ⚠️ Needs rewrite
├── views.py                    # ActorView, SearchView
├── admin.py                    # Django admin configuration
└── templates/                  # Django templates
```

**Key Models**:
- `Actor` (polymorphic base) → `Person`, `Organization`
- `Membership` (Person ↔ Organization + Post)
- `Donation` (Actor → Actor with £ value)
- `Consultancy` (Organization client ↔ Organization agency)

**Generic Relations** (Popolo metadata):
- `Identifier`, `OtherName`, `ContactDetail`, `Link`, `Source`, `Note`

---

### 2. api/v2 App (REST API Layer)

**Purpose**: JSON API for frontend islands and external consumers.

**Directory Structure**:
```
api/v2/
├── views.py        # DRF ViewSets and APIViews
├── serializers.py  # DRF serializers
├── filters.py      # django-filter configuration
├── pagination.py   # Custom pagination classes
└── urls.py         # API routing
```

**Aggregate Endpoints** (Dashboard Data):
```
GET /api/v2/aggregates/stats/
  → Total donations, total value, concentration metrics
  → Filters: date_range, value_min, donor_type

GET /api/v2/aggregates/party-donations/
  → Total received per party, donor count, avg donation
  → Filters: date_range, value_min, donor_type

GET /api/v2/aggregates/top-donors/
  → Top N donors ranked by total donated
  → Paginated (100/page), supports filtering

GET /api/v2/aggregates/donor-concentration/
  → Gini coefficient, HHI, concentration category
  → Pareto distribution metrics
```

**Actor Endpoints** (Profile Data):
```
GET /api/v2/actors/{id}/
  → Actor detail (name, type, image, classification)

GET /api/v2/actors/{id}/donations-from/
  → Donations received by this actor

GET /api/v2/actors/{id}/donations-to/
  → Donations made by this actor

GET /api/v2/actors/{id}/consultancies/
  → Lobbying relationships (if organization)
```

**Common Query Parameters**:
- `received_after` / `received_before`: Date filters (YYYY-MM-DD or YYYY or YYYY-MM)
- `value_min` / `value_max`: Donation value range
- `donor_type`: Filter by person/organization
- `limit` / `offset`: Pagination

---

### 3. cms App (Wagtail Integration)

**Purpose**: Editorial content management with embedded data islands.

**Directory Structure**:
```
cms/
├── models.py               # Wagtail page models (HomePage)
├── blocks.py               # Custom StreamField blocks
├── templates/cms/blocks/   # Block templates with island markers
│   ├── stats_grid.html
│   ├── party_breakdown.html
│   └── top_donors_leaderboard.html
└── migrations/
```

**Custom StreamField Blocks**:
- `StatsGridBlock`: Embeds homepage metrics island
- `PartyBreakdownBlock`: Embeds party donation breakdown
- `TopDonorsLeaderboardBlock`: Embeds paginated leaderboard
- `FilterPanelBlock`: Embeds filter controls
- `DataVisualizationBlock`: Container for all visualization blocks

**How It Works**:
1. Editor adds block in Wagtail admin
2. Block renders server-side template with `[data-island]` marker
3. Vite detects marker and hydrates React component
4. Component fetches live data from API v2

---

### 4. frontend/ (Islands Architecture)

**Purpose**: Selective React hydration for interactive components.

**Directory Structure**:
```
frontend/
├── islands/                # Top-level interactive components
│   ├── StatsGrid.tsx       # ✅ Homepage metrics
│   ├── PartyBreakdown.tsx  # ✅ Party donation grid
│   ├── TopDonorsLeaderboard.tsx # ✅ Paginated leaderboard
│   ├── FilterPanel.tsx     # ✅ Filter controls
│   └── ConcentrationChart.tsx # ⏳ Scaffolded (not implemented)
├── components/             # Reusable primitives
│   ├── StatCard.tsx        # ✅ Metric display card
│   ├── PartyCard.tsx       # ✅ Party with color accent
│   └── ActorCard.tsx       # ✅ Person/org card
├── hooks/                  # Custom React hooks
│   ├── useTopDonors.ts     # ✅ TanStack Query hook
│   └── useHomepageStats.ts # ✅ TanStack Query hook
├── store/                  # Zustand state management
│   └── filterStore.ts      # ✅ URL-synchronized filters
├── types/                  # TypeScript definitions
│   ├── actor.ts
│   └── filters.ts
├── styles/                 # Global SCSS + variables
├── islands.tsx             # ✅ Island loader/registry
├── main.tsx                # Vite entry point
├── package.json            # NPM dependencies
├── vite.config.ts          # Vite configuration
└── tsconfig.json           # TypeScript configuration
```

**Island Lifecycle**:
1. **Server Render**: Django template outputs HTML with `<div data-island="Name">`
2. **Island Detection**: `islands.tsx` runs on `DOMContentLoaded`
3. **Lazy Load**: Dynamic import (`() => import('./islands/Name')`)
4. **Hydration**: `createRoot(el).render(<Component />)`
5. **Data Fetch**: Island uses `useQuery()` to call API v2
6. **State Sync**: `useFilterStore()` reads/writes URL parameters

**Why This Works**:
- SEO-friendly (server-rendered HTML)
- Fast initial load (minimal JavaScript)
- Progressive enhancement (works without JS)
- Shareable URLs (filter state in URL)
- No client-side routing needed

---

## Data Flow

### Data Import Pipeline

```
External API (e.g., ParlParse JSON)
          │
          ▼
┌───────────────────┐
│  fetch_json()     │ ← helpers.py caches to data/ directory
│  (with caching)   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Parse JSON       │ ← Extract fields, normalize names
│  Transform data   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  get_or_create()  │ ← Deduplicate by external identifiers
│  Django ORM       │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  PostgreSQL       │
│  Database         │
└───────────────────┘
```

**Key Features**:
- **File-based caching**: `data/` directory stores fetched files
- **Rate limiting**: 0.5s delay between requests
- **Deduplication**: Uses `get_or_create()` with external IDs
- **Canonical resolution**: `canonical_person` / `canonical_organization` fields

### API Request Flow (Island → API → Database)

```
React Island (Browser)
          │
          ▼
┌───────────────────┐
│  useQuery()       │ ← TanStack Query with 5min cache
│  fetch(API v2)    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  DRF ViewSet      │ ← django-filter applies query params
│  (api/v2/views)   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  ORM Aggregation  │ ← Sum(), Count(), annotate()
│  .values()        │
│  .annotate()      │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  PostgreSQL       │
│  (GROUP BY query) │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  DRF Serializer   │ ← Transform to JSON
│  (TopDonorSer...)  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  JSON Response    │ ← HTTP 200 with data
└─────────┬─────────┘
          │
          ▼
React Island (Browser)
  → Renders UI with data
```

### URL State Flow (Filter Changes)

```
User Changes Filter (FilterPanel)
          │
          ▼
┌───────────────────┐
│  setFilter({...}) │ ← Zustand store action
│  (filterStore.ts) │
└─────────┬─────────┘
          │
          ├─────────────────────┐
          │                     │
          ▼                     ▼
┌───────────────────┐   ┌──────────────────┐
│  Update URL       │   │  Update store    │
│  pushState()      │   │  state           │
└─────────┬─────────┘   └────────┬─────────┘
          │                      │
          └──────────┬───────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │  All islands using  │
          │  useFilterStore()   │
          │  auto-refetch       │
          └─────────┬───────────┘
                    │
                    ▼
          ┌─────────────────────┐
          │  New API calls with │
          │  updated params     │
          └─────────────────────┘
```

**Benefits**:
- Shareable URLs (copy/paste link with filters)
- Browser back/forward navigation works
- Multiple islands synchronized automatically
- No custom event system needed

---

## Frontend Architecture (Islands)

### Islands Architecture Philosophy

**"Progressive Enhancement with Selective Interactivity"**

- **Server-rendered by default**: Django templates render full HTML
- **Islands hydrate selectively**: React components load only where needed
- **URL-driven state**: Filter state lives in URL parameters
- **No client-side routing**: Django handles all navigation

### Island Registry (`frontend/islands.tsx`)

```typescript
const islands = {
  'StatsGrid': () => import('./islands/StatsGrid'),
  'PartyBreakdown': () => import('./islands/PartyBreakdown'),
  'TopDonorsLeaderboard': () => import('./islands/TopDonorsLeaderboard'),
  'FilterPanel': () => import('./islands/FilterPanel'),
  'ConcentrationChart': () => import('./islands/ConcentrationChart'),
};

// Detect and hydrate all islands
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

### State Management (Zustand)

```typescript
// frontend/store/filterStore.ts
interface FilterState {
  dateFrom?: string;    // YYYY or YYYY-MM or YYYY-MM-DD
  dateTo?: string;
  minValue?: number;
  donorType?: 'person' | 'organization' | 'trade-union' | 'company';
  page: number;
}

const useFilterStore = create((set) => ({
  ...DEFAULT_STATE,

  setFilter: (updates) => {
    // Update URL parameters
    const params = new URLSearchParams(window.location.search);
    Object.entries(updates).forEach(([key, value]) => {
      if (value) params.set(key, String(value));
      else params.delete(key);
    });
    window.history.pushState({}, '', `?${params}`);

    // Update store
    set(updates);
  },

  loadFromUrl: () => {
    const params = new URLSearchParams(window.location.search);
    set({
      dateFrom: params.get('date_from') || undefined,
      dateTo: params.get('date_to') || undefined,
      minValue: params.get('value_min') ? Number(params.get('value_min')) : undefined,
      donorType: params.get('donor_type') as any || undefined,
      page: Number(params.get('page')) || 1,
    });
  },
}));

// Initialize from URL on page load
useFilterStore.getState().loadFromUrl();

// Handle browser back/forward
window.addEventListener('popstate', () => {
  useFilterStore.getState().loadFromUrl();
});
```

### Data Fetching Pattern (TanStack Query)

```typescript
// frontend/hooks/useTopDonors.ts
function useTopDonors(limit = 20) {
  const { dateFrom, dateTo, minValue, donorType, page } = useFilterStore();

  const queryParams = new URLSearchParams();
  if (dateFrom) queryParams.set('received_after', dateFrom);
  if (dateTo) queryParams.set('received_before', dateTo);
  if (minValue) queryParams.set('value_min', String(minValue));
  if (donorType) queryParams.set('donor_type', donorType);
  queryParams.set('limit', String(limit));
  queryParams.set('offset', String((page - 1) * limit));

  return useQuery({
    queryKey: ['top-donors', queryParams.toString()],
    queryFn: async () => {
      const response = await fetch(`/api/v2/aggregates/top-donors/?${queryParams}`);
      if (!response.ok) throw new Error('Failed to fetch');
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
```

**Why TanStack Query?**
- Automatic caching (5min stale time)
- Loading/error states built-in
- Automatic refetching when query key changes
- Devtools for debugging

### Styling Strategy

**CSS Modules** for scoped component styles:
```scss
// frontend/islands/StatsGrid.module.scss
.statsGrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}
```

**Bootstrap 5** for layout/grid:
```typescript
<div className="container">
  <div className="row g-3">
    <div className="col-md-3">
      <FilterPanel />
    </div>
    <div className="col-md-9">
      <TopDonorsLeaderboard />
    </div>
  </div>
</div>
```

**Typography** (from `docs/FRONTEND_DESIGN.md`):
- **Headings**: Playfair Display (editorial serif)
- **Body/UI**: Inter (modern sans-serif)
- **Currency**: Tabular nums, letter-spacing -0.01em

---

## API Architecture

### Design Principles

1. **Read-Only**: All endpoints are GET only (no mutations)
2. **Filter-Driven**: Consistent query parameters across endpoints
3. **Paginated**: Large datasets use limit/offset pagination
4. **Cached**: Future Redis caching for aggregate endpoints
5. **Versioned**: `/api/v2/` namespace (v1 deprecated)

### Aggregate Endpoints Design

**Pattern**: Optimized for dashboard widgets, not general-purpose queries.

```python
# api/v2/views.py
class TopDonorsView(generics.ListAPIView):
    serializer_class = TopDonorSerializer
    pagination_class = AggregatePagination

    def get_queryset(self):
        # 1. Start with donations
        qs = Donation.objects.exclude(donor__isnull=True)

        # 2. Apply filters from query params
        filterset = DonationFilterSet(self.request.query_params, queryset=qs)
        qs = filterset.qs

        # 3. Aggregate by donor
        aggregated = qs.values('donor_id', 'donor__name').annotate(
            total_donated=Sum('value'),
            donation_count=Count('id')
        ).order_by('-total_donated')

        return aggregated
```

**Performance Optimization**:
- Only fetch Actor objects for paginated subset (not all 21k donors)
- Reduces query time from ~3s to <0.5s

### Actor Endpoints Design

**Pattern**: Relational queries with prefetching.

```python
# api/v2/views.py
@action(detail=True, methods=['get'])
def donations_from(self, request, pk=None):
    actor = self.get_object()

    # Use canonical field if available
    donations = Donation.objects.filter(
        Q(recipient_id=actor.id) | Q(canonical_recipient_id=actor.id)
    ).select_related('donor').prefetch_related(
        'donor__identifiers',
        'sources'
    )

    # Apply filters
    filterset = DonationFilterSet(request.query_params, queryset=donations)

    # Paginate and serialize
    page = self.paginate_queryset(filterset.qs)
    serializer = DonationSerializer(page, many=True)
    return self.get_paginated_response(serializer.data)
```

---

## Data Model Architecture

### Popolo Specification

Based on [Popolo Project](http://www.popoloproject.com/) open government data standard.

**Key Concepts**:
- **Interoperability**: Common vocabulary with other civic tech projects
- **Flexibility**: Supports partial dates, multiple identifiers, generic relations
- **Completeness**: Rich model for political data

### Model Hierarchy

```
┌──────────────────────────────────────┐
│  PolymorphicModel (django-polymorphic) │
│  • Single-table inheritance           │
│  • Automatic type casting             │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Actor (Polymorphic Base)            │
│  • name, image, start_date, end_date │
│  • Generic relations (identifiers,   │
│    other_names, links, sources)      │
└──────┬───────────────────────────────┘
       │
       ├─────────────────┬──────────────┐
       │                 │              │
       ▼                 ▼              ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│   Person    │  │ Organization │  │ (Future      │
│             │  │              │  │  types)      │
│ • given_name│  │ • summary    │  └──────────────┘
│ • family_name│ │ • description│
│ • email     │  │ • classification│
│ • gender    │  │ • parent     │
│ • birth_date│  │ • founding_date│
└─────────────┘  └──────────────┘
```

### Relationship Models

```
Membership
├── person (FK → Person)
├── organization (FK → Organization)
├── post (FK → Post, optional)
├── on_behalf_of (FK → Organization, optional)
├── role (CharField: "Member of Parliament", "Minister", etc.)
├── start_date (CharField: YYYY[-MM[-DD]])
└── end_date (CharField: YYYY[-MM[-DD]])

Donation
├── donor (FK → Actor, can be Person or Organization)
├── recipient (FK → Actor, can be Person or Organization)
├── canonical_donor (FK → Actor, for entity resolution)
├── canonical_recipient (FK → Actor, for entity resolution)
├── value (DecimalField)
├── donation_type (CharField)
├── received_date (DateField)
└── accepted_date (DateField)

Consultancy
├── client (FK → Organization)
├── agency (FK → Organization)
├── start_date (CharField: YYYY[-MM[-DD]])
└── end_date (CharField: YYYY[-MM[-DD]])
```

### Abstract Behaviors

```python
class Timestampable(models.Model):
    created_at = AutoCreatedField()
    updated_at = AutoLastModifiedField()

    class Meta:
        abstract = True

class Dateframeable(models.Model):
    start_date = CharField(max_length=10, blank=True, null=True)
    end_date = CharField(max_length=10, blank=True, null=True)

    objects = DateframeableQuerySet.as_manager()

    class Meta:
        abstract = True

    def current(self, moment=None):
        """True if this object was active at the given moment."""
        # Implementation handles YYYY, YYYY-MM, YYYY-MM-DD formats
```

### Generic Relations (Popolo Metadata)

```python
# All these can attach to any model
Identifier (scheme + identifier)
OtherName (name + note)
ContactDetail (type + value + label)
Link (url + note)
Source (url + note)
Note (note)
```

**Why Generic Relations?**
- Avoids separate join tables for each model
- Consistent interface across types
- Follows Popolo specification

**Trade-offs**:
- Slightly slower queries than direct ForeignKey
- Cannot use database foreign key constraints
- ORM queries more complex

---

## Deployment Architecture

### Current (Development Only)

**Docker Compose** orchestration for local development:

```yaml
# docker-compose.yml
services:
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/code
    ports:
      - "8000:8000"
    environment:
      - DATABASE_SYSTEM=postgresql
      - UTI_DB_HOST=db
    depends_on:
      - db
      - redis

  vite:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - .:/app
      - /app/node_modules  # Anonymous volume
    command: npm run dev
    ports:
      - "5173:5173"
    environment:
      - NODE_ENV=development

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=undertheinfluence
      - POSTGRES_USER=uti
      - POSTGRES_PASSWORD=***

  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

### Future (Production)

**Planned Architecture** (not yet implemented):

```
Internet
    │
    ▼
┌──────────────┐
│  Nginx       │ ← SSL termination, static files
│  (Reverse    │
│   Proxy)     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Gunicorn    │ ← WSGI server (Django app)
│  (Workers)   │
└──────┬───────┘
       │
       ├────────────────┬─────────────────┐
       │                │                 │
       ▼                ▼                 ▼
┌────────────┐  ┌────────────┐  ┌─────────────┐
│ PostgreSQL │  │   Redis    │  │ Static Files│
│    15      │  │     7      │  │   (CDN?)    │
└────────────┘  └────────────┘  └─────────────┘
```

**Production Requirements**:
- Environment variables in `.env` file (not committed)
- `DEBUG=False` in production
- `ALLOWED_HOSTS` configured
- Static files collected to `static/dist/`
- Database migrations applied
- SSL certificates configured
- Monitoring/logging setup (future)

---

## Key Design Decisions

### 1. Islands Architecture (Not SPA)

**Decision**: Use server-rendered Django templates with selective React hydration.

**Rationale**:
- **SEO**: Search engines index server-rendered HTML
- **Performance**: Fast initial load, minimal JavaScript
- **Accessibility**: Works without JavaScript (progressive enhancement)
- **Maintainability**: Natural Django integration, no client-side routing

**Trade-offs**:
- Not suitable for real-time collaboration features
- Client-side routing would require additional complexity
- State management more complex than pure SPA

**Alternatives Considered**:
- ❌ **Full SPA**: Poor SEO, slow initial load, requires client-side routing
- ❌ **HTMX**: Insufficient for complex visualizations (network graphs)
- ❌ **Alpine.js**: Too limited for stateful components

---

### 2. Polymorphic Models (Not Separate Tables)

**Decision**: Use django-polymorphic for Actor base class.

**Rationale**:
- Single table for querying all actors (search, relationships)
- Type-specific fields in subclasses (Person.given_name, Organization.parent)
- Foreign keys can reference any actor type (Donation.donor)
- Automatic downcasting to correct type

**Trade-offs**:
- Additional database joins for type resolution
- More complex queries than separate tables
- ContentType dependency

**Alternatives Considered**:
- ❌ **Separate Person/Organization tables**: Cannot query all actors together
- ❌ **Abstract base class**: Cannot use ForeignKey to Actor

---

### 3. Partial Dates as Strings (Not DateField)

**Decision**: Store dates as `CharField` with YYYY/YYYY-MM/YYYY-MM-DD format.

**Rationale**:
- Supports incomplete dates (common in political data: "born 1945")
- Matches Popolo specification
- Lexicographic ordering works correctly ("2020" < "2020-06" < "2020-06-15")

**Trade-offs**:
- Cannot use database date functions directly
- Requires custom validation (regex + strptime)
- Comparison edge cases (YYYY vs YYYY-MM)

**Alternatives Considered**:
- ❌ **DateField with defaults**: Misleading (implies precision we don't have)
- ❌ **Separate year/month/day fields**: More complex queries

---

### 4. URL-Driven State (Not Client-Side Only)

**Decision**: Store filter state in URL parameters, synchronized via Zustand.

**Rationale**:
- **Shareable links**: Copy/paste URL with filters intact
- **Browser navigation**: Back/forward buttons work
- **Deep linking**: Direct access to filtered views
- **Multiple islands**: Automatic synchronization

**Trade-offs**:
- URL can get long with many filters
- Sensitive filters would need different approach
- More complex than pure client-side state

**Alternatives Considered**:
- ❌ **Client-side only**: Not shareable, breaks back button
- ❌ **Custom events**: Race conditions, "event soup"

---

### 5. Zustand (Not Redux/MobX)

**Decision**: Use Zustand for lightweight state management.

**Rationale**:
- **Minimal boilerplate**: 1KB gzipped
- **No provider**: Works without React context
- **TypeScript support**: First-class types
- **Prevents event soup**: Centralized state updates

**Trade-offs**:
- Smaller ecosystem than Redux
- No time-travel debugging by default
- Less middleware options

**Alternatives Considered**:
- ❌ **Redux**: Too much boilerplate for small app
- ❌ **Custom events**: Race conditions, no centralized state

---

### 6. CSS Modules (Not Tailwind/Styled-Components)

**Decision**: Use CSS Modules with SCSS for component styling.

**Rationale**:
- **Scoped styles**: Prevents conflicts between components
- **Familiar syntax**: Standard CSS/SCSS
- **Bootstrap compatibility**: Works alongside global styles
- **SCSS preprocessing**: Variables, mixins, nesting

**Trade-offs**:
- More verbose than Tailwind utility classes
- Requires naming conventions (BEM-like)

**Alternatives Considered**:
- ❌ **Tailwind**: Cluttered markup, harder to override Bootstrap
- ❌ **Styled-Components**: Runtime cost, JSX clutter

---

### 7. Django Vite (Not Webpack/Parcel)

**Decision**: Use Vite via django-vite for asset bundling.

**Rationale**:
- **Fast HMR**: Instant hot module replacement
- **Modern ES modules**: No bundling in dev mode
- **TypeScript support**: Built-in, no config
- **Django integration**: django-vite handles asset loading

**Trade-offs**:
- Newer tool (less mature than Webpack)
- Browser support (requires modern browsers)

**Alternatives Considered**:
- ❌ **Webpack**: Slow HMR, complex configuration
- ❌ **Parcel**: Less ecosystem, fewer plugins

---

## Future Considerations

### Performance Optimization (High Priority)
- **Materialized views**: For expensive aggregate queries
- **Redis caching**: API endpoint caching (15min TTL)
- **Database indexes**: Based on query profiling
- **Connection pooling**: pgbouncer for PostgreSQL

### Feature Additions (Medium Priority)
- **Politicians directory page**: `/politicians/` with filtering
- **Network visualization**: D3.js force-directed graphs
- **Enhanced profiles**: Tabbed interface, timeline, network view
- **Data export**: CSV download for tables

### Testing (Low Priority - Future)
- **Frontend tests**: Vitest + React Testing Library
- **Backend tests**: pytest-django for API
- **Integration tests**: End-to-end testing
- **Accessibility tests**: WCAG 2.1 AA compliance

### Monitoring (Low Priority - Future)
- **Application monitoring**: Sentry for error tracking
- **Performance monitoring**: APM tool
- **Logging**: Structured logging to ELK stack
- **Metrics**: Prometheus metrics export

---

## Appendix: Configuration Reference

### Environment Variables

**Required**:
```bash
DEBUG=True                          # Development mode
DATABASE_SYSTEM=postgresql          # Database backend
SECRET_KEY=***                      # Django secret key (change in production!)
```

**Database (if PostgreSQL)**:
```bash
UTI_DB_NAME=undertheinfluence       # Database name
UTI_DB_USER=uti                     # Database user
UTI_DB_PASS=***                     # Database password
UTI_DB_HOST=db                      # Host (service name in Docker)
UTI_DB_PORT=5432                    # Port
```

**Optional**:
```bash
ALLOWED_HOSTS=localhost,127.0.0.1   # Permitted hostnames
BASE_URL=http://localhost:8000      # Public base URL
TWFY_API_KEY=***                    # TheyWorkForYou API key (future)
```

**Docker Compose Auto-Configured**:
- Database connection settings
- Redis connection settings
- Vite dev server host

---

## References

**Project Documentation**:
- `docs/CURRENT_STATE.md` - Feature inventory and status
- `docs/data-models.md` - Detailed data model reference
- `docs/FRONTEND_DESIGN.md` - UI/UX design system
- `docs/FRONTEND_IMPLEMENTATION.md` - Detailed implementation plan
- `CLAUDE.md` - Instructions for Claude Code

**External Resources**:
- [Popolo Specification](http://www.popoloproject.com/)
- [Islands Architecture](https://jasonformat.com/islands-architecture/)
- [Django 6.0 Documentation](https://docs.djangoproject.com/en/6.0/)
- [Vite Guide](https://vitejs.dev/guide/)
- [TanStack Query](https://tanstack.com/query/latest)

---

**Document Maintenance**: Update this document when:
- Architecture decisions are made
- New components/apps are added
- Technology stack changes
- Deployment architecture changes

**Last Major Update**: January 19, 2026 (v4.0 - Islands Architecture Edition)
