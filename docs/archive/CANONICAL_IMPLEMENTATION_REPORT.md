# Canonical Entity Resolution Implementation Report

**Date:** January 27, 2026
**Status:** Implemented & Optimized
**Key Components:** `EntityResolutionService`, `populate_canonical`, `ActorResolution`

---

## 1. Executive Summary

The "Canonical Implementation" is a high-performance system designed to solve the fragmentation of political actors across multiple data sources (e.g., "David Sainsbury" vs "Lord Sainsbury", "Unite" vs "Unite the Union").

It moves beyond simple string matching to a **confidence-weighted, multi-pass resolution strategy** that is **non-destructive** (preserving original data while linking to a "canonical" master entity).

**Key Achievement:** The system has been optimized from an O(N²) linear scan (unusable on 155k actors) to an **in-memory indexed O(1) lookup system** capable of processing 3,000+ records per second.

---

## 2. Core Architecture

### 2.1 The "Effective Actor" Pattern (Non-Destructive)

Instead of deleting duplicate records (which destroys the audit trail of imports), we implemented a pointer system:

```python
class Donation(models.Model):
    # Original Import Data (Never Changed)
    donor = models.ForeignKey(Actor, ...)
    
    # Resolved Canonical Reference (Updated by Resolution Engine)
    canonical_donor = models.ForeignKey(Actor, ...)

    @property
    def effective_donor(self):
        """Returns canonical donor if set, otherwise original donor."""
        return self.canonical_donor or self.donor
```

This allows:
1.  **Reversibility:** Merges can be undone by clearing the `canonical_donor` field.
2.  **Auditability:** We always know exactly what the original source said.
3.  **Aggregation:** Queries group by `Coalesce(canonical_id, id)` to sum totals across aliases.

### 2.2 Entity Resolution Service (`datafetch/services/entity_resolution.py`)

This is the brain of the operation. It uses a 7-tier confidence strategy:

| Tier | Method | Confidence | Logic |
|------|--------|------------|-------|
| 1 | **Identifier** | 1.0 | External ID match (Companies House, EC Donor ID) |
| 2 | **EC Ref** | 0.95 | Electoral Commission ID match |
| 3 | **Exact Name** | 0.95 | Case-insensitive exact match |
| 4 | **Strong Alias** | 0.90 | "Unite the Union" -> "Unite" (via `OtherName`) |
| 5 | **Strong Norm** | 0.85 | Conservative normalization (strips "Ltd", "PLC") |
| 6 | **Weak Alias** | 0.75 | Nicknames / Former names |
| 7 | **Weak Norm** | 0.70 | Aggressive normalization (strips titles "Lord", "Sir") |

### 2.3 Optimization: In-Memory Indexing

The critical performance breakthrough (Phase 3.2) was removing database hits during the resolution loop.

The `prefetch_all_actors()` method builds Python dictionaries for O(1) access:
- **`_name_index`**: `{"david sainsbury": [Actor(830), Actor(4083)]}`
- **`_normalized_strong_index`**: Maps normalized strings to actors.
- **`_ch_index`**: Maps Companies House numbers directly to canonical IDs.
- **`_score_cache`**: Caches the "richness" score of every actor.

**Result:** `populate_canonical` runs in minutes rather than days.

---

## 3. Workflows & Commands

There are two distinct workflows for resolution:

### Workflow A: Automated Backfill (`populate_canonical`)
**Best for:** Processing millions of donations/meetings efficiently.
**Logic:** Iterates through *relationships* (Donations, Meetings) and links them to the best existing Actor using the Service.
**Command:**
```bash
# Fast mode (Identifiers + Exact Name only) - 3000/sec
python manage.py populate_canonical --dataset all --fast --batch-size 2000

# Full mode (Fuzzy matching) - Slower but more thorough
python manage.py populate_canonical --dataset all --min-confidence 0.85
```

### Workflow B: Duplicate Detection & Merging (`resolve_duplicates`)
**Best for:** Cleaning up the Actor table itself (finding "Lord Sainsbury" vs "David Sainsbury").
**Logic:** Scans *Actors* to find pairs that represent the same entity, creates `ActorResolution` records for review.
**Command:**
```bash
# 1. Find candidates (creates ActorResolution records)
python manage.py resolve_duplicates --threshold 0.85 --auto-approve

# 2. Apply approved merges (updates canonical pointers)
python manage.py apply_entity_resolutions --auto-approve-threshold 0.90
```

---

## 4. Current Impact & Status

### Data Quality (Post-Cleanup)
- **Duplicate Donations:** Reduced from 28,516 to **5**.
- **Orphaned Donations:** Reduced from 637 to **111**.
- **Semicolon Actors:** 1,000+ parsing errors completely resolved.

### Companies House Enrichment
- **51,157** organizations matched to Companies House data.
- **12,532** auto-approved (High confidence).
- Enables precise director/PSC network analysis.

### Top Resolved Entities (Examples)
1. **Unite the Union:** Consolidated from "Unite", "Unite Union", "TGWU".
2. **David Sainsbury:** Consolidated "David Sainsbury", "Lord Sainsbury of Turville".
3. **Google:** Consolidated "Google UK Ltd", "Google Ireland", "Google".

---

## 5. Next Steps

1.  **Run Full Resolution:** Execute the optimized `resolve_duplicates` on the full dataset (now that the code uses the Service).
2.  **Review "Pending" Matches:** Use the Django Admin (`/admin/datafetch/actorresolution/`) to manually approve the ~10,000 "Pending" fuzzy matches (0.70 - 0.85 confidence).
3.  **Visualization:** The "Minister Network" graph now uses these canonical links to draw accurate edges (e.g., donations from "Sainsbury" now link to the same node as "Lord Sainsbury").
