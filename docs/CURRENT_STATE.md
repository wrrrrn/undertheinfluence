# UnderTheInfluence: Current State Summary

**Last Updated**: January 27, 2026
**Branch**: `feature/ux`
**Status**: Working prototype with Astro 5 + Svelte 5 frontend

---

## Executive Summary

UnderTheInfluence is a **working Django 6.0 web application** that tracks political influence in UK politics through donations, lobbying, and ministerial meetings data. The project has successfully completed:

- **Backend modernization** (Django 1.8 → 6.0, Python 3.7 → 3.12)
- **Full Dockerization** for development and deployment
- **Modern frontend architecture** using Astro 5 + Svelte 5 + D3.js
- **API v2** with aggregate endpoints, filtering, and network graph data
- **Interactive visualizations** including minister network graph with donation and meeting data

**What Works Right Now**:
- ✅ Docker Compose development environment
- ✅ Django 6.0.1 + Wagtail 7.2.x + PostgreSQL 15
- ✅ Astro 5 + Svelte 5 frontend with Tailwind CSS
- ✅ D3.js minister network visualization (donations + meetings)
- ✅ API v2 aggregate endpoints with filtering
- ✅ Data import from ParlParse, Ministers, MPs' Register, and Ministerial Meetings
- ✅ CORS support for Astro frontend

**What's Next**: Add more visualizations, politician directory page, enhance entity profiles.

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
| **Astro** | 5.x | ✅ SSR + partial hydration |
| **Svelte** | 5.x | ✅ Interactive components |
| **D3.js** | 7.x | ✅ Data visualization |
| **Tailwind CSS** | 3.x | ✅ Utility-first styling |
| **TypeScript** | 5.x | ✅ Type safety |

### Infrastructure
- **Docker** + **Docker Compose** for development
- **django-vite** for asset integration
- **python-decouple** for environment configuration
- Custom Docker skills for common operations

---

## Architecture Summary

### Astro + Svelte Frontend

The frontend uses **Astro 5** for server-side rendering with **Svelte 5** components for interactivity:

```
┌─────────────────────────────────────────────────────────────┐
│                    Astro Page (.astro)                       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Server-Rendered HTML (Static Content)                │  │
│  │ - Hero section, typography, stats                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Svelte Component (client:visible)                    │  │
│  │ - MinisterNetwork visualization (D3.js)              │  │
│  │ - Interactive hover/click behavior                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Server-Rendered HTML (Methodology, Footer)           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Principles**:
- 📄 **Server-rendered by default** - SEO-friendly, fast initial load
- 🏝️ **Partial hydration** - Svelte components hydrate via `client:visible`
- 📊 **D3.js visualizations** - Interactive network graphs
- ♿ **Progressive enhancement** - Works without JavaScript
- 🎯 **Minimal bundle** - Svelte compiles away the framework

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
- ✅ Ministerial meetings models (MinisterialMeeting, MeetingAttendee)
- ✅ Supporting models (Area, Identifier, OtherName, ContactDetail, Link, Source)
- ✅ Temporal behaviors (Dateframeable, Timestampable)
- ✅ Entity resolution fields (canonical_person, canonical_organization)

**Data Import** (`datafetch/management/commands/`):
- ✅ **Working**: `import_parlparse` (MPs/Lords since 2010)
- ✅ **Working**: `import_ministers` (ministerial appointments)
- ✅ **Working**: `import_mpsinterests` (MPs' Register of Interests)
- ✅ **Working**: `import_ministerial_meetings` (GOV.UK transparency data)
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
- `GET /api/v2/aggregates/minister-network/` - D3.js network graph data
  - Ministers, donors, and meeting attendees as nodes
  - Donation and meeting connections as links
  - Filters: limit, min_value, min_meetings, current_only
  - Returns nodes, links, and stats for force simulation

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

**Svelte Components** (`frontend/src/components/`):
- ✅ **MinisterNetwork** - D3.js force-directed network visualization
  - Shows ministers, donors, and meeting attendees as nodes
  - Donation connections (solid lines) and meeting connections (dashed lines)
  - Interactive: hover to preview, click to pin detail card
  - Configurable: limit, minValue, minMeetings, currentOnly filters
  - Boundary constraints keep nodes within SVG
  - Natural history color palette (terracotta, forest green, warm brown)

**Astro Pages** (`frontend/src/pages/`):
- ✅ **index.astro** - Editorial homepage
  - Masthead with investigation label
  - Hero section with headline and deck
  - Stats strip (API-driven)
  - Full-width minister network visualization
  - Pull quote / insight section
  - Methodology section
  - Footer

**Layouts** (`frontend/src/layouts/`):
- ✅ **BaseLayout.astro** - Base HTML layout with Tailwind styles

**State Management**:
- ✅ Svelte 5 Runes (`$state`, `$props`, `$derived`)
- ✅ Component-local state (no global store needed)
- ✅ D3.js force simulation state

### Frontend - Styling

**Design System** (Natural History / Editorial):
- ✅ Tailwind CSS for utility-first styling
- ✅ Custom theme with organic color palette
- ✅ Typography: Zodiak (headlines) + Satoshi (body)
- ✅ Tabular figures for numeric data alignment
- ✅ Responsive grid layouts

**Color Palette**:
- Ministers: `#C54B3C` (Terracotta red)
- Donors: `#4A6741` (Forest green)
- Organizations: `#6B5B4F` (Warm brown)
- Meetings: `#7B9E87` (Sage green)
- Paper: `#FAF8F5` (Warm white)
- Ink: `#2C2C2C` (Dark gray)

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
# Start backend services (Django + PostgreSQL + Redis)
docker compose up -d

