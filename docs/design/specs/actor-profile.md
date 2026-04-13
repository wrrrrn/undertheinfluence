# Actor Profile — Design Spec

**Date**: 2026-04-12
**Status**: Draft
**Author**: Claude + Warren

## Overview

The actor profile is the most-linked page on the site (~25+ inbound links from the homepage alone). It answers: **"What is the full picture of this person's financial and political life?"** The key design insight is that roles, donations, and meetings are not separate categories — they're a single chronological story. A donation from Rupert Murdoch means something different when you can see it arrived while Johnson was Foreign Secretary.

**No tabs.** Everything lives on a single vertical timeline. The reader scrolls through a person's political life.

## Layout & Hierarchy

### Grid Structure
- Container: `max-w-[1400px] mx-auto px-6`
- Header: 12-col grid, 8+4 split (name/role left, headline stat right)
- Timeline: single column, full width of container

### Content Zones (top to bottom)

1. **Profile Header** (~180px) — Name, current/latest role, party, headline financial figure
2. **Summary Stats Strip** (~80px) — Secondary stats as a horizontal strip with border dividers
3. **Timeline** (variable, scrollable) — Unified chronological view of the person's political life

### Responsive Behavior
- **Desktop (1440px)**: Header is 8+4 grid. Timeline rows have date left, content right.
- **Tablet (768px)**: Header stacks. Timeline maintains two-column layout but tighter.
- **Mobile (375px)**: Single column throughout. Timeline dates stack above content.

## Component Inventory

### Profile Header (Static Astro)
- **Purpose**: Establish who this person is, their most important role, and the headline financial figure
- **Data source**: `/api/v2/actors/{id}/` + `/api/v2/actors/{id}/memberships/`
- **States**:
  - Default: Name, role, party, headline stat
  - No role found: Show name and party only
  - Organisation (not person): Show "ORGANISATION" label, classification instead of party

