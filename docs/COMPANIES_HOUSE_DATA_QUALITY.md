# Companies House Data Quality Investigation

This document summarizes the investigation and cleanup of data quality issues discovered in the Companies House enrichment pipeline, specifically around concatenated organization names.

## Problem Summary

During Companies House enrichment, we discovered that ~64% of auto-approved matches in the 85-90% confidence band were partial matches to **concatenated organization names** - where two company names were incorrectly stored as a single organization.

### Example Concatenated Names
```
"Barratt David Wilson Homes" → Should be "Barratt" + "David Wilson Homes"
"Association of the British Pharmaceutical Industry Biogen" → Should be "ABPI" + "Biogen"
"Taylor Wimpey Tesco" → Should be "Taylor Wimpey" + "Tesco"
```

### Root Cause

The PRCA/APPC lobbying register import (`import_appc.py`) was scraping client lists where company names appeared on the same line without proper delimiters. The pattern `CompanyA Ltd CompanyB` was stored as a single organization.

## Impact

Before cleanup:
- **Max agencies per director**: 42 (inflated - same director linked to multiple concatenated orgs)
- **Directors with 10+ agencies**: 531 (inflated)
- **Organizations with concatenated names**: 1,679

## Solution

### 1. Fixed Import Script (`import_appc.py`)

Added `_split_concatenated_clients()` method with:
- Pattern detection: `(Ltd|Limited|PLC|Inc|LLP)` followed by space and capital letter
- Exclusion patterns for false positives (Limited Partnership, T/A, C/o, UK suffix, etc.)
- Statistics tracking for split operations

### 2. Created Cleanup Command (`split_concatenated_orgs.py`)

Management command to split existing concatenated organizations:
- **Regex Splitting:** Detects "Suffix-First" patterns (e.g., `CompanyA Ltd CompanyB`)
- **Match-Based Splitting:** Detects "Prefix/Suffix" patterns using Companies House data
  - Problem: Names like "WWF XLB Property Ltd" or "Tribe TRITAX BIG BOX REIT" lack internal delimiters.
  - Solution: Uses the confirmed Companies House match to identify the split point.
  - Logic: Detects if the CH Match appears at the *start* (Suffix Split) or *end* (Prefix Split) of the name.
  - Safeguard: Verifies the "Match Part" has high similarity (>= 0.90) to the CH record before splitting.
- **Actions:**
  - Renames original org to the "Unknown" part (or "Known" part depending on split type)
  - Creates new org for the other part
  - Clones consultancy relationships to both (conservative approach)
  - Updates match status to 'approved'

### 3. Raised Auto-Approve Threshold & Improved Logic

- Changed auto-approve threshold from 0.85 to 0.90.
- Implemented **Partial Match Penalty** in `companies_house_matcher.py`:
  - Penalizes matches where the organization name has significant unmatched words (2+ unmatched words).
  - Multiplies confidence by 0.7, preventing auto-approval of concatenated names like "Taylor Wimpey Tesco".

### 4. Word Overlap Analysis

Developed SQL analysis to detect partial matches by counting unmatched words between org name and Companies House name.

## Results

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Max agencies/director | 42 | 29 | -31% |
| Directors with 10+ agencies | 531 | 183 | -66% |
| Orgs with concat names (Regex) | 1,679 | ~20 | -99% |
| Match-based splits performed | 0 | 1,637 | +1,637 |
| Auto-approved with 2+ unmatched words | 36.8% | 0.7% | -98% |

## Analysis Scripts

### 1. Confidence Distribution

```sql
-- Confidence distribution by status
SELECT
    CASE
        WHEN confidence >= 0.95 THEN '95-100%'
        WHEN confidence >= 0.90 THEN '90-95%'
        WHEN confidence >= 0.85 THEN '85-90%'
        WHEN confidence >= 0.80 THEN '80-85%'
        WHEN confidence >= 0.75 THEN '75-80%'
        ELSE 'Below 75%'
    END AS confidence_band,
    status,
    COUNT(*) AS count,
    ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER ())::numeric, 1) AS pct
FROM datafetch_companieshousematch
GROUP BY 1, status
ORDER BY 1, status;
```

### 2. Word Overlap Analysis (Detect Partial Matches)

