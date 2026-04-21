# UnderTheInfluence: Current State Summary

**Last Updated**: April 16, 2026
**Branch**: `feature/ux`
**Status**: Working application with full Astro 5 + Svelte 5 frontend, 10 pages, actor-type-adaptive profiles, editorial design system, and 5-phase UX workflow

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
- ✅ Astro 5 + Svelte 5 frontend with Tailwind CSS and editorial design system
- ✅ **10 Astro pages**: homepage, directory, network, meetings, lobbying, parties, analysis, actor profiles, privacy, terms, data
- ✅ **Actor profile timeline** (ActorTimeline.svelte) — unified chronological view of donations, meetings, roles, consultancies
- ✅ **Interconnected entity links** — meeting attendees, donors, ministers, lobbying agencies all link to their actor profiles
- ✅ **D3.js minister network visualization** (force-directed, donations + meetings, physics controls)
- ✅ API v2 aggregate endpoints with filtering and Redis caching (1hr TTL on all 6 homepage endpoints)
- ✅ Data import from ParlParse, Ministers, MPs' Register, and Ministerial Meetings
- ✅ **Ministerial Meetings Import** - 41,362 meetings from 23 departments
- ✅ **Companies House Enrichment** - 51,157 organizations matched (24.5% auto-approved)
- ✅ **Data Quality Cleanup** - 127,600+ issues resolved (99.98% duplicate reduction)
- ✅ **Entity Resolution Service** - Fast canonical actor linking (~10% match rate)
- ✅ **UX workflow skills** — `/ux-audit`, `/ux-design`, `/ux-mockup`, `/ux-refine`, `/ux-constraints`
- ✅ CORS support for Astro frontend

**What's Next**: Trade union profile design, data import fixes (concatenated names), department aggregate pages, timeline pagination, search functionality. See `docs/UX_IMPLEMENTATION_PLAN.md` for full roadmap.

---

## Technology Stack (April 2026)

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
├── Consultancy (Organization client ↔ Organization agency)
└── MinisterialMeeting (Minister ↔ External Actor)
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
- ✅ **Working**: `enrich_companies_house` (directors, PSCs, company data)
- ⚠️ **Partial**: `import_ec` (Electoral Commission - API changes needed)
- ⚠️ **Partial**: `import_appc` (APPC lobbying - site changes)

**Database** (PostgreSQL via Docker):
- **155,065 actors** (90,728 persons + 64,337 organizations)
- **136,590 memberships** (including directors, PSCs, parliamentary roles)
- **91,513 donations** (Electoral Commission + MPs Register of Interests)
- **62,798 consultancies** (lobbying relationships)
- **41,362 ministerial meetings** (23 departments, 119,793 attendees)
- **Companies House**: 51,157 matches (12,532 auto-approved, 11,198 pending review)
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
- `GET /api/v2/actors/{id}/` - Actor detail (with aggregate stats: unique donors/orgs/ministers counts)
- `GET /api/v2/actors/{id}/donations-received/` - Donations received
- `GET /api/v2/actors/{id}/donations-made/` - Donations made
- `GET /api/v2/actors/{id}/memberships/` - Memberships (with `on_behalf_of` for party)
- `GET /api/v2/actors/{id}/meetings/` - Ministerial meetings (with attendees)
- `GET /api/v2/actors/{id}/consultancies/` - Lobbying relationships
- `GET /api/v2/actors/{id}/agency-clients/` - Top clients ranked by political activity (agency pages)
- `GET /api/v2/actors/{id}/cross-connections/` - Bidirectional cross-connections (org→persons with political ties, person→orgs with political activity). Data quality filter on names. Party field on org→person.
- `GET /api/v2/actors/{id}/funding-summary/` - Pre-aggregated funding data for party pages (top donors, yearly totals with per-year top 5, category breakdown, public funds, union funding). Redis-cached 1hr.

**Features**:
- django-filter integration for consistent filtering
- Pagination (10-100 items per page)
- Canonical field resolution (merged entities)
- Partial date support in filters
- Documented query parameters

### Frontend - Components

**Svelte Components** (`frontend/src/components/`):
- ✅ **MinisterNetwork** - D3.js force-directed network visualization
  - Ministers, donors, directors, PSCs as nodes with type-specific colors
  - Bridge node detection (entities connecting 2+ ministers) with gold ring highlight
  - Interactive: hover for 2-hop highlighting, click to pin detail panel
  - Configurable physics panel (repulsion, link distance, gravity, collision)
- ✅ **ActorTimeline** - Unified chronological timeline for actor profiles
  - Merges roles, donations, meetings, consultancies into single date-sorted stream
  - Year grouping with collapsible summaries (top donors, top meeting orgs)
  - Interconnected links: attendees, donors, ministers, agencies all clickable
  - Self-filtering: org's own name removed from attendee lists on org pages
  - Minister names shown on org meeting rows
  - **Progressive lazy loading** for party pages: renders all years from funding summary data, fetches real donations per year on demand when expanded