### Summary Stats Strip (Static Astro)
- **Purpose**: Quick numerical overview before the reader dives into the timeline
- **Data source**: Actor response fields + count from each endpoint
- **States**:
  - Default: 3-4 stats in a horizontal row
  - Zero values: Omit that stat entirely (don't show "0 meetings")

### Timeline (Svelte `client:visible`)
- **Purpose**: Tell the chronological story of this person's political life — when they held power, who gave them money during that time, and who they met
- **Data source**: All endpoints merged and sorted by date
- **Props**: `actor`, `donations`, `donationsMade`, `memberships`, `meetings`, `consultancies`
- **States**:
  - Default: Populated timeline with role spans and event rows
  - Loading: "Loading timeline..." (brief, data is SSR-fetched)
  - Empty: "No recorded activity for this actor."
  - Sparse: If only roles exist (no donations/meetings), show roles as the spine with a note

## Data Communication

### Page-Level Story

**"Boris Johnson received £1.7m in donations from 147 sources across his career as MP, Foreign Secretary, and Prime Minister — and held 335 meetings with external organisations while in office."**

The page communicates this through:
- The **headline stat** (£1.7m) at the largest size in the header
- The **timeline** showing donations and meetings overlaid on role periods, so the reader sees *when and in which capacity* the activity happened

A reader should get the story in 5 seconds: see the name, see the money, see the roles, scroll and see the pattern.

### Element-by-Element Intent

| Element | Communicative Intent | Visual Treatment |
|---------|---------------------|-----------------|
| **Name** | "This is Boris Johnson" | Zodiak 5xl/6xl, largest element on the page |
| **Role line** | "His most significant position — this is why he matters" | Zodiak lg, ink-light, directly below name |
| **Party badge** | "He's a Conservative — essential political context" | Small text or subtle badge, ink-muted |
| **Headline stat (£1.7m)** | "The total scale of money flowing to this person" | stat-figure (4rem), Zodiak bold — the single most prominent number |
| **Stats strip: donations count** | "Many separate transactions, not just one big cheque" | Zodiak 2xl bold, with "donations received" label below |
| **Stats strip: meetings count** | "Significant volume of external access" | Same treatment as donations count |
| **Stats strip: connections** | "How many distinct entities are linked to this person" | Same treatment |
| **Timeline: Role spans** | "When he held power and in what capacity" | Horizontal bands/bars spanning date ranges. Background colour or left-border accent. These form the *context layer* that donations and meetings are plotted against. |
| **Timeline: Donation events** | "Who gave him money, when, how much, and for what purpose — while he was [role]" | Point events on the timeline. Donor name (bold, linked), amount (right-aligned, tabular), type badge, purpose text. The reader should immediately see which role period the donation falls within. |
| **Timeline: Meeting events** | "Who got access to him, when, and about what — while he was [role]" | Point events. Organisation name (bold), department (muted), purpose, date. Same visual language as donations but visually distinguishable (different left-border colour or icon). |
| **Timeline: "Showing X of Y"** | "There's more data available" | Muted text with "Load more" action |

### Data Display Rules
- **Money**: `formatCurrency` — £1.7m, £24k, £15k. Never raw decimals.
- **Dates**: Point events show "18 Jan 2023". Role spans show "Jul 2019 — Sep 2022". Partial dates (YYYY only) show the year. Canonical date priority for donations: `accepted_date` > `reported_date` > `received_date`. If none, event is "Undated".
- **Names**: Donor/org names in Zodiak semibold. Truncate with `title` attr if longer than ~40 chars on mobile.
- **Counts**: "147 donations" not "147". Always with the noun.
- **Types**: Donation type ("VISIT", "CASH") as small uppercase badges next to the donor name.

### Comparisons & Sorting
- **Default sort**: Chronological, most recent first. This is a timeline — time is the primary axis.
- **Role spans**: Sorted by start_date descending, shown as background context.
- **Events (donations + meetings)**: Interleaved by date within the timeline. All events from all types in a single stream.
- **Comparison**: The timeline enables temporal comparison — the reader sees donation clustering, meeting frequency changes, and correlations with role transitions.

### Relationships & Direction
- **Donations**: "[Donor name] → Boris Johnson" — the donor name is the primary label, Johnson is implicit (it's his page).
- **Meetings**: "Boris Johnson met [Organisation]" — the organisation is the primary label.
- **Key people**: For corporate donors, show directors/PSCs in annotation (accent-border pattern from current implementation).
- **All entity names link to their profile pages** — the reader can always click through to explore the other side of a relationship.

### Empty & Edge Cases
- **No donations**: Omit donations count from stats strip. Timeline shows roles and meetings only. No empty placeholder.
- **No meetings**: Omit meetings count. Timeline shows roles and donations only.
- **No roles**: Show donations and meetings without the role-context layer. Add a note: "No parliamentary roles recorded."
- **No data at all**: "No recorded activity for this actor." Single line, italic, ink-muted.
- **Very long org name**: Truncate with ellipsis + title attribute. Max ~60 chars desktop, ~35 mobile.
- **Very small donation**: Show it — £100 donations are still interesting (they show breadth of support).
- **Undated events**: Some donations lack `accepted_date`. Use `reported_date` as fallback, then `received_date`. If all are null, group in an "Undated" section at the bottom of the timeline.
- **Role overlap**: Politicians often hold multiple simultaneous roles (e.g., "MP for X" + "Prime Minister"). For the "while serving as" context on each event, show the most significant role using this priority: ministerial role > party leadership > backbench MP. The `ministerialRoles` filter in the Astro page already handles this.
- **Organisation profile** (not person): Same layout but label says "ORGANISATION". Organisations don't have "roles" — the timeline shows donations made/received and consultancy periods instead.
- **Political party profile**: Gets dedicated funding sections between header and timeline (see Party Archetype below). Timeline uses **progressive lazy loading** — all years shown with summary data, real donations fetched per year on demand. No synthetic data.

## Copy & Content

### Headlines & Labels
- **Section label**: "POLITICIAN" (for persons) or "ORGANISATION" (for orgs)
- **Role line**: Most recent ministerial/significant role (not "MP for X" if they were also PM)
- **Stats labels**: "RECEIVED", "DONATIONS", "MEETINGS" — all uppercase, stat-label class
- **Timeline section**: No heading needed — the timeline speaks for itself after the stats strip
- **Empty state**: "No recorded activity for this actor."
- **Load more**: "Load more" as accent-colored link text

### Dynamic Content
- Currency: `formatCurrency` (£1.7m, £503k)
- Dates: "18 Jan 2023" for events, "Jul 2019 — Sep 2022" for spans
- Counts: Always with noun ("147 donations", "335 meetings")

### Tone
- Authoritative, neutral. State facts, don't editorialize.
- Good: "The Prime Minister" / "Secretary of State for Foreign and Commonwealth Affairs"
- Bad: "Controversial PM" / "Top Tory"

## Visual References

### Patterns to Follow
- **Stats strip**: Homepage stats pattern (lines 192-207 of index.astro) but with clear hierarchy — headline stat at 4rem, secondary stats at 2xl
- **Section label**: `.section-label` class from global.css
- **Annotation pattern**: Accent-border left annotations for key people (already in current ActorProfile.svelte)
- **Timeline**: Inspired by FRONTEND_DESIGN.md Section 5.4 "Timeline" — central spine, event nodes, horizontal stems to descriptions

### Timeline Visual Language
- **Role spans**: Horizontal bands with a subtle background tint or thick left border in accent color. Role name in Zodiak semibold. Date range in ink-muted.
- **Donation events**: Left border in donor-node green (#5B7355). Donor name bold, amount right-aligned.
- **Meeting events**: Left border in director-node blue (#4A7BA7). Org name bold, date right-aligned.
- **Year markers**: Bold Zodiak, dividing the timeline into scannable sections.
- **Spine**: Subtle 1px vertical line in ink/10, connecting all events.

### Design System Departures
- **No tabs**: Deliberate departure from the Section 6.2 "tabbed content" pattern. The timeline replaces tabs because temporal context is the core insight — "when and in which capacity" cannot be communicated by category-separated tabs.
- **Mixed event types in one stream**: The design system doesn't define a multi-type timeline. This is a new pattern specific to actor profiles.

## Technical Notes

### Data Merging for Timeline
The Svelte component must:
1. Take all memberships, donations, meetings, and consultancies
2. Assign each a date (memberships use `start_date`, donations use `accepted_date` or `reported_date`, meetings use `meeting_date`)
3. Merge into a single array sorted by date descending
4. Group by year for year-marker headings
5. For role spans, track which roles were active at any given point so donation/meeting events can show "while serving as [role]"

### Pagination
- **Standard actors**: Initial load of 50 most recent events (from SSR). "Load more" fetches the next 50 via client-side fetch. Role spans always load in full (there are typically <20).
- **Party pages**: Progressive lazy loading. No donations pre-fetched. `yearlyTotals` from `funding-summary` endpoint provides all years with summary data (top 5 donors, totals, unique donor counts). Timeline renders all years as collapsed summaries. Clicking "Show all N ▸" fetches real donations for that year from `/actors/{id}/donations-received/?received_after=YYYY-01-01&received_before=YYYY-12-31&limit=500`.

---

## Party Archetype

**Added 2026-04-13.** Political party pages get dedicated funding sections between the stats strip and timeline. These are server-rendered in Astro (not part of the Svelte timeline component).

### Content Zones (party-specific, top to bottom)

1. **Profile Header** — Name, "POLITICAL PARTY" section label, headline stat (£503.2m received)
2. **Summary Stats Strip** — "21,336 donations from 2,995 donors"
3. **Top Private Donors** — Ranked list (top 20 by lifetime value), 2-column grid. Each shows name (linked), donation count, total amount, and "Also funded X MPs" annotation when applicable.
4. **Cross-Funding of MPs** — Dedicated section (styled like Public Funding) showing party donors who also made separate donations to individual party MPs. Header shows total cross-funding amount and donor count. Ranked by amount given to MPs. Surfaces the overlap between party and personal political funding.
5. **Trade Union Funding** — Accent-border-left section. Total, donation count, source count. Top 10 unions listed with amounts. Explanatory note distinguishing institutional from individual/corporate funding.
6. **Public Funding** — Same treatment as Trade Union. Shows Short Money, Policy Development Grants. Explanatory note that these are statutory allocations, not private donations.
7. **Funding by Type** — Breakdown by donation type (Cash, Public Funds, Non Cash, Exempt Trust, Visit). Each with count, percentage, and total.
8. **Funding by Year** — Interactive bar chart. Each year is a `<details>` element with:
   - Year label (Zodiak bold), horizontal bar (proportional width), amount, donor count
   - "Election" badge in accent red for election years
   - "In govt" / "Opposition" annotation
   - Bars use `bg-accent/30` for in-govt years, `bg-ink/10` for opposition
   - Expandable: click reveals top 5 donors for that year with amounts
9. **Timeline** — Progressive lazy-loaded timeline (see Pagination above)

### Data Sources
- Sections 3-8: `GET /api/v2/actors/{id}/funding-summary/` (Redis-cached 1hr)
- Section 9: `GET /api/v2/actors/{id}/donations-received/` (per-year, on demand)

### Design Decisions
- **No synthetic data**: Earlier implementation built fake donation objects with hardcoded "15 Jun" dates and "Cash" types. Replaced with real data fetched on demand.
- **Cross-Funding elevated**: "Also funded X MPs" was previously an inline annotation on donor rows. Now has its own section because it's a key interconnectedness signal — donors who fund both the party and individual MPs represent concentrated influence.
- **Duplicate label suppressed**: When `actor.classification` matches the section label (e.g., both say "Political Party"), the classification line below the name is hidden.
