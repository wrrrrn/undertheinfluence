# Data Quality Check & Cleanup Dry Run Log

**Date:** January 23, 2026
**Status:** Dry Run Analysis Complete

---

## 1. Data Quality Check Results

Command: `python manage.py check_data_quality`

### Findings
- **Orphaned Donations:** 106 donations have a null donor.
- **Duplicate Records:**
  - 1,273 person names with duplicates.
  - 1,795 organization names with duplicates.
  - 1,444 potentially duplicate donations.
- **Data Validation:**
  - 5 donations with zero value.
  - 47 donations where `accepted_date` < `received_date`.
  - 55,163 persons with empty names (Note: Many of these are valid titles like "Lord X", need verification).
- **Data Completeness:**
  - 19,630 memberships are missing a `start_date`.

**Total Issues Identified:** 79,463

---

## 2. Cleanup Dry Run Results

Command: `python manage.py clean_data --dry-run`

### Proposed Actions
This command identified **5,207** specific issues that can be safely automatically fixed or deleted.

| Issue Type | Found | Action Proposed | Impact |
|------------|-------|-----------------|--------|
| **Orphaned Donations** | 0 | None (Already handled or none strictly zero-value/no-date) | 0 |
| **Duplicate Donations** | 1,444 groups | Delete duplicates, keep original | **3,637 deletions** |
| **Semicolon Actors** | 1,402 | Delete bad actor records (parsing artifacts) | **1,402 deletions** |
| **Roundtable Actors** | 168 | Delete garbage "Roundtable..." actors | **168 deletions** |
| **Zero Value Donations** | 0 | None | 0 |
| **Invalid Dates** | 0 | None | 0 |

### Total Fixable Issues: 5,207

---

## 3. Analysis & Next Steps

1.  **Duplicate Donations:** The 3,637 duplicate donations are safe to delete. They are redundant records likely created by re-running imports without deduplication logic.
2.  **Garbage Actors:** The 1,402 "semicolon actors" (e.g., "Company A; Company B") and 168 "Roundtable" actors are essentially parsing errors from the `import_appc_archive` or ministerial meetings scripts. Deleting them is correct.
3.  **Missing Start Dates:** The 19,630 memberships with missing start dates were NOT addressed by `clean_data`. This confirms the need for the fix applied to `import_appc_archive.py` (which now correctly sets dates for *new* imports). For existing data, we may need a migration script or to re-run the import with the fix.
4.  **Import Status Correction:** `import_appc` was confirmed as **working** (current lobby register), correcting previous documentation.

### Recommendation
Proceed with `python manage.py clean_data --fix=all` to execute these 5,207 fixes.
