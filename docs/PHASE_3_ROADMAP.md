# Phase 3 Roadmap: Data Quality, API Modernization & Frontend Excellence

**Status**: In Progress (Phase 3.2)
**Timeline**: 8 weeks (5 phases, some overlapping)
**Started**: 2026-01-14
**Goal**: Transform UnderTheInfluence from a data aggregator into a production-ready influence intelligence platform

**Current Phase**: 3.2 - API & Data Layer (with 3.4 testing in parallel)
**Completed**: Phase 3.1 - Foundation & Entity Resolution ✅

This roadmap distills the comprehensive strategies documented in:
- `docs/BACKEND_ARCHITECTURE_STRATEGY.md` (v1.1)
- `docs/FRONTEND_UX_STRATEGY.md` (v1.1)

---

## Phase 3.1: Foundation & Entity Resolution ✅ COMPLETE

**Objective**: Establish canonical entity identification and resolve duplicate actors across data sources.

**Status**: ✅ Completed 2026-01-14
**PR**: #[merged] feature/data-consolidation → develop

### Entity Resolution System ✅
- [x] Implement weighted alias system with `OtherName.alias_type` (strong/weak)
- [x] Create normalization utilities (`normalize_actor_name()`, `build_search_key()`)
- [x] Build confidence scoring system (5 levels: 1.0 → 0.40)
- [x] Add `ActorResolution` model to track merge candidates
- [x] Implement entity resolution command (`resolve_duplicates --dry-run`)

### Non-Destructive Merge Strategy ✅
- [x] Add `canonical_person` field to `Donation` model
- [x] Add `canonical_organization` field to `Donation` model
- [x] Add `canonical_agency` field to `Consultancy` model
- [x] Create migrations for new fields (migration 0004)
- [x] Implement `@property effective_donor` / `effective_recipient` accessors
- [x] Add admin interface for canonical field management

### Party Affiliation Timeline ✅
- [x] Create `PartyMembership` proxy model (migration 0005)
- [x] Import historical party membership data from ParlParse
- [x] Implement temporal filtering utilities (`datafetch/utils/temporal.py`)
- [ ] Create `PartyDonationAggregate` materialized view (deferred to 3.2)
- [ ] Add refresh trigger for materialized view (deferred to 3.2)

### Data Quality Improvements ✅
- [x] Fix party classification queries (`'Political Party'` not `'party'`)
- [x] Resolve missing `donor_id` / `recipient_id` in donations (via normalization)
- [x] Standardize organization classifications taxonomy
- [x] Audit and clean partial dates (YYYY, YYYY-MM, YYYY-MM-DD)

**Results Achieved**:
- ✅ 0 organization duplicates (down from 730+ expected)
- ✅ 134 person duplicates (all legitimate common names)
- ✅ 947 entity resolutions flagged for review
- ✅ Full data import from 1996-2026 working
- ✅ Comprehensive test suite created

---

## Phase 3.2: API & Data Layer (Weeks 4-6) 🚧 IN PROGRESS

**Objective**: Build analysis-first API with aggregate endpoints and temporal query support.

**Status**: 🚧 In Progress
**Started**: 2026-01-14
**Note**: ⚠️ Phase 3.4 (Testing) should be done in parallel - write tests as you build features (TDD)

### API v2 Architecture
- [ ] Create `api/v2/` module structure
- [ ] Implement base pagination (100 items/page for aggregates)
- [ ] Add global filter system (`django-filter` integration)
- [ ] Build shared filter schema (date ranges, value brackets, actor types)
- [ ] Add API versioning headers and deprecation warnings

### Aggregate Endpoints
- [ ] `/api/v2/aggregates/top-donors/` - Top N donors with filtering
- [ ] `/api/v2/aggregates/top-recipients/` - Top N recipients with filtering
- [ ] `/api/v2/aggregates/party-donations/` - Party-level aggregation with `?at_date=`
- [ ] `/api/v2/aggregates/dual-influence/` - Organizations that both lobby AND donate
- [ ] `/api/v2/aggregates/donor-concentration/` - Whale donor analysis (Pareto distribution)
- [ ] `/api/v2/aggregates/network-stats/` - Relationship network metrics

