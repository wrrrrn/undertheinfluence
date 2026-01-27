-- ============================================================================
-- DONOR CONCENTRATION & DOMINANCE ANALYSIS
-- ============================================================================
-- Purpose: Analyze donor concentration, whale donors, and donation distribution
-- Focus: Who gives the most, concentration patterns, donor types
-- Date: 2026-01-26 (Updated with Canonical Resolution)
-- Database: PostgreSQL
-- ============================================================================


-- ============================================================================
-- SECTION 1: TOP DONORS
-- ============================================================================

-- 1.1 Top 50 Donors by Total Value (Across All Recipients)
-- Uses canonical_donor_id to aggregate duplicate donors
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS donor_type,
  COUNT(d.id) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation,
  MIN(d.received_date) AS first_donation,
  MAX(d.received_date) AS latest_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON COALESCE(d.canonical_donor_id, d.donor_id) = donor.id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.donor_id IS NOT NULL AND d.value > 0
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 50;


-- 1.2 Top Donors to Each Major Party (Last 5 Years)
WITH safe_donations AS (
  SELECT
    d.id,
    d.value,
    d.donor_id,
    d.canonical_donor_id,
    d.recipient_id,
    d.canonical_recipient_id,
    CASE WHEN d.received_date::text ~ '^\d{4}-\d{2}-\d{2}$' THEN d.received_date::date END AS received_dt
  FROM datafetch_donation d
)
SELECT
  party.id AS party_id,
  MAX(party.name) AS party_name,
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(donor_org.classification) AS donor_type,
  COUNT(sd.id) AS donation_count,
  SUM(sd.value) AS total_donated
FROM safe_donations sd
JOIN datafetch_actor donor ON COALESCE(sd.canonical_donor_id, sd.donor_id) = donor.id
JOIN datafetch_actor party ON COALESCE(sd.canonical_recipient_id, sd.recipient_id) = party.id
JOIN datafetch_organization party_org ON party_org.actor_ptr_id = party.id
LEFT JOIN datafetch_organization donor_org ON donor_org.actor_ptr_id = donor.id
WHERE sd.value > 0
  AND party_org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
  AND sd.received_dt >= DATE '2020-01-01'
GROUP BY party.id, donor.id
ORDER BY party_name, total_donated DESC;


-- ============================================================================
-- SECTION 2: CONCENTRATION METRICS
-- ============================================================================

-- 2.1 Whale Donors vs Long Tail (distribution by value brackets)
WITH donor_totals AS (
  SELECT 
    COALESCE(canonical_donor_id, donor_id) AS final_donor_id, 
    SUM(value) AS donor_total
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY COALESCE(canonical_donor_id, donor_id)
),
donor_brackets AS (
  SELECT
    CASE
      WHEN donor_total >= 1000000 THEN '£1M+'
      WHEN donor_total >= 500000 THEN '£500K-£1M'
      WHEN donor_total >= 100000 THEN '£100K-£500K'
      WHEN donor_total >= 50000 THEN '£50K-£100K'
      WHEN donor_total >= 10000 THEN '£10K-£50K'
      ELSE 'Under £10K'
    END AS donor_bracket,
    donor_total
  FROM donor_totals
)
SELECT
  donor_bracket,
  COUNT(*) AS donor_count,
  SUM(donor_total) AS total_value,
  ROUND(AVG(donor_total), 2) AS avg_per_donor,
  ROUND(100.0 * SUM(donor_total) / SUM(SUM(donor_total)) OVER (), 2) AS pct_of_total
FROM donor_brackets
GROUP BY donor_bracket
ORDER BY
  CASE
    WHEN donor_bracket = '£1M+' THEN 1
    WHEN donor_bracket = '£500K-£1M' THEN 2
    WHEN donor_bracket = '£100K-£500K' THEN 3
    WHEN donor_bracket = '£50K-£100K' THEN 4
    WHEN donor_bracket = '£10K-£50K' THEN 5
    ELSE 6
  END;


-- 2.2 Top 1% vs Bottom 99% Concentration
WITH donor_totals AS (
  SELECT
    COALESCE(canonical_donor_id, donor_id) AS final_donor_id,
    SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY COALESCE(canonical_donor_id, donor_id)
),
ranked_donors AS (
  SELECT
    final_donor_id,
    total_donated,
    NTILE(100) OVER (ORDER BY total_donated DESC) AS percentile
  FROM donor_totals
)
SELECT
  CASE WHEN percentile = 1 THEN 'Top 1%' ELSE 'Bottom 99%' END AS donor_group,
  COUNT(DISTINCT final_donor_id) AS donor_count,
  SUM(total_donated) AS total_donated,
  ROUND(AVG(total_donated), 2) AS avg_per_donor,
  ROUND(100.0 * SUM(total_donated) / SUM(SUM(total_donated)) OVER (), 2) AS pct_of_total
FROM ranked_donors
GROUP BY CASE WHEN percentile = 1 THEN 'Top 1%' ELSE 'Bottom 99%' END
ORDER BY total_donated DESC;


-- ============================================================================
-- SECTION 3: DONOR TYPE BREAKDOWN
-- ============================================================================

-- 3.1 Donations by Donor Classification
SELECT
  COALESCE(org.classification, 'Individual') AS donor_classification,
  COUNT(DISTINCT COALESCE(d.canonical_donor_id, d.donor_id)) AS distinct_donors,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation,
  COUNT(DISTINCT COALESCE(d.canonical_recipient_id, d.recipient_id)) AS distinct_recipients,
  ROUND(100.0 * SUM(d.value) / SUM(SUM(d.value)) OVER (), 2) AS pct_of_total