- ✅ **ActorProfile** - Tab-based actor view (legacy, being replaced by timeline)
- ✅ **SiteNav** / **SiteFooter** - Navigation and footer components

**Astro Pages** (`frontend/src/pages/`):
- ✅ **index.astro** - Editorial homepage (stats, top recipients, party funding, ministerial access, lobbying)
- ✅ **person/[id].astro** - Actor profile (person or org) with header, stats strip, and timeline. Party pages have dedicated funding sections: Top Private Donors, Cross-Funding of MPs, Trade Union Funding, Public Funding, Funding by Type, Funding by Year (expandable bars with govt/election annotations)
- ✅ **directory.astro** - Politician directory with search and pagination
- ✅ **network.astro** - Full-page minister network D3 visualization
- ✅ **meetings.astro** - Departmental meetings explorer
- ✅ **lobbying.astro** - Lobbying clients and dual influence data
- ✅ **parties.astro** - Party donation breakdown
- ✅ **analysis.astro** - Analysis hub linking to deep-dive pages
- ✅ **privacy.astro** / **terms.astro** / **data.astro** - Static legal/info pages

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

**See `docs/UX_IMPLEMENTATION_PLAN.md` for the full UX roadmap with build order.**

### Actor Type-Specific Profiles (High Priority)
The profile page now adapts based on actor type. Remaining work:
- ✅ **Politician profile** — Full UX pass complete. Party affiliation, contextual stats, linked summaries. Spec: `docs/design/specs/politician-profile.md`
- ✅ **Organisation/Company profile** — Minister names on meetings, classification labels, adaptive headline stat. Spec: `docs/design/specs/organisation-profile.md`
- ✅ **Lobbying Agency profile** — Client list hero, lobbyists in header, "Staff With Political Ties" section. Spec: `docs/design/specs/lobbying-agency-profile.md`. Data quality issues remain (concatenated names).
- ✅ **Political Party profile** — Funding breakdown with aggregate data: top private donors, trade union funding (separated), public funding (separated), funding by year (clickable with per-year top donors, government/opposition annotations), donation type breakdown. Spec: `docs/design/specs/political-party-profile.md`.
- ❌ **Trade Union profile** — Donation recipients view (421 unions, 11k donations made). Needs `/ux-design` spec.

### Backend Data Fixes (High Priority)
- ✅ **Party affiliation** — Fixed 2026-04-13. API serializer + frontend lookup corrected. Party shows on all MP pages.
- ✅ **Labour Party mistyped as Person** — Fixed 2026-04-13. 21,336 donations (£503m) were invisible because "Labour Party" was stored as a Person record instead of Organization. Reassigned to correct Organization #3525.
- ✅ **Cartesian join in ActorDetailView** — Fixed 2026-04-13. Direct annotations on the Actor queryset caused an 8M-row intermediate result for Conservative Party (27k received × 288 made). Converted all annotations to Subqueries. Actor detail went from hanging (>5min) to 0.2s.
- ✅ **Donation context enrichment** — Donations-made rows now show recipient party + role at time of donation. Batch membership lookup, 1 extra query per page.
- ❌ **Department aggregate endpoint** — Meetings belong to ministers not departments; need `/api/v2/departments/{id}/meetings/`
- ❌ **Concatenated name splitting** — Lobbyist names and client names from APPC/consultancy register are concatenated (e.g. "Georgia Hunt Annette Jack" = 2 people). Needs import command fix + re-import.

### New Pages (Medium Priority)
- ❌ **Department profile page** — Aggregate meetings across ministers in a department (blocked on API)
- ❌ **Search results page** — Search box exists in nav but isn't wired up

### Visualizations (Medium Priority)
- ✅ Minister network (force-directed, donations + meetings, bridge nodes)
- ❌ Ego networks (actor-specific view)
- ❌ Sankey diagrams (influence paths)
- ❌ Cluster detection visualization

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

### Data Quality (Mostly Complete)
- ✅ **Automated cleanup completed** (~127,600 issues resolved)
  - ✅ 28,516 → 5 duplicate donations (-99.98%)
  - ✅ 637 → 111 orphaned donations (-83%)
  - ✅ 116,542 → 19,447 missing membership dates (-83%)
  - ✅ Concatenated names split into proper entities
- ⚠️ **Remaining work**
  - 47 invalid donation dates (need EC verification)
  - ~2,500 concatenated/problematic names
  - ~211,000 unlinked entities (entity resolution in progress)
