# Lobbying Agency Profile — Design Spec

**Date**: 2026-04-13 (updated 2026-04-13)
**Status**: Phase A+B Implemented, Phase C Planned (data quality fixes, Political Connections redesign)
**Author**: Claude + Warren
**Audits**: FTI Consulting (#26179, 1,390 clients), PLMR (#27613, 1,186 clients), Hanover Communications (#26415, 1,396 clients), Open Road (#27450, 61 clients)

## Overview

The lobbying agency profile answers: **"Who hires this agency to lobby government, and who does the lobbying?"**

Unlike company profiles (meetings-focused) or politician profiles (donations-focused), a lobbying agency's story is its **client list** — the companies paying it to influence government. The secondary story is its **people** — the lobbyists on its register, especially those with political connections (former MPs, donors, meeting attendees).

## What's Been Done (Phase A — Critical Fixes)

| Change | Status |
|--------|--------|
| Section label: detect "LOBBYING AGENCY" from consultancy count | ✅ Done |
| Headline stat: "1,390 CLIENTS" (not "10 MEETINGS") | ✅ Done |
| Consultancy rows: show client name, not self-referencing agency name | ✅ Done |
| Consultancy label: "Client" on agency pages, "Consultancy" on client pages | ✅ Done |
| Stats strip: directional label "clients" | ✅ Done |
| Consultancy fetch limit: 50 → 200 | ✅ Done |

## What's Planned (Phase B — Client List Hero & Lobbyists)

### Client List as Hero Element

The timeline of individual consultancy rows doesn't work for agencies with 1,000+ clients. The agency page needs a **client list component** — a ranked, searchable list of clients as the primary view.

**Design**: Below the header/stats strip, before the timeline:
- **Aesthetic**: **Specimen Catalogue**. Ranked by number of engagement periods (not alphabetical). Use rank numerals as specimen IDs.
- Each client linked to their profile
- Client's political activity shown inline with **Leader Lines**: "AstraZeneca — 254 meetings, 15 agencies" 
- Requires new aggregate endpoint: `GET /api/v2/actors/{id}/agency-clients/` returning clients with activity stats

### Lobbyists Section

**Aesthetic**: **Bridge Humans**. Highlight lobbyists with political ties (former MPs, donors) using the **Copper** (`#B87333`) node color for their names or a subtle copper halo. Use **Marginalia** to explain the connection (e.g., *Former MP for Southwark*).

**Data available**: FTI Consulting has **233 registered lobbyists** via Membership records with `role='Lobbyist'`. Across all agencies: 12,554 lobbyist records, 9,482 unique people, 265 agencies.

**Interconnectedness opportunity**:
- **18 lobbyists are also MPs** (or former MPs) — revolving door
- **26 lobbyists have donation records** — political donors who are also lobbyists  
- **29 lobbyists attended ministerial meetings** — direct government access

**Design**: "LOBBYISTS" section in the header (similar to Key People on company pages), with political connections highlighted:
```
LOBBYISTS (233 registered)

● Phil Kennedy — also: MP for Southwark (2010-2015), donated £12k to Labour
● Martha Levy — also: attended 3 ministerial meetings
  Alex Burchill · Juliet Bootle · Samuel Betz · Harriet Davies · ...
  + 225 more
```

**Data quality blocker**: Lobbyist names are concatenated ("Harriet Davies Stephen Day" = 2 people in 1 record). Needs splitting before individual lobbyist profiles are useful. Documented in `docs/CURRENT_STATE.md`.

**Backend requirements:**
1. Memberships endpoint already works for org direction (returns lobbyists)
2. New cross-connections endpoint or annotation for lobbyist political activity
3. Name splitting for concatenated lobbyist records (data cleanup)

### Consultancy Collapse/Grouping

With 200 consultancy rows loaded, the timeline is still long. Should collapse like donations/meetings when > threshold. Group by year, show top clients in summary.

## Data Communication

### Page-Level Story

**"FTI Consulting represents 1,390 clients lobbying the UK government — from AstraZeneca to Shell to Mastercard — and employs 233 registered lobbyists including former MPs."**

The headline number (1,390 clients) communicates scale. The client list communicates breadth. The lobbyist section communicates the human infrastructure of lobbying — and the revolving door between politics and lobbying.

### Key Interconnectedness Chains

1. **Agency → Client → Ministers met**: FTI Consulting → AstraZeneca → 254 meetings with 52 ministers
2. **Agency → Lobbyist → Political history**: FTI Consulting → Phil Kennedy → former MP, donated to Labour
3. **Agency → Client → Other agencies**: FTI Consulting → AstraZeneca → also hires DevoConnect, Edelman, Portland Communications

## Phase C: Data Quality & Political Connections Redesign

### Audit findings (2026-04-13): Hanover Communications & Open Road

Both agency pages share the same structural issues. The frontend is working correctly — the problems are in the data and in how the Political Connections section is designed.

### Issue 1: Political Connections Section (Redesign Required)

**Current behavior**: A "POLITICAL CONNECTIONS" sub-section appears nested inside the Registered Lobbyists block. It lists org members who have political activity (donations, meetings, parliamentary roles) via the `/cross-connections/` endpoint.

**Problems found across both audits:**

| Problem | Hanover (#26415) | Open Road (#27450) |
|---------|------------------|-------------------|
| Garbage names | "Councillor" (role as name, id:155332) | "Silva" (surname only, id:34110) |
| Confusing placement | Nested inside lobbyists block, reads as a footnote | Same |
| Vague label | "Political Connections" — what kind? | Same |
| Misleading role labels | "(Member)" is a fallback, not informative | "(Lobbyist)" correct but "1 meetings" grammar |
| Grammar | — | "1 meetings" (should be singular) |
| Thin signal | 2 of 771 members flagged | 1 of 177 members flagged |

**Redesign approach** (part of the Universal Political Connections upgrade — see also politician-profile.md "Corporate Connections" and organisation-profile.md "Staff With Political Ties"):

1. **Move out of the lobbyists block** — Its own section between header and client list, using the same placement and styling as all other profile types. Label: **"Staff With Political Ties"** (consistent with org pages).

2. **Data quality filter in the API** (backend): The `/cross-connections/` endpoint excludes:
   - Names with fewer than 2 words (catches "Councillor", "Silva", "Dark", "Forster")
   - Names matching known role titles (`Councillor`, `Director`, `Secretary`, etc.)

3. **Grammar**: Use `pluralize()` helper throughout — "1 meeting" not "1 meetings", "1 donation" not "1 donations".

4. **Contextual framing**: Activity summary as dot-separated list:
   - `Former MP: {first parliamentary role}` (if parliamentary_roles)
   - `Donated £{amount} to politicians ({count} {pluralize(count, 'donation')})` (if donation_count > 0)
   - `Attended {count} ministerial {pluralize(count, 'meeting')}` (if meeting_count > 0)

5. **Consistent styling**: Same `pl-3 border-l-2 border-accent/30` left-border treatment, `section-label` header, `font-display font-semibold text-sm` names — identical pattern to politician "Corporate Connections" and org "Staff With Political Ties".

### Issue 2: Concatenated Names (Data Import Bug)

This is a systemic import issue affecting both lobbyist names and client organisation names.

**Lobbyist names** (from APPC/PRCA register import):
- "Georgia Hunt Annette Jack" = Georgia Hunt + Annette Jack (2 people)
- "Mia Ayres Henry Berridge" = Mia Ayres + Henry Berridge
- "Alexa Knight Graham Mc" = Alexa Knight + Graham Mc??? (broken at line break)
- Surname-only: "Dark", "Forster", "Dunn", "Davies", "Millan"

**Client names** (from consultancy register import):
- "AB Agri AbbVie" = AB Agri + AbbVie (animal feed + pharma)
- "Google HSBC" = Google + HSBC
- "Asda DeepMind Technologies" = Asda + DeepMind
- "CALM Carnival" = CALM (charity) + Carnival (cruise line)
- "London Stock Exchange Group Meta" = LSEG + Meta

**Also case-variant duplicates:**
- "DeepMind Technologies" (id:46795) vs "DEEPMIND TECHNOLOGIES LIMITED" (id:132707 AND id:27466)

**Impact on the page**: The "Top Clients by Political Activity" section shows concatenated entities with 0 meetings and 0 donations, ranked alongside real clients. Open Road's client list is ~50% garbage.

**Fix required**: This is a data import bug in the management commands that parse the APPC/consultancy register. Client names and lobbyist names on the same register line are being concatenated instead of split. Fix needs:
1. Identify the import command(s) responsible
2. Fix the name-splitting logic
3. Re-import to split existing concatenated records
4. Run entity resolution to merge case-variant duplicates

**Frontend mitigation** (until data is fixed): The client list endpoint could filter out clients with 0 total political activity (0 meetings + 0 donations + 0 other_agencies) to hide the garbage entries. This would clean up Open Road's client list from 11 → ~3 real entries.

### Issue 3: Grammar (Singular/Plural)

Multiple places use plural form with count of 1:
- Stats strip: "meetings with 1 ministers" → "meeting with 1 minister"
- Political Connections: "1 meetings" → "1 meeting"
- Timeline: "1 engagements" → "1 engagement"

**Fix**: Add a simple pluralize helper and use it in:
- `[id].astro` stats strip labels
- `[id].astro` Political Connections display
- `ActorTimeline.svelte` engagement count labels

### Issue 4: Timeline Pagination

Both pages show a fraction of total events with no way to load more:
- Hanover: "Showing 51 of 2,168 events"
- Open Road: "Showing 50 of 238 events"

The "Showing X of Y" text is informative but the reader has no way to see more. This is documented in the actor-profile.md spec as "Load more" but not yet implemented.

## Audit Findings (2026-04-13 — Hanover Communications #26415)

### Data Quality Issues `[upstream]`
- **"Councillor" as person name** (id:155332): Role title imported as actor name. Appears in "Staff With Political Ties" linking to a garbage profile. Root cause: import parser. Fix: data quality filter in `ActorCrossConnectionsView` API (exclude names < 2 words, role-title names).
- **Concatenated lobbyist names**: "Mia Ayres Henry Berridge" (2 people), "Lily Lofty Mark Mac" (2 people). Root cause: APPC register import concatenates names on same line. Fix: import command name-splitting.
- **Concatenated client names**: "AB Agri AbbVie", "London Stock Exchange Group Meta", "CALM Carnival". Root cause: consultancy register import. Appears in timeline consultancy rows.
- **Single-word lobbyist surnames**: "Forster", "Dunn", "Malone" — incomplete records from import.
- Frontend renders what API returns — these issues need upstream fixes, not client-side filtering.

### Spec vs Design System Gaps
- **Client list lacks taxonomic feel**: 583 clients shown as flat ranked list. Design system calls for classification/specimen-style treatment. Could clients be grouped by sector?
- **Lobbyist links to garbage profiles**: Every lobbyist name links to a concatenated-name profile. Link destination is useless. `[upstream]` — fix requires name splitting in import.
- **No client search/filter**: 583 clients with only 20 shown and no search.
- **51 of 2,168 events shown**: No load more. Dead end for exploration.

### Accessibility Issues
- Section labels ("Staff With Political Ties", "Top Clients") use `<p>` not headings — same issue as org pages.

### Grammar
- `pluralize()` confirmed working for this actor's data (1 meeting → singular correct).

## Revision History

| Date | Change |
|------|--------|
| 2026-04-13 | Phase A: critical fixes (label, headline, counterparty display). Phase B spec written. |
| 2026-04-13 | Phase C spec: Political Connections redesign, concatenated names diagnosis, grammar fixes. Audited Hanover (#26415) and Open Road (#27450). |
| 2026-04-13 | Updated Phase C to universal cross-connections pattern, added audit findings from Hanover #26415. |
