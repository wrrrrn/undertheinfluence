-- ============================================================================
-- SECTOR & INDUSTRY FUNDING ANALYSIS
-- ============================================================================
-- Purpose: Analyze donations by industry sector - who is lobbying whom in specific sectors
-- Focus: Agriculture, Finance, Energy, Technology, Healthcare, etc.
-- Date: 2026-01-19
-- Database: PostgreSQL
-- ============================================================================


-- ============================================================================
-- SECTION 1: SECTOR IDENTIFICATION & CLASSIFICATION
-- ============================================================================
-- Define industries/sectors based on organization names and classifications

-- 1.1 Donor Organizations by Inferred Sector
-- Categorize donors into industry sectors based on name patterns
WITH donor_sectors AS (
  SELECT
    donor.id AS donor_id,
    donor.name AS donor_name,
    org.classification AS org_type,
    CASE
      -- Financial Services
      WHEN LOWER(donor.name) LIKE '%bank%' OR LOWER(donor.name) LIKE '%financial%'
        OR LOWER(donor.name) LIKE '%investment%' OR LOWER(donor.name) LIKE '%insurance%'
        OR LOWER(donor.name) LIKE '%capital%' THEN 'Financial Services'

      -- Agriculture & Food
      WHEN LOWER(donor.name) LIKE '%farm%' OR LOWER(donor.name) LIKE '%agricult%'
        OR LOWER(donor.name) LIKE '%food%' OR LOWER(donor.name) LIKE '%rural%' THEN 'Agriculture & Food'

      -- Energy & Utilities
      WHEN LOWER(donor.name) LIKE '%energy%' OR LOWER(donor.name) LIKE '%power%'
        OR LOWER(donor.name) LIKE '%electric%' OR LOWER(donor.name) LIKE '%gas%'
        OR LOWER(donor.name) LIKE '%oil%' OR LOWER(donor.name) LIKE '%renewable%' THEN 'Energy & Utilities'

      -- Technology & Telecom
      WHEN LOWER(donor.name) LIKE '%tech%' OR LOWER(donor.name) LIKE '%software%'
        OR LOWER(donor.name) LIKE '%digital%' OR LOWER(donor.name) LIKE '%data%'
        OR LOWER(donor.name) LIKE '%telecom%' OR LOWER(donor.name) LIKE '%internet%' THEN 'Technology & Telecom'

      -- Healthcare & Pharmaceuticals
      WHEN LOWER(donor.name) LIKE '%health%' OR LOWER(donor.name) LIKE '%medical%'
        OR LOWER(donor.name) LIKE '%pharma%' OR LOWER(donor.name) LIKE '%hospital%'
        OR LOWER(donor.name) LIKE '%care%' THEN 'Healthcare & Pharma'

      -- Real Estate & Construction
      WHEN LOWER(donor.name) LIKE '%property%' OR LOWER(donor.name) LIKE '%real estate%'
        OR LOWER(donor.name) LIKE '%construction%' OR LOWER(donor.name) LIKE '%building%'
        OR LOWER(donor.name) LIKE '%housing%' THEN 'Real Estate & Construction'

      -- Manufacturing & Industrial
      WHEN LOWER(donor.name) LIKE '%manufactur%' OR LOWER(donor.name) LIKE '%industrial%'
        OR LOWER(donor.name) LIKE '%engineering%' OR LOWER(donor.name) LIKE '%factory%' THEN 'Manufacturing & Industrial'

      -- Transport & Logistics
      WHEN LOWER(donor.name) LIKE '%transport%' OR LOWER(donor.name) LIKE '%aviation%'
        OR LOWER(donor.name) LIKE '%airline%' OR LOWER(donor.name) LIKE '%shipping%'
        OR LOWER(donor.name) LIKE '%logistics%' THEN 'Transport & Logistics'

      -- Retail & Consumer
      WHEN LOWER(donor.name) LIKE '%retail%' OR LOWER(donor.name) LIKE '%consumer%'
        OR LOWER(donor.name) LIKE '%shop%' OR LOWER(donor.name) LIKE '%store%' THEN 'Retail & Consumer'

      -- Media & Entertainment
      WHEN LOWER(donor.name) LIKE '%media%' OR LOWER(donor.name) LIKE '%broadcast%'
        OR LOWER(donor.name) LIKE '%publishing%' OR LOWER(donor.name) LIKE '%entertainment%'
        OR LOWER(donor.name) LIKE '%gaming%' THEN 'Media & Entertainment'

      -- Trade Unions
      WHEN org.classification = 'Trade Union' THEN 'Trade Unions'

      -- Lobbying Agencies
      WHEN org.classification = 'Lobbying agency' THEN 'Lobbying & PR'

      -- Political Parties
      WHEN org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party') THEN 'Political Party'

      -- Individuals
      WHEN org.actor_ptr_id IS NULL THEN 'Individual'

      -- Other Organizations
      ELSE 'Other Organization'
    END AS sector
  FROM datafetch_actor donor
  LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
  WHERE donor.id IN (SELECT DISTINCT donor_id FROM datafetch_donation WHERE donor_id IS NOT NULL)
)
SELECT
  sector,
  COUNT(DISTINCT donor_id) AS organizations_count,
  STRING_AGG(DISTINCT donor_name, ', ') FILTER (WHERE donor_name IS NOT NULL) AS sample_organizations
