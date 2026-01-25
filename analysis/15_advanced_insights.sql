-- ============================================================================
-- ADVANCED INFLUENCE INSIGHTS: EFFICIENCY, GEOGRAPHY & NETWORKS
-- ============================================================================
-- Purpose: Advanced cross-domain analysis not covered in standard reports.
-- Focus: Cost of access, cross-dept coordination, Lords-lobbyist links, geography.
-- Date: 2026-01-23
-- Database: PostgreSQL
-- ============================================================================


-- ============================================================================
-- SECTION 1: THE "COST OF ACCESS" INDEX
-- ============================================================================
-- Comparative metric: Donation Value vs. Ministerial Meeting Count.
-- Identifies "Pay-to-Play" risks vs "Trusted Advisor" status.

WITH org_stats AS (
    SELECT
        a.id,
        a.name,
        -- Donation totals
        COALESCE((
            SELECT SUM(d.value)
            FROM datafetch_donation d
            WHERE d.donor_id = a.id AND d.value > 0
        ), 0) as total_donated,
        -- Meeting totals (via MeetingAttendee)
        COALESCE((
            SELECT COUNT(*)
            FROM datafetch_meetingattendee ma
            WHERE ma.actor_id = a.id
        ), 0) as meeting_count
    FROM datafetch_actor a
    JOIN datafetch_organization o ON a.id = o.actor_ptr_id
    WHERE 
       -- Filter for active participants only
       (EXISTS (SELECT 1 FROM datafetch_donation d WHERE d.donor_id = a.id) 
        OR 
        EXISTS (SELECT 1 FROM datafetch_meetingattendee ma WHERE ma.actor_id = a.id))
)
SELECT
    name as organization,
    total_donated,
    meeting_count,
    CASE 
        WHEN meeting_count > 0 THEN ROUND(total_donated / meeting_count, 2)
        ELSE NULL 
    END as cost_per_meeting,
    CASE
        WHEN total_donated > 100000 AND meeting_count < 5 THEN 'High Donor / Low Access (Donor)'
        WHEN total_donated < 5000 AND meeting_count > 10 THEN 'Low Donor / High Access (Expert/Lobbyist)'
        WHEN total_donated > 50000 AND meeting_count > 10 THEN 'Full Spectrum Influence'
        ELSE 'Transactional'
    END as influence_profile
FROM org_stats
WHERE meeting_count > 0 OR total_donated > 50000
ORDER BY total_donated DESC
LIMIT 50;


-- ============================================================================
-- SECTION 2: CROSS-DEPARTMENTAL "BLITZ" CAMPAIGNS
-- ============================================================================
-- Identifies organizations targeting 3+ government departments within a single
-- quarter. This pattern indicates a major coordinated lobbying push.

WITH meeting_quarters AS (
    SELECT
        ma.actor_id as external_actor_id,
        -- Normalize dates to quarters (e.g., '2024-Q1')
        TO_CHAR(mm.meeting_date::date, 'YYYY-"Q"Q') as quarter,
        COUNT(DISTINCT mm.department_id) as dept_count,
        STRING_AGG(DISTINCT dept.name, ', ') as departments
    FROM datafetch_meetingattendee ma
    JOIN datafetch_ministerialmeeting mm ON ma.meeting_id = mm.id
    JOIN datafetch_actor dept ON mm.department_id = dept.id
    WHERE mm.meeting_date IS NOT NULL
    GROUP BY ma.actor_id, TO_CHAR(mm.meeting_date::date, 'YYYY-"Q"Q')
)
SELECT
    org.name as organization,
    mq.quarter,
    mq.dept_count,
    mq.departments
FROM meeting_quarters mq
JOIN datafetch_actor org ON mq.external_actor_id = org.id
WHERE mq.dept_count >= 3
ORDER BY mq.quarter DESC, mq.dept_count DESC;


-- ============================================================================
-- SECTION 3: THE "LORDS-LOBBYIST" NEXUS (DOUBLE HATTERS)
-- ============================================================================
-- Identifies members of the House of Lords who simultaneously hold 
-- directorships or advisory roles in Lobbying Agencies or Major Donors.

