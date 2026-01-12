# UnderTheInfluence Modernization Progress

This document tracks the progress of modernizing the UnderTheInfluence Django application from Django 1.8/Wagtail 1.1 to modern versions.

## Overview

- **Start Date**: January 12, 2026
- **Current Phase**: Ready for Phase 2 ⚠️
- **Current Branch**: review-status
- **Phase 1 (Docker Foundation)**: COMPLETED ✅
- **Phase 1.5 (Data Ingestion)**: BLOCKED ⛔ (see findings below)
- **Recommendation**: Skip to Phase 2 (Django Upgrade)

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
- **Python**: 3.7
- **Django**: 1.8.19
- **Wagtail**: 1.1
- **Test Status**: Manual test passed - default Wagtail page displays

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

## Phase 1.5: Data Ingestion & Testing - BLOCKED ⛔

**Objective**: Populate the database with real data and verify data import functionality

**Status**: ⛔ BLOCKED by critical Python 3.7 + Django 1.8 incompatibility

**See**: `docs/phase-1-5-findings.md` for detailed analysis

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
   - [ ] Test `import_parlparse --since 2010` (primary politician data)
   - [ ] Test `import_ministers --since 2010` (ministerial appointments)
   - [ ] Test `import_ec` (Electoral Commission donations)
   - [ ] Test `import_appc` (lobbying register)
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
   - [ ] Test actor detail pages (/person/, /organization/)
   - [ ] Test search functionality (/search/)
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

### Critical Blocker Discovered

**Python 3.7 + Django 1.8 ORM Incompatibility**:
- Python 3.7 implemented PEP 479 (StopIteration handling in generators)
- Django 1.8's ORM predates this change and breaks with `RuntimeError: generator raised StopIteration`
- Affects ALL database queries using `.get()`, `.get_or_create()`, etc.
- Cannot be easily patched without modifying Django core
- **Resolution**: Must upgrade to Django 1.11+ which supports Python 3.7

### Issues Fixed

✅ **RawGit CDN Shutdown**: Updated `import_parlparse` to use `raw.githubusercontent.com`
✅ **Name Field Length**: Increased Person name fields from 128 to 512 characters
✅ **PostgreSQL Timezone**: Monkey-patched Django 1.8's timezone check

### Issues Discovered (Not Yet Testable)

- External API availability and rate limits - ❓ Unknown (blocked by ORM issue)
- Data format changes since 2015 - ❓ Unknown (blocked by ORM issue)
- Missing or deprecated data sources - ❓ Unknown (blocked by ORM issue)

### Recommendation

**Skip Phase 1.5 and proceed to Phase 2 immediately**. Data imports can be tested after Django 1.11 upgrade when Python 3.7 compatibility is restored.

## Phase 2: Django & Wagtail Upgrade - PENDING

**Objective**: Upgrade from Django 1.8 → 5.1 and Wagtail 1.1 → 7.2

**Status**: Not started

**Planned Tasks**:
- Incremental Django upgrades (1.8 → 1.11 → 2.2 → 3.2 → 4.2 → 5.1)
- Wagtail upgrade to match Django versions
- Fix deprecated API usage
- Update URL patterns
- Migrate middleware configuration
- Update template tags
- Fix model changes

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
- Python 3.7 is end-of-life (2023-06-27) but necessary for legacy compatibility
- Will upgrade to Python 3.11+ in Phase 2 alongside Django upgrade

## Next Steps

1. **Phase 1.5: Data Ingestion** (Current)
   - Test all data import commands to determine functionality
   - Create Wagtail homepage via admin interface
   - Populate database with real UK political data
   - Document which data sources still work
   - Fix broken import commands

2. **Phase 2: Django/Wagtail Upgrade** (After data validation)
   - Plan incremental upgrade strategy
   - Set up automated testing with populated database
   - Begin Django 1.8 → 1.11 upgrade
