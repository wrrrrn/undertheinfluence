-- ==============================================================================
-- 10. MP LOBBYING CONNECTIONS
-- ==============================================================================
-- Demonstrates how MPs connect to lobbying activities through organizational
-- memberships. Path: MP → Membership → Organization → Consultancy (as client)
-- Date: 2026-01-26 (Updated with Canonical Resolution)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 10.1 AGGREGATED VIEW: MPs by Organization with Lobbying Activity
-- ------------------------------------------------------------------------------
SELECT
    COALESCE(client_canon.name, org.name) AS organization_name,
    org.classification AS org_type,
    COUNT(DISTINCT mp.id) AS mp_member_count,
    COUNT(DISTINCT c.id) AS consultancy_count,
    COUNT(DISTINCT COALESCE(c.canonical_agency_id, c.agency_id)) AS unique_agencies_hired,
    STRING_AGG(DISTINCT mp.name, ', ' ORDER BY mp.name) FILTER (WHERE mp.name IS NOT NULL) AS mp_members_sample
FROM datafetch_organization org
JOIN datafetch_membership m ON m.organization_id = org.actor_ptr_id
JOIN datafetch_person mp ON m.person_id = mp.actor_ptr_id
JOIN datafetch_consultancy c ON c.client_id = org.actor_ptr_id
LEFT JOIN datafetch_actor client_canon ON c.canonical_client_id = client_canon.id
WHERE EXISTS (
    SELECT 1 FROM datafetch_membership hc_membership
    JOIN datafetch_organization hc ON hc_membership.organization_id = hc.actor_ptr_id
    WHERE hc_membership.person_id = mp.actor_ptr_id
      AND hc.name = 'House of Commons'
)
GROUP BY COALESCE(client_canon.name, org.name), org.classification
ORDER BY mp_member_count DESC, consultancy_count DESC
LIMIT 30;


-- ------------------------------------------------------------------------------
-- 10.2 TIMELINE VIEW: When MPs Join Orgs That Hire Lobbyists
-- ------------------------------------------------------------------------------
SELECT
    mp.name AS mp_name,
    org.name AS organization_name,
    m.start_date AS mp_joined_org,
    c.start_date AS lobbying_started,
    agency.name AS lobbying_agency,
    CASE
        WHEN m.start_date < c.start_date THEN 'MP joined before lobbying'
        ELSE 'MP joined after lobbying started'
    END AS temporal_relationship
FROM datafetch_person mp
JOIN datafetch_membership m ON m.person_id = mp.actor_ptr_id
JOIN datafetch_organization org ON m.organization_id = org.actor_ptr_id
JOIN datafetch_consultancy c ON c.client_id = org.actor_ptr_id
JOIN datafetch_actor agency ON COALESCE(c.canonical_agency_id, c.agency_id) = agency.id
WHERE EXISTS (
    SELECT 1 FROM datafetch_membership hc_m
    JOIN datafetch_organization hc ON hc_m.organization_id = hc.actor_ptr_id
    WHERE hc_m.person_id = mp.actor_ptr_id AND hc.name = 'House of Commons'
)
ORDER BY mp.name, m.start_date DESC
LIMIT 50;