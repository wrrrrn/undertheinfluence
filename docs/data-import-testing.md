# Data Import Testing - Phase 1.5

This document tracks the testing and status of all data import commands.

**Date Started**: January 12, 2026
**Environment**: Docker (Python 3.7, Django 1.8, PostgreSQL 15)

## Testing Progress

### Priority 1: Core Data Imports

#### 1. import_parlparse
**Purpose**: Import MPs and Lords from ParlParse (Popolo format JSON)
**Status**: ⏸️ Not tested yet
**Command**: `docker compose exec web python manage.py import_parlparse --since 2010`

**Expected data**:
- Person records (MPs, Lords)
- Memberships (constituency, party affiliations)
- Posts (parliamentary positions)

**Notes**:
- Primary data source for politicians
- Uses Popolo standard format
- Caches to `data/` directory

---

#### 2. import_ministers
**Purpose**: Import ministerial appointments
**Status**: ⏸️ Not tested yet
**Command**: `docker compose exec web python manage.py import_ministers --since 2010`

**Expected data**:
- Ministerial roles and appointments
- Government positions
- Date ranges for appointments

**Notes**:
- Complements parlparse data
- Links ministers to their roles

---

#### 3. import_ec
**Purpose**: Import Electoral Commission donations (CSV API)
**Status**: ⏸️ Not tested yet
**Command**: `docker compose exec web python manage.py import_ec`

**Expected data**:
- Political donations
- Donor and recipient information
- Donation amounts and dates

**Notes**:
- Large dataset, may be slow
- CSV format from EC API
- Core feature for tracking political influence

---

#### 4. import_appc
**Purpose**: Import APPC lobbying register (web scraping)
**Status**: ⏸️ Not tested yet
**Command**: `docker compose exec web python manage.py import_appc`

**Expected data**:
- Lobbying consultancies
- Client-agency relationships
- Lobbyist organizations

**Notes**:
- Web scraping based (may break if site structure changed)
- APPC website structure may have changed since 2015
- Core feature for lobbying transparency

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
- [ ] Verify `data/` directory is writable

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

### Issue Template
```
### [Command Name] - [Issue Summary]
**Date**: YYYY-MM-DD
**Error**: [Error message or description]
**Cause**: [Root cause if identified]
**Status**: [Open/Fixed/Workaround]
**Resolution**: [How it was fixed or worked around]
```

---

## Data Sources Status

Track which external data sources are still available:

| Source | URL | Status | Notes |
|--------|-----|--------|-------|
| ParlParse | https://www.theyworkforyou.com/ | ❓ Unknown | Popolo JSON endpoint |
| Electoral Commission | https://www.electoralcommission.org.uk/ | ❓ Unknown | CSV API |
| APPC | http://www.appc.org.uk/ | ❓ Unknown | Web scraping |
| EveryPolitician | https://everypolitician.org/ | ❓ Unknown | May be archived |
| TheyWorkForYou | https://www.theyworkforyou.com/api/ | ❓ Unknown | Requires API key |
| Companies House | https://developer.company-information.service.gov.uk/ | ❓ Unknown | API v3+ |
| Powerbase | http://powerbase.info/ | ❓ Unknown | Wiki-based |

---

## Success Criteria

Phase 1.5 will be considered complete when:

- [ ] All Priority 1 import commands tested
- [ ] At least 2 Priority 1 commands working with data imported
- [ ] Wagtail homepage created and accessible
- [ ] Person and organization detail pages rendering with real data
- [ ] Search functionality working
- [ ] API endpoints returning real data
- [ ] Documentation updated with working vs. broken imports
- [ ] Known issues documented with workarounds or fixes
