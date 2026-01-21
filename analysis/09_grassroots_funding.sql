-- ============================================================================
-- GRASSROOTS FUNDING ANALYSIS (EXCLUDING WHALES & UNIONS)
-- ============================================================================
-- Purpose: Analyze donations EXCLUDING mega-donors and trade unions
-- Focus: Grassroots individual donors and smaller organizations
-- Date: 2026-01-19
-- Database: PostgreSQL
--
-- EXCLUSIONS:
-- - Trade Unions (classification = 'Trade Union')
-- - Whale Donors (total donations >= £500,000)
-- - Large single donations (>= £50,000)
-- ============================================================================


-- ============================================================================
-- SECTION 0: DEFINE EXCLUSIONS
-- ============================================================================

-- 0.1 Identify Whale Donors (£500K+ lifetime total)
-- Use this as a reference for what we're excluding
WITH donor_totals AS (
  SELECT
    donor_id,
    SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY donor_id
),
whale_donors AS (
  SELECT donor_id
  FROM donor_totals
  WHERE total_donated >= 500000
),
trade_unions AS (
  SELECT actor_ptr_id AS donor_id
  FROM datafetch_organization
  WHERE classification = 'Trade Union'
)
SELECT
  'Whale Donors (£500K+)' AS exclusion_type,
  (SELECT COUNT(*) FROM whale_donors) AS donor_count,
  (SELECT SUM(d.value) FROM datafetch_donation d WHERE d.donor_id IN (SELECT donor_id FROM whale_donors) AND d.value > 0) AS total_excluded
UNION ALL
SELECT
  'Trade Unions',
  (SELECT COUNT(*) FROM trade_unions),
  (SELECT SUM(d.value) FROM datafetch_donation d WHERE d.donor_id IN (SELECT donor_id FROM trade_unions) AND d.value > 0)
UNION ALL
SELECT
  'Total Donations (All)',
  (SELECT COUNT(DISTINCT donor_id) FROM datafetch_donation WHERE donor_id IS NOT NULL AND value > 0),
  (SELECT SUM(value) FROM datafetch_donation WHERE value > 0);


-- ============================================================================
-- SECTION 1: GRASSROOTS DONOR ANALYSIS
-- ============================================================================

-- 1.1 Top Grassroots Donors (Excluding Whales & Unions)
WITH donor_totals AS (
  SELECT
    donor_id,
    SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY donor_id
),
whale_donors AS (
  SELECT donor_id FROM donor_totals WHERE total_donated >= 500000
),
trade_unions AS (
  SELECT actor_ptr_id FROM datafetch_organization WHERE classification = 'Trade Union'
),
grassroots_donations AS (
  SELECT d.*
  FROM datafetch_donation d
  WHERE d.value > 0
    AND d.donor_id NOT IN (SELECT donor_id FROM whale_donors)
    AND d.donor_id NOT IN (SELECT actor_ptr_id FROM trade_unions)
)
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(COALESCE(org.classification, 'Individual')) AS donor_type,
  COUNT(gd.id) AS donation_count,
  SUM(gd.value) AS total_donated,
  ROUND(AVG(gd.value), 2) AS avg_donation,
  COUNT(DISTINCT gd.recipient_id) AS recipients_funded,
  MIN(gd.received_date) AS first_donation,
  MAX(gd.received_date) AS latest_donation
FROM grassroots_donations gd
JOIN datafetch_actor donor ON donor.id = gd.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 50;


-- 1.2 Grassroots Donor Concentration (Without Whales/Unions)
WITH donor_totals AS (
  SELECT
    donor_id,
    SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY donor_id
),
whale_donors AS (
  SELECT donor_id FROM donor_totals WHERE total_donated >= 500000
),
trade_unions AS (
  SELECT actor_ptr_id FROM datafetch_organization WHERE classification = 'Trade Union'
),
grassroots_donor_totals AS (
  SELECT
    donor_id,
    total_donated
  FROM donor_totals
  WHERE donor_id NOT IN (SELECT donor_id FROM whale_donors)
    AND donor_id NOT IN (SELECT actor_ptr_id FROM trade_unions)
),
grassroots_brackets AS (
  SELECT
    CASE
      WHEN total_donated >= 100000 THEN '£100K-£500K'
      WHEN total_donated >= 50000 THEN '£50K-£100K'
      WHEN total_donated >= 10000 THEN '£10K-£50K'
      WHEN total_donated >= 5000 THEN '£5K-£10K'
      WHEN total_donated >= 1000 THEN '£1K-£5K'
      ELSE 'Under £1K'
    END AS donor_bracket,
    total_donated
  FROM grassroots_donor_totals
)
SELECT
  donor_bracket,
  COUNT(*) AS donor_count,
  SUM(total_donated) AS total_value,
  ROUND(AVG(total_donated), 2) AS avg_per_donor,
  ROUND(100.0 * SUM(total_donated) / SUM(SUM(total_donated)) OVER (), 2) AS pct_of_grassroots_total