FROM donor_sectors
GROUP BY sector
ORDER BY organizations_count DESC;


-- ============================================================================
-- SECTION 2: SECTOR-LEVEL DONATION ANALYSIS
-- ============================================================================

-- 2.1 Donations by Sector - Overall Breakdown
WITH donor_sectors AS (
  SELECT
    donor.id AS donor_id,
    org.classification AS org_type,
    CASE
      WHEN LOWER(donor.name) LIKE '%bank%' OR LOWER(donor.name) LIKE '%financial%'
        OR LOWER(donor.name) LIKE '%investment%' OR LOWER(donor.name) LIKE '%insurance%' THEN 'Financial Services'
      WHEN LOWER(donor.name) LIKE '%farm%' OR LOWER(donor.name) LIKE '%agricult%'
        OR LOWER(donor.name) LIKE '%food%' OR LOWER(donor.name) LIKE '%rural%' THEN 'Agriculture & Food'
      WHEN LOWER(donor.name) LIKE '%energy%' OR LOWER(donor.name) LIKE '%power%'
        OR LOWER(donor.name) LIKE '%oil%' OR LOWER(donor.name) LIKE '%gas%' THEN 'Energy & Utilities'
      WHEN LOWER(donor.name) LIKE '%tech%' OR LOWER(donor.name) LIKE '%software%'
        OR LOWER(donor.name) LIKE '%digital%' THEN 'Technology & Telecom'
      WHEN LOWER(donor.name) LIKE '%health%' OR LOWER(donor.name) LIKE '%pharma%' THEN 'Healthcare & Pharma'
      WHEN LOWER(donor.name) LIKE '%property%' OR LOWER(donor.name) LIKE '%construction%' THEN 'Real Estate & Construction'
      WHEN LOWER(donor.name) LIKE '%transport%' OR LOWER(donor.name) LIKE '%aviation%' THEN 'Transport & Logistics'
      WHEN org.classification = 'Trade Union' THEN 'Trade Unions'
      WHEN org.classification = 'Lobbying agency' THEN 'Lobbying & PR'
      WHEN org.actor_ptr_id IS NULL THEN 'Individual'
      ELSE 'Other Organization'
    END AS sector
  FROM datafetch_actor donor
  LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
),
sector_donations AS (
  SELECT
    ds.sector,
    d.recipient_id,
    d.value,
    d.donor_id
  FROM datafetch_donation d
  JOIN donor_sectors ds ON ds.donor_id = d.donor_id
  WHERE d.value > 0
)
SELECT
  sector,
  COUNT(DISTINCT donor_id) AS distinct_donors,
  COUNT(DISTINCT recipient_id) AS distinct_recipients,
  COUNT(*) AS total_donations,
  SUM(value) AS total_donated,
  ROUND(AVG(value), 2) AS avg_donation,
  ROUND(100.0 * SUM(value) / SUM(SUM(value)) OVER (), 2) AS pct_of_total_donations
FROM sector_donations
GROUP BY sector
ORDER BY total_donated DESC;


-- ============================================================================
-- SECTION 3: AGRICULTURE SECTOR DEEP DIVE
-- ============================================================================

-- 3.1 Agriculture Donors - Who They Fund
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS org_type,
  COUNT(DISTINCT d.recipient_id) AS recipients_funded,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation,
  MIN(d.received_date) AS first_donation,
  MAX(d.received_date) AS latest_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
  AND (
    LOWER(donor.name) LIKE '%farm%'
    OR LOWER(donor.name) LIKE '%agricult%'
    OR LOWER(donor.name) LIKE '%food%'
    OR LOWER(donor.name) LIKE '%rural%'
  )
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 30;