```sql
-- Count unmatched words between org name and CH company name
-- High unmatched word count indicates partial match to concatenated name
WITH matches AS (
    SELECT
        chm.id,
        chm.confidence,
        a.name AS org_name,
        chm.company_name AS ch_name
    FROM datafetch_companieshousematch chm
    JOIN datafetch_organization o ON chm.organization_id = o.actor_ptr_id
    JOIN datafetch_actor a ON o.actor_ptr_id = a.id
    WHERE chm.status = 'auto_approved'
),
word_analysis AS (
    SELECT
        id,
        confidence,
        org_name,
        ch_name,
        (
            SELECT COUNT(*)
            FROM unnest(string_to_array(UPPER(org_name), ' ')) AS word
            WHERE LENGTH(word) > 2
              AND word NOT IN (SELECT unnest(string_to_array(UPPER(ch_name), ' ')))
              AND word NOT IN ('LTD', 'LIMITED', 'PLC', 'INC', 'LLP', 'THE', 'AND', 'OF', 'UK', 'FOR')
        ) AS unmatched_words
    FROM matches
)
SELECT
    unmatched_words,
    COUNT(*) AS count,
    ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER ())::numeric, 1) AS pct
FROM word_analysis
GROUP BY unmatched_words
ORDER BY unmatched_words;
```

### 3. Detect Concatenation Patterns

```sql
-- Find organizations with classic concatenation pattern
-- (Ltd|Limited|PLC|Inc|LLP) followed by space and capital letter
SELECT a.name, chm.company_name, chm.confidence
FROM datafetch_companieshousematch chm
JOIN datafetch_organization o ON chm.organization_id = o.actor_ptr_id
JOIN datafetch_actor a ON o.actor_ptr_id = a.id
WHERE a.name ~ '(Ltd|Limited|PLC|Inc|LLP)\.?\s+[A-Z]'
ORDER BY a.name
LIMIT 50;

-- Broader pattern including Group, Company, Holdings
SELECT a.name
FROM datafetch_organization o
JOIN datafetch_actor a ON o.actor_ptr_id = a.id
WHERE a.name ~ '(Ltd|Limited|PLC|Inc|LLP|Group|Company|Holdings)\.?\s+[A-Z][a-z]'
ORDER BY a.name;
```

### 4. Sample Problematic Matches

```sql
-- View matches with high unmatched word counts
WITH matches AS (
    SELECT
        chm.id,
        chm.confidence,
        a.name AS org_name,
        chm.company_name AS ch_name
    FROM datafetch_companieshousematch chm
    JOIN datafetch_organization o ON chm.organization_id = o.actor_ptr_id
    JOIN datafetch_actor a ON o.actor_ptr_id = a.id
    WHERE chm.status = 'auto_approved'
      AND chm.confidence < 0.90
),
word_analysis AS (
    SELECT
        id,
        confidence,
        org_name,
        ch_name,
        (
            SELECT COUNT(*)
            FROM unnest(string_to_array(UPPER(org_name), ' ')) AS word
            WHERE LENGTH(word) > 2
              AND word NOT IN (SELECT unnest(string_to_array(UPPER(ch_name), ' ')))
              AND word NOT IN ('LTD', 'LIMITED', 'PLC', 'INC', 'LLP', 'THE', 'AND', 'OF', 'UK', 'FOR')
        ) AS unmatched_words
    FROM matches
)
SELECT
    ROUND(confidence::numeric * 100, 1) AS conf_pct,
    org_name,
    ch_name,
    unmatched_words
FROM word_analysis
WHERE unmatched_words >= 2
ORDER BY unmatched_words DESC, confidence DESC
LIMIT 25;
```

### 5. Director/PSC Inflation Check

```sql
-- Check for inflated multi-agency director counts
SELECT
    a.name AS director_name,
    COUNT(DISTINCT m.organization_id) AS agency_count,
    STRING_AGG(DISTINCT oa.name, ', ' ORDER BY oa.name) AS agencies
FROM datafetch_membership m
JOIN datafetch_person p ON m.person_id = p.actor_ptr_id
JOIN datafetch_actor a ON p.actor_ptr_id = a.id
JOIN datafetch_organization o ON m.organization_id = o.actor_ptr_id
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
WHERE m.role = 'Director'
GROUP BY a.name
HAVING COUNT(DISTINCT m.organization_id) > 10
ORDER BY agency_count DESC
LIMIT 20;
```

### 6. Summary Statistics

```sql
-- Overall match quality summary
SELECT
    'Total matches' AS metric, COUNT(*) AS value
FROM datafetch_companieshousematch
UNION ALL
SELECT 'Auto-approved', COUNT(*)
FROM datafetch_companieshousematch WHERE status = 'auto_approved'
UNION ALL
SELECT 'Pending review', COUNT(*)
FROM datafetch_companieshousematch WHERE status = 'pending'
UNION ALL
SELECT 'Orgs with concat pattern', COUNT(*)
FROM datafetch_organization o
JOIN datafetch_actor a ON o.actor_ptr_id = a.id
WHERE a.name ~ '(Ltd|Limited|PLC|Inc|LLP)\.?\s+[A-Z]';
```

