# Data Pipeline: Import, Quality & Remediation

**Last Updated**: April 13, 2026
**Status**: Living document — covers the full data lifecycle from import to cleanup to entity resolution

---

## 1. Current State

### Database Metrics

| Entity | Count | Primary Source |
|--------|-------|---------------|
| **Persons** | 90,728 | ParlParse, MPs Register, Companies House |
| **Organizations** | 64,337 | APPC, Companies House, Meetings |
| **Donations** | 91,513 | MPs Register of Interests |
| **Consultancies** | 62,798 | APPC/PRCA lobbying register |
| **Ministerial Meetings** | 41,362 | GOV.UK transparency data |
| **Meeting Attendees** | 119,793 | GOV.UK transparency data |
| **Memberships** | 136,590 | ParlParse, Companies House, APPC |

### Import Command Status

| Command | Status | Notes |
|---------|--------|-------|
| `import_parlparse` | ✅ Working | Foundation data — MPs, Lords, memberships. Run first. |
| `import_ministers` | ✅ Working | Ministerial appointments. Requires parlparse. |
| `import_mpsinterests` | ✅ Working | MPs' Register of Interests (donations, gifts). |
| `import_ministerial_meetings` | ✅ Working | 41,362 meetings from 23 departments. |
| `import_appc` | ✅ Working | PRCA current lobbying register. **Has name concatenation bugs.** |
| `import_appc_archive` | ✅ Working | Historical APPC PDFs. **Has name concatenation bugs.** |
| `import_lordsinterests` | ✅ Working | Lords' Register of Interests. |
| `import_ec` | ⛔ Broken | Electoral Commission API changed. |
| `import_twfy` | ⏸️ Partial | Requires API key, rate-limited. |
| `import_everypolitician` | ⛔ Broken | Uses defunct cdn.rawgit.com. |
| `enrich_companies_house` | ✅ Working | 51,157 orgs matched. Has some false matches. |
| `populate_canonical` | ✅ Working | Entity resolution, ~10% match rate in fast mode. |

---

## 2. Import Pipeline

### Import Order

Run in this order (each step depends on the previous):

```bash
# 1. Foundation data (persons, orgs, posts, memberships)
docker compose exec api python manage.py import_parlparse --since 2010

# 2. Ministerial appointments (requires persons)
docker compose exec api python manage.py import_ministers --since 2010

# 3. MPs' Register of Interests (requires persons)
docker compose exec api python manage.py import_mpsinterests --since 1996

# 4. Lords' Register of Interests
docker compose exec api python manage.py import_lordsinterests --refresh

# 5. Ministerial meetings (requires persons/ministers)
docker compose exec api python manage.py import_ministerial_meetings \
    --department DSIT --since 2024 --auto

# 6. PRCA current lobbying register
docker compose exec api python manage.py import_appc

# 7. Historical APPC PDFs
docker compose exec api python manage.py import_appc_archive --refresh

# 8. Companies House enrichment (directors, PSCs)
docker compose exec api python manage.py enrich_companies_house \
    --category lobbying_agency --fetch-all --force

# 9. Entity resolution
docker compose exec api python manage.py populate_canonical --dataset all --fast
```

### Ministerial Meetings Coverage

23 departments imported (41,362 meetings total):
BEIS (7,332), DfT (4,332), DHSC (3,917), DBT (3,642), Home Office (2,469), DESNZ (2,305), DCMS (2,254), DSIT (2,047), MHCLG (2,033), DWP (1,926), MoJ (1,619), Defra (1,440), DfE (1,109), Cabinet Office (1,034), HMT (1,013), NIO (910), FCDO (597), FCO (481), BIS (403), MoD (305), Wales Office (146), DECC (41), UKEF (7).

Use `--auto` to scrape GOV.UK collection pages for quarterly publications.

### Companies House Enrichment

| Status | Count | % |
|--------|-------|---|
| Auto-approved | 12,532 | 24.5% |
| Pending review | 11,198 | 21.9% |
| Not found | 16,419 | 32.1% |
| Not applicable | 10,892 | 21.3% |

