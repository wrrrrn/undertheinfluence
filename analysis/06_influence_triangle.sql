-- ============================================================================
-- INFLUENCE TRIANGLE ANALYSIS (Lobbying + Donations + Meetings)
-- ============================================================================
-- Purpose: Analyze the intersection of lobbying, donations, AND ministerial meetings
-- Focus: Organizations using multiple influence channels, the full "influence triangle"
-- Date: 2026-01-22
-- Database: PostgreSQL
-- Note: All queries use non-inflating joins to avoid cartesian products
-- ============================================================================


-- ============================================================================
-- SECTION 1: THE FULL INFLUENCE TRIANGLE (Lobbying + Donations + Meetings)
-- ============================================================================

-- 1.1 Organizations with ALL THREE: Lobbying + Donations + Meetings
-- The "maximum influence" organizations
WITH lobbying_clients AS (
    SELECT
        client_id as org_id,
        COUNT(DISTINCT agency_id) as agencies_used,
        COUNT(*) as consultancy_records
    FROM datafetch_consultancy
    GROUP BY client_id
),
donors AS (
    SELECT
        donor_id as org_id,
        SUM(value) as total_donated,
        COUNT(*) as donation_count,
        COUNT(DISTINCT recipient_id) as recipients_funded
    FROM datafetch_donation
    WHERE value > 0
    GROUP BY donor_id
),
meeting_orgs AS (
    SELECT
        external_actor_id as org_id,
        COUNT(*) as meeting_count,
        COUNT(DISTINCT minister_id) as ministers_met,
        COUNT(DISTINCT department_id) as departments
    FROM datafetch_ministerialmeeting
    GROUP BY external_actor_id
)
SELECT
    a.name as organization,
    COALESCE(o.classification, 'Unclassified') as org_type,
    COALESCE(mo.meeting_count, 0) as meetings,
    COALESCE(mo.ministers_met, 0) as ministers_met,
    COALESCE(mo.departments, 0) as departments,
    COALESCE(lc.agencies_used, 0) as lobbying_agencies,
    COALESCE(lc.consultancy_records, 0) as consultancy_records,
    COALESCE(dn.total_donated, 0) as total_donated,
    COALESCE(dn.donation_count, 0) as donations,
    COALESCE(dn.recipients_funded, 0) as recipients_funded
FROM datafetch_actor a
LEFT JOIN datafetch_organization o ON o.actor_ptr_id = a.id
LEFT JOIN lobbying_clients lc ON lc.org_id = a.id
LEFT JOIN donors dn ON dn.org_id = a.id
LEFT JOIN meeting_orgs mo ON mo.org_id = a.id
WHERE lc.org_id IS NOT NULL
  AND dn.org_id IS NOT NULL
  AND mo.org_id IS NOT NULL
ORDER BY dn.total_donated DESC
LIMIT 100;

-- 1.2 Influence Triangle Summary Statistics
-- How many orgs use 1, 2, or all 3 channels?
WITH lobbying_clients AS (
    SELECT DISTINCT client_id as org_id FROM datafetch_consultancy
),
donors AS (
    SELECT DISTINCT donor_id as org_id FROM datafetch_donation WHERE value > 1000
),
meeting_orgs AS (
    SELECT DISTINCT external_actor_id as org_id FROM datafetch_ministerialmeeting
)
SELECT
    'All THREE (lobbying + donations + meetings)' as influence_channels,
    COUNT(*) as organization_count
FROM lobbying_clients lc
JOIN donors d ON d.org_id = lc.org_id
JOIN meeting_orgs mo ON mo.org_id = lc.org_id
UNION ALL
SELECT
    'Lobbying + Donations only',
    COUNT(*)
FROM lobbying_clients lc
JOIN donors d ON d.org_id = lc.org_id
WHERE lc.org_id NOT IN (SELECT org_id FROM meeting_orgs)
UNION ALL
SELECT
    'Lobbying + Meetings only',
    COUNT(*)
FROM lobbying_clients lc
JOIN meeting_orgs mo ON mo.org_id = lc.org_id
WHERE lc.org_id NOT IN (SELECT org_id FROM donors)
UNION ALL
SELECT
    'Donations + Meetings only',
    COUNT(*)
FROM donors d
JOIN meeting_orgs mo ON mo.org_id = d.org_id
WHERE d.org_id NOT IN (SELECT org_id FROM lobbying_clients)
UNION ALL
SELECT
    'Lobbying only',
    COUNT(*)
FROM lobbying_clients lc
WHERE lc.org_id NOT IN (SELECT org_id FROM donors)
  AND lc.org_id NOT IN (SELECT org_id FROM meeting_orgs)
UNION ALL
SELECT
    'Donations only (>£1000)',
    COUNT(*)
FROM donors d
WHERE d.org_id NOT IN (SELECT org_id FROM lobbying_clients)
  AND d.org_id NOT IN (SELECT org_id FROM meeting_orgs)
UNION ALL
SELECT
    'Meetings only',
    COUNT(*)
FROM meeting_orgs mo
WHERE mo.org_id NOT IN (SELECT org_id FROM lobbying_clients)
  AND mo.org_id NOT IN (SELECT org_id FROM donors);


-- ============================================================================
-- SECTION 2: INFLUENCE TRIANGLES - DONOR-AGENCY-MINISTER RELATIONSHIPS
-- ============================================================================

