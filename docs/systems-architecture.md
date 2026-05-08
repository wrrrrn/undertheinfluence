# UnderTheInfluence Systems Architecture

**Version:** 5.0 (Astro Frontend + API Caching)
**Last Updated:** April 16, 2026
**Status:** Living Document

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture Diagrams](#architecture-diagrams)
4. [Component Overview](#component-overview)
5. [Data Flow](#data-flow)
6. [Frontend Architecture (Astro + Svelte)](#frontend-architecture-astro--svelte)
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

### Current Status (April 2026)

**Working Features**:
- ✅ Django 6.0.4 + Wagtail 7.2.x backend (headless API)
- ✅ Astro 5 + Svelte 5 + Tailwind CSS frontend (decoupled, port 4321)
- ✅ D3.js minister network visualization (force-directed, 90 ministers, 298 donors)
- ✅ API v2 with aggregate endpoints, filtering, and Redis caching (1hr TTL)
- ✅ 10 Astro pages: homepage, directory, network, meetings, lobbying, parties, analysis, actor profiles
- ✅ Actor profile pages with unified timeline (donations, meetings, roles, consultancies)
- ✅ Full interconnectedness: every entity name links to its profile page
- ✅ Docker-based development environment (PostgreSQL, Redis, Django, Astro)
- ✅ Data import from ParlParse, Ministers, MPs' Register, Ministerial Meetings
- ✅ Entity resolution and Companies House enrichment

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
| **Cache** | Redis | 7 | API aggregate caching (1hr TTL), session cache |
| **Python** | Python | 3.12 | Runtime environment |
| **Polymorphism** | django-polymorphic | 4.2.x | Actor model inheritance |
| **Configuration** | python-decouple | 3.8 | Environment variables |

### Frontend (Decoupled)

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Orchestrator** | Astro | 5.x | SSR pages, partial hydration, routing |
| **Components** | Svelte | 5.x | Interactive components (Runes-based reactivity) |
| **Visualization** | D3.js | 7.x | Force simulation, scales (math only — SVG rendered by Svelte) |
| **Styling** | Tailwind CSS | 3.x | Utility-first styling, design system tokens |
| **Typography** | Zodiak + Satoshi | — | Display serif + geometric sans (Fontshare) |
| **Runtime** | Node.js | 20.x | Astro SSR adapter |

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
- **api**: Django 6.0.4 application (port 8000)
  - Headless API (JSON only — no HTML templates)
  - Wagtail CMS admin
  - Django admin
- **web**: Astro 5 frontend (port 4321)
  - SSR pages with Svelte component hydration
  - Fetches data from api service at build/request time
- **db**: PostgreSQL 15 database (port 5432)
  - Persistent data storage
  - Full-text search (pg_trgm)
- **redis**: Redis 7 cache (port 6379)
  - API aggregate endpoint caching (1hr TTL via `cache_utils.py`)
  - Session storage

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

**Purpose**: JSON API for Astro frontend and external consumers.

**Directory Structure**:
```
api/v2/
├── views.py        # DRF ViewSets and APIViews
├── serializers.py  # DRF serializers
├── filters.py      # django-filter configuration
├── pagination.py   # Custom pagination classes
├── cache_utils.py  # Redis cache key generation, invalidation
└── urls.py         # API routing
```

**Aggregate Endpoints** (Dashboard Data — all cached 1hr via Redis):
```
GET /api/v2/aggregates/stats/                    [cached]
  → Total donations, total value, concentration metrics

GET /api/v2/aggregates/party-donations/          [cached]
  → Total received per party, donor count
  → Party filter pushed into SQL (not Python post-filter)

GET /api/v2/aggregates/top-recipients/           [cached]
  → Top N recipients ranked by total received
  → select_related('polymorphic_ctype') to avoid N+1

GET /api/v2/aggregates/top-lobbying-clients/     [cached]
  → Top clients ranked by agency count
  → Agencies returned as [{id, name}] objects (not strings)
  → Batch agency query (single SQL, not per-client)

GET /api/v2/aggregates/department-meetings/      [cached]
  → Departments ranked by meeting count, with top attendees

GET /api/v2/aggregates/minister-network/         [cached]
  → D3-compatible network graph (nodes, links, stats)
  → Ministers, donors, directors, PSCs, meeting attendees

GET /api/v2/aggregates/top-donors/
  → Top N donors ranked by total donated

GET /api/v2/aggregates/donor-concentration/
  → Gini coefficient, HHI, concentration category
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

**Purpose**: Headless CMS for editorial content. Wagtail admin is available but the frontend does not render Wagtail pages — it's a separate Astro application.

**Note**: The CMS StreamField blocks (StatsGridBlock, etc.) are legacy from the React/Islands era and are no longer used by the Astro frontend.

---

### 4. frontend/ (Astro + Svelte)

**Purpose**: Decoupled frontend application consuming Django as a headless API.

See [Frontend Architecture (Astro + Svelte)](#frontend-architecture-astro--svelte) for full details.

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
- **Canonical resolution**: `canonical_actor` fields link records to authoritative entities
- **Entity resolution service**: `datafetch/services/entity_resolution.py` with fast mode
- **Name normalization**: `datafetch/utils/normalization.py` for consistent matching

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

## Frontend Architecture (Astro + Svelte)

### Architecture Philosophy

**"Decoupled SSR with Selective Hydration"**

The frontend is a standalone Astro 5 application that consumes Django as a headless API. Django serves JSON only — no HTML templates.

- **Astro pages** handle routing, data fetching (server-side), and static rendering
- **Svelte components** hydrate selectively for interactivity (`client:visible`, `client:load`)
- **D3.js** provides math (force simulation, scales) — SVG is rendered by Svelte, not D3
- **Tailwind CSS** implements the design system (see `docs/FRONTEND_DESIGN.md`)

### Directory Structure

```
frontend/
├── src/
│   ├── pages/                  # Astro file-based routing
│   │   ├── index.astro         # Homepage
│   │   ├── network.astro       # Full-page network visualization
│   │   ├── directory.astro     # Entity directory
│   │   ├── person/[id].astro   # Person profiles
│   │   ├── organisation/[id].astro  # Organization profiles
│   │   └── party/[id].astro    # Political party profiles
│   ├── components/             # Svelte interactive components
│   │   ├── MinisterNetwork.svelte   # D3 force-directed graph
│   │   ├── ActorTimeline.svelte     # Unified chronological timeline
│   │   ├── SiteNav.svelte           # Navigation bar
│   │   └── SiteFooter.svelte        # Footer
│   ├── layouts/
│   │   └── BaseLayout.astro    # Shared page shell
│   ├── lib/
│   │   └── utils.ts            # API_URL, PUBLIC_API_URL, formatCurrency, getActorUrl
│   └── styles/
│       └── global.css          # Tailwind layers, font-face, design tokens
├── astro.config.mjs            # Astro config (Node adapter, Svelte, Tailwind)
├── tailwind.config.mjs         # Design system tokens
└── package.json
```

### Data Flow

```
Browser → Astro Page (SSR)
              │
              ├── Server-side fetch() to Django API (http://api:8000)
              │   (stats, recipients, parties, lobbying, meetings)
              │
              ├── Render HTML with data
              │
              └── Hydrate Svelte components (client:visible)
                    │
                    └── Client-side fetch() to Django API (http://localhost:8000)
                        (MinisterNetwork, ActorTimeline — interactive data)
```

**Two API URLs**:
- `API_URL` (`http://api:8000/api/v2`) — Docker internal, used by Astro SSR fetches
- `PUBLIC_API_URL` (`http://localhost:8000/api/v2`) — Browser-accessible, used by Svelte `client:visible` components

### Key Patterns

**Astro pages fetch data at request time**:
```astro
const [statsRes, recipientsRes] = await Promise.all([
  fetch(`${API_URL}/aggregates/stats/`),
  fetch(`${API_URL}/aggregates/top-recipients/?limit=100`),
]);
```

**Svelte components hydrate for interactivity**:
```astro
<MinisterNetwork client:visible apiUrl={`${PUBLIC_API_URL}/aggregates/minister-network/`} />
```

**Interconnectedness via `getActorUrl()`**:
```typescript
// Every entity name that has an ID links to its profile page
export function getActorUrl(actor: { id: number; actor_type?: string; classification?: string }): string {
  if (actor.classification === 'Political Party') return `/party/${actor.id}`;
  if (actor.actor_type === 'organization') return `/organisation/${actor.id}`;
  return `/person/${actor.id}`;
}
```

### Styling

**Tailwind CSS** with design system tokens from `docs/FRONTEND_DESIGN.md`:
- **Typography**: Zodiak (display/headlines), Satoshi (body/UI)
- **Colors**: Paper `#FAF9F6`, Ink `#1a1a1a`, Accent `#C54B3C`
- **Patterns**: `.section-label`, `.stat-figure`, `.stat-label`, `.annotation`
- **Aesthetic**: Victorian natural history illustration — stippled halos, hatched fills, leader lines

---

## API Architecture

### Design Principles

1. **Read-Only**: All endpoints are GET only (no mutations)
2. **Filter-Driven**: Consistent query parameters across endpoints
3. **Paginated**: Large datasets use limit/offset pagination
4. **Cached**: Redis caching on all aggregate endpoints (1hr TTL via `cache_utils.py`)
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

### 1. Decoupled Astro Frontend (Not Django Templates)

**Decision**: Separate Astro 5 frontend consuming Django as a headless JSON API.

**Rationale**:
- **SEO**: Astro SSR renders full HTML server-side
- **Performance**: Partial hydration — only interactive components load JavaScript
- **Design freedom**: Tailwind + custom design system without Django template constraints
- **D3 integration**: Svelte components render SVG directly, D3 provides math only

**Trade-offs**:
- Two servers in development (Django :8000, Astro :4321)
- Two API URL constants needed (server-side vs client-side)

**Alternatives Considered**:
- ❌ **Django templates + HTMX**: Insufficient for D3 visualizations
- ❌ **Next.js/React**: Heavier runtime than Astro + Svelte
- ❌ **Django templates + Islands (previous architecture)**: Too coupled, difficult to iterate on design

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

### 4. Svelte 5 Runes (Not React Hooks)

**Decision**: Use Svelte 5 with Runes-based reactivity for interactive components.

**Rationale**:
- **Compiled**: No virtual DOM runtime — smaller bundles
- **Runes**: `$state()`, `$derived()` are simpler than React hooks
- **Template syntax**: More readable than JSX for SVG-heavy components
- **Astro integration**: First-class `client:visible` hydration

**Alternatives Considered**:
- ❌ **React 18**: Heavier runtime for this use case
- ❌ **Vue 3**: Similar capability, less Astro ecosystem support

---

### 5. Tailwind CSS (Not CSS Modules)

**Decision**: Use Tailwind CSS utility classes for all styling.

**Rationale**:
- **Design system tokens**: Colors, spacing, typography mapped directly
- **No naming**: No BEM conventions or class name debates
- **Responsive**: Built-in breakpoint prefixes
- **Co-located**: Styles live with markup

**Alternatives Considered**:
- ❌ **CSS Modules**: More verbose, naming overhead (previous architecture used this)
- ❌ **Bootstrap**: Too opinionated, conflicts with natural history aesthetic

---

## Future Considerations

### Performance Optimization
- ✅ **Redis caching**: All aggregate endpoints cached (1hr TTL) — `cache_utils.py`
- ✅ **N+1 fixes**: Batch queries for lobbying agencies, `select_related('polymorphic_ctype')` for recipients
- ✅ **SQL optimization**: Party filter pushed into SQL, canonical resolution via `Coalesce()`
- **Materialized views**: For expensive aggregate queries (future — concentration calc still materializes ~21k rows)
- **Connection pooling**: pgbouncer for PostgreSQL (future)

### Feature Additions
- ✅ **Network visualization**: D3.js minister network (90 ministers, 298 donors, 431 donation links)
- ✅ **Enhanced profiles**: Unified timeline with donations, meetings, roles, consultancies
- ✅ **Directory page**: `/directory` with actor listing
- ✅ **Party profiles**: Dedicated `/party/[id]` pages with funding breakdown
- **Data export**: CSV download for tables (future)

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
- `docs/UX_IMPLEMENTATION_PLAN.md` - UX roadmap and implementation tracking
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

**Last Major Update**: April 16, 2026 (v5.0 - Astro Frontend + API Caching)