# Django API runs on http://localhost:8000

# Start frontend dev server (from frontend/ directory)
cd frontend && npm run dev

# Astro dev server runs on http://localhost:4321
# Hot Module Replacement (HMR) enabled
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
  - Ego network visualization (D3.js) - building on MinisterNetwork
  - Activity timeline (chronological event feed)
- ⏳ **Network Visualizations**
  - ✅ Minister network (force-directed, donations + meetings)
  - ❌ Ego networks (actor-specific view)
  - ❌ Sankey diagrams (influence paths)
  - ❌ Cluster detection visualization
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
  - Filter by relationship type (building on minister-network pattern)
- ❌ `GET /api/v2/actors/{id}/paths-to/{target}/` - Influence paths
  - Find all routes from donor to politician
  - Used for Sankey diagrams
- ❌ `GET /api/v2/network/clusters/` - Community detection
  - Identify tightly-connected groups
  - Cluster analysis metrics

**Note**: `GET /api/v2/aggregates/minister-network/` is now implemented as the foundation for network visualizations.

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
├── frontend/               # Astro + Svelte frontend
│   ├── src/
│   │   ├── components/      # Svelte components
│   │   │   └── MinisterNetwork.svelte  # D3.js network visualization
│   │   ├── layouts/         # Astro layouts
│   │   │   └── BaseLayout.astro
│   │   ├── pages/           # Astro pages (file-based routing)
│   │   │   └── index.astro  # Homepage
│   │   └── styles/          # Global CSS
│   │       └── global.css
│   ├── public/              # Static assets
│   ├── astro.config.mjs     # Astro configuration
│   ├── tailwind.config.mjs  # Tailwind CSS theme
│   ├── package.json         # NPM dependencies
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

### 1. Astro + Svelte (Not React Islands)
**Decision**: Use Astro 5 for SSR with Svelte 5 for interactive components.

**Rationale**:
- Built-in partial hydration (`client:visible`, `client:load`)
- Svelte compiles away - smaller bundle size
- Better DX for content-heavy pages
- Svelte 5 Runes more intuitive than React hooks
- No need for custom island loader

**Trade-offs**:
- Smaller ecosystem than React
- Learning curve for Svelte syntax

### 2. Svelte 5 Runes (Not Zustand/Redux)
**Decision**: Use Svelte 5 Runes (`$state`, `$props`, `$derived`) for state management.

**Rationale**:
- Built-in reactive primitives
- No external state library needed
- Compile-time optimizations
- Clean, readable syntax

**Trade-offs**:
- Component-local state (no global store pattern by default)
- Svelte 5 is newer, fewer examples

### 3. Tailwind CSS (Not Bootstrap/CSS Modules)
**Decision**: Use Tailwind CSS for utility-first styling.

**Rationale**:
- Rapid prototyping
- Custom theme support
- No CSS naming decisions
- Astro integration is excellent

**Trade-offs**:
- Verbose class strings
- Less semantic HTML

### 4. D3.js Force Simulation (Not React Flow/Cytoscape)
**Decision**: Use D3.js force simulation for network visualization.

**Rationale**:
- Fine-grained control over physics
- Works well with Svelte reactive updates
- Industry standard for data viz
- No additional dependencies

**Trade-offs**:
- More manual setup than high-level libs
- Requires understanding force simulation parameters

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

**Last Major Update**: January 27, 2026 (Astro + Svelte frontend, minister network visualization)
