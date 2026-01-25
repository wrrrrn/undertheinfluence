-- ============================================================================
-- MINISTERIAL INFLUENCE ANALYSIS (Funding + Meetings)
-- ============================================================================
-- Purpose: Comprehensive ministerial influence analysis combining donations AND meetings
-- Focus: Who funds ministers? Who meets with them? Where do funding and access overlap?
-- Date: 2026-01-22
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
    COUNT(DISTINCT mm.external_actor_id) as external_actors
FROM datafetch_ministerialmeeting mm
JOIN datafetch_actor d ON mm.department_id = d.id
GROUP BY d.name
ORDER BY meetings DESC;

-- 1.2 Top 50 external actors by ministerial access
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

-- 1.4 Meeting attendees breakdown by meeting
-- Shows how many attendees per meeting (now that we've split concatenated lists)
SELECT
    COUNT(*) as total_meetings,
    COUNT(DISTINCT mm.id) FILTER (WHERE ma_count.attendee_count = 1) as single_attendee_meetings,
    COUNT(DISTINCT mm.id) FILTER (WHERE ma_count.attendee_count BETWEEN 2 AND 5) as small_group_meetings,
    COUNT(DISTINCT mm.id) FILTER (WHERE ma_count.attendee_count > 5) as large_meetings,
    ROUND(AVG(ma_count.attendee_count), 2) as avg_attendees_per_meeting
FROM datafetch_ministerialmeeting mm
LEFT JOIN (
    SELECT meeting_id, COUNT(*) as attendee_count
    FROM datafetch_meetingattendee
    GROUP BY meeting_id
) ma_count ON ma_count.meeting_id = mm.id;


-- ============================================================================
-- SECTION 2: MINISTERIAL FUNDING ANALYSIS
-- ============================================================================

-- 2.1 Top Individual Recipients (MPs/Lords/Politicians) by Total Donations
SELECT
  recipient.id AS person_id,
  MAX(recipient.name) AS person_name,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_received,
  COUNT(DISTINCT d.donor_id) AS distinct_donors,
  ROUND(AVG(d.value), 2) AS avg_donation,
  MIN(d.received_date) AS first_donation,
  MAX(d.received_date) AS latest_donation
FROM datafetch_donation d
JOIN datafetch_actor recipient ON recipient.id = d.recipient_id
JOIN datafetch_person person ON person.actor_ptr_id = recipient.id
WHERE d.value > 0
GROUP BY recipient.id
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
    AND m.role NOT LIKE '%Member of the Scottish Parliament%'
    AND (m.end_date IS NULL OR m.end_date = '' OR m.end_date >= CURRENT_DATE::text)
),
minister_donations AS (
  SELECT
    d.recipient_id AS person_id,
    COUNT(*) AS donation_count,
    SUM(d.value) AS total_received,
    COUNT(DISTINCT d.donor_id) AS distinct_donors,
    MIN(d.received_date) AS first_donation,
    MAX(d.received_date) AS latest_donation
  FROM datafetch_donation d
  WHERE d.value > 0
  GROUP BY d.recipient_id
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  MAX(cm.role) AS ministerial_role,
  MAX(dept.name) AS department,
  COALESCE(md.donation_count, 0) AS donation_count,
  COALESCE(md.total_received, 0) AS total_received,
  COALESCE(md.distinct_donors, 0) AS distinct_donors,
  md.first_donation,
  md.latest_donation
FROM current_ministers cm
JOIN datafetch_actor person ON person.id = cm.person_id
LEFT JOIN datafetch_actor dept ON dept.id = cm.dept_id
LEFT JOIN minister_donations md ON md.person_id = cm.person_id
GROUP BY person.id, md.donation_count, md.total_received, md.distinct_donors, md.first_donation, md.latest_donation
ORDER BY total_received DESC;

-- 2.3 Donations by Government Department
WITH department_ministers AS (
  SELECT DISTINCT
    m.person_id,
    m.organization_id AS dept_id,
    m.role
  FROM datafetch_membership m
  WHERE m.role IS NOT NULL
    AND m.role != ''
    AND m.role NOT LIKE '%Member of Parliament%'
    AND m.role NOT LIKE '%MSP for%'
),
minister_donations AS (
  SELECT
    dm.dept_id,
    dm.person_id,
    d.value,
    d.donor_id
  FROM department_ministers dm
  JOIN datafetch_donation d ON d.recipient_id = dm.person_id
  WHERE d.value > 0
)
SELECT
  dept.id AS department_id,
  MAX(dept.name) AS department_name,
  COUNT(DISTINCT md.person_id) AS ministers_count,
  COUNT(DISTINCT CASE WHEN md.value > 0 THEN md.person_id END) AS ministers_with_donations,
  COUNT(*) AS total_donations,
  SUM(md.value) AS total_received,
  COUNT(DISTINCT md.donor_id) AS distinct_donors,
  ROUND(AVG(md.value), 2) AS avg_donation
FROM department_ministers dm
LEFT JOIN datafetch_actor dept ON dept.id = dm.dept_id
LEFT JOIN minister_donations md ON md.dept_id = dm.dept_id
WHERE dept.name IS NOT NULL
GROUP BY dept.id
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 3: COMBINED MINISTERIAL ACCESS + FUNDING
-- ============================================================================

-- 3.1 Ministers with BOTH meetings AND donations - Full Profile
WITH minister_meetings AS (
    SELECT
        minister_id,
        COUNT(*) as meeting_count,
        COUNT(DISTINCT external_actor_id) as unique_orgs_met,
        COUNT(DISTINCT department_id) as departments_met_in
    FROM datafetch_ministerialmeeting
    GROUP BY minister_id
),
minister_donations AS (
    SELECT
        recipient_id as minister_id,
        COUNT(*) as donation_count,
        SUM(value) as total_received,
        COUNT(DISTINCT donor_id) as unique_donors
    FROM datafetch_donation
    WHERE value > 0
    GROUP BY recipient_id
)
SELECT
    p.name as minister,
    COALESCE(mm.meeting_count, 0) as meetings,
    COALESCE(mm.unique_orgs_met, 0) as orgs_met,
    COALESCE(md.donation_count, 0) as donations,
    COALESCE(md.total_received, 0) as total_received,
    COALESCE(md.unique_donors, 0) as unique_donors,
    CASE
        WHEN mm.meeting_count > 0 AND md.donation_count > 0 THEN 'Meetings + Donations'
        WHEN mm.meeting_count > 0 THEN 'Meetings Only'
        WHEN md.donation_count > 0 THEN 'Donations Only'
    END as influence_channels
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
        a.id,
        a.name,
        COUNT(*) as meeting_count,
        COUNT(DISTINCT mm.minister_id) as ministers_met
    FROM datafetch_ministerialmeeting mm
    JOIN datafetch_actor a ON mm.external_actor_id = a.id
    GROUP BY a.id, a.name
),
donor_orgs AS (
    SELECT
        a.id,
        a.name,
        SUM(d.value) as total_donated,
        COUNT(*) as donation_count,
        COUNT(DISTINCT d.recipient_id) as recipients
    FROM datafetch_donation d
    JOIN datafetch_actor a ON d.donor_id = a.id
    WHERE d.value > 0
    GROUP BY a.id, a.name
)
SELECT
    COALESCE(mo.name, do.name) as organization,
    COALESCE(mo.meeting_count, 0) as meetings,
    COALESCE(mo.ministers_met, 0) as ministers_met,
    COALESCE(do.total_donated, 0) as total_donated,
    COALESCE(do.donation_count, 0) as donations,
    COALESCE(do.recipients, 0) as recipients_funded,
    CASE
        WHEN mo.id IS NOT NULL AND do.id IS NOT NULL THEN 'Full Influence (Meetings + Donations)'
        WHEN mo.id IS NOT NULL THEN 'Access Only (Meetings)'
        WHEN do.id IS NOT NULL THEN 'Funding Only (Donations)'
    END as influence_type
