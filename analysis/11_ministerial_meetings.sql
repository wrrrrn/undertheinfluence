-- =============================================================================
-- 11. MINISTERIAL MEETINGS & LOBBYING PRACTITIONERS ANALYSIS
-- =============================================================================
-- Focus: GOV.UK ministerial transparency data and lobbying practitioner connections
-- Data: 7,183 meetings across 8 departments (as of Jan 2026)
--
-- Key Questions Answered:
-- - Who has the most ministerial access?
-- - Which ministers meet most frequently with external actors?
-- - How do lobbying, donations, and meetings interconnect?
-- - Which practitioners lobby for which clients?
-- =============================================================================

-- =============================================================================
-- SECTION 1: MINISTERIAL MEETINGS OVERVIEW
-- =============================================================================

-- 1.1 Total meetings by department
-- Shows distribution of transparency data across government
SELECT
    d.name as department,
    COUNT(*) as meetings,
    COUNT(DISTINCT mm.minister_id) as ministers,
    COUNT(DISTINCT mm.external_actor_id) as external_actors
FROM datafetch_ministerialmeeting mm
JOIN datafetch_actor d ON mm.department_id = d.id
GROUP BY d.name
ORDER BY meetings DESC;

-- 1.2 Top 50 external actors by ministerial access
-- Who gets the most face time with ministers?
SELECT
    a.name as organization,
    COUNT(*) as meetings,
    COUNT(DISTINCT mm.minister_id) as ministers_met,
    COUNT(DISTINCT mm.department_id) as departments
FROM datafetch_ministerialmeeting mm
JOIN datafetch_actor a ON mm.external_actor_id = a.id
GROUP BY a.id, a.name
ORDER BY meetings DESC
LIMIT 50;

-- 1.3 Top ministers by meeting count
-- Which ministers are most accessible?
SELECT
    p.name as minister,
    d.name as department,
    COUNT(*) as meetings,
    COUNT(DISTINCT mm.external_actor_id) as unique_actors
FROM datafetch_ministerialmeeting mm
JOIN datafetch_actor p ON mm.minister_id = p.id
JOIN datafetch_actor d ON mm.department_id = d.id
GROUP BY p.name, d.name
ORDER BY meetings DESC
LIMIT 30;

-- =============================================================================
-- SECTION 2: MEETING TOPICS & PATTERNS
-- =============================================================================

-- 2.1 Meeting topics by keyword analysis
-- What are ministers discussing?
SELECT
    CASE
        WHEN purpose ILIKE '%AI%' OR purpose ILIKE '%artificial intelligence%' THEN 'AI/Artificial Intelligence'
        WHEN purpose ILIKE '%climate%' OR purpose ILIKE '%net zero%' OR purpose ILIKE '%green%' THEN 'Climate/Environment'
        WHEN purpose ILIKE '%digital%' OR purpose ILIKE '%online%' OR purpose ILIKE '%internet%' THEN 'Digital/Online'
        WHEN purpose ILIKE '%trade%' OR purpose ILIKE '%export%' OR purpose ILIKE '%import%' THEN 'Trade'
        WHEN purpose ILIKE '%health%' OR purpose ILIKE '%NHS%' OR purpose ILIKE '%pharmaceutical%' THEN 'Health/Pharma'
        WHEN purpose ILIKE '%transport%' OR purpose ILIKE '%rail%' OR purpose ILIKE '%road%' OR purpose ILIKE '%EV%' THEN 'Transport'
        WHEN purpose ILIKE '%invest%' THEN 'Investment'
        WHEN purpose ILIKE '%skill%' OR purpose ILIKE '%education%' OR purpose ILIKE '%training%' THEN 'Skills/Education'
        WHEN purpose ILIKE '%energy%' OR purpose ILIKE '%nuclear%' OR purpose ILIKE '%power%' THEN 'Energy'
        WHEN purpose ILIKE '%housing%' OR purpose ILIKE '%planning%' THEN 'Housing/Planning'
        WHEN purpose ILIKE '%safety%' OR purpose ILIKE '%child%' THEN 'Safety/Child Protection'
        ELSE 'Other'
    END as topic,
    COUNT(*) as meetings,
    COUNT(DISTINCT mm.external_actor_id) as unique_actors
