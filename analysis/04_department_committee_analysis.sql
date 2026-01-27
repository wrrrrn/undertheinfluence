-- ============================================================================
-- DEPARTMENT & COMMITTEE ANALYSIS
-- ============================================================================
-- Purpose: Analyze influence across government departments and parliamentary committees
-- Focus: Funding, meetings, and attendees by department; committee member funding
-- Date: 2026-01-26 (Updated with Canonical Resolution)
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
        COUNT(DISTINCT minister_id) as ministers_with_meetings
    FROM datafetch_ministerialmeeting
    GROUP BY department_id
),
dept_attendees AS (
    SELECT
        mm.department_id,
        COUNT(DISTINCT ma.id) as total_attendees,
        COUNT(DISTINCT COALESCE(ma.canonical_actor_id, ma.actor_id)) as unique_attendee_orgs
    FROM datafetch_meetingattendee ma
    JOIN datafetch_ministerialmeeting mm ON mm.id = ma.meeting_id
    GROUP BY mm.department_id
),
dept_ministers AS (
    SELECT
        m.organization_id as dept_id,
        m.person_id
    FROM datafetch_membership m
    WHERE m.role IS NOT NULL AND m.role != ''
),
dept_funding AS (
    SELECT
        dm.dept_id,
        COUNT(*) as donation_count,
        SUM(d.value) as total_received
    FROM dept_ministers dm
    JOIN datafetch_donation d ON COALESCE(d.canonical_recipient_id, d.recipient_id) = dm.person_id
    WHERE d.value > 0
    GROUP BY dm.dept_id
)
SELECT
    dept.name as department,
    COALESCE(dm.meeting_count, 0) as meetings,
    COALESCE(da.total_attendees, 0) as total_attendees,
    COALESCE(da.unique_attendee_orgs, 0) as unique_attendee_orgs,
    COALESCE(df.total_received, 0) as total_minister_funding
FROM datafetch_actor dept
LEFT JOIN dept_meetings dm ON dm.department_id = dept.id
LEFT JOIN dept_attendees da ON da.department_id = dept.id
LEFT JOIN dept_funding df ON df.dept_id = dept.id
WHERE dept.id IN (SELECT DISTINCT department_id FROM datafetch_ministerialmeeting)
ORDER BY meetings DESC;

-- 1.2 Top Organizations by Department Access (Meetings)
SELECT
    dept.name as department,
    COALESCE(canon.name, org.name) as organization,
    COUNT(DISTINCT mm.id) as meetings
FROM datafetch_meetingattendee ma
JOIN datafetch_ministerialmeeting mm ON mm.id = ma.meeting_id
JOIN datafetch_actor dept ON mm.department_id = dept.id
JOIN datafetch_actor org ON ma.actor_id = org.id
LEFT JOIN datafetch_actor canon ON ma.canonical_actor_id = canon.id
GROUP BY dept.name, COALESCE(ma.canonical_actor_id, ma.actor_id), COALESCE(canon.name, org.name)
HAVING COUNT(DISTINCT mm.id) >= 5
ORDER BY dept.name, meetings DESC;


-- ============================================================================
-- SECTION 2: SELECT COMMITTEE OVERVIEW
-- ============================================================================

-- 2.1 Committee Member Funding Summary
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
    SUM(d.value) AS total_received
  FROM committee_members cm
  JOIN datafetch_donation d ON COALESCE(d.canonical_recipient_id, d.recipient_id) = cm.person_id
  WHERE d.value > 0
  GROUP BY cm.committee_id
)
SELECT
  org.name AS committee_name,
  COUNT(DISTINCT cm.person_id) AS total_members,
  COALESCE(md.total_received, 0) AS total_donations_to_members,
  ROUND(COALESCE(md.total_received, 0) / NULLIF(COUNT(DISTINCT cm.person_id), 0), 2) AS avg_per_member
FROM datafetch_actor org
JOIN committee_members cm ON cm.committee_id = org.id
LEFT JOIN member_donations md ON md.committee_id = org.id
GROUP BY org.id, org.name, md.total_received
ORDER BY total_donations_to_members DESC
LIMIT 30;


-- ============================================================================
-- SECTION 3: INDUSTRY-SPECIFIC COMMITTEE ANALYSIS
-- ============================================================================

-- 3.1 Financial Services - Treasury Committee
WITH treasury_committee AS (
  SELECT id FROM datafetch_actor WHERE name LIKE '%Treasury Committee%' LIMIT 1
),
treasury_members AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.organization_id IN (SELECT id FROM treasury_committee)
)
SELECT
  COALESCE(canon.name, donor.name) AS donor_name,
  SUM(d.value) AS total_donated,
  COUNT(DISTINCT COALESCE(d.canonical_recipient_id, d.recipient_id)) AS members_funded
FROM datafetch_donation d
JOIN treasury_members tm ON tm.person_id = COALESCE(d.canonical_recipient_id, d.recipient_id)
JOIN datafetch_actor donor ON d.donor_id = donor.id
LEFT JOIN datafetch_actor canon ON d.canonical_donor_id = canon.id
WHERE d.value > 0
  AND (LOWER(COALESCE(canon.name, donor.name)) LIKE '%bank%' OR LOWER(COALESCE(canon.name, donor.name)) LIKE '%financial%')
GROUP BY COALESCE(d.canonical_donor_id, d.donor_id), COALESCE(canon.name, donor.name)
ORDER BY total_donated DESC;