- ⚠️ **Issues found during UX audit (April 2026)**
  - ~~**Party affiliation not imported**~~ ✅ Fixed — import was correct (9,364 memberships with `on_behalf_of`); API serializer and frontend lookup were wrong. Now shows party on all MP pages.
  - **Duplicate donor name variants** — e.g. "Lord Waheed Alli" vs "Lord Waheed Ali" appear as separate donors. Entity resolution should catch spelling variants at ingest.
  - **Meeting attendee strings unparsed in summaries** — `organisation_met_raw` contains comma-separated lists displayed as wall-of-text. Parsed `attendees[]` exist but raw field is what shows in summaries.
  - **Meeting attendees not linked in UI** — API returns `attendees[].actor.id` but timeline displayed them as dead text (now fixed with interconnected links)
- ⚠️ **Organisation & Companies House data quality (April 2026)**
  - **Duplicate orgs (critical)** — Only 4,579 of 64,349 orgs (7.1%) have `canonical_entry_id` set. Major companies have many unflagged duplicates: HSBC has 26 separate org records ("HSBC", "HSBC UK", "HSBC Holdings", "HSBC Holdings plc", "HSBC Bank PLC", "Hsbc", "HSBC Group", "HSBC)" etc.). Same company gets multiple sparse profile pages.
  - **Concatenated org names** — 1,730 orgs classified as "Concatenated (Needs Split)" are unparsed meeting attendee lists stored as single org records (e.g. "Barclays, HSBC UK, Lloyds Banking Group...").
  - **Unknown/unclassified orgs** — 10,711 orgs classified "Unknown", 19,800 as "External Organization" (~47% of all orgs). Only Companies House-enriched orgs have reliable classifications.
  - **Directors missing end_date** — All 62,747 Director memberships have blank `end_date`. Cannot distinguish current vs former directors. Companies House API may provide cessation dates.
  - **ALL-CAPS org names** — 3,627 orgs stored in all caps (e.g. "J.C. BAMFORD EXCAVATORS LIMITED"). Need title-case normalisation for display.
  - **Stray punctuation** — Org names with trailing parentheses, commas, or other artefacts from CSV parsing (e.g. "HSBC)").
  - **Meeting attendee type bias** — 84,572 attendees linked to orgs vs 35,221 to persons (2.4:1 ratio). Unparsed attendee strings default to organisation type, so some persons may be miscategorised as orgs.
  - **Companies House number misassignments** — Some orgs have incorrect CH numbers in `Identifier` table, causing false entity resolution matches. Known examples: "Bp" (actor 49940) assigned Centrica's CH number 03033654; "Exeter City Council Labour Group" (actor 4429) assigned CH number for "EXETER CITY GROUP LIMITED". Need an audit of CH number assignments, particularly for orgs whose names don't match the CH company name.
  - **Lobbyist names concatenated** — APPC register import stored pairs of lobbyist names as single Person records (e.g. "Harriet Davies Stephen Day", "Juliet Bootle Alex Burchill"). 12,554 lobbyist records across 265 agencies, 9,482 unique people — but many are actually 2 people concatenated. Needs splitting similar to meeting attendee parsing.
  - **Lobbyist-to-meeting-attendee linking** — 29 lobbyists appear as meeting attendees, 18 are also MPs, 26 have donation records. These revolving-door connections aren't surfaced anywhere. Entity resolution could link more lobbyists to their meeting attendee records if name parsing is fixed first.
  - **Duplicate director memberships** — Companies House enrichment creates multiple membership records for the same person→company relationship. Example: Michael Kenneth Roberts (actor 109903) has 24 director memberships but only ~15 unique companies — duplicates arise from: (a) same org_id appearing multiple times (e.g. DAVID WILSON HOMES LIMITED #132207 × 2), (b) duplicate org records for the same company (e.g. "Barratt David Wilson Homes" #159541 and #159542, "BDW Trading Limited" #32382 and #49371 and "BDW Trading Ltd" #129200). Frontend deduplicates by normalised org name for display, but the underlying duplicate memberships and unresolved org duplicates remain.
  - ~~**Entity resolution doesn't set `Actor.canonical_entry`**~~ Partially addressed (2026-04-13). Ran `resolve_org_duplicates --ch-only`: **1,806 orgs linked** by Companies House number (deterministic, zero ambiguity). Canonical coverage went from 7.1% → 9.9% (4,579 → 6,385 orgs). General backfill (Phase 2) deferred — found false positives in `Identifier` table (e.g. "Bp" assigned Centrica's CH number 03033654, "Exeter City Council Labour Group" matched to "EXETER CITY GROUP LIMITED"). These are upstream enrichment errors, not resolution bugs.
  - **3,205 orgs share a Companies House number but aren't linked** — Low-hanging fruit. 1,741 company numbers map to 2+ orgs in `CompaniesHouseMatch`. These can be grouped and canonicalised with zero ambiguity.
  - **Recommended entity resolution improvement phases:**
    1. **CH-number canonical linking** (immediate) — Group orgs by approved `CompaniesHouseMatch.company_number`, pick richest record as canonical, set `canonical_entry` on rest. Resolves ~3,205 orgs deterministically.
    2. **Split concatenated attendee strings** (import fix) — 1,730 "Concatenated (Needs Split)" records are unparsed meeting CSV values stored as single org records ("Barclays, HSBC, Lloyds..."). Need splitting into individual `MeetingAttendee` rows linked to correct orgs. This is an import parsing issue, not dedup.
    3. **Fuzzy match against canonical set** — For ~16,400 orgs with no CH match (`not_found`), run fuzzy name matching against the enriched canonical set from Phase 1. Catches "HSBC)" → "HSBC", "Hsbc" → "HSBC".
    4. **Backfill `Actor.canonical_entry`** — Add mode to `populate_canonical` that sets `Actor.canonical_entry` directly (not just relationship-level canonical fields). Makes `effective_self` work everywhere and enables frontend to redirect duplicate profile pages to the canonical.

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
│   │   ├── import_mpsinterests.py
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
│   ├── UX_IMPLEMENTATION_PLAN.md  # UX roadmap
│   ├── FRONTEND_DESIGN.md  # Design system
│   ├── systems-architecture.md
│   ├── data-models.md
│   └── design/specs/       # Page design specs
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
- **Major cleanup completed** (see `docs/DATA_PIPELINE.md`)
  - ✅ 28,516 → 5 duplicate donations (-99.98%)
  - ✅ 637 → 111 orphaned donations (-83%)
  - ✅ 116,542 → 19,447 missing membership dates (-83%)
  - ⚠️ 47 invalid donation dates remaining
  - ⚠️ ~2,500 concatenated names remaining