FROM datafetch_ministerialmeeting mm
WHERE purpose IS NOT NULL AND purpose != ''
GROUP BY topic
ORDER BY meetings DESC;

-- 2.2 Tech company meetings vs child safety group meetings
-- Guardian-style analysis
WITH tech_meetings AS (
    SELECT COUNT(*) as count
    FROM datafetch_ministerialmeeting mm
    JOIN datafetch_actor a ON mm.external_actor_id = a.id
    WHERE LOWER(a.name) IN ('google', 'meta', 'amazon', 'apple', 'microsoft', 'x', 'tiktok', 'openai')
),
safety_meetings AS (
    SELECT COUNT(*) as count
    FROM datafetch_ministerialmeeting mm
    WHERE purpose ILIKE '%child%' OR purpose ILIKE '%safety%'
)
SELECT
    'Tech Companies' as category,
    (SELECT count FROM tech_meetings) as meetings
UNION ALL
SELECT
    'Child Safety Topics',
    (SELECT count FROM safety_meetings);

-- =============================================================================
-- SECTION 3: LOBBYING INFRASTRUCTURE
-- =============================================================================

-- 3.1 Lobbying overview statistics
SELECT
    'Total Consultancies' as metric, COUNT(*)::text as value FROM datafetch_consultancy
UNION ALL
SELECT 'Unique Clients', COUNT(DISTINCT client_id)::text FROM datafetch_consultancy
UNION ALL
SELECT 'Unique Agencies', COUNT(DISTINCT agency_id)::text FROM datafetch_consultancy;

-- 3.2 Top lobbying agencies by client count
SELECT
    a.name as agency,
    COUNT(DISTINCT c.client_id) as clients,
    COUNT(*) as consultancy_records
FROM datafetch_consultancy c
JOIN datafetch_actor a ON c.agency_id = a.id
GROUP BY a.id, a.name
ORDER BY clients DESC
LIMIT 30;

-- 3.3 Top lobbying agencies by practitioner headcount
SELECT
    oa.name as agency,
    COUNT(DISTINCT pa.id) as practitioners
FROM datafetch_membership m
JOIN datafetch_person p ON m.person_id = p.actor_ptr_id
JOIN datafetch_actor pa ON p.actor_ptr_id = pa.id
JOIN datafetch_organization o ON m.organization_id = o.actor_ptr_id
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
WHERE oa.name IN (
    SELECT DISTINCT a2.name
    FROM datafetch_consultancy c2
    JOIN datafetch_actor a2 ON c2.agency_id = a2.id
)
GROUP BY oa.name
ORDER BY practitioners DESC
LIMIT 30;

-- =============================================================================
-- SECTION 4: THE INFLUENCE TRIANGLE (Meetings + Lobbying + Donations)
-- =============================================================================

-- 4.1 Organizations with BOTH ministerial meetings AND lobbying clients
-- Shows companies that pay lobbyists AND meet directly with ministers
WITH meeting_orgs AS (
    SELECT DISTINCT a.id, a.name
    FROM datafetch_ministerialmeeting mm
    JOIN datafetch_actor a ON mm.external_actor_id = a.id
),
lobbying_clients AS (
    SELECT DISTINCT a.id, a.name
    FROM datafetch_consultancy c
    JOIN datafetch_actor a ON c.client_id = a.id
)
SELECT
    mo.name as organization,
    (SELECT COUNT(*) FROM datafetch_ministerialmeeting mm WHERE mm.external_actor_id = mo.id) as meetings,
    (SELECT COUNT(DISTINCT agency_id) FROM datafetch_consultancy c WHERE c.client_id = lc.id) as lobbying_agencies
