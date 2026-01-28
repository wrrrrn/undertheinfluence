# Data Quality Analysis Report

**Date**: 2026-01-26 (Updated)
**Previous Report**: 2026-01-25
**Status**: Post-Cleanup, Companies House Enrichment & Entity Resolution

---

## Executive Summary

Major data quality improvements achieved through systematic cleanup:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Orphaned donations** | 637 | 111 | -83% |
| **Duplicate donations** | 28,516 | 5 | -99.98% |
| **Zero value donations** | 427 | 5 | -99% |
| **Invalid donation dates** | 76 | 47 | -38% |
| **Missing membership start_dates** | 116,542 | 19,447 | -83% |
| **Invalid membership dates** | 26 | 0 | -100% |
| **Concatenated names (semicolons)** | 1,000+ | 0 | -100% |

**Total Issues Resolved**: ~126,000+ records fixed

---

## Current Database State

### Core Metrics

| Entity | Count |
|--------|-------|
| **Total Actors** | 155,066 |
| **Persons** | 90,728 |
| **Organizations** | 64,337 |
| **Donations** | 91,513 |
| **Consultancies** | 62,798 |
| **Ministerial Meetings** | 41,362 |
| **Meeting Attendees** | 119,793 |
| **Memberships** | 136,590 |

### Companies House Enrichment

| Status | Count | % |
|--------|-------|---|
| **Auto-approved** | 12,532 | 24.5% |
| **Pending review** | 11,198 | 21.9% |
| **Not found** | 16,419 | 32.1% |
| **Not applicable** | 10,892 | 21.3% |
| Approved | 98 | 0.2% |
| Rejected | 18 | 0.0% |
| **Total processed** | 51,157 | 100% |

---

## Issue Categories (Current State)

### 1. ✅ Orphaned Donations - MOSTLY RESOLVED

**Current**: 111 donations with null donor
**Previous**: 637

**Status**: Reduced by 83%. Remaining 111 require manual review.

**Cause**: Donor actors deleted, donations retained with SET_NULL.

**Action**: Review remaining 111 manually or delete if no value.

---

### 2. ✅ Duplicate Donations - RESOLVED

**Current**: 5 duplicate groups (5 extra records)
**Previous**: 25,539 groups (28,516 duplicates)

**Status**: 99.98% reduction. Effectively resolved.

**Cause**: Re-running import commands without deduplication (now fixed).

---

### 3. ✅ Zero Value Donations - RESOLVED

**Current**: 5 donations with £0 value
**Previous**: 427

**Status**: 99% reduction. Remaining 5 may be legitimate in-kind donations.

---

### 4. ⚠️ Invalid Donation Dates - PARTIALLY RESOLVED

**Current**: 47 donations where accepted_date < received_date
**Previous**: 76

**Status**: 38% reduction. Remaining require Electoral Commission source verification.

**Sample**:
```
ID 57145: accepted=2010-10-05, received=2010-10-25 (20 days off)
ID 64775: accepted=2009-04-24, received=2009-09-22 (151 days off)
```

**Action**: Export and cross-reference with EC source data.

---

### 5. ℹ️ Duplicate Person Names - VALID DATA

**Current**: 1,516 names appearing multiple times (3,066 records)
**Previous**: 134 names

**Status**: Increase due to more data imports. NOT a data quality issue.

**Explanation**: These are different people with the same name (e.g., "John Smith") or temporal positions (e.g., "Bishop of Durham" at different times).

**No Action Required**: Use entity resolution for true duplicates only.

---

### 6. ℹ️ Empty Person Names - VALID DATA

| Field | Empty Count | Explanation |
|-------|-------------|-------------|
| `name` | 0 | All persons have names |
| `family_name` | 54,588 | Lords/Bishops use titles |
| `given_name` | 54,484 | Lords/Bishops use titles |

**Status**: NOT a data quality issue. Lords and Bishops legitimately use titles instead of personal names.

**No Action Required**.

---

### 7. ✅ Missing Membership Start Dates - MOSTLY RESOLVED

**Current**: 19,447 memberships without start_date
**Previous**: 116,542

**Status**: 83% reduction.

**Breakdown by Role Type**:

| Role Category | Total | Missing Start Date |
|---------------|-------|-------------------|
| Director (Companies House) | 62,747 | 581 (0.9%) |
| Beneficial Owner (Companies House) | 9,014 | 0 (0%) |
| Member of Parliament | 7,929 | 0 (0%) |
| Lobbying Employee (APPC) | 32,230 | 18,865 (58.5%) |
| Other | 24,670 | 1 (0%) |

