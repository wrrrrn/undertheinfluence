# Lobbying — Design Spec

**Date**: 2026-04-16
**Status**: Draft
**Author**: Claude + Warren
**Audit**: Completed 2026-04-16 (see audit in conversation)
**Inspiration**: UKGovScan `/lobbying` (register table, recent-vs-all-time, quarters-active intensity column) — translated to our data (meetings + donations) where UKGovScan uses contracts.

## Overview

`/lobbying` is the page that explains how the UK's consultant lobbying industry connects to political power. It has three acts: (1) the **register** of active lobbying agencies, (2) the **top clients** commissioning the most representation, (3) the **dual-influence overlay** — who hires lobbyists *and* donates to parties.

The page answers three questions a reader might arrive with:
- "Who are the lobbying firms?" → Register section.
- "Who is buying the most lobbying right now?" → Top Clients section.
- "Where does lobbying money meet donation money?" → Dual Influence section.

Its role in site navigation is as the primary lens on consultancy — complementing `/directory` (actor search), `/meetings` (departmental access), and `/parties` (party funding). It is also the canonical jumping-off point into individual agency profiles and their client-profile cross-links.

## Layout & Hierarchy

### Grid Structure
- Container: `max-w-[1400px] mx-auto px-6`
- Asymmetric layouts: hero uses 8+4 split (headline + hero annotation), register is full-width, cross-reference is 7+5 (clients + dual influence).
- No full-bleed anywhere — this is a dense information page, not a visualisation canvas.

### Content Zones (top to bottom)

1. **Hero** — Section label, headline "Who hires the lobbyists?", subhead. Annotated source note (register + data cutoff) in the 4-col right gutter. ~220px.
2. **Composite Stats Strip** — Four tabular figures + labels: **active agencies / recent clients (last 4 quarters) / clients who also donate / clients with ministerial meetings**. Border-y treatment like homepage. ~130px.
3. **Register** — Full-width sortable table of lobbying agencies styled as a specimen catalogue. Plate numerals, per-agency activity bar (hatched), classification metadata. Pagination. ~640px collapsed to 30 rows.
4. **Top Clients & Their Agencies** — 7-col. Redesigned specimen catalogue with proper agency chips, classification, quarters-active. ~720px.
5. **Dual Influence** — 5-col. Stippled proportional donation-volume bars alongside lobbying-agency counts, annotated. ~720px.
6. **Methodology / Source Note** — Source attributions for ORCL register + EC donations + GOV.UK meetings, plus limitation notes. ~160px.
7. **Footer** — handled by BaseLayout.

### Responsive Behaviour

- **Desktop (1440px)**: Layout as described.
- **Tablet (768px)**: Register keeps full width but drops the activity-bar column; cross-reference columns stack (clients first, dual influence below).
- **Mobile (375px)**: Register transforms into a vertical list — each row a mini-specimen-card with name + recent/all-time inline, sort pills above become a `<select>`. Cross-reference sections are full-width, stacked. Composite stats become a 2×2 grid.

## Component Inventory

### Hero (Static Astro)
- **Purpose**: Establish the investigation. Frame the rest of the page.
- **Copy**:
  - Section label: "Lobbying Influence"
  - Headline: "Who hires the lobbyists?"
  - Subhead: "Consultant lobbyists in the UK must register their clients quarterly. This is the register — and the shape of the industry it reveals."
- **Right gutter (4-col)**: A small annotation block — "About this data" header + 2 sentences on the Transparency of Lobbying Act and what the register captures. Connected to the subhead by a leader line on desktop (SVG overlay).
- **Natural history treatment**: Leader line from annotation gutter to the word "register" in the subhead. Terminal `.leader-dot` (accent red).

### Composite Stats Strip (Static Astro)
- **Purpose**: Scale-setting — four figures contextualise the register and the cross-references.
- **Data source**: `GET /api/v2/aggregates/lobbying-composite-stats/` (new endpoint — see Backend Dependencies).
- **Elements** (Zodiak `text-5xl`, tabular-nums; labels small-caps Satoshi):
  - `{n}` — **Active agencies** (label: "Registered Consultant Lobbyists")
  - `{n}` — **Recent clients (last 4 quarters)** (label: "Clients declared Q{x} {year} – Q{y} {year}" — dynamic range)
  - `{n}` — **Clients who also donate** (label: "Overlap with Electoral Commission register")
  - `{n}` — **Clients with ministerial meetings** (label: "Overlap with GOV.UK transparency data")
