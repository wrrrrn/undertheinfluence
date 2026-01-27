-- ============================================================================
-- ORGANIZATIONAL DONATION FLOWS ANALYSIS
-- ============================================================================
-- Purpose: Analyze donation patterns between organizations and bidirectional flows
-- Focus: Org-to-org donations, org-to-MP donations, flow matrices
-- Date: 2026-01-26 (Updated with Canonical Resolution)
-- Database: PostgreSQL
-- ============================================================================

-- ============================================================================
-- SECTION 1: ORGANIZATIONS AS DONORS & RECIPIENTS
-- ============================================================================

-- 1.1 Top Organizations as Donors
SELECT
  donor.id AS org_id,
  MAX(donor.name) AS org_name,
  MAX(org.classification) AS org_type,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  COUNT(DISTINCT COALESCE(d.canonical_recipient_id, d.recipient_id)) AS distinct_recipients
FROM datafetch_donation d
JOIN datafetch_actor donor ON COALESCE(d.canonical_donor_id, d.donor_id) = donor.id
JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 50;

-- 1.2 Top Organizations as Recipients
SELECT
  recipient.id AS org_id,
  MAX(recipient.name) AS org_name,
  MAX(org.classification) AS org_type,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_received
FROM datafetch_donation d
JOIN datafetch_actor recipient ON COALESCE(d.canonical_recipient_id, d.recipient_id) = recipient.id
JOIN datafetch_organization org ON org.actor_ptr_id = recipient.id
WHERE d.value > 0
GROUP BY recipient.id
ORDER BY total_received DESC
LIMIT 50;


-- ============================================================================
-- SECTION 2: ORGANIZATION-TO-ORGANIZATION FLOWS
-- ============================================================================

-- 2.1 Major Org-to-Org Donations
SELECT
  donor.name AS donor_org,
  recipient.name AS recipient_org,
  COUNT(*) AS count,
  SUM(d.value) AS total_value
FROM datafetch_donation d
JOIN datafetch_actor donor ON COALESCE(d.canonical_donor_id, d.donor_id) = donor.id
JOIN datafetch_organization donor_org ON donor_org.actor_ptr_id = donor.id
JOIN datafetch_actor recipient ON COALESCE(d.canonical_recipient_id, d.recipient_id) = recipient.id
JOIN datafetch_organization recipient_org ON recipient_org.actor_ptr_id = recipient.id
WHERE d.value > 0
GROUP BY donor.id, recipient.id, donor.name, recipient.name
ORDER BY total_value DESC
LIMIT 50;


-- ============================================================================
-- SECTION 3: BIDIRECTIONAL FLOW ANALYSIS
-- ============================================================================

-- 3.1 Donation Flow Matrix by Actor Type
WITH flows AS (
  SELECT
    CASE 
        WHEN p_donor.actor_ptr_id IS NOT NULL THEN 'Individual'
        WHEN o_donor.classification LIKE '%Party%' THEN 'Party'
        ELSE 'Organization'
    END as donor_type,
    CASE 
        WHEN p_recip.actor_ptr_id IS NOT NULL THEN 'Individual'
        WHEN o_recip.classification LIKE '%Party%' THEN 'Party'
        ELSE 'Organization'
    END as recipient_type,
    d.value
  FROM datafetch_donation d
  LEFT JOIN datafetch_person p_donor ON COALESCE(d.canonical_donor_id, d.donor_id) = p_donor.actor_ptr_id
  LEFT JOIN datafetch_organization o_donor ON COALESCE(d.canonical_donor_id, d.donor_id) = o_donor.actor_ptr_id
  LEFT JOIN datafetch_person p_recip ON COALESCE(d.canonical_recipient_id, d.recipient_id) = p_recip.actor_ptr_id
  LEFT JOIN datafetch_organization o_recip ON COALESCE(d.canonical_recipient_id, d.recipient_id) = o_recip.actor_ptr_id
  WHERE d.value > 0
)
SELECT
  donor_type,
  recipient_type,
  SUM(value) as total_flow,
  COUNT(*) as transaction_count
FROM flows
GROUP BY donor_type, recipient_type
ORDER BY total_flow DESC;