# Data Quality Analysis and Remediation Plan

**Date**: 2026-01-14
**Total Issues Found**: 167,967
**Automatically Fixable**: 28,969 (17.2%)
**Requires Manual Review**: 214 (0.1%)
**Requires Import Fixes**: 138,784 (82.6%)

---

## Executive Summary

Data quality audit identified 8 categories of issues across 167k records. Most issues stem from:
1. **Re-running import commands without deduplication** (25k duplicate donations)
2. **Missing start_date logic in lobbying agency imports** (116k memberships)
3. **Lords/Bishops with titles but no family_name/given_name** (24k persons - actually valid)
4. **Incomplete/placeholder donation records** (427 orphaned, 427 zero-value)

**Recommendation**: Run automated cleanup (`clean_data` command), then fix import commands to prevent recurrence.

---

## Issue Categories

### 1. ✅ Orphaned Donations (637 total)

**Status**: Automatically fixable (423/637)

**Root Cause**:
- Donor actors deleted, leaving donations with null donor due to SET_NULL on_delete
- Most are also zero-value with no dates (import placeholders)

**Breakdown**:
- 423 with null donor, zero value, and no dates → **DELETE**
- 214 with null donor but have value/dates → **MANUAL REVIEW**

**Automated Fix**:
```bash
python manage.py clean_data --fix=orphaned_donations
```

**Sample Data**:
```
ID 119480: recipient=Stuart Polak, value=£0.00, date=None
ID 119481: recipient=Stuart Polak, value=£0.00, date=None
```

---

### 2. ⚠️ Duplicate Person Names (134 names)

**Status**: Requires entity resolution

**Root Cause**:
- Legitimate different people with same names (e.g., "John Taylor")
- Position titles that change over time (e.g., "Bishop of Durham")

**Analysis**:
- Top duplicates: "John Taylor" (4), "Bishop of Blackburn" (3), "David Evans" (3)
- Each instance has unique identifiers (different people)
- Some are temporal positions (current vs former bishops)

**Examples**:
```
'John Taylor' (4 instances)
  - ID 427: 5 identifiers, 9 memberships
  - ID 948: 3 identifiers, 3 memberships
  - ID 52517: 1 identifier, 6 memberships

'Bishop of Durham' (3 instances) - Different bishops over time
  - ID 809: 2 identifiers, 1 membership
  - ID 2066: 3 identifiers, 1 membership
  - ID 52585: 1 identifier, 1 membership
```

**Recommendation**:
- **Not duplicates** - these are different people or temporal positions
- Use entity resolution system for true duplicates
- Add temporal handling for position titles

**Manual Review**: Check identifiers to confirm distinct persons

---

### 3. ✅ Duplicate Donations (25,539 groups → 28,516 duplicates)

**Status**: Automatically fixable

**Root Cause**: Re-running import commands without deduplication

**Analysis**:
- 25,539 donation groups with identical attributes
- Each duplicate has unique source URL (re-imported from same EC pages)
- Largest duplication: 33 identical £2,500 donations from same donor/date

**Sample**:
```
33 identical donations: £2,500 on 2014-03-20
  Sources: 33 unique URLs
  IDs: [47871, 47961, 47962, 47963, 47966...]

27 identical donations: £5,000 on 2024-06-10
  Sources: 27 unique URLs
```

**Automated Fix**:
```bash
python manage.py clean_data --fix=duplicate_donations
```
- Keeps oldest ID (minimum ID)
- Deletes 28,516 duplicates
- Preserves 25,539 original donations

