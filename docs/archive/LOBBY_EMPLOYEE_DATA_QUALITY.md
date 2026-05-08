# Lobby Employee Data Quality Report

**Generated:** January 2026
**Scope:** Analysis of lobbying agency employee data from APPC register imports

---

## Executive Summary

The lobby employee data contains significant quality issues that inflate record counts and complicate analysis:

| Issue | Impact | Records Affected |
|-------|--------|-----------------|
| Duplicate memberships | 10x inflation | 95,980 excess records |
| Name parsing errors | ~750 garbage person records | ~25,000 memberships |
| Agency name variations | 16+ duplicate agency pairs | ~2,000 consultancies |

**True unique employee count:** ~10,000 (vs 108,223 membership records)

---

## Issue 1: Duplicate Membership Records

### Root Cause

The `Organization.add_member()` method in `datafetch/models/models.py:177` creates a new `Membership` record every time without checking for duplicates:

```python
def add_member(self, person):
    m = Membership(organization=self, person=person)
    m.save()  # No get_or_create check!
```

When importing multiple APPC quarterly register PDFs, the same person-organization pairs get created multiple times (once per quarterly snapshot where they appear).

### Scale of Duplication

| Metric | Value |
|--------|-------|
| Total person-org pairs | 12,243 |
| Unique pairs (1 record) | 55 |
| Pairs with 2 records | 2,379 |
| Pairs with 3+ records | 9,809 |
| Maximum duplicates for one pair | 335 |
| **Total excess records** | **95,980** |

### Worst Cases

| Person Name | Agency | Duplicate Count |
|-------------|--------|-----------------|
| Councillor | Cratus Communications Ltd | 335 |
| Councillor | FTI Consulting | 215 |
| Party Officer | FTI Consulting | 183 |
| Councillor | Connect | 159 |
| Councillor | BECG | 156 |

Note: "Councillor" and "Party Officer" are **name parsing errors** (see Issue 2).

### Fix Required

Update `Organization.add_member()` to use `get_or_create`:

```python
def add_member(self, person):
    Membership.objects.get_or_create(
        organization=self,
        person=person
    )
```

Or create a cleanup migration to deduplicate existing records.

---

## Issue 2: Name Parsing Errors

### Categories of Bad Names

| Issue Type | Affected Persons | Examples |
|------------|-----------------|----------|
| Single word only | 405 | Adam, Alexia, Baker, Board, Chair, Director, Member |
| Truncated surname (Mc/Mac) | 343 | Graham Mc, Lauren Mc, Andrew Mac, Victoria Mc |
| Role/placeholder | 8 | Client, Councillor, Party Officer, Director, Relevant Roles |

### Root Cause: Truncated Irish/Scottish Names

The APPC register PDF parser fails to keep multi-word surnames together. Names like:
- "Graham **Mc**Millan" → parsed as "Graham Mc" + "Millan" (two people)
- "Lauren **Mc**Guire" → parsed as "Lauren Mc" + "Guire"

This creates two Person records for one actual person.

### Root Cause: Roles Parsed as Names

The PDF structure contains section headers or role labels that get parsed as person names:
- "Councillor" (appears in 937 orgs)
- "Party Officer" (appears in 183 orgs)
- "Client" / "Pro" / "Relevant Roles" / "Bono Clients"

These are clearly metadata, not actual employee names.

### Cleanup Approach

1. **Delete garbage names:**
```sql
DELETE FROM datafetch_membership
WHERE person_id IN (
    SELECT id FROM datafetch_actor
    WHERE name IN ('Client', 'Pro', 'Relevant Roles', 'Bono Clients',
                   'Councillor', 'Party Officer', 'Cllr', 'Director')
);
```

2. **Flag truncated names for manual review:**
```sql
SELECT * FROM datafetch_actor
WHERE name ~ ' Mc$' OR name ~ ' Mac$' OR name ~ ' O$';
```

---

## Issue 3: Agency Name Variations

### Confirmed Duplicate Agency Pairs

Based on **100% employee overlap** (same employees at both "agencies"):

