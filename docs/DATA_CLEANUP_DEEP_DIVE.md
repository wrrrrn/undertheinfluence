# Data Quality Deep Dive: Comprehensive Analysis

**Date:** January 23, 2026
**Status:** Independent Review Complete
**Reviewer:** Claude (automated analysis)
**Scope:** Full data quality audit including Companies House matching, actor type issues, entity resolution, and cleanup command evaluation.

---

## Executive Summary

This document presents an independent verification of the data cleanup work, confirming most findings while identifying **additional issues not currently addressed** by existing cleanup commands.

### Key Statistics

| Metric | Count |
|--------|-------|
| Total Actors | 156,651 |
| Total Persons | 91,799 |
| Total Organizations | 64,851 |
| Total Donations | 95,150 |
| Total Consultancies | 63,914 |
| Total Memberships | 132,749 |
| Ministerial Meetings | 41,362 |
| Meeting Attendees | 120,509 |
| Companies House Matches | 48,260 |

### Verdict

**Phase 1 cleanup work is solid** and addresses the most egregious issues (concatenated organizations, semicolon actors, long garbage names). However, significant "Phase 2" work is needed for:
- Entity type correction (Persons stored as Organizations)
- Entity resolution (duplicate names, canonical linking)
- Name quality normalization

---

## Part 1: Companies House Match Analysis

### Current Distribution

| Status | Count | Percentage |
|--------|-------|------------|
| Not Found | 15,691 | 32.5% |
| Auto-approved | 12,383 | 25.7% |
| Pending | 10,289 | 21.3% |
| Not Applicable | 9,761 | 20.2% |
| Approved (manual) | 98 | 0.2% |
| Rejected | 38 | 0.1% |

### Root Causes of "Not Found" (32.5%)

Analysis of the 15,691 "Not Found" records reveals:

| Pattern | Count | Notes |
|---------|-------|-------|
| Contains " and " | 2,492 | Concatenated attendee lists |
| Contains " & " | 888 | Concatenated attendee lists |
| Contains semicolons | 344 | Clear parsing errors |
| Name > 100 chars | 100 | Likely concatenations |
| Looks like person name (2-3 words) | 4,786 | Wrong actor type |

**Key Insight:** The "Not Found" rate is inflated by:
1. Concatenated attendee names that can't match any single company
2. Person names incorrectly stored as Organizations
3. Event descriptions stored as actor names

### Pending Matches (21.3%)

The 10,289 pending matches are mostly valid:
- 80% fall in the 0.85-0.88 confidence range
- 344 have 0.95+ confidence but were flagged by partial match penalty
- Acronym false positives (e.g., "PCC" → "PCC (CHELTENHAM) LIMITED")

**Recommendation:** Keep auto-approve threshold at 0.90. Use admin bulk-approve for obvious "Ltd" vs "Limited" variations.

### Detailed Analysis

See `docs/COMPANIES_HOUSE_DATA_QUALITY.md` for:
- Word overlap analysis queries
- Confidence distribution breakdowns
- Director/PSC inflation metrics
- Cleanup SQL scripts

---

## Part 2: Verified Issues (Concur with Original Analysis)

### 2.1 Concatenated Organizations

**Status:** ✅ Confirmed

**Pattern:** `(Ltd|Limited|PLC|Inc|LLP)\.?\s+[A-Z][a-z]`

**Count:** 1,352 organizations

**Examples:**
```
"Barratt David Wilson Homes" → "Barratt" + "David Wilson Homes"
"Taylor Wimpey Tesco" → "Taylor Wimpey" + "Tesco"
```

**Addressed by:** `split_concatenated_orgs.py`

### 2.2 Delimiter-Based Concatenations

**Status:** ✅ Confirmed

| Delimiter | Count |
|-----------|-------|
| Semicolons (`;`) | 1,404 |
| " and " | 6,220 |
| " & " | 2,749 |
| Colon-space (`: `) | 493 |
| Slash (` / `) | 132 |

**Addressed by:**
- Semicolons: `clean_data --fix=semicolon_actors`
- Others: Partially by `split_concatenated_attendees` (needs heuristic improvements)

### 2.3 Long Names (>150 chars)

**Status:** ✅ Confirmed with caveat