FROM datafetch_donation d
LEFT JOIN datafetch_actor donor ON COALESCE(d.canonical_donor_id, d.donor_id) = donor.id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
GROUP BY COALESCE(org.classification, 'Individual')
ORDER BY total_donated DESC;


-- 3.2 Individual vs Organizational Donors
SELECT
  CASE
    WHEN person.actor_ptr_id IS NOT NULL THEN 'Individual'
    WHEN org.actor_ptr_id IS NOT NULL THEN 'Organization'
    ELSE 'Unknown'
  END AS donor_type,
  COUNT(DISTINCT COALESCE(d.canonical_donor_id, d.donor_id)) AS distinct_donors,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation,
  ROUND(100.0 * SUM(d.value) / SUM(SUM(d.value)) OVER (), 2) AS pct_of_total
FROM datafetch_donation d
JOIN datafetch_actor donor ON COALESCE(d.canonical_donor_id, d.donor_id) = donor.id
LEFT JOIN datafetch_person person ON person.actor_ptr_id = donor.id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
GROUP BY donor_type
ORDER BY total_donated DESC;


-- ============================================================================
-- SECTION 4: REPEAT DONORS
-- ============================================================================

-- 4.1 Donor Frequency Distribution
WITH donor_frequency AS (
  SELECT
    COALESCE(canonical_donor_id, donor_id) AS final_donor_id,
    COUNT(*) AS donation_count,
    SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY COALESCE(canonical_donor_id, donor_id)
),
frequency_brackets AS (
  SELECT
    CASE
      WHEN donation_count = 1 THEN 'One-time donor'
      WHEN donation_count BETWEEN 2 AND 5 THEN '2-5 donations'
      WHEN donation_count BETWEEN 6 AND 10 THEN '6-10 donations'
      WHEN donation_count BETWEEN 11 AND 20 THEN '11-20 donations'
      ELSE '20+ donations'
    END AS frequency_bracket,
    final_donor_id,
    total_donated
  FROM donor_frequency
)
SELECT
  frequency_bracket,
  COUNT(DISTINCT final_donor_id) AS donor_count,
  SUM(total_donated) AS total_donated,
  ROUND(AVG(total_donated), 2) AS avg_per_donor,
  ROUND(100.0 * SUM(total_donated) / SUM(SUM(total_donated)) OVER (), 2) AS pct_of_total
FROM frequency_brackets
GROUP BY frequency_bracket
ORDER BY
  CASE
    WHEN frequency_bracket = '20+ donations' THEN 1
    WHEN frequency_bracket = '11-20 donations' THEN 2
    WHEN frequency_bracket = '6-10 donations' THEN 3
    WHEN frequency_bracket = '2-5 donations' THEN 4
    ELSE 5
  END;


-- 4.2 Top Repeat Donors
WITH donor_metrics AS (
  SELECT
    COALESCE(canonical_donor_id, donor_id) AS final_donor_id,
    COUNT(*) AS donation_count,
    SUM(value) AS total_donated,
    COUNT(DISTINCT COALESCE(canonical_recipient_id, recipient_id)) AS recipients_count,
    MAX(received_date) - MIN(received_date) AS donation_span
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY COALESCE(canonical_donor_id, donor_id)
  HAVING COUNT(*) >= 10
)
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(COALESCE(org.classification, 'Individual')) AS donor_type,
  dm.donation_count,
  dm.total_donated,
  dm.recipients_count,
  ROUND(dm.total_donated::numeric / dm.donation_count, 2) AS avg_per_donation
FROM donor_metrics dm
JOIN datafetch_actor donor ON donor.id = dm.final_donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
GROUP BY donor.id, dm.donation_count, dm.total_donated, dm.recipients_count
ORDER BY donation_count DESC
LIMIT 30;


-- ============================================================================
-- SECTION 5: DONOR DIVERSITY
-- ============================================================================

-- 5.1 How Many Different Recipients Do Donors Fund?
WITH donor_recipient_counts AS (
  SELECT
    COALESCE(canonical_donor_id, donor_id) AS final_donor_id,
    COUNT(DISTINCT COALESCE(canonical_recipient_id, recipient_id)) AS recipients_funded,
    SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY COALESCE(canonical_donor_id, donor_id)
),
recipient_brackets AS (
  SELECT
    CASE
      WHEN recipients_funded = 1 THEN 'Single recipient'
      WHEN recipients_funded BETWEEN 2 AND 5 THEN '2-5 recipients'
      WHEN recipients_funded BETWEEN 6 AND 10 THEN '6-10 recipients'
      ELSE '10+ recipients'
    END AS recipient_bracket,
    final_donor_id,
    total_donated
  FROM donor_recipient_counts
)
SELECT
  recipient_bracket,
  COUNT(DISTINCT final_donor_id) AS donor_count,
  SUM(total_donated) AS total_donated,
  ROUND(AVG(total_donated), 2) AS avg_per_donor,
  ROUND(100.0 * SUM(total_donated) / SUM(SUM(total_donated)) OVER (), 2) AS pct_of_total
FROM recipient_brackets
GROUP BY recipient_bracket
ORDER BY
  CASE
    WHEN recipient_bracket = '10+ recipients' THEN 1
    WHEN recipient_bracket = '6-10 recipients' THEN 2
    WHEN recipient_bracket = '2-5 recipients' THEN 3
    ELSE 4
  END;