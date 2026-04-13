# UX Implementation Plan

**Date**: 2026-04-12
**Status**: Living document
**Core principle**: Interconnectedness — every entity name is a doorway into that entity's web of connections

---

## UX Process

Every page goes through a 5-phase design workflow before it's considered done. No phase should be skipped.

| Phase | Skill | What it produces | Gate |
|-------|-------|-----------------|------|
| 1. Understanding | `/ux-audit` | Screenshots + structured audit report against design system | Baseline established, issues catalogued |
| 2. Feasibility | `/ux-constraints` | Technical analysis of what's possible in Astro+Svelte+D3+Tailwind | Approach chosen, blockers identified |
| 3. Design | `/ux-design` | Written spec in `docs/design/specs/` — layout, components, data communication, copy | Spec approved by Warren |
| 4. Build | `/ux-mockup` | Implemented page + Playwright screenshots validated against spec | All spec sections pass |
| 5. Polish | `/ux-refine` | Design system compliance fixes, interconnectedness audit, responsive check | No Fail items in audit |

**Key rules:**
- Design is written before code. `/ux-design` produces the spec. `/ux-mockup` builds to that spec.
- Every audit includes an **Interconnectedness check** — any entity name without a link to a useful page is a failure.
- Don't link to empty pages. If a destination page doesn't exist yet, keep the name as plain text and note it in this plan.

---

## Page Hierarchy & Build Order

The site has a clear information architecture. Pages are ordered by importance — the most-linked, most-visited pages come first.

### Actor Types & Profile Variants

The `/person/[id]` route currently shows the same layout for every actor. But actors fall into distinct archetypes with very different data profiles. Each needs its own design treatment.

**Data from the database (155k actors with activity):**

| Archetype | Classification(s) | Count | Primary data | What the page should communicate |
|-----------|-------------------|-------|--------------|----------------------------------|
| **Politician** | Person (with memberships) | ~4,500 MPs/Lords | Donations received, meetings, roles | "What money and access flowed to this person, and in which roles?" |
| **Donor** | Person or Company/Unincorporated Assn/Trust/etc. | ~35,000 | Donations made, key people | "Who does this person/entity fund, and how much?" |
| **Political Party** | Political Party | 190 | Donations received (56k records!) | "Where does this party's money come from?" |
| **Lobbying Agency** | Lobbying Agency | 72 | Client list (consultancies) | "Who hired this agency to lobby government?" |
| **Lobbying Client** | Private Ltd Co / PLC / Company | ~8,000 | Agencies hired, meetings, donations | "How is this company trying to influence politics — through lobbying, meetings, and money?" |
| **Meeting Attendee Org** | External Organization | ~18,500 | Meetings attended | "Which ministers met this org, when, and why?" |
| **Government Department** | Government Department / Legislature | 15 | Meetings hosted | "Who gets access to this department?" — currently empty pages |
| **Director / PSC** | Person (via Companies House) | ~35,000 | Company connections | "What companies is this person connected to, and do those companies donate/lobby?" |
| **Trade Union** | Trade Union | 421 | Donations made (11k), meetings | "How much does this union spend on political donations and who do they support?" |

**The key insight**: a company like HSBC (PLC) has 197 meetings and 6 lobbying relationships but zero donations. A person like Kemi Badenoch has 111 donations received and 122 meetings. A lobbying agency like FTI Consulting has dozens of clients but no meetings of its own. The profile page should adapt to show what matters for each type.

**Design approach**: Rather than building separate pages per type, the `ActorTimeline` and profile header should adapt based on the actor's data profile:
- **Header**: Show classification-appropriate label ("POLITICIAN" / "LOBBYING AGENCY" / "POLITICAL PARTY" / "TRADE UNION" / "COMPANY")
- **Headline stat**: Show the most meaningful number (total received for politicians, total donated for donors, client count for agencies, meeting count for orgs)
- **Timeline**: Already adapts — shows only sections with data. But could be enhanced with type-specific features (e.g., client list for agencies, party funding breakdown for parties)

**Each archetype needs its own `/ux-design` spec** before refinement work begins.

### Tier 1: Core (built, needs refinement)

These pages are the backbone. They exist, have data, and are functional. They need design system polish, interconnectedness passes, and actor-type-specific design work.