| Length Bucket | Count |
|---------------|-------|
| >300 chars | 96 |
| 201-300 chars | 71 |
| 151-200 chars | 104 |
| 101-150 chars | 1,729 |

**Sample (983 chars):**
```
"Environmental and Economic SolutionsNational Association of Local Councils Water Vole Business and Biodiversity Forum British Beer and Pub Association Marks and Spencer..."
```

**Caveat:** The 150-char threshold may catch some legitimate long organization names. Consider content inspection before deletion.

**Addressed by:** `cleanup_concatenated_orgs.py`

### 2.4 CamelCase Smashed Names

**Status:** ✅ Confirmed

**Count:** 446 actors with multiple CamelCase transitions (likely concatenations without delimiters)

**Examples:**
```
"Wildlife and Countryside LinkNorth Yorkshire MooresWildlife Trusts..."
"AbbVie Inc Altana AI Technologies Limited Apple Distribution..."
```

**Addressed by:** Not currently addressed - needs new command

---

## Part 3: NEW Issues Discovered

### 3.1 Person Names Stored as Organizations

**Status:** ❌ NOT ADDRESSED

**Count:** ~491+ actors with person titles stored as Organization records

| Pattern | Count |
|---------|-------|
| Names ending in " MP" | 191 |
| Names starting with Dr/Prof | 111 |
| Names starting with Sir/Dame | 100 |
| Names starting with Lord/Lady/Baron/Baroness | 89 |

**Examples:**
- "Aaron Bell MP" → Organization (should be Person)
- "Sir David Attenborough" → Organization (should be Person)
- "Dr Sarah Gilbert" → Organization (should be Person)