-- 3.2 Agriculture Sector - Top Recipients (MPs/Parties)
WITH agriculture_donations AS (
  SELECT
    d.recipient_id,
    d.donor_id,
    d.value
  FROM datafetch_donation d
  JOIN datafetch_actor donor ON donor.id = d.donor_id
  WHERE d.value > 0
    AND (
      LOWER(donor.name) LIKE '%farm%'
      OR LOWER(donor.name) LIKE '%agricult%'
      OR LOWER(donor.name) LIKE '%food%'
      OR LOWER(donor.name) LIKE '%rural%'
    )
)
SELECT
  recipient.id AS recipient_id,
  MAX(recipient.name) AS recipient_name,
  CASE
    WHEN person.actor_ptr_id IS NOT NULL THEN 'Individual MP/Lord'
    WHEN recipient_org.classification IN ('Political Party', 'Registered Political Party') THEN 'Political Party'
    ELSE 'Organization'
  END AS recipient_type,
  COUNT(DISTINCT ad.donor_id) AS agriculture_donors_count,
  COUNT(*) AS donation_count,
  SUM(ad.value) AS total_received,
  ROUND(AVG(ad.value), 2) AS avg_donation
FROM agriculture_donations ad
JOIN datafetch_actor recipient ON recipient.id = ad.recipient_id
LEFT JOIN datafetch_person person ON person.actor_ptr_id = recipient.id
LEFT JOIN datafetch_organization recipient_org ON recipient_org.actor_ptr_id = recipient.id
GROUP BY recipient.id, recipient_type
ORDER BY total_received DESC
LIMIT 30;


