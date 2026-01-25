-- ============================================================================
-- DEPARTMENT & COMMITTEE ANALYSIS
-- ============================================================================
-- Purpose: Analyze influence across government departments and parliamentary committees
-- Focus: Funding, meetings, and attendees by department; committee member funding
-- Date: 2026-01-22
-- Database: PostgreSQL
-- ============================================================================


-- ============================================================================
-- SECTION 1: DEPARTMENT-LEVEL OVERVIEW
-- ============================================================================

-- 1.1 All Departments - Meetings, Attendees, and Minister Funding
WITH dept_meetings AS (
    SELECT
        department_id,
        COUNT(*) as meeting_count,
        COUNT(DISTINCT minister_id) as ministers_with_meetings,
        COUNT(DISTINCT external_actor_id) as unique_orgs
    FROM datafetch_ministerialmeeting
    GROUP BY department_id
),
dept_attendees AS (
    SELECT
        mm.department_id,
        COUNT(DISTINCT ma.id) as total_attendees,
        COUNT(DISTINCT ma.actor_id) as unique_attendee_orgs
    FROM datafetch_meetingattendee ma
    JOIN datafetch_ministerialmeeting mm ON mm.id = ma.meeting_id
    GROUP BY mm.department_id
),
dept_ministers AS (
    SELECT
        m.organization_id as dept_id,
        m.person_id
    FROM datafetch_membership m
    WHERE m.role IS NOT NULL
      AND m.role != ''
      AND m.role NOT LIKE '%Member of Parliament%'
      AND m.role NOT LIKE '%MSP for%'
),
dept_funding AS (
    SELECT
        dm.dept_id,
        COUNT(*) as donation_count,
        SUM(d.value) as total_received,
        COUNT(DISTINCT d.donor_id) as unique_donors
    FROM dept_ministers dm
    JOIN datafetch_donation d ON d.recipient_id = dm.person_id
    WHERE d.value > 0
    GROUP BY dm.dept_id
)
SELECT
    dept.name as department,
    COALESCE(dm.meeting_count, 0) as meetings,
    COALESCE(da.total_attendees, 0) as total_attendees,
    COALESCE(da.unique_attendee_orgs, 0) as unique_attendee_orgs,
    COALESCE(df.donation_count, 0) as donations_to_ministers,
    COALESCE(df.total_received, 0) as total_minister_funding,
    COALESCE(df.unique_donors, 0) as unique_donors
FROM datafetch_actor dept
WHERE dept.id IN (
    SELECT DISTINCT department_id FROM datafetch_ministerialmeeting
    UNION
    SELECT DISTINCT organization_id FROM datafetch_membership
    WHERE role IS NOT NULL AND role != ''
)
LEFT JOIN dept_meetings dm ON dm.department_id = dept.id
LEFT JOIN dept_attendees da ON da.department_id = dept.id
LEFT JOIN dept_funding df ON df.dept_id = dept.id
WHERE COALESCE(dm.meeting_count, 0) > 0 OR COALESCE(df.donation_count, 0) > 0
ORDER BY COALESCE(dm.meeting_count, 0) DESC;

-- 1.2 Top Organizations by Department Access (Meetings)
-- Which organizations have the most access to each department?
SELECT
    dept.name as department,
    org.name as organization,
    COUNT(*) as meetings,
    COUNT(DISTINCT mm.minister_id) as ministers_met
FROM datafetch_ministerialmeeting mm
JOIN datafetch_actor dept ON mm.department_id = dept.id
JOIN datafetch_actor org ON mm.external_actor_id = org.id
GROUP BY dept.name, org.name
HAVING COUNT(*) >= 3
ORDER BY dept.name, meetings DESC;

-- 1.3 Meeting Attendees by Department
-- Which organizations attend meetings at each department?
SELECT
    dept.name as department,
    org.name as attendee_organization,
    COUNT(*) as attendance_count,
    COUNT(DISTINCT mm.id) as distinct_meetings
FROM datafetch_meetingattendee ma
JOIN datafetch_ministerialmeeting mm ON mm.id = ma.meeting_id
JOIN datafetch_actor dept ON mm.department_id = dept.id
JOIN datafetch_actor org ON ma.actor_id = org.id
GROUP BY dept.name, org.name
HAVING COUNT(*) >= 2
ORDER BY dept.name, attendance_count DESC;