**Impact:** These cannot match Companies House (they're people, not companies), inflating the "Not Found" rate.

**Recommendation:** New command `convert_titled_persons` to:
1. Detect title patterns (MP, Lord, Sir, Dr, etc.)
2. Create corresponding Person record
3. Migrate MeetingAttendee relationships
4. Delete the Organization record

### 3.2 Duplicate Names Across Types

**Status:** ❌ NOT ADDRESSED

**Count:** 1,336 names exist as BOTH Person AND Organization records

**Examples:**
| Name | Person ID | Org ID(s) |
|------|-----------|-----------|
| 2Excel | 81521 | 49721, 50710, 37866 |
| Adelle Tracey | 38212 | 27571 |
| Aberdeen Airport | 82071 | 137102 |
| AXA UK | 66729 | 135160 |

**Impact:** Entity resolution is broken - the same entity appears multiple times with different types.

**Recommendation:** New command `merge_duplicate_actors` to:
1. Identify names appearing in both Person and Organization tables
2. Determine correct type based on context (donations, memberships, meeting roles)
3. Merge records using canonical_* fields
4. Update all foreign key references

### 3.3 Event Descriptions as Actor Names

**Status:** ⚠️ PARTIALLY ADDRESSED (only "Roundtable")

**Count:** 722 actors have names that are event descriptions, not entities

**Patterns:**
- "Roundtable on AI" (87 - addressed)
- "Call with Eurostar CEO" (many - not addressed)
- "Breakfast with British Business Representatives"
- "Meeting with industry stakeholders"
- "Briefing for Academy of Medical Royal Colleges"

**Recommendation:** Expand `clean_data --fix=roundtable_actors` to include:
- `^Call (with|to)`
- `^Meeting (with|of)`
- `^Breakfast (with|for|hosted)`
- `^Briefing (for|with)`
- `^Reception (for|with|hosted)`
- `^Discussion (with|on)`

### 3.4 Name Quality Issues

**Status:** ❌ NOT ADDRESSED

| Pattern | Count |
|---------|-------|
| Contains multiple commas | 3,255 |
| Starts with lowercase | 733 |
| Contains double spaces | 720 |
| Ends with comma/semicolon | 129 |
| Contains brackets `[]` | 70 |
| Contains pipe `\|` | 2 |

**Recommendation:** New command `normalize_actor_names` to:
1. Trim leading/trailing whitespace
2. Collapse double spaces
3. Remove trailing punctuation
4. Title-case names starting with lowercase (with exceptions for "eBay", "iPhone", etc.)
5. Flag or remove names with unusual characters

### 3.5 Entity Resolution Not Started

**Status:** ❌ NOT ADDRESSED

**Canonical field usage:**

| Field | Populated | Total | Percentage |
|-------|-----------|-------|------------|
| MeetingAttendee.canonical_actor_id | 25 | 120,509 | 0.02% |
| Donation.canonical_donor_id | 0 | 95,150 | 0% |
| Donation.canonical_recipient_id | 0 | 95,150 | 0% |

**Impact:** Cross-dataset analysis is broken. We cannot reliably answer:
- "Did this donor also attend ministerial meetings?"
- "Did this lobbying client donate to politicians?"

**Recommendation:** Phase 2 priority - implement entity resolution workflow:
1. High-confidence automated linking (exact name + CH number match)
2. Medium-confidence suggestions for manual review
3. Admin interface for bulk approval

---

## Part 4: Valid Data (Not Issues)

### Meeting-Only Actors

**Count:** 43,425 actors exist only as meeting attendees (no donations, consultancies, or memberships)

**Status:** ✅ VALID DATA - NOT AN ISSUE

These represent the external organizations and individuals that ministers meet with. This is valuable data showing:
- Who has access to government ministers
- Which organizations are actively engaging with which departments
- Patterns of ministerial engagement over time

**Do NOT delete these.** They should be:
1. Type-corrected (Person vs Organization) where needed
2. Entity-resolved to canonical records where duplicates exist
3. Enriched with Companies House data where applicable

---

## Part 5: Cleanup Command Evaluation

### Summary Table

| Command | Purpose | Dry-Run | Risk Level | Concerns |
|---------|---------|---------|------------|----------|
| `clean_data` | Master orchestrator | ✅ | Medium | Pattern duplication with `flag_non_ch_orgs` |
| `flag_non_ch_orgs` | Mark non-registrable orgs | ✅ | Low | Pattern order dependency, early break |
| `cleanup_concatenated_orgs` | Delete >150 char names | ✅ | **High** | May delete legitimate long names |
| `split_concatenated_attendees` | Split semicolon/colon actors | ✅ | Medium | Heuristic Person/Org detection |
| `split_concatenated_orgs` | Split "Ltd Company" patterns | ✅ | Medium | Relationship duplication |
| `split_consultancy_clients` | Split space-separated clients | ✅ | Medium | Complex heuristics, hardcoded company list |

### Critical Issues

#### 1. `merge_split_names` Logic is Brittle

**Location:** `clean_data.py`

**Problem:** Assumes consecutive database IDs correlate to split names:
```python
actor_b = Actor.objects.get(id=actor_a.id + 1)
```

**Risk:** Could merge completely unrelated actors if IDs aren't consecutive or if unrelated actors happen to be adjacent.

**Recommendation:** Replace with pattern-based matching (find "Mc" or "Mac" at end of name, look for following record starting with lowercase continuation).

#### 2. Pattern Duplication

**Problem:** Pattern definitions are duplicated between `clean_data.py` and `flag_non_ch_orgs.py`.

**Risk:** Changes in one file won't reflect in the other, leading to inconsistent behavior.

**Recommendation:** Extract patterns to a shared module (`datafetch/utils/org_patterns.py`).

#### 3. No Idempotency Checks

**Problem:** None of the commands check if an actor has already been processed.

**Risk:** Running commands multiple times could cause:
- Double-splitting (already split actors get split again)
- Lost data (already processed records get re-processed)

**Recommendation:** Add `Note` or flag field check before processing each record.

#### 4. Relationship Duplication on Split

**Problem:** When splitting organizations, consultancy relationships are cloned to ALL new orgs.

**Example:** If "Company A Ltd Company B" had a consultancy with "Tech Client":
- After split: BOTH "Company A Ltd" AND "Company B" get consultancy with "Tech Client"
- This may not be correct - only one company may have been the actual client

**Recommendation:** Add option to assign relationships to first/primary part only, or flag for manual review.

---

## Part 6: Recommended Execution Order

### Phase 1: Safe Cleanup (Current Commands)

Run in this order:

```bash
# 1. Flag non-registrable orgs (status change only, safe)
docker compose exec api python manage.py clean_data --fix=flag_non_ch_orgs --dry-run
docker compose exec api python manage.py clean_data --fix=flag_non_ch_orgs

# 2. Delete obviously broken actors
docker compose exec api python manage.py clean_data --fix=semicolon_actors --dry-run
docker compose exec api python manage.py clean_data --fix=roundtable_actors --dry-run

# 3. Split concatenated organizations (review dry-run carefully)
docker compose exec api python manage.py split_concatenated_orgs --dry-run --verbose

# 4. Clean up very long garbage names (review samples first)
docker compose exec api python manage.py cleanup_concatenated_orgs --dry-run
```

### Phase 2: New Commands Needed

| Priority | Command | Target Count | Complexity |
|----------|---------|--------------|------------|
| HIGH | `convert_titled_persons` | ~500 | Medium |
| HIGH | `expand_event_descriptions` | ~700 | Low |
| MEDIUM | `merge_duplicate_actors` | 1,336 | High |
| MEDIUM | `split_camelcase_smash` | ~446 | High |
| LOW | `normalize_actor_names` | ~4,000 | Low |

### Phase 3: Entity Resolution

1. Populate `canonical_actor_id` for meeting attendees
2. Populate `canonical_donor_id` and `canonical_recipient_id` for donations
3. Create admin interface for manual entity resolution
4. Implement fuzzy matching for suggested merges

---

## Part 7: Monitoring Queries

### Check Cleanup Progress

```sql
-- Remaining concatenated patterns
SELECT COUNT(*) FROM datafetch_actor
WHERE name ~ '(Ltd|Limited|PLC|Inc|LLP)\.?\s+[A-Z][a-z]';

-- Remaining semicolon actors
SELECT COUNT(*) FROM datafetch_actor WHERE name LIKE '%;%';

-- Remaining long names
SELECT COUNT(*) FROM datafetch_actor WHERE LENGTH(name) > 150;

-- Person titles as Organizations
SELECT COUNT(*) FROM datafetch_organization o
JOIN datafetch_actor a ON o.actor_ptr_id = a.id
WHERE a.name ~ '( MP$|^(Lord|Lady|Sir|Dame|Dr|Professor) )';

-- Duplicate Person/Org names
SELECT COUNT(DISTINCT a1.name) FROM datafetch_actor a1
JOIN datafetch_person p ON a1.id = p.actor_ptr_id
JOIN datafetch_actor a2 ON a1.name = a2.name AND a1.id <> a2.id
JOIN datafetch_organization o ON a2.id = o.actor_ptr_id;
```

### Companies House Progress

```sql
SELECT status, COUNT(*),
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct
FROM datafetch_companieshousematch
GROUP BY status
ORDER BY count DESC;
```

---

## Related Documentation

- `docs/COMPANIES_HOUSE_DATA_QUALITY.md` - Detailed CH matching analysis and SQL scripts
- `docs/DATA_CLEANUP_RESULTS.md` - Phase 1 cleanup execution results
- `docs/ADDITIONAL_CLEANUP_COMMANDS_ANALYSIS.md` - Individual command evaluation
- `analysis/14_companies_house_progress.sql` - CH enrichment progress tracking

---

## Appendix: Sample Problematic Records

### CamelCase Smashed Names (Top 5 by Length)

```
1. Environmental and Economic SolutionsNational Association of Local Councils Water Vole Business... (983 chars)
2. AFC Energy Airbus (Hydrogen in Aviation) All-Party Parliamentary Group for British Buses... (875 chars)
3. Ibbertya Holdings Limited Ilford Grand Hotel Ltd Inspired Pensions John Lewis... (866 chars)
4. Candace Dixon Caroline Taylor Charlie Blomley Chris Madel Ciron Edwards... (862 chars)
5. Alexion Amgen Assura AstraZeneca UK Ltd Atomic Weapons Establishment... (850 chars)
```

### Event Descriptions as Actors (Samples)

```
- "Call with Eurostar CEO"
- "Breakfast with British Business Representatives"
- "Briefing for Academy of Medical Royal Colleges"
- "Call to Andrew Blackhouse (Chair of Fire and Rescue Authority)"
- "Reception hosted by British Business Bank Board"
```

### Person Titles as Organizations (Samples)

```
- "Aaron Bell MP"
- "Sir David Attenborough"
- "Lord Frost"
- "Dame Cressida Dick"
- "Professor Chris Whitty"
```

---

**Last Updated:** January 23, 2026
