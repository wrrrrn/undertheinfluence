-- ============================================================================
-- MINISTERIAL INFLUENCE ANALYSIS (Funding + Meetings)
-- ============================================================================
-- Purpose: Comprehensive ministerial influence analysis combining donations AND meetings
-- Focus: Who funds ministers? Who meets with them? Where do funding and access overlap?
-- Date: 2026-01-26 (Updated with Canonical Resolution)
-- Database: PostgreSQL
-- ============================================================================

-- ============================================================================
-- SECTION 1: MINISTERIAL MEETINGS OVERVIEW
-- ============================================================================

-- 1.1 Total meetings by department
SELECT
    d.name as department,
    COUNT(*) as meetings,
    COUNT(DISTINCT mm.minister_id) as ministers,
    (SELECT COUNT(DISTINCT COALESCE(ma.canonical_actor_id, ma.actor_id)) 
     FROM datafetch_meetingattendee ma 
     JOIN datafetch_ministerialmeeting mm2 ON ma.meeting_id = mm2.id
     WHERE mm2.department_id = mm.department_id) as unique_external_actors
FROM datafetch_ministerialmeeting mm
JOIN datafetch_actor d ON mm.department_id = d.id
GROUP BY d.name, mm.department_id
ORDER BY meetings DESC;

-- 1.2 Top 50 external actors by ministerial access
SELECT
    COALESCE(canon.name, a.name) as organization,
    COUNT(DISTINCT mm.id) as meetings,
    COUNT(DISTINCT mm.minister_id) as ministers_met,
    COUNT(DISTINCT mm.department_id) as departments
FROM datafetch_meetingattendee ma
JOIN datafetch_ministerialmeeting mm ON ma.meeting_id = mm.id
JOIN datafetch_actor a ON ma.actor_id = a.id
LEFT JOIN datafetch_actor canon ON ma.canonical_actor_id = canon.id
GROUP BY COALESCE(ma.canonical_actor_id, ma.actor_id), COALESCE(canon.name, a.name)
ORDER BY meetings DESC
LIMIT 50;

-- 1.3 Top ministers by meeting count
SELECT
    p.name as minister,
    d.name as department,
    COUNT(DISTINCT mm.id) as meetings,
    COUNT(DISTINCT COALESCE(ma.canonical_actor_id, ma.actor_id)) as unique_actors_met
FROM datafetch_ministerialmeeting mm
JOIN datafetch_actor p ON mm.minister_id = p.id
JOIN datafetch_actor d ON mm.department_id = d.id
LEFT JOIN datafetch_meetingattendee ma ON mm.id = ma.meeting_id
GROUP BY p.name, d.name
ORDER BY meetings DESC
LIMIT 30;


-- ============================================================================
-- SECTION 2: MINISTERIAL FUNDING ANALYSIS
-- ============================================================================

-- 2.1 Top Individual Recipients (MPs/Lords/Politicians) by Total Donations
SELECT
  recipient.name AS person_name,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_received,
  COUNT(DISTINCT COALESCE(d.canonical_donor_id, d.donor_id)) AS distinct_donors,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor recipient ON COALESCE(d.canonical_recipient_id, d.recipient_id) = recipient.id
JOIN datafetch_person person ON person.actor_ptr_id = recipient.id
WHERE d.value > 0
GROUP BY recipient.id, recipient.name
ORDER BY total_received DESC
LIMIT 50;

-- 2.2 Current Ministers - Donations Received
WITH current_ministers AS (
  SELECT DISTINCT
    m.person_id,
    m.organization_id AS dept_id,
    m.role
  FROM datafetch_membership m
  WHERE m.role IS NOT NULL
    AND m.role != ''
    AND m.role NOT LIKE '%Member of Parliament%'
    AND m.role NOT LIKE '%MSP for%'
    AND (m.end_date IS NULL OR m.end_date = '' OR m.end_date >= CURRENT_DATE::text)
),
minister_donations AS (
  SELECT
    COALESCE(d.canonical_recipient_id, d.recipient_id) AS person_id,
    COUNT(*) AS donation_count,
    SUM(d.value) AS total_received,
    COUNT(DISTINCT COALESCE(d.canonical_donor_id, d.donor_id)) AS distinct_donors
  FROM datafetch_donation d
  WHERE d.value > 0
  GROUP BY COALESCE(d.canonical_recipient_id, d.recipient_id)
)
SELECT
  person.name AS person_name,
  MAX(cm.role) AS ministerial_role,
  MAX(dept.name) AS department,
  COALESCE(md.donation_count, 0) AS donation_count,
  COALESCE(md.total_received, 0) AS total_received,
  COALESCE(md.distinct_donors, 0) AS distinct_donors
