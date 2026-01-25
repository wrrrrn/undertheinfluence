-- ============================================================================
-- SUMMARY STATISTICS & DATA QUALITY
-- ============================================================================
-- Purpose: Database overview, data quality checks, and aggregate statistics
-- Focus: Record counts, date ranges, null analysis, classification stats, meetings
-- Date: 2026-01-22
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
-- SECTION 10: MINISTERIAL MEETINGS OVERVIEW
-- ============================================================================

-- 10.1 Meetings Summary Statistics
SELECT 'Total Ministerial Meetings' AS metric, COUNT(*) AS count FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Unique Ministers', COUNT(DISTINCT minister_id) FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Unique External Actors', COUNT(DISTINCT external_actor_id) FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Departments Covered', COUNT(DISTINCT department_id) FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Roundtable Meetings', COUNT(*) FROM datafetch_ministerialmeeting WHERE is_roundtable = true
UNION ALL
SELECT 'Total Meeting Attendees', COUNT(*) FROM datafetch_meetingattendee
UNION ALL
SELECT 'Unique Attendee Organizations', COUNT(DISTINCT actor_id) FROM datafetch_meetingattendee;


-- 10.2 Meetings by Department
SELECT
    d.name as department,
    COUNT(*) as meetings,
    COUNT(DISTINCT mm.minister_id) as ministers,
    COUNT(DISTINCT mm.external_actor_id) as external_actors
FROM datafetch_ministerialmeeting mm
JOIN datafetch_actor d ON mm.department_id = d.id
GROUP BY d.name
ORDER BY meetings DESC;


-- 10.3 Meeting Date Coverage
SELECT
    'Earliest Meeting' AS metric,
    MIN(meeting_date)::text AS value
FROM datafetch_ministerialmeeting
WHERE meeting_date IS NOT NULL
UNION ALL
SELECT
    'Latest Meeting',
    MAX(meeting_date)::text
FROM datafetch_ministerialmeeting
WHERE meeting_date IS NOT NULL;


-- 10.4 Attendee Distribution Analysis
SELECT
    CASE
        WHEN attendee_count = 1 THEN '1 attendee'
        WHEN attendee_count BETWEEN 2 AND 3 THEN '2-3 attendees'
        WHEN attendee_count BETWEEN 4 AND 5 THEN '4-5 attendees'
        WHEN attendee_count BETWEEN 6 AND 10 THEN '6-10 attendees'
        ELSE '10+ attendees'
    END AS attendee_group,
    COUNT(*) AS meeting_count
FROM (
    SELECT
        mm.id,
        COUNT(ma.id) AS attendee_count
    FROM datafetch_ministerialmeeting mm
    LEFT JOIN datafetch_meetingattendee ma ON ma.meeting_id = mm.id
    GROUP BY mm.id
) subq
GROUP BY attendee_group
ORDER BY
    CASE attendee_group
        WHEN '1 attendee' THEN 1
        WHEN '2-3 attendees' THEN 2
        WHEN '4-5 attendees' THEN 3
        WHEN '6-10 attendees' THEN 4
        ELSE 5
    END;


-- ============================================================================
-- SECTION 11: CROSS-DATASET INFLUENCE OVERVIEW
-- ============================================================================

-- 11.1 Full Database Influence Summary
SELECT
    'Organizations with meetings' as category,
    COUNT(DISTINCT external_actor_id)::text as count
FROM datafetch_ministerialmeeting
UNION ALL
SELECT
    'Organizations with lobbying clients',
    COUNT(DISTINCT client_id)::text
FROM datafetch_consultancy
UNION ALL
SELECT
    'Organizations as donors',
    COUNT(DISTINCT donor_id)::text
FROM datafetch_donation WHERE donor_id IS NOT NULL AND value > 0
UNION ALL
SELECT
    'Organizations using ALL channels',
    COUNT(*)::text
FROM (
    SELECT DISTINCT client_id as org_id FROM datafetch_consultancy
    INTERSECT
    SELECT DISTINCT donor_id FROM datafetch_donation WHERE value > 1000
    INTERSECT
    SELECT DISTINCT external_actor_id FROM datafetch_ministerialmeeting
) all_three;


-- 11.2 Top 10 Most Influential Organizations (All Channels)
WITH org_meetings AS (
    SELECT external_actor_id as org_id, COUNT(*) as meetings
    FROM datafetch_ministerialmeeting
    GROUP BY external_actor_id
),
org_lobbying AS (
    SELECT client_id as org_id, COUNT(DISTINCT agency_id) as agencies
    FROM datafetch_consultancy
    GROUP BY client_id
),
org_donations AS (
    SELECT donor_id as org_id, SUM(value) as total_donated
    FROM datafetch_donation
    WHERE value > 0
    GROUP BY donor_id
)
SELECT
    a.name as organization,
    COALESCE(om.meetings, 0) as meetings,
    COALESCE(ol.agencies, 0) as lobbying_agencies,
    COALESCE(od.total_donated, 0) as total_donated
FROM datafetch_actor a
LEFT JOIN org_meetings om ON om.org_id = a.id
LEFT JOIN org_lobbying ol ON ol.org_id = a.id
LEFT JOIN org_donations od ON od.org_id = a.id
WHERE (om.meetings > 0 OR ol.agencies > 0 OR od.total_donated > 0)
ORDER BY
    (CASE WHEN om.meetings > 0 THEN 1 ELSE 0 END +
     CASE WHEN ol.agencies > 0 THEN 1 ELSE 0 END +
     CASE WHEN od.total_donated > 0 THEN 1 ELSE 0 END) DESC,
    COALESCE(od.total_donated, 0) DESC
LIMIT 10;


-- ============================================================================
-- END OF SUMMARY STATISTICS & DATA QUALITY
-- ============================================================================
