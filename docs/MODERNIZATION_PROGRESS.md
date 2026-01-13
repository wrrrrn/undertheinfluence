# UnderTheInfluence Modernization Progress

This document tracks the progress of modernizing the UnderTheInfluence Django application from Django 1.8/Wagtail 1.1 to modern versions.

## Overview

- **Start Date**: January 12, 2026
- **Current Phase**: Phase 2 COMPLETE ✅ (Django 5.1 / Wagtail 7.2.x)
- **Current Branch**: django-upgrade
- **Phase 1 (Docker Foundation)**: COMPLETED ✅
- **Phase 1.5 (Data Ingestion)**: UNBLOCKED ✅
- **Phase 2 (Django/Wagtail Upgrade)**: COMPLETED ✅

## Phase 1: Docker Foundation - COMPLETED ✅

**Status**: Successfully completed on January 12, 2026

**Objective**: Set up Docker infrastructure for the legacy Django 1.8 + Wagtail 1.1 application

### Completed Tasks

1. **Docker Infrastructure**
   - ✅ Created Dockerfile with Python 3.7 base (maximum compatible version for legacy stack)
   - ✅ Created docker-compose.yml with PostgreSQL 15, Redis 7, and web services
   - ✅ Created .dockerignore for optimized build context
   - ✅ Added health checks for all services

2. **Configuration Migration**
   - ✅ Replaced unsafe YAML configuration (`yaml.load()`) with python-decouple
   - ✅ Created .env.example template with comprehensive settings
   - ✅ Created .env file for local development
   - ✅ Updated .gitignore to exclude .env and .claude/

3. **Security Fixes**
   - ✅ Fixed unsafe `yaml.load()` in settings.py (replaced with environment variables)
   - ✅ Fixed SQL injection vulnerability in api/views.py by adding ALLOWED_SORT_FIELDS whitelist

4. **Dependency Updates**
   - ✅ Updated requirements.txt with Python 3.7 compatible versions
   - ✅ Pinned djangorestframework==3.6.4 (last version supporting Django 1.8)
   - ✅ Pinned pytest-django==4.5.2 (Python 3.7 compatible)

5. **Database Setup**
   - ✅ Created PostgreSQL initialization script (pg_trgm, unaccent extensions)
   - ✅ Successfully ran all Django migrations
   - ✅ Database schema fully migrated

6. **Verification**
   - ✅ All containers running successfully
   - ✅ Django application accessible at http://localhost:8000
   - ✅ Default Wagtail welcome page displays correctly
   - ✅ No startup errors or warnings

### Key Technical Decisions

**Python Version**: Python 3.7
- Required for compatibility with Django 1.8 + Wagtail 1.1 + django-modelcluster 0.6.2
- Python 3.8+ causes RuntimeError with django-modelcluster
- Python 3.10+ incompatible with Django 1.8 (collections.Iterator moved to collections.abc)

**Django REST Framework**: 3.6.4
- DRF 3.7+ requires Django 1.11+ (uses django.urls module)
- DRF 3.6.4 is the last version supporting Django 1.8

**Configuration Management**:
- Migrated from YAML files to environment variables
- Uses python-decouple for 12-factor app compliance
- More secure than yaml.load() which has arbitrary code execution vulnerability

### Files Created

- `Dockerfile` - Multi-stage build with Python 3.7
- `docker-compose.yml` - Orchestration for web, PostgreSQL, Redis services
- `.dockerignore` - Optimizes Docker build context
- `.env.example` - Environment variable template
- `.env` - Local development configuration (gitignored)
- `docker/postgres-init/01-init.sql` - PostgreSQL extensions initialization
- `MODERNIZATION_PROGRESS.md` - This file

### Files Modified

- `requirements.txt` - Updated with compatible package versions
- `undertheinfluence/settings.py` - Migrated to environment variables
- `api/views.py` - Added sort field whitelist for security
- `.gitignore` - Added .claude/, .env, .env.local

### Current Application State

- **Running**: ✅ Yes
- **URL**: http://localhost:8000
- **Database**: PostgreSQL 15 (all migrations applied)
- **Cache**: Redis 7
- **Python**: 3.10
- **Django**: 5.1.x
- **Wagtail**: 7.2.x
- **Test Status**: Application starts successfully.

### Commands Reference

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f web

# Run Django commands
docker compose exec web python manage.py [command]

# Access Django shell
docker compose exec web python manage.py shell

# Run migrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python manage.py createsuperuser

