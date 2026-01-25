---

## 6. Root Cause Analysis & Import Fixes

### A. The Splitting Logic Flaw
**Code Location:** `datafetch/management/commands/import_ministerial_meetings.py` -> `_create_meeting_attendees`

**Current Logic:**
```python
if ',' in meeting.organisation_met_raw:
    # Splits only on commas
    attendee_names = meeting.organisation_met_raw.split(',')
```

**The Problem:**
This logic is too simple. It misses:
1.  **" and "**: The most common natural language delimiter used by departments.
2.  **" / "**: Often used for lists.
3.  **";"**: Explicitly used as a delimiter but treated as part of the name.
4.  **"&"**: Used as a delimiter but also common in company names, leading to false positives if blindly split.

**Recommended Fix:**
Implement a robust `split_attendees(raw_string)` utility function that:
1.  Splits on explicit delimiters: `;`, ` / ` (with spaces).
2.  Splits on ` and ` / ` & ` **ONLY IF** the resulting parts look like distinct entities (heuristic check: length > 3, contains corporate suffix or known entity).
3.  Respects "protected" phrases (e.g., "Police and Crime Commissioner").

### B. "Roundtable" as an Actor
**Code Location:** `datafetch/services/ministerial_meetings_parser.py`

**The Problem:**
The parser treats the "Organisation/Individual" column content as an actor name, even if it says "Roundtable on AI". The `import_ministerial_meetings.py` command then blindly creates an `Actor` named "Roundtable on AI".

**Recommended Fix:**
Modify `MinisterialMeetingsParser.parse_csv`:
```python
if 'roundtable' in external_actor.lower():
    # It's a description, not an actor
    purpose = f"{purpose} ({external_actor})"
    # How to handle the actor?
    # Option 1: Skip if no other names present
    # Option 2: Extract names if "Roundtable with X, Y, Z"
```
Or better, in `_create_meeting_attendees`:
```python
if actor_name.lower().startswith('roundtable'):
    meeting.is_roundtable = True
    meeting.purpose += f" [{actor_name}]"
    meeting.save()
    return  # Do not create an attendee record
```

### C. Missing Source URLs
**Code Location:** `import_ministerial_meetings.py` -> `_manual_import`

**The Problem:**
In manual mode, `source_url` defaults to `''` if not provided via `--url`. Historical imports likely used `--file` without specifying the source.

**Recommended Fix:**
1.  Make `--url` mandatory for manual imports, OR
2.  Allow `--source-url` as an explicit metadata argument when importing from a local file.

### D. "Semicolon Actors"
**Root Cause:**
Direct result of the comma-only splitting logic. Since `;` isn't a comma, the entire string `Org A; Org B` is treated as one name.

**Recommended Fix:**
Add `;` to the split delimiters in the enhanced `split_attendees` function.