FROM grassroots_brackets
GROUP BY donor_bracket
ORDER BY
  CASE
    WHEN donor_bracket = '£100K-£500K' THEN 1
    WHEN donor_bracket = '£50K-£100K' THEN 2
    WHEN donor_bracket = '£10K-£50K' THEN 3
    WHEN donor_bracket = '£5K-£10K' THEN 4
    WHEN donor_bracket = '£1K-£5K' THEN 5
    ELSE 6
  END;


-- 1.3 Individual-Only Donors (No Organizations at All)
-- Pure grassroots: only individual people donating
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  COUNT(d.id) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation,
  COUNT(DISTINCT d.recipient_id) AS recipients_funded,
  MIN(d.received_date) AS first_donation,
  MAX(d.received_date) AS latest_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
JOIN datafetch_person person ON person.actor_ptr_id = donor.id  -- Must be a person
WHERE d.value > 0
  AND d.value < 50000  -- Exclude large single donations
GROUP BY donor.id
HAVING SUM(d.value) < 500000  -- Exclude whales
ORDER BY total_donated DESC
LIMIT 50;


-- ============================================================================
-- SECTION 2: PARTY FUNDING WITHOUT WHALES & UNIONS
-- ============================================================================

-- 2.1 Party Funding (Grassroots Only)
WITH donor_totals AS (
  SELECT donor_id, SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY donor_id
),
whale_donors AS (
  SELECT donor_id FROM donor_totals WHERE total_donated >= 500000
),
trade_unions AS (
  SELECT actor_ptr_id FROM datafetch_organization WHERE classification = 'Trade Union'
),
grassroots_party_donations AS (
  SELECT
    d.recipient_id,
    d.donor_id,
    d.value
  FROM datafetch_donation d
  JOIN datafetch_organization org ON org.actor_ptr_id = d.recipient_id
  WHERE d.value > 0
    AND org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
    AND d.donor_id NOT IN (SELECT donor_id FROM whale_donors)
    AND d.donor_id NOT IN (SELECT actor_ptr_id FROM trade_unions)
)
SELECT
  party.id AS party_id,
  MAX(party.name) AS party_name,
  COUNT(*) AS donation_count,
  COUNT(DISTINCT gpd.donor_id) AS distinct_donors,
  SUM(gpd.value) AS total_received,
  ROUND(AVG(gpd.value), 2) AS avg_donation,
  ROUND(SUM(gpd.value)::numeric / COUNT(DISTINCT gpd.donor_id), 2) AS avg_per_donor
FROM grassroots_party_donations gpd
JOIN datafetch_actor party ON party.id = gpd.recipient_id
GROUP BY party.id
ORDER BY total_received DESC;


-- 2.2 Party Funding Comparison: With vs Without Whales/Unions
WITH donor_totals AS (
  SELECT donor_id, SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY donor_id
),
whale_donors AS (
  SELECT donor_id FROM donor_totals WHERE total_donated >= 500000
),
trade_unions AS (
  SELECT actor_ptr_id FROM datafetch_organization WHERE classification = 'Trade Union'
),
party_all AS (
  SELECT
    d.recipient_id AS party_id,
    SUM(d.value) AS total_all
  FROM datafetch_donation d
  JOIN datafetch_organization org ON org.actor_ptr_id = d.recipient_id
  WHERE d.value > 0
    AND org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
  GROUP BY d.recipient_id
),
party_grassroots AS (
  SELECT
    d.recipient_id AS party_id,
    SUM(d.value) AS total_grassroots
  FROM datafetch_donation d
  JOIN datafetch_organization org ON org.actor_ptr_id = d.recipient_id
  WHERE d.value > 0
    AND org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
    AND d.donor_id NOT IN (SELECT donor_id FROM whale_donors)
    AND d.donor_id NOT IN (SELECT actor_ptr_id FROM trade_unions)
  GROUP BY d.recipient_id
)
SELECT
  party.id AS party_id,
  MAX(party.name) AS party_name,
  COALESCE(pa.total_all, 0) AS total_all_donations,
  COALESCE(pg.total_grassroots, 0) AS total_grassroots_only,
  COALESCE(pa.total_all, 0) - COALESCE(pg.total_grassroots, 0) AS total_from_whales_unions,
  ROUND(100.0 * COALESCE(pg.total_grassroots, 0) / NULLIF(pa.total_all, 0), 2) AS pct_from_grassroots