# Rebuild after code changes
docker compose build web
docker compose restart web
```

## Phase 1.5: Data Ingestion & Testing - UNBLOCKED ✅

**Objective**: Populate the database with real data and verify data import functionality

**Status**: ✅ UNBLOCKED. The upgrade to Django 1.11 has resolved the `RuntimeError: generator raised StopIteration` issue. Data import commands can now be tested.

**Rationale**:
- The application currently has an empty database showing Wagtail welcome page
- Need to test data import commands before major upgrades
- Real data will help validate that Phase 2 upgrades don't break functionality
- Understanding which data sources still work vs. need updates

### Available Import Commands

1. **import_parlparse** - Parliamentary data (MPs, Lords) from ParlParse (Popolo format)
2. **import_ministers** - Ministerial appointments
3. **import_everypolitician** - MP profile images and metadata from EveryPolitician
4. **import_ec** - Electoral Commission donations data (CSV API)
5. **import_appc** - APPC lobbying register (web scraping)
6. **import_twfy** - TheyWorkForYou API (partial implementation)
7. **import_mpsinterests** - MPs' Register of Interests (partial implementation)
8. **import_lordsinterests** - Lords' Register of Interests (partial implementation)
9. **import_companieshouse** - Company metadata (partial implementation)
10. **import_powerbase** - Powerbase wiki data (partial implementation)

### Planned Tasks

1. **Test Core Data Imports** (Priority: High)
   - [x] Test `import_parlparse --since 2010` (primary politician data)
   - [x] Test `import_ministers --since 2010` (ministerial appointments)
   - [x] Test `import_ec` (Electoral Commission donations) - ✅ Working
   - [x] Test `import_appc` (lobbying register) - ✅ Working
   - [x] Develop `import_appc_archive` (historical PDFs) - ✅ Parsing Working
   - [x] Test `import_mpsinterests` (MPs' interests) - ✅ Working
   - [ ] Document which commands work vs. fail
   - [ ] Document any API changes or broken endpoints

2. **Test Secondary Imports** (Priority: Medium)
   - [ ] Test `import_everypolitician` (note: slow, downloads images)
   - [ ] Test `import_twfy` (if API key available)
   - [ ] Test partial implementations (mpsinterests, lordsinterests, etc.)
   - [ ] Identify which need completion vs. deprecation

3. **Fix Broken Imports** (Priority: Medium)
   - [ ] Update any commands with broken external APIs
   - [ ] Fix parsing errors due to changed data formats
   - [ ] Update URL endpoints if sources have moved
   - [ ] Add error handling for missing/changed fields

4. **Create Wagtail Homepage** (Priority: High)
   - [ ] Log into Wagtail admin at /admin/
   - [ ] Create root homepage using MyPage or DataPage model
   - [ ] Add basic content to verify frontend rendering
   - [ ] Configure site settings

5. **Verify Application Functionality**
   - ✅ Test actor detail pages (/person/, /organization/)
   - ✅ Test search functionality (/search/)
   - [ ] Test API endpoints (/api/)
   - [ ] Verify data relationships (donations, memberships, consultancies)

### Testing Strategy

```bash
# Test each import command incrementally
docker compose exec web python manage.py import_parlparse --since 2010
docker compose exec web python manage.py import_ministers --since 2010
docker compose exec web python manage.py import_ec

# Check database population
docker compose exec db psql -U uti -d undertheinfluence -c "SELECT COUNT(*) FROM datafetch_person;"
docker compose exec db psql -U uti -d undertheinfluence -c "SELECT COUNT(*) FROM datafetch_organization;"
docker compose exec db psql -U uti -d undertheinfluence -c "SELECT COUNT(*) FROM datafetch_donation;"