FROM meeting_orgs mo
JOIN lobbying_clients lc ON LOWER(mo.name) = LOWER(lc.name)
ORDER BY meetings DESC
LIMIT 50;

-- 4.2 Full influence triangle: meetings + lobbying + donations
WITH meeting_orgs AS (
    SELECT a.id, a.name, COUNT(*) as meeting_count
    FROM datafetch_ministerialmeeting mm
    JOIN datafetch_actor a ON mm.external_actor_id = a.id
    GROUP BY a.id, a.name
    HAVING COUNT(*) >= 2
),
lobbying_clients AS (
    SELECT a.id, a.name, COUNT(DISTINCT agency_id) as agency_count
    FROM datafetch_consultancy c
    JOIN datafetch_actor a ON c.client_id = a.id
    GROUP BY a.id, a.name
),
donors AS (
    SELECT a.id, a.name, SUM(d.value) as total_donated
    FROM datafetch_donation d
    JOIN datafetch_actor a ON d.donor_id = a.id
    WHERE d.value > 1000
    GROUP BY a.id, a.name
)
SELECT
    COALESCE(mo.name, lc.name, dn.name) as organization,
    COALESCE(mo.meeting_count, 0) as meetings,
    COALESCE(lc.agency_count, 0) as lobbyist_agencies,
    COALESCE(dn.total_donated, 0) as total_donated
FROM meeting_orgs mo
FULL OUTER JOIN lobbying_clients lc ON LOWER(mo.name) = LOWER(lc.name)
FULL OUTER JOIN donors dn ON LOWER(COALESCE(mo.name, lc.name)) = LOWER(dn.name)
WHERE (mo.meeting_count > 0 OR lc.agency_count > 0 OR dn.total_donated > 0)
  AND (
    (mo.meeting_count > 0 AND lc.agency_count > 0) OR
    (mo.meeting_count > 0 AND dn.total_donated > 0) OR
    (lc.agency_count > 0 AND dn.total_donated > 0)
  )
ORDER BY meetings DESC, total_donated DESC
LIMIT 50;

-- =============================================================================
-- SECTION 5: TECH GIANTS' LOBBYING NETWORKS
-- =============================================================================

-- 5.1 Which lobbying agencies do tech giants use?
SELECT
    client_a.name as company,
    agency_a.name as lobbying_agency,
    COUNT(*) as records,
    MIN(c.start_date) as first_engagement,
    MAX(c.end_date) as last_engagement
FROM datafetch_consultancy c
JOIN datafetch_actor client_a ON c.client_id = client_a.id
JOIN datafetch_actor agency_a ON c.agency_id = agency_a.id
WHERE LOWER(client_a.name) IN (
    'google', 'meta', 'microsoft', 'amazon', 'apple', 'uber',
    'airbus', 'nissan', 'stellantis', 'astrazeneca', 'gsk', 'novartis'
)
GROUP BY client_a.name, agency_a.name
ORDER BY client_a.name, records DESC;

-- 5.2 Tech company ministerial access summary
SELECT
    a.name as company,
    COUNT(*) as meetings,
    COUNT(DISTINCT mm.minister_id) as ministers_met,
    COUNT(DISTINCT mm.department_id) as departments,
    (SELECT COUNT(DISTINCT agency_id)
     FROM datafetch_consultancy c
     WHERE LOWER((SELECT name FROM datafetch_actor WHERE id = c.client_id)) = LOWER(a.name)
    ) as lobbying_agencies
FROM datafetch_ministerialmeeting mm
JOIN datafetch_actor a ON mm.external_actor_id = a.id
WHERE LOWER(a.name) IN ('google', 'meta', 'microsoft', 'amazon', 'apple', 'openai', 'x')
GROUP BY a.id, a.name
ORDER BY meetings DESC;

-- =============================================================================
-- SECTION 6: TRADE UNIONS - FULL SPECTRUM INFLUENCE
-- =============================================================================