WITH lords AS (
    -- Identify active Peers
    SELECT DISTINCT person_id 
    FROM datafetch_membership m 
    JOIN datafetch_organization o ON m.organization_id = o.actor_ptr_id 
    JOIN datafetch_actor a ON o.actor_ptr_id = a.id
    WHERE a.name = 'House of Lords' 
    AND (m.end_date IS NULL OR m.end_date > CURRENT_DATE::text)
),
lobbying_agencies AS (
    -- Identify Lobbying Agencies
    SELECT DISTINCT agency_id as org_id 
    FROM datafetch_consultancy
    UNION
    SELECT actor_ptr_id FROM datafetch_organization WHERE classification ILIKE '%lobby%'
),
major_donors AS (
    -- Identify Donors > £50k
    SELECT DISTINCT donor_id as org_id
    FROM datafetch_donation 
    WHERE value > 50000
)
SELECT
    peer.name as peer_name,
    org.name as external_org_name,
    m.role as external_role,
    CASE 
        WHEN la.org_id IS NOT NULL THEN 'Lobbying Agency'
        WHEN md.org_id IS NOT NULL THEN 'Major Donor'
        ELSE 'Other'
    END as org_type,
    m.start_date
FROM datafetch_membership m
JOIN lords l ON m.person_id = l.person_id
JOIN datafetch_actor peer ON m.person_id = peer.id
JOIN datafetch_actor org ON m.organization_id = org.id
LEFT JOIN lobbying_agencies la ON m.organization_id = la.org_id
LEFT JOIN major_donors md ON m.organization_id = md.org_id
WHERE (la.org_id IS NOT NULL OR md.org_id IS NOT NULL)
  AND (m.end_date IS NULL OR m.end_date > CURRENT_DATE::text)
  AND org.name != 'House of Lords'
ORDER BY peer_name;


-- ============================================================================
-- SECTION 4: GEOGRAPHIC "DONOR DESERTS" & HOTBEDS
-- ============================================================================
-- Aggregates donations by the constituency (Area) of the recipient MP.
-- Highlights geographic disparity in political funding.
-- NOTE: Currently commented out as datafetch_area table is empty.
--       Requires population of Area data to function.

/*
SELECT
    area.name as constituency,
    -- Extract region if possible, or parent area
    COALESCE(parent_area.name, 'Unknown') as region,
    COUNT(DISTINCT d.id) as donation_count,
    SUM(d.value) as total_received,
    COUNT(DISTINCT d.recipient_id) as mp_count,
    STRING_AGG(DISTINCT mp.name, ', ') as mps
FROM datafetch_donation d
JOIN datafetch_membership m ON d.recipient_id = m.person_id
JOIN datafetch_area area ON m.area_id = area.id
LEFT JOIN datafetch_area parent_area ON area.parent_id = parent_area.id
JOIN datafetch_actor mp ON m.person_id = mp.id
WHERE 
    d.value > 0 
    AND m.role = 'Member of Parliament'
    -- Ensure donation date falls within MP's tenure in that constituency
    -- Cast DATE to TEXT for lexicographical comparison with Popolo partial dates
    AND (d.received_date::text >= m.start_date OR m.start_date IS NULL OR m.start_date = '')
    AND (d.received_date::text <= m.end_date OR m.end_date IS NULL OR m.end_date = '')
GROUP BY area.name, parent_area.name
ORDER BY total_received DESC
LIMIT 50;
*/


-- ============================================================================
-- SECTION 5: ELECTION CYCLE DYNAMICS
-- ============================================================================
-- Compares donation volume vs meeting volume over time.
-- Looks for "Purdah" effects (meetings drop, donations spike?).

WITH monthly_stats AS (
    SELECT
        TO_CHAR(DATE_TRUNC('month', d.received_date), 'YYYY-MM') as month_year,
        SUM(d.value) as donation_total,
        COUNT(d.id) as donation_count
    FROM datafetch_donation d
    WHERE d.value > 0 
      AND d.received_date >= '2023-01-01'
      AND d.received_date <= CURRENT_DATE
    GROUP BY 1
),
meeting_stats AS (
    SELECT
        TO_CHAR(DATE_TRUNC('month', mm.meeting_date::date), 'YYYY-MM') as month_year,
        COUNT(*) as meeting_count
    FROM datafetch_ministerialmeeting mm
    WHERE mm.meeting_date >= '2023-01-01'
      AND mm.meeting_date <= CURRENT_DATE
    GROUP BY 1
)
SELECT
    COALESCE(d.month_year, m.month_year) as period,
    COALESCE(d.donation_total, 0) as donations_gbp,
    COALESCE(d.donation_count, 0) as num_donations,
    COALESCE(m.meeting_count, 0) as num_meetings
FROM monthly_stats d
FULL OUTER JOIN meeting_stats m ON d.month_year = m.month_year
ORDER BY period DESC;