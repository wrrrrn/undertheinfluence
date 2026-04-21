# UnderTheInfluence Documentation

**Last Updated**: April 16, 2026

This directory contains all project documentation for UnderTheInfluence, a Django-based web application tracking political influence in UK politics.

---

## 📖 Start Here

**New to the project?** Read these in order:

1. **`CURRENT_STATE.md`** - Overview of what's built, what works, and what's planned
2. **`systems-architecture.md`** - How the system is designed (Islands Architecture, API, data models)
3. **`data-models.md`** - Detailed reference for database models (Popolo-based)

---

## 📚 Core Documentation

### Architecture & Design

**`systems-architecture.md`** (v5.0 - Astro Frontend + API Caching)
- Complete system architecture reference
- Technology stack (Django 6.0, Astro 5, Svelte 5, PostgreSQL 15, Redis)
- Architecture diagrams (high-level, Docker Compose)
- Frontend architecture (Astro SSR, Svelte partial hydration, D3.js)
- API architecture (aggregate endpoints, Redis caching, filtering)
- Key design decisions with rationale

**`data-models.md`**
- Popolo-based data model reference
- Model hierarchy (Actor → Person/Organization)
- Relationship models (Membership, Donation, Consultancy)
- Supporting models (Identifier, OtherName, Link, Source, etc.)
- Abstract behaviors (Timestampable, Dateframeable)
- Data import sources and status

**`CURRENT_STATE.md`**
- Feature inventory (what's built, what's planned)
- Technology stack tables
- Working features vs pending features
- File structure reference
- Known issues and next steps
- Success metrics baseline

### Frontend & UX

**`FRONTEND_DESIGN.md`** (v2.0 - Natural History Edition)
- Design system and visual identity
- Typography (Zodiak headlines + Satoshi body)
- Color palette (paper/ink, accent red, node colors, party colors)
- Component design system (stats as typography, section labels, rules, annotations)
- Layout & spacing rules (newspaper grid, asymmetric columns)
- Visualization patterns (network graph, timeline, radial charts)
- Accessibility checklist

**`UX_IMPLEMENTATION_PLAN.md`** ⭐ UX roadmap
- 5-phase UX process (audit → constraints → design → mockup → refine)
- Page hierarchy and build order (4 tiers)
- Actor type analysis (9 archetypes with distinct data profiles)
- Completed work, blocked items, and planned improvements
- Interconnectedness principle and audit requirements

**`UI-STACK.md`** *(archived — historical migration guide)*
- Documents the React → Astro/Svelte transition (completed January 2026)
- Kept for reference only; see `systems-architecture.md` for current architecture

**`design/specs/`** - Design specifications for individual pages
- `homepage.md` - Homepage design spec (all items complete as of April 16)
- `actor-profile.md` - Actor profile page spec (timeline-based, no tabs)
- `politician-profile.md` - Politician-specific profile refinements
- `organisation-profile.md` - Organisation/company profile spec
- `lobbying-agency-profile.md` - Lobbying agency profile spec (client list hero, political ties)

### API & Backend

**`BACKEND_DESIGN.md`** ⭐ Backend decision framework
- The strategy: REST-shaped core resources + named aggregate/summary endpoints
- Endpoint taxonomy (Family A REST / Family B named queries — five shapes)
- The checkpoint: shape of a good endpoint (§4), data correctness rules (§7)
- Known issues punch list (§8) and backend roadmap (§9)
- URL migration plan (§11) and audit stance (§12)

**`BACKEND_CONSTRAINTS_SNAPSHOT.md`** ⭐ Living snapshot of backend state
- Maintained by python-architect; consumed by `/ux-audit`, `/ux-constraints`, `/ux-design`, `/d3-viz`, and the `frontend-designer` agent
- Per-endpoint reference cards (§2), per-page fetch map (§3), inventory of available aggregate fields (§4)
- Data-quality constants (§5), performance characteristics (§6)
- "What is NOT available today" (§7), open architectural questions + landed verdicts (§8)
- Read this before proposing any backend-adjacent design work — architect may have already answered the question.

**`API_REFERENCE.md`**
- REST API v2 endpoint reference
- Aggregate endpoints (top donors, party donations, network stats)
- Actor detail endpoints
- Query parameters and response formats
- Interactive documentation links (Swagger/ReDoc)

### Data Pipeline & Quality

