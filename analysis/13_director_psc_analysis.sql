-- ============================================================
-- 13. LOBBYING AGENCY DIRECTOR & PSC (BENEFICIAL OWNER) ANALYSIS
-- ============================================================
-- Analyzes Companies House director and beneficial owner data
-- for lobbying agencies to identify ownership structures.
-- Date: 2026-01-26 (Updated with Canonical Resolution)
-- ============================================================

-- ------------------------------------------------------------
-- 1. PEOPLE DIRECTING MULTIPLE LOBBYING AGENCIES
-- ------------------------------------------------------------
SELECT
    p.name AS director_name,
    COUNT(DISTINCT COALESCE(c.canonical_agency_id, c.agency_id)) AS agency_count,
    STRING_AGG(DISTINCT a.name, ', ') AS agencies
FROM datafetch_membership m
JOIN datafetch_consultancy c ON m.organization_id = c.agency_id
JOIN datafetch_actor p ON m.person_id = p.id
JOIN datafetch_actor a ON COALESCE(c.canonical_agency_id, c.agency_id) = a.id
WHERE m.role = 'Director'
GROUP BY p.name
HAVING COUNT(DISTINCT COALESCE(c.canonical_agency_id, c.agency_id)) > 1
ORDER BY agency_count DESC;


-- ------------------------------------------------------------
-- 2. BENEFICIAL OWNERSHIP CONCENTRATION
-- ------------------------------------------------------------
SELECT
    m.role AS ownership_type,
    COUNT(*) AS count
FROM datafetch_membership m
JOIN datafetch_consultancy c ON m.organization_id = c.agency_id
WHERE m.role LIKE 'Beneficial Owner%'
GROUP BY m.role
ORDER BY count DESC;


-- ------------------------------------------------------------
-- 3. CORPORATE OWNERSHIP (HOLDING COMPANIES)
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
-- 4. MINISTERS MEETING LOBBYING AGENCIES
-- ------------------------------------------------------------
SELECT
    p.name AS minister_name,
    COUNT(DISTINCT mm.id) AS meetings_with_lobbying_agencies,
    STRING_AGG(DISTINCT a.name, ', ') AS agencies_met
FROM datafetch_ministerialmeeting mm
JOIN datafetch_meetingattendee ma ON mm.id = ma.meeting_id
JOIN datafetch_consultancy c ON COALESCE(ma.canonical_actor_id, ma.actor_id) = COALESCE(c.canonical_agency_id, c.agency_id)
JOIN datafetch_actor p ON mm.minister_id = p.id
JOIN datafetch_actor a ON COALESCE(ma.canonical_actor_id, ma.actor_id) = a.id
GROUP BY p.name
ORDER BY meetings_with_lobbying_agencies DESC
LIMIT 15;