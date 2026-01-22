-- ============================================================================
-- Lobby Employee Analysis
-- ============================================================================
-- Analyzes employees of lobbying agencies, including:
-- - Agency size and employee counts
-- - "Revolving door" (former MPs now in lobbying)
-- - Employee mobility between agencies
-- - Data quality metrics
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. OVERVIEW STATISTICS
-- ----------------------------------------------------------------------------

-- Summary metrics
WITH agency_ids AS (
    SELECT DISTINCT agency_id FROM datafetch_consultancy WHERE agency_id IS NOT NULL
),
lobby_memberships AS (
    SELECT m.* FROM agency_ids ai
    JOIN datafetch_membership m ON m.organization_id = ai.agency_id
    WHERE m.person_id IS NOT NULL
)
SELECT
    'Total lobbying agencies' AS metric, COUNT(DISTINCT agency_id)::text AS value FROM agency_ids
UNION ALL SELECT 'Total membership records', COUNT(*)::text FROM lobby_memberships
UNION ALL SELECT 'Distinct employees', COUNT(DISTINCT person_id)::text FROM lobby_memberships
UNION ALL SELECT 'Records with start_date', COUNT(*)::text FROM lobby_memberships WHERE start_date IS NOT NULL AND start_date != ''
UNION ALL SELECT 'Records with end_date', COUNT(*)::text FROM lobby_memberships WHERE end_date IS NOT NULL AND end_date != ''
UNION ALL SELECT 'Records with role', COUNT(*)::text FROM lobby_memberships WHERE role IS NOT NULL AND role != '';

-- ----------------------------------------------------------------------------
-- 2. TOP LOBBYING AGENCIES BY EMPLOYEE COUNT
-- ----------------------------------------------------------------------------

WITH agency_ids AS (
    SELECT DISTINCT agency_id FROM datafetch_consultancy WHERE agency_id IS NOT NULL
)
SELECT
    o.actor_ptr_id AS org_id,
    a.name AS agency_name,
    o.classification,
    COUNT(DISTINCT m.person_id) AS employee_count,
    COUNT(DISTINCT c.client_id) AS client_count
FROM datafetch_organization o
JOIN datafetch_actor a ON o.actor_ptr_id = a.id
JOIN agency_ids ai ON o.actor_ptr_id = ai.agency_id
LEFT JOIN datafetch_membership m ON m.organization_id = o.actor_ptr_id
LEFT JOIN datafetch_consultancy c ON c.agency_id = o.actor_ptr_id
GROUP BY o.actor_ptr_id, a.name, o.classification
ORDER BY employee_count DESC
LIMIT 30;

-- ----------------------------------------------------------------------------
-- 3. AGENCY SIZE DISTRIBUTION
-- ----------------------------------------------------------------------------

WITH agency_ids AS (
    SELECT DISTINCT agency_id FROM datafetch_consultancy WHERE agency_id IS NOT NULL
),
agency_employee_counts AS (
    SELECT
        ai.agency_id,
        COUNT(DISTINCT m.person_id) AS emp_count
    FROM agency_ids ai
    LEFT JOIN datafetch_membership m ON m.organization_id = ai.agency_id
    GROUP BY ai.agency_id
)
SELECT
    CASE
        WHEN emp_count = 0 THEN '0 employees'
        WHEN emp_count BETWEEN 1 AND 10 THEN '1-10'
        WHEN emp_count BETWEEN 11 AND 50 THEN '11-50'
        WHEN emp_count BETWEEN 51 AND 100 THEN '51-100'
        WHEN emp_count BETWEEN 101 AND 200 THEN '101-200'
        WHEN emp_count BETWEEN 201 AND 500 THEN '201-500'
        ELSE '500+'
    END AS size_bucket,
    COUNT(*) AS agency_count
FROM agency_employee_counts
GROUP BY size_bucket
ORDER BY MIN(emp_count);

-- ----------------------------------------------------------------------------
-- 4. REVOLVING DOOR: FORMER MPS NOW IN LOBBYING
-- ----------------------------------------------------------------------------