-- 1.4 Department Deep Dive Template (DSIT as example)
-- Detailed breakdown for a specific department
WITH dsit_dept AS (
    SELECT id FROM datafetch_actor
    WHERE name LIKE '%Science, Innovation and Technology%'
       OR name LIKE '%DSIT%'
       OR name LIKE '%Digital%Culture%'
    LIMIT 1
)
SELECT
    org.name as organization,
    COUNT(DISTINCT mm.id) as meetings,
    COUNT(DISTINCT mm.minister_id) as ministers_met,
    (
        SELECT COUNT(*)
        FROM datafetch_meetingattendee ma2
        JOIN datafetch_ministerialmeeting mm2 ON mm2.id = ma2.meeting_id
        WHERE ma2.actor_id = org.id AND mm2.department_id IN (SELECT id FROM dsit_dept)
    ) as attendee_appearances,
    STRING_AGG(DISTINCT SUBSTRING(mm.purpose, 1, 50), '; ') as sample_topics
FROM datafetch_ministerialmeeting mm
JOIN datafetch_actor org ON mm.external_actor_id = org.id
WHERE mm.department_id IN (SELECT id FROM dsit_dept)
GROUP BY org.id, org.name
ORDER BY meetings DESC
LIMIT 30;


-- ============================================================================
-- SECTION 2: SELECT COMMITTEE OVERVIEW
-- ============================================================================

-- 2.1 Committee Membership Statistics
SELECT
  org.id AS committee_id,
  MAX(org.name) AS committee_name,
  COUNT(DISTINCT m.person_id) AS member_count,
  MIN(m.start_date) AS earliest_membership,
  MAX(m.end_date) AS latest_membership_end
FROM datafetch_membership m
JOIN datafetch_actor org ON org.id = m.organization_id
JOIN datafetch_organization org_detail ON org_detail.actor_ptr_id = org.id
WHERE LOWER(org.name) LIKE '%committee%'
GROUP BY org.id
ORDER BY member_count DESC
LIMIT 30;

-- 2.2 All Committees with Member Counts and Donation Totals
WITH committee_members AS (
  SELECT
    m.organization_id AS committee_id,
    m.person_id
  FROM datafetch_membership m
  JOIN datafetch_actor org ON org.id = m.organization_id
  WHERE LOWER(org.name) LIKE '%committee%'
),
member_donations AS (
  SELECT
    cm.committee_id,
    cm.person_id,
    SUM(d.value) AS total_received
  FROM committee_members cm
  JOIN datafetch_donation d ON d.recipient_id = cm.person_id
  WHERE d.value > 0
  GROUP BY cm.committee_id, cm.person_id
)
SELECT
  org.id AS committee_id,
  MAX(org.name) AS committee_name,
  COUNT(DISTINCT cm.person_id) AS total_members,
  COUNT(DISTINCT md.person_id) AS members_with_donations,
  COALESCE(SUM(md.total_received), 0) AS total_donations_to_members,
  ROUND(COALESCE(AVG(md.total_received), 0), 2) AS avg_per_member_with_donations
FROM committee_members cm
LEFT JOIN datafetch_actor org ON org.id = cm.committee_id
LEFT JOIN member_donations md ON md.committee_id = cm.committee_id AND md.person_id = cm.person_id
GROUP BY org.id
ORDER BY total_donations_to_members DESC;


-- ============================================================================
-- SECTION 3: DEPARTMENTAL SELECT COMMITTEES
-- ============================================================================

-- 3.1 Major Departmental Select Committees - Member Funding
WITH major_committees AS (
  SELECT id, name
  FROM datafetch_actor
  WHERE name IN (
    'Home Affairs Committee',
    'Treasury Committee',
    'Foreign Affairs Committee',
    'Defence Committee',
    'Health and Social Care Committee',
    'Education Committee',
    'Environment, Food and Rural Affairs Committee',
    'Business, Energy and Industrial Strategy Committee',
    'Transport Committee',
    'Work and Pensions Committee',
    'Justice Committee',
    'Digital, Culture, Media and Sport Committee'
  )
),
committee_members AS (
  SELECT
    m.organization_id AS committee_id,
    m.person_id,
    m.role,
    m.start_date,
    m.end_date
  FROM datafetch_membership m
  WHERE m.organization_id IN (SELECT id FROM major_committees)
),
member_donations AS (
  SELECT
    cm.committee_id,
    cm.person_id,
    cm.role,
    d.donor_id,
    d.value,
    d.received_date
  FROM committee_members cm
  JOIN datafetch_donation d ON d.recipient_id = cm.person_id
  WHERE d.value > 0
)
SELECT
  committee.name AS committee_name,
  person.id AS person_id,
  MAX(person.name) AS person_name,
  MAX(md.role) AS committee_role,
  COUNT(*) AS donation_count,
  SUM(md.value) AS total_received,
  COUNT(DISTINCT md.donor_id) AS distinct_donors,
  ROUND(AVG(md.value), 2) AS avg_donation
