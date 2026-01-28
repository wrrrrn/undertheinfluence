-- ============================================================================
-- POLITICIAN PROFILES: DEEP DIVE (HISTORICAL & INFLUENCE)
-- ============================================================================
-- Purpose: Comprehensive view of specific politicians (Donations, Meetings, Roles)
-- Targets: Nigel Farage, Keir Starmer, Kemi Badenoch, Zack Polanski
-- Date: 2026-01-23
-- Database: PostgreSQL
-- ============================================================================

-- ============================================================================
-- CONFIGURATION: TARGET POLITICIANS
-- ============================================================================
-- Define the cohort once here for use in subsequent queries.
-- Replace IDs or Names to analyze different people.

CREATE TEMPORARY TABLE target_politicians AS
SELECT id, name
FROM datafetch_actor
WHERE id IN (
    2198, -- Keir Starmer
    3173, -- Nigel Farage
    2539, -- Kemi Badenoch
    2867  -- Zack Polanski
);


-- ============================================================================
-- 1. PROFILE OVERVIEW & PARTY HISTORY
-- ============================================================================
-- Shows current and historical party affiliations.

SELECT 
    tp.name as politician,
    o_actor.name as party_name,
    pm.role as party_role,
    pm.start_date,
    pm.end_date,
    CASE 
        WHEN pm.end_date IS NULL OR pm.end_date > CURRENT_DATE::text THEN 'Current'
        ELSE 'Historical'
    END as status
FROM target_politicians tp
JOIN datafetch_membership pm ON tp.id = pm.person_id
JOIN datafetch_organization o ON pm.organization_id = o.actor_ptr_id
JOIN datafetch_actor o_actor ON o.actor_ptr_id = o_actor.id
WHERE o.classification IN ('Political Party', 'Registered Political Party')
ORDER BY tp.name, pm.start_date DESC;


-- ============================================================================
-- 2. CAREER TIMELINE (Parliamentary & Ministerial Roles)
-- ============================================================================
-- Shows their career trajectory: MP seats, Government posts, Shadow Cabinet.

SELECT 
    tp.name as politician,
    m.role as position,
    o_actor.name as organization,
    m.start_date,
    m.end_date
FROM target_politicians tp
JOIN datafetch_membership m ON tp.id = m.person_id
LEFT JOIN datafetch_organization o ON m.organization_id = o.actor_ptr_id
LEFT JOIN datafetch_actor o_actor ON o.actor_ptr_id = o_actor.id
WHERE o.classification NOT IN ('Political Party', 'Registered Political Party') 
   OR o.classification IS NULL
ORDER BY tp.name, m.start_date DESC;


-- ============================================================================
-- 3. FINANCIAL SUPPORT SUMMARY
-- ============================================================================
-- High-level donation stats per politician.

SELECT 
    tp.name as politician,
    COUNT(d.id) as donation_count,
    SUM(d.value) as total_received,
    COUNT(DISTINCT d.donor_id) as distinct_donors,
    ROUND(AVG(d.value), 2) as avg_donation,
    MIN(d.received_date) as first_donation,
    MAX(d.received_date) as latest_donation
FROM target_politicians tp
LEFT JOIN datafetch_donation d ON tp.id = d.recipient_id AND d.value > 0
GROUP BY tp.name
ORDER BY total_received DESC NULLS LAST;


-- ============================================================================
-- 4. TOP DONORS (Who funds them?)
-- ============================================================================
-- Breakdown of the biggest backers for each politician.

WITH ranked_donors AS (
    SELECT 
        tp.name as politician,
        donor.name as donor_name,
        COALESCE(org.classification, 'Individual') as donor_type,
        SUM(d.value) as total_donated,
        COUNT(d.id) as donation_count,
        ROW_NUMBER() OVER (PARTITION BY tp.name ORDER BY SUM(d.value) DESC) as rank
    FROM target_politicians tp
    JOIN datafetch_donation d ON tp.id = d.recipient_id
    JOIN datafetch_actor donor ON d.donor_id = donor.id
    LEFT JOIN datafetch_organization org ON donor.id = org.actor_ptr_id
    WHERE d.value > 0
    GROUP BY tp.name, donor.name, org.classification
)
SELECT 
    politician,
    rank,
    donor_name,
    donor_type,
    total_donated,
    donation_count
FROM ranked_donors
WHERE rank <= 10
ORDER BY politician, rank;


-- ============================================================================
-- 5. MINISTERIAL MEETINGS HOSTED (Influence Access Granted)
-- ============================================================================
-- If they were a minister, who did they meet with? Top 5 organizations met.

WITH meeting_counts AS (
    SELECT 
        tp.name as politician,
        COALESCE(attendee.canonical_actor_id, attendee.actor_id) as org_id,
        MAX(COALESCE(attendee_canon.name, attendee_actor.name)) as org_name,
        COUNT(DISTINCT mm.id) as meetings_count
    FROM target_politicians tp
    JOIN datafetch_ministerialmeeting mm ON tp.id = mm.minister_id
    JOIN datafetch_meetingattendee attendee ON mm.id = attendee.meeting_id
    JOIN datafetch_actor attendee_actor ON attendee.actor_id = attendee_actor.id
    LEFT JOIN datafetch_actor attendee_canon ON attendee.canonical_actor_id = attendee_canon.id
    GROUP BY tp.name, COALESCE(attendee.canonical_actor_id, attendee.actor_id)
),
ranked_meetings AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY politician ORDER BY meetings_count DESC) as rank
    FROM meeting_counts
)
SELECT 
    politician,
    rank,
    org_name,
    meetings_count
FROM ranked_meetings
WHERE rank <= 10
ORDER BY politician, rank;


-- ============================================================================
-- 6. DONOR-LOBBYIST CONNECTIONS (Indirect Influence)
-- ============================================================================
-- Do their donors hire lobbyists? (The Influence Triangle)

SELECT 
    tp.name as politician,
    donor.name as donor_name,
    d.total_donated as amount_given_to_mp,
    COUNT(DISTINCT c.agency_id) as lobbying_firms_hired,
    STRING_AGG(DISTINCT agency.name, ', ') as lobbying_agencies
FROM target_politicians tp
JOIN (
    SELECT recipient_id, donor_id, SUM(value) as total_donated
    FROM datafetch_donation
    WHERE value > 1000
    GROUP BY recipient_id, donor_id
) d ON tp.id = d.recipient_id
JOIN datafetch_actor donor ON d.donor_id = donor.id
JOIN datafetch_consultancy c ON donor.id = c.client_id
JOIN datafetch_actor agency ON c.agency_id = agency.id
GROUP BY tp.name, donor.name, d.total_donated
ORDER BY tp.name, d.total_donated DESC;

-- Clean up
DROP TABLE target_politicians;