WITH agency_ids AS (
    SELECT DISTINCT agency_id FROM datafetch_consultancy WHERE agency_id IS NOT NULL
),
person_content_type AS (
    SELECT id FROM django_content_type WHERE app_label = 'datafetch' AND model = 'person'
),
mp_identifiers AS (
    SELECT DISTINCT i.object_id AS person_id
    FROM datafetch_identifier i
    JOIN person_content_type pct ON i.content_type_id = pct.id
    WHERE i.scheme = 'uk.org.publicwhip'
)
SELECT
    p.name AS former_mp_name,
    STRING_AGG(DISTINCT a.name, ' | ' ORDER BY a.name) AS lobbying_agencies,
    COUNT(DISTINCT m.organization_id) AS agency_count
FROM mp_identifiers mpi
JOIN datafetch_actor p ON mpi.person_id = p.id
JOIN datafetch_membership m ON m.person_id = mpi.person_id
JOIN agency_ids ai ON m.organization_id = ai.agency_id
JOIN datafetch_actor a ON ai.agency_id = a.id
GROUP BY p.name
ORDER BY agency_count DESC, p.name;

-- ----------------------------------------------------------------------------
-- 5. EMPLOYEE MOBILITY BETWEEN AGENCIES
-- ----------------------------------------------------------------------------

-- Distribution of employees by number of agencies worked at
WITH agency_ids AS (
    SELECT DISTINCT agency_id FROM datafetch_consultancy WHERE agency_id IS NOT NULL
),
multi_agency_employees AS (
    SELECT
        m.person_id,
        COUNT(DISTINCT m.organization_id) AS agency_count
    FROM agency_ids ai
    JOIN datafetch_membership m ON m.organization_id = ai.agency_id
    WHERE m.person_id IS NOT NULL
    GROUP BY m.person_id
)
SELECT
    agency_count AS agencies_worked_at,
    COUNT(*) AS employee_count
FROM multi_agency_employees
GROUP BY agency_count
ORDER BY agency_count;

-- ----------------------------------------------------------------------------
-- 6. EMPLOYEES WHO WORKED AT 3+ AGENCIES (potential data quality issues filtered)
-- ----------------------------------------------------------------------------

WITH agency_ids AS (
    SELECT DISTINCT agency_id FROM datafetch_consultancy WHERE agency_id IS NOT NULL
),
-- Filter out known garbage names
clean_persons AS (
    SELECT p.id, p.name
    FROM datafetch_actor p
    JOIN datafetch_person per ON p.id = per.actor_ptr_id
    WHERE p.name NOT IN ('Client', 'Pro', 'Relevant Roles', 'Bono Clients', 'Councillor', 'Party Officer', 'Cllr')
      AND LENGTH(p.name) > 5
      AND p.name ~ '[A-Z][a-z]+ [A-Z][a-z]+'  -- proper name pattern (First Last)
),
multi_agency_employees AS (
    SELECT
        m.person_id,
        COUNT(DISTINCT m.organization_id) AS agency_count
    FROM agency_ids ai
    JOIN datafetch_membership m ON m.organization_id = ai.agency_id
    WHERE m.person_id IS NOT NULL
    GROUP BY m.person_id
    HAVING COUNT(DISTINCT m.organization_id) >= 3
)
SELECT
    cp.name AS employee_name,
    mae.agency_count,
    STRING_AGG(DISTINCT a.name, ', ' ORDER BY a.name) AS agencies
FROM multi_agency_employees mae
JOIN clean_persons cp ON mae.person_id = cp.id
JOIN datafetch_membership m ON m.person_id = mae.person_id
JOIN agency_ids ai ON m.organization_id = ai.agency_id
JOIN datafetch_actor a ON ai.agency_id = a.id
GROUP BY cp.name, mae.agency_count
ORDER BY mae.agency_count DESC, cp.name
LIMIT 50;

