-- ============================================================================
-- ORGANIZATIONAL DONATION FLOWS ANALYSIS
-- ============================================================================
-- Purpose: Analyze donation patterns between organizations and bidirectional flows
-- Focus: Org-to-org donations, org-to-MP donations, flow matrices
-- Date: 2026-01-19
-- Database: PostgreSQL
-- ============================================================================

-- ============================================================================
-- SECTION 4: ORGANIZATIONS ANALYSIS (GIVING & RECEIVING)
-- ============================================================================

-- 4.1 Top Organizations as Donors
SELECT
  donor.id AS org_id,
  MAX(donor.name) AS org_name,
  MAX(org.classification) AS org_type,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  COUNT(DISTINCT d.recipient_id) AS distinct_recipients,
  ROUND(AVG(d.value), 2) AS avg_donation,
  MIN(d.received_date) AS first_donation,
  MAX(d.received_date) AS latest_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 50;


-- 4.2 Top Organizations as Recipients
SELECT
  recipient.id AS org_id,
  MAX(recipient.name) AS org_name,
  MAX(org.classification) AS org_type,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_received,
  COUNT(DISTINCT d.donor_id) AS distinct_donors,
  ROUND(AVG(d.value), 2) AS avg_donation,
  MIN(d.received_date) AS first_donation,
  MAX(d.received_date) AS latest_donation
FROM datafetch_donation d
JOIN datafetch_actor recipient ON recipient.id = d.recipient_id
JOIN datafetch_organization org ON org.actor_ptr_id = recipient.id
WHERE d.value > 0
GROUP BY recipient.id
ORDER BY total_received DESC
LIMIT 50;


-- 4.3 Organizations Both Giving and Receiving (Excluding Parties)
WITH org_as_donor AS (
  SELECT
    d.donor_id AS org_id,
    COUNT(*) AS donations_given_count,
    SUM(d.value) AS total_donated,
    COUNT(DISTINCT d.recipient_id) AS recipients
  FROM datafetch_donation d
  JOIN datafetch_organization org ON org.actor_ptr_id = d.donor_id
  WHERE d.value > 0
  GROUP BY d.donor_id
),
org_as_recipient AS (
  SELECT
    d.recipient_id AS org_id,
    COUNT(*) AS donations_received_count,
    SUM(d.value) AS total_received,
    COUNT(DISTINCT d.donor_id) AS donors
  FROM datafetch_donation d
  JOIN datafetch_organization org ON org.actor_ptr_id = d.recipient_id
  WHERE d.value > 0
  GROUP BY d.recipient_id
)
SELECT
  org_actor.id AS org_id,
  MAX(org_actor.name) AS org_name,
  MAX(org.classification) AS org_type,
  COALESCE(oad.donations_given_count, 0) AS donations_given,
  COALESCE(oad.total_donated, 0) AS total_donated,
  COALESCE(oad.recipients, 0) AS distinct_recipients,
  COALESCE(oar.donations_received_count, 0) AS donations_received,
  COALESCE(oar.total_received, 0) AS total_received,
  COALESCE(oar.donors, 0) AS distinct_donors,
  COALESCE(oar.total_received, 0) - COALESCE(oad.total_donated, 0) AS net_received
FROM datafetch_organization org
JOIN datafetch_actor org_actor ON org_actor.id = org.actor_ptr_id
LEFT JOIN org_as_donor oad ON oad.org_id = org.actor_ptr_id
LEFT JOIN org_as_recipient oar ON oar.org_id = org.actor_ptr_id
WHERE (oad.org_id IS NOT NULL OR oar.org_id IS NOT NULL)
  AND org.classification NOT IN ('Political Party', 'Registered Political Party', 'Registered Party')
GROUP BY org_actor.id, org.classification, oad.donations_given_count, oad.total_donated, oad.recipients, oar.donations_received_count, oar.total_received, oar.donors
ORDER BY COALESCE(oar.total_received, 0) + COALESCE(oad.total_donated, 0) DESC
LIMIT 50;


-- 4.4 Organization-to-Organization Donations
SELECT
  donor.id AS donor_org_id,
  MAX(donor.name) AS donor_org_name,
  MAX(donor_org.classification) AS donor_org_type,
  recipient.id AS recipient_org_id,
  MAX(recipient.name) AS recipient_org_name,
  MAX(recipient_org.classification) AS recipient_org_type,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation,
  MIN(d.received_date) AS first_donation,
  MAX(d.received_date) AS latest_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
