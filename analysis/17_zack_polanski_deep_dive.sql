-- ============================================================================
-- ZACK POLANSKI: DATA DEEP DIVE
-- ============================================================================
-- Date: 2026-01-23
-- Subject: Zack Polanski (Green Party Deputy Leader, London Assembly Member)
-- Actor ID: 2867
-- ============================================================================

-- 1. BASIC IDENTITY
-- Check for the actor record.
SELECT id, name FROM datafetch_actor WHERE id = 2867;

-- 2. ROLES & MEMBERSHIPS
-- Findings: Only "Member of the London Assembly" is recorded.
-- GAP: No explicit "Green Party" membership or "Deputy Leader" role found in datafetch_membership.
SELECT 
    p.name as politician,
    org.name as organization,
    m.role,
    m.start_date,
    m.end_date
FROM datafetch_membership m
JOIN datafetch_actor p ON m.person_id = p.id
JOIN datafetch_actor org ON m.organization_id = org.id
WHERE p.id = 2867;

-- 3. FINANCIAL ACTIVITY: DONATIONS GIVEN
-- Findings: Zack Polanski is a regular donor TO the Green Party.
-- Likely "tithe" or salary contributions.
SELECT 
    donor.name as donor,
    recipient.name as recipient,
    d.value,
    d.received_date,
    d.nature_of_donation
FROM datafetch_donation d
JOIN datafetch_actor donor ON d.donor_id = donor.id
JOIN datafetch_actor recipient ON d.recipient_id = recipient.id
WHERE donor.id = 2867
ORDER BY d.received_date DESC;

-- 4. FINANCIAL ACTIVITY: DONATIONS RECEIVED
-- Findings: No individual donations recorded for him personally.
SELECT 
    recipient.name as recipient,
    donor.name as donor,
    d.value,
    d.received_date
FROM datafetch_donation d
JOIN datafetch_actor recipient ON d.canonical_recipient_id = recipient.id
JOIN datafetch_actor donor ON d.donor_id = donor.id
WHERE recipient.id = 2867;

-- 5. MINISTERIAL MEETINGS
-- Findings: No meetings hosted (not a minister) and no meetings attended (as external actor).
SELECT 
    mm.meeting_date,
    mm.purpose,
    minister.name as host_minister,
    org.name as organization_represented
FROM datafetch_meetingattendee ma
JOIN datafetch_ministerialmeeting mm ON ma.meeting_id = mm.id
JOIN datafetch_actor minister ON mm.minister_id = minister.id
LEFT JOIN datafetch_actor org ON ma.actor_id = org.id
WHERE ma.actor_id = 2867 OR ma.canonical_actor_id = 2867;
