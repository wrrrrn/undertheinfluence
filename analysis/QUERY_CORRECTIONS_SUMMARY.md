# Data Analysis Query Corrections Summary
**Date:** 2026-01-13
**Issue:** Previous queries had multiplicative join inflation
**Solution:** Refactored with non-inflating CTEs and proper aggregation

---

## What Changed

### Problem: Multiplicative Join Inflation

Our original queries joined `datafetch_donation` and `datafetch_consultancy` tables directly, causing donation amounts to be counted multiple times when:
- A lobbying client hired multiple agencies
- A donor made donations across multiple years
- Joins created Cartesian products

### Solution: Pre-Aggregate Then Join

The improved queries:
1. **Pre-aggregate consultancies** per (agency, client)
2. **Pre-aggregate donations** per (donor, recipient)
3. **Join aggregated results** (no multiplication)
4. **Use proper GROUP BY** with all non-aggregated columns
5. **Safe date casting** (check regex before casting to date)

---

## Impact: Corrected Numbers

### Lobbying-Donation Overlap

| Metric | OLD (Inflated) | NEW (Correct) | Difference |
|--------|----------------|---------------|------------|
| **Total donated by lobbying clients** | £305.7M | **£72.5M** | ↓ 76% (4.2x inflation) |
| Organizations that lobby + donate | 62 | 62 | ✓ Same |
| Total donations | 1,714 | 1,714 | ✓ Same |
| Distinct recipients | 235 | 235 | ✓ Same |

**Key Finding:** The total donation value was inflated by 4.2x due to multiplicative joins.

---

### Trade Union Dominance (Even Stronger!)

| Organization Type | OLD % | NEW % | Change |
|-------------------|-------|-------|--------|
| **Trade Unions (3)** | 93.37% | **96.54%** | ↑ 3.17% |
| **Companies (45)** | 6.19% | **3.14%** | ↓ 3.05% |
| Other (8) | 0.37% | 0.24% | ↓ 0.13% |
| LLPs (2) | 0.04% | 0.03% | ↓ 0.01% |
| Unincorp. Assoc. (4) | 0.03% | 0.04% | ↑ 0.01% |

**Corrected totals:**
- Trade Unions: **£70.0M** (was £285.4M)
- Companies: **£2.3M** (was £18.9M)

---

### Recipients of Lobbying-Client Donations

| Recipient Type | OLD Total | NEW Total | OLD % | NEW % |
|----------------|-----------|-----------|-------|-------|
| **Political Parties (4)** | £281.7M | **£68.6M** | 92.2% | **94.5%** |
| **Individual MPs/Lords (221)** | £10.4M | **£2.1M** | 3.4% | **2.9%** |
| **Campaigns/Organizations (10)** | £13.5M | **£1.8M** | 4.4% | **2.5%** |

**Key Finding:** Political parties receive an even HIGHER percentage (94.5% vs. 92.2%) when correctly calculated.

---

### Top Lobbying-Donating Organizations (CORRECTED)

| Rank | Organization | OLD Total | NEW Total | Difference |
|------|--------------|-----------|-----------|------------|
| 1 | **Unite the Union** | £269.0M | **£67.2M** | ↓ £201.8M (4.0x inflated) |
| 2 | **Community** | £16.4M | **£2.7M** | ↓ £13.7M (6.0x inflated!) |
| 3 | **Electoral Reform Society** | £12.4M | **£1.6M** | ↓ £10.8M (7.8x inflated!) |
| 4 | **Manchester Airport Group** | £1.08M | **£120K** | ↓ £960K (9.0x inflated!) |
| 5 | **Quinn Estates Ltd** | £1.36M | **£105K** | ↓ £1.26M (13.0x inflated!) |

**Pattern:** Organizations with multiple consultancy periods had the highest inflation factors.

---

## Why The Differences Matter

### 1. Unite the Union's True Impact

**OLD (Inflated):**
- Unite appeared to donate £269M (88% of lobbying-client donations)
- This suggested massive, coordinated lobbying + donation campaigns