| Page | Route | Status | Design spec | Next action |
|------|-------|--------|-------------|-------------|
| **Homepage** | `/` | Built, data-rich | None yet | `/ux-audit` → `/ux-design` |
| **Actor Profile: Politician** | `/person/[id]` | ✅ Full UX pass complete | `politician-profile.md` | Party dot, linked summaries, contextual stats, a11y fixes |
| **Actor Profile: Organisation** | `/person/[id]` | ✅ Phase 2a complete | `organisation-profile.md` | Ministers in summaries, headline stat, classification label, co-attendees |
| **Actor Profile: Lobbying Agency** | `/person/[id]` | ✅ Phases A+B done | `lobbying-agency-profile.md` | Phase C needed: Political Connections redesign, grammar fixes, client list filtering. Blocked on data import fix for concatenated names. |
| **Actor Profile: Political Party** | `/person/[id]` | ✅ Full funding view | `political-party-profile.md` | Done: Top donors, cross-funding of MPs, union/public separation, funding by type/year with expandable bars, progressive timeline loading |
| **Actor Profile: Trade Union** | `/person/[id]` | Not differentiated | None | `/ux-design` — needs donation recipients view |
| **Network Graph** | `/network` | Built, D3 force graph | None yet | `/ux-audit` |

### Tier 2: Navigation & Discovery (built, varying quality)

These pages help users find actors and explore the data. They need full design passes.

| Page | Route | Status | Design spec | Next action |
|------|-------|--------|-------------|-------------|
| **Directory** | `/directory` | Built, search + pagination | None yet | `/ux-audit` → `/ux-design` |
| **Analysis** | `/analysis` | Built, links to deep-dives | None yet | `/ux-audit` |
| **Parties** | `/parties` | Built, party donation data | None yet | `/ux-audit` → `/ux-design` |
| **Meetings** | `/meetings` | Built, department meetings | None yet | `/ux-audit` → `/ux-design` |
| **Lobbying** | `/lobbying` | Built, clients + dual influence | None yet | `/ux-audit` → `/ux-design` |

### Tier 3: New pages needed

These pages don't exist yet but are needed to complete the interconnectedness story.

| Page | Route | Why needed | Blocked on |
|------|-------|-----------|------------|
| **Department Profile** | `/department/[id]` | Aggregate all meetings across ministers in a department. Currently department names are unlinked because this page doesn't exist. | New API endpoint or frontend aggregation logic |
| **Search Results** | `/search` | Global search across all actors. Search box exists in nav but isn't wired up. | Search API endpoint |

### Tier 4: Static / Legal (done)

| Page | Route | Status |
|------|-------|--------|
| Privacy Policy | `/privacy` | Static, complete |
| Terms of Use | `/terms` | Static, complete |
| Data Access | `/data` | Static, complete |

### Recommended build order

**Phase 1: Foundation** (homepage + core profile)
1. **Homepage** — front door, sets expectations
2. **Actor Profile: Politician** — most linked-to page, spec exists (needs party fix)

**Phase 2: Actor type variants** (design specs first, then build)
3. **Actor Profile: Organisation/Company** — HSBC-style pages, meeting-heavy
4. **Actor Profile: Lobbying Agency** — client list as hero, e.g. FTI Consulting
5. **Actor Profile: Political Party** — funding breakdown, e.g. Conservative Party
6. **Actor Profile: Trade Union** — donation recipients, e.g. Unite

**Phase 3: Navigation & discovery**
7. **Directory** — primary search/browse tool, needs type filters
8. **Parties** → **Meetings** → **Lobbying** — analytical lenses
9. **Analysis** — hub page, refine last

**Phase 4: New pages**
10. **Department Profile** — unlocks department name linking
11. **Search Results** — unlocks the search box in the nav

For each: `/ux-audit` → `/ux-constraints` (if needed) → `/ux-design` → `/ux-mockup` → `/ux-refine`

For each: `/ux-audit` → `/ux-design` → `/ux-mockup` → `/ux-refine`

---

## Completed Work

### Interconnectedness: Actor Profile Links (2026-04-12)

All entity names on person/org profile pages now link to their actor profiles when an actor ID is available from the API.

**Files modified:**
- `frontend/src/components/ActorTimeline.svelte`
- `frontend/src/components/ActorProfile.svelte`

