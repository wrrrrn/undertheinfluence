-- ============================================================================
-- POLITICAL PARTY FUNDING ANALYSIS
-- ============================================================================
-- Purpose: Comprehensive breakdown of political party financing
-- Focus: Which parties receive most funding, from whom, and how
-- Date: 2026-01-26 (Updated with Canonical Resolution)
-- Database: PostgreSQL
-- ============================================================================


-- ============================================================================
-- SECTION 1: PARTY-LEVEL OVERVIEW
-- ============================================================================

-- 1.1 Top Political Parties by Total Donations Received
WITH party_donations AS (
  SELECT
    COALESCE(canonical_recipient_id, recipient_id) AS final_recipient_id,
    COUNT(*) AS donation_count,
    SUM(value) AS total_received,
    COUNT(DISTINCT COALESCE(canonical_donor_id, donor_id)) AS distinct_donors,
    MIN(received_date) AS first_donation,
    MAX(received_date) AS latest_donation
  FROM datafetch_donation
  WHERE recipient_id IS NOT NULL AND value > 0
  GROUP BY COALESCE(canonical_recipient_id, recipient_id)
)
SELECT
  party.id AS party_id,
  MAX(party.name) AS party_name,
  MAX(org.classification) AS classification,
  pd.donation_count,
  pd.total_received,
  pd.distinct_donors,
  ROUND(pd.total_received::numeric / pd.donation_count, 2) AS avg_donation,
  ROUND(pd.total_received::numeric / pd.distinct_donors, 2) AS avg_per_donor,
  pd.first_donation,
  pd.latest_donation
FROM party_donations pd
JOIN datafetch_actor party ON party.id = pd.final_recipient_id
JOIN datafetch_organization org ON org.actor_ptr_id = party.id
WHERE org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
GROUP BY party.id, pd.donation_count, pd.total_received, pd.distinct_donors, pd.first_donation, pd.latest_donation
ORDER BY pd.total_received DESC;


-- 1.2 Party Funding Market Share
WITH party_totals AS (
  SELECT
    COALESCE(d.canonical_recipient_id, d.recipient_id) AS party_id,
    SUM(d.value) AS total_received
  FROM datafetch_donation d
  JOIN datafetch_organization org ON org.actor_ptr_id = COALESCE(d.canonical_recipient_id, d.recipient_id)
  WHERE d.value > 0
    AND org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
  GROUP BY COALESCE(d.canonical_recipient_id, d.recipient_id)
)
SELECT
  party.id AS party_id,
  MAX(party.name) AS party_name,
  pt.total_received,
  ROUND(100.0 * pt.total_received / SUM(pt.total_received) OVER (), 2) AS pct_of_party_funding,
  ROUND(pt.total_received::numeric / SUM(pt.total_received) OVER () * 650, 0) AS hypothetical_seats_by_funding
FROM party_totals pt
JOIN datafetch_actor party ON party.id = pt.party_id
GROUP BY party.id, pt.total_received
ORDER BY pt.total_received DESC;


-- ============================================================================
-- SECTION 2: DONOR TYPE BREAKDOWN BY PARTY
-- ============================================================================

-- 2.1 Party Donations by Donor Type (Individuals vs Organizations)
WITH party_recipients AS (
  SELECT org.actor_ptr_id AS party_id
  FROM datafetch_organization org
  WHERE org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
)
SELECT
  party.id AS party_id,
  MAX(party.name) AS party_name,
  CASE
    WHEN donor_person.actor_ptr_id IS NOT NULL THEN 'Individual'
    WHEN donor_org.actor_ptr_id IS NOT NULL THEN COALESCE(donor_org.classification, 'Organization')
    ELSE 'Unknown'
  END AS donor_type,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_received,
  COUNT(DISTINCT COALESCE(d.canonical_donor_id, d.donor_id)) AS distinct_donors,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN party_recipients pr ON pr.party_id = COALESCE(d.canonical_recipient_id, d.recipient_id)