- **Natural history treatment**: Leader line from the single most notable figure (biggest delta) into a one-line margin annotation: e.g. "1 in 5 lobbying clients also donate to political parties." Implementation: absolutely-positioned `<span>` + SVG `<line>`.
- **States**:
  - Default: figures from API.
  - Loading: `—` placeholders.
  - Error: fail silently with `—`.

### Lobbying Register (Static Astro — server rendered table; tiny Svelte island for sorting)
- **Purpose**: The canonical, sortable list of consultant lobbying agencies. Reader can answer: "Is this agency active? How long has it been registered? How busy is it right now?"
- **Data source**: `GET /api/v2/aggregates/lobbying-register/?sort={field}&limit=30&offset={n}` (new endpoint — see Backend Dependencies).
- **Default sort**: `recent_clients desc` — "who's active right now" is the most useful default.
- **Columns** (all right-aligned for numeric columns, tabular-nums):
  1. **Plate numeral** — rank (1–30 on page 1), Zodiak bold text-lg, muted when not the default sort, full-ink when sorted by recent-clients
  2. **Name** — Zodiak, links to `/person/{agency.id}`, hover:text-accent
  3. **Classification** — small-caps Satoshi text-xs, ink-muted ("Limited Company" / "LLP" / "Partnership")
  4. **Registered** — date, ink-muted, partial-date-safe (YYYY or YYYY-MM shown as-is)
  5. **Recent clients (4Q)** — count, tabular-nums
  6. **All-time clients** — count, tabular-nums, ink-muted
  7. **Quarters active** — max(distinct_quarters) across all consultancies — intensity signal
  8. **Activity bar** — thin horizontal SVG, full-cell width, hatched fill proportional to `recent_clients / max(recent_clients)` across the page — textured (see Visual References). ~160px wide.
- **Sort pills** (Svelte island — minimal state): Recent clients (default) · All-time clients · Quarters active · Name · Registered. Each pill is a client-side sort toggle; URL search param syncs (`?sort=name`).
- **Pagination**: Prev/Next at bottom, "Showing 1–30 of {n}" to left. Page size 30.
- **Natural history treatment**:
  - Plate numerals set the register visually as a specimen catalogue.
  - `border-b border-ink/5` between rows — fine plate rule lines.
  - Activity bar uses diagonal hatching (`pattern id="hatch-accent"`, stroke `#C54B3C` at 45°, 4px pitch, 0.6 opacity) filled to `recent_clients / max`. Full-scale track background at `opacity="0.03"`.
  - Classification column functions as secondary "Latin name" annotation.
