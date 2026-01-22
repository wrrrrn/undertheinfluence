-- ============================================================
-- 13. LOBBYING AGENCY DIRECTOR & PSC (BENEFICIAL OWNER) ANALYSIS
-- ============================================================
-- Analyzes Companies House director and beneficial owner data
-- for lobbying agencies to identify ownership structures,
-- corporate consolidation, and political connections.
--
-- Data sources:
--   - Companies House Officers API (directors)
--   - Companies House PSC API (beneficial owners)
--   - Imported via: manage.py enrich_companies_house --fetch-all
-- ============================================================

-- ------------------------------------------------------------
-- 1. PEOPLE DIRECTING MULTIPLE LOBBYING AGENCIES
-- Identifies individuals with influence across multiple agencies
-- ------------------------------------------------------------
SELECT
    a.name AS director_name,
    COUNT(DISTINCT m.organization_id) AS agency_count,
    STRING_AGG(DISTINCT oa.name, ', ' ORDER BY oa.name) AS agencies
FROM datafetch_membership m
JOIN datafetch_person p ON m.person_id = p.actor_ptr_id
JOIN datafetch_actor a ON p.actor_ptr_id = a.id
JOIN datafetch_organization o ON m.organization_id = o.actor_ptr_id
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
WHERE m.role = 'Director'
GROUP BY a.name
HAVING COUNT(DISTINCT m.organization_id) > 1
ORDER BY agency_count DESC, a.name
LIMIT 20;


-- ------------------------------------------------------------
-- 2. LOBBYING AGENCIES WITH LARGEST BOARDS
-- Identifies agencies with most directors
-- ------------------------------------------------------------
SELECT
    oa.name AS agency_name,
    COUNT(m.id) AS director_count,
    STRING_AGG(pa.name, ', ' ORDER BY pa.name) AS directors
FROM datafetch_organization o
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
JOIN datafetch_membership m ON m.organization_id = o.actor_ptr_id
JOIN datafetch_person p ON m.person_id = p.actor_ptr_id
JOIN datafetch_actor pa ON p.actor_ptr_id = pa.id
WHERE m.role = 'Director'
GROUP BY oa.name
HAVING COUNT(m.id) > 3
ORDER BY director_count DESC
LIMIT 15;


-- ------------------------------------------------------------
-- 3. BENEFICIAL OWNERSHIP CONCENTRATION
-- Breakdown of ownership stakes across lobbying agencies
-- ------------------------------------------------------------
SELECT
    m.role AS ownership_type,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS percentage
FROM datafetch_membership m
WHERE m.role LIKE 'Beneficial Owner%'
GROUP BY m.role
ORDER BY count DESC;


-- ------------------------------------------------------------
-- 4. OWNER-OPERATORS
-- Directors who also own significant stakes in their agencies
-- ------------------------------------------------------------
SELECT
    pa.name AS person_name,
    oa.name AS agency_name,
    dir.role AS director_role,
    psc.role AS ownership_stake,
    psc.start_date AS ownership_since
FROM datafetch_membership dir
JOIN datafetch_membership psc ON dir.person_id = psc.person_id
    AND dir.organization_id = psc.organization_id
JOIN datafetch_person p ON dir.person_id = p.actor_ptr_id
JOIN datafetch_actor pa ON p.actor_ptr_id = pa.id
JOIN datafetch_organization o ON dir.organization_id = o.actor_ptr_id
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
WHERE dir.role = 'Director'
  AND psc.role LIKE 'Beneficial Owner%'
ORDER BY pa.name, oa.name;


-- ------------------------------------------------------------
-- 5. CORPORATE OWNERSHIP (HOLDING COMPANIES)
-- Identifies agencies owned by corporate entities
-- Uses Notes table where corporate PSCs are stored
-- ------------------------------------------------------------
SELECT
    oa.name AS agency_name,
    n.content AS corporate_owner_details
FROM datafetch_note n
JOIN django_content_type ct ON n.content_type_id = ct.id
JOIN datafetch_organization o ON n.object_id = o.actor_ptr_id
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
WHERE ct.model = 'organization'
  AND n.content LIKE 'Corporate Beneficial Owner:%'
ORDER BY oa.name;


-- ------------------------------------------------------------
-- 6. PARENT COMPANIES OWNING MULTIPLE AGENCIES
-- Groups agencies by their corporate parent
-- ------------------------------------------------------------
SELECT
    SUBSTRING(n.content FROM 'Corporate Beneficial Owner: ([^(]+)') AS parent_company,
    COUNT(DISTINCT o.actor_ptr_id) AS agencies_owned,
    STRING_AGG(DISTINCT oa.name, ', ' ORDER BY oa.name) AS agencies
FROM datafetch_note n
JOIN django_content_type ct ON n.content_type_id = ct.id
JOIN datafetch_organization o ON n.object_id = o.actor_ptr_id
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
WHERE ct.model = 'organization'
  AND n.content LIKE 'Corporate Beneficial Owner:%'