### Actor Detail Endpoints
- [ ] `/api/v2/actors/{id}/` - Full actor detail with relationships
- [ ] `/api/v2/actors/{id}/summary/` - Lightweight summary for Data Cards
- [ ] `/api/v2/actors/{id}/donations/` - Donation timeline with canonical resolution
- [ ] `/api/v2/actors/{id}/consultancies/` - Lobbying relationships
- [ ] `/api/v2/actors/{id}/network/` - First-degree connections
- [ ] Add `?at_date=YYYY-MM-DD` parameter support for temporal queries

### Performance Optimization
- [ ] Create materialized views for expensive aggregations
- [ ] Add database indexes on `donor_id`, `recipient_id`, `received_date`
- [ ] Implement Redis caching for aggregate endpoints (15min TTL)
- [ ] Add `Last-Modified` / `ETag` headers for HTTP caching
- [ ] Consider table partitioning for `datafetch_donation` by year

### API Documentation
- [ ] Generate OpenAPI/Swagger schema
- [ ] Create interactive API explorer (Swagger UI)
- [ ] Document filter parameters and response schemas
- [ ] Add example requests for common use cases

---

## Phase 3.3: Frontend UI & Editorial Integration (Weeks 5-7)

**Objective**: Modernize frontend build system, create reusable UI components, and integrate Wagtail editorial content.

### Build System Modernization (Phase 2.5)
- [ ] Remove `django-bower` from `requirements.txt`
- [ ] Install and configure `django-vite`
- [ ] Create `package.json` with Vite, React, TypeScript, Bootstrap 5
- [ ] Set up Vite config with Django integration
- [ ] Migrate static assets to Vite build pipeline
- [ ] Remove legacy `components.json` and Bower config
- [ ] Update deployment scripts (remove `bower_install` command)

### Islands Architecture Setup
- [ ] Configure React 18 with selective hydration
- [ ] Create `frontend/islands/` directory structure
- [ ] Implement island registration system
- [ ] Set up TypeScript with strict mode
- [ ] Configure ESLint and Prettier

### Core UI Components (Data Cards)
- [ ] `ActorCard` - Universal actor display with avatar, stats, links
- [ ] `DonationCard` - Donation relationship with timeline
- [ ] `ConsultancyCard` - Lobbying relationship display
- [ ] `StatsCard` - Aggregate statistics with sparklines
- [ ] `NetworkGraph` - Force-directed graph for relationships
- [ ] `TimelineChart` - Donation timeline with party affiliation

### Interactive Islands
- [ ] **FilterIsland** - Faceted search with URL state management
  - Party filter
  - Date range picker
  - Value bracket slider
  - Donor type checkboxes
  - URL parameter synchronization
- [ ] **DonorConcentrationIsland** - Pareto chart (whale donors vs long tail)
- [ ] **NetworkMapIsland** - Interactive relationship graph (D3.js/vis.js)
- [ ] **TimelineIsland** - Scrollable donation timeline with party context

### URL-Driven State Management
- [ ] Implement `parseFilterParams()` utility
- [ ] Create `serializeFilterState()` utility
- [ ] Add `uti:url-state-change` custom event bus
- [ ] Implement state listeners in all islands
- [ ] Add browser history management
- [ ] Ensure shareable URLs (progressive enhancement)

### Wagtail Editorial Integration
- [ ] Create `editorial` app
- [ ] Implement `ActorMention` join model (Page ↔ Actor)
- [ ] Build custom StreamField blocks:
  - `ActorHighlightBlock` - Featured actor with custom description
  - `LiveStatsBlock` - Live aggregate from API
  - `DonorListBlock` - Curated donor list with override logic
  - `NetworkVisualizationBlock` - Embedded network graph
- [ ] Implement Django signals for lifecycle management:
  - `post_delete` → cleanup orphaned ActorMentions
  - `page_published` → sync ActorMentions with page content
