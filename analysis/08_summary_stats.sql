-- ============================================================================
-- SUMMARY STATISTICS & DATA QUALITY
-- ============================================================================
-- Purpose: Database overview, data quality checks, and aggregate statistics
-- Focus: Record counts, date ranges, null analysis, classification stats
-- Date: 2026-01-19
-- Database: PostgreSQL
-- ============================================================================

-- SECTION 7: SECTOR & CLASSIFICATION ANALYSIS
-- ============================================================================

-- 7.1 Donations by Donor Classification
SELECT
  COALESCE(org.classification, 'Unclassified/Individual') AS donor_classification,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  COUNT(DISTINCT d.donor_id) AS distinct_donors,
  COUNT(DISTINCT d.recipient_id) AS distinct_recipients,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = d.donor_id
WHERE d.value > 0
GROUP BY COALESCE(org.classification, 'Unclassified/Individual')
ORDER BY total_donated DESC;


-- 7.2 Lobbying Clients by Classification
SELECT
  COALESCE(client_org.classification, 'Unclassified') AS client_type,
  COUNT(DISTINCT c.client_id) AS distinct_clients,
  COUNT(DISTINCT c.agency_id) AS distinct_agencies,
  COUNT(*) AS consultancy_count
FROM datafetch_consultancy c
LEFT JOIN datafetch_organization client_org ON client_org.actor_ptr_id = c.client_id
GROUP BY COALESCE(client_org.classification, 'Unclassified')
ORDER BY distinct_clients DESC;


-- ============================================================================
-- SECTION 8: DATA QUALITY CHECKS
-- ============================================================================

-- 8.1 Null Donor Analysis (by donation type)
SELECT
  donation_type,
  COUNT(*) AS total_count,
  COUNT(*) FILTER (WHERE donor_id IS NULL) AS null_donor_count,
  ROUND(100.0 * COUNT(*) FILTER (WHERE donor_id IS NULL) / COUNT(*), 1) AS null_donor_pct,
  COUNT(DISTINCT recipient_id) AS distinct_recipients
FROM datafetch_donation
GROUP BY donation_type
ORDER BY null_donor_count DESC;


-- ============================================================================
-- SECTION 9: SUMMARY STATISTICS
-- ============================================================================

-- 9.1 Database Overview
SELECT 'Total Persons' AS metric, COUNT(*) AS count FROM datafetch_person
UNION ALL
SELECT 'Total Organizations', COUNT(*) FROM datafetch_organization
UNION ALL
SELECT 'Total Donations', COUNT(*) FROM datafetch_donation
UNION ALL
SELECT 'Donations with Value > 0', COUNT(*) FROM datafetch_donation WHERE value > 0
UNION ALL
SELECT 'Donations with Donor NULL', COUNT(*) FROM datafetch_donation WHERE donor_id IS NULL
UNION ALL
SELECT 'Total Consultancies', COUNT(*) FROM datafetch_consultancy
UNION ALL
SELECT 'Total Memberships', COUNT(*) FROM datafetch_membership
UNION ALL
SELECT 'Ministerial Memberships', COUNT(*) FROM datafetch_membership WHERE role IS NOT NULL AND role <> '';


-- 9.2 Date Range Coverage (safe casting)
WITH safe_donations AS (
  SELECT
    CASE WHEN received_date::text ~ '^\d{4}-\d{2}-\d{2}$' THEN received_date::date END AS received_dt
  FROM datafetch_donation
)
SELECT 'Earliest Donation' AS metric, MIN(received_dt)::text AS date_value
FROM safe_donations
WHERE received_dt IS NOT NULL
UNION ALL
SELECT 'Latest Donation', MAX(received_dt)::text
FROM safe_donations
WHERE received_dt IS NOT NULL;


-- ============================================================================
-- APPENDIX: TIME-BASED ANALYSIS (SAFE DATE CASTING)
-- ============================================================================

-- A.1 Donations by Year (Lobbying Clients Only)
WITH lobbying_clients AS (
  SELECT DISTINCT client_id FROM datafetch_consultancy
),
safe_donations AS (
  SELECT
    d.*,
    CASE WHEN d.received_date::text ~ '^\d{4}-\d{2}-\d{2}$' THEN d.received_date::date END AS received_dt
  FROM datafetch_donation d
  WHERE d.donor_id IN (SELECT client_id FROM lobbying_clients)
    AND d.value > 0
)
SELECT
  EXTRACT(YEAR FROM received_dt) AS year,
  COUNT(DISTINCT donor_id) AS active_lobbying_donors,
  COUNT(*) AS donation_count,
  SUM(value) AS total_donated,
  ROUND(AVG(value), 2) AS avg_donation
FROM safe_donations
WHERE received_dt IS NOT NULL
GROUP BY EXTRACT(YEAR FROM received_dt)
ORDER BY year DESC;


-- ============================================================================
-- END OF QUERY SUITE
-- ============================================================================

-- ============================================================================
-- END OF SUMMARY STATISTICS & DATA QUALITY
-- ============================================================================
