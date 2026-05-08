# Homepage — Design Spec

**Date**: 2026-04-15
**Status**: Draft
**Author**: Claude + Warren
**Audit**: Completed 2026-04-15 (see audit report in conversation)

## Overview

The homepage is the front door to the investigation. It establishes the scope ("91,513 donations, £1.6bn"), shows the centrepiece visualisation (the minister network), and offers three lenses for deeper exploration (party funding, ministerial access, lobbying). Every entity name on the page is a doorway into the web of connections.

The page serves two audiences: journalists/researchers arriving from a link (need to immediately understand the scope and find something worth investigating), and returning users exploring the data (need quick navigation to specific actors or lenses).

## Layout & Hierarchy

### Grid Structure
- Container: `max-w-[1400px] mx-auto px-6`
- Asymmetric layouts: hero uses 8-col, deep dive uses 1+2 split
- Full-bleed for network graph only

### Content Zones (top to bottom)

1. **Hero** — Large headline + subhead establishing the investigation. ~200px.
2. **Stats Strip** — Three key metrics as typography. Border-y treatment. ~120px.
3. **Network Graph** — Full-width D3 force-directed minister network. ~800px.
4. **Top Recipients + Deep Dive** — 3-column split (1 col recipients, 2 col deep dive cards). Variable height.
5. **Methodology** — Source attribution. 1+3 column split. ~150px.
6. **Footer** — Links, legal. Handled by BaseLayout.

### Responsive Behaviour

- **Desktop (1440px)**: Full layout as described. Network graph at 1400×800.
- **Tablet (768px)**: Network graph shrinks but remains. Deep dive cards stack into single column below recipients.
- **Mobile (375px)**: Single column throughout. Network graph replaced with a simplified alternative (see below). Stats stack vertically. Deep dive cards full-width.

## Component Inventory

### Hero (Static Astro)
- **Purpose**: Establish the investigation — what it is, who it's about
- **Copy**: "The web of money and access in Westminster"
- **Subhead**: "Who funds British politics — and what do they get in return?"
- **No changes needed** from current implementation

### Stats Strip (Static Astro)
- **Purpose**: Communicate the sheer scale of the data
- **Data source**: `GET /api/v2/aggregates/stats/`
- **Elements**:
  - `91,513` — Donations tracked (tabular-nums)
  - `£1.6bn` — Total value declared
  - `312` — Dual-influence relationships → **change label** to "Donors who also lobby" or add `title` tooltip: "Entities that both donate to politicians and hire lobbyists"
- **States**:
  - Default: Numbers rendered from API
  - Loading: Show `—` placeholders
  - Error: Show `—` placeholders (fail silently)

### Minister Network (Svelte `client:visible`)
- **Purpose**: The centerpiece — show the web of financial connections between donors and ministers as an organic, taxonomic diagram
- **Aesthetic**: Use **stippled node halos** and thin, hand-drawn style edges.
- **Data source**: `GET /api/v2/aggregates/minister-network/`
- **Existing component**: `MinisterNetwork.svelte` — no changes to the component itself
- **Desktop**: Full interactive graph with hover/click/physics
- **Mobile (< 640px)**: **Hide the graph entirely**. Replace with:
  - A section heading "The Government Ministers Network"
  - A **static "Field Map" SVG** showing the central high-density cluster (non-interactive, provides the "Aha!" moment on 375px).
  - A brief explanatory paragraph
  - A "View interactive network →" link to `/network` (the full-page network)
- **Loading state**: Replace "LOADING NETWORK DATA..." with a **Taxonomic Skeleton**: a faint dot-cloud pattern on the parchment background with leader lines pointing to empty "Specimen" labels, plus "Cataloging connections..." text in ink-muted.

### Top Recipients (Static Astro)
- **Purpose**: League table of who benefits most from political donations — a ranked specimen list
- **Design**: Styled as a **Specimen Plate**. Use thin rule lines between rows and a prominent rank numeral in Zodiak bold.
- **Data source**: `GET /api/v2/aggregates/top-recipients/?limit=100` (filtered to persons client-side, sliced to 20)
- **Section label**: "Top Recipients" (accent red, uppercase)

