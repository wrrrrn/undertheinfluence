# Data Import Guide

Comprehensive guide for importing political influence data into UnderTheInfluence.

## Quick Start

### Full Import from 1996

```bash
# Run the automated import script
./scripts/full_data_import.sh
```

This will:
1. Wipe the database (with confirmation)
2. Run migrations
3. Import ParlParse data (MPs, Lords, memberships) from 1996
4. Import Ministers data from 1996
5. Optionally import TheyWorkForYou biographical data (if API key set)
6. Import MPs' Register of Interests from 1996
7. Import Lords' Register of Interests
8. Import APPC Archive (historical lobbying registers)
9. Run entity resolution to identify duplicates
10. Display statistics

### Options

```bash
# Skip database wipe (append to existing data)
./scripts/full_data_import.sh --skip-wipe

# Quick mode (skip entity resolution)
./scripts/full_data_import.sh --quick

# Both options
./scripts/full_data_import.sh --skip-wipe --quick
```

### View Import Statistics

```bash
# Show current database statistics (without running imports)
./scripts/import_stats.sh
```

This displays:
- Record counts (Persons, Organizations, Memberships, Donations, Consultancies)
- Organization breakdown by classification
- Duplicate detection counts
- Entity resolution status
- Identifier schemes and counts

## Manual Import Commands

If you need more control, run imports individually:

### 1. ParlParse (MPs & Lords)

```bash
# Import all data from 1996 onwards
docker compose exec api python manage.py import_parlparse --since 1996 --refresh

# Import all data (no date filter)
docker compose exec api python manage.py import_parlparse --refresh

# Append new data without refreshing cache
docker compose exec api python manage.py import_parlparse --since 2020
```

**What it imports:**
- Persons (MPs and Lords)
- Organizations (parties, government departments)
- Posts (parliamentary seats, ministerial positions)
- Memberships (linking persons to organizations/posts)

