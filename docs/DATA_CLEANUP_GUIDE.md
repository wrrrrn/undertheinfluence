# Data Cleanup Guide

This guide documents the data cleanup process for the UnderTheInfluence database.

## Overview

The `clean_data` management command provides various fix types to address data quality issues. Fixes should be run in a specific order to ensure proper deduplication and entity resolution.

**Always run with `--dry-run` first** to review what will change before applying.

## Quick Start

```bash
# Run all fixes in correct order (dry-run first!)
docker compose exec api python manage.py clean_data --fix=all --dry-run

# Then apply
docker compose exec api python manage.py clean_data --fix=all
```

## Fix Types by Phase

### Phase 0: General Data Quality

Safe fixes for obvious data issues.

```bash
# Remove donations with null donor, zero value, no date
docker compose exec api python manage.py clean_data --fix=orphaned_donations --dry-run

# Remove exact duplicate donations (keeps oldest)
docker compose exec api python manage.py clean_data --fix=duplicate_donations --dry-run

# Fix invalid membership date formats
docker compose exec api python manage.py clean_data --fix=invalid_dates --dry-run
```

**Not in `--fix=all` (run explicitly if needed):**
```bash
# Delete zero-value donations - CAUTION: may delete valid records
docker compose exec api python manage.py clean_data --fix=zero_value --dry-run
```

### Phase 1: Split Concatenated Entries

These MUST run before type fixes to properly split concatenated names.

```bash
# Split actors with semicolons: "Org A; Org B" -> ["Org A", "Org B"]
docker compose exec api python manage.py clean_data --fix=semicolon_actors --dry-run

# Split "Header: A, B, C" patterns into separate actors
docker compose exec api python manage.py clean_data --fix=split_concatenated_attendees --dry-run

# Split "Company Ltd Another Company" concatenations
docker compose exec api python manage.py clean_data --fix=split_concatenated_orgs --dry-run

# Split space-separated consultancy client lists
docker compose exec api python manage.py clean_data --fix=split_consultancy_clients --dry-run

# Parse "Roundtable with A, B, C" into proper attendees
docker compose exec api python manage.py clean_data --fix=parse_event_descriptions --dry-run

# Split CamelCase concatenated names
docker compose exec api python manage.py clean_data --fix=split_camelcase --dry-run
```

### Phase 2: Fix Entity Types

Run after splitting to correctly classify actors.

```bash
# Convert Organizations with person titles (MP, Lord, Sir, Dr) to Person records
docker compose exec api python manage.py clean_data --fix=convert_titled_persons --dry-run

# Report remaining "Roundtable" actors (handled by parse_event_descriptions)
docker compose exec api python manage.py clean_data --fix=roundtable_actors --dry-run
```

### Phase 3: Clean Up Names

Run after type fixes to normalize names.

```bash
# Fix double spaces, trailing punctuation
docker compose exec api python manage.py clean_data --fix=normalize_actor_names --dry-run

# Merge split names like "Mc" + "Donald" -> "McDonald"
docker compose exec api python manage.py clean_data --fix=merge_split_names --dry-run
```

**Not in `--fix=all` (dangerous):**
```bash
# Delete very long garbage names - CAUTION: deletes without migrating relationships
docker compose exec api python manage.py clean_data --fix=cleanup_concatenated_orgs --dry-run --min-length=150
```

### Phase 3.5: Standardize Classifications & Person Data

Separate commands to clean up Organization classifications and Person data quality.

#### Organization Classifications

Rationalizes 46 inconsistent values down to ~35 standardized categories.

```bash
# View current stats
docker compose exec api python manage.py cleanup_org_classifications --stats-only

# Preview changes (dry-run)
docker compose exec api python manage.py cleanup_org_classifications --dry-run

# Apply fixes
docker compose exec api python manage.py cleanup_org_classifications
```

**What it fixes:**
| Issue | Examples | Count |
|-------|----------|-------|
| Case inconsistencies | "company" → "Company", "Friendly society" → "Friendly Society" | ~4,300 |
| Duplicate categories | "Registered Political Party" → "Political Party" | ~50 |
| Empty values | (none) → "Unknown" | ~10,500 |
| Typos | "Oversea Company" → "Overseas Company" | ~100 |

**Categories flagged for manual review (not auto-fixed):**
- "External Organization" (23,923) - meeting attendees' organizations, needs investigation
- "Other" (886) - mixed bag

#### Person Data Quality

Fixes corrupted prefixes, inconsistent titles, and parses empty name fields.

```bash
# View current stats
docker compose exec api python manage.py cleanup_person_data --stats-only

# Preview changes (dry-run)
docker compose exec api python manage.py cleanup_person_data --dry-run

# Apply fixes
docker compose exec api python manage.py cleanup_person_data

# Check for duplicates (report only)
docker compose exec api python manage.py cleanup_person_data --check-duplicates

# Fix only prefixes (not names)
docker compose exec api python manage.py cleanup_person_data --fix prefixes
```

