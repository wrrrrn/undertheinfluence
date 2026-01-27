-- ============================================================================
-- CANONICAL ENTITY RESOLUTION ANALYSIS
-- ============================================================================
-- Purpose: Analyze the results of the entity resolution process (populate_canonical)
-- Focus: Resolution rates, top resolved entities, data quality impact
-- Date: 2026-01-26
-- Database: PostgreSQL
-- ============================================================================


-- ============================================================================
-- SECTION 1: RESOLUTION PROGRESS & COVERAGE
-- ============================================================================

-- 1.1 Resolution Rate by Dataset
-- How many records have been successfully linked to a canonical actor?
SELECT
    'Meeting Attendees' as dataset,
    COUNT(*) as total_records,
    COUNT(canonical_actor_id) as resolved_count,
    ROUND(100.0 * COUNT(canonical_actor_id) / COUNT(*), 2) as resolution_pct
FROM datafetch_meetingattendee
UNION ALL
SELECT
    'Donations (Donor)',
    COUNT(*),
    COUNT(canonical_donor_id),
    ROUND(100.0 * COUNT(canonical_donor_id) / COUNT(*), 2)
FROM datafetch_donation
WHERE donor_id IS NOT NULL
UNION ALL
SELECT
    'Donations (Recipient)',
    COUNT(*),
    COUNT(canonical_recipient_id),
    ROUND(100.0 * COUNT(canonical_recipient_id) / COUNT(*), 2)
FROM datafetch_donation
WHERE recipient_id IS NOT NULL
UNION ALL
SELECT
    'Consultancies (Client)',
    COUNT(*),
    COUNT(canonical_client_id),
    ROUND(100.0 * COUNT(canonical_client_id) / COUNT(*), 2)
FROM datafetch_consultancy
WHERE client_id IS NOT NULL
UNION ALL
SELECT
    'Consultancies (Agency)',
    COUNT(*),
    COUNT(canonical_agency_id),
    ROUND(100.0 * COUNT(canonical_agency_id) / COUNT(*), 2)
FROM datafetch_consultancy
WHERE agency_id IS NOT NULL;


-- ============================================================================
-- SECTION 2: TOP RESOLVED ENTITIES
-- ============================================================================

-- 2.1 Most Frequently Resolved Meeting Attendees
-- Who attends meetings under the most aliases?
SELECT
    canonical.name as canonical_name,
    COUNT(DISTINCT ma.actor_id) as distinct_source_actors,
    COUNT(*) as total_meetings
FROM datafetch_meetingattendee ma
JOIN datafetch_actor canonical ON ma.canonical_actor_id = canonical.id
WHERE ma.actor_id != ma.canonical_actor_id
GROUP BY canonical.id, canonical.name
ORDER BY distinct_source_actors DESC
LIMIT 20;

-- 2.2 Most Frequently Resolved Donors
-- Which donors give under the most variations?
SELECT
    canonical.name as canonical_name,
    COUNT(DISTINCT d.donor_id) as distinct_source_donors,
    COUNT(*) as total_donations,
    SUM(d.value) as total_value
FROM datafetch_donation d
JOIN datafetch_actor canonical ON d.canonical_donor_id = canonical.id
WHERE d.donor_id != d.canonical_donor_id
GROUP BY canonical.id, canonical.name
ORDER BY distinct_source_donors DESC
LIMIT 20;


-- ============================================================================
-- SECTION 3: IMPACT ON AGGREGATION
-- ============================================================================

-- 3.1 Top Donors: Original vs Canonical
-- Compare rankings before and after resolution to see impact
WITH original_ranks AS (
    SELECT
        donor_id,
        SUM(value) as total_value,
        RANK() OVER (ORDER BY SUM(value) DESC) as rank_original
    FROM datafetch_donation
    WHERE value > 0 AND donor_id IS NOT NULL
    GROUP BY donor_id
),
canonical_ranks AS (
    SELECT
        COALESCE(canonical_donor_id, donor_id) as final_id,
        SUM(value) as total_value,
        RANK() OVER (ORDER BY SUM(value) DESC) as rank_canonical
    FROM datafetch_donation
    WHERE value > 0 AND donor_id IS NOT NULL
    GROUP BY COALESCE(canonical_donor_id, donor_id)
)
SELECT
    a.name as actor_name,
    orig.total_value as original_total,
    canon.total_value as canonical_total,
    orig.rank_original,
    canon.rank_canonical,
    (canon.total_value - orig.total_value) as aggregation_gain
FROM canonical_ranks canon
JOIN datafetch_actor a ON canon.final_id = a.id
LEFT JOIN original_ranks orig ON orig.donor_id = canon.final_id
WHERE (canon.total_value - orig.total_value) > 0
ORDER BY aggregation_gain DESC
LIMIT 20;


-- ============================================================================
-- SECTION 4: DATA QUALITY INSIGHTS
-- ============================================================================

-- 4.1 "Shattered" Identities
-- Actors that appear as multiple distinct entities in the source data
-- but resolve to a single canonical entity across ALL datasets
WITH all_resolutions AS (
    -- Meeting resolutions
    SELECT canonical_actor_id as canon_id, actor_id as source_id
    FROM datafetch_meetingattendee
    WHERE canonical_actor_id != actor_id
    UNION
    -- Donation resolutions
    SELECT canonical_donor_id, donor_id
    FROM datafetch_donation
    WHERE canonical_donor_id != donor_id AND donor_id IS NOT NULL
    UNION
    -- Consultancy resolutions
    SELECT canonical_client_id, client_id
    FROM datafetch_consultancy
    WHERE canonical_client_id != client_id AND client_id IS NOT NULL
)
SELECT
    canon.name as canonical_entity,
    COUNT(DISTINCT source_id) as fragment_count,
    STRING_AGG(DISTINCT source.name, ' | ' ORDER BY source.name) as variations
FROM all_resolutions r
JOIN datafetch_actor canon ON r.canon_id = canon.id
JOIN datafetch_actor source ON r.source_id = source.id
GROUP BY canon.id, canon.name
HAVING COUNT(DISTINCT source_id) > 2
ORDER BY fragment_count DESC
LIMIT 30;
