# Data Import Testing - Phase 1.5

This document tracks the testing and status of all data import commands.

**Date Started**: January 12, 2026
**Environment**: Docker (Python 3.7, Django 1.11.29, PostgreSQL 15)

## Testing Progress

### Priority 1: Core Data Imports

#### 1. import_parlparse
**Purpose**: Import MPs and Lords from ParlParse (Popolo format JSON)
**Status**: ✅ Working
**Command**: `docker compose exec web python manage.py import_parlparse --since 2010`

**Expected data**:
- Person records (MPs, Lords)
- Memberships (constituency, party affiliations)
- Posts (parliamentary positions)

**Notes**:
- Primary data source for politicians
- Uses Popolo standard format
- **FIXED (Jan 12, 2026)**: Added `name` and `source` to `ignore_fields` in `_process_memberships` to handle unexpected fields in the JSON source.

---

#### 2. import_ministers
**Purpose**: Import ministerial appointments
**Status**: ✅ Working
**Command**: `docker compose exec web python manage.py import_ministers --since 2010`

**Expected data**:
- Ministerial roles and appointments
- Government positions
- Date ranges for appointments

**Notes**:
- Complements parlparse data
- Links ministers to their roles
- **FIXED (Jan 12, 2026)**: Updated defunct `cdn.rawgit.com` URL to `raw.githubusercontent.com`.

---

#### 3. import_ec
**Purpose**: Import Electoral Commission donations (CSV API)
**Status**: ⛔ BROKEN
**Command**: `docker compose exec web python manage.py import_ec`

**Expected data**:
- Political donations
- Donor and recipient information
- Donation amounts and dates

**Notes**:
- **BROKEN (Jan 12, 2026)**: The old CSV API endpoint `http://search.electoralcommission.org.uk/api/csv/Donations` is defunct and returns only headers. The Electoral Commission now uses an interactive search portal at `https://search.electoralcommission.org.uk/Search/Donations?...`. A complete rewrite of the importer is necessary to adapt to this new data retrieval method.

---

#### 4. import_appc
**Purpose**: Import APPC lobbying register (web scraping)
**Status**: ⛔ BROKEN
**Command**: `docker compose exec web python manage.py import_appc`

**Expected data**:
- Lobbying consultancies
- Client-agency relationships
- Lobbyist organizations

**Notes**:
- **BROKEN (Jan 12, 2026)**: The website `appc.org.uk` is defunct. The APPC merged with the PRCA in 2018. The new data source is the PRCA Public Affairs Register (e.g., `https://prca.org.uk/register/prca-public-affairs-and-lobbying-register/`). The importer needs to be rewritten to scrape this new source.

---

### Priority 2: Enrichment Data

#### 5. import_everypolitician
**Purpose**: Import MP photos and metadata from EveryPolitician
**Status**: ⏸️ Not tested yet
**Command**: `docker compose exec web python manage.py import_everypolitician`

**Expected data**:
- Profile images for MPs
- Additional metadata

**Notes**:
- **WARNING**: Very slow (downloads many large images)
- Should run after import_parlparse
- May want to skip for initial testing
- **LIKELY BROKEN**: Uses `cdn.rawgit.com` URL.

---

#### 6. import_twfy
**Purpose**: Import data from TheyWorkForYou API
**Status**: ⏸️ Not tested yet (partial implementation)
**Command**: `docker compose exec web python manage.py import_twfy`

**Expected data**:
- MP voting records (potentially)
- Parliamentary activity

**Notes**:
- Requires TWFY_API_KEY in environment
- Implementation may be incomplete
- Check if API still compatible

---

### Priority 3: Partial Implementations

#### 7. import_mpsinterests
**Purpose**: Import MPs' Register of Interests
**Status**: ⏸️ Not tested yet (partial implementation)
**Command**: `docker compose exec web python manage.py import_mpsinterests`

**Notes**:
- May only fetch data, not parse/import
- Check implementation status

---

#### 8. import_lordsinterests
**Purpose**: Import Lords' Register of Interests
**Status**: ⏸️ Not tested yet (partial implementation)
**Command**: `docker compose exec web python manage.py import_lordsinterests`

**Notes**:
- May only fetch data, not parse/import
- Check implementation status

---

#### 9. import_companieshouse
**Purpose**: Import company metadata from Companies House
**Status**: ⏸️ Not tested yet (partial implementation)
**Command**: `docker compose exec web python manage.py import_companieshouse`

**Notes**:
- May require Companies House API key
- Check implementation status

---

#### 10. import_powerbase
**Purpose**: Import data from Powerbase wiki
**Status**: ⏸️ Not tested yet (partial implementation)
**Command**: `docker compose exec web python manage.py import_powerbase`

**Notes**:
- Powerbase wiki may have changed or moved
- Check implementation status