-- 2.1 Full Influence Triangles: Org pays lobbyist, donates, AND meets minister
-- Most comprehensive view of coordinated influence
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
donor_agencies AS (
  SELECT
    client_id AS donor_id,
    agency_id,
    COUNT(*) AS consultancy_count
  FROM datafetch_consultancy
  GROUP BY client_id, agency_id
),
donor_meetings AS (
  SELECT
    external_actor_id AS donor_id,
    minister_id,
    COUNT(*) AS meeting_count
  FROM datafetch_ministerialmeeting
  GROUP BY external_actor_id, minister_id
)
SELECT
  donor.name AS organization,
  agency.name AS lobbying_agency,
  recipient.name AS recipient_funded,
  drt.total_donated,
  drt.donation_count AS donations,
  da.consultancy_count AS consultancy_periods,
  COALESCE(dm.meeting_count, 0) AS meetings_with_recipient
FROM donor_recipient_totals drt
JOIN donor_agencies da ON da.donor_id = drt.donor_id
JOIN datafetch_actor donor ON donor.id = drt.donor_id
JOIN datafetch_actor agency ON agency.id = da.agency_id
JOIN datafetch_actor recipient ON recipient.id = drt.recipient_id
LEFT JOIN donor_meetings dm ON dm.donor_id = drt.donor_id AND dm.minister_id = drt.recipient_id
WHERE drt.total_donated > 10000
ORDER BY drt.total_donated DESC
LIMIT 50;

-- 2.2 Same Organization: Donates AND Meets Same Minister
-- Direct influence: org funds AND meets with the same person
WITH minister_donations AS (
    SELECT
        d.donor_id,
        d.recipient_id as minister_id,
        SUM(d.value) as total_donated,
        COUNT(*) as donation_count
    FROM datafetch_donation d
    JOIN datafetch_person p ON p.actor_ptr_id = d.recipient_id
    WHERE d.value > 0
    GROUP BY d.donor_id, d.recipient_id
),
minister_meetings AS (
    SELECT
        mm.external_actor_id as org_id,
        mm.minister_id,
        COUNT(*) as meeting_count
    FROM datafetch_ministerialmeeting mm
    GROUP BY mm.external_actor_id, mm.minister_id
)
SELECT
    org.name as organization,
    minister.name as minister,
    mm.meeting_count as meetings,
    md.total_donated,
    md.donation_count as donations
FROM minister_donations md
JOIN minister_meetings mm ON mm.org_id = md.donor_id AND mm.minister_id = md.minister_id
JOIN datafetch_actor org ON org.id = md.donor_id
JOIN datafetch_actor minister ON minister.id = md.minister_id
ORDER BY md.total_donated DESC
LIMIT 50;


-- ============================================================================
-- SECTION 3: LOBBYING AGENCIES AND MINISTERIAL ACCESS
-- ============================================================================

-- 3.1 Top Lobbying Agencies - Client Meeting Access
-- Which agencies have clients with the most ministerial access?
WITH agency_clients AS (
    SELECT
        agency_id,
        client_id
    FROM datafetch_consultancy
    GROUP BY agency_id, client_id
),
client_meetings AS (
    SELECT
        external_actor_id as client_id,
        COUNT(*) as meeting_count,
        COUNT(DISTINCT minister_id) as ministers_met
    FROM datafetch_ministerialmeeting
    GROUP BY external_actor_id
)
SELECT
    agency.name as lobbying_agency,
    COUNT(DISTINCT ac.client_id) as total_clients,
    COUNT(DISTINCT CASE WHEN cm.meeting_count > 0 THEN ac.client_id END) as clients_with_meetings,
    SUM(COALESCE(cm.meeting_count, 0)) as total_client_meetings,
    SUM(COALESCE(cm.ministers_met, 0)) as total_ministers_met
FROM agency_clients ac
JOIN datafetch_actor agency ON agency.id = ac.agency_id
LEFT JOIN client_meetings cm ON cm.client_id = ac.client_id
GROUP BY agency.id, agency.name
HAVING COUNT(DISTINCT ac.client_id) >= 5
ORDER BY total_client_meetings DESC
LIMIT 30;

-- 3.2 Top Lobbying Agencies by Client Donations
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


-- ============================================================================
-- SECTION 4: MPs RECEIVING DONATIONS FROM LOBBYING CLIENTS
-- ============================================================================

-- 4.1 MPs Receiving Donations from Lobbying Clients
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

-- 4.2 Recipients of Lobbying-Client Donations (Breakdown by Type)
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


-- ============================================================================
-- SECTION 5: SUMMARY STATISTICS
-- ============================================================================

-- 5.1 Top Lobbying Agencies by Client Count
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

-- 5.2 Lobbying-Donating Organizations by Type
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
-- SECTION 6: ORGANIZATIONS THAT BOTH LOBBY AND DONATE (Reference)
-- ============================================================================
-- Note: This is less interesting than the full influence triangle above,
-- but retained for completeness and backward compatibility.

-- 6.1 Organizations That Both Lobby AND Donate
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
ORDER BY ds.total_donated DESC
LIMIT 100;

-- 6.2 Summary: Lobbying-Donation Overlap Stats
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


-- ============================================================================
-- END OF INFLUENCE TRIANGLE ANALYSIS
-- ============================================================================