JOIN datafetch_organization donor_org ON donor_org.actor_ptr_id = donor.id
JOIN datafetch_actor recipient ON recipient.id = d.recipient_id
JOIN datafetch_organization recipient_org ON recipient_org.actor_ptr_id = recipient.id
WHERE d.value > 0
GROUP BY donor.id, recipient.id
ORDER BY total_donated DESC
LIMIT 50;


-- ============================================================================
-- SECTION 5: INDIVIDUALS ANALYSIS (GIVING & RECEIVING)
-- ============================================================================

-- 5.1 Top Individual Donors
SELECT
  donor.id AS person_id,
  MAX(donor.name) AS person_name,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  COUNT(DISTINCT d.recipient_id) AS distinct_recipients,
  ROUND(AVG(d.value), 2) AS avg_donation,
  MIN(d.received_date) AS first_donation,
  MAX(d.received_date) AS latest_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
JOIN datafetch_person person ON person.actor_ptr_id = donor.id
WHERE d.value > 0
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 50;


-- 5.2 Top Individual Recipients (MPs/Lords/Politicians)
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


-- 5.3 Individuals Both Giving and Receiving
WITH person_as_donor AS (
  SELECT
    d.donor_id AS person_id,
    COUNT(*) AS donations_given_count,
    SUM(d.value) AS total_donated,
    COUNT(DISTINCT d.recipient_id) AS recipients
  FROM datafetch_donation d
  JOIN datafetch_person person ON person.actor_ptr_id = d.donor_id
  WHERE d.value > 0
  GROUP BY d.donor_id
),
person_as_recipient AS (
  SELECT
    d.recipient_id AS person_id,
    COUNT(*) AS donations_received_count,
    SUM(d.value) AS total_received,
    COUNT(DISTINCT d.donor_id) AS donors
  FROM datafetch_donation d
  JOIN datafetch_person person ON person.actor_ptr_id = d.recipient_id
  WHERE d.value > 0
  GROUP BY d.recipient_id
)
SELECT
  person_actor.id AS person_id,
  MAX(person_actor.name) AS person_name,
  COALESCE(pad.donations_given_count, 0) AS donations_given,
  COALESCE(pad.total_donated, 0) AS total_donated,
  COALESCE(pad.recipients, 0) AS distinct_recipients,
  COALESCE(par.donations_received_count, 0) AS donations_received,
  COALESCE(par.total_received, 0) AS total_received,
  COALESCE(par.donors, 0) AS distinct_donors,
  COALESCE(par.total_received, 0) - COALESCE(pad.total_donated, 0) AS net_received
FROM datafetch_person person
JOIN datafetch_actor person_actor ON person_actor.id = person.actor_ptr_id
LEFT JOIN person_as_donor pad ON pad.person_id = person.actor_ptr_id
LEFT JOIN person_as_recipient par ON par.person_id = person.actor_ptr_id
WHERE (pad.person_id IS NOT NULL OR par.person_id IS NOT NULL)
GROUP BY person_actor.id, pad.donations_given_count, pad.total_donated, pad.recipients, par.donations_received_count, par.total_received, par.donors
ORDER BY COALESCE(par.total_received, 0) + COALESCE(pad.total_donated, 0) DESC
LIMIT 50;


-- 5.4 Individual-to-Individual Donations
SELECT
  donor.id AS donor_person_id,
  MAX(donor.name) AS donor_name,
  recipient.id AS recipient_person_id,
  MAX(recipient.name) AS recipient_name,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation,
  MIN(d.received_date) AS first_donation,
  MAX(d.received_date) AS latest_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
JOIN datafetch_person donor_person ON donor_person.actor_ptr_id = donor.id
JOIN datafetch_actor recipient ON recipient.id = d.recipient_id
JOIN datafetch_person recipient_person ON recipient_person.actor_ptr_id = recipient.id
WHERE d.value > 0
GROUP BY donor.id, recipient.id
ORDER BY total_donated DESC
LIMIT 50;