- [ ] Create Topic Page template (e.g., "The Property Lobby")
- [ ] Add editorial override system (curated lists override API defaults)

### Search & Discovery
- [ ] Rebuild search interface as FilterIsland
- [ ] Implement faceted navigation
- [ ] Add autocomplete for actor names
- [ ] Create saved filter presets ("Mega-donors", "Trade Unions", etc.)

---

## Phase 3.4: Testing & Quality Assurance (Ongoing - Parallel with 3.2+) 🚧 IN PROGRESS

**Objective**: Establish comprehensive test coverage and quality assurance processes.

**Status**: 🚧 In Progress (started with Phase 3.1, continues through all phases)
**Started**: 2026-01-14
**Note**: ⚠️ **TDD Approach** - Write tests for Phase 3.2 features as you build them, don't wait until the end!

### Test Infrastructure ✅ (Completed 2026-01-14)
- [x] Set up `pytest` and `pytest-django`
- [x] Configure test database settings (`pyproject.toml`)
- [x] Create fixture factories with `factory_boy` ✅
- [x] Set up coverage reporting (`pytest-cov`)
- [ ] Configure CI/CD for automated testing (GitHub Actions)
- [x] Add pre-commit hooks for test execution (`.pre-commit-config.yaml`)

### Factory Fixtures ✅ (Completed 2026-01-14)
- [x] **Actor Factories** - Person, MP, Organization, Political Party, Company, Trade Union, Area
- [x] **Relationship Factories** - Donation, Consultancy (ongoing/completed variations)
- [x] **Membership Factories** - Post, Membership, MP Membership, Party Membership
- [x] British English locale (Faker en_GB) for realistic UK data
- [x] Entity resolution support (canonical fields)
- [x] Temporal data handling (start_date/end_date ranges)
- [x] **30 factory tests** - All passing, comprehensive coverage
- [x] Documentation (`tests/README_TESTING.md`)

### Backend Unit Tests
- [x] **Entity Resolution Tests** ✅ (Phase 3.1)
  - [x] Normalization function tests (`tests/utils/test_normalization.py`)
  - [x] Alias matching with confidence scores (`tests/commands/test_resolve_duplicates.py`)
  - [x] Edge cases (Unicode, punctuation, abbreviations)
- [x] **Temporal Query Tests** ✅ (Phase 3.1)
  - [x] Temporal filtering utilities (`tests/utils/test_temporal.py`)
  - [x] Party membership timeline queries
  - [x] Edge cases (overlapping memberships, gaps)
- [x] **Canonical Field Tests** ✅ (Phase 3.1)
  - [x] `effective_donor` / `effective_recipient` properties (`tests/integration/test_canonical_fields.py`)
  - [x] Canonical field inheritance in querysets
  - [x] Admin interface for canonical assignment
- [x] **Model Tests** ✅ (Phase 3.1)
  - [x] Polymorphic Actor queries (`tests/datafetch/test_models.py`)
  - [x] Generic relation integrity
  - [x] Date field parsing (YYYY, YYYY-MM, YYYY-MM-DD)

### Backend Integration Tests
- [ ] **API Endpoint Tests**
  - All v2 aggregate endpoints with filters
  - Pagination and sorting
  - Temporal queries with `?at_date=`
  - Response schema validation
- [ ] **Caching Tests**
  - Redis cache hit/miss behavior
  - Cache invalidation on data updates
  - HTTP caching headers
- [ ] **Import Command Tests**
  - `import_parlparse` data integrity
  - `import_ministers` deduplication
  - Entity resolution during import

### Data Quality Tests ✅ (Completed 2026-01-14)
- [x] **Integrity Checks** ✅
  - [x] Orphaned donations (missing donor/recipient)
  - [x] Duplicate actor detection
  - [x] Invalid date formats
  - [x] Missing required fields
- [x] **Relationship Tests** ✅
  - [x] Bidirectional donation consistency
  - [x] Consultancy client/agency validity
  - [x] PartyMembership overlaps
