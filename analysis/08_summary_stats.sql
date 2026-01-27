-- ============================================================================
-- SUMMARY STATISTICS & DATA QUALITY
-- ============================================================================
-- Purpose: Database overview, data quality checks, and aggregate statistics
-- Focus: Record counts, date ranges, null analysis, classification stats, meetings
-- Date: 2026-01-26 (Updated with Canonical Resolution)
-- Database: PostgreSQL
-- ============================================================================

-- ============================================================================
-- SECTION 1: DATABASE OVERVIEW
-- ============================================================================

-- 1.1 Core Record Counts
SELECT 'Total Persons' AS metric, COUNT(*) AS count FROM datafetch_person
UNION ALL
SELECT 'Total Organizations', COUNT(*) FROM datafetch_organization
UNION ALL
SELECT 'Total Actors', COUNT(*) FROM datafetch_actor
UNION ALL
SELECT 'Total Donations', COUNT(*) FROM datafetch_donation
UNION ALL
SELECT 'Donations with Value > 0', COUNT(*) FROM datafetch_donation WHERE value > 0
UNION ALL
SELECT 'Total Consultancies', COUNT(*) FROM datafetch_consultancy
UNION ALL
SELECT 'Ministerial Meetings', COUNT(*) FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Meeting Attendees', COUNT(*) FROM datafetch_meetingattendee;


-- ============================================================================
-- SECTION 2: DONATION SUMMARY
-- ============================================================================

-- 2.1 Donations by Donor Classification
SELECT
  COALESCE(org.classification, 'Individual') AS donor_classification,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  COUNT(DISTINCT COALESCE(d.canonical_donor_id, d.donor_id)) AS distinct_donors
FROM datafetch_donation d
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = COALESCE(d.canonical_donor_id, d.donor_id)
WHERE d.value > 0
GROUP BY COALESCE(org.classification, 'Individual')
ORDER BY total_donated DESC;


-- ============================================================================
-- SECTION 3: MINISTERIAL MEETINGS OVERVIEW
-- ============================================================================

-- 3.1 Meetings by Department
SELECT
    d.name as department,
    COUNT(*) as meetings,
    COUNT(DISTINCT mm.minister_id) as ministers,
    (SELECT COUNT(DISTINCT COALESCE(ma.canonical_actor_id, ma.actor_id)) 
     FROM datafetch_meetingattendee ma 
     JOIN datafetch_ministerialmeeting mm2 ON ma.meeting_id = mm2.id 
     WHERE mm2.department_id = mm.department_id) as external_actors
FROM datafetch_ministerialmeeting mm
JOIN datafetch_actor d ON mm.department_id = d.id
GROUP BY d.name, mm.department_id
ORDER BY meetings DESC;


-- ============================================================================
-- SECTION 4: CROSS-DATASET INFLUENCE
-- ============================================================================

-- 4.1 Influence Channels Summary
SELECT
    'Organizations with meetings' as category,
    COUNT(DISTINCT COALESCE(canonical_actor_id, actor_id))::text as count
FROM datafetch_meetingattendee
UNION ALL
SELECT
    'Organizations hiring lobbyists',
    COUNT(DISTINCT COALESCE(canonical_client_id, client_id))::text
FROM datafetch_consultancy
UNION ALL
SELECT
    'Organizations donating > £1k',
    COUNT(DISTINCT COALESCE(canonical_donor_id, donor_id))::text
FROM datafetch_donation WHERE value > 1000
UNION ALL
SELECT
    'Organizations using ALL THREE channels',
    COUNT(*)::text
FROM (
    SELECT DISTINCT COALESCE(canonical_client_id, client_id) as org_id FROM datafetch_consultancy
    INTERSECT
    SELECT DISTINCT COALESCE(canonical_donor_id, donor_id) FROM datafetch_donation WHERE value > 1000
    INTERSECT
    SELECT DISTINCT COALESCE(canonical_actor_id, actor_id) FROM datafetch_meetingattendee
) all_three;