FROM datafetch_actor party
JOIN datafetch_organization party_org ON party_org.actor_ptr_id = party.id
LEFT JOIN party_all pa ON pa.party_id = party.id
LEFT JOIN party_grassroots pg ON pg.party_id = party.id
WHERE party_org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
  AND (pa.total_all IS NOT NULL OR pg.total_grassroots IS NOT NULL)
GROUP BY party.id, pa.total_all, pg.total_grassroots
ORDER BY total_all_donations DESC;


-- 2.3 Which Parties Depend Most on Whales/Unions?
-- Shows vulnerability to losing large donors
WITH donor_totals AS (
  SELECT donor_id, SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY donor_id
),
whale_donors AS (
  SELECT donor_id FROM donor_totals WHERE total_donated >= 500000
),
trade_unions AS (
  SELECT actor_ptr_id FROM datafetch_organization WHERE classification = 'Trade Union'
),
party_all AS (
  SELECT
    d.recipient_id AS party_id,
    SUM(d.value) AS total_all
  FROM datafetch_donation d
  JOIN datafetch_organization org ON org.actor_ptr_id = d.recipient_id
  WHERE d.value > 0
    AND org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
  GROUP BY d.recipient_id
),
party_whales_unions AS (
  SELECT
    d.recipient_id AS party_id,
    SUM(d.value) AS total_from_whales_unions
  FROM datafetch_donation d
  JOIN datafetch_organization org ON org.actor_ptr_id = d.recipient_id
  WHERE d.value > 0
    AND org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
    AND (
      d.donor_id IN (SELECT donor_id FROM whale_donors)
      OR d.donor_id IN (SELECT actor_ptr_id FROM trade_unions)
    )
  GROUP BY d.recipient_id
)
SELECT
  party.id AS party_id,
  MAX(party.name) AS party_name,
  pa.total_all AS total_donations,
  COALESCE(pwu.total_from_whales_unions, 0) AS from_whales_unions,
  pa.total_all - COALESCE(pwu.total_from_whales_unions, 0) AS from_grassroots,
  ROUND(100.0 * COALESCE(pwu.total_from_whales_unions, 0) / pa.total_all, 2) AS pct_from_whales_unions
FROM party_all pa
JOIN datafetch_actor party ON party.id = pa.party_id
LEFT JOIN party_whales_unions pwu ON pwu.party_id = pa.party_id
GROUP BY party.id, pa.total_all, pwu.total_from_whales_unions
ORDER BY pct_from_whales_unions DESC;


-- ============================================================================
-- SECTION 3: MP FUNDING WITHOUT WHALES & UNIONS
-- ============================================================================

-- 3.1 Top MPs by Grassroots Donations
WITH donor_totals AS (
  SELECT donor_id, SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY donor_id
),
whale_donors AS (
  SELECT donor_id FROM donor_totals WHERE total_donated >= 500000
),
trade_unions AS (
  SELECT actor_ptr_id FROM datafetch_organization WHERE classification = 'Trade Union'
),
grassroots_mp_donations AS (
  SELECT
    d.recipient_id,
    d.donor_id,
    d.value
  FROM datafetch_donation d
  JOIN datafetch_person person ON person.actor_ptr_id = d.recipient_id
  WHERE d.value > 0
    AND d.donor_id NOT IN (SELECT donor_id FROM whale_donors)
    AND d.donor_id NOT IN (SELECT actor_ptr_id FROM trade_unions)
)
SELECT
  mp.id AS mp_id,
  MAX(mp.name) AS mp_name,
  COUNT(*) AS donation_count,
  COUNT(DISTINCT gmd.donor_id) AS distinct_donors,
  SUM(gmd.value) AS total_received,
  ROUND(AVG(gmd.value), 2) AS avg_donation,
  ROUND(SUM(gmd.value)::numeric / COUNT(DISTINCT gmd.donor_id), 2) AS avg_per_donor
FROM grassroots_mp_donations gmd
JOIN datafetch_actor mp ON mp.id = gmd.recipient_id
GROUP BY mp.id
ORDER BY total_received DESC
LIMIT 50;


