-- ============================================================================
-- GRASSROOTS FUNDING ANALYSIS (EXCLUDING WHALES & UNIONS)
-- ============================================================================
-- Purpose: Analyze donations EXCLUDING mega-donors and trade unions
-- Focus: Grassroots individual donors and smaller organizations
-- Date: 2026-01-26 (Updated with Canonical Resolution)
-- Database: PostgreSQL
--
-- EXCLUSIONS:
-- - Trade Unions (classification = 'Trade Union')
-- - Whale Donors (total donations >= £500,000)
-- ============================================================================


-- ============================================================================
-- SECTION 1: DEFINE EXCLUSIONS
-- ============================================================================

-- 1.1 Identify Whale Donors and Unions
WITH donor_totals AS (
  SELECT
    COALESCE(canonical_donor_id, donor_id) as donor_id,
    SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE value > 0
  GROUP BY COALESCE(canonical_donor_id, donor_id)
),
whale_donors AS (
  SELECT donor_id FROM donor_totals WHERE total_donated >= 500000
),
trade_unions AS (
  SELECT actor_ptr_id AS donor_id
  FROM datafetch_organization
  WHERE classification ILIKE '%union%'
)
SELECT
  'Whale Donors (£500K+)' AS category,
  (SELECT COUNT(*) FROM whale_donors) AS count,
  (SELECT SUM(d.value) FROM datafetch_donation d WHERE COALESCE(d.canonical_donor_id, d.donor_id) IN (SELECT donor_id FROM whale_donors)) AS value
UNION ALL
SELECT
  'Trade Unions',
  (SELECT COUNT(*) FROM trade_unions),
  (SELECT SUM(d.value) FROM datafetch_donation d WHERE COALESCE(d.canonical_donor_id, d.donor_id) IN (SELECT donor_id FROM trade_unions));


-- ============================================================================
-- SECTION 2: PARTY FUNDING WITHOUT WHALES & UNIONS
-- ============================================================================

-- 2.1 Party Funding Comparison
WITH donor_totals AS (
  SELECT COALESCE(canonical_donor_id, donor_id) as donor_id, SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE value > 0
  GROUP BY COALESCE(canonical_donor_id, donor_id)
),
whales_unions AS (
    SELECT donor_id FROM donor_totals WHERE total_donated >= 500000
    UNION
    SELECT actor_ptr_id FROM datafetch_organization WHERE classification ILIKE '%union%'
),
party_funding AS (
    SELECT
        COALESCE(d.canonical_recipient_id, d.recipient_id) as party_id,
        SUM(d.value) as total_all,
        SUM(CASE WHEN wu.donor_id IS NULL THEN d.value ELSE 0 END) as total_grassroots
    FROM datafetch_donation d
    LEFT JOIN whales_unions wu ON COALESCE(d.canonical_donor_id, d.donor_id) = wu.donor_id
    JOIN datafetch_organization org ON org.actor_ptr_id = COALESCE(d.canonical_recipient_id, d.recipient_id)
    WHERE d.value > 0 AND org.classification ILIKE '%Party%'
    GROUP BY COALESCE(d.canonical_recipient_id, d.recipient_id)
)
SELECT
    p.name as party,
    pf.total_all,
    pf.total_grassroots,
    ROUND(100.0 * pf.total_grassroots / NULLIF(pf.total_all, 0), 2) as pct_grassroots
FROM party_funding pf
JOIN datafetch_actor p ON pf.party_id = p.id
ORDER BY pf.total_all DESC;


-- ============================================================================
-- SECTION 3: TOP GRASSROOTS RECIPIENTS (MPs)
-- ============================================================================

-- 3.1 Top MPs by Grassroots Donations
WITH donor_totals AS (
  SELECT COALESCE(canonical_donor_id, donor_id) as donor_id, SUM(value) AS total_donated
  FROM datafetch_donation WHERE value > 0 GROUP BY COALESCE(canonical_donor_id, donor_id)
),
whales_unions AS (
    SELECT donor_id FROM donor_totals WHERE total_donated >= 500000
    UNION
    SELECT actor_ptr_id FROM datafetch_organization WHERE classification ILIKE '%union%'
)
SELECT
    p.name as mp_name,
    COUNT(*) as donation_count,
    SUM(d.value) as total_grassroots
FROM datafetch_donation d
LEFT JOIN whales_unions wu ON COALESCE(d.canonical_donor_id, d.donor_id) = wu.donor_id
JOIN datafetch_person p ON p.actor_ptr_id = COALESCE(d.canonical_recipient_id, d.recipient_id)
JOIN datafetch_actor a ON p.actor_ptr_id = a.id
WHERE d.value > 0 AND wu.donor_id IS NULL
GROUP BY p.actor_ptr_id, p.name, a.name
ORDER BY total_grassroots DESC
LIMIT 50;