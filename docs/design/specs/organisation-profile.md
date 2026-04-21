# Organisation/Company Profile — Design Spec

**Date**: 2026-04-13
**Status**: Phase 2a Implemented, Phase 2b Planned
**Author**: Claude + Warren
**Audit**: Completed 2026-04-13 — AstraZeneca (#25949), HSBC (#27467)
**Constraints**: Completed 2026-04-13 — 2 backend changes required

## Overview

The organisation profile answers: **"How is this company trying to influence politics — through lobbying, meetings, and money?"**

Organisations are the mirror image of politicians. A politician page asks "who's influencing this person?" An organisation page asks "who is this company influencing, and through what channels?" The data profile is typically: many meetings with ministers, some lobbying agency relationships, rarely donations (companies can't donate directly to politicians in the UK, but can to parties).

The page serves three reader types:
1. **Journalist** looking for patterns — which departments does this company target? How many different ministers?
2. **Researcher** checking a specific relationship — did AstraZeneca meet the Health Secretary?
3. **Casual browser** who clicked a company name from a meeting row — what else has this company been up to?

## What's Changing (from current implementation)

The current page uses the same layout as politician profiles but communicates the wrong story. The collapsed meeting summaries show co-attendees instead of ministers, there's no headline stat, and the section label is generic.

### Phase 2a (do now — fixes every org page)

| Change | Type | Priority |
|--------|------|----------|
| Collapsed meeting summaries: show ministers, not co-attendees | Frontend | **Critical** — currently misleading |
| Adaptive headline stat (meetings or lobbying, not donations) | Frontend | **High** — header is empty |
| Classification-based section label ("COMPANY" not "ORGANISATION") | Frontend | **High** — adds specificity |
| Stats strip: "with X ministers" context | Backend + Frontend | **High** — needs new annotations |
| Add `unique_ministers_met_count` + `meeting_attendance_count` to API | Backend | **High** — required for stats |
| Bump meetings limit to 300 | Frontend | **Low** — covers 99%+ of orgs |

### Phase 2b (follow-up — Companies House interconnectedness)

| Change | Type | Priority |
|--------|------|----------|
| Add `?direction=members` to memberships endpoint | Backend | **Medium** — enables Key People list |
| New `/cross-connections/` endpoint with `Exists` annotations | Backend | **Medium** — enables political connection highlights |
| Key People section (directors/PSCs below timeline) | Frontend | **Medium** — base interconnectedness |
| Cross-connections highlight (directors with political activity) | Frontend | **High** — the interconnectedness story |

## Layout & Hierarchy

### Grid Structure
Same container as politician profile: `max-w-[1400px] mx-auto px-6`

### Content Zones (top to bottom)

1. **Section Label** — Classification-derived: "COMPANY", "PLC", "TRADE BODY", etc.
2. **Profile Header** (~180px) — Name, classification detail, headline stat (meetings or lobbying count)
3. **Stats Strip** (~80px) — Meeting count with minister/department context, lobbying count
4. **Timeline** (variable) — Year-grouped meetings, consultancies, and any donations

### Section Label Mapping

| API classification | Display label |
|-------------------|---------------|
| `Private Limited Company` | COMPANY |
| `Public Limited Company` | COMPANY |
| `PLC` | COMPANY |
| `Company` | COMPANY |
| `Lobbying Agency` | LOBBYING AGENCY |
| `Political Party` | POLITICAL PARTY |
| `Trade Union` | TRADE UNION |
| `Unincorporated Association` | ORGANISATION |
| `null` / unknown | ORGANISATION |

### Responsive Behavior
Same as politician profile — no structural changes needed.

## Data Communication

### Page-Level Story

**"AstraZeneca attended 254 ministerial meetings across multiple departments and hired 15 lobbying agencies — a company with systematic, multi-channel access to government."**

For HSBC: **"HSBC attended 197 ministerial meetings — predominantly roundtables with the Treasury and Business departments alongside other major banks."**

The story for an org page is always about **access and channels** — not about money (orgs rarely donate directly to politicians).

### Element-by-Element Interrogation

#### Header: Name + Classification + Headline Stat

**Intent**: "What is this entity, and what's the scale of its political engagement?"

**Current problem**: The header right side is empty because `total_received` is £0 for most companies. The story is meetings + lobbying, but those numbers are buried in the stats strip.

**Fix**: Adaptive headline stat. Priority order:
1. If `meeting_attendance_count > 0`: show meeting count as headline (e.g. "254" / "MEETINGS")
2. Else if `consultancies_as_client > 0`: show lobbying count (e.g. "15" / "LOBBYING AGENCIES")
3. Else if `total_received > 0`: show total received
4. Else if `total_donated > 0`: show total donated
5. Else: no headline stat

For AstraZeneca: **"254 MEETINGS"** at 4rem Zodiak. This immediately communicates the scale.

**Does the visual weight match?** Yes — the meeting count is the single most important number for understanding a company's political engagement. Placing it at the same visual weight as £1.3m for Badenoch is correct — they're both the headline story.

**Classification detail**: Below the name, show the full classification ("Private Limited Company") in `text-sm text-ink-muted`, similar to how party name appears on politician pages. This grounds the entity — the reader knows HSBC is a PLC, not a charity or trade body.

#### Stats Strip

**Intent**: "Quick inventory of this company's influence channels."

**Current problem**: Shows "272 MEETINGS" and "15 LOBBYING RELATIONSHIPS" — but doesn't communicate who the meetings were with. "254 meetings with 47 ministers across 12 departments" tells a much richer story than "254 meetings".

**Stats to show** (only non-zero, in order):
1. Meetings: **"254"** / "meetings with **47** ministers" — requires `unique_ministers_met_count` from API
2. Lobbying: **"15"** / "lobbying agencies hired"
3. Donations received (if any): **"X"** / "donations from X donors"
4. Donations made (if any): **"X"** / "donations made"

#### Collapsed Meeting Summary — CRITICAL FIX

**Intent**: "At a glance: who in government does this company have access to?"
**Aesthetic**: **Annotated Branching**. Use thin leader lines connecting the minister names to the meeting counts. Use **Marginalia** (small italic notes) in the right margin of the summary to indicate the "Ministry Context" (e.g., *Predominantly Treasury access*).

**Current failure**: Shows co-attendees ("Barclays 30 meetings, Lloyds 20 meetings"). This tells the reader which banks attend the same roundtables — not useful. The reader wants: "Chancellor of the Exchequer 15 meetings, Secretary of State for Business 8 meetings" — **which ministers** has this company met?

**Fix**: When `actor.actor_type === 'organization'`, build `topMeetingOrgs` from `meeting.minister` instead of `meeting.attendees`:

```typescript
// In buildYearGroups(), for org pages:
if (actor.actor_type === 'organization') {
  // Count ministers met (not co-attendees)
  if (m.minister && m.minister.id !== actor.id) {
    const ministerKey = `${year}-minister-${m.minister.id}`;
    const existing = meetingOrgCounts.get(ministerKey);
    if (existing) {
      existing.count++;
    } else {
      meetingOrgCounts.set(ministerKey, {
        name: m.minister.name,
        id: m.minister.id,
        count: 1
      });
    }
  }
} else {
  // Existing logic: count attendees for politician pages
  // ...
}
```

The summary then reads: "35 meetings with 12 ministers" and lists:
- **Greg Clark** — 8 meetings
- **Anna Soubry** — 5 meetings
- **Claire Perry** — 4 meetings
- ...

Each minister name linked to their profile. This answers "who in government gives this company access?"

**Co-attendees as secondary context**: The co-attendee data (Barclays, Lloyds, Santander appearing alongside HSBC) is still valuable — it reveals the company's **peer group** and whether meetings are 1-on-1 access or industry roundtables. Show this as a secondary line below the minister-focused summary:

```
65 meetings with 12 ministers                    SHOW ALL 65 ▸
  Greg Clark                    8 meetings
  Anna Soubry                   5 meetings
  Claire Perry                  4 meetings
  ...
  ─────────────────────────────────────────
  Frequently with: Barclays, Lloyds Banking Group, Santander, Natwest
```

The "Frequently with" line shows the top 3-4 co-attendees as a comma-separated list (linked where IDs exist). This preserves the peer group signal without it dominating the summary. It also communicates meeting type — many co-attendees = roundtable, few = direct access.

**Label**: "with X ministers" as primary, "Frequently with: ..." as secondary.

#### Expanded Meeting Rows

**Intent**: "Each meeting: what was discussed, which minister, which department, who else was there."

**Current state**: Already works well for org pages. Minister name appears first (linked), then co-attendees, then department. Purpose text is prominent.

**One improvement**: On org pages, the minister and department are the most important pieces of context (not the co-attendees). Consider showing the minister name more prominently — perhaps as the lead element instead of the purpose text. Or add the minister name to the left date column as context, similar to "as Leader of the Conservative Party" on politician pages.

**Verdict**: Expanded rows are functional. The collapsed summary is the critical fix.

#### Consultancy Rows

**Intent**: "Which lobbying agencies has this company hired, and when?"

**Current state**: Shows "DevoConnect Consultancy" with date ranges. Agency names are linked. For AstraZeneca, this shows 15 lobbying relationships clearly.

**Works well. No changes needed.**

#### Staff With Political Ties (cross-connections org→person)

**Intent**: "Who runs this company, and do any of those people have their own political connections?"

This is the **core interconnectedness opportunity** for org profiles — the mirror of "Corporate Connections" on politician pages. Companies House enrichment linked 51,157 orgs to their directors and PSCs. The question the reader is really asking is not just "what meetings did AstraZeneca attend?" but "who are the people behind AstraZeneca, and are they personally connected to the political system?"

**Data source**: `GET /api/v2/actors/{id}/cross-connections/` — returns directors/lobbyists/members of an org who have political activity (donations, meetings, parliamentary roles). The same endpoint that serves "Corporate Connections" on person pages, but in the org→person direction.

**Data from the database**:
- 1,214 orgs have members with political activity
- 62,747 Director memberships, ~8,000 PSC memberships across 15,152 enriched orgs
- ~3% of enriched companies have a director with direct political connections — small but high-signal

**Placement**: Between the profile header section and stats strip — same position as "Corporate Connections" on politician pages. Consistent cross-profile-type pattern.

**Design**:
```
STAFF WITH POLITICAL TIES

● Phil Kennedy — Lobbyist
  Former MP: Member of Parliament for Southwark · Donated £12,000 to politicians

● Martha Levy — Director
  Attended 3 ministerial meetings
```

**Elements per entry**:
- Person name: `font-display font-semibold text-sm`, linked to `/person/{person.id}`
- Role: `text-xs text-ink-muted ml-1.5` (Director, Lobbyist, PSC)
- Activity summary: `text-xs text-ink-light mt-0.5` — dot-separated list of:
  - `Former MP: {first parliamentary role}` (if parliamentary_roles)
  - `Donated £{amount} to politicians ({count} {pluralize(count, 'donation')})` (if donation_count > 0)
  - `Attended {count} ministerial {pluralize(count, 'meeting')}` (if meeting_count > 0)

**Styling**: Same `pl-3 border-l-2 border-accent/30` left-border treatment as politician "Corporate Connections". Consistent pattern across all profile types.

**Data quality filter** (backend): The cross-connections endpoint excludes:
- Names with fewer than 2 words (catches "Councillor", "Silva", "Dark")
- Names matching known role titles ("Councillor", "Director", "Secretary", etc.)
This prevents garbage data from appearing in the high-signal section.

**States**:
- No cross-connections: Section hidden entirely
- Connections exist: Show all (typically 1-20, no pagination needed)

**Key People list**: The existing Key People section (lines 225-238 of `[id].astro`) shows directors/PSCs as a simple linked list in the header. "Staff With Political Ties" is the elevated subset — directors who have their own political activity. Both sections can coexist: Key People shows everyone, Political Ties highlights the signal.

### Data Display Rules

Same as politician profile, plus:
- **Classification**: Full text ("Private Limited Company"), not abbreviated
- **Meeting label on summaries**: "with X ministers" (not "with X organisations") for org pages
- **Lobbying label**: "lobbying agencies hired" (clarifies direction — the org is the client)

### Interconnectedness

| Entity | Location | Status |
|--------|----------|--------|
| Minister names (expanded rows) | Meeting rows | ✅ Working |
| Minister names (collapsed summary) | Summary top 5 | ❌ **FIX** — show ministers, not co-attendees |
| Co-attendee names (expanded rows) | Meeting rows | ✅ Working |
| Lobbying agency names | Consultancy rows | ✅ Working |
| Staff with political ties | Cross-connections section | ❌ **Ready** — endpoint exists, needs data quality filter |
| Key People (directors/PSCs) | Header section | ✅ Working |
| Department names | Meeting rows | ❌ Blocked on department pages |

### Empty & Edge Cases
- **No meetings, no lobbying, no donations**: "No recorded activity for this organisation." (rare — most orgs in the DB have some activity)
- **Only meetings, no lobbying**: Omit lobbying from stats strip. Timeline shows meetings only.
- **Only lobbying, no meetings**: Lobbying count as headline stat. Timeline shows consultancy rows.
- **Very high meeting count (300+)**: Bump frontend limit to 300. Show "Showing 300 of 450 events" with note.

## Copy & Content

### Headlines & Labels
- **Section label**: Classification-derived (see mapping table above)
- **Classification detail**: Full classification text below name, `text-sm text-ink-muted`
- **Stats labels**: "MEETINGS WITH X MINISTERS", "LOBBYING AGENCIES HIRED"
- **Collapsed meeting summary label**: "X meetings with X ministers" (not "X organisations")

### Tone
Same as politician profile — authoritative, neutral. "AstraZeneca" not "Big Pharma".

## Backend Changes Required

### 1. Actor Detail — Org-specific annotations

Add alongside existing annotations in `ActorDetailView.get_queryset()`:

```python
# Count of meetings attended (as attendee, not minister)
meeting_attendance_count_sq = MeetingAttendee.objects.filter(
    Q(actor_id=OuterRef('pk')) | Q(canonical_actor_id=OuterRef('pk'))
).values('actor_id').annotate(
    cnt=Count('meeting', distinct=True)
).values('cnt')

# Unique ministers met (as attendee)
unique_ministers_met_sq = MeetingAttendee.objects.filter(
    Q(actor_id=OuterRef('pk')) | Q(canonical_actor_id=OuterRef('pk'))
).values('actor_id').annotate(
    cnt=Count('meeting__minister', distinct=True)
).values('cnt')
```

Add to serializer: `meeting_attendance_count`, `unique_ministers_met_count`

### 2. Cross-Connections — Data Quality Filter

**File**: `api/v2/views.py` — `ActorCrossConnectionsView`

The existing endpoint already works for org→person direction. Add data quality filter to the SQL:
```sql
AND array_length(string_to_array(trim(om.name), ' '), 1) >= 2
AND lower(trim(om.name)) NOT IN ('councillor', 'director', 'secretary', 'minister', 'sir', 'lord', 'dame')
```

This is part of the universal cross-connections upgrade — the same endpoint now handles both org→person and person→org directions. See politician-profile.md for the person→org spec.

## Audit Findings (2026-04-13 — HSBC #27467)

### Spec vs Design System Gaps
- **Sparse layout for data-rich entity**: HSBC has 197 meetings with 66 ministers across multiple departments, but the page feels underweight. No sidebar, no annotations, no supplementary context. The "Density Without Clutter" principle is underdelivered.
- **No department dimension**: Stats strip says "66 ministers" but not "across X departments". Adding department count would tell the multi-channel access story the spec describes.
- **Cross-connections data gap (not code gap)**: All 10 HSBC directors have zero donations and zero meetings — "Staff With Political Ties" correctly hidden. The cross-connections endpoint works, there's just no signal for this entity.
- **Vintage natural history aesthetic underdelivered**: Typographically correct but lacks dense/layered/annotated feel. The meeting summaries are the most successful element.

### Accessibility Issues
- Collapsed meeting summary buttons have very long accessible names (entire content as button text) — disorienting for screen readers
- "Key People" and "Top Clients" section labels use `<p>` not headings — screen readers can't navigate to them
- Stats strip items lack semantic grouping

### Backend Assessment
- Existing org→person cross-connections query works but needs data quality filter (name word-count, role-title exclusion)
- Entity resolution (`COALESCE(canonical_entry_id, id)`) not used in current query — should be added
- No new endpoints needed for HSBC-type pages

## Revision History

| Date | Change |
|------|--------|
| 2026-04-13 | Initial spec from audit + constraints analysis |
| 2026-04-13 | Updated cross-connections to universal pattern, added audit findings from HSBC #27467. |