**What it fixes:**
| Issue | Examples | Count |
|-------|----------|-------|
| Corrupted "na" prefixes | "Lord na" → "Lord", "Lady na" → "Lady" | 73 |
| Inconsistent prefixes | "The Rt Hon" → "Rt Hon", "Prof" → "Professor" | ~130 |
| Empty given_name/family_name | Parses from name field | ~54,000 |

**Duplicate detection:**
The `--check-duplicates` flag identifies:
- Exact name duplicates (1,516 names appear multiple times)
- "Lord na" records that duplicate properly-parsed Lords (67 confirmed duplicates)

### Phase 4: Deduplicate

Run after cleaning to merge duplicate records.

```bash
# Merge records that exist as both Person AND Organization
docker compose exec api python manage.py clean_data --fix=merge_duplicate_types --dry-run
```

### Phase 5: Categorize

Run after main cleanup.

```bash
# Flag organizations not registrable with Companies House (councils, universities, etc.)
docker compose exec api python manage.py clean_data --fix=flag_non_ch_orgs --dry-run
```

### Phase 5.5: Companies House Enrichment (Re-run)

After data cleanup, organization names are cleaner. Re-run Companies House matching on previously unmatched orgs to improve match rates.

**Use `--retry-not-found`** to retry organizations that previously had `status=not_found`.

```bash
# Check how many orgs could be retried
docker compose exec api python manage.py shell -c "
from datafetch.models.influence_mapping import CompaniesHouseMatch
print(f'not_found: {CompaniesHouseMatch.objects.filter(status=\"not_found\").count()}')"

# Dry run to preview (small sample)
docker compose exec api python manage.py enrich_companies_house --retry-not-found --dry-run --limit 50

# Run by category (recommended order - highest value first)
# 1. Lobbying agencies (highest confidence, ~200 orgs)
docker compose exec api python manage.py enrich_companies_house \
    --retry-not-found --category lobbying_agency --batch-size 100

# 2. Donors (~8k orgs)
docker compose exec api python manage.py enrich_companies_house \
    --retry-not-found --category donor --batch-size 500

# 3. Lobbying clients
docker compose exec api python manage.py enrich_companies_house \
    --retry-not-found --category lobbying_client --batch-size 500

# 4. Meeting attendees (largest, dirtiest data ~17k orgs)
docker compose exec api python manage.py enrich_companies_house \
    --retry-not-found --category meeting_attendee --batch-size 500

# Or retry all categories at once
docker compose exec api python manage.py enrich_companies_house \
    --retry-not-found --batch-size 500 --no-input
```

**Key options for `enrich_companies_house`:**

| Option | Description |
|--------|-------------|
| `--retry-not-found` | Retry orgs with `status=not_found` (after cleanup) |
| `--category <cat>` | `lobbying_agency`, `donor`, `meeting_attendee`, `lobbying_client`, `all` |
| `--batch-size N` | Process in batches, prompting between (use with `--no-input` for unattended) |
| `--no-input` | Run without prompts (for scripts) |
| `--dry-run` | Preview without changes |
| `--verbose` | Show each org being processed |
| `--auto-approve-threshold` | Confidence for auto-approval (default: 0.90) |

### Phase 6: Entity Resolution

Separate command to populate canonical fields for cross-dataset linking.

**Note:** As of Jan 2026, this command is highly optimized with in-memory indexing.

```bash
# Dry run to preview
docker compose exec api python manage.py populate_canonical --dry-run --verbose

# Standard run (Recommended) - Full fuzzy matching
# Now optimized to process ~1000+ records/sec
docker compose exec api python manage.py populate_canonical --dataset all --batch-size 2000

# Legacy "Fast mode" (Identifiers + Exact Name only)
# Use only if memory is extremely constrained
docker compose exec api python manage.py populate_canonical --fast --batch-size 2000
```

**How canonical linking works:**

Each record (MeetingAttendee, Donation, Consultancy) has a `canonical_actor` field that points to the authoritative Actor record. This enables:

1. **Cross-dataset queries**: Find all interactions with "Shell" regardless of name variant
2. **Aggregation**: Sum donations from same entity across different name spellings
3. **Network analysis**: Build complete influence networks

**Match confidence levels:**
- 1.0: Identifier match (EC donor ID, ParlParse person ID, Companies House number)
- 0.95: Exact name match after normalization (case, punctuation, legal suffixes)
- 0.85: Strong alias match
- 0.70: Weak/fuzzy alias match (Levenshtein distance)

**Performance tips:**
- The command now builds an in-memory index of all ~150k actors at startup (takes ~5-10s).
- Use `--batch-size 2000` or higher for optimal throughput.
- Score caching prevents redundant database calculations.

## Command Options

### clean_data Options

| Option | Description |
|--------|-------------|
| `--fix=<type>` | Specific fix type or `all` |
| `--dry-run` | Show what would change without modifying |
| `--limit=N` | Process only N records (for testing) |
| `--min-length=N` | Minimum name length for cleanup_concatenated_orgs |
| `--verbose` | Show detailed output |