# Test web interface
# Visit http://localhost:8000/person/1/
# Visit http://localhost:8000/search/?search=Cameron
# Visit http://localhost:8000/api/
```

### Recommendation

**Proceed with testing data import commands as originally planned** before moving to the next Django upgrade.

## Phase 2: Django & Wagtail Upgrade - COMPLETE ✅

**Objective**: Upgrade from Django 1.8 → 6.0.1 and Wagtail 1.1 → 7.2

**Status**: The full upgrade to Django 6.0.1 and Wagtail 7.2.x is complete and stable.

### Investigation & Recovery (January 12, 2026)

Upon review, it was discovered that an upgrade to Django 1.11 and Wagtail 2.0 had been started but was left incomplete, causing the application to fail at startup. The following fixes were implemented to stabilize the environment:

1.  **Dependency Analysis**:
    - `requirements.txt` showed `Django>=1.11` and `wagtail>=2.0`, but contained an incompatible `djangorestframework==3.6.4`.
    - ✅ **Action**: Upgraded `djangorestframework` to `3.7.7` for Django 1.11 compatibility.

2.  **Settings Configuration**:
    - `undertheinfluence/settings.py` was still using the deprecated `MIDDLEWARE_CLASSES` setting from Django 1.8.
    - ✅ **Action**: Migrated to the new `MIDDLEWARE` setting, which is required for Django 1.10+.

3.  **Verification**:
    - ✅ Rebuilt the Docker container to install the corrected dependencies.
    - ✅ Ran `docker compose exec web python manage.py migrate` successfully.
    - ✅ Restarted the web container and confirmed that the application starts without any system check errors.

**Conclusion**: The application is now stable on Django 1.11.29 and Wagtail 2.0. The original blocker for Phase 1.5 is resolved.

### Frontend Rendering Findings (January 12, 2026)

-   **ActorView Functionality**: The `datafetch.views.ActorView` dynamically renders templates (`person.html` for `Person` objects and `organization.html` for `Organization` objects) based on the specific subclass of the `Actor` being displayed. This ensures appropriate UI presentation for different types of entities.
-   **URL Pattern Clarification**: The correct URL pattern for accessing individual person or organization detail pages is `/person/<pk>/` or `/organization/<pk>/`, respectively, where `<pk>` is the primary key of the `Actor` object. This avoids issues where Wagtail might incorrectly intercept requests due to malformed URLs.

### Frontend Rendering Fixes and Verification (January 12, 2026)

-   **Template Tag Issues**: Resolved `TemplateSyntaxError: 'wagtail_tags' is not a registered tag library` by replacing `wagtail_tags` with `wagtailcore_tags` or `wagtailimages_tags` in all affected templates (`cms/templates/cms/data_page.html`, `cms/templates/cms/my_page.html`, `cms/templates/cms/tags/nav.html`, `cms/templates/cms/tags/top_menu_children.html`, `cms/templates/cms/tags/top_menu.html`, `cms/templates/cms/snippets/quote.html`, `cms/templates/cms/snippets/analysis.html`, `cms/templates/cms/snippets/profile.html`). A full container rebuild was necessary to clear template caches.
-   **Date Field `TypeError`**: Resolved `TypeError: object of type 'NoneType' has no len()` in `datafetch/models/popolo/behaviors.py` by adding explicit `None` checks before calling `len()` on `self.start_date` and `self.end_date` in the `start_datetime` and `end_datetime` properties.
-   **Verification**:
    -   ✅ Person detail pages (`/person/<pk>/`) are rendering correctly.
    -   ✅ Organization detail pages (`/organization/<pk>/`) are rendering correctly.
    -   ✅ Search functionality (`/search/?q=...`) is working and displaying results.
    -   ✅ Wagtail admin (`/admin/`) is accessible and redirecting to the login page as expected.

### Django 6.0.1 and Wagtail 7.2 Upgrade (January 13, 2026)

The project has been successfully upgraded through multiple intermediate versions to Django 6.0.1 and Wagtail 7.2.x. This involved:

1.  **Python Version Upgrade**: Updated Dockerfile to use Python 3.12 (from 3.7) for compatibility with Django 6.x.
2.  **Incremental Django Upgrades**:
    -   From Django 3.2.x to Django 4.0.x.
    -   From Django 4.0.x to Django 4.1.x.
    -   From Django 4.1.x to Django 4.2.x LTS.
    -   From Django 4.2.x LTS to Django 5.0.x.
    -   From Django 5.0.x to Django 5.1.x.
    -   From Django 5.1.x to Django 6.0.x.
3.  **Incremental Wagtail Upgrades**:
    -   From Wagtail 2.15.x to Wagtail 3.0.x.
    -   From Wagtail 3.0.x to Wagtail 4.0.x.
    -   From Wagtail 4.0.x to Wagtail 4.2.x.
    -   From Wagtail 4.2.x to Wagtail 7.2.x (resolved by pip).
4.  **Dependency Resolution**:
    -   Removed `django-bower` as it's incompatible with Django 2.0+.
    -   Upgraded `django-modelcluster` to `6.x` for Wagtail 3.0+ compatibility.
    -   Upgraded `djangorestframework` to `3.15.x` for Django 4.2+ compatibility.
    -   Upgraded `django-filter` to `23.3` for Wagtail 7.2.x compatibility.
    -   Upgraded `django-polymorphic` to `4.2.x` for Django 6.0+ / Python 3.12+ compatibility.
5.  **Codebase Adaptations**:
    -   Updated Wagtail import paths (`wagtail.core` to `wagtail`, `wagtail.admin.edit_handlers` to `wagtail.admin.panels`) in `cms/models.py` and `undertheinfluence/urls.py`.
    -   Replaced deprecated `StreamFieldPanel`, `SnippetChooserPanel`, and `ImageChooserPanel` with `FieldPanel` in `cms/models.py`.
    -   Added explicit `use_json_field=True` to `StreamField` definition in `cms/models.py`.
    -   Imported `register_snippet` explicitly in `cms/models.py`.
6.  **Migration Handling**:
    -   Applied necessary core migrations after each major framework upgrade.
    -   Patched `cms/migrations/0001_initial.py` temporarily to resolve `ModuleNotFoundError: No module named 'wagtail.core'` during migration loading. This patch was kept to maintain application functionality.
    -   Generated and applied new migrations for `cms` and `datafetch` apps (`cms/migrations/0002_alter_analysis_body.py`, `datafetch/migrations/0002_alter_actor_options_alter_organization_options_and_more.py`, `datafetch/migrations/0003_alter_actor_options_alter_organization_options.py`).
7.  **Database Connection Fix**: Explicitly set the database `NAME` to `'undertheinfluence'` in `undertheinfluence/settings.py` to resolve `fatal: database 'uti' does not exist` error.

**Conclusion**: The project is now running on a modern and supported stack, setting the stage for further development and improved stability.

### Next Steps in Phase 2

**Status**: Phase 2 (Django & Wagtail Upgrade) is now COMPLETE ✅.

The next steps in the modernization roadmap are:

1.  **Phase 2.5: Frontend Modernization** - PENDING
2.  **Phase 3: Code Modernization** - PENDING
3.  **Phase 4: Elasticsearch Integration** - PENDING


## Phase 2.5: Frontend Modernization - PENDING

**Objective**: Replace django-bower with modern frontend tools

**Status**: Not started

## Phase 3: Code Modernization - PENDING

**Objective**: Clean up deprecated patterns and improve code quality

**Status**: Not started

## Phase 4: Elasticsearch Integration - PENDING

**Objective**: Add Elasticsearch for improved search functionality

**Status**: Not started

## Issues Encountered & Resolved

### Issue 1: Python 3.11 Incompatibility
- **Error**: `ImportError: cannot import name 'Iterator' from 'collections'`
- **Cause**: Python 3.10+ moved Iterator from collections to collections.abc
- **Resolution**: Downgraded to Python 3.9, then further to 3.7

### Issue 2: django-modelcluster RuntimeError
- **Error**: `RuntimeError: __class__ not set defining 'ClusterableModel'`
- **Cause**: django-modelcluster 0.6.2 incompatible with Python 3.8+
- **Resolution**: Downgraded to Python 3.7

### Issue 3: pytest-django Version Conflict
- **Error**: No version satisfying pytest-django==4.7.0
- **Cause**: pytest-django 4.7.0 requires Python 3.8+
- **Resolution**: Pinned to pytest-django==4.5.2

### Issue 4: Django REST Framework Incompatibility
- **Error**: `ModuleNotFoundError: No module named 'django.urls'`
- **Cause**: DRF 3.10.3 expects Django 1.11+ (django.urls introduced in 1.11)
- **Resolution**: Pinned to djangorestframework==3.6.4

### Issue 5: PostgreSQL Timezone Configuration
- **Error**: `AssertionError: database connection isn't set to UTC`
- **Cause**: Django 1.8's postgresql_psycopg2 backend requires database timezone to be UTC
- **Initial attempts**:
  - Added `OPTIONS: {'options': '-c timezone=utc'}` to DATABASES settings (didn't work)
  - Added `TZ=UTC` and `PGTZ=UTC` environment variables to docker-compose.yml (didn't work)
  - Added `command: postgres -c timezone=UTC` to docker-compose.yml (didn't work)
- **Final resolution**:
  - Executed `ALTER DATABASE undertheinfluence SET timezone TO 'UTC';` at PostgreSQL level
  - This persisted the timezone setting at the database level
  - Restarted web container and timezone issue resolved

## Notes

- All security vulnerabilities in Phase 1 scope have been addressed
- The application is now fully containerized and ready for incremental upgrades
- Database uses PostgreSQL 15 (production-grade setup)
- Redis 7 configured for caching (ready for use in later phases)
- Python 3.10 is used for current compatibility.
- Will upgrade to Python 3.11+ in Phase 2.5 alongside further Django/Wagtail upgrades.

## Next Steps

1.  **Phase 1.5: Data Ingestion**
    - [ ] Test all data import commands to determine functionality.
    - [ ] Create Wagtail homepage via admin interface.
    - [ ] Populate database with real UK political data.
    - [ ] Document which data sources still work.
    - [ ] Fix any broken import commands.

2.  **Phase 2: Django/Wagtail Upgrade (Continued)**
    - [ ] Once data ingestion is validated, proceed with the upgrade from Django 1.11 to 2.2.