Categories: `lobbying_agency`, `lobbying_client`, `donor`, `meeting_attendee`, `all`.

---

## 3. Data Quality: Current Issues

### Resolved (149,000+ records fixed)

| Issue | Before | After | Method |
|-------|--------|-------|--------|
| Duplicate donations | 28,516 | 5 | `clean_data --fix=duplicate_donations` |
| Orphaned donations | 637 | 111 | `clean_data --fix=orphaned_donations` |
| Zero-value donations | 427 | 5 | `clean_data --fix=orphaned_donations` |
| Missing membership dates | 116,542 | 19,447 | Date inference from import sources |
| Invalid membership dates | 26 | 0 | `clean_data --fix=invalid_dates` |
| Semicolon-concatenated names | 1,000+ | 0 | `clean_data --fix=semicolon_actors` |
| Labour Party stored as Person | 21,336 donations invisible | Fixed | Manual SQL: reassigned donations from Person #38892 to Org #3525, deleted mistyped Person record (2026-04-13) |

### Outstanding Issues

#### A. Concatenated Lobbyist Names (CRITICAL — ~12,554 records)

**Symptom**: Person records like "Georgia Hunt Annette Jack" (2 people as 1), "Alexa Knight Graham Mc" (broken at line), "Forster" (surname only).

**Root cause**: Two import paths, same bug:

1. **HTML scraper** (`import_appc.py:186-192`): Practitioners come from `<br>`-separated text. When two names appear on the same line without separators, they concatenate. There is **no practitioner name-splitting logic** — clients get `_split_concatenated_clients()` but practitioners do not.

2. **PDF parser** (`datafetch/services/appc_parser.py:286`): Greedy regex `[A-Z][a-zA-Z'-]+` matches "Georgia Hunt Annette Jack" as a single name. Also breaks Mc/Mac surnames: "McMillan" → "Mc" + "Millan" (343 records).

