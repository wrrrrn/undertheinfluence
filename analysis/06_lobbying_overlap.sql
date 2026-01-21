-- ============================================================================
-- LOBBYING-DONATION OVERLAP ANALYSIS
-- ============================================================================
-- Purpose: Analyze the intersection of lobbying and political donations
-- Focus: Organizations that both lobby AND donate, influence triangles
-- Date: 2026-01-19
-- Database: PostgreSQL
-- Note: All queries use non-inflating joins to avoid cartesian products
-- ============================================================================

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
GROUP BY client.id, cs.consultancy_count, cs.agencies_used, ds.donation_count, ds.total_donated, ds.distinct_recipients, ds.first_donation, ds.latest_donation
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
GROUP BY agency.id, client.id, acc.consultancy_count, cd.donation_count, cd.total_donated, cd.distinct_recipients
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
GROUP BY donor.id, agency.id, recipient.id, drt.total_donated, drt.donation_count, da.consultancy_count, drt.first_donation, drt.latest_donation
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
  JOIN donating_orgs don ON don.donor_id = lc.client_id
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
-- END OF LOBBYING-DONATION OVERLAP ANALYSIS
-- ============================================================================