FROM member_donations md
JOIN datafetch_actor committee ON committee.id = md.committee_id
JOIN datafetch_actor person ON person.id = md.person_id
GROUP BY committee.name, person.id
ORDER BY committee.name, total_received DESC;

-- 3.2 Committee Chairs - Funding Analysis
WITH committee_chairs AS (
  SELECT
    m.organization_id AS committee_id,
    m.person_id,
    m.start_date,
    m.end_date
  FROM datafetch_membership m
  WHERE LOWER(m.role) LIKE '%chair%'
    AND m.organization_id IN (
      SELECT id FROM datafetch_actor WHERE LOWER(name) LIKE '%committee%'
    )
),
chair_donations AS (
  SELECT
    cc.committee_id,
    cc.person_id,
    d.donor_id,
    d.value,
    d.received_date
  FROM committee_chairs cc
  JOIN datafetch_donation d ON d.recipient_id = cc.person_id
  WHERE d.value > 0
)
SELECT
  committee.name AS committee_name,
  person.id AS person_id,
  MAX(person.name) AS chair_name,
  COUNT(*) AS donation_count,
  SUM(cd.value) AS total_received,
  COUNT(DISTINCT cd.donor_id) AS distinct_donors,
  ROUND(AVG(cd.value), 2) AS avg_donation
FROM chair_donations cd
JOIN datafetch_actor committee ON committee.id = cd.committee_id
JOIN datafetch_actor person ON person.id = cd.person_id
GROUP BY committee.name, person.id
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 4: INDUSTRY-SPECIFIC COMMITTEE ANALYSIS
-- ============================================================================

-- 4.1 Financial Services - Treasury Committee
WITH treasury_committee AS (
  SELECT id FROM datafetch_actor
  WHERE name LIKE '%Treasury Committee%'
  LIMIT 1
),
treasury_members AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.organization_id IN (SELECT id FROM treasury_committee)
),
financial_donors AS (
  SELECT d.*
  FROM datafetch_donation d
  JOIN datafetch_organization org ON org.actor_ptr_id = d.donor_id
  WHERE d.value > 0
    AND (
      LOWER(org.classification) LIKE '%bank%'
      OR LOWER(org.name) LIKE '%bank%'
      OR LOWER(org.name) LIKE '%financial%'
      OR LOWER(org.name) LIKE '%investment%'
      OR LOWER(org.name) LIKE '%insurance%'
    )
)
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS donor_type,
  recipient.id AS recipient_id,
  MAX(recipient.name) AS recipient_name,
  COUNT(*) AS donation_count,
  SUM(fd.value) AS total_donated,
  ROUND(AVG(fd.value), 2) AS avg_donation
FROM financial_donors fd
JOIN treasury_members tm ON tm.person_id = fd.recipient_id
JOIN datafetch_actor donor ON donor.id = fd.donor_id
JOIN datafetch_actor recipient ON recipient.id = fd.recipient_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
GROUP BY donor.id, recipient.id
ORDER BY total_donated DESC;

-- 4.2 Agriculture - DEFRA Committee
WITH defra_committee AS (
  SELECT id FROM datafetch_actor
  WHERE name LIKE '%Environment, Food and Rural Affairs Committee%'
  LIMIT 1
),
defra_members AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.organization_id IN (SELECT id FROM defra_committee)
),
agriculture_donors AS (
  SELECT d.*
  FROM datafetch_donation d
  JOIN datafetch_organization org ON org.actor_ptr_id = d.donor_id
  WHERE d.value > 0
    AND (
      LOWER(org.name) LIKE '%farm%'
      OR LOWER(org.name) LIKE '%agricult%'
      OR LOWER(org.name) LIKE '%rural%'
      OR LOWER(org.name) LIKE '%food%'
    )
)
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS donor_type,
  recipient.id AS recipient_id,
  MAX(recipient.name) AS recipient_name,
  COUNT(*) AS donation_count,
  SUM(ad.value) AS total_donated,
  ROUND(AVG(ad.value), 2) AS avg_donation