**Remaining Issue**: 18,865 lobbying employee memberships from APPC imports still lack start dates. The APPC source data doesn't include temporal information.

**Recommendation**: Consider inferring dates from APPC register publication dates.

---

### 8. ✅ Invalid Membership Dates - RESOLVED

**Current**: 0 memberships with end_date < start_date
**Previous**: 26

**Status**: 100% resolved. All date swaps corrected.

---

## Remaining Data Quality Issues

### Concatenated Names (Partial Cleanup)

| Pattern | Count | Status |
|---------|-------|--------|
| Semicolon-separated | 0 | ✅ Resolved |
| Colon + list pattern | 347 | ⚠️ Remaining |
| Names > 100 chars | 1,596 | ⚠️ Review needed |
| Names > 200 chars | 121 | ⚠️ Review needed |
| CamelCase patterns | 692 | ⚠️ Review needed |

**Total remaining concatenated/problematic names**: ~2,500

**Action**: Run additional cleanup passes or manual review.

---

### Entity Resolution Status

| Dataset | Total | Linked | % Linked |
|---------|-------|--------|----------|
| Meeting Attendees | 119,793 | In progress | ~10% (fast mode) |
| Donations (canonical) | 91,513 | Pending | 0% |
| Consultancies (canonical) | 62,798 | Pending | 0% |

**Status**: Entity resolution available via `populate_canonical` command.

**Optimized Full Resolution** (~1000+ records/sec):
```bash
docker compose exec api python manage.py populate_canonical --dataset all --batch-size 2000
```

**Match confidence levels:**
- 1.0: Identifier match (EC donor ID, Companies House number)
- 0.95: Exact name match after normalization
- 0.85: Strong alias match
- 0.70: Fuzzy match (Levenshtein distance)

---

## Summary Statistics

### Issues Resolved

| Category | Before | After | Fixed |
|----------|--------|-------|-------|
| Orphaned donations | 637 | 111 | 526 |
| Duplicate donations | 28,516 | 5 | 28,511 |
| Zero value donations | 427 | 5 | 422 |
| Invalid donation dates | 76 | 47 | 29 |
| Missing membership start_dates | 116,542 | 19,447 | 97,095 |
| Invalid membership dates | 26 | 0 | 26 |
| Semicolon concatenations | 1,000+ | 0 | 1,000+ |
| **TOTAL FIXED** | | | **~127,600** |

### Remaining Issues

| Category | Count | Severity | Action |
|----------|-------|----------|--------|
| Orphaned donations | 111 | Medium | Manual review |
| Invalid donation dates | 47 | Low | EC verification |
| Missing APPC start_dates | 18,865 | Low | Accept or infer |
| Concatenated names | ~2,500 | Medium | Additional cleanup |
| Unlinked entities | 211,286 | Medium | Run entity resolution |

---

## Recommendations

### Immediate Actions

1. **Run Entity Resolution**
   ```bash
   docker compose exec api python manage.py populate_canonical --dataset all
   ```

2. **Review Remaining Concatenated Names**
   ```bash
   docker compose exec api python manage.py clean_data --fix=all --dry-run
   ```

3. **Export Invalid Donation Dates for EC Verification**
   ```sql
   SELECT id, donor_id, recipient_id, value, accepted_date, received_date
   FROM datafetch_donation
   WHERE accepted_date < received_date;
   ```

### Prevention Measures (Implemented)

- ✅ Deduplication in import commands
- ✅ Date validation in imports
- ✅ Concatenated name detection and splitting
- ✅ Companies House matching for organization validation

---

## Commands Reference

```bash
# Check current data quality
docker compose exec api python manage.py clean_data --fix=all --dry-run

# Run specific fixes
docker compose exec api python manage.py clean_data --fix=orphaned_donations
docker compose exec api python manage.py clean_data --fix=duplicate_donations
docker compose exec api python manage.py clean_data --fix=split_concatenated_attendees

# Entity resolution
docker compose exec api python manage.py populate_canonical --dry-run
docker compose exec api python manage.py populate_canonical --dataset all

# Companies House enrichment
docker compose exec api python manage.py enrich_companies_house --retry-not-found --category all
```

---

**Report Updated**: 2026-01-26
**Previous Version**: 2026-01-25