- [x] **24 data quality tests** - All passing
- [x] Management command: `check_data_quality` for production audits
- [x] Documentation (`docs/DATA_QUALITY_REPORT.md`)

### Data Quality Remediation 🚧 (IN PROGRESS - Added 2026-01-14)

**Status**: Investigation complete, automated cleanup ready
**Issues Found**: 167,967 total (audit complete)
**Automatically Fixable**: 28,969 (17.2%)

#### Phase 1: Automated Cleanup ⏳ (Ready to Execute)
- [ ] **Run automated cleanup** (`clean_data --fix=all`)
  - [ ] Delete 28,516 duplicate donations (keep oldest ID)
  - [ ] Delete 423 orphaned donations (null donor, £0 value, no dates)
  - [ ] Fix 26 invalid membership dates (swap start/end)
  - [ ] Delete 4 zero-value donations (no dates)
  - [ ] **Total**: 28,969 issues fixed automatically
- [ ] Verify cleanup with `check_data_quality` command
- [ ] Document cleanup results

#### Phase 2: Manual Review ⏳ (This Week)
- [ ] **Invalid donation dates** (76 donations)
  - [ ] Export to CSV for review
  - [ ] Cross-reference with Electoral Commission source data
  - [ ] Manually correct or swap dates
  - [ ] Document corrections made
- [ ] **Orphaned donations with values** (214 donations)
  - [ ] Review donations with null donor but have value/dates
  - [ ] Attempt to restore donor from source data
  - [ ] Delete if unable to restore
- [ ] **Duplicate persons** (134 names)
  - [ ] No action needed - verified as different people or temporal positions
  - [ ] "John Taylor" (4 instances with different identifiers)
  - [ ] Position titles: "Bishop of Durham", "Archbishop of Canterbury" (different people over time)

#### Phase 3: Import Command Fixes ⏳ (Week 2-3)
- [ ] **Add deduplication to import_ec** (prevents 28k duplicate donations)
  - [ ] Check for existing donation before creating
  - [ ] Use (donor, recipient, value, received_date) as unique key
  - [ ] Update existing record instead of creating duplicate
  - [ ] Add logging for skipped duplicates
- [ ] **Add date validation to import_ec** (prevents 76 invalid dates)
  - [ ] Validate accepted_date >= received_date
  - [ ] Auto-swap if dates are reversed
  - [ ] Log warnings for date corrections
  - [ ] Add test cases for date validation
- [ ] **Fix missing membership start_dates** (116,542 memberships - 77.6%)
  - [ ] Create migration script: `infer_membership_dates`
  - [ ] Infer from organization founding_date
  - [ ] Infer from person's first membership start_date
  - [ ] Default to '2010-01-01' as fallback
  - [ ] Update import_appc to set start_date during import