FROM current_ministers cm
JOIN datafetch_actor person ON person.id = cm.person_id
LEFT JOIN datafetch_actor dept ON dept.id = cm.dept_id
LEFT JOIN minister_donations md ON md.person_id = cm.person_id
GROUP BY person.id, person.name, md.donation_count, md.total_received, md.distinct_donors
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 3: COMBINED MINISTERIAL ACCESS + FUNDING
-- ============================================================================

-- 3.1 Ministers with BOTH meetings AND donations - Full Profile
WITH minister_meetings AS (
    SELECT
        mm.minister_id,
        COUNT(DISTINCT mm.id) as meeting_count,
        COUNT(DISTINCT COALESCE(ma.canonical_actor_id, ma.actor_id)) as unique_orgs_met
    FROM datafetch_ministerialmeeting mm
    JOIN datafetch_meetingattendee ma ON mm.id = ma.meeting_id
    GROUP BY mm.minister_id
),
minister_donations AS (
    SELECT
        COALESCE(d.canonical_recipient_id, d.recipient_id) as minister_id,
        COUNT(*) as donation_count,
        SUM(d.value) as total_received
    FROM datafetch_donation d
    WHERE d.value > 0
    GROUP BY COALESCE(d.canonical_recipient_id, d.recipient_id)
)
SELECT
  p.name as minister,
  COALESCE(mm.meeting_count, 0) as meetings,
  COALESCE(mm.unique_orgs_met, 0) as orgs_met,
  COALESCE(md.donation_count, 0) as donations,
  COALESCE(md.total_received, 0) as total_received
FROM datafetch_actor p
JOIN datafetch_person person ON person.actor_ptr_id = p.id
LEFT JOIN minister_meetings mm ON mm.minister_id = p.id
LEFT JOIN minister_donations md ON md.minister_id = p.id
WHERE (mm.meeting_count > 0 OR md.donation_count > 0)
ORDER BY COALESCE(md.total_received, 0) + (COALESCE(mm.meeting_count, 0) * 1000) DESC
LIMIT 50;

-- 3.2 Organizations with BOTH ministerial access AND donations
-- The "full influence" organizations
WITH meeting_orgs AS (
    SELECT
        COALESCE(ma.canonical_actor_id, ma.actor_id) as org_id,
        COUNT(DISTINCT mm.id) as meeting_count,
        COUNT(DISTINCT mm.minister_id) as ministers_met
    FROM datafetch_meetingattendee ma
    JOIN datafetch_ministerialmeeting mm ON ma.meeting_id = mm.id
    GROUP BY COALESCE(ma.canonical_actor_id, ma.actor_id)
),
donor_orgs AS (
    SELECT
        COALESCE(d.canonical_donor_id, d.donor_id) as org_id,
        SUM(d.value) as total_donated,
        COUNT(*) as donation_count
    FROM datafetch_donation d
    WHERE d.value > 0
    GROUP BY COALESCE(d.canonical_donor_id, d.donor_id)
)
SELECT
    a.name as organization,
    COALESCE(mo.meeting_count, 0) as meetings,
    COALESCE(do.total_donated, 0) as total_donated,
    CASE
        WHEN mo.org_id IS NOT NULL AND do.org_id IS NOT NULL THEN 'Full Influence (Meetings + Donations)'
        WHEN mo.org_id IS NOT NULL THEN 'Access Only (Meetings)'
        WHEN do.org_id IS NOT NULL THEN 'Funding Only (Donations)'
    END as influence_type
FROM datafetch_actor a
LEFT JOIN meeting_orgs mo ON mo.org_id = a.id
LEFT JOIN donor_orgs do ON do.org_id = a.id
WHERE (mo.org_id IS NOT NULL OR do.org_id IS NOT NULL)
  AND (mo.meeting_count > 5 OR do.total_donated > 5000)
ORDER BY
    CASE WHEN mo.org_id IS NOT NULL AND do.org_id IS NOT NULL THEN 0 ELSE 1 END,
    COALESCE(do.total_donated, 0) DESC
LIMIT 100;


-- ============================================================================
-- SECTION 4: MEETING TOPICS & PATTERNS
-- ============================================================================

