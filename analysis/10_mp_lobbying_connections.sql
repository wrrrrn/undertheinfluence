-- ==============================================================================
-- 10. MP LOBBYING CONNECTIONS
-- ==============================================================================
-- Demonstrates how MPs connect to lobbying activities through organizational
-- memberships. Path: MP → Membership → Organization → Consultancy (as client)
--
-- Key Insight: MPs don't directly hire lobbyists, but their affiliated
-- organizations do. This reveals indirect influence channels.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 10.1 FULL CONNECTION PATH: MPs to Lobbying Agencies
-- ------------------------------------------------------------------------------
-- Shows the complete chain: MP → Member of Org → Org hires Lobbyist
-- Limited to 50 rows for sample

SELECT
    -- MP Details
    mp.id AS mp_id,
    mp.name AS mp_name,
    mp.given_name || ' ' || mp.family_name AS mp_full_name,

    -- Membership Details
    m.role AS membership_role,
    m.label AS membership_label,
    m.start_date AS member_since,
    m.end_date AS member_until,

    -- Organization Details
    org.id AS organization_id,
    org.name AS organization_name,
    org.classification AS org_type,

    -- Consultancy Details
    c.id AS consultancy_id,
    c.start_date AS consultancy_start,
    c.end_date AS consultancy_end,

    -- Lobbying Agency Details
    agency.id AS agency_id,
    agency.name AS lobbying_agency_name,
    agency.classification AS agency_type

FROM datafetch_person mp

-- Step 1: MP → Membership
INNER JOIN datafetch_membership m
    ON m.person_id = mp.id

-- Step 2: Membership → Organization
INNER JOIN datafetch_organization org
    ON m.organization_id = org.id

-- Step 3: Organization → Consultancy (as client)
INNER JOIN datafetch_consultancy c
    ON c.client_id = org.id

-- Step 4: Consultancy → Lobbying Agency
INNER JOIN datafetch_organization agency
    ON c.agency_id = agency.id

-- Filter to actual MPs (members of House of Commons)
WHERE EXISTS (
    SELECT 1 FROM datafetch_membership hc_membership
    INNER JOIN datafetch_organization hc
        ON hc_membership.organization_id = hc.id
    WHERE hc_membership.person_id = mp.id
        AND hc.name = 'House of Commons'
)

-- Order by MP name and consultancy date
ORDER BY mp.name, c.start_date DESC

LIMIT 50;


-- ------------------------------------------------------------------------------
-- 10.2 AGGREGATED VIEW: MPs by Organization with Lobbying Activity
-- ------------------------------------------------------------------------------
-- Shows which organizations have both MP members AND lobbying consultancies

SELECT
    org.name AS organization_name,
    org.classification AS org_type,

    -- Count of MP members
    COUNT(DISTINCT mp.id) AS mp_member_count,

    -- Count of lobbying consultancies
    COUNT(DISTINCT c.id) AS consultancy_count,

    -- Count of unique lobbying agencies hired
    COUNT(DISTINCT c.agency_id) AS unique_agencies_hired,

    -- List some example MPs (limited to 3)
    STRING_AGG(
        DISTINCT mp.name,
        ', '
        ORDER BY mp.name
    ) FILTER (WHERE row_num <= 3) AS sample_mp_members,

    -- List some example lobbying agencies (limited to 3)
    STRING_AGG(
        DISTINCT agency.name,
        ', '
        ORDER BY agency.name
    ) FILTER (WHERE agency_row_num <= 3) AS sample_agencies_hired

FROM datafetch_organization org

-- Find MP memberships
INNER JOIN datafetch_membership m
    ON m.organization_id = org.id

INNER JOIN datafetch_person mp
    ON m.person_id = mp.id

-- Find consultancies where org is the client
INNER JOIN datafetch_consultancy c
    ON c.client_id = org.id

INNER JOIN datafetch_organization agency
    ON c.agency_id = agency.id

-- Add row numbers for filtering
LEFT JOIN LATERAL (
    SELECT ROW_NUMBER() OVER (PARTITION BY org.id ORDER BY mp.name) as row_num
    FROM datafetch_membership m2
    WHERE m2.organization_id = org.id
) mp_rn ON true