-- ============================================================================
-- DATA QUALITY ANALYSIS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 7. DUPLICATE MEMBERSHIP RECORDS
-- ----------------------------------------------------------------------------

-- Find exact duplicate person-organization pairs
WITH agency_ids AS (
    SELECT DISTINCT agency_id FROM datafetch_consultancy WHERE agency_id IS NOT NULL
)
SELECT
    p.name AS employee_name,
    a.name AS agency_name,
    COUNT(*) AS duplicate_count
FROM datafetch_membership m
JOIN agency_ids ai ON m.organization_id = ai.agency_id
JOIN datafetch_actor p ON m.person_id = p.id
JOIN datafetch_actor a ON m.organization_id = a.id
GROUP BY p.name, a.name
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
LIMIT 30;

-- ----------------------------------------------------------------------------
-- 8. NAME QUALITY ISSUES
-- ----------------------------------------------------------------------------

-- Suspicious employee names (too short, no space, garbage patterns)
WITH agency_ids AS (
    SELECT DISTINCT agency_id FROM datafetch_consultancy WHERE agency_id IS NOT NULL
)
SELECT
    p.name AS suspicious_name,
    COUNT(DISTINCT m.organization_id) AS orgs_count,
    COUNT(*) AS total_records,
    CASE
        WHEN LENGTH(p.name) < 5 THEN 'Too short'
        WHEN p.name !~ ' ' THEN 'No space (single word)'
        WHEN p.name ~ '^[A-Z][a-z]+$' THEN 'Single name only'
        WHEN p.name IN ('Client', 'Pro', 'Relevant Roles', 'Bono Clients') THEN 'Known garbage'
        WHEN p.name ~ 'Mc$' OR p.name ~ 'Mac$' THEN 'Truncated surname'
        ELSE 'Other pattern'
    END AS issue_type
FROM datafetch_membership m
JOIN agency_ids ai ON m.organization_id = ai.agency_id
JOIN datafetch_actor p ON m.person_id = p.id
WHERE LENGTH(p.name) < 5
   OR p.name !~ ' '
   OR p.name IN ('Client', 'Pro', 'Relevant Roles', 'Bono Clients', 'Councillor', 'Party Officer', 'Cllr')
   OR p.name ~ 'Mc$' OR p.name ~ 'Mac$'
GROUP BY p.name
ORDER BY total_records DESC
LIMIT 50;

-- ----------------------------------------------------------------------------
-- 9. AGENCY NAME VARIATIONS
-- ----------------------------------------------------------------------------

-- Find agencies with similar names (potential duplicates)
WITH agency_ids AS (
    SELECT DISTINCT agency_id FROM datafetch_consultancy WHERE agency_id IS NOT NULL
),
agency_names AS (
    SELECT DISTINCT a.id, a.name, LOWER(a.name) as name_lower
    FROM agency_ids ai
    JOIN datafetch_actor a ON ai.agency_id = a.id
)
SELECT
    an1.name AS agency_1,
    an2.name AS agency_2,
    similarity(an1.name_lower, an2.name_lower) AS name_similarity
FROM agency_names an1
CROSS JOIN agency_names an2
WHERE an1.id < an2.id
  AND similarity(an1.name_lower, an2.name_lower) > 0.5
ORDER BY name_similarity DESC
LIMIT 50;

-- Fallback if pg_trgm not installed: exact case variations
WITH agency_ids AS (
    SELECT DISTINCT agency_id FROM datafetch_consultancy WHERE agency_id IS NOT NULL
),
agency_names AS (
    SELECT a.id, a.name, LOWER(REGEXP_REPLACE(a.name, '[^a-zA-Z0-9]', '', 'g')) as name_normalized
    FROM agency_ids ai
    JOIN datafetch_actor a ON ai.agency_id = a.id
)
SELECT
    name_normalized,
    STRING_AGG(name, ' | ' ORDER BY name) AS variations,
    COUNT(*) AS variation_count
FROM agency_names
GROUP BY name_normalized
HAVING COUNT(*) > 1
ORDER BY variation_count DESC;