FROM meeting_orgs mo
FULL OUTER JOIN donor_orgs do ON mo.id = do.id
WHERE mo.id IS NOT NULL OR do.id IS NOT NULL
ORDER BY
    CASE WHEN mo.id IS NOT NULL AND do.id IS NOT NULL THEN 0 ELSE 1 END,
    COALESCE(do.total_donated, 0) DESC
LIMIT 100;

-- 3.3 Same Organization Funding AND Meeting a Minister
-- Most direct influence: org donates to minister AND meets with them
WITH minister_donations AS (
    SELECT
        d.donor_id,
        d.recipient_id as minister_id,
        SUM(d.value) as total_donated,
        COUNT(*) as donation_count
    FROM datafetch_donation d
    JOIN datafetch_person p ON p.actor_ptr_id = d.recipient_id
    WHERE d.value > 0
    GROUP BY d.donor_id, d.recipient_id
),
minister_meetings AS (
    SELECT
        mm.external_actor_id as org_id,
        mm.minister_id,
        COUNT(*) as meeting_count
    FROM datafetch_ministerialmeeting mm
    GROUP BY mm.external_actor_id, mm.minister_id
)
SELECT
    org.name as organization,
    minister.name as minister,
    mm.meeting_count as meetings,
    md.total_donated,
    md.donation_count as donations
