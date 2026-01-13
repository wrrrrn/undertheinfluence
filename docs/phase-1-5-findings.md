# Phase 1.5 Data Import Findings

**Date**: January 12, 2026
**Status**: BLOCKED - Critical compatibility issues discovered

## Summary

Attempting to import data from external sources revealed **fundamental compatibility issues** between Django 1.8 (2015) and Python 3.7 (2018) that make Phase 1.5 impractical without first upgrading Django.

## Issues Discovered

### 1. RawGit CDN Shutdown
**Impact**: HIGH
**Command Affected**: `import_parlparse`

**Problem**:
- Data source URL used `cdn.rawgit.com` which shut down years ago
- No data could be fetched

**Fix Applied**:
```python
# OLD (broken)
url = "https://cdn.rawgit.com/mysociety/parlparse/master/members/people.json"

# NEW (working)
url = "https://raw.githubusercontent.com/mysociety/parlparse/master/members/people.json"
```

**File Modified**: `datafetch/management/commands/import_parlparse.py:232`

**Status**: ✅ FIXED

---

### 2. Name Field Length Validation Error
**Impact**: MEDIUM
**Command Affected**: `import_parlparse`

**Problem**:
- Person model's name fields (family_name, given_name, etc.) had `max_length=128`
- Real data from ParlParse contains names up to 185 characters
- Validation error: `Ensure this value has at most 128 characters (it has 185).`

**Fix Applied**:
- Increased all name fields from `max_length=128` to `max_length=512`
- Created migration `datafetch/migrations/0002_auto_20260112_1643.py`
- Applied migration successfully

**Files Modified**:
- `datafetch/models/models.py:69-75` (Person model fields)

**Status**: ✅ FIXED

---

### 3. Python 3.7 StopIteration in Generators (BLOCKER)
**Impact**: CRITICAL
**Command Affected**: `import_parlparse` and likely all import commands

**Problem**:
```python
RuntimeError: generator raised StopIteration
```

**Root Cause**:
- Python 3.7 implemented PEP 479 which changed how `StopIteration` exceptions behave in generators
- Django 1.8's ORM uses generators extensively and was written before PEP 479
- When Django 1.8's query methods hit a `StopIteration`, Python 3.7 converts it to `RuntimeError`
- This breaks core Django ORM functionality like `.get()` and `.filter()`

**Technical Details**:
- Error occurs in: `/usr/local/lib/python3.7/site-packages/django/db/models/query.py:965`
- Triggered by: `models.Person.objects.get(identifiers=identifier)`
- This is a known incompatibility between Django < 1.11 and Python >= 3.7

**Why This is a Blocker**:
- This affects ALL database queries that use generators
- Cannot be easily patched without modifying Django core
- Data import commands rely heavily on `.get()` and `.get_or_create()`
- Even if we fix one query, we'll hit this repeatedly

**Possible Solutions**:
1. ❌ Downgrade to Python 3.6 - End of life since 2021, no security updates
2. ❌ Patch Django 1.8 core - Too risky, would need extensive testing
3. ✅ **Upgrade to Django 1.11+** - Proper fix, Django 1.11 supports Python 3.7

**Status**: ⛔ **BLOCKER** - Cannot proceed with data imports on Django 1.8 + Python 3.7

---

## PostgreSQL Timezone Issue (RESOLVED)

**Problem**: Django 1.8's `postgresql_psycopg2` backend has overly strict timezone checking
**Fix**: Monkey-patched `utc_tzinfo_factory` in settings.py
**File**: `undertheinfluence/settings.py:136-149`
**Status**: ✅ FIXED

---

## Data Source Status

| Source | Original URL | Status | Notes |
|--------|--------------|--------|-------|
| ParlParse | cdn.rawgit.com | ❌ Dead | Fixed: Now uses raw.githubusercontent.com |
| ElectoralCommission | Unknown | ❓ Untested | |
| APPC | Unknown | ❓ Untested | |
| EveryPolitician | Unknown | ❓ Untested | |

---

## Recommendation

**Skip Phase 1.5 and proceed directly to Phase 2 (Django Upgrade)**

### Reasoning:

1. **Python 3.7 + Django 1.8 is fundamentally incompatible** for data import operations
2. **Can't downgrade Python** - Would lose Python 3.7 compatibility we fought to achieve in Phase 1
3. **Can't patch Django 1.8** - Too complex and risky
4. **Data imports aren't critical for upgrade testing** - We can:
   - Test the upgrade with empty database first
   - Import data after reaching Django 1.11+ (where Python 3.7 works)
   - Validate that the application structure works without real data

### Revised Plan:

**Phase 2 becomes higher priority**:
1. Upgrade Django 1.8 → 1.11 (adds Python 3.7 support)
2. Test data imports on Django 1.11 + Python 3.7
3. Continue Django upgrades: 1.11 → 2.2 → 3.2 → 4.2 → 5.1
4. Upgrade Python: 3.7 → 3.11
5. Return to data imports on modern stack

**Alternative: Import data after each Django upgrade**:
- After Django 1.11: Test `import_parlparse`
- After Django 2.2: Test `import_ec`, `import_appc`
- Validates that upgrades don't break import logic

---

## Lessons Learned

1. **Legacy Framework + Modern Python = Problems**: Django 1.8 was never tested with Python 3.7
2. **External Dependencies Break**: CDN shutdowns (RawGit) make old codebases fragile
3. **Data Quality Issues**: Real-world data doesn't always match schema assumptions (185-char names)
4. **Upgrade Path Matters**: Should have started with Django upgrade, not data imports

---

## Files Modified During Phase 1.5

1. `datafetch/management/commands/import_parlparse.py:232` - Updated RawGit URL
2. `datafetch/models/models.py:69-75` - Increased name field lengths
3. `datafetch/migrations/0002_auto_20260112_1643.py` - Migration for field changes
4. `undertheinfluence/settings.py:136-149` - Timezone monkey patch

---

## Next Steps

See `docs/MODERNIZATION_PROGRESS.md` for updated plan prioritizing Django upgrade over data imports.