FROM agriculture_donors ad
JOIN defra_members dm ON dm.person_id = ad.recipient_id
JOIN datafetch_actor donor ON donor.id = ad.donor_id
JOIN datafetch_actor recipient ON recipient.id = ad.recipient_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
GROUP BY donor.id, recipient.id
ORDER BY total_donated DESC;


-- ============================================================================
-- SECTION 5: COMMITTEE MEMBER VS NON-MEMBER COMPARISON
-- ============================================================================

-- 5.1 Do Committee Members Receive More Funding?
WITH committee_members AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.organization_id IN (
    SELECT id FROM datafetch_actor WHERE LOWER(name) LIKE '%committee%'
  )
),
all_mps AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.role LIKE '%Member of Parliament%'
),
mp_donations AS (
  SELECT
    amp.person_id,
    CASE WHEN cm.person_id IS NOT NULL THEN 'Committee Member' ELSE 'Non-Committee MP' END AS mp_category,
    d.value,
    d.donor_id
  FROM all_mps amp
  LEFT JOIN committee_members cm ON cm.person_id = amp.person_id
  JOIN datafetch_donation d ON d.recipient_id = amp.person_id
  WHERE d.value > 0
)
SELECT
  mp_category,
  COUNT(DISTINCT person_id) AS mp_count,
  COUNT(*) AS total_donations,
  SUM(value) AS total_received,
  COUNT(DISTINCT donor_id) AS distinct_donors,
  ROUND(AVG(value), 2) AS avg_donation,
  ROUND(SUM(value)::numeric / COUNT(DISTINCT person_id), 2) AS avg_per_mp
FROM mp_donations
GROUP BY mp_category
ORDER BY total_received DESC;

-- 5.2 Top Donors to Committee Members
WITH committee_members AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.organization_id IN (
    SELECT id FROM datafetch_actor WHERE LOWER(name) LIKE '%committee%'
  )
),
committee_member_donors AS (
  SELECT
    d.donor_id,
    d.recipient_id,
    SUM(d.value) AS total_donated,
    COUNT(*) AS donation_count
  FROM datafetch_donation d
  JOIN committee_members cm ON cm.person_id = d.recipient_id
  WHERE d.value > 0
  GROUP BY d.donor_id, d.recipient_id
)
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(COALESCE(org.classification, 'Individual')) AS donor_type,
  COUNT(DISTINCT cmd.recipient_id) AS committee_members_funded,
  SUM(cmd.donation_count) AS total_donations,
  SUM(cmd.total_donated) AS total_donated,
  ROUND(AVG(cmd.total_donated), 2) AS avg_per_member
FROM committee_member_donors cmd
JOIN datafetch_actor donor ON donor.id = cmd.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 50;


-- ============================================================================
-- SECTION 6: CROSS-COMMITTEE & MINISTERIAL ANALYSIS
-- ============================================================================

