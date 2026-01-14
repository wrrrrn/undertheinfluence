# Data Ingest Report Status

**Date:** 2026-01-13
**Status:** ⚠️ CORRECTED QUERIES - REPORT REGENERATION NEEDED

---

## What Happened

Our initial analysis (in `DATA_INGEST_REPORT.md` and `LOBBYING_DONATION_OVERLAP_SUMMARY.md`) contained **inflated numbers** due to multiplicative joins in the SQL queries.

**Problem:**
Joining `datafetch_donation` and `datafetch_consultancy` directly caused donation values to be counted multiple times when organizations had multiple consultancy periods or agencies.

**Solution:**
Refactored all queries in `data_analysis_queries.sql` (Version 2.0) with:
- Non-inflating CTEs (pre-aggregate then join)
- Safe date casting
- Proper GROUP BY clauses
- ID-based grouping (not name-based)

---

## Corrected Numbers Summary

### Lobbying-Donation Overlap

|  Metric | Version 1 (Inflated) | Version 2 (Correct) | Inflation Factor |
|--------|---------------------|---------------------|-------------------|
| **Total donated by lobbying clients** | £305.7M | **£72.5M** | **4.2x** |
| Organizations that lobby + donate | 62 | 62 | ✓ |
| Individual donations | 1,714 | 1,714 | ✓ |
| Distinct recipients | 235 | 235 | ✓ |

### Key Findings (CORRECTED)

1. **Extreme Concentration:** 277 donors (1.3%) account for 65% of all donation value *(unchanged - correct)*

2. **Lobbying-Donation Overlap (CORRECTED):**
   - **62 organizations** both lobby AND donate (correct count)
   - **£72.5M total** donated (was £305.7M - **76% lower**)
   - **Trade unions = 96.54%** of lobbying-client donations (was 93.37%)
   - **Companies = 3.14%** of lobbying-client donations (was 6.19%)
   - **235 recipients:** 221 MPs/Lords + 4 parties + 10 campaigns
   - **Political parties receive 94.5%** (was 92.2%)
   - **Individual MPs receive 2.9%** (was 3.4%)

3. **Foreign Influence:** Cayman Islands (£49K) and Qatar (£40K) = £89K total (was £965K - **91% lower**)

### Individual Organization Corrections

| Organization | V1 (Inflated) | V2 (Correct) | Factor |
|--------------|---------------|--------------|--------|
| Unite the Union | £269.0M | **£67.2M** | 4.0x |
| Community | £16.4M | **£2.7M** | 6.0x |
| Electoral Reform Society | £12.4M | **£1.6M** | 7.8x |
| Manchester Airport Group | £1.08M | **£120K** | 9.0x |
| Quinn Estates Ltd | £1.36M | **£105K** | 13.0x |
| Cayman Islands Government | £885K | **£49K** | 18.0x |
| Arup | £732K | **£33K** | 22.0x |
| Criterion Capital Ltd | £715K | **£55K** | 13.0x |
| Dignity in Dying | £520K | **£43K** | 12.0x |
| Road Haulage Association | £317K | **£32K** | 9.9x |

**Pattern:** Organizations with multiple consultancy periods had highest inflation factors (13-22x).

---

## Files Status

### ✅ CORRECTED
- `analysis/data_analysis_queries.sql` - Version 2.0 (production-quality, non-inflating)
- `analysis/QUERY_CORRECTIONS_SUMMARY.md` - Detailed comparison of old vs. new
- `analysis/REPORT_STATUS.md` - This file

### ⚠️ NEEDS REGENERATION
- `analysis/DATA_INGEST_REPORT.md` - Contains inflated numbers from V1 queries
- `analysis/LOBBYING_DONATION_OVERLAP_SUMMARY.md` - Contains inflated numbers from V1 queries

---

## Action Items

1. ✅ **Refactor SQL queries** - DONE (Version 2.0)
2. ✅ **Document corrections** - DONE (this file + QUERY_CORRECTIONS_SUMMARY.md)
3. ⏳ **Regenerate DATA_INGEST_REPORT.md** - TODO (use V2 query results)
4. ⏳ **Regenerate LOBBYING_DONATION_OVERLAP_SUMMARY.md** - TODO (use V2 query results)

---

## How to Use

**For Phase 2 UI design decisions:**
- ✅ Use numbers from `QUERY_CORRECTIONS_SUMMARY.md` (Version 2)
- ❌ DO NOT use numbers from the old `DATA_INGEST_REPORT.md`
- ✅ Run queries from `data_analysis_queries.sql` Version 2.0

**Corrected thresholds for UI filters:**
- "Large lobbying-client donation": **>£25K** (not >£100K)
- "Whale lobbying donor": **>£250K** (not >£1M)
- Only 2 orgs exceed £1M: Unite (£67M), Community (£2.7M)

---

## Key Takeaways

1. **Trade unions dominate even MORE** (96.54% vs. 93.37%)
2. **Total lobbying-client donations are MUCH smaller** (£72.5M vs. £305.7M)
3. **Companies barely donate while lobbying** (£2.3M, only 3.1%)
4. **Foreign influence smaller but still concerning** (£89K vs. £965K)
5. **Political parties receive 94.5%** of lobbying-client donations (even higher concentration)

The corrected story: UK lobbying-client political donations are EXTREMELY concentrated in 3 trade unions (Unite, Community, Community Trade Union), with companies playing a minimal donation role despite extensive lobbying activity.

---

**Last Updated:** 2026-01-13
**Query Version:** 2.0 (Production)
**Report Status:** Corrections documented, full report regeneration pending