## Cleanup Commands

### Split Existing Concatenated Organizations

```bash
# Preview changes
docker compose exec api python manage.py split_concatenated_orgs --dry-run --verbose

# Apply changes
docker compose exec api python manage.py split_concatenated_orgs

# Limit to first N organizations
docker compose exec api python manage.py split_concatenated_orgs --limit 100
```

### Move Problematic Matches to Pending

```sql
-- Flag matches with 2+ unmatched words for review
WITH matches AS (
    SELECT
        chm.id,
        a.name AS org_name,
        chm.company_name AS ch_name
    FROM datafetch_companieshousematch chm
    JOIN datafetch_organization o ON chm.organization_id = o.actor_ptr_id
    JOIN datafetch_actor a ON o.actor_ptr_id = a.id
    WHERE chm.status = 'auto_approved'
      AND chm.confidence < 0.90
),
word_analysis AS (
    SELECT
        id,
        (
            SELECT COUNT(*)
            FROM unnest(string_to_array(UPPER(org_name), ' ')) AS word
            WHERE LENGTH(word) > 2
              AND word NOT IN (SELECT unnest(string_to_array(UPPER(ch_name), ' ')))
              AND word NOT IN ('LTD', 'LIMITED', 'PLC', 'INC', 'LLP', 'THE', 'AND', 'OF', 'UK', 'FOR')
        ) AS unmatched_words
    FROM matches
),
to_flag AS (
    SELECT id FROM word_analysis WHERE unmatched_words >= 2
)
UPDATE datafetch_companieshousematch
SET status = 'pending',
    notes = 'Flagged: 2+ unmatched words - likely partial match'
WHERE id IN (SELECT id FROM to_flag);
```

### Delete Invalid Director/PSC Memberships

```sql
-- Delete memberships for orgs without valid CH matches
WITH orgs_without_valid_ch AS (
    SELECT o.actor_ptr_id
    FROM datafetch_organization o
    WHERE NOT EXISTS (
        SELECT 1 FROM datafetch_companieshousematch chm
        WHERE chm.organization_id = o.actor_ptr_id
          AND chm.status IN ('auto_approved', 'manually_approved')
    )
)
DELETE FROM datafetch_membership
WHERE organization_id IN (SELECT actor_ptr_id FROM orgs_without_valid_ch)
  AND (role = 'Director' OR role LIKE 'Beneficial Owner%');
```

## Prevention

### Import Script Improvements

The `import_appc.py` now includes:

1. **Split detection** with exclusion patterns:
   - `Limited Partnership`, `Limited Company`, `Limited Liability`
   - `T/A` (Trading As), `C/o` (Care of) patterns
   - Geographic suffixes (`Ltd UK`, `Limited USA`)
   - `Public Limited Company` (full PLC name)

2. **Statistics tracking**:
   - Agencies created/updated
   - Clients created/existing
   - Consultancies created
   - Concatenated names split

3. **Verbose mode** for debugging:
   ```bash
   docker compose exec api python manage.py import_appc --verbose
   ```

### Enrichment Threshold

Auto-approve threshold raised from 0.85 to 0.90 to reduce false positives:
```bash
# New default
docker compose exec api python manage.py enrich_companies_house --category lobbying_client

# Override if needed
docker compose exec api python manage.py enrich_companies_house --auto-approve-threshold 0.95
```

## Monitoring

Run periodic quality checks:

```bash
# Check confidence distribution
/docker-query "SELECT status, COUNT(*), ROUND((AVG(confidence)*100)::numeric,1) as avg_conf FROM datafetch_companieshousematch GROUP BY status"

# Check for new concatenated patterns
/docker-query "SELECT COUNT(*) FROM datafetch_actor WHERE name ~ '(Ltd|Limited|PLC)\.?\s+[A-Z]'"

# Check director inflation
/docker-query "SELECT MAX(cnt) as max_agencies FROM (SELECT COUNT(DISTINCT organization_id) as cnt FROM datafetch_membership WHERE role='Director' GROUP BY person_id) sub"
```

## Related Files

- `datafetch/management/commands/import_appc.py` - PRCA lobbying register import
- `datafetch/management/commands/split_concatenated_orgs.py` - Cleanup command
- `datafetch/management/commands/enrich_companies_house.py` - CH enrichment
- `datafetch/utils/companies_house_matcher.py` - Matching logic
- `analysis/13_director_psc_analysis.sql` - Director/PSC analysis queries