### populate_canonical Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would change without modifying |
| `--dataset=<type>` | `meeting_attendees`, `donations`, `consultancies`, or `all` |
| `--batch-size=N` | Records per batch (default: 1000, use 500 for progress visibility) |
| `--min-confidence=N` | Minimum confidence for linking (default: 0.85) |
| `--fast` | Fast mode: identifier + exact name only (skip slow fuzzy matching) |
| `--limit=N` | Process only N records (for testing) |
| `--verbose` | Show each resolution |
| `--skip-existing` | Skip records that already have canonical links (default: true) |

### cleanup_org_classifications Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would change without modifying |
| `--stats-only` | Only show statistics, no changes |
| `--batch-size=N` | Records per batch (default: 1000) |

### cleanup_person_data Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would change without modifying |
| `--stats-only` | Only show statistics, no changes |
| `--fix=<type>` | `all`, `prefixes`, or `names` (default: all) |
| `--check-duplicates` | Report potential duplicate persons |
| `--batch-size=N` | Records per batch (default: 500) |

## Understanding the Output

### Before/After Stats

Each run shows database counts before and after:

```
BEFORE:
  Persons:            91,296
  Organizations:      63,901
  Actors (total):     155,198

AFTER:
  Persons:            91,296
  Organizations:      63,901
  Actors (total):     155,198

Changes:
  (none if dry-run)
```

### What "Negative" Changes Mean

**Decreasing actor counts is often correct:**

When splitting "Denmark: Copenhagen Infrastructure Partners, Latvia, UK":
1. We find existing actors for each part (no new creation)
2. We link meetings to those existing actors
3. We delete the original concatenated actor
4. Net: -1 actor (but meetings now linked correctly)

This is **deduplication**, not data loss.

### What Each Action Shows

```
Would split: "Header: A, B, C" -> ['A', 'B', 'C']     # Dry-run
Splitting: "Header: A, B, C" -> ['A', 'B', 'C']       # Live run

Would convert: Aaron Bell MP                          # Dry-run
Converting: Aaron Bell MP                             # Live run

Would merge: "Mc" + "Donald" -> "McDonald"            # Dry-run
Merging: "Mc" + "Donald" -> "McDonald"                # Live run
```

## Complete Workflow

```bash
# 1. Check current state
docker compose exec api python manage.py clean_data --fix=all --dry-run

# 2. Run phase by phase, reviewing each
docker compose exec api python manage.py clean_data --fix=orphaned_donations --dry-run
docker compose exec api python manage.py clean_data --fix=orphaned_donations

docker compose exec api python manage.py clean_data --fix=semicolon_actors --dry-run
docker compose exec api python manage.py clean_data --fix=semicolon_actors

# ... continue for each fix type ...

# 3. Flag non-CH organizations
docker compose exec api python manage.py clean_data --fix=flag_non_ch_orgs --dry-run
docker compose exec api python manage.py clean_data --fix=flag_non_ch_orgs

# 3.5. Standardize classifications and person data
docker compose exec api python manage.py cleanup_org_classifications --dry-run
docker compose exec api python manage.py cleanup_org_classifications

docker compose exec api python manage.py cleanup_person_data --dry-run
docker compose exec api python manage.py cleanup_person_data

# 4. Re-run Companies House enrichment on cleaned data
docker compose exec api python manage.py enrich_companies_house --retry-not-found --category lobbying_agency
docker compose exec api python manage.py enrich_companies_house --retry-not-found --category donor --batch-size 500
docker compose exec api python manage.py enrich_companies_house --retry-not-found --category lobbying_client --batch-size 500
docker compose exec api python manage.py enrich_companies_house --retry-not-found --category meeting_attendee --batch-size 500

# 5. Run entity resolution
docker compose exec api python manage.py populate_canonical --dry-run
docker compose exec api python manage.py populate_canonical --dataset all

# 6. Verify final state
docker compose exec api python manage.py clean_data --fix=all --dry-run
docker compose exec api python manage.py cleanup_org_classifications --stats-only
docker compose exec api python manage.py cleanup_person_data --stats-only
# Should show minimal/no issues remaining
```

## Troubleshooting

### "MultipleObjectsReturned" Error

The cleanup commands handle duplicate records gracefully using `filter().first()` instead of `get()`.

### Stats Changed During Dry-Run

If BEFORE and AFTER stats differ during `--dry-run`, something else modified the database:
- Check for concurrent processes
- Verify you used `--dry-run` flag
- Check Docker logs for other commands

### Too Many Records to Process

Use `--limit` to test on a subset:
```bash
docker compose exec api python manage.py clean_data --fix=split_camelcase --dry-run --limit=100
```

## Related Documentation

- `docs/DATA_QUALITY_REPORT.md` - Comprehensive quality analysis
- `docs/DATA_IMPORT_GUIDE.md` - Import procedures
- `datafetch/utils/data_cleanup.py` - Shared utility patterns
- `datafetch/services/entity_resolution.py` - Resolution service
- `datafetch/management/commands/cleanup_org_classifications.py` - Org classification cleanup
- `datafetch/management/commands/cleanup_person_data.py` - Person data cleanup
