# UnderTheInfluence: Current State Summary

**Last Updated**: January 19, 2026
**Branch**: `feature/new-ui`
**Status**: Working prototype with modern frontend architecture

---

## Executive Summary

UnderTheInfluence is a **working Django 6.0 web application** that tracks political influence in UK politics through donations and lobbying data. The project has successfully completed:

- **Backend modernization** (Django 1.8 → 6.0, Python 3.7 → 3.12)
- **Full Dockerization** for development and deployment
- **Modern frontend architecture** using Islands Architecture with React/Vite
- **API v2** with aggregate endpoints and filtering
- **Basic UI** with interactive homepage components

**What Works Right Now**:
- ✅ Docker Compose development environment
- ✅ Django 6.0.1 + Wagtail 7.2.x + PostgreSQL 15
- ✅ Islands Architecture with Vite 5 + React 18 + TypeScript
- ✅ Homepage with StatsGrid, PartyBreakdown, TopDonorsLeaderboard islands
- ✅ API v2 aggregate endpoints with filtering
- ✅ Data import from ParlParse (MPs/Lords) and Ministers
- ✅ Zustand-based URL state management

**What's Next**: Expand frontend components, add politician directory page, enhance entity profiles.

---

## Technology Stack (January 2026)

### Backend
| Component | Version | Status |
|-----------|---------|--------|
| **Django** | 6.0.1 | ✅ Stable |
| **Wagtail CMS** | 7.2.x | ✅ Stable |
| **Python** | 3.12 | ✅ Stable |
| **PostgreSQL** | 15 | ✅ Stable (Docker) |
| **Redis** | 7 | ✅ Stable (Docker) |
| **Django REST Framework** | 3.15.x | ✅ Stable |
| **django-polymorphic** | 4.2.x | ✅ Stable |

### Frontend
| Component | Version | Status |
|-----------|---------|--------|
| **Vite** | 5.x | ✅ Build system |
| **React** | 18.x | ✅ Islands only |
| **TypeScript** | 5.x | ✅ Type safety |
| **Bootstrap** | 5.x | ✅ Layout/grid |
| **CSS Modules** | (Vite) | ✅ Scoped styles |
| **Zustand** | 4.5.x | ✅ State management |
| **TanStack Query** | 5.x | ✅ Data fetching |

### Infrastructure
- **Docker** + **Docker Compose** for development
- **django-vite** for asset integration
- **python-decouple** for environment configuration
- Custom Docker skills for common operations

---

## Architecture Summary

### Islands Architecture

The frontend uses **Islands Architecture** - server-rendered Django templates with selective React hydration:

```
┌─────────────────────────────────────────┐
│         Django Template (HTML)          │
│                                         │
│  ┌──────────────┐   ┌──────────────┐  │
│  │ Static HTML  │   │ Static HTML  │  │
│  └──────────────┘   └──────────────┘  │
│                                         │
│  ┌────────────────────────────────┐    │
│  │ React Island (StatsGrid)       │    │
│  │ <div data-island="StatsGrid">  │    │
│  │   [Interactive Component]      │    │
│  │ </div>                         │    │
│  └────────────────────────────────┘    │
│                                         │
│  ┌──────────────┐   ┌──────────────┐  │
│  │ Static HTML  │   │ Static HTML  │  │
│  └──────────────┘   └──────────────┘  │
└─────────────────────────────────────────┘
```

**Key Principles**:
- 📄 **Server-rendered by default** - SEO-friendly, fast initial load
- 🏝️ **Islands hydrate selectively** - React only where interactivity is needed
- 🔗 **URL-driven state** - Filter state lives in URL parameters (shareable links)
- ♿ **Progressive enhancement** - Works without JavaScript
- 🎯 **Minimal bundle** - ~40-60KB gzipped (vs 200KB+ for SPAs)

### Data Model (Popolo-Based)