**Test cases**: Open Road (#27450) and Hanover Communications (#26415) — both show severe concatenation on their profile pages.

#### B. Concatenated Client Org Names (HIGH — ~1,730+ records)

**Symptom**: Org records like "AB Agri AbbVie" (animal feed + pharma), "Google HSBC", "Asda DeepMind Technologies".

**Root cause**: Same two paths as lobbyists. The client splitter `_split_concatenated_clients()` (`import_appc.py:50-109`) only splits on `(Ltd|Limited|PLC|Inc|LLP)` suffixes — misses suffix-less concatenations like "Google HSBC".

**Test case**: Open Road (#27450) has 12 clients but ~half are concatenated garbage.

#### C. Garbage Person Records — Roles as Names (QUICK WIN — ~750 records)

**Symptom**: Person records named "Councillor" (937 memberships!), "Party Officer", "Director", "Chair", "Board", "Member", "Dark", "Silva".

**Root cause**: 
- PDF parser (`appc_parser.py:287`): Incomplete garbage filter — only excludes `['advisory', 'role', 'party', 'officer']`. Misses "Councillor", "Director", etc.
- HTML scraper (`import_appc.py:190`): No single-word name rejection.
- MPs' Register (`import_mpsinterests.py:61-76`): `_get_or_create_donor()` accepts any string as a donor name.

#### D. Duplicate Membership Records (~95,980 excess)

**Symptom**: Same person→org pair repeated up to 335 times (e.g., "Councillor" at "Cratus Communications" × 335).

**Root cause**: Historical imports called `add_member()` without dedup. The code is now fixed (`get_or_create`), but existing duplicates remain.

**Cleanup**: `DELETE FROM datafetch_membership WHERE id NOT IN (SELECT MIN(id) FROM datafetch_membership GROUP BY person_id, organization_id);`

#### E. Duplicate Organization Records (64,349 orgs, only 9.9% canonicalized)

**Symptom**: "HSBC" has 26 separate org records ("HSBC", "HSBC UK", "HSBC Holdings plc", "Hsbc", "HSBC)").

**Root cause**: Each import creates orgs by exact name match. No cross-import normalization. `resolve_org_duplicates --ch-only` has linked 1,806 orgs by Companies House number; ~3,205 more are ready.

**Blocker**: Some CH number misassignments exist (e.g., "Bp" assigned Centrica's CH number). Must audit before running Phase 2.

#### F. Duplicate Org Records for Same Company (HIGH — visible on profile pages)

**Symptom**: Philip Davies (#674) shows 17 corporate connections but many are the same company:
- "Ashill Land" appears as 7+ org records: "Ashill Group" (#28341), "Ashill Land" (#128711), "Ashill Land Ltd" (#30026, #51715), "Ashill Land Limited" (#42785, #51345, #47360, #49369, #35306), "ASHILL LAND LIMITED" (#32379)
- Concatenated names: "Ashill Land Ashill Land Limited" (#156778), "Ashill Land Aster Group" (#25809), "Ashill Land Beadles Group" (#29992)
- "Greyhound Board of Great Britain Gumtree" (#49111) and "Greyhound Board of Great Britain Gumtree UK" (#39816) — two concatenated names (Greyhound Board + Gumtree)

**Root cause**: Multiple import runs create separate org records for case/suffix variants. Concatenated client names from APPC import (Issue B). Entity resolution hasn't merged these yet.

**Impact**: Corporate Connections section on politician pages shows duplicate entries. Makes the data look unreliable.

**Fix**: Combination of entity resolution (merge case/suffix variants) and fixing concatenated client imports (Issue B). The `canonical_entry` dedup in the cross-connections query handles some cases but only when the canonical pointer has been set.

#### G. Portland Classification Missing (QUICK WIN)

**Symptom**: Portland (#27687) has 933 consultancies as agency but is classified as "Private Limited Company" instead of "Lobbying Agency". The frontend heuristic catches it (shows "LOBBYING AGENCY" label) but it should be fixed at the data level.

**Root cause**: `import_appc` doesn't set classification to "Lobbying Agency" on the org record, or it was overwritten by Companies House enrichment.

**Fix**: `UPDATE datafetch_organization SET classification = 'Lobbying Agency' WHERE actor_ptr_id IN (SELECT agency_id FROM datafetch_consultancy GROUP BY agency_id HAVING COUNT(*) > 10);`

#### H. Electoral Commission Import Creates Parties as Person Records (CRITICAL — fixed for Labour, may affect others)

**Symptom**: "Labour Party" (actor #38892) was stored as a `Person` record instead of an `Organization`. 21,336 donations totalling £503m were invisible because the party-donations API filters by `Organization.classification = 'Political Party'`.

**Root cause**: `import_ec.py:153-189` — the `_process_recipient()` method determines Person vs Organization based on `regulated_entity_type`. Labour hit the wrong code path and was created as a Person. Conservative and LibDems were correctly classified.

**Fix applied** (2026-04-13): Manually reassigned all donations from Person #38892 to Organization "Labour" #3525. Deleted the mistyped Person record. Also reassigned 2 donor records, 1 meeting attendee record, and 1 canonical_entry pointer.

**Prevention**: When `import_ec` is fixed for the new API, harden `_process_recipient()` to:
1. Check if a recipient with the same EC identifier already exists as an Organization before creating a Person
2. Never create entities with known party names ("Labour", "Conservative", "Liberal Democrat", etc.) as Person records
3. Add a post-import validation that flags any Organization-classification actor stored as Person

#### I. Missing Mayor Memberships (MEDIUM)

**Symptom**: Andy Street (#6127) received £2.3m and attended 10 ministerial meetings as West Midlands Mayor, but has zero membership records. His page shows "PERSON" with no role. Other mayors (Sadiq Khan, Andy Burnham, Steve Rotheram, Boris Johnson) DO have mayor memberships.

**Root cause**: The ministerial meetings import records Street as an attendee ("West Midlands Mayor") but doesn't create a Membership record. ParlParse only covers MPs/Lords. Mayor memberships for Khan/Burnham/Rotheram were likely imported from a different source.

**Fix**: Create Membership records for metro mayors from the ministerial meetings data — parse "West Midlands Mayor", "Mayor of the West Midlands" etc. from attendee roles/titles.

#### J. Meeting Attendee Roles as Names (MEDIUM — visible on homepage)

**Symptom**: "CEO (Vistry Group)" appears as a top meeting attendee for the Transport department on the homepage. This is a role/title, not a person or organisation name.

**Root cause**: `import_ministerial_meetings` stores raw attendee strings from GOV.UK CSV data. Some departments list attendees as roles rather than names (e.g., "CEO (Vistry Group)", "Director General", "Managing Director"). The import doesn't distinguish roles from names.

**Impact**: Appears on the homepage Meetings by Department section. Also inflates meeting attendee counts for the affected departments.

**Fix**: Add a role-pattern filter to `import_ministerial_meetings` — detect strings matching patterns like "CEO (...)", "Director ...", "Managing Director" and either skip them or store them in a separate field. Post-import cleanup: `DELETE FROM datafetch_meetingattendee WHERE actor_name_raw ~ '^(CEO|CFO|CTO|Director|Managing Director|Head of|Chair) '`.

#### K. Organisation Misclassified as Person (MEDIUM — affects meeting data)

**Symptom**: "Scope" (id:53744, a disability charity) is classified as `Person` instead of `Organization`. Appears as a top DWP meeting attendee with `actor_type: "person"`.

**Root cause**: `import_ministerial_meetings` creates new Actor records for unmatched attendees. The importer defaults to creating Person records when it can't determine the type. Organisations attending meetings (charities, trade bodies, companies) get misclassified.

**Fix**: Add heuristics to `import_ministerial_meetings` to detect org-like names (contains "Ltd", "PLC", "Council", "Association", "Foundation", "Charity", "Institute", "Federation", "Union", etc.) and create Organization records instead. For existing data: identify Person records that are meeting attendees with org-like names and reclassify.

#### L. Department Classification Inconsistencies (LOW — blocks department linking)

**Symptom**: Government departments have inconsistent classifications in the database:
- "Department for Business, Energy and Industrial Strategy" → `"Government Department"` ✓
- "Home Office" → `"Unknown"` ✗
- "Department for Business and Trade" → `"External Organization"` ✗

**Root cause**: `import_ministerial_meetings` creates department Organisation records with whatever classification was set at creation time. Some departments were created by other imports with wrong classifications, and the meetings import doesn't correct them.

**Fix**: `UPDATE datafetch_organization SET classification = 'Government Department' WHERE actor_ptr_id IN (SELECT DISTINCT department_id FROM datafetch_ministerialmeeting WHERE department_id IS NOT NULL);`

#### M. Case-Variant Duplicate Organisations (MEDIUM — visible on homepage)

**Symptom**: "AstraZeneca" (id:26122) and "Astrazeneca" (id:25949) both appear in the top lobbying clients list on the homepage. "NATIONAL GRID PLC" and "National Grid plc" appear separately.

**Root cause**: Organisation lookup uses exact name matching. Imports from different sources use different capitalisation for the same entity. Entity resolution's fuzzy matching hasn't caught these because they're in different name-case buckets.

**Fix**: Add case-insensitive matching to `resolve_org_duplicates`: `SELECT name, LOWER(name), COUNT(*) FROM datafetch_actor WHERE polymorphic_ctype_id = (org type) GROUP BY LOWER(name) HAVING COUNT(*) > 1`. Then merge using `canonical_entry`.

#### N. Agency Name Variants in Lobbying Data (LOW — inflates agency counts)

**Symptom**: Same lobbying agency appears under multiple name variants for the same client: "becg"/"BECG", "Incisive Health"/"Evoke Incisive Health"/"Evoke Incisive Health Limited". This inflates agency counts on the homepage (e.g., "18 agencies" may really be 12).

**Root cause**: Different quarterly APPC register filings use different name forms for the same agency. Each creates a separate Org record. Entity resolution hasn't merged these.

**Fix**: Extend `resolve_org_duplicates` with a fuzzy pass specifically for lobbying agencies — compare agencies that share clients. If two agencies have >50% client overlap and similar names, they're likely the same entity.

#### O. Companies House Number Misassignments (BLOCKING — was Issue I)

**Symptom**: "Bp" (actor 49940) assigned Centrica's CH number 03033654. "Exeter City Council Labour Group" matched to "EXETER CITY GROUP LIMITED".

**Root cause**: `enrich_companies_house` auto-approves first API result for short/ambiguous names.

**Fix**: Audit all matches where org name and CH company name have low similarity. Tighten auto-approval threshold.

---

## 4. Remediation Strategy

### Dependency Graph

```
Tier 1 (quick wins, no dependencies):
  1.1 Delete garbage Person records
  1.2 Deduplicate memberships
  1.3 Expand garbage-name filter in parser
  1.4 Add single-word name rejection to importers

Tier 2 (medium effort):
  2.4 Audit CH misassignments ──→ 1.5 Re-run CH linking ──→ 2.5 Fuzzy org matching
  2.2 Fix import_appc.py ──→ 2.1 Split existing concatenated lobbyists
  2.3 Fix PDF regex ──→ 2.1

Tier 3 (larger efforts):
  3.1 Normalize org names on import ──→ 3.3 Selective APPC re-import
  3.2 Improve client splitting ──→ 3.3
```

### Tier 1: Quick Wins

| # | Action | Type | Impact | Effort | Where |
|---|--------|------|--------|--------|-------|
| 1.1 | Delete garbage Person records | Cleanup | ~750 persons, ~25k memberships | 1 hour | SQL below |
| 1.2 | Deduplicate membership records | Cleanup | ~95,980 excess records | 1 hour | SQL below |
| 1.3 | Expand garbage-name blocklist | Import fix | Prevents future garbage | 30 min | `appc_parser.py:287` |
| 1.4 | Add single-word name rejection | Import fix | Prevents "Silva", "Dark" | 30 min | `import_appc.py:191` |
| 1.5 | Re-run `resolve_org_duplicates --ch-only` | Cleanup | ~3,205 more orgs linked | 1 hour | After 2.4 |

**SQL for 1.1** — Delete garbage names:
```sql
-- Step 1: Delete memberships pointing to garbage persons
DELETE FROM datafetch_membership
WHERE person_id IN (
    SELECT id FROM datafetch_actor
    WHERE name IN ('Client', 'Pro', 'Relevant Roles', 'Bono Clients',
                   'Councillor', 'Party Officer', 'Cllr', 'Director', 'Partner',
                   'Chair', 'Board', 'Member', 'Treasurer')
);

-- Step 2: Delete the garbage Person/Actor records
DELETE FROM datafetch_person WHERE actor_ptr_id IN (
    SELECT id FROM datafetch_actor
    WHERE name IN ('Client', 'Pro', 'Relevant Roles', 'Bono Clients',
                   'Councillor', 'Party Officer', 'Cllr', 'Director', 'Partner',
                   'Chair', 'Board', 'Member', 'Treasurer')
);
DELETE FROM datafetch_actor WHERE name IN (
    'Client', 'Pro', 'Relevant Roles', 'Bono Clients',
    'Councillor', 'Party Officer', 'Cllr', 'Director', 'Partner',
    'Chair', 'Board', 'Member', 'Treasurer'
);
```

**SQL for 1.2** — Deduplicate memberships:
```sql
DELETE FROM datafetch_membership
WHERE id NOT IN (
    SELECT MIN(id)
    FROM datafetch_membership
    GROUP BY person_id, organization_id
);
```

**Code for 1.3** — Expand blocklist in `appc_parser.py`:
```python
GARBAGE_NAMES = {
    'councillor', 'director', 'chair', 'board', 'member', 'treasurer',
    'partner', 'client', 'pro', 'bono', 'relevant', 'roles', 'cllr',
    'secretary', 'manager', 'president', 'founder', 'associate',
    'consultant', 'adviser', 'advisor', 'officer', 'executive',
}
```

**Code for 1.4** — Single-word name rejection (add to both importers):
```python
# Reject names that are a single word (all real people have given + family name)
if ' ' not in name.strip():
    continue
```

### Tier 2: Medium Effort, High Impact

| # | Action | Type | Impact | Effort | Where |
|---|--------|------|--------|--------|-------|
| 2.1 | Write `split_concatenated_lobbyists` command | Cleanup | ~12,554 persons split | 1-2 days | New command |
| 2.2 | Add practitioner name splitting to HTML scraper | Import fix | Prevents future concatenation | 1 day | `import_appc.py:186-192` |
| 2.3 | Fix PDF regex for Mc/Mac names | Import fix | ~343 truncated names | 4 hours | `appc_parser.py:286` |
| 2.4 | Audit CH number misassignments | Cleanup | Unblocks org dedup | 1 day | New audit script |
| 2.5 | Run fuzzy org name matching (Phase 2 dedup) | Cleanup | ~16,400 orgs | 1 day | Extend `resolve_org_duplicates` |

**Approach for 2.1** — Splitting concatenated lobbyist names:
1. Query all Person records that are members of Lobbying Agency orgs
2. Identify names with 4+ words (likely concatenated pairs)
3. Split into 2-word name pairs, create new Person records
4. Transfer Membership to new persons, delete concatenated record
5. Run with `--dry-run` first

**Approach for 2.2** — Practitioner name splitting in `import_appc.py`:
Add `_split_concatenated_practitioners()` method analogous to `_split_concatenated_clients()`. Heuristic: if a name has 4+ space-separated words, split on boundaries where `[lowercase] [Uppercase]` appears mid-string.

**Approach for 2.3** — Fix Mc/Mac regex in `appc_parser.py:286`:
Change `[A-Z][a-zA-Z'-]+` to handle Mc/Mac/O' prefixes keeping the next uppercase letter attached.

**Approach for 2.4** — CH audit:
Query all `CompaniesHouseMatch` records where org name vs CH company name have Levenshtein ratio < 0.5. Flag for manual review. Delete incorrect `Identifier` records.

### Tier 3: Larger Efforts

| # | Action | Type | Impact | Effort | Where |
|---|--------|------|--------|--------|-------|
| 3.1 | Add org name normalization to all imports | Import fix | Prevents future duplicates | 2-3 days | All import commands |
| 3.2 | Improve client splitting for suffix-less names | Import fix | ~1,730 concatenated orgs | 2 days | `import_appc.py` |
| 3.3 | Selective APPC re-import | Cleanup | Clean lobbying data | 1 day | Wipe APPC data + re-import |

**3.3 approach**: Don't wipe the whole database (would lose 41k meetings, 91k donations). Instead:
1. Fix all import code first (Tier 1+2)
2. Delete only actors sourced from APPC (lobbying agencies, their practitioners, clients, consultancies)
3. Re-run `import_appc` and `import_appc_archive` with fixed code
4. Re-run entity resolution

---

## 5. Entity Resolution Architecture

### The "Effective Actor" Pattern

Non-destructive: original import data preserved, canonical pointers added separately.

```python
class Donation(models.Model):
    donor = models.ForeignKey(Actor, ...)           # Original (never changed)
    canonical_donor = models.ForeignKey(Actor, ...)  # Resolved (updated by engine)

    @property
    def effective_donor(self):
        return self.canonical_donor or self.donor
```

### Resolution Tiers

| Tier | Method | Confidence | Speed |
|------|--------|------------|-------|
| 1 | Identifier match (EC donor ID, CH number) | 1.0 | Instant |
| 2 | Exact name match (normalized) | 0.95 | Instant |
| 3 | Strong alias match | 0.85 | Fast |
| 4 | Weak/fuzzy match (Levenshtein) | 0.70 | Slow |

### Commands

```bash
# Fast mode (identifier + exact name only, 3000+ records/sec)
docker compose exec api python manage.py populate_canonical --dataset all --fast

# Full mode (includes fuzzy matching, slower)
docker compose exec api python manage.py populate_canonical --dataset all

# Specific datasets
docker compose exec api python manage.py populate_canonical --dataset meeting_attendees --fast
docker compose exec api python manage.py populate_canonical --dataset donations --fast
docker compose exec api python manage.py populate_canonical --dataset consultancies --fast

# Org dedup by Companies House number
docker compose exec api python manage.py resolve_org_duplicates --ch-only
```

---

## 6. Cleanup Commands Reference

### General cleanup

```bash
# Run all safe fixes (dry-run first!)
docker compose exec api python manage.py clean_data --fix=all --dry-run
docker compose exec api python manage.py clean_data --fix=all

# Individual fixes
docker compose exec api python manage.py clean_data --fix=orphaned_donations
docker compose exec api python manage.py clean_data --fix=duplicate_donations
docker compose exec api python manage.py clean_data --fix=invalid_dates
docker compose exec api python manage.py clean_data --fix=placeholder_clients
docker compose exec api python manage.py clean_data --fix=semicolon_actors
docker compose exec api python manage.py clean_data --fix=split_concatenated_attendees
docker compose exec api python manage.py clean_data --fix=split_concatenated_orgs
```

### Taxonomy & naming

```bash
# Standardize org classifications (40+ types → 35 core categories)
docker compose exec api python manage.py cleanup_org_classifications

# Fix corrupted Person prefixes
docker compose exec api python manage.py cleanup_person_data
```

### Entity resolution

```bash
# Canonical linking (fast mode)
docker compose exec api python manage.py populate_canonical --dataset all --fast

# Org dedup by CH number (deterministic, zero ambiguity)
docker compose exec api python manage.py resolve_org_duplicates --ch-only

# Legacy duplicate detection
docker compose exec api python manage.py resolve_duplicates --threshold 0.85 --auto-approve
docker compose exec api python manage.py apply_entity_resolutions --auto-approve-threshold 0.90
```

### Post-import verification

```bash
# Database statistics
docker compose exec api python manage.py shell -c "
from datafetch.models import Person, Organization, Membership, Donation, Consultancy
print(f'Persons: {Person.objects.count():,}')
print(f'Organizations: {Organization.objects.count():,}')
print(f'Memberships: {Membership.objects.count():,}')
print(f'Donations: {Donation.objects.count():,}')
print(f'Consultancies: {Consultancy.objects.count():,}')
"
```

---

## 7. Troubleshooting

**Import fails with "Person DoesNotExist"**: Run `import_parlparse` before `import_ministers`.

**Duplicate actors created**: Run `clean_data --fix=all`, then `populate_canonical --dataset all --fast`.

**Rate limiting**: `helpers.py` has 0.5s rate limit. Wait and retry. For TheyWorkForYou, request higher limits.

**Memory issues with large imports**: Import in date ranges: `--since 2020`, then `--since 2015`, etc.

---

## Consolidated From

This document replaces the following (now archived):
- `docs/DATA_IMPORT_GUIDE.md`
- `docs/DATA_QUALITY_REPORT.md`
- `docs/DATA_CLEANUP_GUIDE.md`
- `docs/data-import-testing.md`
- `docs/ADDITIONAL_CLEANUP_COMMANDS_ANALYSIS.md`
- `docs/CANONICAL_IMPLEMENTATION_REPORT.md`
- `docs/ENTITY_RESOLUTION_OPTIMIZATION.md`
- `analysis/LOBBY_EMPLOYEE_DATA_QUALITY.md`