---

## Testing Checklist

### Pre-Import Setup
- [x] Database timezone configured (UTC)
- [x] Admin user created (username: admin)
- [x] Migrations applied
- [ ] Check environment variables needed (TWFY_API_KEY, etc.)
- [x] Verify `data/` directory is writable

### Test Sequence

**Recommended order**:

1. `import_parlparse --since 2010` (foundation data - MPs/Lords)
2. `import_ministers --since 2010` (adds ministerial roles)
3. `import_ec` (donations data)
4. `import_appc` (lobbying data)
5. Verify data in admin and web interface
6. `import_everypolitician` (if needed for photos)
7. Test remaining commands as needed

### Validation Queries

After each import, check database:

```bash
# Count records
docker compose exec db psql -U uti -d undertheinfluence -c "
  SELECT
    (SELECT COUNT(*) FROM datafetch_person) as persons,
    (SELECT COUNT(*) FROM datafetch_organization) as organizations,
    (SELECT COUNT(*) FROM datafetch_membership) as memberships,
    (SELECT COUNT(*) FROM datafetch_donation) as donations,
    (SELECT COUNT(*) FROM datafetch_consultancy) as consultancies;
"

# Sample data
docker compose exec db psql -U uti -d undertheinfluence -c "
  SELECT id, name FROM datafetch_person ORDER BY id LIMIT 5;
"
```

### Web Interface Testing

After imports:
- [ ] Visit http://localhost:8000/ (homepage)
- [ ] Visit http://localhost:8000/person/1/ (person detail)
- [ ] Visit http://localhost:8000/search/?search=test (search)
- [ ] Visit http://localhost:8000/api/ (API)
- [ ] Check Wagtail admin at http://localhost:8000/admin/

---

## Issues Found

*Document any errors, API changes, or broken functionality here as testing progresses*

### `import_parlparse` - FieldError on Membership
**Date**: 2026-01-12
**Error**: `django.core.exceptions.FieldError: Invalid field name(s) for model Membership: 'name'` and `'source'`
**Cause**: The source Popolo JSON contains `name` and `source` fields on membership objects, which are not present on the `Membership` model.
**Status**: Fixed
**Resolution**: Added `'name'` and `'source'` to the `ignore_fields` tuple in the `_process_memberships` function of the `import_parlparse` command.

### `import_ec` - Empty CSV
**Date**: 2026-01-12
**Error**: The command runs without error, but no donations are imported.
**Cause**: The API at `http://search.electoralcommission.org.uk/api/csv/Donations` now returns a CSV file with only a header row and no data. The Electoral Commission website has a new "Political Finance Online" portal, and the old API endpoint appears to be defunct.
**Status**: Open
**Resolution**: The `import_ec` command needs to be completely rewritten to work with the new data portal. This is a significant task and is deferred for now.

### `import_appc` - Connection Refused
**Date**: 2026-01-12
**Error**: `requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))`
**Cause**: The target website `http://www.appc.org.uk/` is defunct. The APPC merged with the PRCA in 2018.
**Status**: Open
**Resolution**: The `import_appc` command needs to be rewritten to scrape the new PRCA Public Affairs Register. This is a significant task and is deferred for now.

---

## Data Sources Status

Track which external data sources are still available:

| Source | URL | Status | Notes |
|--------|-----|--------|-------|
| ParlParse | https://raw.githubusercontent.com/mysociety/parlparse/master/members/people.json | ✅ Working | Popolo JSON endpoint. URL was updated from `cdn.rawgit.com`. |
| Electoral Commission | https://www.electoralcommission.org.uk/ | ⛔ Broken | The old CSV API endpoint is defunct. New portal requires a new scraper. |
| APPC | https://prca.org.uk/register/prca-public-affairs-and-lobbying-register/ | ⛔ Broken | The original `appc.org.uk` is defunct; merged with PRCA. Needs new scraper. |
| EveryPolitician | https://everypolitician.org/ | ❓ Unknown | May be archived. Uses `cdn.rawgit.com` and is likely broken. |
| TheyWorkForYou | https://www.theyworkforyou.com/api/ | ❓ Unknown | Requires API key |
| Companies House | https://developer.company-information.service.gov.uk/ | ❓ Unknown | API v3+ |
| Powerbase | http://powerbase.info/ | ❓ Unknown | Wiki-based |

---

## Success Criteria

Phase 1.5 will be considered complete when:

- [x] All Priority 1 import commands tested
- [x] At least 2 Priority 1 commands working with data imported
- [ ] Wagtail homepage created and accessible
- [ ] Person and organization detail pages rendering with real data
- [ ] Search functionality working
- [ ] API endpoints returning real data
- [x] Documentation updated with working vs. broken imports
- [x] Known issues documented with workarounds or fixes