-- 6.1 Trade unions with meetings, lobbying, AND donations
-- Unions are unique in using all three influence channels
SELECT
    a.name as union_name,
    COALESCE(meetings.count, 0) as ministerial_meetings,
    COALESCE(lobbying.agency_count, 0) as lobbying_agencies,
    COALESCE(donations.total, 0) as total_donated,
    COALESCE(donations.donation_count, 0) as donation_count
FROM datafetch_actor a
JOIN datafetch_organization o ON a.id = o.actor_ptr_id
LEFT JOIN (
    SELECT external_actor_id, COUNT(*) as count
    FROM datafetch_ministerialmeeting
    GROUP BY external_actor_id
) meetings ON a.id = meetings.external_actor_id
LEFT JOIN (
    SELECT client_id, COUNT(DISTINCT agency_id) as agency_count
    FROM datafetch_consultancy
    GROUP BY client_id
) lobbying ON a.id = lobbying.client_id
LEFT JOIN (
    SELECT donor_id, SUM(value) as total, COUNT(*) as donation_count
    FROM datafetch_donation
    WHERE value > 0
    GROUP BY donor_id
) donations ON a.id = donations.donor_id
WHERE o.classification ILIKE '%union%'
  AND (meetings.count > 0 OR lobbying.agency_count > 0 OR donations.total > 0)
ORDER BY donations.total DESC NULLS LAST
LIMIT 30;

-- =============================================================================
-- SECTION 7: LOBBYING PRACTITIONERS
-- =============================================================================

-- 7.1 Total practitioners count
SELECT
    'Total practitioners in lobbying agencies' as metric,
    COUNT(DISTINCT pa.id)::text as value
FROM datafetch_membership m
JOIN datafetch_person p ON m.person_id = p.actor_ptr_id
JOIN datafetch_actor pa ON p.actor_ptr_id = pa.id
JOIN datafetch_organization o ON m.organization_id = o.actor_ptr_id
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
WHERE oa.name IN (
    SELECT DISTINCT a2.name
    FROM datafetch_consultancy c2
    JOIN datafetch_actor a2 ON c2.agency_id = a2.id
);

-- 7.2 Sample practitioners from top agency (Portland)
SELECT DISTINCT pa.name as practitioner
FROM datafetch_membership m
JOIN datafetch_person p ON m.person_id = p.actor_ptr_id
JOIN datafetch_actor pa ON p.actor_ptr_id = pa.id
JOIN datafetch_organization o ON m.organization_id = o.actor_ptr_id
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
WHERE oa.name = 'Portland'
ORDER BY pa.name
LIMIT 50;

-- 7.3 Search for notable political names in lobbying practitioners
-- (Former ministers, special advisors, etc.)
SELECT DISTINCT pa.name as practitioner, oa.name as agency
FROM datafetch_membership m
JOIN datafetch_person p ON m.person_id = p.actor_ptr_id
JOIN datafetch_actor pa ON p.actor_ptr_id = pa.id
JOIN datafetch_organization o ON m.organization_id = o.actor_ptr_id
JOIN datafetch_actor oa ON o.actor_ptr_id = oa.id
WHERE oa.name IN (
    SELECT DISTINCT a2.name
    FROM datafetch_consultancy c2
    JOIN datafetch_actor a2 ON c2.agency_id = a2.id
)
AND (
    pa.name ILIKE '%campbell%' OR
    pa.name ILIKE '%mandelson%' OR
    pa.name ILIKE '%blair%' OR
    pa.name ILIKE '%osborne%' OR
    pa.name ILIKE '%cameron%' OR
    pa.name ILIKE '%clegg%' OR
    pa.name ILIKE '%hilton%'
)
ORDER BY pa.name;

-- =============================================================================
-- SECTION 8: SPECIFIC ORGANIZATION DEEP DIVES
-- =============================================================================

