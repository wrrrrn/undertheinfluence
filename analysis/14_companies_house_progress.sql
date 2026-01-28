-- ============================================================================
-- COMPANIES HOUSE MATCH PROGRESS BY CATEGORY
-- ============================================================================
-- Purpose: Track Companies House enrichment progress across organization categories
-- Usage: Run periodically to monitor enrichment pipeline status
-- Date: 2026-01-23
-- Database: PostgreSQL
-- ============================================================================

-- Categories tracked:
--   lobbying_agency       - PRCA lobbying agencies (from datafetch_consultancy.agency_id)
--   lobbying_client       - Lobbying clients (from datafetch_consultancy.client_id)
--   donor                 - Donation donors (from datafetch_donation.donor_id)
--   meeting_attendee      - All meeting attendees (from datafetch_meetingattendee.actor_id)

-- Status meanings:
--   auto_approved    - High confidence match (>=0.90), automatically linked
--   pending          - Lower confidence match (0.85-0.89), needs manual review
--   rejected         - Match reviewed and rejected
--   not_found        - Searched but no Companies House match found
--   not_applicable   - Not CH registrable (govt, council, university, etc.)
--   remaining        - Not yet processed (no CompaniesHouseMatch record)

-- ============================================================================
-- MAIN PROGRESS QUERY
-- ============================================================================

-- Note: All categories filter to Organizations only (Persons cannot match Companies House)
WITH agency_ids AS (
    -- Agencies are always Organizations (FK constraint)
    SELECT DISTINCT agency_id as org_id
    FROM datafetch_consultancy
),
client_ids AS (
    -- Clients are always Organizations (FK constraint)
    SELECT DISTINCT client_id as org_id
    FROM datafetch_consultancy
),
donor_ids AS (
    -- Filter to only Organizations (excludes individual Person donors)
    SELECT DISTINCT d.donor_id as org_id
    FROM datafetch_donation d
    INNER JOIN datafetch_organization o ON d.donor_id = o.actor_ptr_id
    WHERE d.donor_id IS NOT NULL
),
attendee_ids AS (
    -- Filter to only Organizations (excludes individual Person attendees)
    SELECT DISTINCT ma.actor_id as org_id
    FROM datafetch_meetingattendee ma
    INNER JOIN datafetch_organization o ON ma.actor_id = o.actor_ptr_id
),
matched AS (
    SELECT organization_id as org_id, status
    FROM datafetch_companieshousematch
)
SELECT
    category,
    total,
    auto_approved,
    pending,
    rejected,
    not_found,
    not_applicable,
    matched_total,
    total - matched_total as remaining
FROM (
    SELECT 'lobbying_agency' as category,
        COUNT(*) as total,
        COUNT(CASE WHEN m.status = 'auto_approved' THEN 1 END) as auto_approved,
        COUNT(CASE WHEN m.status = 'pending' THEN 1 END) as pending,
        COUNT(CASE WHEN m.status = 'rejected' THEN 1 END) as rejected,
        COUNT(CASE WHEN m.status = 'not_found' THEN 1 END) as not_found,
        COUNT(CASE WHEN m.status = 'not_applicable' THEN 1 END) as not_applicable,
        COUNT(m.org_id) as matched_total
    FROM agency_ids a
    LEFT JOIN matched m ON a.org_id = m.org_id

    UNION ALL

    SELECT 'lobbying_client',
        COUNT(*),
        COUNT(CASE WHEN m.status = 'auto_approved' THEN 1 END),
        COUNT(CASE WHEN m.status = 'pending' THEN 1 END),
        COUNT(CASE WHEN m.status = 'rejected' THEN 1 END),
        COUNT(CASE WHEN m.status = 'not_found' THEN 1 END),
        COUNT(CASE WHEN m.status = 'not_applicable' THEN 1 END),
        COUNT(m.org_id)
    FROM client_ids c
    LEFT JOIN matched m ON c.org_id = m.org_id

    UNION ALL

    SELECT 'donor',
        COUNT(*),
        COUNT(CASE WHEN m.status = 'auto_approved' THEN 1 END),
        COUNT(CASE WHEN m.status = 'pending' THEN 1 END),
        COUNT(CASE WHEN m.status = 'rejected' THEN 1 END),
        COUNT(CASE WHEN m.status = 'not_found' THEN 1 END),
        COUNT(CASE WHEN m.status = 'not_applicable' THEN 1 END),
        COUNT(m.org_id)
    FROM donor_ids d
    LEFT JOIN matched m ON d.org_id = m.org_id

    UNION ALL

    SELECT 'meeting_attendee',
        COUNT(*),
        COUNT(CASE WHEN m.status = 'auto_approved' THEN 1 END),
        COUNT(CASE WHEN m.status = 'pending' THEN 1 END),
        COUNT(CASE WHEN m.status = 'rejected' THEN 1 END),
        COUNT(CASE WHEN m.status = 'not_found' THEN 1 END),
        COUNT(CASE WHEN m.status = 'not_applicable' THEN 1 END),
        COUNT(m.org_id)
    FROM attendee_ids att
    LEFT JOIN matched m ON att.org_id = m.org_id
) sub
ORDER BY remaining DESC;


-- ============================================================================
-- SUMMARY TOTALS
-- ============================================================================

SELECT
    'TOTAL' as status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM datafetch_companieshousematch), 1) as pct
FROM datafetch_companieshousematch
UNION ALL
SELECT
    status,
    COUNT(*),
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM datafetch_companieshousematch), 1)
FROM datafetch_companieshousematch
GROUP BY status
ORDER BY count DESC;


-- ============================================================================
-- DONOR BREAKDOWN (Orgs vs Persons)
-- ============================================================================
-- Note: Only Organizations can match Companies House. Persons are individuals.

SELECT
    CASE
        WHEN p.actor_ptr_id IS NOT NULL THEN 'Person (not matchable)'
        WHEN o.actor_ptr_id IS NOT NULL THEN 'Organization (matchable)'
        ELSE 'Unknown'
    END as actor_type,
    COUNT(DISTINCT d.donor_id) as count
FROM datafetch_donation d
LEFT JOIN datafetch_person p ON d.donor_id = p.actor_ptr_id
LEFT JOIN datafetch_organization o ON d.donor_id = o.actor_ptr_id
WHERE d.donor_id IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC;


-- ============================================================================
-- MEETING ATTENDEE BREAKDOWN (Orgs vs Persons)
-- ============================================================================
-- Note: Only Organizations can match Companies House. Persons are individuals.

SELECT
    CASE
        WHEN p.actor_ptr_id IS NOT NULL THEN 'Person (not matchable)'
        WHEN o.actor_ptr_id IS NOT NULL THEN 'Organization (matchable)'
        ELSE 'Unknown'
    END as actor_type,
    COUNT(DISTINCT ma.actor_id) as count
FROM datafetch_meetingattendee ma
LEFT JOIN datafetch_person p ON ma.actor_id = p.actor_ptr_id
LEFT JOIN datafetch_organization o ON ma.actor_id = o.actor_ptr_id
GROUP BY 1
ORDER BY 2 DESC;


-- ============================================================================
-- END OF QUERY
-- ============================================================================
