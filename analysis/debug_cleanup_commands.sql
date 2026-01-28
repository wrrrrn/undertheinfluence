-- ============================================================================
-- CLEANUP COMMAND IMPACT ANALYSIS
-- ============================================================================

-- 1. cleanup_concatenated_orgs.py (Names > 150 chars)
SELECT
    'Organizations > 150 chars' as issue,
    COUNT(*) as count
FROM datafetch_actor
WHERE LENGTH(name) > 150;

-- 2. flag_non_ch_orgs.py (Not Found Orgs matching patterns)
-- Sample patterns from the command (government, council, etc.)
SELECT
    'Not Found Orgs (Potential Non-CH)' as issue,
    COUNT(*) as count
FROM datafetch_companieshousematch m
JOIN datafetch_actor a ON m.organization_id = a.id
WHERE m.status = 'not_found'
  AND (
       a.name ILIKE '%department%' OR
       a.name ILIKE '%ministry%' OR
       a.name ILIKE '%council%' OR
       a.name ILIKE '%university%' OR
       a.name ILIKE '%nhs%' OR
       a.name ILIKE '%police%' OR
       a.name ILIKE '%union%'
  );

-- 3. split_concatenated_attendees.py (Messy Actors)
-- Actors with semicolons or colon-space
SELECT
    'Messy Actors (semicolon/colon)' as issue,
    COUNT(*) as count
FROM datafetch_actor
WHERE name LIKE '%;%' OR name LIKE '%: %';

-- 4. split_concatenated_orgs.py (Regex Pattern)
-- Pattern: Suffix (Ltd/etc) followed by space and Capital
SELECT
    'Concatenated Orgs (Regex Pattern)' as issue,
    COUNT(*) as count
FROM datafetch_actor
WHERE name ~* '(Ltd|Limited|PLC|Inc|LLP)\.?\s+[A-Z]';

-- 5. split_consultancy_clients.py (Long names with multiple caps)
-- Heuristic: Names > 100 chars with 3+ all-caps words (rough approximation)
SELECT
    'Concatenated Consultancy Clients (Heuristic)' as issue,
    COUNT(*) as count
FROM datafetch_organization o
JOIN datafetch_actor a ON o.actor_ptr_id = a.id
WHERE LENGTH(a.name) > 100
  AND a.name ~ '[A-Z]{2,}.*[A-Z]{2,}.*[A-Z]{2,}';
