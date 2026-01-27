-- ============================================================================
-- ADVANCED INFLUENCE INSIGHTS: EFFICIENCY, GEOGRAPHY & NETWORKS
-- ============================================================================
-- Purpose: Advanced cross-domain analysis covering cost of access and blitz campaigns
-- Date: 2026-01-26 (Updated with Canonical Resolution)
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
        -- Donation totals (using canonical)
        COALESCE((
            SELECT SUM(d.value)
            FROM datafetch_donation d
            WHERE COALESCE(d.canonical_donor_id, d.donor_id) = a.id AND d.value > 0
        ), 0) as total_donated,
        -- Meeting totals (using canonical)
        COALESCE((
            SELECT COUNT(DISTINCT ma.meeting_id)
            FROM datafetch_meetingattendee ma
            WHERE COALESCE(ma.canonical_actor_id, ma.actor_id) = a.id
        ), 0) as meeting_count
    FROM datafetch_actor a
    JOIN datafetch_organization o ON a.id = o.actor_ptr_id
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
        WHEN total_donated > 100000 AND meeting_count < 5 THEN 'High Donor / Low Access'
        WHEN total_donated < 5000 AND meeting_count > 10 THEN 'Low Donor / High Access (Advisor)'
        WHEN total_donated > 50000 AND meeting_count > 10 THEN 'Full Spectrum Influence'
        ELSE 'Balanced'
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
        COALESCE(ma.canonical_actor_id, ma.actor_id) as external_actor_id,
        TO_CHAR(mm.meeting_date::date, 'YYYY-"Q"Q') as quarter,
        COUNT(DISTINCT mm.department_id) as dept_count,
        STRING_AGG(DISTINCT dept.name, ', ') as departments
    FROM datafetch_meetingattendee ma
    JOIN datafetch_ministerialmeeting mm ON ma.meeting_id = mm.id
    JOIN datafetch_actor dept ON mm.department_id = dept.id
    GROUP BY 1, 2
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