-- 6.1 MPs Serving on Multiple Committees - Funding Analysis
WITH mp_committee_counts AS (
  SELECT
    m.person_id,
    COUNT(DISTINCT m.organization_id) AS committee_count
  FROM datafetch_membership m
  WHERE m.organization_id IN (
    SELECT id FROM datafetch_actor WHERE LOWER(name) LIKE '%committee%'
  )
  GROUP BY m.person_id
),
mp_donations AS (
  SELECT
    mcc.person_id,
    mcc.committee_count,
    SUM(d.value) AS total_received,
    COUNT(*) AS donation_count,
    COUNT(DISTINCT d.donor_id) AS distinct_donors
  FROM mp_committee_counts mcc
  JOIN datafetch_donation d ON d.recipient_id = mcc.person_id
  WHERE d.value > 0
  GROUP BY mcc.person_id, mcc.committee_count
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  md.committee_count,
  md.donation_count,
  md.total_received,
  md.distinct_donors,
  ROUND(md.total_received / md.committee_count, 2) AS avg_per_committee,
  ROUND(md.total_received::numeric / md.donation_count, 2) AS avg_donation
FROM mp_donations md
JOIN datafetch_actor person ON person.id = md.person_id
WHERE md.committee_count > 1
GROUP BY person.id, md.committee_count, md.donation_count, md.total_received, md.distinct_donors
ORDER BY total_received DESC
LIMIT 30;

-- 6.2 Committee Overlap with Ministerial Roles
WITH committee_members AS (
  SELECT DISTINCT
    m.person_id,
    m.organization_id AS committee_id
  FROM datafetch_membership m
  WHERE m.organization_id IN (
    SELECT id FROM datafetch_actor WHERE LOWER(name) LIKE '%committee%'
  )
),
ministers AS (
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
dual_role_mps AS (
  SELECT DISTINCT cm.person_id
  FROM committee_members cm
  INNER JOIN ministers m ON m.person_id = cm.person_id
),
dual_role_donations AS (
  SELECT
    drm.person_id,
    SUM(d.value) AS total_received,
    COUNT(*) AS donation_count,
    COUNT(DISTINCT d.donor_id) AS distinct_donors
  FROM dual_role_mps drm
  JOIN datafetch_donation d ON d.recipient_id = drm.person_id
  WHERE d.value > 0
  GROUP BY drm.person_id
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  STRING_AGG(DISTINCT committee.name, ', ') AS committees,
  STRING_AGG(DISTINCT min.role, ', ') AS ministerial_roles,
  drd.donation_count,
  drd.total_received,
  drd.distinct_donors,
  ROUND(drd.total_received::numeric / drd.donation_count, 2) AS avg_donation
FROM dual_role_donations drd
JOIN datafetch_actor person ON person.id = drd.person_id
LEFT JOIN committee_members cm ON cm.person_id = drd.person_id
LEFT JOIN datafetch_actor committee ON committee.id = cm.committee_id
LEFT JOIN ministers min ON min.person_id = drd.person_id
GROUP BY person.id, drd.donation_count, drd.total_received, drd.distinct_donors
ORDER BY total_received DESC
LIMIT 30;


-- ============================================================================
-- SECTION 7: SUMMARY STATISTICS
-- ============================================================================

-- 7.1 Overall Committee Funding Summary
WITH committee_stats AS (
  SELECT
    COUNT(DISTINCT org.id) AS total_committees,
    COUNT(DISTINCT m.person_id) AS total_committee_members
  FROM datafetch_membership m
  JOIN datafetch_actor org ON org.id = m.organization_id
  WHERE LOWER(org.name) LIKE '%committee%'
),
committee_member_donations AS (
  SELECT
    cm.person_id,
    SUM(d.value) AS total_received
  FROM datafetch_membership cm
  JOIN datafetch_donation d ON d.recipient_id = cm.person_id
  WHERE cm.organization_id IN (
    SELECT id FROM datafetch_actor WHERE LOWER(name) LIKE '%committee%'
  )
  AND d.value > 0
  GROUP BY cm.person_id
)
SELECT
  'Total Committees' AS metric,
  (SELECT total_committees FROM committee_stats)::text AS value
UNION ALL
SELECT
  'Total Committee Members',
  (SELECT total_committee_members FROM committee_stats)::text
UNION ALL
SELECT
  'Members with Donations',
  COUNT(DISTINCT person_id)::text
FROM committee_member_donations
UNION ALL
SELECT
  'Total Donations to Committee Members',
  SUM(total_received)::text
FROM committee_member_donations
UNION ALL
SELECT
  'Average per Committee Member',
  ROUND(AVG(total_received), 2)::text
FROM committee_member_donations;

-- 7.2 Department Meeting Summary
SELECT
    'Total Departments with Meetings' as metric,
    COUNT(DISTINCT department_id)::text as value
FROM datafetch_ministerialmeeting
UNION ALL
SELECT
    'Total Meetings',
    COUNT(*)::text
FROM datafetch_ministerialmeeting
UNION ALL
SELECT
    'Total Meeting Attendees',
    COUNT(*)::text
FROM datafetch_meetingattendee
UNION ALL
SELECT
    'Unique Attendee Organizations',
    COUNT(DISTINCT actor_id)::text
FROM datafetch_meetingattendee;


-- ============================================================================
-- END OF DEPARTMENT & COMMITTEE ANALYSIS
-- ============================================================================