FROM minister_donations md
JOIN minister_meetings mm ON mm.org_id = md.donor_id AND mm.minister_id = md.minister_id
JOIN datafetch_actor org ON org.id = md.donor_id
JOIN datafetch_actor minister ON minister.id = md.minister_id
ORDER BY md.total_donated DESC
LIMIT 50;


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

-- 4.2 Tech company meetings vs child safety group meetings
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
      WHEN m.role LIKE '%Parliamentary Private Secretary%' OR m.role LIKE '%PPS%' THEN 'PPS - Parliamentary Private Secretary'
      WHEN m.role LIKE '%Whip%' THEN 'Whip'
      WHEN m.role LIKE '%Shadow%' THEN 'Shadow Cabinet/Minister'
      ELSE 'Other Ministerial Role'
    END AS rank_category
  FROM datafetch_membership m
  WHERE m.role IS NOT NULL
    AND m.role != ''
    AND m.role NOT LIKE '%Member of Parliament%'
    AND m.role NOT LIKE '%MSP for%'
),
rank_donations AS (
  SELECT
    mr.rank_category,
    COUNT(DISTINCT mr.person_id) AS ministers_count,
    COUNT(*) AS total_donations,
    SUM(d.value) AS total_received,
    COUNT(DISTINCT d.donor_id) AS distinct_donors
  FROM ministerial_ranks mr
  JOIN datafetch_donation d ON d.recipient_id = mr.person_id
  WHERE d.value > 0
  GROUP BY mr.rank_category
),
rank_meetings AS (
  SELECT
    mr.rank_category,
    COUNT(*) AS total_meetings,
    COUNT(DISTINCT mm.external_actor_id) AS distinct_orgs_met
  FROM ministerial_ranks mr
  JOIN datafetch_ministerialmeeting mm ON mm.minister_id = mr.person_id
  GROUP BY mr.rank_category
)
SELECT
  COALESCE(rd.rank_category, rm.rank_category) as rank_category,
  COALESCE(rd.ministers_count, 0) as ministers_with_donations,
  COALESCE(rd.total_donations, 0) as donations,
  COALESCE(rd.total_received, 0) as total_received,
  COALESCE(rm.total_meetings, 0) as meetings,
  COALESCE(rm.distinct_orgs_met, 0) as unique_orgs_met
FROM rank_donations rd
FULL OUTER JOIN rank_meetings rm ON rm.rank_category = rd.rank_category
ORDER BY total_received DESC;

-- 5.2 Top Donors to Current Ministers
WITH current_ministers AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.role IS NOT NULL
    AND m.role != ''
    AND m.role NOT LIKE '%Member of Parliament%'
    AND m.role NOT LIKE '%MSP for%'
    AND (m.end_date IS NULL OR m.end_date = '' OR m.end_date >= CURRENT_DATE::text)
),
minister_donor_totals AS (
  SELECT
    d.donor_id,
    d.recipient_id,
    SUM(d.value) AS total_donated,
    COUNT(*) AS donation_count
  FROM datafetch_donation d
  JOIN current_ministers cm ON cm.person_id = d.recipient_id
  WHERE d.value > 0
  GROUP BY d.donor_id, d.recipient_id
)
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(COALESCE(donor_org.classification, 'Individual')) AS donor_type,
  COUNT(DISTINCT mdt.recipient_id) AS ministers_funded,
  SUM(mdt.donation_count) AS total_donations,
  SUM(mdt.total_donated) AS total_donated,
  ROUND(AVG(mdt.total_donated), 2) AS avg_per_minister
FROM minister_donor_totals mdt
JOIN datafetch_actor donor ON donor.id = mdt.donor_id
LEFT JOIN datafetch_organization donor_org ON donor_org.actor_ptr_id = donor.id
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 50;


-- ============================================================================
-- SECTION 6: TECH GIANTS PROFILE (Meetings + Funding)
-- ============================================================================

-- 6.1 Tech company influence summary
SELECT
    a.name as company,
    COUNT(DISTINCT mm.id) as meetings,
    COUNT(DISTINCT mm.minister_id) as ministers_met,
    COUNT(DISTINCT mm.department_id) as departments,
    COALESCE((
        SELECT SUM(d.value)
        FROM datafetch_donation d
        WHERE d.donor_id = a.id AND d.value > 0
    ), 0) as total_donated,
    (SELECT COUNT(DISTINCT agency_id)
     FROM datafetch_consultancy c
     WHERE c.client_id = a.id
    ) as lobbying_agencies
FROM datafetch_ministerialmeeting mm
JOIN datafetch_actor a ON mm.external_actor_id = a.id
WHERE LOWER(a.name) IN ('google', 'meta', 'microsoft', 'amazon', 'apple', 'openai', 'x')
GROUP BY a.id, a.name
ORDER BY meetings DESC;

