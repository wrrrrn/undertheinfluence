# Additional Cleanup Commands Analysis

**Date:** January 23, 2026
**Status:** Analysis Complete
**Scope:** Evaluation of five specialized cleanup management commands.

---

## Executive Summary

We have identified five additional management commands designed to target specific data quality issues beyond the scope of the general `clean_data` command. Analysis shows they target valid data quality problems (concatenated names, non-registrable organizations) and should be executed as part of the remediation phase.

### Impact Summary

| Command | Target Issue | Affected Records | Recommendation |
|---------|--------------|------------------|----------------|
| `cleanup_concatenated_orgs` | Organizations > 150 chars | 160 | **Execute** (Safe deletion) |
| `flag_non_ch_orgs` | Non-registrable "Not Found" orgs | 244+ | **Execute** (Metadata update only) |
| `split_concatenated_attendees` | Actors with ";" or ": " | 1,870 | **Execute** (Splits & cleans) |
| `split_concatenated_orgs` | "Company Ltd Company" pattern | 278 | **Execute** (Splits valid entities) |
| `split_consultancy_clients` | Long lists of client names | 448 | **Execute** (Splits lists) |

---

## 1. `cleanup_concatenated_orgs`
**Purpose:** Deletes organizations with names longer than 150 characters.
**Logic:** Checks for linkages (donations, consultancies) before deleting. Safe to delete if they are just parsing artifacts from ministerial meetings (which are now handled by `MeetingAttendee`).
**Target:** 160 records.
**Risk:** Low. Very long names are almost certainly parsing errors.

## 2. `flag_non_ch_orgs`
**Purpose:** Scans `CompaniesHouseMatch` records with status='not_found' and flags them as 'not_applicable' if they match patterns for government departments, councils, unions, etc.
**Logic:** Regex matching against name.
**Target:** ~244 records identified in sample check.
**Risk:** Low. This is a status update, not a deletion. It prevents wasted API calls.

## 3. `split_concatenated_attendees`
**Purpose:** Splits actors with names containing semicolons (`;`) or colon-space (`: `).
**Logic:** Parses the string, creates new `Person`/`Organization` records for each part, updates `MeetingAttendee` links, and deletes the original "messy" actor.
**Target:** 1,870 records.
**Risk:** Medium. Logic includes heuristics for Person vs Organization. The "semicolon" part is very safe; the "colon" part needs to be checked (usually "Roundtable: Attendee 1, Attendee 2").

## 4. `split_concatenated_orgs`
**Purpose:** Splits organizations matching the pattern "Name Ltd Name" (suffix followed by capital letter).
**Logic:** Regex splitting + Companies House match-based splitting.
**Target:** 278 records.
**Risk:** Low. The pattern `(Ltd|PLC) [A-Z]` is a strong indicator of concatenation.

## 5. `split_consultancy_clients`
**Purpose:** Splits long strings of space-separated company names (e.g., "Advent ASOS BHP").
**Logic:** Heuristics based on capitalization and known company suffixes.
**Target:** 448 records.
**Risk:** Medium. Splitting on spaces is tricky, but the script uses a sophisticated list of "known companies" and suffix logic.

---

## Execution Plan

Run the commands in this order to progressively clean the data:

1.  **`flag_non_ch_orgs`**: Quick win to reduce "Not Found" noise.
2.  **`cleanup_concatenated_orgs`**: Delete the unfixable long garbage strings.
3.  **`split_concatenated_attendees`**: Fix the semicolon/colon separated lists.
4.  **`split_concatenated_orgs`**: Fix the "Company Ltd Company" errors.
5.  **`split_consultancy_clients`**: Fix the space-separated client lists.