**`DATA_PIPELINE.md`** ⭐ Consolidated data reference
- Import pipeline: commands, order, coverage (23 departments, 155k actors)
- Data quality: current issues with root causes and code references
- Remediation strategy: prioritized fix plan (Tier 1-3) with SQL and code
- Entity resolution: architecture, commands, resolution tiers
- Cleanup command reference
- Troubleshooting guide

Consolidates the former: DATA_IMPORT_GUIDE, DATA_QUALITY_REPORT, DATA_CLEANUP_GUIDE, data-import-testing, ADDITIONAL_CLEANUP_COMMANDS_ANALYSIS, CANONICAL_IMPLEMENTATION_REPORT, ENTITY_RESOLUTION_OPTIMIZATION (all archived)

---

## 🎨 Design Assets

**`design/`** directory contains:
- `dashboard-01.png` - Homepage dashboard mockup
- `dashboard-02.png` - Dashboard with filters mockup
- `dashboard-03.png` - Data visualization mockup
- `timeline.png` - Timeline/activity feed design reference
- `visual-design-interpretation.html` - Interactive design spec
- Design system visuals (typography, colors, components)

---

## 📦 Archive

**`archive/`** directory contains historical planning documents (January 14-19, 2026):
- Strategic planning docs (BACKEND_ARCHITECTURE_STRATEGY, FRONTEND_UX_STRATEGY)
- Phase roadmaps (PHASE_3_ROADMAP, PHASE_3.4_PROGRESS)
- Outdated import documentation
- Historical wireframes

**See `archive/README.md` for details on what's archived and why.**

These documents are preserved for reference but no longer actively maintained.

---

## 🚀 Quick Reference

### I want to...

**Understand the current state of the project**
→ Read `CURRENT_STATE.md`

**Understand how the system is designed**
→ Read `systems-architecture.md`

**Understand the database schema**
→ Read `data-models.md`

**Use the API**
→ Read `API_REFERENCE.md` or visit `/api/v2/docs/` for interactive docs

**Build or change a backend endpoint**
→ Read `BACKEND_DESIGN.md` — especially §4 "shape of a good endpoint" and §7 "data correctness rules"

**Import data**
→ Read `DATA_PIPELINE.md` (Section 2: Import Pipeline)

**Build a new frontend page**
→ Read `UX_IMPLEMENTATION_PLAN.md` (roadmap) + `FRONTEND_DESIGN.md` (design system) + `design/specs/` (page specs)
→ Follow the 5-phase process: `/ux-audit` → `/ux-design` → `/ux-mockup` → `/ux-refine`

**Fix data quality issues**
→ Read `DATA_PIPELINE.md` (Sections 3-4: Data Quality + Remediation Strategy)

**Understand why a design decision was made**
→ Check "Key Design Decisions" in `systems-architecture.md` or `data-models.md`

**See historical planning**
→ Browse `archive/` directory

---

## 📝 Document Maintenance

### When to Update

**`CURRENT_STATE.md`** - Update when:
- New features are completed and working
- Technology stack changes
- Deployment status changes
- Major milestones reached

**`systems-architecture.md`** - Update when:
- Architecture decisions are made
- New components/apps are added
- Technology stack changes
- Deployment architecture changes

**`data-models.md`** - Update when:
- New models are added
- Model fields change
- Data sources change
- Import commands are fixed/added

**`FRONTEND_DESIGN.md`** - Update when:
- Design system changes (colors, typography, spacing)
- New components are added
- Accessibility standards updated

### Document Ownership

All documentation is maintained by the development team. When making significant changes to the codebase, update the relevant documentation in the same PR/commit.

---

## 🔗 External Resources

**Project Code**:
- Main repository: https://github.com/spudmind/undertheinfluence
- Deployment repository: https://github.com/spudmind/uti-deploy

**Data Sources**:
- ParlParse (MySociety): https://github.com/mysociety/parlparse
- Electoral Commission: https://search.electoralcommission.org.uk/
- TheyWorkForYou API: https://www.theyworkforyou.com/api/

**Standards & Specifications**:
- Popolo Specification: http://www.popoloproject.com/
- Django 6.0 Documentation: https://docs.djangoproject.com/en/6.0/
- Astro Documentation: https://docs.astro.build/
- Svelte 5 Documentation: https://svelte.dev/docs/svelte

---

**Last Major Update**: April 16, 2026 (Homepage complete, API caching, documentation refresh)