-- 6.2 Which lobbying agencies do tech giants use?
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


-- ============================================================================
-- SECTION 7: TRADE UNIONS - FULL SPECTRUM INFLUENCE
-- ============================================================================

-- 7.1 Trade unions with meetings, lobbying, AND donations
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


-- ============================================================================
-- SECTION 8: SPECIFIC DEPARTMENT DEEP DIVES
-- ============================================================================

-- 8.1 Home Office - Meetings + Funding
WITH home_office_ministers AS (
  SELECT DISTINCT m.person_id, m.role
  FROM datafetch_membership m
  JOIN datafetch_actor dept ON dept.id = m.organization_id
  WHERE dept.name = 'Home Office'
    AND m.role IS NOT NULL
    AND m.role != ''
),
minister_donations AS (
  SELECT
    hom.person_id,
    SUM(d.value) as total_received,
    COUNT(*) as donation_count,
    COUNT(DISTINCT d.donor_id) as distinct_donors
  FROM home_office_ministers hom
  JOIN datafetch_donation d ON d.recipient_id = hom.person_id
  WHERE d.value > 0
  GROUP BY hom.person_id
),
minister_meetings AS (
  SELECT
    hom.person_id,
    COUNT(*) as meeting_count,
    COUNT(DISTINCT mm.external_actor_id) as orgs_met
  FROM home_office_ministers hom
  JOIN datafetch_ministerialmeeting mm ON mm.minister_id = hom.person_id
  GROUP BY hom.person_id
)
SELECT
  person.name AS minister_name,
  MAX(hom.role) AS role,
  COALESCE(md.donation_count, 0) AS donations,
  COALESCE(md.total_received, 0) AS total_received,
  COALESCE(md.distinct_donors, 0) AS donors,
  COALESCE(mmtg.meeting_count, 0) AS meetings,
  COALESCE(mmtg.orgs_met, 0) AS orgs_met
FROM home_office_ministers hom
JOIN datafetch_actor person ON person.id = hom.person_id
LEFT JOIN minister_donations md ON md.person_id = hom.person_id
LEFT JOIN minister_meetings mmtg ON mmtg.person_id = hom.person_id
GROUP BY person.id, person.name, md.donation_count, md.total_received, md.distinct_donors, mmtg.meeting_count, mmtg.orgs_met
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 9: SUMMARY STATISTICS
-- ============================================================================

-- 9.1 Ministerial meetings summary
SELECT
    'Total Meetings' as metric, COUNT(*)::text as value FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Unique External Actors', COUNT(DISTINCT external_actor_id)::text FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Unique Ministers', COUNT(DISTINCT minister_id)::text FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Departments Covered', COUNT(DISTINCT department_id)::text FROM datafetch_ministerialmeeting
UNION ALL
SELECT 'Roundtable Meetings', COUNT(*)::text FROM datafetch_ministerialmeeting WHERE is_roundtable = true
UNION ALL
SELECT 'Total Meeting Attendees', COUNT(*)::text FROM datafetch_meetingattendee;

-- 9.2 Overall Ministerial vs Non-Ministerial Funding
WITH ministers AS (
  SELECT DISTINCT person_id
  FROM datafetch_membership
  WHERE role IS NOT NULL
    AND role != ''
    AND role NOT LIKE '%Member of Parliament%'
    AND role NOT LIKE '%MSP for%'
),
donation_summary AS (
  SELECT
    d.recipient_id,
    CASE WHEN m.person_id IS NOT NULL THEN 'Minister (Current or Former)' ELSE 'Non-Minister MP' END AS recipient_category,
    d.value,
    d.donor_id
  FROM datafetch_donation d
  JOIN datafetch_person p ON p.actor_ptr_id = d.recipient_id
  LEFT JOIN ministers m ON m.person_id = d.recipient_id
  WHERE d.value > 0
)
SELECT
  recipient_category,
  COUNT(DISTINCT recipient_id) AS recipient_count,
  COUNT(*) AS total_donations,
  SUM(value) AS total_received,
  COUNT(DISTINCT donor_id) AS distinct_donors,
  ROUND(AVG(value), 2) AS avg_donation,
  ROUND(SUM(value)::numeric / COUNT(DISTINCT recipient_id), 2) AS avg_per_person
FROM donation_summary
GROUP BY recipient_category
ORDER BY total_received DESC;

-- 9.3 Cross-reference summary: How many orgs use multiple influence channels?
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


-- ============================================================================
-- END OF MINISTERIAL INFLUENCE ANALYSIS
-- ============================================================================