JOIN datafetch_actor party ON party.id = COALESCE(d.canonical_recipient_id, d.recipient_id)
JOIN datafetch_actor donor ON donor.id = COALESCE(d.canonical_donor_id, d.donor_id)
LEFT JOIN datafetch_person donor_person ON donor_person.actor_ptr_id = donor.id
LEFT JOIN datafetch_organization donor_org ON donor_org.actor_ptr_id = donor.id
WHERE d.value > 0
GROUP BY party.id, donor_type
ORDER BY party_name, total_received DESC;


-- ============================================================================
-- SECTION 3: TOP DONORS TO EACH PARTY
-- ============================================================================

-- 3.1 Top Organization Donors to Each Party (Unified)
WITH party_recipients AS (
  SELECT org.actor_ptr_id AS party_id
  FROM datafetch_organization org
  WHERE org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
),
org_party_donations AS (
  SELECT
    COALESCE(d.canonical_donor_id, d.donor_id) AS final_donor_id,
    COALESCE(d.canonical_recipient_id, d.recipient_id) AS final_recipient_id,
    COUNT(*) AS donation_count,
    SUM(d.value) AS total_donated
  FROM datafetch_donation d
  JOIN party_recipients pr ON pr.party_id = COALESCE(d.canonical_recipient_id, d.recipient_id)
  JOIN datafetch_organization donor_org ON donor_org.actor_ptr_id = COALESCE(d.canonical_donor_id, d.donor_id)
  WHERE d.value > 0
  GROUP BY COALESCE(d.canonical_donor_id, d.donor_id), COALESCE(d.canonical_recipient_id, d.recipient_id)
)
SELECT
  party.id AS party_id,
  MAX(party.name) AS party_name,
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(donor_org.classification) AS donor_org_type,
  opd.donation_count,
  opd.total_donated,
  ROUND(opd.total_donated::numeric / opd.donation_count, 2) AS avg_donation
FROM org_party_donations opd
JOIN datafetch_actor party ON party.id = opd.final_recipient_id
JOIN datafetch_actor donor ON donor.id = opd.final_donor_id
LEFT JOIN datafetch_organization donor_org ON donor_org.actor_ptr_id = donor.id
GROUP BY party.id, donor.id, opd.donation_count, opd.total_donated
ORDER BY party_name, opd.total_donated DESC;


-- ============================================================================
-- SECTION 4: TEMPORAL TRENDS
-- ============================================================================

-- 4.1 Party Donations by Year
WITH safe_donations AS (
  SELECT
    d.*,
    COALESCE(d.canonical_recipient_id, d.recipient_id) AS final_recipient_id,
    COALESCE(d.canonical_donor_id, d.donor_id) AS final_donor_id,
    CASE WHEN d.received_date::text ~ '^\d{4}-\d{2}-\d{2}$' THEN d.received_date::date END AS received_dt
  FROM datafetch_donation d
  WHERE d.value > 0
),
party_year_totals AS (
  SELECT
    sd.final_recipient_id AS party_id,
    EXTRACT(YEAR FROM sd.received_dt) AS year,
    COUNT(*) AS donation_count,
    SUM(sd.value) AS total_received,
    COUNT(DISTINCT sd.final_donor_id) AS distinct_donors
  FROM safe_donations sd
  JOIN datafetch_organization org ON org.actor_ptr_id = sd.final_recipient_id
  WHERE sd.received_dt IS NOT NULL
    AND org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
  GROUP BY sd.final_recipient_id, EXTRACT(YEAR FROM sd.received_dt)
)
SELECT
  pyt.year,
  party.id AS party_id,
  MAX(party.name) AS party_name,
  pyt.donation_count,
  pyt.total_received,
  pyt.distinct_donors,
  ROUND(pyt.total_received::numeric / pyt.donation_count, 2) AS avg_donation
FROM party_year_totals pyt
JOIN datafetch_actor party ON party.id = pyt.party_id
WHERE pyt.year >= 2010
GROUP BY pyt.year, party.id, pyt.donation_count, pyt.total_received, pyt.distinct_donors
ORDER BY pyt.year DESC, pyt.total_received DESC;


