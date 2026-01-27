-- ============================================================================
-- SECTOR & INDUSTRY INFLUENCE ANALYSIS
-- ============================================================================
-- Purpose: Analyze influence by industry sector - donations, meetings, and lobbying
-- Focus: Agriculture, Finance, Energy, Technology, Healthcare, etc.
-- Date: 2026-01-26 (Updated with Canonical Resolution)
-- Database: PostgreSQL
-- ============================================================================


-- ============================================================================
-- SECTION 1: SECTOR IDENTIFICATION
-- ============================================================================

-- 1.1 Sector Breakdown Overview
WITH classified_actors AS (
  SELECT
    COALESCE(canonical.id, a.id) as actor_id,
    COALESCE(canonical.name, a.name) as name,
    CASE
      WHEN LOWER(COALESCE(canonical.name, a.name)) LIKE '%bank%' OR LOWER(COALESCE(canonical.name, a.name)) LIKE '%financial%' THEN 'Financial Services'
      WHEN LOWER(COALESCE(canonical.name, a.name)) LIKE '%energy%' OR LOWER(COALESCE(canonical.name, a.name)) LIKE '%power%' OR LOWER(COALESCE(canonical.name, a.name)) LIKE '%oil%' THEN 'Energy & Utilities'
      WHEN LOWER(COALESCE(canonical.name, a.name)) IN ('google', 'meta', 'microsoft', 'amazon', 'apple') OR LOWER(COALESCE(canonical.name, a.name)) LIKE '%tech%' THEN 'Technology'
      WHEN LOWER(COALESCE(canonical.name, a.name)) LIKE '%health%' OR LOWER(COALESCE(canonical.name, a.name)) LIKE '%pharma%' THEN 'Healthcare'
      WHEN LOWER(COALESCE(canonical.name, a.name)) LIKE '%defence%' OR LOWER(COALESCE(canonical.name, a.name)) LIKE '%arms%' THEN 'Defence'
      WHEN o.classification ILIKE '%union%' THEN 'Trade Unions'
      ELSE 'Other'
    END AS sector
  FROM datafetch_actor a
  LEFT JOIN datafetch_actor canonical ON a.id = canonical.id -- Self-join placeholder if canonical logic differs
  LEFT JOIN datafetch_organization o ON o.actor_ptr_id = a.id
)
SELECT
  sector,
  COUNT(*) as actor_count
FROM classified_actors
GROUP BY sector
ORDER BY actor_count DESC;


-- ============================================================================
-- SECTION 2: SECTOR FUNDING ANALYSIS
-- ============================================================================

-- 2.1 Donations by Sector
WITH donor_sectors AS (
  SELECT
    COALESCE(d.canonical_donor_id, d.donor_id) as donor_id,
    CASE
      WHEN LOWER(donor.name) LIKE '%bank%' OR LOWER(donor.name) LIKE '%financial%' THEN 'Financial Services'
      WHEN LOWER(donor.name) LIKE '%energy%' THEN 'Energy'
      WHEN LOWER(donor.name) LIKE '%tech%' THEN 'Technology'
      WHEN LOWER(donor.name) LIKE '%health%' THEN 'Healthcare'
      WHEN org.classification ILIKE '%union%' THEN 'Trade Unions'
      ELSE 'Other'
    END AS sector,
    d.value
  FROM datafetch_donation d
  JOIN datafetch_actor donor ON COALESCE(d.canonical_donor_id, d.donor_id) = donor.id
  LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
  WHERE d.value > 0
)
SELECT
  sector,
  COUNT(DISTINCT donor_id) as unique_donors,
  SUM(value) as total_donated
FROM donor_sectors
GROUP BY sector
ORDER BY total_donated DESC;


-- ============================================================================
-- SECTION 3: SECTOR MEETING ANALYSIS
-- ============================================================================

-- 3.1 Meetings by Sector
WITH attendee_sectors AS (
  SELECT
    COALESCE(ma.canonical_actor_id, ma.actor_id) as actor_id,
    CASE
      WHEN LOWER(a.name) LIKE '%bank%' OR LOWER(a.name) LIKE '%financial%' THEN 'Financial Services'
      WHEN LOWER(a.name) LIKE '%energy%' THEN 'Energy'
      WHEN LOWER(a.name) IN ('google', 'meta', 'microsoft', 'amazon') THEN 'Technology'
      WHEN LOWER(a.name) LIKE '%health%' THEN 'Healthcare'
      WHEN o.classification ILIKE '%union%' THEN 'Trade Unions'
      ELSE 'Other'
    END AS sector,
    ma.meeting_id
  FROM datafetch_meetingattendee ma
  JOIN datafetch_actor a ON COALESCE(ma.canonical_actor_id, ma.actor_id) = a.id
  LEFT JOIN datafetch_organization o ON o.actor_ptr_id = a.id
)
SELECT
  sector,
  COUNT(DISTINCT meeting_id) as meetings,
  COUNT(DISTINCT actor_id) as unique_orgs
FROM attendee_sectors
GROUP BY sector
ORDER BY meetings DESC;


-- ============================================================================
-- SECTION 4: COMBINED INFLUENCE (Donations + Meetings)
-- ============================================================================

-- 4.1 Top Organizations by Sector with BOTH Donations and Meetings
WITH org_stats AS (
    SELECT
        COALESCE(ma.canonical_actor_id, ma.actor_id) as org_id,
        COUNT(DISTINCT ma.meeting_id) as meetings
    FROM datafetch_meetingattendee ma
    GROUP BY COALESCE(ma.canonical_actor_id, ma.actor_id)
),
donor_stats AS (
    SELECT
        COALESCE(canonical_donor_id, donor_id) as org_id,
        SUM(value) as total_donated
    FROM datafetch_donation
    WHERE value > 0
    GROUP BY COALESCE(canonical_donor_id, donor_id)
)
SELECT
    a.name as organization,
    CASE
        WHEN LOWER(a.name) LIKE '%bank%' THEN 'Financial Services'
        WHEN LOWER(a.name) LIKE '%energy%' THEN 'Energy'
        WHEN LOWER(a.name) LIKE '%union%' THEN 'Trade Unions'
        ELSE 'Other'
    END as sector,
    COALESCE(ds.total_donated, 0) as total_donated,
    COALESCE(os.meetings, 0) as meetings
FROM datafetch_actor a
LEFT JOIN org_stats os ON os.org_id = a.id
LEFT JOIN donor_stats ds ON ds.org_id = a.id
WHERE COALESCE(ds.total_donated, 0) > 0 AND COALESCE(os.meetings, 0) > 0
ORDER BY total_donated DESC
LIMIT 50;