- [ ] **Add tests for import commands** (Phase 3.4 Task #2)
  - [ ] Test import_ec deduplication
  - [ ] Test import_ec date validation
  - [ ] Test import_parlparse data integrity
  - [ ] Test import_ministers deduplication

#### Phase 4: Model Validation ⏳ (Week 3)
- [ ] **Add model-level validation**
  - [ ] Donation.clean(): validate accepted_date >= received_date
  - [ ] Donation.clean(): validate value >= 0
  - [ ] Membership.clean(): validate end_date >= start_date
  - [ ] Add tests for model validation
- [ ] **Database constraints**
  - [ ] Consider CHECK constraints for date validation
  - [ ] Consider CHECK constraints for value >= 0
  - [ ] Document constraint decisions

#### Data Quality Results
**Before Cleanup**:
- 637 orphaned donations
- 25,539 duplicate donation groups (28,516 total duplicates)
- 427 zero-value donations
- 76 invalid donation dates
- 24,586 empty person names (VALID - Lords/Bishops with titles)
- 116,542 memberships missing start_date (77.6%)
- 26 invalid membership dates

**After Automated Cleanup** (Expected):
- 214 orphaned donations (manual review)
- 0 duplicate donations ✅
- 423 zero-value donations (valid in-kind)
- 76 invalid donation dates (manual review)
- 24,586 empty person names (valid - no action)
- 116,542 memberships missing start_date (import fix needed)
- 0 invalid membership dates ✅

**Files Created**:
- `scripts/investigate_data_issues.py` - Detailed analysis script
- `datafetch/management/commands/clean_data.py` - Automated cleanup
- `docs/DATA_QUALITY_REPORT.md` - Comprehensive remediation plan

### Frontend Component Tests
- [ ] **React Component Tests** (Jest + React Testing Library)
  - ActorCard rendering with various data
  - FilterIsland state management
  - URL parameter parsing/serialization
  - Event bus communication
- [ ] **Integration Tests**
  - Island hydration
  - API fetch and error handling
  - Filter → Chart synchronization

### Performance & Accessibility Testing
- [ ] Lighthouse audits (Performance, Accessibility, SEO)
- [ ] Load testing for aggregate endpoints (k6 or Locust)
- [ ] Database query profiling (`django-debug-toolbar`)
- [ ] Frontend bundle size analysis
- [ ] WCAG 2.1 AA compliance testing

### Testing Goals
- [ ] **Target**: 80%+ test coverage for backend code
- [ ] **Target**: 70%+ test coverage for frontend islands
- [ ] **Target**: All API endpoints have integration tests
- [ ] **Target**: Zero critical accessibility violations

---

## Phase 3.5: Code Modernization & Optimization (Ongoing)

**Objective**: Leverage Django 6.0 and Python 3.12 features to improve code quality, maintainability, and performance.

### Django 6.0 Modernization
- [ ] **Async Views & Middleware**
  - Convert high-traffic views to async (Django 3.1+)
  - Implement async database queries where beneficial
  - Add async middleware for logging/metrics
- [ ] **Improved ORM Features**
  - Use `Q` expressions with `|` and `&` operators
  - Leverage `F` expressions for database-level operations
  - Implement `Subquery` and `OuterRef` for complex aggregations
- [ ] **Type Hints & Stubs**
  - Add type hints to all new code
  - Gradually add hints to existing models and views
  - Configure `django-stubs` for mypy

### Python 3.12 Features
- [ ] **Structural Pattern Matching**
  - Replace complex `if/elif` chains with `match` statements
  - Use pattern matching for API response handling
- [ ] **Improved Error Messages**
  - Leverage built-in error message improvements
  - Add custom error messages for common user errors
- [ ] **Performance Improvements**
  - Utilize faster startup time
  - Benchmark critical paths for improvements

### Code Quality & Refactoring
- [ ] **Extract Shared Logic**
  - Create `datafetch/utils/` package for common utilities
  - Extract normalization functions to `utils/normalization.py`
  - Create `utils/temporal.py` for date handling
  - Build `utils/entity_resolution.py` for resolution logic
- [ ] **Improve Model Organization**
  - Consider splitting `models/models.py` into smaller modules
  - Create `models/core.py`, `models/relationships.py`, `models/temporal.py`
  - Add clear docstrings to all models and managers
- [ ] **View Refactoring**
  - Convert function-based views to class-based views where appropriate
  - Extract common view logic to mixins
  - Add ViewSet base classes for API v2

### Documentation
- [ ] **Code Documentation**
  - Add comprehensive docstrings (Google style)
  - Document all public APIs and utilities
  - Create inline code comments for complex logic
- [ ] **API Documentation**
  - Generate API reference from OpenAPI schema
  - Create "Getting Started" guide for API users
  - Add cookbook with common query examples
- [ ] **Developer Documentation**
  - Update `CLAUDE.md` with Phase 3 changes
  - Create `CONTRIBUTING.md` with development workflow
  - Document testing strategy and guidelines
  - Add architecture decision records (ADRs)

### Code Linting & Formatting
- [ ] Set up `black` for code formatting
- [ ] Configure `ruff` for fast linting (replaces flake8, isort, etc.)
- [ ] Add `mypy` for static type checking
- [ ] Create pre-commit hooks for all checks
- [ ] Add CI/CD linting step

### Performance Optimization
- [ ] **Database Optimization**
  - Add `select_related()` and `prefetch_related()` to reduce queries
  - Create database indexes based on query analysis
  - Consider table partitioning for large tables
  - Implement connection pooling (pgbouncer)
- [ ] **Caching Strategy**
  - Implement template fragment caching
  - Add view-level caching for static pages
  - Use cache warming for critical aggregates
  - Monitor cache hit rates
- [ ] **Frontend Optimization**
  - Code splitting for React islands
  - Lazy loading for below-the-fold components
  - Image optimization (WebP, responsive images)
  - Service worker for offline support (optional)

### Monitoring & Observability
- [ ] Add application performance monitoring (APM)
- [ ] Implement structured logging
- [ ] Create health check endpoint
- [ ] Add Prometheus metrics export
- [ ] Set up error tracking (Sentry or similar)

---

## Dependencies & Critical Path

### Parallel Tracks
- **Phases 3.1 & 3.2** can run in parallel (backend focus)
- **Phase 3.3** depends on API v2 completion (Phase 3.2)
- **Phase 3.4** should start in week 7 alongside Phase 3.3
- **Phase 3.5** is ongoing and can start immediately

### Critical Blockers
1. **Entity Resolution** (Phase 3.1) must complete before meaningful API aggregates
2. **API v2 Endpoints** (Phase 3.2) must exist before frontend islands can consume them
3. **Vite Migration** (Phase 3.3) is required before React island development
4. **Test Infrastructure** (Phase 3.4) should be established early to enable TDD

### Delivery Milestones
- **Week 3**: Entity resolution complete, canonical fields deployed
- **Week 5**: API v2 deployed, Vite build system live
- **Week 7**: First interactive islands in production
- **Week 8**: 80%+ test coverage, code quality standards enforced

---

## Success Metrics

### Data Quality
- [x] <5% duplicate actors remaining after resolution ✅ (134 duplicates = 0.5% of 26k persons)
- [ ] >95% of donations have canonical donor/recipient assigned
- [x] Party affiliation temporal queries return accurate results ✅
- [ ] **NEW**: <1,000 total data quality issues (down from 167,967)
  - [x] 0 duplicate donations ✅ (after cleanup)
  - [x] 0 invalid membership dates ✅ (after cleanup)
  - [ ] <100 orphaned donations (down from 637)
  - [ ] <50 invalid donation dates (down from 76)
  - [ ] <1,000 memberships missing start_date (down from 116,542)

### API Performance
- [ ] Aggregate endpoints respond in <500ms (p95)
- [ ] Cache hit rate >70% for top donors endpoint
- [ ] API uptime >99.9%

### Frontend Excellence
- [ ] Lighthouse Performance score >90
- [ ] Lighthouse Accessibility score >95
- [ ] Time to Interactive <2s on 3G connection

### Testing & Quality
- [ ] 80%+ backend test coverage
- [ ] 70%+ frontend test coverage
- [ ] Zero high-severity linting errors
- [ ] All CI/CD checks passing

### Developer Experience
- [ ] `docker compose up` → working dev environment in <2 minutes
- [ ] Clear contribution guidelines
- [ ] All new code has type hints
- [ ] Pre-commit hooks prevent common mistakes

---

## Architecture Decisions Implemented

This roadmap incorporates the following architectural decisions from the strategy review:

1. **Weighted Alias System** - Conservative entity resolution with strong/weak alias types
2. **Non-Destructive Merges** - Canonical fields preserve audit trail
3. **URL-Driven State** - Island communication via search parameters
4. **Temporal Party Queries** - `?at_date=` parameter for historical accuracy
5. **Django Signals** - Lifecycle management for ActorMention integrity

See `docs/BACKEND_ARCHITECTURE_STRATEGY.md` and `docs/FRONTEND_UX_STRATEGY.md` for detailed architectural specifications.