-- ============================================================================
-- SECTION 5: DONOR CONCENTRATION BY PARTY
-- ============================================================================

-- 5.1 Top 10 Donors' Share of Each Party's Funding
WITH party_recipients AS (
  SELECT org.actor_ptr_id AS party_id
  FROM datafetch_organization org
  WHERE org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
),
donor_party_totals AS (
  SELECT
    COALESCE(d.canonical_recipient_id, d.recipient_id) AS party_id,
    COALESCE(d.canonical_donor_id, d.donor_id) AS donor_id,
    SUM(d.value) AS total_donated
  FROM datafetch_donation d
  JOIN party_recipients pr ON pr.party_id = COALESCE(d.canonical_recipient_id, d.recipient_id)
  WHERE d.value > 0
  GROUP BY COALESCE(d.canonical_recipient_id, d.recipient_id), COALESCE(d.canonical_donor_id, d.donor_id)
),
ranked_donors AS (
  SELECT
    party_id,
    donor_id,
    total_donated,
    ROW_NUMBER() OVER (PARTITION BY party_id ORDER BY total_donated DESC) AS donor_rank
  FROM donor_party_totals
),
top_donor_totals AS (
  SELECT
    party_id,
    SUM(total_donated) AS top_10_total
  FROM ranked_donors
  WHERE donor_rank <= 10
  GROUP BY party_id
),
party_totals AS (
  SELECT
    party_id,
    SUM(total_donated) AS party_total
  FROM donor_party_totals
  GROUP BY party_id
)
SELECT
  party.id AS party_id,
  MAX(party.name) AS party_name,
  tdt.top_10_total AS top_10_donors_total,
  pt.party_total AS party_total_all_donors,
  ROUND(100.0 * tdt.top_10_total / pt.party_total, 2) AS pct_from_top_10
FROM top_donor_totals tdt
JOIN party_totals pt ON pt.party_id = tdt.party_id
JOIN datafetch_actor party ON party.id = tdt.party_id
GROUP BY party.id, tdt.top_10_total, pt.party_total
ORDER BY pct_from_top_10 DESC;


-- ============================================================================
-- SECTION 6: CROSS-PARTY DONORS
-- ============================================================================

-- 6.1 Donors Who Fund Multiple Parties
WITH party_recipients AS (
  SELECT org.actor_ptr_id AS party_id
  FROM datafetch_organization org
  WHERE org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
),
multi_party_donors AS (
  SELECT
    COALESCE(d.canonical_donor_id, d.donor_id) AS final_donor_id,
    COUNT(DISTINCT COALESCE(d.canonical_recipient_id, d.recipient_id)) AS parties_funded,
    SUM(d.value) AS total_donated,
    STRING_AGG(DISTINCT party.name, ', ') AS parties_list
  FROM datafetch_donation d
  JOIN party_recipients pr ON pr.party_id = COALESCE(d.canonical_recipient_id, d.recipient_id)
  JOIN datafetch_actor party ON party.id = COALESCE(d.canonical_recipient_id, d.recipient_id)
  WHERE d.value > 0
  GROUP BY COALESCE(d.canonical_donor_id, d.donor_id)
  HAVING COUNT(DISTINCT COALESCE(d.canonical_recipient_id, d.recipient_id)) > 1
)
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(COALESCE(org.classification, 'Individual')) AS donor_type,
  mpd.parties_funded,
  mpd.total_donated,
  ROUND(mpd.total_donated::numeric / mpd.parties_funded, 2) AS avg_per_party,
  MAX(mpd.parties_list) AS parties_funded_list
FROM multi_party_donors mpd
JOIN datafetch_actor donor ON donor.id = mpd.final_donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
GROUP BY donor.id, mpd.parties_funded, mpd.total_donated
ORDER BY parties_funded DESC, total_donated DESC
LIMIT 30;