- **Data quality filter**: Exclude agencies where `Actor.id IN (SELECT actor_id FROM CompaniesHouseMatch WHERE not_applicable_reason = 'concatenated')`. Flagged upstream; not our job to re-detect.
- **States**:
  - Default: 30 rows server-rendered.
  - Loading (sort change): brief opacity dip (200ms) on the tbody.
  - Empty: "No agencies match the current filter." in ink-muted italic (shouldn't happen at default filter).

### Top Clients & Their Agencies (Static Astro)
- **Purpose**: Rank of organisations buying the most consultant lobbying right now — specimen catalogue of the biggest buyers.
- **Data source**: `GET /api/v2/aggregates/top-lobbying-clients/?limit=20` (existing, cached; but fix required — see Bug Fixes).
- **Row structure** (top-to-bottom per row):
  - **Plate numeral** (Zodiak bold text-xl) + **client name** (Zodiak, links to `/person/{actor.id}`, hover:text-accent) + **agency count** right-aligned ("{n} agencies")
  - **Classification line** — secondary Satoshi text-xs, ink-muted: "{classification} · {quarters_active}Q active" (e.g., "Private Limited Company · 12Q active")
  - **Agency chips** — indented under `border-l-2 border-accent/20`, each agency as a linked chip: `<a href="/person/{agency.id}" class="hover:text-accent">{agency.name}</a>` separated by ` · `. Chips link to `/person/{agency.id}` (API change required — see Bug Fixes).
- **Natural history treatment**: Plate numeral + classification-as-Latin-name + taxonomic branching (`border-l-2`) on the agency chips.
- **Data quality filter**: Same CompaniesHouseMatch filter. Still-present concatenated names after filter are rendered faithfully (policy: don't hide upstream issues).

### Dual Influence (Static Astro)
- **Purpose**: Show organisations that route influence through *both* donations and lobbying. Answers "who's playing both games?"
- **Data source**: `GET /api/v2/aggregates/dual-influence/?limit=20` (existing — but **needs cache decorator added** — see Backend Dependencies).
- **Row structure** (per entity):
  - **Entity name** (Zodiak, links to `/person/{organization.id}`, hover:text-accent) + **donation volume bar** (stippled, proportional to `total_donated / max` in set) right-aligned, ~120px wide.
  - **Under name, secondary line**: "£{total_donated} to politicians · {donation_count} donations · {lobbying_count} agencies retained" (tabular-nums, Satoshi xs, ink-muted).
- **Natural history treatment**:
  - Stippled donation bar using `pattern id="stipple-accent"` — dot density proportional to volume (see Visual References). Each row's bar scales to the page maximum.
  - Thin plate divider (`border-b border-ink/5`) between rows.
  - Leader line from the top entity (biggest dual-influence player) into a margin annotation: "{top_entity} donates {£X} AND retains {N} lobbying agencies — the largest dual-influence footprint in the data."
- **States**:
  - Default: 20 rows.
  - Loading: skeleton rows (name + hatched placeholder bar).
  - Empty: "No dual-influence data available." in ink-muted italic (shouldn't happen — known-good dataset).

### Methodology / Source Note (Static Astro)
- **Purpose**: Attribution + limitation disclosure.
- **Content**: Three short paragraphs with leader lines to specific source names.
  - ORCL register (quarterly): scope, what "declared" means, what's excluded (in-house lobbyists).
  - Electoral Commission donations (since 2001): threshold notes.
  - GOV.UK ministerial meetings (since 2010): department coverage, known gaps.
- **Natural history treatment**: Each source name is a small `.source`-class citation. Minimal chrome.

## Data Communication

### Page-Level Story

**"The lobbying industry has {N} registered agencies representing {M} recent clients, and {X} of those clients also donate directly to political parties — a dual route to influence worth £{Y}."**

How the design delivers this:
- The composite stats strip is the one-paragraph summary above, rendered as four numbers.
- The register makes the industry's shape concrete — size, age, and activity of each firm.
- The cross-references (top clients, dual influence) answer the "so what?" — which entities actually drive the industry, and which blur the line between lobbying and donating.

Five-second scan: the reader should land, scan the four stats, and walk away with the scale. The register and cross-refs are for second-minute engagement.

### Element-by-Element Intent

| Element | Communicative Intent | Visual Treatment |
|---|---|---|
| Hero headline | "This page is about who buys political access through registered lobbyists" | Display Zodiak, left-aligned, with section label above |
| Hero gutter annotation | "The register is the statutory source — here's what it covers and what it doesn't" | Small-caps label + 2 sentences, leader line to "register" in subhead |
| Stat: active agencies | "The size of the professional consultant-lobbying industry" | Zodiak text-5xl tabular-nums |
| Stat: recent clients | "How much active work is happening *right now*, not historically" | Zodiak text-5xl; label names the 4-quarter window dynamically |
| Stat: clients who donate | "Lobbying overlaps with direct party funding" | Zodiak text-5xl; annotated leader line carries the "1 in 5" sentence |
| Stat: clients with meetings | "Lobbying overlaps with ministerial access" | Zodiak text-5xl |
| Register: plate numeral | "This is a formal catalogue, not a buzzy leaderboard" | Zodiak bold text-lg |
| Register: activity bar | "How active is this agency *this year* vs its peers?" | Hatched proportional bar — enables at-a-glance comparison without reading numbers |
| Register: quarters active | "Depth of engagement — is this a one-quarter blip or a decade-long fixture?" | Right-aligned tabular-nums integer |
| Top client: classification line | "This is not just 'Tesco' — it's a Private Limited Company with 12 quarters on the register" | Satoshi xs ink-muted, below name |
| Top client: agency chips | "These are the specific firms they hired, each clickable" | Linked chips with `border-l-2` branching |
| Dual influence: stippled bar | "Donation volume — a visual proxy for size of political spend" | Proportional stippled fill, right-aligned |
| Dual influence: leader-line annotation | "Here's the single most notable dual-influence player" | Margin annotation on the top row |

### Data Display Rules
- **Money**: `formatCurrency` from utils.ts — £1.6bn / £503m / £847k / £12,345. Tabular-nums throughout.
- **Dates**: Partial-date-safe. `YYYY-MM-DD` → "13 Dec 2019". `YYYY-MM` → "Dec 2019". `YYYY` → "2019". Never display `null` — use `—`.
- **Quarter ranges**: "Q4 2023 – Q3 2024" (with en-dash).
- **Counts**: Pluralise with `pluralize()` helper — "1 agency" / "18 agencies", "1 donation" / "954 donations".
- **Names**: Truncate with `title` attribute on hover at ~50ch for agency names in chip rows; names in the register name column can wrap to 2 lines.
- **Classifications**: Display as-returned from API (already normalised). "Private Limited Company", "Limited Liability Partnership", "Trade Union", "Unincorporated Association". If `classification === 'Unknown'` — show `—`.

### Comparisons & Sorting
- **Register default**: sorted by `recent_clients desc`. Alternatives: all-time clients, quarters active, name (alpha), registered (chronological).
- **Top clients**: sorted by `agency_count desc`. No alternative sort — this is the editorial ranking.
- **Dual influence**: sorted by a composite score (`total_donated desc` primary, `lobbying_count desc` secondary). Already how the existing endpoint sorts.
- **Comparison enablers**: tabular-nums right-aligned on every numeric column; hatched/stippled proportional bars for visual comparison.

### Relationships & Direction
- **Lobbying**: `client → agency` (client hired agency). Register row describes the *agency*; each row is "agencies engaged by {count} clients". Top Clients describes the *client*; row is "{client} engaged these {count} agencies". Direction must be unambiguous from the column label ("Recent clients" = clients of this agency; "18 agencies" = agencies hired by this client).
- **Donation overlap**: `client → party/politician`. Shown in Dual Influence as aggregate amount + count.
- **Meeting overlap**: `client → minister`. Shown in Composite Stats as a count only.

### Interconnectedness (CRITICAL)

Every entity name on the page must link:
- Register: agency name → `/person/{agency.id}` with `hover:text-accent transition-colors`.
- Top Clients: client name → `/person/{actor.id}`. Agency chips → `/person/{agency.id}`. Both require the existing `[object Object]` bug fix + API shape change (see Bug Fixes).
- Dual Influence: organisation name → `/person/{organization.id}` (already correct in current implementation).
- Methodology source names: external links to the source websites (ORCL, EC, GOV.UK) — `<a>` with `rel="noopener"` `target="_blank"`.

No entity name with a known actor ID may appear as plain text on this page. If the API returns a name without an ID (e.g. for the ORCL register agencies that are not yet resolved to Actor records), plain text is acceptable but must be flagged as a data quality gap (Warn row in the audit, not a Fail).

### Empty & Edge Cases
- **Zero agencies**: impossible at default filter (72 lobbying agency actors). If filter returns zero, show "No agencies match this filter" in italic ink-muted.
- **Zero dual-influence overlap**: also impossible at our data size. Fallback copy: "No dual-influence data available."
- **Agency with zero recent clients**: register shows `0` in the recent-clients column and a 0-width activity bar (still shows the empty track). Distinguishes "on the register but dormant" from absence of data.
- **Long names**: client names wrap to 2 lines max in the register; agency chips truncate with ellipsis + `title` attr.
- **Concatenated names upstream**: filtered via CompaniesHouseMatch flag (see above). If any slip through, render faithfully — policy is don't hide upstream bugs.
- **Partial dates**: register's "Registered" column handles YYYY, YYYY-MM, YYYY-MM-DD without conversion errors.

## Copy & Content

### Headlines & Labels
- **Page title** (`<title>`): "Lobbying Register & Influence | Under The Influence"
- **Section label (hero)**: "Lobbying Influence"
- **H1**: "Who hires the lobbyists?"
- **Subhead**: "Consultant lobbyists in the UK must register their clients quarterly. This is the register — and the shape of the industry it reveals."
- **Section labels** (before each major zone, accent-red uppercase):
  - "Lobbying Register"
  - "Top Clients"
  - "Dual Influence"
  - "Methodology"
- **Section H2s**:
  - "The Register" (above the sortable table)
  - "Top Clients & Their Agencies" (above the specimen catalogue)
  - "Dual Influence" (above the stippled bars)
  - "How this data is compiled" (above the methodology)

### Dynamic Content
- **Stat strip labels** — dynamic quarter range: "Clients declared Q{x} {year}{en-dash}Q{y} {year}" using the API's `window_start`/`window_end`.
- **Register annotation**: "1 in 5 lobbying clients also donate to political parties" — computed from `clients_who_donate / recent_clients`, rounded to the nearest 1/5 / 1/4 / 1/3 / half.
- **Dual influence margin annotation**: "{top_entity.name} donates {£X} AND retains {N} lobbying agencies — the largest dual-influence footprint in the data."

### Tone
- Authoritative data journalism — declarative, not hedged.
- Use "clients" and "agencies" not "customers" or "firms".
- Avoid "reveals" / "uncovers" — prefer "shows" / "records".
- Never editorialise on specific companies. Only editorialise at the aggregate: "The industry is concentrated" is fair; "{Company X} dominates" is not.

## Visual References

### Patterns to Follow
- **Stat strip layout**: match `frontend/src/pages/index.astro` lines 192–207 (border-y, tabular-nums, asymmetric column widths).
- **Specimen catalogue rows**: match the top-recipients pattern on the homepage but with an added activity-bar column.
- **Hatched bar pattern**: from political-party-profile.md — `pattern id="hatch-{key}"` definitions in SVG `<defs>`, reused across rows.
- **Leader line annotations**: from homepage's `.leader-dot` class; thin SVG `<line>` + circle terminal.
- **Section labels**: `.section-label` class — uppercase, accent red, tracking-widest, text-xs.

### Vintage Natural History Prescription

**1. Hero** — Leader line from the right-gutter "About this data" annotation into the word "register" in the subhead. Terminal `.leader-dot` at the word. Absolute-positioned SVG overlay (`pointer-events-none`), rendered only ≥ md breakpoint.

**2. Composite Stats Strip** — Leader line from the single most notable stat (default: "clients who also donate") into a margin annotation below the strip: "1 in 5 lobbying clients also donate to political parties." Implementation: absolutely-positioned `<span>` + SVG `<line>` from stat to annotation.

**3. Register table** —
- Activity bar column uses diagonal hatching: `<pattern id="hatch-activity" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="4" stroke="#C54B3C" stroke-width="1" opacity="0.6"/></pattern>`. Fill proportional to `recent_clients / max(recent_clients)` across the current page. Full-scale track uses same pattern at `opacity="0.06"`.
- Plate numeral: Zodiak bold text-lg, right-aligned in a 3ch-wide first column. When the table is sorted by a column other than recent-clients, the numeral is ink-muted (indicating rank is not the current sort).
- Classification as secondary annotation: Satoshi text-xs ink-muted, below or beside the name depending on viewport.
- Row divider: `border-b border-ink/5` — fine plate-rule lines.

**4. Top Clients catalogue** —
- Plate numeral: Zodiak bold text-xl, 3ch first column.
- Classification line: "{classification} · {quarters_active}Q active" — the quarters-active piece is the intensity signal borrowed from UKGovScan.
- Agency chips: taxonomic branching — `border-l-2 border-accent/20 pl-3` on the chip container.
- Row divider: `border-b border-ink/5`.

**5. Dual Influence bars** —
- Stippled proportional bar using `<pattern id="stipple-donation" patternUnits="userSpaceOnUse" width="6" height="6"><circle cx="1" cy="1" r="0.6" fill="#5B7355" opacity="0.4"/><circle cx="4" cy="4" r="0.6" fill="#5B7355" opacity="0.3"/></pattern>`. Botanical-green dots — the donor node colour — deliberately distinct from the register's accent-red hatched bars so the two sections read as different taxa.
- Fill proportional to `total_donated / max(total_donated)` across the 20 rows.
- Fine ink outline: `stroke="#5B7355" stroke-width="0.75" stroke-opacity="0.5"` — lithographic plate outline.
- Leader line from row #1 into a margin annotation (right gutter on desktop; above the list on mobile).

**6. Methodology** — Each source name is wrapped in a small `.source` class annotation. No decorative treatment — this section is restrained scholarly footnote.

### Design System Departures
- **New pattern ID**: `stipple-donation` using donor-node green (#5B7355). Adding to the shared pattern library (global.css + inline SVG). Justified because Dual Influence communicates a different *kind* of signal from the register's hatched accent bars — stippled green for "money that flows to politicians", hatched red for "activity on the register".
- **Register table** is the first sortable table on the site. Sort pills pattern is new — define it in global.css as a reusable `.sort-pills` component: inline flex, small-caps, `hover:text-accent`, active state is ink + `border-b-2 border-accent`.

## Backend Dependencies

New or changed endpoints required (see `/ux-constraints` from the audit for python-architect's full analysis).

1. **New**: `GET /api/v2/aggregates/lobbying-register/` — sortable agency register. Returns per agency: `{id, name, classification, registered_date, recent_client_count, alltime_client_count, quarters_active, meeting_count, donation_touch_count}`. Cache 1hr. Filter excludes `CompaniesHouseMatch.not_applicable_reason = 'concatenated'`. Supports `?sort=recent_clients|alltime_clients|quarters_active|name|registered` and `?limit=30&offset={n}`.
2. **New**: `GET /api/v2/aggregates/lobbying-composite-stats/` — four figures + `window_start`/`window_end`: `{active_agencies, recent_clients, clients_who_donate, clients_with_meetings, window_start, window_end}`. Cache 1hr.
3. **Fix (existing)**: `GET /api/v2/aggregates/dual-influence/` — add cache decorator (`make_aggregate_cache_key`, 1hr TTL). No other changes.
4. **Fix (existing)**: `GET /api/v2/aggregates/top-lobbying-clients/` — return `agencies: [{id, name}]` instead of `agencies: [str]`. Frontend expects objects already (see homepage spec); current `/lobbying.astro` consumes them as strings and renders `[object Object]`. Fixing at the API level + updating both consumers is the clean path.
5. **Fix (existing)**: `AgencyClientsView` uses raw SQL without canonical resolution. Add `COALESCE(canonical_agency_id, agency_id)` and `COALESCE(canonical_client_id, client_id)` to the CTE. Not consumed by this page but the fix lands in the same session.

## Bug Fixes (pre-requisite to this design)

Must be shipped before or alongside the new spec implementation:

1. **Agency rendering** — `frontend/src/pages/lobbying.astro:86` currently does `client.agencies.join(' · ')` on an array of objects. Must become per-agency chip rendering (see Top Clients component).
2. **Client names unlinked** — same file line 81: `<span class="font-display font-bold">{client.actor.name}</span>` must become a linked `<a href={\`/person/${client.actor.id}\`}>`.
3. **10px typography** — all `text-[10px]` on the page bumps to `text-xs` (12px) minimum, and rank numerals to Zodiak `text-lg`.
4. **DualInfluence caching** — backend fix, see above.
5. **Concatenated-name filter** — backend fix, see above.

## Revision History

- **2026-04-16** — Initial draft.