LEFT JOIN LATERAL (
    SELECT ROW_NUMBER() OVER (PARTITION BY org.id ORDER BY agency.name) as agency_row_num
    FROM datafetch_consultancy c2
    WHERE c2.client_id = org.id
) agency_rn ON true

-- Filter to actual MPs
WHERE EXISTS (
    SELECT 1 FROM datafetch_membership hc_membership
    INNER JOIN datafetch_organization hc
        ON hc_membership.organization_id = hc.id
    WHERE hc_membership.person_id = mp.id
        AND hc.name = 'House of Commons'
)

GROUP BY org.id, org.name, org.classification

-- Show most active orgs first
ORDER BY mp_member_count DESC, consultancy_count DESC

LIMIT 30;


-- ------------------------------------------------------------------------------
-- 10.3 SPECIFIC EXAMPLE: Trade Union Lobbying with MP Members
-- ------------------------------------------------------------------------------
-- Focuses on trade unions, which commonly have both MP members and lobbying

SELECT
    org.name AS union_name,

    -- MP membership stats
    COUNT(DISTINCT mp.id) AS current_mp_members,
    STRING_AGG(DISTINCT mp.name, ', ' ORDER BY mp.name) AS mp_names,

    -- Lobbying stats
    COUNT(DISTINCT c.id) AS total_consultancies,
    COUNT(DISTINCT c.agency_id) AS unique_agencies,
    STRING_AGG(DISTINCT agency.name, ', ' ORDER BY agency.name) AS agencies_hired,

    -- Date ranges
    MIN(c.start_date) AS earliest_consultancy,
    MAX(c.end_date) AS latest_consultancy

FROM datafetch_organization org

-- MP memberships
INNER JOIN datafetch_membership m
    ON m.organization_id = org.id
    AND (m.end_date IS NULL OR m.end_date >= '2020-01-01')  -- Current/recent

INNER JOIN datafetch_person mp
    ON m.person_id = mp.id

-- Consultancies
INNER JOIN datafetch_consultancy c
    ON c.client_id = org.id

INNER JOIN datafetch_organization agency
    ON c.agency_id = agency.id

-- Filter to trade unions with MP members
WHERE org.classification LIKE '%union%'
    OR org.classification LIKE '%Trade union%'
    OR org.name LIKE '%Union%'

    -- Verify they are actual MPs
    AND EXISTS (
        SELECT 1 FROM datafetch_membership hc_membership
        INNER JOIN datafetch_organization hc
            ON hc_membership.organization_id = hc.id
        WHERE hc_membership.person_id = mp.id
            AND hc.name = 'House of Commons'
            AND (hc_membership.end_date IS NULL OR hc_membership.end_date >= '2020-01-01')
    )

GROUP BY org.id, org.name

ORDER BY current_mp_members DESC, total_consultancies DESC;


-- ------------------------------------------------------------------------------
-- 10.4 TIMELINE VIEW: When MPs Join Orgs That Hire Lobbyists
-- ------------------------------------------------------------------------------
-- Analyzes temporal overlap: Did the MP join before or after lobbying started?

SELECT
    mp.name AS mp_name,
    org.name AS organization_name,

    -- Membership timeline
    m.start_date AS mp_joined_org,
    m.end_date AS mp_left_org,

    -- Consultancy timeline
    c.start_date AS lobbying_started,
    c.end_date AS lobbying_ended,
    agency.name AS lobbying_agency,

    -- Temporal relationship
    CASE
        WHEN m.start_date < c.start_date THEN 'MP joined before lobbying'
        WHEN m.start_date > c.start_date THEN 'MP joined after lobbying started'
        ELSE 'MP joined same time as lobbying'
    END AS temporal_relationship,

    -- Overlap analysis
    CASE
        WHEN m.end_date IS NULL OR c.end_date IS NULL THEN 'Potentially overlapping'
        WHEN m.start_date <= c.end_date AND (m.end_date IS NULL OR m.end_date >= c.start_date)
            THEN 'Overlapping membership and lobbying'
        ELSE 'No overlap'
    END AS overlap_status

FROM datafetch_person mp

INNER JOIN datafetch_membership m
    ON m.person_id = mp.id

INNER JOIN datafetch_organization org
    ON m.organization_id = org.id

INNER JOIN datafetch_consultancy c
    ON c.client_id = org.id

INNER JOIN datafetch_organization agency
    ON c.agency_id = agency.id