**NEW (Correct):**
- Unite donates £67.2M (92.7% of lobbying-client donations)
- Still massive, but 4x smaller than initially calculated
- More realistic: Unite hires 1 agency (Campaign Collective) with 4 consultancy periods

### 2. Company Donations Much Smaller

**OLD:** Companies donate £18.9M (6.2%)
**NEW:** Companies donate £2.3M (3.1%)

This means **companies that lobby mostly DON'T donate significantly**, even more so than we thought. Lobbying and donations are even MORE separate for corporate clients.

### 3. Individual MPs Receive Less

**OLD:** 221 MPs receive £10.4M (avg £47K each)
**NEW:** 221 MPs receive £2.1M (avg £9.5K each)

Individual MP donations from lobbying clients are **5x smaller** than initially calculated.

---

## Implications for UI Design

### 1. Adjust Value Thresholds

**OLD thresholds (inflated):**
- "Large donation from lobbying client": >£100K
- "Whale lobbying donors": >£1M

**NEW thresholds (realistic):**
- "Large donation from lobbying client": >£25K
- "Whale lobbying donors": >£250K

### 2. Update Messaging

**OLD messaging:** "47 organizations donate £305.7M while lobbying"
**NEW messaging:** "62 organizations donate £72.5M while lobbying"

### 3. Recalibrate Filters

Value filters should use corrected brackets:
- £1K-£10K
- £10K-£50K
- £50K-£250K
- £250K-£1M
- £1M+ (only 2 orgs: Unite £67M, Community £2.7M)

---

## Query Improvements Made

### 1. Safe Date Casting
```sql
-- OLD (breaks on partial dates)
received_date::date

-- NEW (only casts valid YYYY-MM-DD)
CASE WHEN received_date::text ~ '^\d{4}-\d{2}-\d{2}$'
  THEN received_date::date
END
```

### 2. Non-Inflating Joins
```sql
-- OLD (inflates by consultancy count)
FROM datafetch_donation d
JOIN datafetch_consultancy c ON c.client_id = d.donor_id

-- NEW (pre-aggregate)
WITH consultancy_summary AS (
  SELECT client_id, COUNT(*) AS consultancy_count
  FROM datafetch_consultancy
  GROUP BY client_id
),
donation_summary AS (
  SELECT donor_id, SUM(value) AS total_donated
  FROM datafetch_donation
  GROUP BY donor_id
)
SELECT * FROM consultancy_summary cs
JOIN donation_summary ds ON ds.donor_id = cs.client_id
```

### 3. Group By Actor IDs (Not Names)
```sql
-- OLD (can split/merge on name changes)
GROUP BY donor.name

-- NEW (stable across name changes)
GROUP BY donor.id
```

---

## Validation

To verify correctness:

1. **Row counts unchanged:** 1,714 donations, 62 organizations, 235 recipients ✓
2. **Sum of parts = whole:** £70.0M + £2.3M + £177K + £22K + £32K = £72.5M ✓
3. **Individual org sums match:** Unite £67.2M (single aggregation) ✓
4. **No duplicate counting:** Each donation counted exactly once ✓

---

## Conclusion

The corrected queries provide accurate, defensible numbers for Phase 2 UI design. The key corrections:

1. **Total lobbying-client donations: £72.5M** (not £305.7M)
2. **Trade union dominance: 96.54%** (even higher than the inflated 93.37%)
3. **Company donations: £2.3M** (much lower than inflated £18.9M)
4. **Parties receive: 94.5%** (higher concentration than inflated 92.2%)

These numbers tell a **clearer story**: UK political donations from lobbying clients are EXTREMELY concentrated in 3 trade unions, with companies playing a minimal donation role despite extensive lobbying.

---

**Regenerated Reports:**
- `analysis/DATA_INGEST_REPORT.md` - Full analysis with corrected numbers
- `analysis/LOBBYING_DONATION_OVERLAP_SUMMARY.md` - Updated executive summary
- `analysis/data_analysis_queries.sql` - Production-quality SQL suite

**Date:** 2026-01-13