**Prevention**: Implement deduplication in `import_ec` command (Phase 3.4 Task #2)

---

### 4. ✅ Zero Value Donations (427 total)

**Status**: Partially fixable (4 with no dates)

**Root Cause**: Import placeholders or incomplete Electoral Commission records

**Breakdown by Type**:
- Gift: 196
- Visit: 127
- Sponsorship: 98
- Cash: 2
- Total value not reported: 4

**Analysis**:
- 427/427 have no received_date (suspicious)
- 4 also have no accepted_date/reported_date → **DELETE**
- 423 may be legitimate "in-kind" donations with unvalued contributions

**Sample**:
```
ID 63241: Croydon Labour Group → Labour Party, type=Cash, value=£0, date=None
ID 64284: African Humanitarian Action → Clare Short, type=Visit, value=£0, date=None
ID 65918: Holocaust Education Trust → Anne Milton, type=Visit, value=£0, date=None
```

**Automated Fix**:
```bash
python manage.py clean_data --fix=zero_value
```
- Deletes 4 with no dates
- Keeps 423 (may be legitimate "in-kind" with unvalued contributions)

**Recommendation**: Review Electoral Commission source data for these specific donations

---

### 5. ⚠️ Invalid Donation Dates (76)

**Status**: Requires manual review

**Root Cause**: Data entry errors in Electoral Commission source data

**Pattern**: accepted_date < received_date (logically impossible)

**Analysis**:
- Most are off by 1-3 days (likely typos)
- Some off by months (151 days max)

**Sample**:
```
ID 57145: accepted=2010-10-05, received=2010-10-25 (20 days off)
ID 58301: accepted=2010-05-25, received=2010-05-28 (3 days off)
ID 62157: accepted=2009-11-12, received=2009-11-13 (1 day off)
ID 64775: accepted=2009-04-24, received=2009-09-22 (151 days off)
```

**Recommendation**:
- Export list of 76 donation IDs
- Cross-reference with Electoral Commission source
- Manually correct or swap dates
- Add validation in import_ec command

**Prevention**: Add date validation: `assert accepted_date >= received_date`

---

### 6. ℹ️ Empty Person Names (24,586)

**Status**: VALID DATA - No fix needed

**Root Cause**: Lords and Bishops with titles but no family_name/given_name

**Analysis**:
- 0 with empty `name` field
- 24,580 with empty `family_name`
- 24,476 with empty `given_name`
- BUT all have `name` field populated with titles

**Examples** (VALID):
```
ID 10: name='Marquess of Lothian', family='', given='Michael Andrew Foster Jude Kerr'
  ✓ 5 identifiers, 22 memberships (ACTIVE)

ID 718: name='Bishop of Norwich', family='', given='Graham Richard James'
  ✓ 2 identifiers, 2 memberships (ACTIVE)

ID 731: name='Earl of Courtown', family='', given='James'
  ✓ 3 identifiers, 8 memberships (ACTIVE)
```

**Verdict**:
- **NOT a data quality issue**
- These are legitimate Person records with titles
- `name` field contains the title (correct)
- `family_name`/`given_name` are empty because they use titles
- All have identifiers and active memberships

**No Action Required**: Data is correct as-is

---

### 7. 🚨 Missing Membership Start_Date (116,542)

**Status**: Requires import command fixes

**Root Cause**: Lobbying agency memberships imported without start_date logic

**Analysis**:
- 116,542 / 150,179 total memberships = **77.6% missing**
- Breakdown by organization:
  - Lobbying agency: 109,868 (94%)
  - Company: 2,103
  - Trade Union: 1,934
  - Other: 2,637

**Sample**:
```
ID 25702: Cameron Grant Patrick Hogan @ 3x1 Group, role='', start_date=None
ID 25703: Will Little Katrine Pearson @ 3x1 Group, role='', start_date=None
ID 25704: Nina Beebe Tiernan Kenny @ Access Partnership, role='', start_date=None
```

**Root Cause**:
- `import_appc` command creates Membership records without inferring start_date
- No temporal data in APPC source

**Recommendation**:
1. **Immediate**: Infer start_date from context:
   - Use organization founding_date if available
   - Use person's first recorded activity
   - Default to import_date as fallback

2. **Long-term**: Fix `import_appc` to infer dates during import

**Migration Script Needed**:
```python
# For existing data
for membership in Membership.objects.filter(start_date__isnull=True):
    if membership.organization.founding_date:
        membership.start_date = membership.organization.founding_date
    elif membership.person.memberships.exclude(start_date__isnull=True).exists():
        membership.start_date = membership.person.memberships.exclude(
            start_date__isnull=True
        ).order_by('start_date').first().start_date
    else:
        membership.start_date = '2010-01-01'  # Fallback
    membership.save()
```

---

### 8. ✅ Invalid Membership Dates (26)

**Status**: Automatically fixable

**Root Cause**: end_date < start_date (dates swapped during import)

**Pattern**: Mostly committee chairs with recent start_dates but old end_dates

**Analysis**:
- All 26 are committee/parliamentary roles
- Dates need to be swapped

**Sample**:
```
ID 11105: Lindsay Hoyle @ Members Estimate Committee
  start=2024-07-09, end=2024-05-30 → SWAP

ID 13204: Andrew Slaughter @ Justice Committee
  start=2024-09-11, end=2022-05-17 → SWAP

ID 18875: Debbie Abrahams @ Work and Pensions Committee
  start=2024-09-11, end=2015-10-26 → SWAP (9 years off!)
```

**Automated Fix**:
```bash
python manage.py clean_data --fix=invalid_dates
```
- Swaps start_date ↔ end_date for all 26 memberships

**Prevention**: Add validation in `import_parlparse`: `assert end_date >= start_date`

---

## Remediation Plan

### Phase 1: Automated Cleanup (TODAY)

Run the automated cleanup command:

```bash
# Dry run first to review changes
python manage.py clean_data --dry-run

# Apply all fixes
python manage.py clean_data --fix=all

# Or fix specific categories
python manage.py clean_data --fix=orphaned_donations
python manage.py clean_data --fix=duplicate_donations
python manage.py clean_data --fix=invalid_dates
python manage.py clean_data --fix=zero_value
```

**Impact**: Fixes 28,969 issues (17.2%)
- 423 orphaned donations deleted
- 28,516 duplicate donations deleted
- 26 invalid membership dates corrected
- 4 zero-value donations deleted

**After Cleanup**:
```bash
# Verify results
python manage.py check_data_quality
```

Expected remaining issues: ~139k (mostly missing membership start_dates)

---

### Phase 2: Manual Review (THIS WEEK)

**2.1 Invalid Donation Dates (76 donations)**

Export list for manual review:
```python
# Create CSV of invalid dates for review
invalid_donations = []
for d in Donation.objects.filter(received_date__isnull=False, accepted_date__isnull=False):
    if d.accepted_date < d.received_date:
        invalid_donations.append({
            'id': d.id,
            'donor': d.donor.name if d.donor else None,
            'recipient': d.recipient.name if d.recipient else None,
            'value': d.value,
            'accepted_date': d.accepted_date,
            'received_date': d.received_date,
            'source': d.source,
        })

# Export to CSV for manual review
import csv
with open('invalid_donation_dates.csv', 'w') as f:
    writer = csv.DictWriter(f, fieldnames=['id', 'donor', 'recipient', 'value',
                                            'accepted_date', 'received_date', 'source'])
    writer.writeheader()
    writer.writerows(invalid_donations)
```

**Action**: Review CSV, correct dates, or confirm data from Electoral Commission

**2.2 Duplicate Person Names (134 names)**

- **No action needed** - these are different people or temporal positions
- Use entity resolution for true duplicates only

---

### Phase 3: Import Command Fixes (PHASE 3.4 TASK #2)

**3.1 Add Deduplication to import_ec**

Prevent duplicate donations:
```python
# In import_ec command
def import_donation(data):
    # Check if donation already exists
    existing = Donation.objects.filter(
        donor=donor,
        recipient=recipient,
        value=data['value'],
        received_date=data['received_date']
    ).first()

    if existing:
        # Update existing instead of creating duplicate
        return existing

    # Create new donation
    donation = Donation.objects.create(...)
```

**3.2 Add Date Validation**

```python
# Validate donation dates
if accepted_date and received_date:
    if accepted_date < received_date:
        logger.warning(f"Invalid dates: accepted {accepted_date} < received {received_date}")
        # Swap them
        accepted_date, received_date = received_date, accepted_date
```

**3.3 Fix Missing Membership Start_Dates**

Create migration script:
```bash
python manage.py infer_membership_dates
```

Infer start_date from:
1. Organization founding_date
2. Person's first membership start_date
3. Import date as fallback

---

### Phase 4: Validation Rules (PREVENT FUTURE ISSUES)

Add model-level validation:

```python
# datafetch/models/influence_mapping.py

class Donation(Relationship):
    def clean(self):
        # Validate dates
        if self.accepted_date and self.received_date:
            if self.accepted_date < self.received_date:
                raise ValidationError({
                    'accepted_date': 'Accepted date cannot be before received date'
                })

        # Validate value
        if self.value is not None and self.value < 0:
            raise ValidationError({'value': 'Donation value cannot be negative'})

class Membership(models.Model):
    def clean(self):
        # Validate dates
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({
                    'end_date': 'End date cannot be before start date'
                })
```

---

## Summary Statistics

### Before Cleanup

| Issue | Count | Severity |
|-------|-------|----------|
| Orphaned donations | 637 | High |
| Duplicate persons | 134 | Low (valid) |
| Duplicate donations | 28,516 | High |
| Zero value donations | 427 | Medium |
| Invalid donation dates | 76 | Medium |
| Empty person names | 24,586 | None (valid) |
| Missing membership start_dates | 116,542 | High |
| Invalid membership dates | 26 | Medium |
| **TOTAL** | **167,967** | |

### After Automated Cleanup

| Issue | Count | Status |
|-------|-------|--------|
| Orphaned donations | 214 | Manual review |
| Duplicate persons | 134 | Valid (no action) |
| Duplicate donations | 0 | ✅ Fixed |
| Zero value donations | 423 | Valid (in-kind) |
| Invalid donation dates | 76 | Manual review |
| Empty person names | 24,586 | Valid (no action) |
| Missing membership start_dates | 116,542 | Import fix needed |
| Invalid membership dates | 0 | ✅ Fixed |
| **REMAINING** | **141,975** | |

### Required Actions

- ✅ **Automated**: 28,969 issues (17.2%)
- 📋 **Manual Review**: 290 issues (0.2%)
- 🔧 **Import Fixes**: 116,542 issues (82.6%)

---

## Commands Reference

```bash
# Investigation
python manage.py check_data_quality
python manage.py check_data_quality --verbose --check=duplicates
python /app/scripts/investigate_data_issues.py

# Automated Cleanup
python manage.py clean_data --dry-run
python manage.py clean_data --fix=all

# Verification
python manage.py check_data_quality
```

---

## Next Steps

1. ✅ **Today**: Run automated cleanup (`clean_data --fix=all`)
2. 📋 **This Week**: Manual review of 290 remaining issues
3. 🔧 **Phase 3.4 Task #2**: Fix import commands (deduplication, date validation, start_date inference)
4. ✅ **Ongoing**: Monitor data quality with `check_data_quality` command