-- 8.1 Google's full influence profile
SELECT
    'Google' as organization,
    (SELECT COUNT(*) FROM datafetch_ministerialmeeting mm
     JOIN datafetch_actor a ON mm.external_actor_id = a.id
     WHERE LOWER(a.name) = 'google') as ministerial_meetings,
    (SELECT COUNT(DISTINCT agency_id) FROM datafetch_consultancy c
     JOIN datafetch_actor a ON c.client_id = a.id
     WHERE LOWER(a.name) = 'google') as lobbying_agencies,
    (SELECT COALESCE(SUM(value), 0) FROM datafetch_donation d
     JOIN datafetch_actor a ON d.donor_id = a.id
     WHERE LOWER(a.name) = 'google') as total_donated;

-- 8.2 Google's ministerial meetings detail
SELECT
    p.name as minister,
    d.name as department,
    mm.meeting_date,
    mm.purpose
FROM datafetch_ministerialmeeting mm
JOIN datafetch_actor a ON mm.external_actor_id = a.id
JOIN datafetch_actor p ON mm.minister_id = p.id
JOIN datafetch_actor d ON mm.department_id = d.id
WHERE LOWER(a.name) = 'google'
ORDER BY mm.meeting_date DESC
LIMIT 30;

-- 8.3 Google's lobbying agencies
SELECT
    agency_a.name as lobbying_agency,
    COUNT(*) as records,
    MIN(c.start_date) as first_engagement,
    MAX(c.end_date) as last_engagement
FROM datafetch_consultancy c
JOIN datafetch_actor client_a ON c.client_id = client_a.id
JOIN datafetch_actor agency_a ON c.agency_id = agency_a.id
WHERE LOWER(client_a.name) = 'google'
GROUP BY agency_a.name
ORDER BY records DESC;

-- =============================================================================
-- SECTION 9: SUMMARY STATISTICS
-- =============================================================================

-- 9.1 Ministerial meetings summary
SELECT
    'Total Meetings' as metric, COUNT(*)::text as value FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Unique External Actors', COUNT(DISTINCT external_actor_id)::text FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Unique Ministers', COUNT(DISTINCT minister_id)::text FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Departments Covered', COUNT(DISTINCT department_id)::text FROM datafetch_ministerialmeeting;

-- 9.2 Cross-reference summary: How many orgs use multiple influence channels?
WITH meeting_orgs AS (
    SELECT DISTINCT LOWER(a.name) as name
    FROM datafetch_ministerialmeeting mm
    JOIN datafetch_actor a ON mm.external_actor_id = a.id
),
lobbying_clients AS (
    SELECT DISTINCT LOWER(a.name) as name
    FROM datafetch_consultancy c
    JOIN datafetch_actor a ON c.client_id = a.id
),
donors AS (
    SELECT DISTINCT LOWER(a.name) as name
    FROM datafetch_donation d
    JOIN datafetch_actor a ON d.donor_id = a.id
    WHERE d.value > 1000
)
SELECT
    'Orgs with meetings only' as category,
    COUNT(*) as count
FROM meeting_orgs mo
WHERE mo.name NOT IN (SELECT name FROM lobbying_clients)
  AND mo.name NOT IN (SELECT name FROM donors)
UNION ALL
SELECT
    'Orgs with meetings + lobbying',
    COUNT(*)
FROM meeting_orgs mo
WHERE mo.name IN (SELECT name FROM lobbying_clients)
  AND mo.name NOT IN (SELECT name FROM donors)
UNION ALL
SELECT
    'Orgs with meetings + donations',
    COUNT(*)
FROM meeting_orgs mo
WHERE mo.name NOT IN (SELECT name FROM lobbying_clients)
  AND mo.name IN (SELECT name FROM donors)
UNION ALL
SELECT
    'Orgs with ALL THREE (meetings + lobbying + donations)',
    COUNT(*)
FROM meeting_orgs mo
WHERE mo.name IN (SELECT name FROM lobbying_clients)
  AND mo.name IN (SELECT name FROM donors);