| Agency 1 | Agency 2 | Shared Employees |
|----------|----------|-----------------|
| Atlas Communications Partners Ltd. | Atlas Communications Partners Ltd | 61 |
| JFG Communications Ltd. | JFG Communications Ltd | 14 |

### High Overlap Pairs (Likely Mergers/Rebrands)

| Agency 1 | Agency 2 | Overlap % |
|----------|----------|-----------|
| H+K Strategies | Hill and Knowlton Strategies | 81.8% |
| Cicero Group | H/ Advisors Cicero Group | 69.7% |
| Dentons Global Advisors Interel | Dentons Global Advisors | 69.2% |
| Incisive Health | Evoke Incisive Health Limited | 65.6% |
| BECG | becg | 57.3% |
| Portland | Portland Communications | 48.3% |

### Normalization Issues (Different Spellings of Same Company)

| Normalized Name | Variations |
|-----------------|------------|
| 3x1 | 3x1 \| 3x1 Group |
| becg | BECG \| becg |
| portland | Portland \| Portland Communications |
| mhp | MHP Communications \| MHP Group |
| chambr public affairs | Chambré Public Affairs \| Chambré Public Affairs LLP |

### Fix Required

1. **Canonical agency resolution**: Use the `canonical_agency` field on Consultancy model
2. **Merge duplicate Actor records**: Create entity resolution mappings
3. **Normalize on import**: Apply case normalization and suffix stripping (Ltd, Limited, LLP, etc.)

---

## Recommended Cleanup Steps

### Phase 1: Deduplicate Memberships (Quick Win)

```sql
-- Keep only the first membership record for each person-org pair
DELETE FROM datafetch_membership
WHERE id NOT IN (
    SELECT MIN(id)
    FROM datafetch_membership
    GROUP BY person_id, organization_id
);
```

**Expected result:** Remove ~95,980 duplicate records

### Phase 2: Remove Garbage Person Records

```sql
-- Delete memberships for garbage names
DELETE FROM datafetch_membership
WHERE person_id IN (
    SELECT actor_ptr_id FROM datafetch_person
    WHERE actor_ptr_id IN (
        SELECT id FROM datafetch_actor
        WHERE name IN ('Client', 'Pro', 'Relevant Roles', 'Bono Clients',
                       'Councillor', 'Party Officer', 'Cllr', 'Director', 'Partner',
                       'Chair', 'Board', 'Member', 'Treasurer')
    )
);

-- Then delete the garbage Person/Actor records
DELETE FROM datafetch_person WHERE actor_ptr_id IN (...);
DELETE FROM datafetch_actor WHERE id IN (...);
```

### Phase 3: Agency Entity Resolution

Create mapping table for agency duplicates:

```python
AGENCY_CANONICAL_MAPPING = {
    'Atlas Communications Partners Ltd.': 'Atlas Communications Partners Ltd',
    'JFG Communications Ltd.': 'JFG Communications Ltd',
    'becg': 'BECG',
    'Portland Communications': 'Portland',
    'MHP Group': 'MHP Communications',
    'MHP Group Limited': 'MHP Communications',
    'Hill and Knowlton Strategies': 'H+K Strategies',
    'H/ Advisors Cicero Group': 'Cicero Group',
    # ... etc
}
```

### Phase 4: Fix Import Code

Update `Organization.add_member()` to prevent future duplicates:

```python
def add_member(self, person):
    Membership.objects.get_or_create(
        organization=self,
        person=person,
        defaults={'role': ''}  # or extract role from data
    )
```

---

## Data After Cleanup (Estimated)

| Metric | Current | After Cleanup |
|--------|---------|---------------|
| Membership records | 108,223 | ~12,000 |
| Distinct employees | 10,784 | ~10,000 |
| Lobbying agencies | 217 | ~180 |
| Employee-agency pairs | 12,243 | ~12,000 |

---

## SQL Analysis Queries

See `analysis/12_lobby_employee_analysis.sql` for reusable queries covering:
- Overview statistics
- Top agencies by employee count
- Revolving door (former MPs in lobbying)
- Employee mobility patterns
- Data quality diagnostics