```
Actor (Polymorphic Base)
├── Person (MPs, Lords, donors)
└── Organization (Parties, companies, trade unions)

Relationships:
├── Membership (Person ↔ Organization + Post)
├── Donation (Actor → Actor with £ value)
└── Consultancy (Organization client ↔ Organization agency)
```

**Key Features**:
- Polymorphic models via django-polymorphic
- Partial date support (YYYY, YYYY-MM, YYYY-MM-DD)
- Generic relations for metadata (identifiers, links, sources)
- Canonical fields for entity resolution

---

## What's Built (Working Features)

### Backend - Data Layer

**Models** (`datafetch/models/`):
- ✅ Core Popolo models (Actor, Person, Organization, Post, Membership)
- ✅ Relationship models (Donation, Consultancy)
- ✅ Supporting models (Area, Identifier, OtherName, ContactDetail, Link, Source)
- ✅ Temporal behaviors (Dateframeable, Timestampable)
- ✅ Entity resolution fields (canonical_person, canonical_organization)

**Data Import** (`datafetch/management/commands/`):
- ✅ **Working**: `import_parlparse` (MPs/Lords since 2010)
- ✅ **Working**: `import_ministers` (ministerial appointments)
- ✅ **Working**: `import_mpsinterests` (MPs' Register of Interests)
- ⚠️ **Partial**: `import_ec` (Electoral Commission - API changes needed)
- ⚠️ **Partial**: `import_appc` (APPC lobbying - site changes)

**Database** (PostgreSQL via Docker):
- ~26,000 actors (persons + organizations)
- ~150,000 memberships
- ~91,000+ donations (Electoral Commission data)
- Full import from 1996-2026 working

### Backend - API Layer

**API v2 Endpoints** (`api/v2/`):

**Aggregate Endpoints** (for homepage/dashboards):
- `GET /api/v2/aggregates/stats/` - Homepage key metrics
  - Total donations, total value, concentration metrics
  - Supports date_range, value_min, donor_type filters
- `GET /api/v2/aggregates/party-donations/` - Party breakdown
  - Total received, donor count, avg donation per party
  - Supports same filters as stats
- `GET /api/v2/aggregates/top-donors/` - Top N donors leaderboard
  - Paginated (100/page), ranked by total donated
  - Supports filtering + pagination
- `GET /api/v2/aggregates/donor-concentration/` - Whale donor analysis
  - Gini coefficient, HHI, concentration category
  - Pareto distribution metrics

**Actor Endpoints** (for profiles):
- `GET /api/v2/actors/{id}/` - Actor detail
- `GET /api/v2/actors/{id}/donations-from/` - Donations received
- `GET /api/v2/actors/{id}/donations-to/` - Donations made
- `GET /api/v2/actors/{id}/consultancies/` - Lobbying relationships

**Features**:
- django-filter integration for consistent filtering
- Pagination (10-100 items per page)
- Canonical field resolution (merged entities)
- Partial date support in filters
- Documented query parameters

### Frontend - Components

**Built Islands** (`frontend/islands/`):
- ✅ **StatsGrid** - 4 metric cards with live API data
  - Total donations, total value, concentration, dual influence
  - Filters: date range, min value, donor type
  - Timestamp provenance
- ✅ **PartyBreakdown** - Party donation breakdown grid
  - Party cards with official colors
  - Total received, donor count, avg donation
  - Responsive grid layout
- ✅ **TopDonorsLeaderboard** - Paginated donor ranking
  - Rank calculation accounts for pagination
  - Filters sync with other islands
  - Click-through to donor profiles
- ✅ **FilterPanel** - Interactive filter controls
  - Date range picker, value selector, donor type chips
  - Updates URL state (syncs all islands)
- ⏳ **ConcentrationChart** - D3.js visualization (scaffolded, not implemented)

**Built Components** (`frontend/components/`):
- ✅ **StatCard** - Metric display primitive
  - Value, label, optional icon, variant colors
  - Timestamp for data provenance
  - Click-through href support
- ✅ **PartyCard** - Political party card
  - Party name with official color accent
  - Donation statistics, responsive layout
- ✅ **ActorCard** - Person/organization card (basic version)
  - Name, classification, image
  - Click-through to profile page

**State Management**:
- ✅ Zustand store (`frontend/store/filterStore.ts`)
- ✅ URL parameter synchronization
- ✅ Filter state: dateFrom, dateTo, minValue, donorType, page
- ✅ Browser back/forward navigation works
- ✅ Shareable URLs preserve filter state

**Island Loader** (`frontend/islands.tsx`):
- ✅ Detects `[data-island]` markers in HTML
- ✅ Lazy-loads island components
- ✅ Hydrates with props from data attributes
- ✅ Error handling for failed loads

### Frontend - Styling

**Design System**:
- ✅ Bootstrap 5.x for layout/grid
- ✅ CSS Modules for scoped component styles
- ✅ SCSS preprocessing with Vite
- ✅ Typography: Playfair Display (headings) + Inter (body)
- ✅ Party colors with WCAG AA accessible variants
- ✅ Responsive breakpoints (mobile-first)

**Editorial Design** (from `docs/FRONTEND_DESIGN.md`):
- ✅ 20px border radius for cards (modern, premium feel)
- ✅ Layered shadow system for depth
- ✅ Party color accent bars/badges
- ✅ Tabular numeric formatting for currency

### Wagtail CMS Integration

**Custom Blocks** (`cms/blocks.py`):
- ✅ **StatsGridBlock** - Embeds homepage metrics
- ✅ **PartyBreakdownBlock** - Embeds party breakdown
- ✅ **TopDonorsLeaderboardBlock** - Embeds leaderboard
- ✅ **FilterPanelBlock** - Embeds filter controls
- ✅ **DataVisualizationBlock** - Container for all visualization blocks

**Templates** (`cms/templates/cms/blocks/`):
- ✅ Server-rendered fallbacks for SEO
- ✅ Data attributes for island hydration
- ✅ Progressive enhancement support

**HomePage Model** (`cms/models.py`):
- ✅ StreamField with visualization blocks
- ✅ Editors can add/remove/reorder islands
- ✅ No code required for content changes

### Development Workflow

**Docker Setup**:
```bash
# Start all services (Django + Vite + PostgreSQL + Redis)
docker compose up -d

# Django runs on http://localhost:8000
# Vite dev server runs on http://localhost:5173
# Hot Module Replacement (HMR) works across containers
```

**Custom Skills** (`.claude/skills/`):
- ✅ `/docker-logs` - View container logs
- ✅ `/docker-status` - Check service health
- ✅ `/docker-restart` - Restart services
- ✅ `/docker-migrate` - Run database migrations
- ✅ `/docker-exec` - Execute Django commands
- ✅ `/docker-shell` - Access Django/bash shell
- ✅ `/docker-import` - Data import shortcuts

**Build Commands**:
```bash
# Frontend development (HMR)
npm run dev

# Frontend production build
npm run build

# Django collectstatic
python manage.py collectstatic --noinput
```

---

## What's Not Built Yet (Planned Work)

### Frontend Components (High Priority)
- ❌ **Politician Directory Page** (`/politicians/`)
  - Grouped by government/opposition → party → individuals
  - Compact politician cards with party accents
  - Filtering by party, role, status
- ❌ **Enhanced Actor Profiles**
  - Tabbed interface (Overview, Donations, Network, Timeline)
  - Network graph visualization (D3.js)
  - Activity timeline (chronological event feed)
- ❌ **Network Visualizations**
  - Force-directed graph (ego networks)
  - Sankey diagrams (influence paths)
  - Cluster detection visualization
- ❌ **Data Tables** (replacing current basic views)
  - Sortable, filterable donation tables
  - Infinite scroll or pagination
  - Export to CSV functionality

### API Endpoints (Medium Priority)
- ❌ `GET /api/v2/politicians/` - Politicians directory endpoint
  - Filter by party, role, government status
  - Annotated with current_party, is_minister, is_mp
- ❌ `GET /api/v2/actors/{id}/network/` - Ego network data
  - Multi-hop relationship traversal
  - Filter by relationship type
- ❌ `GET /api/v2/actors/{id}/paths-to/{target}/` - Influence paths
  - Find all routes from donor to politician
  - Used for Sankey diagrams
- ❌ `GET /api/v2/network/clusters/` - Community detection
  - Identify tightly-connected groups
  - Cluster analysis metrics

### Data Quality (Medium Priority)
- ⚠️ **Automated cleanup** (167,967 issues identified)
  - 28,516 duplicate donations (fixable automatically)
  - 637 orphaned donations
  - 76 invalid donation dates
  - 116,542 memberships missing start_date
- ⚠️ **Import command improvements**
  - Add deduplication to `import_ec`
  - Add date validation to `import_ec`
  - Fix missing membership dates in `import_appc`

### Testing (Low Priority - Future)
- ❌ Frontend component tests (Jest + React Testing Library)
- ❌ Backend API tests (pytest-django)
- ❌ Integration tests
- ❌ Accessibility tests (WCAG 2.1 AA)

---

## File Structure (Relevant Files Only)

```
undertheinfluence/
├── api/
│   └── v2/                  # API v2 module
│       ├── views.py         # Aggregate + actor endpoints
│       ├── serializers.py   # DRF serializers
│       ├── filters.py       # django-filter configuration
│       ├── pagination.py    # Custom pagination classes
│       └── urls.py          # API v2 routing
├── cms/
│   ├── blocks.py            # Custom Wagtail StreamField blocks
│   ├── models.py            # Wagtail page models (HomePage)
│   └── templates/cms/blocks/ # Block templates with island markers
├── datafetch/              # Core app
│   ├── models/
│   │   ├── models.py        # Popolo core models (Actor, Person, Org)
│   │   ├── influence_mapping.py # Donation, Consultancy models
│   │   └── popolo/          # Abstract behaviors, querysets
│   ├── management/commands/ # Data import commands
│   │   ├── import_parlparse.py
│   │   ├── import_ministers.py
│   │   └── import_mpsinterests.py
│   ├── views.py             # Django views (ActorView, SearchView)
│   └── templates/           # Django templates
├── frontend/               # Islands Architecture frontend
│   ├── components/          # Reusable React components
│   │   ├── ActorCard.tsx
│   │   ├── StatCard.tsx
│   │   └── PartyCard.tsx
│   ├── islands/             # Top-level interactive islands
│   │   ├── StatsGrid.tsx
│   │   ├── PartyBreakdown.tsx
│   │   ├── TopDonorsLeaderboard.tsx
│   │   └── FilterPanel.tsx
│   ├── hooks/               # Custom React hooks
│   │   ├── useTopDonors.ts
│   │   └── useHomepageStats.ts
│   ├── store/               # Zustand state management
│   │   └── filterStore.ts
│   ├── styles/              # Global SCSS
│   ├── islands.tsx          # Island loader/registry
│   ├── main.tsx             # Vite entry point
│   ├── package.json         # NPM dependencies
│   ├── vite.config.ts       # Vite configuration
│   └── tsconfig.json        # TypeScript configuration
├── undertheinfluence/      # Django project
│   ├── settings.py          # Django settings (environment vars)
│   ├── urls.py              # URL routing
│   └── templates/base.html  # Base template with Vite assets
├── docs/                   # Documentation
│   ├── CURRENT_STATE.md     # This file
│   ├── systems-architecture.md
│   ├── data-models.md
│   ├── FRONTEND_DESIGN.md
│   └── FRONTEND_IMPLEMENTATION.md
├── .env                    # Environment configuration
├── docker-compose.yml      # Docker orchestration
├── Dockerfile              # Django container
├── requirements.txt        # Python dependencies
└── CLAUDE.md               # Project instructions for Claude Code
```

---

## Configuration (.env)

**Key Environment Variables**:
```bash
DEBUG=True                          # Development mode
DATABASE_SYSTEM=postgresql          # Use PostgreSQL (vs SQLite)
UTI_DB_NAME=undertheinfluence       # Database name
UTI_DB_USER=uti                     # Database user
UTI_DB_PASS=***                     # Database password
UTI_DB_HOST=db                      # Docker service name
UTI_DB_PORT=5432                    # PostgreSQL port
SECRET_KEY=***                      # Django secret key
ALLOWED_HOSTS=localhost,127.0.0.1   # Permitted hostnames
```

Docker Compose automatically configures these for local development.

---

## Key Decisions Made

### 1. Islands Architecture (Not SPA)
**Decision**: Use server-rendered Django templates with selective React hydration.

**Rationale**:
- SEO-friendly (server-rendered content)
- Fast initial load (minimal JavaScript)
- Progressive enhancement (works without JS)
- Natural Django integration
- Wagtail CMS compatibility

**Trade-offs**:
- Not suitable for real-time collaboration features
- Client-side routing would require additional complexity

### 2. URL-Driven State (Not Client-Side Only)
**Decision**: Store filter state in URL parameters, synchronized via Zustand.

**Rationale**:
- Shareable links (deep linking)
- Browser back/forward works
- No client-side routing needed
- Multiple islands automatically synchronized

**Trade-offs**:
- URL can get long with many filters
- Sensitive filters would need different approach

### 3. Zustand (Not Redux/MobX)
**Decision**: Use Zustand for lightweight state management.

**Rationale**:
- Minimal boilerplate (1KB gzipped)
- TypeScript support
- No provider wrapper needed
- Prevents custom event "soup"

**Trade-offs**:
- Less ecosystem than Redux
- No time-travel debugging by default

### 4. CSS Modules (Not Tailwind/Styled-Components)
**Decision**: Use CSS Modules with SCSS for component styling.

**Rationale**:
- Scoped styles prevent conflicts
- Familiar CSS syntax
- Works with Bootstrap 5 global styles
- SCSS preprocessing for variables

**Trade-offs**:
- More verbose than Tailwind
- Requires naming conventions

### 5. Bootstrap 5 (Not Custom Framework)
**Decision**: Use Bootstrap 5 for layout/grid system.

**Rationale**:
- Mature, well-documented
- Responsive grid system
- Accessibility built-in
- Familiar to developers

**Trade-offs**:
- Larger bundle than custom solution
- "Bootstrap look" unless customized

### 6. Partial Dates as Strings (Not DateField)
**Decision**: Store dates as `CharField` with YYYY/YYYY-MM/YYYY-MM-DD format.

**Rationale**:
- Matches Popolo specification
- Supports incomplete dates (common in political data)
- Lexicographic ordering works

**Trade-offs**:
- Cannot use database date functions
- Requires custom validation

### 7. Polymorphic Models (Not Separate Tables)
**Decision**: Use django-polymorphic for Actor base class.

**Rationale**:
- Single table for querying all actors
- Type-specific fields in subclasses
- Foreign keys can reference any actor type

**Trade-offs**:
- Additional joins for type resolution
- More complex queries

---

## Known Issues

### Data Quality
- **167,967 total data quality issues** identified (see `docs/DATA_QUALITY_REPORT.md`)
  - 28,516 duplicate donations (fixable automatically)
  - 637 orphaned donations
  - 76 invalid donation dates
  - 116,542 memberships missing start_date (77.6%)
- **Automated cleanup ready**: `clean_data --fix=all` command exists
- **Manual review needed**: Invalid dates, orphaned donations with values

### Import Commands
- **Electoral Commission** (`import_ec`): CSV API endpoint changed, needs update
- **APPC** (`import_appc`): APPC.org.uk defunct (merged with PRCA), needs rewrite

### Performance
- **Top donors endpoint**: Requires optimization for >10,000 donors
  - Current: ~0.5s for 100 results (acceptable)
  - Needs materialized views for larger datasets
- **Network queries**: Not yet implemented (recursive CTEs planned)

### Testing
- **Zero test coverage**: No automated tests exist
  - Frontend: No component tests
  - Backend: No API tests
  - Integration: No end-to-end tests

### Documentation
- **16 documentation files**: Some outdated, some duplicated
  - Needs consolidation and cleanup
  - Version history unclear

---

## Next Steps (Recommended Priority)

### Immediate (This Week)
1. **Politicians Directory Page**
   - `/api/v2/politicians/` endpoint
   - Basic server-rendered directory
   - Group by government/opposition → party
2. **Data Quality Cleanup**
   - Run automated cleanup (`clean_data --fix=all`)
   - Manual review of invalid dates
   - Document cleanup results

### Short-Term (This Month)
3. **Network Visualization**
   - PostgreSQL recursive CTEs for network queries
   - `/api/v2/actors/{id}/network/` endpoint
   - D3.js force-directed graph component
4. **Enhanced Actor Profiles**
   - Tabbed interface (Overview, Donations, Network)
   - Timeline component (chronological activity feed)
   - Related entities sidebar

### Medium-Term (Next 2-3 Months)
5. **Testing Infrastructure**
   - Frontend component tests (Vitest + React Testing Library)
   - Backend API tests (pytest-django)
   - CI/CD pipeline (GitHub Actions)
6. **Performance Optimization**
   - Materialized views for expensive aggregations
   - Redis caching for API endpoints
   - Database indexes based on query analysis
7. **Documentation Consolidation**
   - Merge/archive outdated docs
   - Single source of truth for architecture
   - API documentation (OpenAPI/Swagger)

---

## Success Metrics (Current Baseline)

**Data Coverage**:
- ✅ 26,000+ actors (persons + organizations)
- ✅ 150,000+ memberships
- ✅ 91,000+ donations
- ✅ 30 years of data (1996-2026)

**Performance (Current)**:
- ✅ API v2 aggregates: <0.5s response time (p95)
- ✅ Homepage load: <2s with HMR
- ✅ Island hydration: <200ms per island

**User Experience**:
- ✅ Mobile-responsive layout
- ✅ Progressive enhancement (works without JS)
- ✅ Shareable URLs with filter state
- ⚠️ Accessibility: Not tested (WCAG 2.1 AA compliance unknown)

**Developer Experience**:
- ✅ `docker compose up` → working dev environment
- ✅ Hot Module Replacement (HMR) for frontend
- ✅ Custom Docker skills for common operations
- ✅ TypeScript for type safety

---

## Deployment Status

**Current**: Development only (Docker Compose)

**Production Deployment**: Not yet configured

**Requirements for Production**:
- Environment variable configuration (`.env` for production)
- Static asset collection (`collectstatic`)
- Database migrations
- Gunicorn WSGI server (instead of runserver)
- Nginx reverse proxy (optional but recommended)
- SSL certificates
- Monitoring/logging setup

**Deployment Repository**: https://github.com/spudmind/uti-deploy (needs updating for Django 6.0)

---

## Contacts & Resources

- **GitHub**: https://github.com/spudmind/undertheinfluence
- **Docker Hub**: (not configured)
- **Deployment Repo**: https://github.com/spudmind/uti-deploy

**Data Sources**:
- ParlParse (MySociety): https://github.com/mysociety/parlparse
- Electoral Commission: https://search.electoralcommission.org.uk/
- TheyWorkForYou API: https://www.theyworkforyou.com/api/

**Documentation**:
- Popolo Specification: http://www.popoloproject.com/
- Django 6.0 Docs: https://docs.djangoproject.com/en/6.0/
- Vite Guide: https://vitejs.dev/guide/
- Islands Architecture: https://jasonformat.com/islands-architecture/

---

**Document Maintenance**: This file should be updated whenever:
- New features are completed and working
- Technology stack changes
- Architecture decisions are made
- Deployment status changes

**Last Major Update**: January 19, 2026 (initial creation)