**Data Source:** [ParlParse GitHub](https://github.com/mysociety/parlparse)

### 2. Ministers

```bash
# Import ministerial appointments from 1996
docker compose exec api python manage.py import_ministers --since 1996 --refresh

# Import all ministerial data
docker compose exec api python manage.py import_ministers --refresh
```

**What it imports:**
- Ministerial appointments
- Government positions
- Organizational roles

**Data Source:** [ParlParse Ministers](https://github.com/mysociety/parlparse/tree/master/members)

### 3. TheyWorkForYou (Optional)

```bash
# Requires TWFY_API_KEY in .env
docker compose exec api python manage.py import_twfy --since 1996 --refresh
```

**What it imports:**
- MP biographical data (Wikipedia links, BBC profiles, MP websites)
- Profile images
- Birth dates
- Additional person metadata

**Setup:**
1. Get API key from [TheyWorkForYou](https://www.theyworkforyou.com/api/)
2. Add to `.env`: `TWFY_API_KEY=your_key_here`

**Validation Status:** ⏳ Pending
- Identifier matching bug fixed (2026-01-14)
- Full validation pending API rate limit reset
- See [IMPORT_VALIDATION_STATUS.md](IMPORT_VALIDATION_STATUS.md#-import_twfy-pending-validation) for details

**Note:** Test with `--since 2024` first to reduce API calls

### 4. MPs' Register of Interests

```bash
# Import MPs' donations, gifts, and interests from 1996
docker compose exec api python manage.py import_mpsinterests --since 1996 --refresh

# Import all available data
docker compose exec api python manage.py import_mpsinterests --refresh
```

**What it imports:**
- Donations to MPs
- Gifts received by MPs
- Sponsored visits and hospitality
- Financial interests

**Data Source:** [TheyWorkForYou MPs' Interests](https://www.theyworkforyou.com/pwdata/scrapedxml/regmem/)

**Note:** Requires persons to exist first (run `import_parlparse` first)

### 5. Lords' Register of Interests

```bash
# Import Lords' donations and interests
docker compose exec api python manage.py import_lordsinterests --refresh
```

**What it imports:**
- Sponsorships to Lords
- Overseas visits
- Gifts to Lords
- Financial interests

**Data Source:** [Parliament Data Platform](https://data.parliament.uk/membersdataplatform/)

**Note:** No date filtering available - imports all current data

### 6. Ministerial Meetings (GOV.UK Transparency Data)

```bash
# Auto-discover and import all publications since 2024
docker compose exec api python manage.py import_ministerial_meetings \
    --department DSIT --since 2024 --auto

# Import specific department with auto-discovery
docker compose exec api python manage.py import_ministerial_meetings \
    --department DBT --since 2024 --auto

# Import from specific URL (CSV or XLSX)
docker compose exec api python manage.py import_ministerial_meetings \
    --url https://assets.publishing.service.gov.uk/... \
    --department DSIT --quarter "Q1 2024"

# Dry run (parse without saving)
docker compose exec api python manage.py import_ministerial_meetings \
    --department DSIT --since 2024 --auto --dry-run
```

**What it imports:**
- Ministerial meetings with external organizations/individuals
- Minister and department associations
- Meeting dates, purposes, and locations
- Entity resolution for external actors

**Data Source:** [GOV.UK Transparency Publications](https://www.gov.uk/government/collections)

**Coverage:** 23 departments imported (41,362 meetings):
- BEIS (7,332), DfT (4,332), DHSC (3,917), DBT (3,642)
- Home Office (2,469), DESNZ (2,305), DCMS (2,254), DSIT (2,047)
- MHCLG (2,033), DWP (1,926), MoJ (1,619), Defra (1,440)
- DfE (1,109), Cabinet Office (1,034), HMT (1,013), NIO (910)
- FCDO (597), FCO (481), BIS (403), MoD (305)
- Wales Office (146), DECC (41), UKEF (7)

**Note:** Uses `--auto` flag to scrape GOV.UK collection pages and auto-discover quarterly publications. DCMS was imported manually via individual CSV files (no collection URL).

**Remaining departments:**
- DFID, DIT - have collection URLs but scraper found 0 downloadable files (needs investigation)
- AGO, SO, OAG - publish quarterly returns but lack collection pages (manual import required)

### 7. APPC Archive (Historical Lobbying Registers)

```bash
# Import historical APPC lobbying registers from PDFs
docker compose exec api python manage.py import_appc_archive --refresh

# Process a specific PDF file
docker compose exec api python manage.py import_appc_archive --file /path/to/register.pdf

# Dry run (parse without saving to database)
docker compose exec api python manage.py import_appc_archive --dry-run
```

**What it imports:**
- Lobbying agencies
- Lobbying practitioners (persons)
- Client organizations
- Consultancy relationships

**Data Source:** Historical APPC/PRCA lobbying register PDFs

**Note:** Creates agencies, practitioners, and consultancy relationships

### 8. Companies House Enrichment (Directors & PSCs)

```bash
# Enrich organizations with Companies House data (match + basic info)
docker compose exec api python manage.py enrich_companies_house \
    --category lobbying_agency --verbose

# Fetch directors for matched organizations
docker compose exec api python manage.py enrich_companies_house \
    --category lobbying_agency --fetch-directors --force

# Fetch beneficial owners (PSCs) for matched organizations
docker compose exec api python manage.py enrich_companies_house \
    --category lobbying_agency --fetch-pscs --force

# Fetch both directors AND PSCs
docker compose exec api python manage.py enrich_companies_house \
    --category lobbying_agency --fetch-all --force

# Include resigned directors and ceased PSCs
docker compose exec api python manage.py enrich_companies_house \
    --category lobbying_agency --fetch-all --include-resigned --force

# Test single organization
docker compose exec api python manage.py enrich_companies_house \
    --org-id 12345 --fetch-all --verbose --debug

# Dry run (preview without changes)
docker compose exec api python manage.py enrich_companies_house \
    --category lobbying_agency --fetch-all --dry-run
```

**What it imports:**
- Company directors → `Person` records with `Membership` (role="Director")
- Beneficial owners (PSCs) → `Person` records with `Membership` (role="Beneficial Owner (X%)")
- Corporate directors/PSCs → `Note` attached to organization
- Company identifiers (uk.gov.companieshouse.officer, uk.gov.companieshouse.psc)
- Founding dates, registered addresses, SIC codes, former names

**Categories available:**
- `lobbying_agency` - Organizations that provide lobbying services
- `lobbying_client` - Organizations that hire lobbying agencies
- `donor` - Organizations that make donations
- `meeting_attendee` - Organizations that attend ministerial meetings
- `all` - All organizations

**Identifier schemes created:**
- `uk.gov.companieshouse` - Company registration number
- `uk.gov.companieshouse.officer` - Director/officer ID
- `uk.gov.companieshouse.psc` - Person with Significant Control ID

**Data Source:** [Companies House API](https://developer.company-information.service.gov.uk/)

**Setup:**
1. Get API key from [Companies House Developer Hub](https://developer.company-information.service.gov.uk/)
2. Add to `.env`: `COMPANIES_HOUSE_API_KEY=your_key_here`

**Rate Limits:** 600 requests per 5 minutes. The client handles rate limiting automatically.

**Analysis:** See `analysis/13_director_psc_analysis.sql` for SQL queries analyzing directors, ownership structures, and political connections.

### 9. Entity Resolution (Canonical Linking)

```bash
# Link meeting attendees, donations, and consultancies to canonical actors
docker compose exec api python manage.py populate_canonical --dry-run

# Fast mode (recommended) - identifier + exact name matching only
docker compose exec api python manage.py populate_canonical --fast --batch-size 500

# Process specific datasets
docker compose exec api python manage.py populate_canonical --dataset meeting_attendees --fast
docker compose exec api python manage.py populate_canonical --dataset donations --fast
docker compose exec api python manage.py populate_canonical --dataset consultancies --fast

# Verbose output with sample resolutions
docker compose exec api python manage.py populate_canonical --fast --verbose --limit 1000

# Full fuzzy matching (slower, more matches)
docker compose exec api python manage.py populate_canonical --batch-size 100
```

**What it does:**
- Links `MeetingAttendee.canonical_actor` to authoritative `Actor` records
- Links `Donation.canonical_donor` and `Donation.canonical_recipient`
- Links `Consultancy.canonical_client` and `Consultancy.canonical_agency`

**Match confidence levels:**
- 1.0: Identifier match (EC donor ID, ParlParse person ID)
- 0.95: Exact name match after normalization
- 0.85: Strong alias match
- 0.70: Weak/fuzzy alias match

**Performance:**
- Fast mode: ~500 records/batch, ~10% resolution rate
- Full mode: ~100 records/batch, higher resolution rate but much slower

### 10. Legacy Duplicate Resolution (Deprecated)

```bash
# Old duplicate detection (prefer populate_canonical)
docker compose exec api python manage.py resolve_duplicates --dry-run
```

## Data Quality Improvements (v3.0)

The import scripts have been enhanced with:

### 1. Name Normalization

All actor names are normalized during import using `normalize_actor_name()`:

**Strong Normalization** (applied during import):
- Removes trailing periods
- Collapses multiple spaces
- Preserves capitalization and structure
- Consistent formatting

**Example:**
- Input: `"Cllr Dr Michael AC   Heavens."`
- Output: `"Cllr Dr Michael AC Heavens"`

### 2. Deduplication by Identifiers

Actors are deduplicated by external identifiers **before** name matching:

1. Check if identifier already exists in database
2. If yes, update existing actor with new data
3. If no, create new actor with identifier

This prevents duplicates like:
- ❌ Before: Two "John Smith" actors (one from each data source)
- ✅ After: One "John Smith" actor (merged by identifier)

### 3. Consistent Organization Classification

Party organizations are consistently classified:
- `classification: "Political Party"` (not "party")

## Working Imports ✅

These imports are tested and working:

| Command | Data Source | Since Support | Status |
|---------|-------------|---------------|---------|
| `import_parlparse` | ParlParse | ✅ `--since YYYY` | ✅ Validated |
| `import_ministers` | ParlParse Ministers | ✅ `--since YYYY` | ✅ Validated |
| `import_twfy` | TheyWorkForYou | ✅ `--since YYYY` | ⏳ Fix applied, validation pending* |
| `import_mpsinterests` | TheyWorkForYou MPs' Interests | ✅ `--since YYYY` | ✅ Validated (v3.0+) |
| `import_lordsinterests` | Parliament Data Platform | ❌ No date filter | ✅ Validated (v3.0+) |
| `import_appc_archive` | Historical APPC PDFs | ❌ No date filter | ✅ Validated (v3.0+) |
| `import_ministerial_meetings` | GOV.UK Transparency | ✅ `--since YYYY` | ✅ Validated (41,362 meetings, 23 depts) |
| `import_ec` | Electoral Commission API | ❌ No date filter | ✅ Working (91,328 donations) |
| `import_appc` | PRCA Lobbying Register | ❌ No date filter | ✅ Working (scrapes prca.global) |

**\* import_twfy:** Identifier matching bug fixed 2026-01-14. Full validation pending API rate limit reset. See [IMPORT_VALIDATION_STATUS.md](IMPORT_VALIDATION_STATUS.md) for details.

## Untested/Partial Imports ⏸️

These imports are incomplete or untested:

| Command | Status | Notes |
|---------|--------|-------|
| `import_everypolitician` | Likely broken | Uses defunct cdn.rawgit.com, very slow |
| `import_companieshouse` | Partial | Fetching only, no parsing/import |
| `import_powerbase` | Partial | Fetching only, no parsing/import |

## Import Order

**Recommended order** for full data import:

1. ✅ **import_parlparse** - Foundation data (persons, orgs, posts, memberships)
2. ✅ **import_ministers** - Ministerial appointments (requires persons from step 1)
3. ✅ **import_twfy** - Biographical enrichment (requires persons from step 1)
4. ✅ **import_mpsinterests** - MPs' donations & interests (requires persons from step 1)
5. ✅ **import_lordsinterests** - Lords' donations & interests (requires persons from step 1)
6. ✅ **import_appc_archive** - Historical lobbying registers (creates agencies & consultancies)
7. ✅ **import_ministerial_meetings** - GOV.UK ministerial meetings (requires persons/ministers)
8. ⏸️ **import_ec** - Donations (currently broken)
9. ✅ **import_appc** - Modern lobbying (PRCA current register)

## Post-Import Tasks

After running imports:

### 1. Review Entity Resolutions

```bash
# Open Django admin
open http://localhost:8000/django-admin/datafetch/actorresolution/
```

- Filter by `decision="review"` for high-confidence matches
- Use bulk "Approve" or "Reject" actions
- Search by actor names

### 2. Check Data Statistics

```bash
docker compose exec api python manage.py shell
```

```python
from datafetch.models import Person, Organization, Membership, ActorResolution

# Count records
print(f"Persons: {Person.objects.count():,}")
print(f"Organizations: {Organization.objects.count():,}")
print(f"Memberships: {Membership.objects.count():,}")
print(f"Resolutions: {ActorResolution.objects.count():,}")

# Check for duplicates
from django.db.models import Count
dupes = Person.objects.values('name').annotate(count=Count('id')).filter(count__gt=1)
print(f"Potential name duplicates: {dupes.count()}")
```

### 3. Verify Data Quality

```bash
# Check for actors without identifiers
docker compose exec api python manage.py shell -c "
from datafetch.models import Person, Organization

persons_without_ids = Person.objects.filter(identifiers__isnull=True).count()
orgs_without_ids = Organization.objects.filter(identifiers__isnull=True).count()

print(f'Persons without identifiers: {persons_without_ids:,}')
print(f'Orgs without identifiers: {orgs_without_ids:,}')
"
```

## Troubleshooting

### Import Fails with "Person DoesNotExist"

**Cause:** Ministers import requires persons to exist first

**Solution:** Run `import_parlparse` before `import_ministers`

### Duplicate Actors Created

**Cause:** Old data imported before v3.0 improvements

**Solution:**
1. Wipe database: `./scripts/full_data_import.sh`
2. Or run entity resolution: `docker compose exec api python manage.py resolve_duplicates`

### Memory Issues with Large Imports

**Cause:** Importing all data at once can consume lots of memory

**Solution:** Import in smaller date ranges:
```bash
docker compose exec api python manage.py import_parlparse --since 2020
docker compose exec api python manage.py import_parlparse --since 2015
# etc.
```

### Rate Limiting from External APIs

**Cause:** helpers.py has 0.5s rate limit, but some APIs may still rate limit

**Solution:**
- Wait and retry later
- For TheyWorkForYou: Contact them for higher rate limits

## Data Sources

### ParlParse
- **URL:** https://github.com/mysociety/parlparse
- **Format:** JSON (Popolo specification)
- **Coverage:** MPs, Lords, memberships from 1996+
- **Update Frequency:** Daily

### Ministers
- **URL:** https://github.com/mysociety/parlparse/tree/master/members
- **Format:** JSON (Popolo specification)
- **Coverage:** Ministerial appointments from 2010+
- **Update Frequency:** When appointments change

### TheyWorkForYou
- **URL:** https://www.theyworkforyou.com/api/
- **Format:** JSON API
- **Coverage:** MP biographical data, voting records
- **Update Frequency:** Real-time
- **Requires:** API key (free)

### Electoral Commission (BROKEN)
- **URL:** https://www.electoralcommission.org.uk/
- **Status:** ⛔ Old CSV API defunct
- **Fix Required:** Rewrite for new data portal

### PRCA Lobbying Register
- **URL:** https://www.prca.global/professional-lobbying-register
- **Status:** ✅ Working (scrapes the current live register)
- **Historical Data:** Use `import_appc_archive` for data from 2019-2025.

## Performance Tips

### Faster Imports

```bash
# Use --refresh sparingly (it re-downloads everything)
# Without --refresh, cached files are used
docker compose exec api python manage.py import_parlparse --since 2020

# Use specific date ranges instead of importing everything
docker compose exec api python manage.py import_parlparse --since 2020
```

### Database Optimization

```bash
# After large imports, analyze database
docker compose exec db psql -U undertheinfluence -c "VACUUM ANALYZE;"
```

### Entity Resolution Performance

```bash
# Process in batches by type
docker compose exec api python manage.py resolve_duplicates --type person
docker compose exec api python manage.py resolve_duplicates --type organization
```

## Development

### Testing Imports

```bash
# Use dry-run mode to test without database changes
docker compose exec api python manage.py resolve_duplicates --dry-run

# Test with small dataset first
docker compose exec api python manage.py import_parlparse --since 2024
```

### Adding New Import Scripts

When creating new import commands:

1. **Add normalization:**
   ```python
   from datafetch.utils.normalization import normalize_actor_name

   # Normalize before creating
   name = normalize_actor_name(raw_name, strength='strong')
   ```

2. **Deduplicate by identifiers:**
   ```python
   try:
       identifier = models.Identifier.objects.get(scheme=scheme, identifier=ext_id)
       actor = Actor.objects.get(pk=identifier.object_id)
       # Update existing actor
   except (models.Identifier.DoesNotExist, Actor.DoesNotExist):
       # Create new actor
   ```

3. **Support date filtering:**
   ```python
   def add_arguments(self, parser):
       parser.add_argument('--since', nargs='?', type=int)

   # In handle():
   since = options.get('since')
   if since:
       data = [x for x in data if x['date'] >= str(since)]
   ```

4. **Document in this file**

## See Also

- [Phase 3 Roadmap](PHASE_3_ROADMAP.md) - Entity resolution architecture
- [Data Models](data-models.md) - Popolo data model reference
- [Modernization Progress](MODERNIZATION_PROGRESS.md) - Project upgrade status
