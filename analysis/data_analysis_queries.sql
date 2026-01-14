-- ============================================================================
-- UnderTheInfluence Data Analysis Query Suite (PRODUCTION VERSION)
-- ============================================================================
-- Purpose: Comprehensive analysis queries to inform UI design for Phase 2
-- Date: 2026-01-13
-- Version: 2.0 (Refactored for accuracy and performance)
--
-- Key improvements:
-- - Group by Actor IDs (not names) to avoid split/merge artifacts
-- - Safe date casting (only cast valid YYYY-MM-DD strings)
-- - Avoid multiplicative joins between donations and consultancies
-- - Define reusable CTEs for common patterns
-- - Fix GenericRelation content_type handling (uses IN list)
--
-- Database: PostgreSQL
-- Schema: Popolo-based (datafetch_actor, _organization, _person, _donation, _consultancy, _membership)
-- ============================================================================


-- ============================================================================
-- SECTION 1: CONCENTRATION & DOMINANCE
-- ============================================================================

-- 1.1 Top 20 Donors by Total Value (Across All Recipients)
-- Groups by donor_id to avoid name-based duplicates
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
JOIN datafetch_actor donor ON d.donor_id = donor.id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.donor_id IS NOT NULL AND d.value > 0
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 20;


-- 1.2 Top Donors to Each Major Party (Last 5 Years)
-- Safe date filter using regex check before casting
WITH safe_donations AS (
  SELECT
    d.*,
    CASE WHEN d.received_date ~ '^\d{4}-\d{2}-\d{2}$' THEN d.received_date::date END AS received_dt
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
JOIN datafetch_actor donor ON sd.donor_id = donor.id
JOIN datafetch_actor party ON sd.recipient_id = party.id
JOIN datafetch_organization party_org ON party_org.actor_ptr_id = party.id
LEFT JOIN datafetch_organization donor_org ON donor_org.actor_ptr_id = donor.id
WHERE sd.value > 0
  AND LOWER(COALESCE(party_org.classification,'')) = 'party'
  AND sd.received_dt >= DATE '2020-01-01'
GROUP BY party.id, donor.id
ORDER BY party_name, total_donated DESC;


-- 1.3 Whale Donors vs Long Tail (distribution by value brackets)
WITH donor_totals AS (
  SELECT donor_id, SUM(value) AS donor_total
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY donor_id
)
SELECT
  CASE
    WHEN donor_total >= 1000000 THEN '£1M+'
    WHEN donor_total >= 500000 THEN '£500K-£1M'
    WHEN donor_total >= 100000 THEN '£100K-£500K'
    WHEN donor_total >= 50000 THEN '£50K-£100K'
    WHEN donor_total >= 10000 THEN '£10K-£50K'
    ELSE 'Under £10K'
  END AS donor_bracket,
  COUNT(*) AS donor_count,
  SUM(donor_total) AS total_value,
  ROUND(AVG(donor_total), 2) AS avg_per_donor,
  ROUND(100.0 * SUM(donor_total) / SUM(SUM(donor_total)) OVER (), 2) AS pct_of_total
FROM donor_totals
GROUP BY 1
ORDER BY
  CASE
    WHEN donor_bracket = '£1M+' THEN 1
    WHEN donor_bracket = '£500K-£1M' THEN 2
    WHEN donor_bracket = '£100K-£500K' THEN 3
    WHEN donor_bracket = '£50K-£100K' THEN 4
    WHEN donor_bracket = '£10K-£50K' THEN 5
    ELSE 6
  END;


-- ============================================================================
-- SECTION 2: LOBBYING-DONATION CONNECTIONS (NON-INFLATING JOINS)
-- ============================================================================

-- 2.1 Organizations That Both Lobby AND Donate
-- Stable: groups consultancies and donations separately, then joins
WITH consultancy_summary AS (
  SELECT
    client_id,
    COUNT(*) AS consultancy_count,
    COUNT(DISTINCT agency_id) AS agencies_used
  FROM datafetch_consultancy
  GROUP BY client_id
),
donation_summary AS (
  SELECT
    donor_id,
    COUNT(*) AS donation_count,
    SUM(value) AS total_donated,
    COUNT(DISTINCT recipient_id) AS distinct_recipients,
    MIN(received_date) AS first_donation,
    MAX(received_date) AS latest_donation
  FROM datafetch_donation
  WHERE value > 0
  GROUP BY donor_id
)
SELECT
  client.id AS org_id,
  MAX(client.name) AS org_name,
  MAX(org.classification) AS org_type,
  cs.consultancy_count,
  cs.agencies_used,
  ds.donation_count,
  ds.total_donated,
  ds.distinct_recipients,
  ds.first_donation,
  ds.latest_donation
FROM consultancy_summary cs
JOIN donation_summary ds ON ds.donor_id = cs.client_id
JOIN datafetch_actor client ON client.id = cs.client_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = client.id
ORDER BY ds.total_donated DESC;


-- 2.2 Lobbying Agencies with Clients Who Also Donate
-- Stable: pre-aggregates per (agency, client) to avoid inflation
WITH agency_client_consultancies AS (
  SELECT
    agency_id,
    client_id,
    COUNT(*) AS consultancy_count
  FROM datafetch_consultancy
  GROUP BY agency_id, client_id
),
client_donations AS (
  SELECT
    donor_id AS client_id,
    COUNT(*) AS donation_count,
    SUM(value) AS total_donated,
    COUNT(DISTINCT recipient_id) AS distinct_recipients
  FROM datafetch_donation
  WHERE value > 0
  GROUP BY donor_id
)
SELECT
  agency.id AS agency_id,
  MAX(agency.name) AS agency_name,
  client.id AS client_id,
  MAX(client.name) AS client_name,
  MAX(client_org.classification) AS client_type,
  acc.consultancy_count,
  cd.donation_count,
  cd.total_donated,
  cd.distinct_recipients
FROM agency_client_consultancies acc
JOIN client_donations cd ON cd.client_id = acc.client_id
JOIN datafetch_actor agency ON agency.id = acc.agency_id
JOIN datafetch_actor client ON client.id = acc.client_id
LEFT JOIN datafetch_organization client_org ON client_org.actor_ptr_id = client.id
ORDER BY cd.total_donated DESC
LIMIT 50;


-- 2.3 MPs Receiving Donations from Lobbying Clients
-- Stable: pre-compute donor->recipient totals, then check if donor has consultancies
WITH donor_recipient_totals AS (
  SELECT
    donor_id,
    recipient_id,
    SUM(value) AS total_donated,
    COUNT(*) AS donation_count
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY donor_id, recipient_id
),
lobbying_clients AS (
  SELECT DISTINCT client_id
  FROM datafetch_consultancy
)
SELECT
  recipient.id AS recipient_id,
  MAX(recipient.name) AS recipient_name,
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(donor_org.classification) AS donor_type,
  drt.total_donated,
  drt.donation_count,
  COUNT(DISTINCT c.agency_id) AS agencies_donor_uses
FROM donor_recipient_totals drt
JOIN datafetch_actor recipient ON recipient.id = drt.recipient_id
JOIN datafetch_person recipient_person ON recipient_person.actor_ptr_id = recipient.id
JOIN datafetch_actor donor ON donor.id = drt.donor_id
JOIN lobbying_clients lc ON lc.client_id = drt.donor_id
LEFT JOIN datafetch_organization donor_org ON donor_org.actor_ptr_id = donor.id
LEFT JOIN datafetch_consultancy c ON c.client_id = drt.donor_id
GROUP BY recipient.id, donor.id, drt.total_donated, drt.donation_count
ORDER BY drt.total_donated DESC
LIMIT 50;


-- 2.4 Donor-Agency-Recipient "Influence Triangles"
-- Stable: donation totals computed per (donor, recipient), then joined to agency relationships
WITH donor_recipient_totals AS (
  SELECT
    donor_id,
    recipient_id,
    SUM(value) AS total_donated,
    COUNT(*) AS donation_count,
    MIN(received_date) AS first_donation,
    MAX(received_date) AS latest_donation
  FROM datafetch_donation
  WHERE donor_id IS NOT NULL AND value > 0
  GROUP BY donor_id, recipient_id
),
donor_agencies AS (
  SELECT
    client_id AS donor_id,
    agency_id,
    COUNT(*) AS consultancy_count
  FROM datafetch_consultancy
  GROUP BY client_id, agency_id
)
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  agency.id AS agency_id,
  MAX(agency.name) AS agency_name,
  recipient.id AS recipient_id,
  MAX(recipient.name) AS recipient_name,
  drt.total_donated,
  drt.donation_count,
  da.consultancy_count AS consultancy_periods,
  drt.first_donation,
  drt.latest_donation
FROM donor_recipient_totals drt
JOIN donor_agencies da ON da.donor_id = drt.donor_id
JOIN datafetch_actor donor ON donor.id = drt.donor_id
JOIN datafetch_actor agency ON agency.id = da.agency_id
JOIN datafetch_actor recipient ON recipient.id = drt.recipient_id
WHERE drt.total_donated > 10000
ORDER BY drt.total_donated DESC
LIMIT 50;


-- 2.5 Top Lobbying Agencies by Client Count
-- Stable: groups by agency_id
SELECT
  agency.id AS agency_id,
  MAX(agency.name) AS agency_name,
  COUNT(DISTINCT c.client_id) AS distinct_clients,
  COUNT(*) AS consultancy_count,
  COALESCE(SUM(d.value), 0) AS total_client_donations,
  COUNT(DISTINCT d.recipient_id) AS distinct_donation_recipients
FROM datafetch_consultancy c
JOIN datafetch_actor agency ON agency.id = c.agency_id
LEFT JOIN datafetch_donation d
  ON d.donor_id = c.client_id
  AND d.value > 0
GROUP BY agency.id
HAVING COUNT(DISTINCT c.client_id) >= 10
ORDER BY distinct_clients DESC
LIMIT 30;


-- 2.6 Summary Statistics: Lobbying-Donation Overlap
-- Total count of organizations that both lobby and donate
WITH lobbying_clients AS (
  SELECT DISTINCT client_id FROM datafetch_consultancy
),
donating_orgs AS (
  SELECT DISTINCT donor_id FROM datafetch_donation WHERE donor_id IS NOT NULL AND value > 0
),
overlap_orgs AS (
  SELECT lc.client_id AS org_id
  FROM lobbying_clients lc
  JOIN donating_orgs do ON do.donor_id = lc.client_id
)
SELECT
  COUNT(*) AS organizations_that_lobby_and_donate,
  (SELECT SUM(d.value) FROM datafetch_donation d WHERE d.donor_id IN (SELECT org_id FROM overlap_orgs) AND d.value > 0) AS total_donated_by_lobbying_clients,
  (SELECT COUNT(*) FROM datafetch_donation d WHERE d.donor_id IN (SELECT org_id FROM overlap_orgs) AND d.value > 0) AS total_donations,
  (SELECT COUNT(DISTINCT d.recipient_id) FROM datafetch_donation d WHERE d.donor_id IN (SELECT org_id FROM overlap_orgs) AND d.value > 0) AS distinct_recipients
FROM overlap_orgs;


-- 2.7 Recipients of Lobbying-Client Donations (Breakdown by Type)
WITH lobbying_clients AS (
  SELECT DISTINCT client_id FROM datafetch_consultancy
)
SELECT
  CASE
    WHEN person.actor_ptr_id IS NOT NULL THEN 'Individual MP/Lord'
    WHEN LOWER(COALESCE(org.classification,'')) IN ('party', 'political party') THEN 'Political Party'
    ELSE 'Campaign/Organization'
  END AS recipient_type,
  COUNT(DISTINCT d.recipient_id) AS recipient_count,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_received,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN lobbying_clients lc ON lc.client_id = d.donor_id
JOIN datafetch_actor recipient ON recipient.id = d.recipient_id
LEFT JOIN datafetch_person person ON person.actor_ptr_id = recipient.id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = recipient.id
WHERE d.value > 0
GROUP BY recipient_type
ORDER BY total_received DESC;


-- 2.8 Lobbying-Donating Organizations by Type
WITH lobbying_clients AS (
  SELECT DISTINCT client_id FROM datafetch_consultancy
),
client_donations AS (
  SELECT
    donor_id,
    SUM(value) AS total_donated
  FROM datafetch_donation
  WHERE value > 0
  GROUP BY donor_id
)
SELECT
  COALESCE(org.classification, 'Individual/Unclassified') AS org_type,
  COUNT(DISTINCT lc.client_id) AS organization_count,
  SUM(cd.total_donated) AS total_donated,
  ROUND(AVG(cd.total_donated), 2) AS avg_per_org,
  ROUND(100.0 * SUM(cd.total_donated) / SUM(SUM(cd.total_donated)) OVER (), 2) AS pct_of_total
FROM lobbying_clients lc
JOIN client_donations cd ON cd.donor_id = lc.client_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = lc.client_id
GROUP BY org.classification
ORDER BY total_donated DESC;


-- ============================================================================
-- SECTION 6: SECTOR & CLASSIFICATION ANALYSIS
-- ============================================================================

-- 6.1 Donations by Donor Classification
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


-- 6.2 Lobbying Clients by Classification
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
-- SECTION 7: DATA QUALITY CHECKS
-- ============================================================================

-- 7.1 Null Donor Analysis (by donation type)
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
    CASE WHEN received_date ~ '^\d{4}-\d{2}-\d{2}$' THEN received_date::date END AS received_dt
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
    CASE WHEN d.received_date ~ '^\d{4}-\d{2}-\d{2}$' THEN d.received_date::date END AS received_dt
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