GROUP BY SUBSTRING(n.content FROM 'Corporate Beneficial Owner: ([^(]+)')
HAVING COUNT(DISTINCT o.actor_ptr_id) > 1
ORDER BY agencies_owned DESC;


-- ------------------------------------------------------------
-- 7. REVOLVING DOOR: FORMER MPs NOW LOBBYING DIRECTORS
-- Identifies former MPs who became lobbying agency directors
-- ------------------------------------------------------------
SELECT
    pa.name AS person_name,
    mp_role.role AS mp_role,
    mp_role.end_date AS left_parliament,
    STRING_AGG(DISTINCT oa.name, ', ') AS now_directs
FROM datafetch_membership dir
JOIN datafetch_person p ON dir.person_id = p.actor_ptr_id
JOIN datafetch_actor pa ON p.actor_ptr_id = pa.id
JOIN datafetch_organization o ON dir.organization_id = o.actor_ptr_id
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
JOIN datafetch_membership mp_role ON mp_role.person_id = p.actor_ptr_id
WHERE dir.role = 'Director'
  AND mp_role.role LIKE '%Member of Parliament%'
GROUP BY pa.name, mp_role.role, mp_role.end_date
ORDER BY mp_role.end_date DESC;


-- ------------------------------------------------------------
-- 8. LOBBYING AGENCIES IN MINISTERIAL MEETINGS
-- Agencies (with directors imported) that met with ministers
-- ------------------------------------------------------------
SELECT
    oa.name AS agency_name,
    COUNT(DISTINCT mm.id) AS meeting_count,
    COUNT(DISTINCT m.person_id) AS director_count,
    STRING_AGG(DISTINCT pa.name, ', ' ORDER BY pa.name) AS sample_directors
FROM datafetch_organization o
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
JOIN datafetch_membership m ON m.organization_id = o.actor_ptr_id AND m.role = 'Director'
JOIN datafetch_person p ON m.person_id = p.actor_ptr_id
JOIN datafetch_actor pa ON p.actor_ptr_id = pa.id
JOIN datafetch_ministerialmeeting mm ON mm.external_actor_id = o.actor_ptr_id
GROUP BY oa.name
ORDER BY meeting_count DESC
LIMIT 20;


-- ------------------------------------------------------------
-- 9. MINISTERS MEETING LOBBYING AGENCIES
-- Ministers ranked by meetings with lobbying agencies
-- ------------------------------------------------------------
SELECT
    ma.name AS minister_name,
    COUNT(DISTINCT mm.id) AS meetings_with_lobbying_agencies,
    STRING_AGG(DISTINCT oa.name, ', ' ORDER BY oa.name) AS agencies_met
FROM datafetch_ministerialmeeting mm
JOIN datafetch_person minister ON mm.minister_id = minister.actor_ptr_id
JOIN datafetch_actor ma ON minister.actor_ptr_id = ma.id
JOIN datafetch_organization o ON mm.external_actor_id = o.actor_ptr_id
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
WHERE EXISTS (
    SELECT 1 FROM datafetch_membership m
    WHERE m.organization_id = o.actor_ptr_id AND m.role = 'Director'
)
GROUP BY ma.name
ORDER BY meetings_with_lobbying_agencies DESC
LIMIT 15;


-- ------------------------------------------------------------
-- 10. MEETING DETAILS: LOBBYING AGENCIES WITH MINISTERS
-- Full details of meetings between ministers and lobbying agencies
-- ------------------------------------------------------------
SELECT
    mm.meeting_date,
    ma.name AS minister_name,
    oa.name AS agency_name,
    mm.purpose,
    dep.name AS department
FROM datafetch_ministerialmeeting mm
JOIN datafetch_person minister ON mm.minister_id = minister.actor_ptr_id
JOIN datafetch_actor ma ON minister.actor_ptr_id = ma.id
JOIN datafetch_organization o ON mm.external_actor_id = o.actor_ptr_id
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
JOIN datafetch_organization dep_org ON mm.department_id = dep_org.actor_ptr_id
JOIN datafetch_actor dep ON dep_org.actor_ptr_id = dep.id
WHERE EXISTS (
    SELECT 1 FROM datafetch_membership m
    WHERE m.organization_id = o.actor_ptr_id AND m.role = 'Director'
)
ORDER BY mm.meeting_date DESC
LIMIT 50;


-- ------------------------------------------------------------
-- 11. SUMMARY STATISTICS
-- High-level counts for director/PSC data
-- ------------------------------------------------------------
SELECT
    'Directors imported' AS metric,
    COUNT(*) AS value
FROM datafetch_membership WHERE role = 'Director'
UNION ALL
SELECT
    'Individual PSCs imported',
    COUNT(*)
FROM datafetch_membership WHERE role LIKE 'Beneficial Owner%'
UNION ALL
SELECT
    'Corporate PSCs (holding companies)',
    COUNT(*)
