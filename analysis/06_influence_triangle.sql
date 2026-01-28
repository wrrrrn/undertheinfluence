-- ============================================================================
-- INFLUENCE TRIANGLE ANALYSIS (Lobbying + Donations + Meetings)
-- ============================================================================
-- Purpose: Analyze the intersection of lobbying, donations, AND ministerial meetings
-- Focus: Organizations using multiple influence channels, the full "influence triangle"
-- Date: 2026-01-26 (Updated with Canonical Resolution)
-- Database: PostgreSQL
-- ============================================================================


-- ============================================================================
-- SECTION 1: THE FULL INFLUENCE TRIANGLE
-- ============================================================================

-- 1.1 Organizations with ALL THREE: Lobbying + Donations + Meetings
WITH lobbying_clients AS (
    SELECT
        COALESCE(canonical_client_id, client_id) as org_id,
        COUNT(DISTINCT COALESCE(canonical_agency_id, agency_id)) as agencies_used
    FROM datafetch_consultancy
    GROUP BY COALESCE(canonical_client_id, client_id)
),
donors AS (
    SELECT
        COALESCE(canonical_donor_id, donor_id) as org_id,
        SUM(value) as total_donated
    FROM datafetch_donation
    WHERE value > 0
    GROUP BY COALESCE(canonical_donor_id, donor_id)
),
meeting_orgs AS (
    SELECT
        COALESCE(ma.canonical_actor_id, ma.actor_id) as org_id,
        COUNT(DISTINCT mm.id) as meeting_count
    FROM datafetch_meetingattendee ma
    JOIN datafetch_ministerialmeeting mm ON ma.meeting_id = mm.id
    GROUP BY COALESCE(ma.canonical_actor_id, ma.actor_id)
)
SELECT
    a.name as organization,
    COALESCE(mo.meeting_count, 0) as meetings,
    COALESCE(lc.agencies_used, 0) as agencies,
    COALESCE(dn.total_donated, 0) as total_donated
FROM datafetch_actor a
JOIN lobbying_clients lc ON lc.org_id = a.id
JOIN donors dn ON dn.org_id = a.id
JOIN meeting_orgs mo ON mo.org_id = a.id
ORDER BY dn.total_donated DESC
LIMIT 100;


-- 1.2 Influence Triangle Summary Statistics
WITH lobbying_ids AS (
    SELECT DISTINCT COALESCE(canonical_client_id, client_id) as org_id FROM datafetch_consultancy
),
donor_ids AS (
    SELECT DISTINCT COALESCE(canonical_donor_id, donor_id) as org_id FROM datafetch_donation WHERE value > 1000
),
meeting_ids AS (
    SELECT DISTINCT COALESCE(canonical_actor_id, actor_id) as org_id FROM datafetch_meetingattendee
)
SELECT
    'All THREE (Lobbying + Donations + Meetings)' as category,
    COUNT(*) as count
FROM lobbying_ids l
JOIN donor_ids d ON l.org_id = d.org_id
JOIN meeting_ids m ON l.org_id = m.org_id
UNION ALL
SELECT
    'Lobbying + Donations only',
    COUNT(*)
FROM lobbying_ids l
JOIN donor_ids d ON l.org_id = d.org_id
WHERE l.org_id NOT IN (SELECT org_id FROM meeting_ids);


-- ============================================================================
-- SECTION 2: LOBBYING AGENCIES AND MINISTERIAL ACCESS
-- ============================================================================

-- 2.1 Top Lobbying Agencies by Client Access
WITH agency_clients AS (
    SELECT
        COALESCE(canonical_agency_id, agency_id) as agency_id,
        COALESCE(canonical_client_id, client_id) as client_id
    FROM datafetch_consultancy
    GROUP BY 1, 2
),
client_meetings AS (
    SELECT
        COALESCE(ma.canonical_actor_id, ma.actor_id) as client_id,
        COUNT(DISTINCT mm.id) as meeting_count
    FROM datafetch_meetingattendee ma
    JOIN datafetch_ministerialmeeting mm ON ma.meeting_id = mm.id
    GROUP BY 1
)
SELECT
    agency.name as lobbying_agency,
    COUNT(DISTINCT ac.client_id) as total_clients,
    SUM(COALESCE(cm.meeting_count, 0)) as total_client_meetings
FROM agency_clients ac
JOIN datafetch_actor agency ON ac.agency_id = agency.id
LEFT JOIN client_meetings cm ON ac.client_id = cm.client_id
GROUP BY agency.id, agency.name
ORDER BY total_client_meetings DESC
LIMIT 30;