-- 3.2 Ministers: Grassroots vs Whale/Union Funding
WITH donor_totals AS (
  SELECT donor_id, SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY donor_id
),
whale_donors AS (
  SELECT donor_id FROM donor_totals WHERE total_donated >= 500000
),
trade_unions AS (
  SELECT actor_ptr_id FROM datafetch_organization WHERE classification = 'Trade Union'
),
current_ministers AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.role IS NOT NULL
    AND m.role != ''
    AND m.role NOT LIKE '%Member of Parliament%'
    AND m.role NOT LIKE '%MSP for%'
    AND (m.end_date IS NULL OR m.end_date = '' OR m.end_date >= CURRENT_DATE::text)
),
minister_all_donations AS (
  SELECT
    cm.person_id,
    SUM(d.value) AS total_all
  FROM current_ministers cm
  JOIN datafetch_donation d ON d.recipient_id = cm.person_id
  WHERE d.value > 0
  GROUP BY cm.person_id
),
minister_grassroots_donations AS (
  SELECT
    cm.person_id,
    SUM(d.value) AS total_grassroots
  FROM current_ministers cm
  JOIN datafetch_donation d ON d.recipient_id = cm.person_id
  WHERE d.value > 0
    AND d.donor_id NOT IN (SELECT donor_id FROM whale_donors)
    AND d.donor_id NOT IN (SELECT actor_ptr_id FROM trade_unions)
  GROUP BY cm.person_id
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  COALESCE(mad.total_all, 0) AS total_all_donations,
  COALESCE(mgd.total_grassroots, 0) AS total_grassroots,
  COALESCE(mad.total_all, 0) - COALESCE(mgd.total_grassroots, 0) AS from_whales_unions,
  ROUND(100.0 * COALESCE(mgd.total_grassroots, 0) / NULLIF(mad.total_all, 0), 2) AS pct_from_grassroots
FROM current_ministers cm
JOIN datafetch_actor person ON person.id = cm.person_id
LEFT JOIN minister_all_donations mad ON mad.person_id = cm.person_id
LEFT JOIN minister_grassroots_donations mgd ON mgd.person_id = cm.person_id
WHERE mad.total_all IS NOT NULL
GROUP BY person.id, mad.total_all, mgd.total_grassroots
ORDER BY total_all_donations DESC;


-- ============================================================================
-- SECTION 4: SECTOR ANALYSIS (GRASSROOTS DONORS ONLY)
-- ============================================================================

-- 4.1 Grassroots Donors by Sector (Excluding Whales/Unions)
WITH donor_totals AS (
  SELECT donor_id, SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY donor_id
),
whale_donors AS (
  SELECT donor_id FROM donor_totals WHERE total_donated >= 500000
),
donor_sectors AS (
  SELECT
    donor.id AS donor_id,
    CASE
      WHEN LOWER(donor.name) LIKE '%bank%' OR LOWER(donor.name) LIKE '%financial%' THEN 'Financial Services'
      WHEN LOWER(donor.name) LIKE '%farm%' OR LOWER(donor.name) LIKE '%agricult%' THEN 'Agriculture & Food'
      WHEN LOWER(donor.name) LIKE '%energy%' OR LOWER(donor.name) LIKE '%power%' THEN 'Energy & Utilities'
      WHEN LOWER(donor.name) LIKE '%tech%' OR LOWER(donor.name) LIKE '%software%' THEN 'Technology'
      WHEN LOWER(donor.name) LIKE '%health%' OR LOWER(donor.name) LIKE '%pharma%' THEN 'Healthcare & Pharma'
      WHEN org.classification = 'Trade Union' THEN 'Trade Union'
      WHEN org.actor_ptr_id IS NULL THEN 'Individual'
      ELSE 'Other Organization'
    END AS sector
  FROM datafetch_actor donor
  LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
  WHERE donor.id IN (SELECT DISTINCT donor_id FROM datafetch_donation WHERE donor_id IS NOT NULL)
),
grassroots_sector_donations AS (
  SELECT
    ds.sector,
    d.value,
    d.donor_id,
    d.recipient_id
  FROM datafetch_donation d
  JOIN donor_sectors ds ON ds.donor_id = d.donor_id
  WHERE d.value > 0
    AND d.donor_id NOT IN (SELECT donor_id FROM whale_donors)
    AND ds.sector != 'Trade Union'  -- Exclude unions
)
SELECT
  sector,
  COUNT(DISTINCT donor_id) AS distinct_donors,
  COUNT(DISTINCT recipient_id) AS distinct_recipients,
  COUNT(*) AS total_donations,
  SUM(value) AS total_donated,
  ROUND(AVG(value), 2) AS avg_donation,
  ROUND(100.0 * SUM(value) / SUM(SUM(value)) OVER (), 2) AS pct_of_grassroots_total
FROM grassroots_sector_donations
GROUP BY sector
ORDER BY total_donated DESC;


-- ============================================================================
-- SECTION 5: SMALL DONOR ANALYSIS (Under £1,000)
-- ============================================================================

-- 5.1 Small Donors Only (Individual donations under £1,000)
-- The true grassroots base
SELECT
  recipient.id AS recipient_id,
  MAX(recipient.name) AS recipient_name,
  CASE
    WHEN person.actor_ptr_id IS NOT NULL THEN 'Individual MP/Lord'
    WHEN recipient_org.classification IN ('Political Party', 'Registered Political Party') THEN 'Political Party'
    ELSE 'Organization'
  END AS recipient_type,
  COUNT(*) AS small_donation_count,
  COUNT(DISTINCT d.donor_id) AS distinct_small_donors,
  SUM(d.value) AS total_from_small_donors,
  ROUND(AVG(d.value), 2) AS avg_small_donation
FROM datafetch_donation d
JOIN datafetch_actor recipient ON recipient.id = d.recipient_id
LEFT JOIN datafetch_person person ON person.actor_ptr_id = recipient.id
LEFT JOIN datafetch_organization recipient_org ON recipient_org.actor_ptr_id = recipient.id
WHERE d.value > 0
  AND d.value < 1000  -- Small donations only
GROUP BY recipient.id, recipient_type
HAVING SUM(d.value) > 10000  -- Must have at least £10K from small donors
ORDER BY total_from_small_donors DESC
LIMIT 50;


-- 5.2 Parties Ranked by Small Donor Count
-- Who has the broadest base of small supporters?
SELECT
  party.id AS party_id,
  MAX(party.name) AS party_name,
  COUNT(DISTINCT d.donor_id) AS small_donor_count,
  COUNT(*) AS small_donation_count,
  SUM(d.value) AS total_from_small_donors,
  ROUND(AVG(d.value), 2) AS avg_small_donation
FROM datafetch_donation d
JOIN datafetch_actor party ON party.id = d.recipient_id
JOIN datafetch_organization org ON org.actor_ptr_id = party.id
WHERE d.value > 0
  AND d.value < 1000  -- Small donations only
  AND org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
GROUP BY party.id
ORDER BY small_donor_count DESC;


-- ============================================================================
-- SECTION 6: SUMMARY STATISTICS
-- ============================================================================

-- 6.1 Overall Impact of Excluding Whales & Unions
WITH donor_totals AS (
  SELECT donor_id, SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY donor_id
),
whale_donors AS (
  SELECT donor_id FROM donor_totals WHERE total_donated >= 500000
),
trade_unions AS (
  SELECT actor_ptr_id FROM datafetch_organization WHERE classification = 'Trade Union'
)
SELECT
  'All Donations' AS category,
  COUNT(DISTINCT donor_id) AS donor_count,
  COUNT(*) AS donation_count,
  SUM(value) AS total_value
FROM datafetch_donation
WHERE value > 0

UNION ALL

SELECT
  'Grassroots (No Whales/Unions)',
  COUNT(DISTINCT donor_id),
  COUNT(*),
  SUM(value)
FROM datafetch_donation
WHERE value > 0
  AND donor_id NOT IN (SELECT donor_id FROM whale_donors)
  AND donor_id NOT IN (SELECT actor_ptr_id FROM trade_unions)

UNION ALL

SELECT
  'Whales Only (£500K+)',
  COUNT(DISTINCT donor_id),
  COUNT(*),
  SUM(value)
FROM datafetch_donation
WHERE value > 0
  AND donor_id IN (SELECT donor_id FROM whale_donors)

UNION ALL

SELECT
  'Trade Unions Only',
  COUNT(DISTINCT donor_id),
  COUNT(*),
  SUM(value)
FROM datafetch_donation
WHERE value > 0
  AND donor_id IN (SELECT actor_ptr_id FROM trade_unions);


-- ============================================================================
-- END OF GRASSROOTS FUNDING ANALYSIS
-- ============================================================================