- **Entity resolution**: `populate_canonical` command highly optimized (in-memory indexing)
- **Companies House enrichment**: 51,157 organizations matched

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

**Full roadmap**: See `docs/UX_IMPLEMENTATION_PLAN.md`

### Phase 1: Foundation ✅ Complete
1. ~~Homepage refinement~~ — Built with editorial design system
2. ~~Party affiliation fix~~ — Fixed (API + frontend)

### Phase 2: Actor Type Variants (Mostly Complete)
3. ~~Lobbying Agency profile~~ ✅ — Client list hero, lobbyists, political ties. Data quality work remains.
4. ~~Organisation/Company profile~~ ✅ — Minister names, classification labels, adaptive stats.
5. ~~Political Party profile~~ ✅ — Aggregate funding view: top private donors, union/public separation, clickable yearly bars with government annotations, per-year donor drill-down.
6. **Trade Union profile** — `/ux-design` spec needed, donation recipients
7. **Universal Political Connections** ✅ — Bidirectional cross-connections on all profile types (person→org "Corporate Connections", org→person "Staff With Political Ties")
8. **Donation context enrichment** ✅ — Recipient party + role at time of donation on all donation-made rows
9. **Person label taxonomy** ✅ — Politician/Mayor/Director/Lobbyist/Person based on membership data
10. **Data import fix: concatenated names** — Lobbyist + client name splitting in import commands

### Phase 3: Navigation & Discovery
6. **Directory refinement** — type filters, party badges
7. **Parties / Meetings / Lobbying pages** — `/ux-audit` → `/ux-design` → `/ux-refine`

### Phase 4: New Pages & Infrastructure
8. **Department aggregate page** — new API endpoint + frontend page
9. **Search results page** — wire up nav search box
10. **Testing infrastructure** — Vitest + pytest-django

---

## Success Metrics (Current Baseline)

**Data Coverage**:
- ✅ 155,065 actors (90,728 persons + 64,337 organizations)
- ✅ 136,590 memberships
- ✅ 91,513 donations
- ✅ 62,798 consultancies (lobbying relationships)
- ✅ **41,362 ministerial meetings** (119,793 attendees, 23 departments)
- ✅ **51,157 Companies House matches** (12,532 auto-approved)
- ✅ 30 years of data (1996-2026)

**Performance (Current)**:
- ✅ API v2 aggregates: <0.5s response time (p95)
- ✅ Actor detail: <0.3s (Subquery annotations, Redis-cached 1hr)
- ✅ Funding summary: <0.1s (Redis-cached 1hr, <0.5s cold)
- ✅ Party pages: ~1s cached, ~8s cold (dev mode Svelte compilation)
- ✅ Politician pages: ~1-2s
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

**Last Major Update**: April 13, 2026 (Political Party profile with aggregate funding view, Universal Political Connections, donation context enrichment, Labour data fix, cartesian join fix, person label taxonomy, government/opposition annotations, public funds and union funding separation)