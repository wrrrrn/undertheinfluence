-- ============================================================================
-- MINISTERIAL MEETING DATA QUALITY INVESTIGATION
-- ============================================================================

-- 1. Check for concatenated names in MeetingAttendee
-- Look for common delimiters that suggest multiple organizations were parsed as one
SELECT
    'Concatenated Names' as issue,
    COUNT(*) as affected_records
FROM datafetch_meetingattendee ma
JOIN datafetch_actor a ON ma.actor_id = a.id
WHERE a.name LIKE '% and %'
   OR a.name LIKE '%/%'
   OR a.name LIKE '%,%'
   OR a.name LIKE '%&%';

-- Sample of concatenated names
SELECT
    a.name as raw_name,
    mm.source_url
FROM datafetch_meetingattendee ma
JOIN datafetch_actor a ON ma.actor_id = a.id
JOIN datafetch_ministerialmeeting mm ON ma.meeting_id = mm.id
WHERE (a.name LIKE '% and %' OR a.name LIKE '%/%')
  AND LENGTH(a.name) < 100 -- Focus on likely valid concatenations, not long lists
ORDER BY RANDOM()
LIMIT 20;

-- 2. Check for "Semicolon" actors (likely from previous bad parsing)
SELECT
    'Semicolon Actors' as issue,
    COUNT(*) as count
FROM datafetch_actor
WHERE name LIKE '%;%';

-- 3. Check for duplicates in MinisterialMeeting (same minister, date, raw org string)
-- This shouldn't happen due to constraints, but good to verify
SELECT
    'Duplicate Meetings' as issue,
    COUNT(*) as count
FROM (
    SELECT minister_id, meeting_date, organisation_met_raw, count(*)
    FROM datafetch_ministerialmeeting
    GROUP BY minister_id, meeting_date, organisation_met_raw
    HAVING count(*) > 1
) sub;

-- 4. Check for "Roundtable" attendees that are not marked as such
-- If the name starts with "Roundtable", it might be a description, not an org
SELECT
    'Unmarked Roundtables' as issue,
    COUNT(*) as count
FROM datafetch_meetingattendee ma
JOIN datafetch_actor a ON ma.actor_id = a.id
JOIN datafetch_ministerialmeeting mm ON ma.meeting_id = mm.id
WHERE a.name ILIKE 'Roundtable%'
  AND mm.is_roundtable = false;

-- 5. Check for null sources
SELECT
    'Missing Source URL' as issue,
    COUNT(*) as count
FROM datafetch_ministerialmeeting
WHERE source_url IS NULL OR source_url = '';
