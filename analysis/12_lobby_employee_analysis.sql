-- ============================================================================
-- LOBBY EMPLOYEE ANALYSIS
-- ============================================================================
-- Analyzes employees of lobbying agencies, including:
-- - Agency size and employee counts
-- - "Revolving door" (former MPs now in lobbying)
-- Date: 2026-01-26 (Updated with Canonical Resolution)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. OVERVIEW STATISTICS
-- ----------------------------------------------------------------------------
WITH agency_ids AS (
    SELECT DISTINCT COALESCE(canonical_agency_id, agency_id) as agency_id FROM datafetch_consultancy
),
lobby_memberships AS (
    SELECT m.* FROM agency_ids ai
    JOIN datafetch_membership m ON m.organization_id = ai.agency_id
)
SELECT 'Total lobbying agencies' AS metric, COUNT(*)::text AS value FROM agency_ids
UNION ALL 
SELECT 'Distinct employees', COUNT(DISTINCT person_id)::text FROM lobby_memberships;


-- ----------------------------------------------------------------------------
-- 2. TOP LOBBYING AGENCIES BY EMPLOYEE COUNT
-- ----------------------------------------------------------------------------
WITH agency_employees AS (
    SELECT
        COALESCE(c.canonical_agency_id, c.agency_id) as agency_id,
        COUNT(DISTINCT m.person_id) as employee_count
    FROM datafetch_consultancy c
    JOIN datafetch_membership m ON m.organization_id = c.agency_id -- Join on original ID to find members
    GROUP BY COALESCE(c.canonical_agency_id, c.agency_id)
)
SELECT
    a.name as agency_name,
    ae.employee_count
FROM agency_employees ae
JOIN datafetch_actor a ON ae.agency_id = a.id
ORDER BY ae.employee_count DESC
LIMIT 30;


-- ----------------------------------------------------------------------------
-- 3. REVOLVING DOOR: FORMER MPS NOW IN LOBBYING
-- ----------------------------------------------------------------------------
WITH former_mps AS (
    SELECT DISTINCT person_id 
    FROM datafetch_membership 
    WHERE role LIKE '%Member of Parliament%' AND end_date < CURRENT_DATE::text
),
lobbying_jobs AS (
    SELECT 
        m.person_id,
        m.organization_id,
        COALESCE(c.canonical_agency_id, c.agency_id) as canonical_agency_id
    FROM datafetch_membership m
    JOIN datafetch_consultancy c ON c.agency_id = m.organization_id
)
SELECT
    p.name AS former_mp_name,
    STRING_AGG(DISTINCT a.name, ' | ') AS lobbying_agencies
FROM former_mps fmp
JOIN lobbying_jobs lj ON fmp.person_id = lj.person_id
JOIN datafetch_actor p ON fmp.person_id = p.id
JOIN datafetch_actor a ON lj.canonical_agency_id = a.id
GROUP BY p.name
ORDER BY COUNT(DISTINCT lj.canonical_agency_id) DESC;