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
docker compose exec web python manage.py import_parlparse --since 1996 --refresh

# Import all data (no date filter)
docker compose exec web python manage.py import_parlparse --refresh

# Append new data without refreshing cache
docker compose exec web python manage.py import_parlparse --since 2020
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
docker compose exec web python manage.py import_ministers --since 1996 --refresh

# Import all ministerial data
docker compose exec web python manage.py import_ministers --refresh
```

**What it imports:**
- Ministerial appointments
- Government positions
- Organizational roles

**Data Source:** [ParlParse Ministers](https://github.com/mysociety/parlparse/tree/master/members)

### 3. TheyWorkForYou (Optional)

```bash
# Requires TWFY_API_KEY in .env
docker compose exec web python manage.py import_twfy --since 1996 --refresh
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
docker compose exec web python manage.py import_mpsinterests --since 1996 --refresh

# Import all available data
docker compose exec web python manage.py import_mpsinterests --refresh
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
docker compose exec web python manage.py import_lordsinterests --refresh
```

**What it imports:**
- Sponsorships to Lords
- Overseas visits
- Gifts to Lords
- Financial interests

**Data Source:** [Parliament Data Platform](https://data.parliament.uk/membersdataplatform/)

**Note:** No date filtering available - imports all current data

### 6. APPC Archive (Historical Lobbying Registers)

```bash
# Import historical APPC lobbying registers from PDFs
docker compose exec web python manage.py import_appc_archive --refresh

# Process a specific PDF file
docker compose exec web python manage.py import_appc_archive --file /path/to/register.pdf

# Dry run (parse without saving to database)
docker compose exec web python manage.py import_appc_archive --dry-run
```

**What it imports:**
- Lobbying agencies
- Lobbying practitioners (persons)
- Client organizations
- Consultancy relationships

**Data Source:** Historical APPC/PRCA lobbying register PDFs

**Note:** Creates agencies, practitioners, and consultancy relationships

### 7. Entity Resolution

```bash
# Identify duplicate actors
docker compose exec web python manage.py resolve_duplicates

# Clear pending resolutions first
docker compose exec web python manage.py resolve_duplicates --clear

# Dry run (preview without creating records)
docker compose exec web python manage.py resolve_duplicates --dry-run

# Filter by type
docker compose exec web python manage.py resolve_duplicates --type person
docker compose exec web python manage.py resolve_duplicates --type organization

# Custom threshold (default 0.6)
docker compose exec web python manage.py resolve_duplicates --threshold 0.7
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

**\* import_twfy:** Identifier matching bug fixed 2026-01-14. Full validation pending API rate limit reset. See [IMPORT_VALIDATION_STATUS.md](IMPORT_VALIDATION_STATUS.md) for details.

## Broken Imports ⛔

These imports are **broken** and should not be used:

| Command | Issue | Fix Required |
|---------|-------|--------------|
| `import_ec` | Electoral Commission CSV API defunct | Rewrite for new portal |
| `import_appc` | appc.org.uk defunct (merged with PRCA) | Rewrite for PRCA register |

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
7. ⏸️ **import_ec** - Donations (currently broken)
8. ⏸️ **import_appc** - Modern lobbying (currently broken)

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
docker compose exec web python manage.py shell
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
docker compose exec web python manage.py shell -c "
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
2. Or run entity resolution: `docker compose exec web python manage.py resolve_duplicates`

### Memory Issues with Large Imports

**Cause:** Importing all data at once can consume lots of memory

**Solution:** Import in smaller date ranges:
```bash
docker compose exec web python manage.py import_parlparse --since 2020
docker compose exec web python manage.py import_parlparse --since 2015
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

### APPC Register (BROKEN)
- **URL:** https://appc.org.uk/
- **Status:** ⛔ Site defunct (merged with PRCA in 2018)
- **Fix Required:** Rewrite for PRCA register

## Performance Tips

### Faster Imports

```bash
# Use --refresh sparingly (it re-downloads everything)
# Without --refresh, cached files are used
docker compose exec web python manage.py import_parlparse --since 2020

# Use specific date ranges instead of importing everything
docker compose exec web python manage.py import_parlparse --since 2020
```

### Database Optimization

```bash
# After large imports, analyze database
docker compose exec db psql -U undertheinfluence -c "VACUUM ANALYZE;"
```

### Entity Resolution Performance

```bash
# Process in batches by type
docker compose exec web python manage.py resolve_duplicates --type person
docker compose exec web python manage.py resolve_duplicates --type organization
```

## Development

### Testing Imports

```bash
# Use dry-run mode to test without database changes
docker compose exec web python manage.py resolve_duplicates --dry-run

# Test with small dataset first
docker compose exec web python manage.py import_parlparse --since 2024
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