-- 3.3 Agriculture Sector - DEFRA Committee Members
-- Agricultural interests funding MPs on the Environment, Food & Rural Affairs Committee
WITH defra_committee AS (
  SELECT id FROM datafetch_actor
  WHERE name LIKE '%Environment, Food and Rural Affairs Committee%'
),
defra_members AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.organization_id IN (SELECT id FROM defra_committee)
),
agriculture_donations AS (
  SELECT
    dm.person_id,
    d.donor_id,
    d.value
  FROM defra_members dm
  JOIN datafetch_donation d ON d.recipient_id = dm.person_id
  JOIN datafetch_actor donor ON donor.id = d.donor_id
  WHERE d.value > 0
    AND (
      LOWER(donor.name) LIKE '%farm%'
      OR LOWER(donor.name) LIKE '%agricult%'
      OR LOWER(donor.name) LIKE '%food%'
      OR LOWER(donor.name) LIKE '%rural%'
    )
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  COUNT(DISTINCT ad.donor_id) AS agriculture_donors,
  COUNT(*) AS donation_count,
  SUM(ad.value) AS total_received,
  ROUND(AVG(ad.value), 2) AS avg_donation
FROM agriculture_donations ad
JOIN datafetch_actor person ON person.id = ad.person_id
GROUP BY person.id
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 4: FINANCIAL SERVICES SECTOR DEEP DIVE
-- ============================================================================

-- 4.1 Financial Services Donors - Who They Fund
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS org_type,
  COUNT(DISTINCT d.recipient_id) AS recipients_funded,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
  AND (
    LOWER(donor.name) LIKE '%bank%'
    OR LOWER(donor.name) LIKE '%financial%'
    OR LOWER(donor.name) LIKE '%investment%'
    OR LOWER(donor.name) LIKE '%insurance%'
    OR LOWER(donor.name) LIKE '%capital%'
  )
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 30;


-- 4.2 Financial Services - Treasury Committee Members
WITH treasury_committee AS (
  SELECT id FROM datafetch_actor
  WHERE name LIKE '%Treasury Committee%'
),
treasury_members AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.organization_id IN (SELECT id FROM treasury_committee)
),
financial_donations AS (
  SELECT
    tm.person_id,
    d.donor_id,
    d.value
  FROM treasury_members tm
  JOIN datafetch_donation d ON d.recipient_id = tm.person_id
  JOIN datafetch_actor donor ON donor.id = d.donor_id
  WHERE d.value > 0
    AND (
      LOWER(donor.name) LIKE '%bank%'
      OR LOWER(donor.name) LIKE '%financial%'
      OR LOWER(donor.name) LIKE '%investment%'
      OR LOWER(donor.name) LIKE '%insurance%'
    )
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  COUNT(DISTINCT fd.donor_id) AS financial_donors,
  COUNT(*) AS donation_count,
  SUM(fd.value) AS total_received,
  ROUND(AVG(fd.value), 2) AS avg_donation
FROM financial_donations fd
JOIN datafetch_actor person ON person.id = fd.person_id
GROUP BY person.id
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 5: ENERGY SECTOR DEEP DIVE
-- ============================================================================

-- 5.1 Energy Sector Donors - Who They Fund
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS org_type,
  COUNT(DISTINCT d.recipient_id) AS recipients_funded,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
  AND (
    LOWER(donor.name) LIKE '%energy%'
    OR LOWER(donor.name) LIKE '%power%'
    OR LOWER(donor.name) LIKE '%electric%'
    OR LOWER(donor.name) LIKE '%gas%'
    OR LOWER(donor.name) LIKE '%oil%'
    OR LOWER(donor.name) LIKE '%renewable%'
  )
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 30;


-- 5.2 Energy Sector - BEIS/Energy Committee Members
-- Energy sector funding to MPs on relevant committees
WITH energy_committees AS (
  SELECT id FROM datafetch_actor
  WHERE name LIKE '%Business, Energy%Committee%'
    OR name LIKE '%Energy%Committee%'
),
committee_members AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.organization_id IN (SELECT id FROM energy_committees)
),
energy_donations AS (
  SELECT
    cm.person_id,
    d.donor_id,
    d.value
  FROM committee_members cm
  JOIN datafetch_donation d ON d.recipient_id = cm.person_id
  JOIN datafetch_actor donor ON donor.id = d.donor_id
  WHERE d.value > 0
    AND (
      LOWER(donor.name) LIKE '%energy%'
      OR LOWER(donor.name) LIKE '%power%'
      OR LOWER(donor.name) LIKE '%oil%'
      OR LOWER(donor.name) LIKE '%gas%'
    )
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  COUNT(DISTINCT ed.donor_id) AS energy_donors,
  COUNT(*) AS donation_count,
  SUM(ed.value) AS total_received,
  ROUND(AVG(ed.value), 2) AS avg_donation
FROM energy_donations ed
JOIN datafetch_actor person ON person.id = ed.person_id
GROUP BY person.id
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 6: HEALTHCARE & PHARMA SECTOR DEEP DIVE
-- ============================================================================

-- 6.1 Healthcare/Pharma Donors - Who They Fund
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS org_type,
  COUNT(DISTINCT d.recipient_id) AS recipients_funded,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
  AND (
    LOWER(donor.name) LIKE '%health%'
    OR LOWER(donor.name) LIKE '%medical%'
    OR LOWER(donor.name) LIKE '%pharma%'
    OR LOWER(donor.name) LIKE '%hospital%'
  )
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 30;


-- 6.2 Healthcare Sector - Health Committee Members & Health Ministers
WITH health_positions AS (
  -- Health Committee members
  SELECT DISTINCT m.person_id, 'Health Committee' AS position_type
  FROM datafetch_membership m
  JOIN datafetch_actor org ON org.id = m.organization_id
  WHERE org.name LIKE '%Health%Committee%'

  UNION

  -- Health Ministers/Department
  SELECT DISTINCT m.person_id, 'Health Minister' AS position_type
  FROM datafetch_membership m
  JOIN datafetch_actor org ON org.id = m.organization_id
  WHERE org.name LIKE '%Department of Health%'
    OR org.name LIKE '%Department for Health%'
),
healthcare_donations AS (
  SELECT
    hp.person_id,
    hp.position_type,
    d.donor_id,
    d.value
  FROM health_positions hp
  JOIN datafetch_donation d ON d.recipient_id = hp.person_id
  JOIN datafetch_actor donor ON donor.id = d.donor_id
  WHERE d.value > 0
    AND (
      LOWER(donor.name) LIKE '%health%'
      OR LOWER(donor.name) LIKE '%pharma%'
      OR LOWER(donor.name) LIKE '%medical%'
    )
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  MAX(hd.position_type) AS position_type,
  COUNT(DISTINCT hd.donor_id) AS healthcare_donors,
  COUNT(*) AS donation_count,
  SUM(hd.value) AS total_received,
  ROUND(AVG(hd.value), 2) AS avg_donation
FROM healthcare_donations hd
JOIN datafetch_actor person ON person.id = hd.person_id
GROUP BY person.id
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 7: TECHNOLOGY SECTOR DEEP DIVE
-- ============================================================================

-- 7.1 Technology Sector Donors - Who They Fund
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS org_type,
  COUNT(DISTINCT d.recipient_id) AS recipients_funded,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
  AND (
    LOWER(donor.name) LIKE '%tech%'
    OR LOWER(donor.name) LIKE '%software%'
    OR LOWER(donor.name) LIKE '%digital%'
    OR LOWER(donor.name) LIKE '%data%'
    OR LOWER(donor.name) LIKE '%internet%'
  )
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 30;


-- ============================================================================
-- SECTION 8: CROSS-SECTOR ANALYSIS
-- ============================================================================

-- 8.1 Sector Funding by Recipient Type (Parties vs MPs)
WITH donor_sectors AS (
  SELECT
    donor.id AS donor_id,
    CASE
      WHEN LOWER(donor.name) LIKE '%bank%' OR LOWER(donor.name) LIKE '%financial%' THEN 'Financial Services'
      WHEN LOWER(donor.name) LIKE '%farm%' OR LOWER(donor.name) LIKE '%agricult%' THEN 'Agriculture & Food'
      WHEN LOWER(donor.name) LIKE '%energy%' OR LOWER(donor.name) LIKE '%power%' THEN 'Energy & Utilities'
      WHEN LOWER(donor.name) LIKE '%tech%' OR LOWER(donor.name) LIKE '%software%' THEN 'Technology & Telecom'
      WHEN LOWER(donor.name) LIKE '%health%' OR LOWER(donor.name) LIKE '%pharma%' THEN 'Healthcare & Pharma'
      WHEN org.classification = 'Trade Union' THEN 'Trade Unions'
      WHEN org.actor_ptr_id IS NULL THEN 'Individual'
      ELSE 'Other'
    END AS donor_sector
  FROM datafetch_actor donor
  LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
),
sector_recipient_donations AS (
  SELECT
    ds.donor_sector,
    CASE
      WHEN person.actor_ptr_id IS NOT NULL THEN 'Individual MP/Lord'
      WHEN recipient_org.classification IN ('Political Party', 'Registered Political Party') THEN 'Political Party'
      ELSE 'Organization'
    END AS recipient_type,
    d.value
  FROM datafetch_donation d
  JOIN donor_sectors ds ON ds.donor_id = d.donor_id
  JOIN datafetch_actor recipient ON recipient.id = d.recipient_id
  LEFT JOIN datafetch_person person ON person.actor_ptr_id = recipient.id
  LEFT JOIN datafetch_organization recipient_org ON recipient_org.actor_ptr_id = recipient.id
  WHERE d.value > 0
)
SELECT
  donor_sector,
  recipient_type,
  COUNT(*) AS donation_count,
  SUM(value) AS total_donated,
  ROUND(AVG(value), 2) AS avg_donation,
  ROUND(100.0 * SUM(value) / SUM(SUM(value)) OVER (PARTITION BY donor_sector), 2) AS pct_of_sector_total
FROM sector_recipient_donations
GROUP BY donor_sector, recipient_type
ORDER BY donor_sector, total_donated DESC;


-- 8.2 Which Sectors Fund Which Parties Most?
WITH donor_sectors AS (
  SELECT
    donor.id AS donor_id,
    CASE
      WHEN LOWER(donor.name) LIKE '%bank%' OR LOWER(donor.name) LIKE '%financial%' THEN 'Financial Services'
      WHEN LOWER(donor.name) LIKE '%farm%' OR LOWER(donor.name) LIKE '%agricult%' THEN 'Agriculture & Food'
      WHEN LOWER(donor.name) LIKE '%energy%' OR LOWER(donor.name) LIKE '%power%' THEN 'Energy & Utilities'
      WHEN LOWER(donor.name) LIKE '%tech%' OR LOWER(donor.name) LIKE '%software%' THEN 'Technology'
      WHEN org.classification = 'Trade Union' THEN 'Trade Unions'
      WHEN org.actor_ptr_id IS NULL THEN 'Individual'
      ELSE 'Other'
    END AS donor_sector
  FROM datafetch_actor donor
  LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
),
sector_party_donations AS (
  SELECT
    ds.donor_sector,
    party.id AS party_id,
    party.name AS party_name,
    d.value
  FROM datafetch_donation d
  JOIN donor_sectors ds ON ds.donor_id = d.donor_id
  JOIN datafetch_actor party ON party.id = d.recipient_id
  JOIN datafetch_organization party_org ON party_org.actor_ptr_id = party.id
  WHERE d.value > 0
    AND party_org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party')
)
SELECT
  donor_sector,
  party_name,
  COUNT(*) AS donation_count,
  SUM(value) AS total_donated,
  ROUND(AVG(value), 2) AS avg_donation
FROM sector_party_donations
GROUP BY donor_sector, party_name
HAVING SUM(value) > 10000
ORDER BY donor_sector, total_donated DESC;


-- ============================================================================
-- END OF SECTOR & INDUSTRY FUNDING ANALYSIS
-- ============================================================================


-- ============================================================================
-- SECTION 9: DEFENSE & AEROSPACE SECTOR DEEP DIVE
-- ============================================================================

-- 9.1 Defense & Aerospace Donors - Who They Fund
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS org_type,
  COUNT(DISTINCT d.recipient_id) AS recipients_funded,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
  AND (
    LOWER(donor.name) LIKE '%defence%'
    OR LOWER(donor.name) LIKE '%defense%'
    OR LOWER(donor.name) LIKE '%aerospace%'
    OR LOWER(donor.name) LIKE '%aviation%'
    OR LOWER(donor.name) LIKE '%military%'
    OR LOWER(donor.name) LIKE '%arms%'
    OR LOWER(donor.name) LIKE '%bae%'
    OR LOWER(donor.name) LIKE '%lockheed%'
    OR LOWER(donor.name) LIKE '%raytheon%'
  )
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 30;


-- 9.2 Defense Sector - Defence Committee Members
-- Defense industry funding to MPs on the Defence Committee
WITH defence_committee AS (
  SELECT id FROM datafetch_actor
  WHERE name LIKE '%Defence Committee%'
),
committee_members AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.organization_id IN (SELECT id FROM defence_committee)
),
defence_donations AS (
  SELECT
    cm.person_id,
    d.donor_id,
    d.value
  FROM committee_members cm
  JOIN datafetch_donation d ON d.recipient_id = cm.person_id
  JOIN datafetch_actor donor ON donor.id = d.donor_id
  WHERE d.value > 0
    AND (
      LOWER(donor.name) LIKE '%defence%'
      OR LOWER(donor.name) LIKE '%defense%'
      OR LOWER(donor.name) LIKE '%aerospace%'
      OR LOWER(donor.name) LIKE '%military%'
    )
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  COUNT(DISTINCT dd.donor_id) AS defence_donors,
  COUNT(*) AS donation_count,
  SUM(dd.value) AS total_received,
  ROUND(AVG(dd.value), 2) AS avg_donation
FROM defence_donations dd
JOIN datafetch_actor person ON person.id = dd.person_id
GROUP BY person.id
ORDER BY total_received DESC;


-- 9.3 Defense Sector - Defence Ministers
WITH defence_ministers AS (
  SELECT DISTINCT m.person_id, m.role
  FROM datafetch_membership m
  JOIN datafetch_actor org ON org.id = m.organization_id
  WHERE org.name LIKE '%Ministry of Defence%'
    OR org.name LIKE '%Department for Defence%'
    OR m.role LIKE '%Defence%'
),
defence_donations AS (
  SELECT
    dm.person_id,
    dm.role,
    d.donor_id,
    d.value
  FROM defence_ministers dm
  JOIN datafetch_donation d ON d.recipient_id = dm.person_id
  JOIN datafetch_actor donor ON donor.id = d.donor_id
  WHERE d.value > 0
    AND (
      LOWER(donor.name) LIKE '%defence%'
      OR LOWER(donor.name) LIKE '%aerospace%'
      OR LOWER(donor.name) LIKE '%military%'
    )
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  MAX(dd.role) AS defence_role,
  COUNT(DISTINCT dd.donor_id) AS defence_donors,
  COUNT(*) AS donation_count,
  SUM(dd.value) AS total_received,
  ROUND(AVG(dd.value), 2) AS avg_donation
FROM defence_donations dd
JOIN datafetch_actor person ON person.id = dd.person_id
GROUP BY person.id
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 10: TRANSPORT & LOGISTICS SECTOR DEEP DIVE
-- ============================================================================

-- 10.1 Transport Sector Donors - Who They Fund
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS org_type,
  COUNT(DISTINCT d.recipient_id) AS recipients_funded,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
  AND (
    LOWER(donor.name) LIKE '%transport%'
    OR LOWER(donor.name) LIKE '%rail%'
    OR LOWER(donor.name) LIKE '%railway%'
    OR LOWER(donor.name) LIKE '%airline%'
    OR LOWER(donor.name) LIKE '%aviation%'
    OR LOWER(donor.name) LIKE '%shipping%'
    OR LOWER(donor.name) LIKE '%logistics%'
    OR LOWER(donor.name) LIKE '%freight%'
    OR LOWER(donor.name) LIKE '%cargo%'
  )
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 30;


-- 10.2 Transport Sector - Transport Committee Members
WITH transport_committee AS (
  SELECT id FROM datafetch_actor
  WHERE name LIKE '%Transport Committee%'
),
committee_members AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.organization_id IN (SELECT id FROM transport_committee)
),
transport_donations AS (
  SELECT
    cm.person_id,
    d.donor_id,
    d.value
  FROM committee_members cm
  JOIN datafetch_donation d ON d.recipient_id = cm.person_id
  JOIN datafetch_actor donor ON donor.id = d.donor_id
  WHERE d.value > 0
    AND (
      LOWER(donor.name) LIKE '%transport%'
      OR LOWER(donor.name) LIKE '%rail%'
      OR LOWER(donor.name) LIKE '%airline%'
      OR LOWER(donor.name) LIKE '%aviation%'
    )
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  COUNT(DISTINCT td.donor_id) AS transport_donors,
  COUNT(*) AS donation_count,
  SUM(td.value) AS total_received,
  ROUND(AVG(td.value), 2) AS avg_donation
FROM transport_donations td
JOIN datafetch_actor person ON person.id = td.person_id
GROUP BY person.id
ORDER BY total_received DESC;


-- 10.3 Aviation Subsector - Specific Analysis
-- Focus on airlines and airports
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  recipient.id AS recipient_id,
  MAX(recipient.name) AS recipient_name,
  CASE
    WHEN person.actor_ptr_id IS NOT NULL THEN 'Individual MP/Lord'
    WHEN recipient_org.classification IN ('Political Party', 'Registered Political Party') THEN 'Political Party'
    ELSE 'Organization'
  END AS recipient_type,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
JOIN datafetch_actor recipient ON recipient.id = d.recipient_id
LEFT JOIN datafetch_person person ON person.actor_ptr_id = recipient.id
LEFT JOIN datafetch_organization recipient_org ON recipient_org.actor_ptr_id = recipient.id
WHERE d.value > 0
  AND (
    LOWER(donor.name) LIKE '%airline%'
    OR LOWER(donor.name) LIKE '%airways%'
    OR LOWER(donor.name) LIKE '%airport%'
    OR LOWER(donor.name) LIKE '%aviation%'
  )
GROUP BY donor.id, recipient.id, recipient_type
ORDER BY total_donated DESC
LIMIT 30;


-- ============================================================================
-- SECTION 11: REAL ESTATE & PROPERTY SECTOR DEEP DIVE
-- ============================================================================

-- 11.1 Real Estate & Property Donors - Who They Fund
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS org_type,
  COUNT(DISTINCT d.recipient_id) AS recipients_funded,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
  AND (
    LOWER(donor.name) LIKE '%property%'
    OR LOWER(donor.name) LIKE '%real estate%'
    OR LOWER(donor.name) LIKE '%construction%'
    OR LOWER(donor.name) LIKE '%building%'
    OR LOWER(donor.name) LIKE '%housing%'
    OR LOWER(donor.name) LIKE '%developer%'
    OR LOWER(donor.name) LIKE '%land%'
    OR LOWER(donor.name) LIKE '%homes%'
  )
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 30;


-- 11.2 Property Developers - Top Recipients
-- Who receives donations from property developers?
WITH property_donations AS (
  SELECT
    d.recipient_id,
    d.donor_id,
    d.value
  FROM datafetch_donation d
  JOIN datafetch_actor donor ON donor.id = d.donor_id
  WHERE d.value > 0
    AND (
      LOWER(donor.name) LIKE '%property%'
      OR LOWER(donor.name) LIKE '%developer%'
      OR LOWER(donor.name) LIKE '%construction%'
      OR LOWER(donor.name) LIKE '%building%'
    )
)
SELECT
  recipient.id AS recipient_id,
  MAX(recipient.name) AS recipient_name,
  CASE
    WHEN person.actor_ptr_id IS NOT NULL THEN 'Individual MP/Lord'
    WHEN recipient_org.classification IN ('Political Party', 'Registered Political Party') THEN 'Political Party'
    ELSE 'Organization'
  END AS recipient_type,
  COUNT(DISTINCT pd.donor_id) AS property_donors_count,
  COUNT(*) AS donation_count,
  SUM(pd.value) AS total_received,
  ROUND(AVG(pd.value), 2) AS avg_donation
FROM property_donations pd
JOIN datafetch_actor recipient ON recipient.id = pd.recipient_id
LEFT JOIN datafetch_person person ON person.actor_ptr_id = recipient.id
LEFT JOIN datafetch_organization recipient_org ON recipient_org.actor_ptr_id = recipient.id
GROUP BY recipient.id, recipient_type
ORDER BY total_received DESC
LIMIT 30;


-- 11.3 Housing Ministers & Property Funding
-- MPs with housing/communities brief receiving property sector donations
WITH housing_ministers AS (
  SELECT DISTINCT m.person_id, m.role
  FROM datafetch_membership m
  JOIN datafetch_actor org ON org.id = m.organization_id
  WHERE org.name LIKE '%Communities and Local Government%'
    OR org.name LIKE '%Housing%'
    OR m.role LIKE '%Housing%'
    OR m.role LIKE '%Communities%'
),
property_donations AS (
  SELECT
    hm.person_id,
    hm.role,
    d.donor_id,
    d.value
  FROM housing_ministers hm
  JOIN datafetch_donation d ON d.recipient_id = hm.person_id
  JOIN datafetch_actor donor ON donor.id = d.donor_id
  WHERE d.value > 0
    AND (
      LOWER(donor.name) LIKE '%property%'
      OR LOWER(donor.name) LIKE '%construction%'
      OR LOWER(donor.name) LIKE '%developer%'
      OR LOWER(donor.name) LIKE '%housing%'
    )
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  MAX(pd.role) AS housing_role,
  COUNT(DISTINCT pd.donor_id) AS property_donors,
  COUNT(*) AS donation_count,
  SUM(pd.value) AS total_received,
  ROUND(AVG(pd.value), 2) AS avg_donation
FROM property_donations pd
JOIN datafetch_actor person ON person.id = pd.person_id
GROUP BY person.id
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 12: RETAIL & CONSUMER GOODS SECTOR DEEP DIVE
-- ============================================================================

-- 12.1 Retail & Consumer Sector Donors - Who They Fund
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS org_type,
  COUNT(DISTINCT d.recipient_id) AS recipients_funded,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
  AND (
    LOWER(donor.name) LIKE '%retail%'
    OR LOWER(donor.name) LIKE '%consumer%'
    OR LOWER(donor.name) LIKE '%supermarket%'
    OR LOWER(donor.name) LIKE '%shop%'
    OR LOWER(donor.name) LIKE '%store%'
    OR LOWER(donor.name) LIKE '%brand%'
  )
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 30;


-- ============================================================================
-- SECTION 13: MEDIA & BROADCASTING SECTOR DEEP DIVE
-- ============================================================================

-- 13.1 Media & Broadcasting Donors - Who They Fund
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS org_type,
  COUNT(DISTINCT d.recipient_id) AS recipients_funded,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
  AND (
    LOWER(donor.name) LIKE '%media%'
    OR LOWER(donor.name) LIKE '%broadcast%'
    OR LOWER(donor.name) LIKE '%publishing%'
    OR LOWER(donor.name) LIKE '%newspaper%'
    OR LOWER(donor.name) LIKE '%news%'
    OR LOWER(donor.name) LIKE '%entertainment%'
    OR LOWER(donor.name) LIKE '%television%'
    OR LOWER(donor.name) LIKE '%radio%'
  )
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 30;


-- 13.2 Media Sector - DCMS Committee Members
-- Digital, Culture, Media and Sport Committee
WITH dcms_committee AS (
  SELECT id FROM datafetch_actor
  WHERE name LIKE '%Digital, Culture, Media and Sport Committee%'
    OR name LIKE '%Culture, Media and Sport Committee%'
),
committee_members AS (
  SELECT DISTINCT m.person_id
  FROM datafetch_membership m
  WHERE m.organization_id IN (SELECT id FROM dcms_committee)
),
media_donations AS (
  SELECT
    cm.person_id,
    d.donor_id,
    d.value
  FROM committee_members cm
  JOIN datafetch_donation d ON d.recipient_id = cm.person_id
  JOIN datafetch_actor donor ON donor.id = d.donor_id
  WHERE d.value > 0
    AND (
      LOWER(donor.name) LIKE '%media%'
      OR LOWER(donor.name) LIKE '%broadcast%'
      OR LOWER(donor.name) LIKE '%publishing%'
    )
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  COUNT(DISTINCT md.donor_id) AS media_donors,
  COUNT(*) AS donation_count,
  SUM(md.value) AS total_received,
  ROUND(AVG(md.value), 2) AS avg_donation
FROM media_donations md
JOIN datafetch_actor person ON person.id = md.person_id
GROUP BY person.id
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 14: GAMBLING & BETTING SECTOR DEEP DIVE
-- ============================================================================

-- 14.1 Gambling & Betting Donors - Who They Fund
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS org_type,
  COUNT(DISTINCT d.recipient_id) AS recipients_funded,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
  AND (
    LOWER(donor.name) LIKE '%gambling%'
    OR LOWER(donor.name) LIKE '%betting%'
    OR LOWER(donor.name) LIKE '%casino%'
    OR LOWER(donor.name) LIKE '%gaming%'
    OR LOWER(donor.name) LIKE '%bookmaker%'
    OR LOWER(donor.name) LIKE '%ladbrokes%'
    OR LOWER(donor.name) LIKE '%william hill%'
  )
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 30;


-- ============================================================================
-- SECTION 15: TOBACCO & ALCOHOL SECTOR DEEP DIVE
-- ============================================================================

-- 15.1 Tobacco & Alcohol Donors - Who They Fund
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(org.classification) AS org_type,
  COUNT(DISTINCT d.recipient_id) AS recipients_funded,
  COUNT(*) AS donation_count,
  SUM(d.value) AS total_donated,
  ROUND(AVG(d.value), 2) AS avg_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON donor.id = d.donor_id
LEFT JOIN datafetch_organization org ON org.actor_ptr_id = donor.id
WHERE d.value > 0
  AND (
    LOWER(donor.name) LIKE '%tobacco%'
    OR LOWER(donor.name) LIKE '%cigarette%'
    OR LOWER(donor.name) LIKE '%brewery%'
    OR LOWER(donor.name) LIKE '%alcohol%'
    OR LOWER(donor.name) LIKE '%distillery%'
    OR LOWER(donor.name) LIKE '%wine%'
    OR LOWER(donor.name) LIKE '%spirits%'
    OR LOWER(donor.name) LIKE '%drinks%'
  )
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 30;


