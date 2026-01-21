-- ============================================================================
-- MP & MINISTERIAL FUNDING ANALYSIS
-- ============================================================================
-- Purpose: Analyze donations from the political/MP/government perspective
-- Focus: Individual MPs, ministerial portfolios, government departments
-- Date: 2026-01-19
-- Database: PostgreSQL
-- ============================================================================


-- ============================================================================
-- SECTION 1: INDIVIDUAL MP ANALYSIS
-- ============================================================================

-- 1.1 Top Individual Recipients (MPs/Lords/Politicians) by Total Donations
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


-- 1.2 MPs by Party - Donations Received
-- Shows which parties have MPs receiving most funding
WITH mp_party_mapping AS (
  SELECT DISTINCT
    m.person_id,
    m.on_behalf_of_id AS party_id
  FROM datafetch_membership m
  WHERE m.on_behalf_of_id IS NOT NULL
    AND m.role LIKE '%Member of Parliament%'
),
mp_donations AS (
  SELECT
    d.recipient_id AS person_id,
    COUNT(*) AS donation_count,
    SUM(d.value) AS total_received,
    COUNT(DISTINCT d.donor_id) AS distinct_donors
  FROM datafetch_donation d
  WHERE d.value > 0
  GROUP BY d.recipient_id
)
SELECT
  party.id AS party_id,
  MAX(party.name) AS party_name,
  COUNT(DISTINCT mpm.person_id) AS mps_receiving_donations,
  SUM(md.donation_count) AS total_donations,
  SUM(md.total_received) AS total_received,
  ROUND(AVG(md.total_received), 2) AS avg_per_mp,
  SUM(md.distinct_donors) AS total_distinct_donors
FROM mp_party_mapping mpm
JOIN mp_donations md ON md.person_id = mpm.person_id
JOIN datafetch_actor party ON party.id = mpm.party_id
GROUP BY party.id
ORDER BY total_received DESC;


-- 1.3 Individual MPs - Both Giving and Receiving
-- MPs who both donate and receive donations
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


-- ============================================================================
-- SECTION 2: MINISTERIAL PORTFOLIO ANALYSIS
-- ============================================================================

