# Data Cleanup Guide

This guide documents the data cleanup process for the UnderTheInfluence database.

## Overview

The cleanup process is divided into phases, starting from basic record fixes to advanced entity resolution and actor merging.

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
docker compose exec api python manage.py clean_data --fix=orphaned_donations

# Remove exact duplicate donations (keeps oldest)
docker compose exec api python manage.py clean_data --fix=duplicate_donations

# Fix invalid membership date formats
docker compose exec api python manage.py clean_data --fix=invalid_dates
```

### Phase 1: Split Concatenated Entries
These MUST run before type fixes to properly split concatenated names.

```bash
# Split actors with semicolons: "Org A; Org B" -> ["Org A", "Org B"]
docker compose exec api python manage.py clean_data --fix=semicolon_actors

# Split "Header: A, B, C" patterns into separate actors
docker compose exec api python manage.py clean_data --fix=split_concatenated_attendees

# Split "Company Ltd Another Company" concatenations
docker compose exec api python manage.py clean_data --fix=split_concatenated_orgs
```

### Phase 2: Fix Entity Types
Run after splitting to correctly classify actors.

```bash
# Convert Organizations with person titles (MP, Lord, Sir, Dr) to Person records
docker compose exec api python manage.py clean_data --fix=convert_titled_persons
```

### Phase 3: Clean Up Names & Classifications
Normalize names and standardize taxonomies.

```bash
# Fix double spaces, trailing punctuation
docker compose exec api python manage.py clean_data --fix=normalize_actor_names

# Standardize Organization classifications (40+ types -> 35 core categories)
docker compose exec api python manage.py cleanup_org_classifications

# Fix corrupted Person prefixes (e.g. "Lord na" -> "Lord")
docker compose exec api python manage.py cleanup_person_data
```

### Phase 4: Companies House Enrichment
Enrich organizations with live data to improve matching confidence.

```bash
# Match organizations to Companies House records
docker compose exec api python manage.py enrich_companies_house --category all --batch-size 500
```

### Phase 5: Automated Entity Resolution (Linking)
Backfill `canonical_*` pointers on millions of records using the high-performance Service.

```bash
# Optimized full backfill (3,000+ records/sec)
docker compose exec api python manage.py populate_canonical --dataset all --batch-size 2000
```

### Phase 5.1: Backfill Actor Canonical Entries
After relationship-level canonical fields are populated, backfill `Actor.canonical_entry` to mark duplicate actors at the entity level. This enables graph visualizations and APIs to consolidate duplicates.

```bash
# Backfill canonical_entry from existing canonical relationships
docker compose exec api python manage.py shell -c "
from datafetch.models import Donation, MeetingAttendee, Actor
from django.db.models import F
from django.db import transaction

# From Donations
with transaction.atomic():
    donation_pairs = Donation.objects.filter(
        canonical_donor__isnull=False
    ).exclude(
        donor_id=F('canonical_donor_id')
    ).values('donor_id', 'canonical_donor_id').distinct()

    donor_to_canonical = {}
    for pair in donation_pairs:
        if pair['donor_id'] not in donor_to_canonical:
            donor_to_canonical[pair['donor_id']] = pair['canonical_donor_id']

    updated = 0
    for donor_id, canonical_id in donor_to_canonical.items():
        updated += Actor.objects.filter(pk=donor_id, canonical_entry__isnull=True).update(
            canonical_entry_id=canonical_id
        )
    print(f'Updated from donations: {updated}')

# From MeetingAttendees
with transaction.atomic():
    attendee_pairs = MeetingAttendee.objects.filter(
        canonical_actor__isnull=False
    ).exclude(
        actor_id=F('canonical_actor_id')
    ).values('actor_id', 'canonical_actor_id').distinct()

    actor_to_canonical = {}
    for pair in attendee_pairs:
        if pair['actor_id'] not in actor_to_canonical:
            actor_to_canonical[pair['actor_id']] = pair['canonical_actor_id']

    updated = 0
    for actor_id, canonical_id in actor_to_canonical.items():
        updated += Actor.objects.filter(pk=actor_id, canonical_entry__isnull=True).update(
            canonical_entry_id=canonical_id
        )
    print(f'Updated from meeting attendees: {updated}')

print(f'Total actors with canonical_entry: {Actor.objects.filter(canonical_entry__isnull=False).count()}')
"
```

Alternatively, use the EntityResolutionService for more comprehensive backfilling:

```bash
docker compose exec api python manage.py shell -c "
from datafetch.services.entity_resolution import EntityResolutionService
from datafetch.models import Actor

service = EntityResolutionService(fast_mode=True)
service.prefetch_all_actors()

stats = service.backfill_canonical_entries(batch_size=1000, min_confidence=0.85)
print(f'Backfill complete: {stats}')
"
```

### Phase 6: Manual Actor Resolution (Merging)
Clean up the Actor table itself by identifying and merging duplicate entities (e.g. "David Sainsbury" ↔ "Lord Sainsbury").

```bash
# 1. Detect duplicates and create review records
# Use --auto-approve to approve identifier and high-confidence matches automatically
docker compose exec api python manage.py resolve_duplicates --threshold 0.85 --auto-approve

# 2. Apply resolutions to the database
# This updates canonical pointers on Donations, Consultancies, and Meetings
docker compose exec api python manage.py apply_entity_resolutions --auto-approve-threshold 0.90
```

## Command Options

### `resolve_duplicates` Options
| Option | Description |
|--------|-------------|
| `--threshold` | Confidence threshold (0.0-1.0, default 0.70) |
| `--auto-approve` | Automatically approve high-confidence matches |
| `--type` | Filter by `person`, `organization`, or `both` |
| `--limit` | Limit number of actors to scan |
| `--clear` | Clear all pending resolutions before running |

### `apply_entity_resolutions` Options
| Option | Description |
|--------|-------------|
| `--auto-approve-threshold` | Approve pending resolutions >= this score before applying |
| `--resolution-id` | Apply only a specific resolution record |
| `--dry-run` | Preview counts of affected donations/meetings |

## Complete Workflow

```bash
# 1. Basic Cleanup
docker compose exec api python manage.py clean_data --fix=all

# 2. Standardize Taxonomies
docker compose exec api python manage.py cleanup_org_classifications
docker compose exec api python manage.py cleanup_person_data

# 3. Enrichment
docker compose exec api python manage.py enrich_companies_house --category all

# 4. Automated Linking (Backfill)
docker compose exec api python manage.py populate_canonical --dataset all

# 5. Strategic Merging (Manual/Supervised)
docker compose exec api python manage.py resolve_duplicates --threshold 0.85 --auto-approve
docker compose exec api python manage.py apply_entity_resolutions --auto-approve-threshold 0.90
```

## Related Documentation
- `docs/CANONICAL_IMPLEMENTATION_REPORT.md` - Deep dive into architecture
- `docs/DATA_QUALITY_REPORT.md` - Latest audit results