| Entity type | Status | Notes |
|-------------|--------|-------|
| Donor names (donations received) | Done (pre-existing) | Links to `/person/{donor.id}` |
| Recipient names (donations made) | Done (pre-existing) | Links to `/person/{recipient.id}` |
| Meeting attendee names (multi-attendee) | **Done** | `<a>` with `hover:text-accent` when `attendee.actor.id` exists |
| Meeting attendee names (single-attendee) | **Done** | No longer falls back to plain `organisation_met_raw`; uses linked attendee data |
| Minister names on org pages | **Done** | When viewing an org's meetings, the minister appears first, linked |
| Self-references filtered | **Done** | Org's own name removed from its meeting attendee lists |
| Consultancy agency/client names | **Done** | Links to `/person/{agency.id}` or `/person/{client.id}` |
| Department names | **Reverted** | Pages are empty — blocked on Department Profile page |
| Donor key people (directors/PSCs) | Not started | Needs API check for actor IDs |
| Summary row donor names (collapsed) | **Done** | `topDonors` linked with `<a>` tags (2026-04-13) |
| Summary row meeting org names (collapsed) | **Done** | Rebuilt from `attendees[]` data with actor IDs (2026-04-13) |

### Politician Profile: Full UX Pass (2026-04-13)

Audit → constraints → design → mockup for politician actor profile. Design spec: `docs/design/specs/politician-profile.md`

**Backend changes:**
- `ActorDetailView`: Added `unique_donors_count` and `unique_meeting_orgs_count` via `Subquery` + `Coalesce` (avoids cartesian join)
- `ActorMembershipsView`: Added `on_behalf_of` to `select_related` (N+1 fix)
- `ActorDetailSerializer`: Added new fields
- `MembershipDetailSerializer`: Added `on_behalf_of` field (party fix from earlier)

**Frontend changes (`ActorTimeline.svelte`):**
- Collapsed donor summary names now linked (`<a>` with hover:text-accent)
- Collapsed meeting summary rebuilt from `attendees[]` data (not `organisation_met_raw`)
- `<button>` → `<div role="button">` to allow nested links
- `focus-visible` outline on expand/collapse controls
- Year markers changed from `<span>` to `<h2>` for screen reader navigation

**Frontend changes (`[id].astro`):**
- Party colour dot next to party name (muted design system colours)
- Stats strip: "97 donations from 71 donors" / "107 meetings with 308 organisations"
- Fixed broken dynamic Tailwind class (`grid-cols-${n}` → conditional `class:list`)
- Party lookup fixed: `on_behalf_of.classification === 'Political Party'`

### Organisation Profile: Phase 2a (2026-04-13)

Audit → constraints → design → mockup for organisation actor profiles. Design spec: `docs/design/specs/organisation-profile.md`

**Backend changes:**
- `ActorDetailView`: Added `meeting_attendance_count` and `unique_ministers_met_count` via Subquery + Coalesce
- These complement the existing `unique_meeting_orgs_count` (for politicians) — orgs and politicians now have type-appropriate meeting stats

**Frontend changes (`[id].astro`):**
- Classification-based section label ("COMPANY" / "LOBBYING AGENCY" / "TRADE UNION" instead of generic "ORGANISATION")
- Full classification shown below name (e.g. "Public Limited Company")
- Adaptive headline stat: total_received → total_donated → meeting_attendance_count → consultancies_as_client → none
- Stats strip: "meetings with X ministers" for orgs, "meetings with X organisations" for politicians

**Frontend changes (`ActorTimeline.svelte`):**
- Org pages: collapsed meeting summaries show **ministers** (not co-attendees)
- "Frequently with" line shows top 4 co-attendees as secondary context (peer group signal)
- Self-name filtering in co-attendees (catches unresolved duplicate org records)
- `isOrg` flag at component scope drives all org-vs-politician branching
- Meetings limit bumped from 200 → 300

**Also completed:**
- Entity resolution Phase 1: 1,806 orgs linked by Companies House number (`resolve_org_duplicates --ch-only`)
- Data quality issues documented in `docs/CURRENT_STATE.md` (8 org-specific items)

### Layout: Horizontal Overflow Fix (2026-04-12)

- Grid column `1fr` → `minmax(0, 1fr)` prevents children expanding beyond container
- `overflow: hidden` on `.summary-content`, `.clickable-row`, `.timeline`
- `min-w-0` on summary row flex containers for proper truncation
- Verified: no overflow at 1440px or 375px

### Skills Updated (2026-04-12)

Interconnectedness principle added to `/ux-audit`, `/ux-design`, `/ux-mockup`.

---

## Blocked / Needs Backend Work

### ~~Party Affiliation on MP Pages~~ ✅ Fixed (2026-04-13)

Import was already correct (9,364 memberships with `on_behalf_of` populated). The issue was:
1. API serializer didn't expose `on_behalf_of` — added to `MembershipDetailSerializer`
2. Frontend checked `m.organization?.classification === 'Party'` — fixed to `m.on_behalf_of?.classification === 'Political Party'`