### Deep Dive: Party Funding (Static Astro)
- **Purpose**: Show the dominance of Conservative funding and invite exploration
- **Changes**:
  - **Lithographic Bars**: Replace uniform bars with **hatched/stippled textures** mapped to party colors (e.g., Conservative #4A7BA7 with diagonal hatching).
  - **Link party names**: Each party name should link to `/party/{party.id}`. Requires passing party ID through the data transform.
- **Interconnectedness**:
  - Party names → `/party/{party.id}` (new)
  - Card → `/parties` ✅ (already working)

### Deep Dive: Ministerial Access (Static Astro)
- **Purpose**: Show which departments are most accessible to external influence, and who gets in
- **Design**: Use **Leader Lines** from the department name to the attendee list.
- **Data source**: `GET /api/v2/aggregates/department-meetings/?limit=5&top_attendees=3`

### Deep Dive: Lobbying Influence (Static Astro)
- **Purpose**: Show that major corporations hire multiple lobbying agencies to access government
- **Data source**: `GET /api/v2/aggregates/top-lobbying-clients/?limit=20`
- **Left column**: Section label, headline, editorial quote, "Explore lobbying →"
- **Right column**: Client list with agency count and agency names
- **Changes**:
  - **Link client names**: Change `<span>{client.name}</span>` to `<a href="/organisation/{client.actor.id}">{client.name}</a>`. API already returns `client.actor.id`.
  - **Link agency names**: Currently rendered as `client.agencies.join(' · ')` — plain strings with no IDs. **Requires API change**: `/top-lobbying-clients/` must return agencies as `[{id, name}]` objects, not strings. Then render each agency as `<a href="/organisation/{agency.id}">{agency.name}</a>` separated by ` · `.
  - Same card restructuring as Ministerial Access — left column links to `/lobbying`, right column has entity links.
- **Data quality `[upstream]`**: "Crick Institute Eton College" is two concatenated entities (#1 client, 18 agencies). "NATIONAL GRID PLC" is all-caps. These are import/entity resolution issues — render faithfully.
- **Interconnectedness**:
  - Client names → `/organisation/{client.actor.id}` (new)
  - Agency names → `/organisation/{agency.id}` (new, requires API change)
  - Card left column → `/lobbying` ✅

### Methodology (Static Astro)
- **Purpose**: Source attribution and editorial positioning
- **Layout**: 1+3 column split (label left, text right)
- **Changes**:
  - **Fix heading**: Change `<h5>` to `<h3>` to fix heading hierarchy
- **No interconnectedness needed** — this is editorial text

## Data Communication

### Page-Level Story

**"Billions of pounds flow between donors, lobbyists, and the politicians who govern Britain — and you can trace every connection."**

The homepage communicates this in layers:
1. **Scale** (stats strip): 91k donations, £1.6bn — this is huge
2. **Structure** (network graph): the connections form a dense web, not isolated transactions
3. **Who benefits** (top recipients): specific names and amounts — this is about real people
4. **Three lenses** (deep dive cards): money flows through parties, access through meetings, influence through lobbying agencies

A reader scanning for 5 seconds should absorb: "This tracks billions in political money. I can see who gets it."

### Element-by-Element Intent

| Element | Communicative Intent | Visual Treatment |
|---------|---------------------|-----------------|
| Hero headline | "This is an investigation into political influence" | Zodiak 6xl/7xl, tight leading, maximum visual weight |
| Hero subhead | "The question driving the investigation" | Satoshi xl, ink-light, relaxed leading |
| Stats: 91,513 | "The sheer volume of financial transactions we track" | Zodiak stat-figure (4rem), tabular-nums, centered |
| Stats: £1.6bn | "The total scale of money flowing into politics" | Zodiak stat-figure, formatted currency |
| Stats: 312 | "A specific, surprising number of dual-influence actors" | Zodiak stat-figure — **needs better label** |
| Network graph | "The connections form a dense, organic web — not isolated transactions" | D3 force-directed, full-width, taxonomic feel with specimen labels |
| Top Recipients list | "These are the specific politicians who received the most money" | Ranked list 1-20, right-aligned tabular amounts, party in parentheses |
| Party bar chart | "The Conservatives have received dramatically more than anyone else" | Horizontal bars, party-coloured, proportional to max |
| Department meetings | "Some departments are far more accessible to external organisations" | Ranked by count, top 3 attendees per dept |
| Lobbying clients | "Major corporations hire many lobbying agencies simultaneously" | Client name + count, agency names listed below |
| Methodology | "This is serious, sourced journalism — not opinion" | Small, understated, bottom of page |

### Data Display Rules

- **Currency**: `formatCurrency()` — £1.6bn / £607.4m / £932k / £847
- **Dates**: Not prominent on homepage — "January 2026" in header bar
- **Names**: Full name as returned by API. Long org names truncated with `title` attribute for full text. Party names abbreviated via `cleanPartyName()`.
- **Counts**: "282 donations", "7,332" (comma-separated), "18 agencies"

### Comparisons & Sorting

| Data set | Sort | Why |
|----------|------|-----|
| Top Recipients | By total received, descending | "Who gets the most" is the question |
| Party bar chart | By total received, descending | Dominance comparison — Conservatives at top |
| Department meetings | By total meetings, descending | "Who's most accessible" |
| Lobbying clients | By agency count, descending | "Who employs the most lobbyists" |

All comparisons use right-aligned tabular numbers for scannable value comparison. Bar chart uses proportional width for visual comparison.

### Relationships & Direction

- **Donations**: Money flows from donors → recipients. Top Recipients shows the receiving end. Direction implicit from "Top Recipients" label.
- **Meetings**: External orgs → government departments. Direction shown by "Department" as category header, attendees nested below.
- **Lobbying**: Clients → agencies. Direction shown by "Top Clients & Their Agencies" label — client hires agency, not the reverse.

### Interconnectedness Plan

| Entity | Status | Route |
|--------|--------|-------|
| Top recipient names | ✅ Linked | `/person/{id}` via `getActorUrl()` |
| Top recipient party names | ✅ Linked | `/party/{party.id}` — row restructured to support two links |
| Party bar chart names | ✅ Linked | `/party/{party.id}` in SVG `<a>` tags |
| Meeting attendee names | ✅ Linked | `/person/{id}` or `/organisation/{id}` via `getActorUrl()` |
| Department names | Plain text | Blocked — department pages empty |
| Lobbying client names | ✅ Linked | `/organisation/{id}` via `getActorUrl()` |
| Lobbying agency names | ✅ Linked | `/organisation/{id}` — API returns `[{id, name}]` objects |
| Network graph nodes | ✅ Clickable | Detail panel with "View full profile →" link |

### Empty & Edge Cases

- **API timeout/error**: Show `—` for stats, "Unable to load" for data sections. Hero and methodology always render.
- **Zero results**: Unlikely in production (91k donations). If it happens, show "No data available" in each section.
- **Long org names**: Truncate with CSS (`truncate` class) + `title` attribute. Already handled in department and lobbying sections.
- **Missing party**: #1 recipient "Mr Andy Street" has no party — acceptable, display without parenthetical.

## URL Routing Changes

The homepage currently links all entities to `/person/{id}` regardless of type. As part of this work, introduce type-aware routing:

| Actor type | Route pattern | Used for |
|------------|--------------|----------|
| Person (politician, donor, director) | `/person/{id}` | Top recipients, network graph profiles |
| Organisation (company, trade union, external org) | `/organisation/{id}` | Meeting attendees, lobbying clients |
| Political Party | `/party/{id}` | Party bar chart, recipient party names |
| Lobbying Agency | `/organisation/{id}` | Agency names in lobbying section |

The frontend needs new route files:
- `frontend/src/pages/organisation/[id].astro` — can initially redirect to or re-export `person/[id].astro` logic
- `frontend/src/pages/party/[id].astro` — same

A `getActorUrl(actor)` helper function should generate the correct URL based on `actor_type` and `classification`:

```typescript
export function getActorUrl(actor: { id: number; actor_type?: string; classification?: string }): string {
  if (actor.classification === 'Political Party') return `/party/${actor.id}`;
  if (actor.actor_type === 'organization') return `/organisation/${actor.id}`;
  return `/person/${actor.id}`;
}
```

This function should be used everywhere entity links are generated — homepage, profile pages, timeline component.

## Copy & Content

### Headlines & Labels
- **Page title** (h1): "The web of money and access in Westminster"
- **Subhead**: "Who funds British politics — and what do they get in return? This investigation maps the financial relationships between donors and government ministers."
- **Section labels**: "Top Recipients", "Deep Dive", "Party Funding", "Ministerial Access", "Lobbying Influence", "Methodology"
- **Deep dive headlines** (h3): "Follow the money by party", "Who gets in the room?", "Who hires the lobbyists?"
- **Chart titles** (h4): "Donations by Party", "Meetings by Department", "Top Clients & Their Agencies"

### Heading Hierarchy Fix

Current: h1 → h3 → h4 → h5 (skips h2)
Target:
- h1: "The web of money and access in Westminster"
- h2: "The Government Ministers Network"
- h3: "Follow the money by party", "Who gets in the room?", "Who hires the lobbyists?", "Methodology"
- h4: "Donations by Party", "Meetings by Department", "Top Clients & Their Agencies"

### Tone
- Authoritative data journalism. Declarative headlines. Numbers speak.
- Editorial quotes in deep dive cards are italic, using pull-quote style.
- Source attributions use smallest text size, uppercase, ink-muted.

## Visual References

### Patterns to Follow
- Stats strip: `stat-figure` + `stat-label` pattern from `global.css`
- Section labels: `.section-label` class (accent red, uppercase, tracked)
- Rules/dividers: `border-ink/10` thin lines, `border-ink` thick top rules
- Deep dive cards: Section label → headline → quote → explore link pattern

### Vintage Natural History Design

The network graph is the strongest natural-history element. Opportunities to strengthen the aesthetic elsewhere:

- **Party bar chart**: Consider using party-coloured bars with a fine ink outline — like hand-coloured plates. The current uniform accent-red bars feel generic. Party colours immediately communicate identity.
- **Top Recipients list**: Already has a strong specimen-list quality — ranked numbers, display font names, tabular figures. Could add a subtle accent-left border on hover to reinforce the "field notebook" feel.
- **Department meetings**: The nested attendee lists with `border-l-2 border-accent/20` already have a taxonomic branching quality. This is good.
- **Lobbying agencies**: The `·`-separated agency lists read like taxonomic synonym lists. This is good. Ensure font is small enough to feel like annotation.

### Design System Departures

- **Party-coloured bars**: The design system says "One Accent Color" — but party colours are explicitly in the palette for this purpose. The bar chart communicates better with party identity colours than uniform red.
- **Deep dive card restructuring**: Currently each deep dive card is a single `<a>`. To support inner entity links, the left-column editorial content becomes the link, and the right-column data panel becomes standalone. This is a structural change but maintains the same visual pattern.

## Backend Changes — All Complete (2026-04-16)

| Priority | Endpoint | Change | Status |
|----------|----------|--------|--------|
| **P0** | `/aggregates/top-lobbying-clients/` | Return agencies as `[{id, name}]` instead of `string[]` | ✅ Done |
| **P0** | `/aggregates/stats/` | Add Redis cache (1hr TTL) | ✅ Done |
| **P1** | `/aggregates/top-lobbying-clients/` | Fix N+1: batch agency query instead of per-client | ✅ Done |
| **P1** | `/aggregates/party-donations/` | Push party filter into SQL instead of Python | ✅ Done |
| **P1** | `/aggregates/party-donations/` | Add Redis cache (1hr TTL) | ✅ Done |
| **P1** | `/aggregates/top-lobbying-clients/` | Add Redis cache (1hr TTL) | ✅ Done |
| **P1** | `/aggregates/department-meetings/` | Add Redis cache (1hr TTL) | ✅ Done |
| **P2** | `/aggregates/top-recipients/` | Add `select_related('polymorphic_ctype')` + Redis cache (1hr TTL) | ✅ Done |

Cache utilities in `api/v2/cache_utils.py`: `make_aggregate_cache_key()`, `invalidate_aggregate_caches()`, `AGGREGATE_CACHE_TTL`.

## Implementation Order — All Complete (2026-04-16)

1. ✅ **Routing infrastructure**: `getActorUrl()` in `frontend/src/lib/utils.ts`, `/organisation/[id].astro` and `/party/[id].astro` route files
2. ✅ **Heading hierarchy fix**: h1 → h2 (network) → h3 (deep dive) → h4 (data panels). Methodology is h2.
3. ✅ **Homepage interconnectedness**: Meeting attendees, lobbying clients, lobbying agencies (now `{id, name}` objects), party bar names, recipient party names — all linked via `getActorUrl()`
4. ✅ **Deep dive card restructure**: Editorial left column is `<a>` to section page, data right column has independent entity links
5. ✅ **Party-coloured bars**: SVG hatched/stippled pattern fills per party from design system palette
6. ✅ **Backend: API changes**: All 8 items above
7. ✅ **Mobile network alternative**: Hidden below `sm` breakpoint, replaced with summary + "View interactive network →" link
8. ✅ **Network loading skeleton**: Stipple dot-cloud pattern with "Cataloguing connections..." text
9. ✅ **Stats label clarity**: "Donors who also lobby" with `title` tooltip
10. ✅ **Mobile stats reflow**: 3-col at all sizes, smaller text/labels on mobile (`text-[2rem]` / `text-[9px]`)
11. ✅ **Recipient party linking**: Row restructured from single `<a>` to `<div>` with separate name and party links
12. ✅ **Hardcoded API URL**: Replaced `localhost:8000` with `PUBLIC_API_URL` from `utils.ts` in index.astro, network.astro, ActorTimeline.svelte
13. ✅ **Network detail panel**: Long names and roles wrap across two lines instead of truncating

## Known Remaining Issues

- **Search input**: Exists in nav but not wired to any functionality. Either implement or mark as coming soon.
- **Data quality [upstream]**: "Crick Institute Eton College" is two concatenated entities (#1 lobbying client). "NATIONAL GRID PLC" is all-caps. Fix belongs in import pipeline.
- **Mobile hero headline**: "Westminster" clips at 375px due to `text-6xl` being too large. Could reduce to `text-5xl` on smallest screens.
- **Network graph keyboard navigation**: No keyboard support — all interactions mouse-only.

## Revision History

- 2026-04-16: All implementation complete. Backend cached, interconnectedness comprehensive, mobile fixed.
- 2026-04-15: Initial draft based on audit findings