-- Filter to MPs
WHERE EXISTS (
    SELECT 1 FROM datafetch_membership hc_membership
    INNER JOIN datafetch_organization hc
        ON hc_membership.organization_id = hc.id
    WHERE hc_membership.person_id = mp.id
        AND hc.name = 'House of Commons'
)

ORDER BY mp.name, m.start_date, c.start_date

LIMIT 50;


-- ------------------------------------------------------------------------------
-- 10.5 INFLUENCE SCORE: MPs Connected to Multi-Lobbying Organizations
-- ------------------------------------------------------------------------------
-- Identifies MPs affiliated with organizations that hire many lobbyists
-- (potential for strong indirect lobbying influence)

WITH mp_org_lobbying AS (
    SELECT
        mp.id AS mp_id,
        mp.name AS mp_name,
        org.id AS org_id,
        org.name AS org_name,
        COUNT(DISTINCT c.id) AS consultancies_count,
        COUNT(DISTINCT c.agency_id) AS unique_agencies
    FROM datafetch_person mp
    INNER JOIN datafetch_membership m ON m.person_id = mp.id
    INNER JOIN datafetch_organization org ON m.organization_id = org.id
    INNER JOIN datafetch_consultancy c ON c.client_id = org.id
    WHERE EXISTS (
        SELECT 1 FROM datafetch_membership hc_m
        INNER JOIN datafetch_organization hc ON hc_m.organization_id = hc.id
        WHERE hc_m.person_id = mp.id AND hc.name = 'House of Commons'
    )
    GROUP BY mp.id, mp.name, org.id, org.name
)

SELECT
    mp_name,
    COUNT(DISTINCT org_id) AS orgs_with_lobbying,
    SUM(consultancies_count) AS total_consultancies,
    SUM(unique_agencies) AS total_unique_agencies,
    STRING_AGG(
        org_name || ' (' || consultancies_count || ' consultancies)',
        ', '
        ORDER BY consultancies_count DESC
    ) AS organizations

FROM mp_org_lobbying

GROUP BY mp_id, mp_name

HAVING SUM(consultancies_count) >= 3  -- MPs connected to 3+ consultancies

ORDER BY total_consultancies DESC, orgs_with_lobbying DESC

LIMIT 30;


-- ------------------------------------------------------------------------------
-- 10.6 DUAL INFLUENCE: MPs in Orgs That Both Lobby AND Donate
-- ------------------------------------------------------------------------------
-- Shows MPs affiliated with organizations using both lobbying and donation channels

SELECT
    mp.name AS mp_name,
    org.name AS organization_name,
    org.classification AS org_type,

    -- Lobbying activity
    COUNT(DISTINCT c.id) AS consultancy_count,
    STRING_AGG(DISTINCT agency.name, ', ' ORDER BY agency.name) AS agencies_hired,

    -- Donation activity
    COUNT(DISTINCT d.id) AS donation_count,
    COALESCE(SUM(d.value), 0) AS total_donated,

    -- MP membership period
    MIN(m.start_date) AS mp_joined,
    MAX(m.end_date) AS mp_left

FROM datafetch_person mp

INNER JOIN datafetch_membership m
    ON m.person_id = mp.id

INNER JOIN datafetch_organization org
    ON m.organization_id = org.id

-- Consultancies (org as client)
LEFT JOIN datafetch_consultancy c
    ON c.client_id = org.id

LEFT JOIN datafetch_organization agency
    ON c.agency_id = agency.id

-- Donations (org as donor)
LEFT JOIN datafetch_donation d
    ON d.donor_id = org.id
    AND d.value > 0

-- Filter to MPs
WHERE EXISTS (
    SELECT 1 FROM datafetch_membership hc_membership
    INNER JOIN datafetch_organization hc
        ON hc_membership.organization_id = hc.id
    WHERE hc_membership.person_id = mp.id
        AND hc.name = 'House of Commons'
)

GROUP BY mp.id, mp.name, org.id, org.name, org.classification

-- Only show orgs with BOTH lobbying and donations
HAVING COUNT(DISTINCT c.id) > 0
    AND COUNT(DISTINCT d.id) > 0
    AND SUM(d.value) > 0

ORDER BY total_donated DESC, consultancy_count DESC

LIMIT 30;