-- 4.1 Meeting topics by keyword analysis
SELECT
    CASE
        WHEN purpose ILIKE '%AI%' OR purpose ILIKE '%artificial intelligence%' THEN 'AI/Artificial Intelligence'
        WHEN purpose ILIKE '%climate%' OR purpose ILIKE '%net zero%' OR purpose ILIKE '%green%' THEN 'Climate/Environment'
        WHEN purpose ILIKE '%digital%' OR purpose ILIKE '%online%' OR purpose ILIKE '%internet%' THEN 'Digital/Online'
        WHEN purpose ILIKE '%trade%' OR purpose ILIKE '%export%' OR purpose ILIKE '%import%' THEN 'Trade'
        WHEN purpose ILIKE '%health%' OR purpose ILIKE '%NHS%' OR purpose ILIKE '%pharmaceutical%' THEN 'Health/Pharma'
        WHEN purpose ILIKE '%transport%' OR purpose ILIKE '%rail%' OR purpose ILIKE '%road%' OR purpose ILIKE '%EV%' THEN 'Transport'
        WHEN purpose ILIKE '%invest%' THEN 'Investment'
        WHEN purpose ILIKE '%housing%' OR purpose ILIKE '%planning%' THEN 'Housing/Planning'
        ELSE 'Other'
    END as topic,
    COUNT(*) as meetings
FROM datafetch_ministerialmeeting mm
WHERE purpose IS NOT NULL AND purpose != ''
GROUP BY topic
ORDER BY meetings DESC;


-- ============================================================================
-- SECTION 5: MINISTERIAL RANK & SENIORITY ANALYSIS
-- ============================================================================

-- 5.1 Ministerial Rank - Combined Meetings and Funding
WITH ministerial_ranks AS (
  SELECT
    m.person_id,
    m.role,
    CASE
      WHEN m.role LIKE '%Secretary of State%' THEN 'Cabinet - Secretary of State'
      WHEN m.role LIKE '%Minister of State%' THEN 'Junior - Minister of State'
      WHEN m.role LIKE '%Parliamentary Under-Secretary%' THEN 'Junior - Parliamentary Under-Secretary'
      ELSE 'Other Ministerial Role'
    END AS rank_category
  FROM datafetch_membership m
  WHERE m.role IS NOT NULL AND m.role != ''
),
rank_donations AS (
  SELECT
    mr.rank_category,
    COUNT(*) AS total_donations,
    SUM(d.value) AS total_received
  FROM ministerial_ranks mr
  JOIN datafetch_donation d ON COALESCE(d.canonical_recipient_id, d.recipient_id) = mr.person_id
  WHERE d.value > 0
  GROUP BY mr.rank_category
),
rank_meetings AS (
  SELECT
    mr.rank_category,
    COUNT(*) AS total_meetings
  FROM ministerial_ranks mr
  JOIN datafetch_ministerialmeeting mm ON mm.minister_id = mr.person_id
  GROUP BY mr.rank_category
)
SELECT
  COALESCE(rd.rank_category, rm.rank_category) as rank_category,
  COALESCE(rd.total_received, 0) as total_received,
  COALESCE(rm.total_meetings, 0) as meetings
FROM rank_donations rd
FULL OUTER JOIN rank_meetings rm ON rm.rank_category = rd.rank_category
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 6: TECH GIANTS PROFILE (Meetings + Funding)
-- ============================================================================

-- 6.1 Tech company influence summary
SELECT
    COALESCE(canon.name, a.name) as company,
    COUNT(DISTINCT mm.id) as meetings,
    COUNT(DISTINCT mm.minister_id) as ministers_met,
    COALESCE((
        SELECT SUM(d.value)
        FROM datafetch_donation d
        WHERE COALESCE(d.canonical_donor_id, d.donor_id) = COALESCE(ma.canonical_actor_id, ma.actor_id) 
          AND d.value > 0
    ), 0) as total_donated
FROM datafetch_meetingattendee ma
JOIN datafetch_ministerialmeeting mm ON ma.meeting_id = mm.id
JOIN datafetch_actor a ON ma.actor_id = a.id
LEFT JOIN datafetch_actor canon ON ma.canonical_actor_id = canon.id
WHERE LOWER(COALESCE(canon.name, a.name)) IN ('google', 'meta', 'microsoft', 'amazon', 'apple', 'openai', 'x')
GROUP BY COALESCE(ma.canonical_actor_id, ma.actor_id), COALESCE(canon.name, a.name)
ORDER BY meetings DESC;


-- ============================================================================
-- SECTION 7: SUMMARY STATISTICS
-- ============================================================================

-- 7.1 Ministerial meetings summary
SELECT
    'Total Meetings' as metric, COUNT(*)::text as value FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Unique External Actors', COUNT(DISTINCT COALESCE(canonical_actor_id, actor_id))::text FROM datafetch_meetingattendee
UNION ALL
SELECT 'Unique Ministers', COUNT(DISTINCT minister_id)::text FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Departments Covered', COUNT(DISTINCT department_id)::text FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Roundtable Meetings', COUNT(*)::text FROM datafetch_ministerialmeeting WHERE is_roundtable = true;