-- 5.5 MPs/Lords with Current Memberships - Donations Received
WITH current_mps AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  JOIN datafetch_organization org ON org.actor_ptr_id = m.organization_id
  JOIN datafetch_actor org_actor ON org_actor.id = org.actor_ptr_id
  WHERE LOWER(org_actor.name) LIKE '%house of commons%'
    OR LOWER(org_actor.name) LIKE '%house of lords%'
    OR m.role LIKE '%MP%'
    OR m.role LIKE '%Lord%'
)
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
JOIN current_mps cm ON cm.person_id = recipient.id
WHERE d.value > 0
GROUP BY recipient.id
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 6: BIDIRECTIONAL FLOW ANALYSIS
-- ============================================================================

-- 6.1 Donation Flow Matrix by Actor Type
WITH donor_type_classification AS (
  SELECT
    d.id AS donation_id,
    d.donor_id,
    d.recipient_id,
    d.value,
    CASE
      WHEN donor_person.actor_ptr_id IS NOT NULL THEN 'Individual'
      WHEN donor_org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party') THEN 'Party'
      WHEN donor_org.actor_ptr_id IS NOT NULL THEN 'Organization'
      ELSE 'Unknown'
    END AS donor_type,
    CASE
      WHEN recipient_person.actor_ptr_id IS NOT NULL THEN 'Individual'
      WHEN recipient_org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party') THEN 'Party'
      WHEN recipient_org.actor_ptr_id IS NOT NULL THEN 'Organization'
      ELSE 'Unknown'
    END AS recipient_type
  FROM datafetch_donation d
  LEFT JOIN datafetch_person donor_person ON donor_person.actor_ptr_id = d.donor_id
  LEFT JOIN datafetch_organization donor_org ON donor_org.actor_ptr_id = d.donor_id
  LEFT JOIN datafetch_person recipient_person ON recipient_person.actor_ptr_id = d.recipient_id
  LEFT JOIN datafetch_organization recipient_org ON recipient_org.actor_ptr_id = d.recipient_id
  WHERE d.value > 0
)
SELECT
  donor_type,
  recipient_type,
  COUNT(*) AS donation_count,
  SUM(value) AS total_value,
  ROUND(AVG(value), 2) AS avg_donation,
  COUNT(DISTINCT donor_id) AS distinct_donors,
  COUNT(DISTINCT recipient_id) AS distinct_recipients,
  ROUND(100.0 * SUM(value) / SUM(SUM(value)) OVER (), 2) AS pct_of_total_value
FROM donor_type_classification
GROUP BY donor_type, recipient_type
ORDER BY total_value DESC;


-- 6.2 Party-to-Individual Donation Flows
WITH party_donors AS (
  SELECT org.actor_ptr_id AS party_id
  FROM datafetch_organization org
  WHERE org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
)
SELECT
  donor.id AS party_id,
  MAX(donor.name) AS party_name,
  recipient.id AS recipient_person_id,
  MAX(recipient.name) AS recipient_name,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN party_donors pd ON pd.party_id = d.donor_id
JOIN datafetch_actor donor ON donor.id = d.donor_id
JOIN datafetch_actor recipient ON recipient.id = d.recipient_id
JOIN datafetch_person recipient_person ON recipient_person.actor_ptr_id = recipient.id
WHERE d.value > 0
GROUP BY donor.id, recipient.id
ORDER BY total_donated DESC
LIMIT 50;


-- 6.3 Organization-to-Individual Donation Flows (Non-Party)
SELECT
  donor.id AS org_id,
  MAX(donor.name) AS org_name,
  MAX(donor_org.classification) AS org_type,
  recipient.id AS recipient_person_id,
  MAX(recipient.name) AS recipient_name,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
JOIN datafetch_organization donor_org ON donor_org.actor_ptr_id = donor.id
JOIN datafetch_actor recipient ON recipient.id = d.recipient_id
JOIN datafetch_person recipient_person ON recipient_person.actor_ptr_id = recipient.id
WHERE d.value > 0
  AND donor_org.classification NOT IN ('Political Party', 'Registered Political Party', 'Registered Party')
GROUP BY donor.id, recipient.id
ORDER BY total_donated DESC
LIMIT 50;


-- ============================================================================

-- ============================================================================
-- END OF ORGANIZATIONAL DONATION FLOWS ANALYSIS
-- ============================================================================