-- 2.1 Current Ministers - Donations Received
-- MPs currently holding ministerial positions and their donation totals
WITH current_ministers AS (
  SELECT DISTINCT
    m.person_id,
    m.organization_id AS dept_id,
    m.role
  FROM datafetch_membership m
  WHERE m.role IS NOT NULL
    AND m.role != ''
    AND m.role NOT LIKE '%Member of Parliament%'
    AND m.role NOT LIKE '%MSP for%'
    AND m.role NOT LIKE '%Member of the Scottish Parliament%'
    AND (m.end_date IS NULL OR m.end_date = '' OR m.end_date >= CURRENT_DATE::text)
),
minister_donations AS (
  SELECT
    d.recipient_id AS person_id,
    COUNT(*) AS donation_count,
    SUM(d.value) AS total_received,
    COUNT(DISTINCT d.donor_id) AS distinct_donors,
    MIN(d.received_date) AS first_donation,
    MAX(d.received_date) AS latest_donation
  FROM datafetch_donation d
  WHERE d.value > 0
  GROUP BY d.recipient_id
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  MAX(cm.role) AS ministerial_role,
  MAX(dept.name) AS department,
  COALESCE(md.donation_count, 0) AS donation_count,
  COALESCE(md.total_received, 0) AS total_received,
  COALESCE(md.distinct_donors, 0) AS distinct_donors,
  md.first_donation,
  md.latest_donation
FROM current_ministers cm
JOIN datafetch_actor person ON person.id = cm.person_id
LEFT JOIN datafetch_actor dept ON dept.id = cm.dept_id
LEFT JOIN minister_donations md ON md.person_id = cm.person_id
GROUP BY person.id, md.donation_count, md.total_received, md.distinct_donors, md.first_donation, md.latest_donation
ORDER BY total_received DESC;


-- 2.2 Donations by Government Department
-- Aggregate donations to all ministers in each department
WITH department_ministers AS (
  SELECT DISTINCT
    m.person_id,
    m.organization_id AS dept_id,
    m.role
  FROM datafetch_membership m
  WHERE m.role IS NOT NULL
    AND m.role != ''
    AND m.role NOT LIKE '%Member of Parliament%'
    AND m.role NOT LIKE '%MSP for%'
    AND m.organization_id IN (
      -- Major government departments
      SELECT id FROM datafetch_actor WHERE name IN (
        'Home Office',
        'HM Treasury',
        'Foreign & Commonwealth Office',
        'Ministry of Defence',
        'Department of Health',
        'Department for Education',
        'Department for Environment, Food and Rural Affairs',
        'Department for Business, Energy & Industrial Strategy',
        'Department for Transport',
        'Department for Work and Pensions',
        'Ministry of Justice',
        'Cabinet Office',
        'Northern Ireland Office',
        'Scotland Office',
        'Wales Office'
      )
    )
),
minister_donations AS (
  SELECT
    dm.dept_id,
    dm.person_id,
    d.value,
    d.donor_id
  FROM department_ministers dm
  JOIN datafetch_donation d ON d.recipient_id = dm.person_id
  WHERE d.value > 0
)
SELECT
  dept.id AS department_id,
  MAX(dept.name) AS department_name,
  COUNT(DISTINCT md.person_id) AS ministers_count,
  COUNT(DISTINCT CASE WHEN md.value > 0 THEN md.person_id END) AS ministers_with_donations,
  COUNT(*) AS total_donations,
  SUM(md.value) AS total_received,
  COUNT(DISTINCT md.donor_id) AS distinct_donors,
  ROUND(AVG(md.value), 2) AS avg_donation
FROM department_ministers dm
LEFT JOIN datafetch_actor dept ON dept.id = dm.dept_id
LEFT JOIN minister_donations md ON md.dept_id = dm.dept_id
GROUP BY dept.id
ORDER BY total_received DESC;


-- 2.3 Ministerial Rank Analysis
-- Compare donations by ministerial seniority
WITH ministerial_ranks AS (
  SELECT
    m.person_id,
    m.role,
    CASE
      WHEN m.role LIKE '%Secretary of State%' THEN 'Cabinet - Secretary of State'
      WHEN m.role LIKE '%Minister of State%' THEN 'Junior - Minister of State'
      WHEN m.role LIKE '%Parliamentary Under-Secretary%' THEN 'Junior - Parliamentary Under-Secretary'
      WHEN m.role LIKE '%Parliamentary Private Secretary%' OR m.role LIKE '%PPS%' THEN 'PPS - Parliamentary Private Secretary'
      WHEN m.role LIKE '%Whip%' THEN 'Whip'
      WHEN m.role LIKE '%Shadow%' THEN 'Shadow Cabinet/Minister'
      ELSE 'Other Ministerial Role'
    END AS rank_category
  FROM datafetch_membership m
  WHERE m.role IS NOT NULL
    AND m.role != ''
    AND m.role NOT LIKE '%Member of Parliament%'
    AND m.role NOT LIKE '%MSP for%'
),
rank_donations AS (
  SELECT
    mr.rank_category,
    mr.person_id,
    d.value,
    d.donor_id
  FROM ministerial_ranks mr
  JOIN datafetch_donation d ON d.recipient_id = mr.person_id
  WHERE d.value > 0
)
SELECT
  rank_category,
  COUNT(DISTINCT person_id) AS ministers_count,
  COUNT(*) AS total_donations,
  SUM(value) AS total_received,
  COUNT(DISTINCT donor_id) AS distinct_donors,
  ROUND(AVG(value), 2) AS avg_donation,
  ROUND(SUM(value)::numeric / COUNT(DISTINCT person_id), 2) AS avg_per_minister
FROM rank_donations
GROUP BY rank_category
ORDER BY total_received DESC;


-- 2.4 Historical Ministers - Donations During Tenure
-- Donations received while holding ministerial office (date-filtered)
-- Note: Requires safe date casting for partial dates
WITH safe_donations AS (
  SELECT
    d.*,
    CASE WHEN d.received_date::text ~ '^\\d{4}-\\d{2}-\\d{2}$' THEN d.received_date::date END AS received_dt
  FROM datafetch_donation d
  WHERE d.value > 0
),
ministerial_tenures AS (
  SELECT
    m.person_id,
    m.organization_id AS dept_id,
    m.role,
    CASE WHEN m.start_date::text ~ '^\\d{4}-\\d{2}-\\d{2}$' THEN m.start_date::date END AS start_dt,
    CASE WHEN m.end_date::text ~ '^\\d{4}-\\d{2}-\\d{2}$' THEN m.end_date::date END AS end_dt
  FROM datafetch_membership m
  WHERE m.role IS NOT NULL
    AND m.role != ''
    AND m.role NOT LIKE '%Member of Parliament%'
    AND m.role NOT LIKE '%MSP for%'
),
donations_during_tenure AS (
  SELECT
    mt.person_id,
    mt.role,
    mt.dept_id,
    sd.id AS donation_id,
    sd.donor_id,
    sd.value,
    sd.received_dt
  FROM ministerial_tenures mt
  JOIN safe_donations sd ON sd.recipient_id = mt.person_id
  WHERE sd.received_dt IS NOT NULL
    AND (mt.start_dt IS NULL OR sd.received_dt >= mt.start_dt)
    AND (mt.end_dt IS NULL OR sd.received_dt <= mt.end_dt)
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  MAX(ddt.role) AS ministerial_role,
  MAX(dept.name) AS department,
  COUNT(*) AS donations_during_tenure,
  SUM(ddt.value) AS total_received_during_tenure,
  COUNT(DISTINCT ddt.donor_id) AS distinct_donors,
  ROUND(AVG(ddt.value), 2) AS avg_donation
FROM donations_during_tenure ddt
JOIN datafetch_actor person ON person.id = ddt.person_id
LEFT JOIN datafetch_actor dept ON dept.id = ddt.dept_id
GROUP BY person.id
ORDER BY total_received_during_tenure DESC
LIMIT 50;


-- 2.5 Top Donors to Current Ministers
-- Who is funding current government ministers?
WITH current_ministers AS (
  SELECT DISTINCT
    m.person_id
  FROM datafetch_membership m
  WHERE m.role IS NOT NULL
    AND m.role != ''
    AND m.role NOT LIKE '%Member of Parliament%'
    AND m.role NOT LIKE '%MSP for%'
    AND (m.end_date IS NULL OR m.end_date = '' OR m.end_date >= CURRENT_DATE::text)
),
minister_donor_totals AS (
  SELECT
    d.donor_id,
    d.recipient_id,
    SUM(d.value) AS total_donated,
    COUNT(*) AS donation_count
  FROM datafetch_donation d
  JOIN current_ministers cm ON cm.person_id = d.recipient_id
  WHERE d.value > 0
  GROUP BY d.donor_id, d.recipient_id
)
SELECT
  donor.id AS donor_id,
  MAX(donor.name) AS donor_name,
  MAX(COALESCE(donor_org.classification, 'Individual')) AS donor_type,
  COUNT(DISTINCT mdt.recipient_id) AS ministers_funded,
  SUM(mdt.donation_count) AS total_donations,
  SUM(mdt.total_donated) AS total_donated,
  ROUND(AVG(mdt.total_donated), 2) AS avg_per_minister
FROM minister_donor_totals mdt
JOIN datafetch_actor donor ON donor.id = mdt.donor_id
LEFT JOIN datafetch_organization donor_org ON donor_org.actor_ptr_id = donor.id
GROUP BY donor.id
ORDER BY total_donated DESC
LIMIT 50;


-- ============================================================================
-- SECTION 3: HOME OFFICE DEEP DIVE
-- ============================================================================
-- Example deep dive into a specific department (template for other departments)

-- 3.1 Home Office Ministers - Donations Breakdown
WITH home_office_ministers AS (
  SELECT DISTINCT
    m.person_id,
    m.role,
    m.start_date,
    m.end_date
  FROM datafetch_membership m
  JOIN datafetch_actor dept ON dept.id = m.organization_id
  WHERE dept.name = 'Home Office'
    AND m.role IS NOT NULL
    AND m.role != ''
),
minister_donations AS (
  SELECT
    hom.person_id,
    hom.role,
    d.donor_id,
    d.value,
    d.received_date
  FROM home_office_ministers hom
  JOIN datafetch_donation d ON d.recipient_id = hom.person_id
  WHERE d.value > 0
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  MAX(md.role) AS home_office_role,
  COUNT(*) AS donation_count,
  SUM(md.value) AS total_received,
  COUNT(DISTINCT md.donor_id) AS distinct_donors,
  ROUND(AVG(md.value), 2) AS avg_donation,
  MIN(md.received_date) AS first_donation,
  MAX(md.received_date) AS latest_donation
FROM minister_donations md
JOIN datafetch_actor person ON person.id = md.person_id
GROUP BY person.id
ORDER BY total_received DESC;


-- ============================================================================
-- SECTION 4: TEMPORAL ANALYSIS - MINISTERIAL APPOINTMENTS
-- ============================================================================

-- 4.1 Donation Pattern Changes Around Ministerial Appointment
-- Compare donations before vs during ministerial service
-- Note: This is a complex temporal analysis - example for one person
WITH person_ministerial_periods AS (
  SELECT
    m.person_id,
    MIN(CASE WHEN m.start_date::text ~ '^\\d{4}-\\d{2}-\\d{2}$' THEN m.start_date::date END) AS first_ministerial_date
  FROM datafetch_membership m
  WHERE m.role IS NOT NULL
    AND m.role != ''
    AND m.role NOT LIKE '%Member of Parliament%'
    AND m.role NOT LIKE '%MSP for%'
  GROUP BY m.person_id
),
safe_donations AS (
  SELECT
    d.*,
    CASE WHEN d.received_date::text ~ '^\\d{4}-\\d{2}-\\d{2}$' THEN d.received_date::date END AS received_dt
  FROM datafetch_donation d
  WHERE d.value > 0
),
categorized_donations AS (
  SELECT
    pmp.person_id,
    sd.value,
    sd.donor_id,
    CASE
      WHEN sd.received_dt < pmp.first_ministerial_date THEN 'Before Ministerial Role'
      WHEN sd.received_dt >= pmp.first_ministerial_date THEN 'After/During Ministerial Role'
      ELSE 'Unknown Date'
    END AS donation_period
  FROM person_ministerial_periods pmp
  JOIN safe_donations sd ON sd.recipient_id = pmp.person_id
  WHERE sd.received_dt IS NOT NULL
    AND pmp.first_ministerial_date IS NOT NULL
)
SELECT
  person.id AS person_id,
  MAX(person.name) AS person_name,
  cd.donation_period,
  COUNT(*) AS donation_count,
  SUM(cd.value) AS total_received,
  COUNT(DISTINCT cd.donor_id) AS distinct_donors,
  ROUND(AVG(cd.value), 2) AS avg_donation
FROM categorized_donations cd
JOIN datafetch_actor person ON person.id = cd.person_id
GROUP BY person.id, cd.donation_period
ORDER BY person_name, donation_period;


-- ============================================================================
-- SECTION 5: SUMMARY STATISTICS - MINISTERIAL FUNDING
-- ============================================================================

-- 5.1 Overall Ministerial vs Non-Ministerial Funding
WITH ministers AS (
  SELECT DISTINCT person_id
  FROM datafetch_membership
  WHERE role IS NOT NULL
    AND role != ''
    AND role NOT LIKE '%Member of Parliament%'
    AND role NOT LIKE '%MSP for%'
),
donation_summary AS (
  SELECT
    d.recipient_id,
    CASE WHEN m.person_id IS NOT NULL THEN 'Minister (Current or Former)' ELSE 'Non-Minister MP' END AS recipient_category,
    d.value,
    d.donor_id
  FROM datafetch_donation d
  JOIN datafetch_person p ON p.actor_ptr_id = d.recipient_id
  LEFT JOIN ministers m ON m.person_id = d.recipient_id
  WHERE d.value > 0
)
SELECT
  recipient_category,
  COUNT(DISTINCT recipient_id) AS recipient_count,
  COUNT(*) AS total_donations,
  SUM(value) AS total_received,
  COUNT(DISTINCT donor_id) AS distinct_donors,
  ROUND(AVG(value), 2) AS avg_donation,
  ROUND(SUM(value)::numeric / COUNT(DISTINCT recipient_id), 2) AS avg_per_person
FROM donation_summary
GROUP BY recipient_category
ORDER BY total_received DESC;


-- ============================================================================
-- END OF MP & MINISTERIAL FUNDING ANALYSIS
-- ============================================================================
