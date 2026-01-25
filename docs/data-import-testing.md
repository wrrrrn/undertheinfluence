# Data Import Testing

This document tracks the status of all data import commands.

**Last Updated**: January 22, 2026
**Environment**: Docker (Python 3.12, Django 6.0.1, Wagtail 7.2.x, PostgreSQL 15)

---

## Import Status Summary

| Command | Status | Records | Notes |
|---------|--------|---------|-------|
| `import_parlparse` | Working | ~4,700 persons | MPs and Lords foundation data |
| `import_ministers` | Working | ~10,000 memberships | Ministerial appointments |
| `import_mpsinterests` | Working | ~45,000 donations | MPs' Register of Interests |
| `import_ministerial_meetings` | Working | ~41,000 meetings | GOV.UK transparency data |
| `enrich_companies_house` | Working | ~15,600 matches | Company data enrichment |
| `import_appc` | Working | - | PRCA current lobbying register |
| `import_ec` | Broken | - | Electoral Commission API changed |
| `import_everypolitician` | Broken | - | Uses defunct cdn.rawgit.com |
| `import_twfy` | Partial | - | Requires API key, network issues |
| `import_lordsinterests` | Working | ~418 interests | Lords' Register of Interests |

---

## Working Imports

### 1. import_parlparse
**Purpose**: Import MPs and Lords from ParlParse (Popolo format JSON)
**Status**: Working
**Command**: `docker compose exec api python manage.py import_parlparse --since 2010`

Foundation data - must run first before other imports.

---

### 2. import_ministers
**Purpose**: Import ministerial appointments
**Status**: Working
**Command**: `docker compose exec api python manage.py import_ministers --since 2010`

Links ministers to their roles with date ranges.

---

### 3. import_mpsinterests
**Purpose**: Import MPs' Register of Interests
**Status**: Working
**Command**: `docker compose exec api python manage.py import_mpsinterests --since 1996`

Maps Category 2 and 3 interests to Donation models.

---

### 4. import_ministerial_meetings
**Purpose**: Import ministerial meetings from GOV.UK transparency data
**Status**: Working
**Command**: `docker compose exec api python manage.py import_ministerial_meetings --department all --since 2024`

**Results (January 2026)**:
- 41,362 meetings imported
- 23 departments covered
- 26,183 individual attendees tracked via MeetingAttendee records

See `docs/MINISTERIAL_MEETINGS_PHASE3_COMPLETE.md` for full details.

---

### 5. enrich_companies_house
**Purpose**: Match and enrich organizations with Companies House data
**Status**: Working
**Command**: `docker compose exec api python manage.py enrich_companies_house --category lobbying_agency`

**Categories**:
- `lobbying_agency` - PRCA lobbying agencies (~217)
- `lobbying_client` - Lobbying clients (~18,600)
- `donor` - Donation donors (~21,400)

**Current Progress** (January 22, 2026):
| Category | Total | Auto-Approved | Pending | Not Found | Remaining |
|----------|-------|---------------|---------|-----------|-----------|
| lobbying_agency | 217 | 196 | 0 | 21 | 0 |
| lobbying_client | 18,635 | 5,500 | 2,929 | 1 | 10,107 |
| donor | 21,414 | 1,980 | 1,518 | 0 | 17,916 |

Requires `COMPANIES_HOUSE_API_KEY` in `.env`.

---

### 6. import_lordsinterests
**Purpose**: Import Lords' Register of Interests
**Status**: Working
**Command**: `docker compose exec api python manage.py import_lordsinterests`

Uses JSON API from data.parliament.uk.

---

### 7. import_appc
**Purpose**: Import PRCA lobbying register (Current)
**Status**: Working
**Command**: `docker compose exec api python manage.py import_appc`

Scrapes the current live register from prca.org.uk.

---

## Broken Imports

### import_ec
**Purpose**: Import Electoral Commission donations
**Status**: Broken
**Issue**: Electoral Commission CSV API has changed or requires different parameters.

Needs investigation and fix.

---

### import_everypolitician
**Purpose**: Import MP photos and metadata
**Status**: Broken
**Issue**: Uses defunct `cdn.rawgit.com` URL.

---

## Partial/Untested Imports

### import_twfy
**Purpose**: Enrich MPs with TheyWorkForYou data (URLs, DOB, images)
**Status**: Partial
**Issue**: Requires `TWFY_API_KEY` in `.env`. May fail on large imports due to network issues.

---

### import_companieshouse
**Purpose**: Legacy company import
**Status**: Superseded
**Note**: Use `enrich_companies_house` instead for confidence-based matching.

---

### import_powerbase
**Purpose**: Import data from Powerbase wiki
**Status**: Untested

---

## Recommended Import Sequence

```bash
# 1. Foundation data (required)
docker compose exec api python manage.py import_parlparse --since 2010
docker compose exec api python manage.py import_ministers --since 2010

# 2. Financial interests
docker compose exec api python manage.py import_mpsinterests --since 1996
docker compose exec api python manage.py import_lordsinterests

# 3. Ministerial meetings
docker compose exec api python manage.py import_ministerial_meetings --department all --since 2020

# 4. Companies House enrichment (requires API key)
docker compose exec api python manage.py enrich_companies_house --category lobbying_agency
docker compose exec api python manage.py enrich_companies_house --category lobbying_client --batch-size 500
docker compose exec api python manage.py enrich_companies_house --category donor --batch-size 500
```

---

## Validation Query

```bash
docker compose exec -T db psql -U uti -d undertheinfluence -c "
SELECT
  (SELECT COUNT(*) FROM datafetch_person) as persons,
  (SELECT COUNT(*) FROM datafetch_organization) as organizations,
  (SELECT COUNT(*) FROM datafetch_membership) as memberships,
  (SELECT COUNT(*) FROM datafetch_donation) as donations,
  (SELECT COUNT(*) FROM datafetch_consultancy) as consultancies,
  (SELECT COUNT(*) FROM datafetch_ministerialmeeting) as meetings,
  (SELECT COUNT(*) FROM datafetch_companieshousematch) as ch_matches;
"
```

---

## Data Sources

| Source | Status | Notes |
|--------|--------|-------|
| ParlParse (GitHub) | Working | Popolo JSON |
| GOV.UK Transparency | Working | Ministerial meetings CSV |
| Companies House API | Working | Requires API key |
| MPs' Register (Parliament) | Working | HTML scraping |
| Lords' Register (Parliament) | Working | JSON API |
| Electoral Commission | Broken | API changed |
| APPC/PRCA | Broken | Site defunct |
| EveryPolitician | Broken | CDN defunct |
| TheyWorkForYou | Partial | Requires API key |
