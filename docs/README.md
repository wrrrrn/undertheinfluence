# UnderTheInfluence Documentation

**Last Updated**: January 22, 2026

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

**`systems-architecture.md`** (v4.0 - Islands Architecture Edition)
- Complete system architecture reference
- Technology stack (Django 6.0, React 18, Vite 5, PostgreSQL 15)
- Architecture diagrams (high-level, request/response flow, Docker Compose)
- Frontend architecture (Islands, Zustand, TanStack Query)
- API architecture (aggregate endpoints, filtering)
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

### Frontend

**`FRONTEND_DESIGN.md`** (v1.1 - Editorial Edition)
- Design system and visual identity
- Typography (Playfair Display + Inter)
- Color palette (party colors, data visualization colors)
- Component design system (cards, badges, buttons)
- Layout & spacing rules
- Accessibility checklist
- Page patterns (homepage, profiles, directory)

**`FRONTEND_IMPLEMENTATION.md`**
- Detailed implementation plan
- Component specifications
- API integration patterns
- State management strategy
- Performance considerations

### API

**`API_REFERENCE.md`**
- REST API v2 endpoint reference
- Aggregate endpoints (top donors, party donations, network stats)
- Actor detail endpoints
- Query parameters and response formats
- Interactive documentation links (Swagger/ReDoc)

### Data Quality & Import

**`DATA_CLEANUP_GUIDE.md`** ⭐ Start here for cleanup
- Step-by-step cleanup workflow
- Fix types by phase (correct execution order)
- Command options and examples
- Understanding output (before/after stats)
- Troubleshooting guide

**`DATA_CLEANUP_RESULTS.md`**
- Summary of all automated cleanup operations
- Statistics on resolved issues (duplicates, concatenations, garbage data)
- Before/After metrics for Companies House and Lobbying data
- Remaining issues and Phase 2 plan

**`MINISTERIAL_MEETINGS_CLEANUP_DEEP_DIVE.md`**
- Detailed analysis of Ministerial Meetings data quality
- Investigation of concatenated attendee names (9,000+ records)
- "Semicolon actors" and roundtable parsing issues
- Remediation plan for complex string splitting

**`ADDITIONAL_CLEANUP_COMMANDS_ANALYSIS.md`**
- Evaluation of 5 specialized cleanup commands
- Impact analysis for splitting concatenated orgs/attendees
- Statistics on target records (160-1,800 affected per command)
- Recommended execution order

**`DATA_QUALITY_REPORT.md`**
- Comprehensive data quality analysis
- 167,967 issues identified across 26,000 actors
- Automated cleanup recommendations
- Issue breakdowns (duplicates, missing dates, orphaned records)
- Entity resolution strategy

**`DATA_IMPORT_GUIDE.md`**
- Complete guide for importing political data
- Quick start scripts (`full_data_import.sh`)
- Individual import commands (ParlParse, Ministers, MP/Lords interests)
- Working vs broken import sources
- Import order recommendations
- Troubleshooting guide

**`data-import-testing.md`**
- Import command testing results
- Status of each data source (✅ Working, ⚠️ Needs Update, ⛔ Broken)
- Known issues with imports
- Manual testing procedures

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

**Import data**
→ Read `DATA_IMPORT_GUIDE.md`

**Build a new frontend component**
→ Read `FRONTEND_DESIGN.md` (design system) + `FRONTEND_IMPLEMENTATION.md` (patterns)

**Fix data quality issues**
→ Read `DATA_CLEANUP_GUIDE.md` (step-by-step workflow), `DATA_QUALITY_REPORT.md` (analysis), `DATA_CLEANUP_RESULTS.md` (past results)

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
- Islands Architecture: https://jasonformat.com/islands-architecture/
- Vite Guide: https://vitejs.dev/guide/
- TanStack Query: https://tanstack.com/query/latest

---

**Last Major Update**: January 22, 2026 (documentation consolidation, added API reference)