FROM datafetch_note n
JOIN django_content_type ct ON n.content_type_id = ct.id
WHERE ct.model = 'organization' AND n.content LIKE 'Corporate Beneficial Owner:%'
UNION ALL
SELECT
    'Unique directors',
    COUNT(DISTINCT person_id)
FROM datafetch_membership WHERE role = 'Director'
UNION ALL
SELECT
    'Agencies with directors',
    COUNT(DISTINCT organization_id)
FROM datafetch_membership WHERE role = 'Director'
UNION ALL
SELECT
    'Multi-agency directors',
    COUNT(*)
FROM (
    SELECT person_id
    FROM datafetch_membership
    WHERE role = 'Director'
    GROUP BY person_id
    HAVING COUNT(DISTINCT organization_id) > 1
) sub;


-- ------------------------------------------------------------
-- 12. DIRECTOR NETWORK: SHARED DIRECTORSHIPS
-- Identifies agencies that share directors (potential coordination)
-- ------------------------------------------------------------
WITH director_agencies AS (
    SELECT
        m.person_id,
        pa.name AS director_name,
        m.organization_id,
        oa.name AS agency_name
    FROM datafetch_membership m
    JOIN datafetch_person p ON m.person_id = p.actor_ptr_id
    JOIN datafetch_actor pa ON p.actor_ptr_id = pa.id
    JOIN datafetch_organization o ON m.organization_id = o.actor_ptr_id
    JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
    WHERE m.role = 'Director'
)
SELECT
    a1.agency_name AS agency_1,
    a2.agency_name AS agency_2,
    COUNT(DISTINCT a1.person_id) AS shared_directors,
    STRING_AGG(DISTINCT a1.director_name, ', ' ORDER BY a1.director_name) AS shared_director_names
FROM director_agencies a1
JOIN director_agencies a2 ON a1.person_id = a2.person_id
    AND a1.organization_id < a2.organization_id
GROUP BY a1.agency_name, a2.agency_name
HAVING COUNT(DISTINCT a1.person_id) > 0
ORDER BY shared_directors DESC, a1.agency_name
LIMIT 30;


-- ------------------------------------------------------------
-- 13. DIRECTORS/PSCS NAMED IN MINISTERIAL MEETINGS
-- Finds directors whose names appear in meeting attendee records
-- Note: Slow query due to ILIKE pattern matching
-- ------------------------------------------------------------
WITH directors_pscs AS (
    SELECT DISTINCT
        pa.name AS person_name,
        pa.id AS person_id,
        m.role,
        oa.name AS company_name
    FROM datafetch_membership m
    JOIN datafetch_person p ON m.person_id = p.actor_ptr_id
    JOIN datafetch_actor pa ON p.actor_ptr_id = pa.id
    JOIN datafetch_organization o ON m.organization_id = o.actor_ptr_id
    JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
    WHERE m.role = 'Director' OR m.role LIKE 'Beneficial Owner%'
)
SELECT
    dp.person_name,
    dp.role,
    dp.company_name,
    mm.meeting_date,
    ma.name AS minister_name,
    LEFT(mm.purpose, 80) AS purpose
FROM directors_pscs dp
JOIN datafetch_ministerialmeeting mm
    ON mm.external_actor_name_raw ILIKE '%' || dp.person_name || '%'
JOIN datafetch_person minister ON mm.minister_id = minister.actor_ptr_id
JOIN datafetch_actor ma ON minister.actor_ptr_id = ma.id
WHERE LENGTH(dp.person_name) > 10  -- avoid short name false positives
ORDER BY mm.meeting_date DESC
LIMIT 50;


-- ------------------------------------------------------------
-- 14. DIRECTORS/PSCS WHO ARE DIRECT MEETING ATTENDEES
-- Directors/PSCs recorded as Person external actors in meetings
-- ------------------------------------------------------------
WITH person_meetings AS (
    SELECT
        mm.id AS meeting_id,
        mm.meeting_date,
        mm.purpose,
        mm.external_actor_id,
        pa.name AS person_name,
        ma.name AS minister_name
    FROM datafetch_ministerialmeeting mm
    JOIN datafetch_person p ON mm.external_actor_id = p.actor_ptr_id
    JOIN datafetch_actor pa ON p.actor_ptr_id = pa.id
    JOIN datafetch_person minister ON mm.minister_id = minister.actor_ptr_id
    JOIN datafetch_actor ma ON minister.actor_ptr_id = ma.id
),
person_roles AS (
    SELECT
        m.person_id,
        m.role,
        oa.name AS company_name
    FROM datafetch_membership m
    JOIN datafetch_organization o ON m.organization_id = o.actor_ptr_id
    JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
    WHERE m.role = 'Director' OR m.role LIKE 'Beneficial Owner%'
)
SELECT
    pm.person_name,
    pr.role,
    pr.company_name,
    pm.meeting_date,
    pm.minister_name,
    LEFT(pm.purpose, 80) AS purpose
FROM person_meetings pm
JOIN person_roles pr ON pm.external_actor_id = pr.person_id
ORDER BY pm.meeting_date DESC;