Party names now show on all MP pages (e.g. Starmer → "Labour", Badenoch → "Conservative").

### Department Pages

**Problem**: Department actor pages show "No recorded activity" because meetings belong to ministers, not departments.

**Fix needed:**
1. New page or API endpoint aggregating meetings by `department.id`
2. Show: all meetings, which ministers, top organisations
3. Re-enable department links in `ActorTimeline.svelte` and `ActorProfile.svelte`

---

## Next Steps (from 2026-04-13 homepage audit)

### 1. Homepage Interconnectedness Fix (Critical, Easy)

The API already returns actor IDs for meeting attendees, lobbying clients, and departments — but `index.astro` discards them and renders plain `<span>`. ~25 unlinked entity names on the homepage that have IDs available.

**Changes needed in `frontend/src/pages/index.astro`:**
- **Department meeting attendees** (line ~310): Change `<span>{attendee.name}</span>` → `<a href="/person/{attendee.actor.id}">{attendee.name}</a>`. Data already available: `attendee.actor.id`.
- **Lobbying client names** (line ~349): Change `<span>{client.name}</span>` → `<a href="/person/{client.actor.id}">{client.name}</a>`. Requires passing `actor.id` through in the data transform (line ~90).
- **Lobbying agency names** (line ~353): Currently just `client.agencies.join('·')` — no IDs available. API returns agency names as strings, not objects. **Needs API change** to return `{id, name}` objects from `/aggregates/top-lobbying-clients/`.
- **Department names** (line ~305): Have `department.id` but department pages are empty. Keep as plain text until Department Profile page exists (existing blocker).
- **Party bar chart** (line ~266): Could link to `/person/{party.id}`. Requires passing party ID through data transform.

### 2. Cache Homepage Stats Endpoint

`/aggregates/stats/` takes 1.4s — materialises 21k donor rows for concentration calc, no caching. Add Redis cache (5-min TTL) matching the `funding-summary` pattern in `api/v2/cache_utils.py`.

### 3. Fix Heading Hierarchy

Homepage has h1 → h3 → h4 → h5, skipping h2. Network section → h2, Deep Dive headings → h3, Methodology → h4.

### 4. Network Graph Loading State

5+ second "LOADING NETWORK DATA..." with no skeleton/placeholder. Add a skeleton that suggests the shape of the graph.

### 5. Network Graph Mobile Treatment

Force-directed graph with 100+ nodes is unusable at 375px. Options: hide on mobile with a "View on desktop" note, or provide an alternative (top connections list).

### 6. Write Homepage Design Spec

No `docs/design/specs/homepage.md` exists. The homepage is the most-visited page and has no spec. Create one following the `/ux-design` process.

### 7. Backend: Push Party Filter into SQL

`/aggregates/party-donations/` aggregates ALL recipients then filters to parties in Python. Push the `classification = 'Political Party'` filter into the SQL query.

### 8. Backend: Fix Lobbying N+1

`/aggregates/top-lobbying-clients/` runs a separate query per client to fetch agencies (10 extra queries at limit=10). Use a single query with window functions or prefetch.

### 9. Data Quality: Concatenated Entity Names [upstream]

"Crick Institute Eton College" is the #1 lobbying client on the homepage (18 agencies). It's two separate entities concatenated during GOV.UK meeting import. Also affects: "CEO (Vistry Group)", "Clarion Events College of Policing", "TJX Europe UK Chamber of Shipping". Fix belongs in `import_ministerial_meetings` — split multi-entity attendee strings.

### 10. Data Quality: Case-Variant Duplicates [upstream]

"AstraZeneca" (id:26122) and "Astrazeneca" (id:25949) both appear in lobbying clients. Entity resolution should catch case-variant duplicates. Add case-insensitive matching to `resolve_org_duplicates`.

---

## Planned Improvements

### Donor Key People Links
Small text below donation rows listing directors/PSCs is unlinked. Check if `donor_key_people` includes actor IDs.

### Organisation Meeting Grouping
On org pages, meetings could be grouped by department or minister for clearer access-pattern visibility.

### Mobile Optimisation
Meeting attendee lists with many names are dense at 375px. Consider "show more" pattern and verify touch target sizes.

### Universal Political Connections (2026-04-13)

Cross-connections are now a **universal feature** applied to all actor profile types. The `/cross-connections/` API endpoint is bidirectional:

| Actor type | Direction | Section label | Shows |
|-----------|-----------|---------------|-------|
| **Politician/Person** | person→org | "Corporate Connections" | Orgs this person directs that have political activity (lobbying, meetings, donations) |
| **Company/Org** | org→person | "Staff With Political Ties" | Directors/members with political activity (donations, meetings, parliamentary roles) |
| **Lobbying Agency** | org→person | "Staff With Political Ties" | Same as company, plus lobbyists with political ties |

**Data scale**: 29,374 people with politically-connected directorships. 1,214 orgs with politically-connected staff.

**Implementation**:
- Backend: Extend `ActorCrossConnectionsView` — detect actor type, run appropriate query, add `direction` field, add data quality filter (exclude names < 2 words, role-title names)
- Frontend: Direction-aware rendering in `[id].astro` with appropriate labels and detail lines
- Grammar: Use `pluralize()` throughout cross-connections display
- Styling: Consistent `pl-3 border-l-2 border-accent/30` treatment across all profile types

**Design specs updated**: `politician-profile.md`, `organisation-profile.md`, `lobbying-agency-profile.md`

**Partially blocked on data import fix** (affects org→person quality only):
- Concatenated lobbyist names: "Georgia Hunt Annette Jack" = 2 people in 1 record
- Concatenated client names: "AB Agri AbbVie", "Google HSBC" = separate companies merged
- Data quality filter mitigates but doesn't solve the root cause

### Donation Context Enrichment (2026-04-13)

Donation rows should show the **recipient's party and role at the time of the donation**. Currently, "Donated £25k to Robert Jenrick" doesn't tell you he was a Conservative leadership candidate. The context transforms a name into a story.

**Applies to**:
- **Donations-made rows** (donor profile pages): show recipient's party + role at donation date
- **Donations-received rows** (politician pages): the `activeRole` pattern already shows the page actor's own role — but showing the *donor's* party/role when the donor is also a politician adds value

**Constraints analysis** (2026-04-13):
- **Feasibility**: High. 1 extra query per page (batch membership lookup). No model changes.
- **Date field**: Use `COALESCE(accepted_date, received_date, reported_date)` — 99.5% coverage on `accepted_date`.
- **Party coverage**: 88% of person recipients have party via `Membership.on_behalf_of`.
- **Edge cases**: Dissolution gaps (use most recent prior), overlapping roles (prefer ministerial), org recipients (null — no party/role).
- **Key insight**: Party lives on the parliamentary membership's `on_behalf_of`, not on ministerial memberships. Must find the concurrent House of Commons membership for party even when showing a ministerial role.

**Backend changes** (`api/v2/views.py` + `api/v2/serializers.py`):
- Add `build_recipient_context(recipient_ids, donations)` helper — batch query memberships, date-range match
- Add `recipient_party` and `recipient_role_at_date` to `DonationDetailSerializer`
- Pass via `get_serializer_context()` on both donation views

**Frontend changes** (`ActorTimeline.svelte`):
- Donations-made rows: `{recipient.name} · {party dot} {party_name} · {role_at_date}`
- Reuse party colour dot from profile header
- Same visual treatment as existing `activeRole` context

**Design specs updated**: `politician-profile.md`

### Timeline Pagination / Load More

All non-party actor profiles show a capped subset of events (typically 50-51) with a "Showing X of Y events" note but no way to load more. Affects high-activity actors:
- Hanover Communications: 51 of 2,168 events shown
- Open Road: 50 of 238 events shown

The actor-profile.md spec already describes a "Load more" pattern but it's not implemented for non-party actors. Party pages now use progressive year-by-year loading (see below). Non-party actors still need client-side pagination in `ActorTimeline.svelte`.

### Party Profile: Progressive Timeline (2026-04-13)

Party pages now use **lazy year-by-year timeline loading**:
- `yearlyTotals` from the `funding-summary` endpoint provides summary data for all years (top 5 donors, totals, counts)
- Timeline renders all years immediately with collapsed summaries showing top donors and "+ X more donors"
- Clicking "Show all N ▸" fetches real donation data for that year from `/actors/{id}/donations-received/?received_after=YYYY-01-01&received_before=YYYY-12-31&limit=500`
- Real dates, real donation types (CASH, NON CASH, PUBLIC FUNDS, VISIT), key people annotations
- No more synthetic donation data with fake "15 Jun" dates

Also added:
- **Cross-Funding of MPs section** — dedicated section (like Public Funding) showing party donors who also fund individual MPs, with amounts and MP counts
- **Duplicate label fix** — "Political Party" no longer appears twice in header (section label + classification)
