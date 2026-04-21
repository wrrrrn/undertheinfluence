# Politician Profile — Design Spec

**Date**: 2026-04-16
**Status**: Implemented (current pass scoped to aesthetic grace notes + data clarity — see §Current Pass below)
**Author**: Claude + Warren
**Supersedes**: `actor-profile.md` (generic draft, retained for reference)
**Audit**: Completed 2026-04-13 — Badenoch (#2539), Starmer (#2198). Re-audited 2026-04-16 — Johnson (#2177).
**Constraints**: Completed 2026-04-13 — all changes feasible, 2 minor backend changes

## Current Pass Scope (2026-04-16)

The 2026-04-16 re-audit (against Johnson) confirmed the page already reads well — party colour dot, linked summaries, classification taxonomy, role specimens are all in place. The page is **closer to the natural-history aesthetic than the full seven-point treatment below implies**.

**Product direction**: keep the current layout and visual language, weave in natural-history grace notes sparingly, and borrow data-clarity moves from UKGovScan without adopting their utilitarian aesthetic. Small surgical additions, not a rewrite.

**Committed for this pass** (see §"Current Pass — Grace Notes + Data Clarity" below for full specs):

Natural history grace notes:
1. **GN1 Specimen dots on event rows** — 7px coloured circle per event, positioned on the spine, colour-coded by type.
2. **GN2 Plate rule on year markers** — hairline extending from the year to the right edge of the content column.
3. **GN3 Margin activity glyphs** — ●▲◆◉ in the date gutter beside year markers, showing which event types occurred that year.
4. **GN9 Hatched year bars** — proportional SVG bar under each collapsed year summary (donations, meetings, consultancies), hatched fill. *(Promoted from aspirational after d3-viz review — highest-impact viz win for minimal code.)*

Data-clarity additions (UKGovScan-influenced, kept to our voice):
5. **DC1 "In politics since {year}"** — lifetime tenure in the header, below the current role.
6. **DC2 "Verify on Parliament.uk →"** — external provenance link in the header gutter. **Blocked** on backend (`ActorDetailSerializer` needs `identifiers` field). Deferred from this pass.

New viz components (from d3-viz review):
7. **V1 Donation-concentration dot plot** — the £1.7m rendered as 147 dots packed in a small SVG, each sized by donation value. Replaces what was planned as GN4 (SVG leader-line annotation). *The viz IS the annotation — shows whether the total is "few big donors" or "many small ones" at a glance.*
8. **V2 Stats-strip activity beeswarm** — each stat in the strip gets a small time-axis beeswarm behind it: dots by year, showing when the activity clustered. For donations: peak years become visible. For meetings: density over the career.

**Deferred**: continuous timeline spine (§1 below full-treatment), full catalogue numeral redesign (§3), type-badge textural treatment, year-marker terminal dot at spine/rule junction. Role-row stipple fills (§7 correction below).

## Captured feedback — next frontend pass (2026-04-17)

Review of the live Kemi page after the Career Shape coxcomb was unblocked by the backend `activity-by-year/` endpoint. Overall read: "high-end data journalism piece — FT/Guardian energy." Muted palette + serif headings + whitespace working. Notes for the next frontend pass:

1. **Coxcomb specific values.** The layered rose reads well as a *shape* but is hard to read as *numbers*. Next pass: add hover or tap-to-reveal per-wedge tooltips showing year + donation count + meeting count + donation total. Keep the visual language calm — the tooltip is an affordance, not a chart element.
2. ~~**Colour mixing on overlapping wedges.**~~ **Resolved 2026-04-17 (revised)** — folded into §Career Shape Coxcomb — Audit Fixes CF3 below. Drop meeting-line `stroke-opacity` from 0.55 → 0.42 and add `mix-blend-mode: multiply` on the meeting path.
3. ~~**Companion visualisation next to the rose.**~~ **Resolved 2026-04-17** — first revision specced a Donation-Type stacked bar; second revision (this file) reversed the decision to a **Donation-Type Waffle (100 patterned tiles)** on d3-viz aesthetic and degenerate-distribution legibility grounds. See §Career Shape Companion — Donation-Type Waffle below. Rejected / deferred candidates unchanged:
   - **Meetings-by-department donut** rejected — for Kemi, 121 of 122 meetings are DBT (99.2% single slice). Degenerate for the typical minister-serving-one-department career pattern. Also: d3-viz vocabulary table explicitly lists donut/pie charts under "Weak natural history fit."
   - **In-and-out dual-axis strip** deferred — for Kemi specifically (1 donation made, 0 consultancies) and the median backbencher (similar), two of three series render empty. Parks cleanly as a future dual-role-actor component.
   - **Top donors sparkbar** deferred — overlaps heavily with the per-year donor ranking already shown in the timeline's collapsed summaries. Timeline + `DonationConcentration` dot plot already cover this story.
4. **The "1 donation made" lonely stat.** Looks empty compared to the histogram-backed stats beside it. Options: drop the empty beeswarm area entirely, fold "donations made" into the main donations card as a secondary metric, or add a "view one" link that expands inline. Current layout draws the eye to the gap, which is the wrong emphasis. **Deferred** — not in scope for this pass.
5. **Timeline jump navigation.** As coverage grows (Kemi already runs 2017→2025), vertical scroll is getting long. Sticky year rail or "jump to year" micro-nav in the left gutter would pay for itself. **Deferred.**
6. **Total vs itemised reassurance.** Header shows £1.3m received; first timeline entry is £4k Hoover Institution visit. A reader can briefly wonder if the numbers are inconsistent. One-line micro-copy ("Total across 111 donations — see individual entries below") under the headline stat would close the loop. **Deferred.**
7. **Coxcomb a11y (new — 2026-04-17 orchestrator audit).** SVG is `aria-hidden="true"` with no `<title>` / `<desc>` — screen readers get nothing. **Resolved** — folded into §Career Shape Coxcomb — Audit Fixes CF1 below.
8. **Peak-year leader line (new — 2026-04-17 orchestrator audit).** The 2024 donation peak reads as "a big wedge" without a narrative anchor. **Resolved** — folded into §Career Shape Coxcomb — Audit Fixes CF2 below.

Items 1, 4, 5, 6 park for a later pass. Items 2, 3, 7, 8 ship together in this pass — all in the Career Shape section.

## Career Shape Companion — Donation-Type Waffle (2026-04-17 revised)

**Status**: Design revised 2026-04-17 after a second d3-viz review and the orchestrator's architect ruling on data source.

**Revision summary:** The previous revision (also dated 2026-04-17, preserved in revision history) specced a Minard-style horizontal stacked bar and a ~10-line extension of `ActorActivityByYearView`. Both are reversed here.

- **Visualisation:** **Waffle chart (100 patterned tiles)** replaces the stacked bar. The waffle wins on aesthetic fit (specimen inventory plate > Minard composition stripe), on legibility for degenerate distributions like Kemi's 94%/6% split (the 1% sliver is a visible tile, not a sub-pixel bar segment), and on data-visibility expressiveness (the grey `Impermissible Donor` tiles are individually countable).
- **Data source:** `category_breakdown` field on `ActorActivityByYearView` (new field, ~10 backend lines). Per `docs/BACKEND_CONSTRAINTS_SNAPSHOT.md` §8 verdict (2026-04-17): Option B — extend `activity-by-year` with `category_breakdown: [{donation_type, count, total}]`. Canonical-correct via the existing `Q(recipient_id=pk) | Q(canonical_recipient_id=pk)` filter, shares cache key with the coxcomb, no new fetch (endpoint already on the wire for politicians). Roadmap placement: `BACKEND_DESIGN.md` §9 piggyback to the already-shipped `activity-by-year/` item.

**Scope**: Single new Svelte component (`DonationTypeWaffle.svelte`) sitting immediately to the right of `ActivityCoxcomb` in the Career Shape section. Resolves the desktop visual-imbalance flag (captured-feedback item 3) by filling the 700px empty paper with a meaningful specimen plate.

### Communicative intent

For Kemi: "She received £1.3m in donations — 94 of every 100 pounds was cash, almost all during her 2024 leadership campaign." For Johnson: "£1.7m — 85% cash, 11% non-cash hospitality, 5% study visits, 1% in-kind." For Starmer: "£847k — 86% cash, 10% non-cash, 3% visits, 1% in-kind." For every politician, one sentence: "**what kind of money is this, and how is it split?**"

The coxcomb already tells the reader *when* the money arrived. The waffle tells them *what kind of money* it was. The two together compose a complete "shape of receipts" specimen plate — one showing temporal rhythm, one showing compositional structure.

### Visual design

A 10×10 grid of 100 patterned tiles, each tile ~20×20px including a 2px gutter, total grid ~220×220px. Every tile inherits its donation-type's pattern + colour. Tiles packed column-major bottom-to-top, left-to-right, so the dominant category forms a full left-column block and smaller categories appear as capped columns on the right — reads as a specimen inventory (most common at left, rarer specimens at right), matching the d3-viz-skill "specimen catalogue" analogue for part-to-whole.

Next to the waffle (right side, ~180px column), a direct-label key: one row per category, showing a small swatch tile + `{Category} · {pct}% · {count}` on one line, `{formatCurrency(total)}` on the line below. Sorted descending by £ total. The dominant category's row gets a thin leader line connecting its swatch to the left-column block of the waffle — "this is the block, this is its name". Exactly one leader line; other categories are directly adjacent to their labels and don't need them.

**Percentage rounding rule**: Integer rounding with largest-remainder method so the 100 tiles always sum to 100% exactly. No 0% categories are rendered (they'd eat a tile they don't deserve); the key lists them with "<1%" instead.

**Pattern assignments** (each type gets a fixed pattern + colour combo, reused everywhere this data appears across the site):

| Category (EC label) | Colour | Pattern | ID |
|---|---|---|---|
| Cash | `#5B7355` botanical green | Stipple | `dtype-cash` |
| Non Cash | `#6B5B4F` warm brown | Diagonal hatch 45° | `dtype-noncash` |
| Visit | `#B87333` copper | Cross-hatch | `dtype-visit` |
| InKind | `#7B9E87` sage | Horizontal hatch | `dtype-inkind` |
| Public Funds | `#4A7BA7` steel blue | Dense hatch 135° | `dtype-publicfunds` |
| Impermissible Donor | `#6b6b6b` ink-muted | Sparse stipple | `dtype-unknown` |
| Unidentifiable Donor | `#6b6b6b` ink-muted | Sparse stipple | `dtype-unknown` (shared pattern) |
| Other (long-tail bucket) | `#4a4a4a` ink-light | Fine dot grid | `dtype-other` |

Data-visibility rule: `Impermissible Donor` and `Unidentifiable Donor` — real EC data-quality labels — render faithfully in their own muted-grey tiles. Not filtered out, not re-labelled. The muted grey and sparse pattern signal "unusual" without editorialising. If a reader hovers one, the tooltip reads the EC label verbatim. Any category not in the fixed map above gets folded into "Other" and the key-row label reads "Total value of donations not reported individually" (another real EC label) when that's the cause, otherwise "Other ({n} categories)".

### SVG structure (rough)

```svg
<svg viewBox="0 0 420 240" class="donation-type-waffle" role="img"
     aria-labelledby="waffle-title waffle-desc">
  <title id="waffle-title">Donation types for {name}, {yearRange}</title>
  <desc id="waffle-desc">
    {total} across {donationCount} donations.
    {dominant.pct}% {dominant.category}; {secondary.pct}% {secondary.category};
    {remaining}.
  </desc>

  <defs>
    <!-- one <pattern> per category, see Pattern assignments -->
    <pattern id="dtype-cash" width="4" height="4" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="0.6" fill="#5B7355" fill-opacity="0.55"/>
      <circle cx="3" cy="3" r="0.5" fill="#5B7355" fill-opacity="0.4"/>
    </pattern>
    <!-- ... -->
  </defs>

  <!-- Total caption, top-left -->
  <text x="0" y="12" font-size="11" font-family="Zodiak, serif" font-weight="600">
    {formatCurrency(total)}
    <tspan font-family="Satoshi" font-weight="400" fill="#6b6b6b">
      across {donationCount} donations
    </tspan>
  </text>

  <!-- The 10×10 grid, column-major, top-left origin at (0, 20) -->
  <g transform="translate(0, 20)">
    {#each tiles as t}
      <rect x={t.col * 20} y={t.row * 20} width="18" height="18"
            fill={`url(#dtype-${t.categoryId})`}
            stroke={t.color} stroke-width="0.4" stroke-opacity="0.6"
            data-category={t.category}
            on:mouseenter={() => hovered = t.category}
            on:mouseleave={() => hovered = null} />
    {/each}
  </g>

  <!-- Direct-label key, right-aligned column -->
  <g transform="translate(230, 24)" font-family="Satoshi, sans-serif">
    {#each keyRows as k, i}
      <!-- swatch -->
      <rect x="0" y={i * 26} width="10" height="10"
            fill={`url(#dtype-${k.categoryId})`}
            stroke={k.color} stroke-width="0.4" stroke-opacity="0.8"/>
      <!-- label line 1: category · pct% · count -->
      <text x="16" y={i * 26 + 8} font-size="10" fill="#1a1a1a">
        {k.category} <tspan fill="#4a4a4a">· {k.pct}% · {k.count} {pluralize(k.count,'donation')}</tspan>
      </text>
      <!-- label line 2: £ total -->
      <text x="16" y={i * 26 + 19} font-size="9" fill="#6b6b6b"
            font-family="Satoshi" font-variant-numeric="tabular-nums">
        {formatCurrency(k.total)}
      </text>
    {/each}
  </g>

  <!-- Leader line from dominant-category key row to the waffle's left column block -->
  <line x1="226" y1={24 + 5} x2="{dominant.leftColRightEdge}" y2={20 + dominant.midY}
        stroke="#6b6b6b" stroke-width="0.8" stroke-opacity="0.4"
        stroke-dasharray="2 2"/>
  <circle cx={dominant.leftColRightEdge} cy={20 + dominant.midY} r="2" fill="#C54B3C"/>

  <!-- Time anchor echoing the coxcomb's -->
  <text x="0" y="238" font-size="9" fill="#6b6b6b" font-family="Satoshi">
    {yearRange}
  </text>
</svg>
```

### D3 setup

No D3 `.stack()`, no scales. The math is tiny:

```ts
// sum totals, compute integer pcts with largest-remainder rounding
const totalValue = breakdown.reduce((a, b) => a + parseFloat(b.total), 0);
const raw = breakdown.map(b => ({ ...b, exact: 100 * parseFloat(b.total) / totalValue }));
const floors = raw.map(r => ({ ...r, floor: Math.floor(r.exact), rem: r.exact % 1 }));
let used = floors.reduce((a, b) => a + b.floor, 0);
// sort a copy by remainder descending, add 1 to as many as needed
const bumped = [...floors].sort((a, b) => b.rem - a.rem);
for (let i = 0; i < 100 - used; i++) bumped[i].pct = bumped[i].floor + 1;
for (const b of bumped) b.pct = b.pct ?? b.floor;
// flatten to 100 tiles, column-major, bottom-up
const tiles = [];
let idx = 0;
for (const cat of floors.sort((a, b) => b.pct - a.pct)) {
  for (let i = 0; i < cat.pct; i++) {
    const col = Math.floor(idx / 10);
    const row = 9 - (idx % 10);
    tiles.push({ row, col, categoryId: slug(cat.category), color: COLOURS[cat.category], category: cat.category });
    idx++;
  }
}
```

All math in a `$derived` block. No `d3.select()`, no layout modules — Svelte renders the `{#each tiles}` loop. The D3 dependency is not needed here; we keep the component dependency-free of D3 entirely (mirrors `DonationConcentration.svelte`'s approach).

### Interactivity

- **Hover on tile**: `hovered = category` via `$state`. On hover, all tiles *not* in the hovered category drop to `opacity="0.35"`; the hovered category's tiles get `stroke-opacity="1"`; the matching key row highlights (background swatch `fill="#FAF9F6"`, text colour accent on the category name). Supplementary tooltip is the aria-description already in `<title>`/`<desc>`; no separate floating tooltip is needed, since the key row *is* the legend.
- **Hover on key row**: mirror-interaction. Hovering the key row dims the other categories' tiles, same as tile-hover. Reading the key becomes the primary interaction path — direct labels, not tooltips, per the d3-viz anti-pattern rule.
- **Click**: deferred. Future: click tile → filter the timeline below to donations of that category.
- **Keyboard**: each key row is a `<button type="button">` (not a `<text>`), focusable, `aria-pressed` reflects hovered state. Arrow keys move between key rows (roving tabindex). The waffle `<rect>` tiles are not focusable — the key is the navigable surface.
- **Reduced motion**: opacity transitions use `transition: opacity 150ms ease` on non-reduced-motion, `none` otherwise, via a `prefers-reduced-motion` media query on the `<style>` block.

### Component inventory

**`DonationTypeWaffle.svelte`** (Svelte 5, `client:idle` via Astro)
- **Type**: Svelte island, `client:idle` hydration (below the fold at first paint; low-priority interactive).
- **Purpose**: Compositional breakdown of donation receipts by donation-type category. Pairs with `ActivityCoxcomb` in the Career Shape section.
- **Data source**: `activityByYear.category_breakdown` from `/api/v2/actors/{id}/activity-by-year/` — an array of `{ donation_type: string, count: number, total: string }`, sorted descending by `total`. New field, ~10 backend lines (see `docs/BACKEND_CONSTRAINTS_SNAPSHOT.md` §8 verdict and `docs/BACKEND_DESIGN.md` §9 item #1 extension). Endpoint is already fetched for politicians at `[id].astro:50` — no new request.
- **Props**: `{ breakdown: Array<{category: string, count: number, total: string}>, yearRange: string, donationCount: number, totalValue: number, name: string }`.
- **States**:
  - Default: 100 tiles + key rows + leader line.
  - Empty (`breakdown.length === 0` or `totalValue === 0`): component returns `null`. Parent controls via `{#if showWaffle}`.
  - Loading: skeleton (below).
  - Hover: dimming + swatch highlight.
- **Loading skeleton** (taxonomic style, per d3-viz skill):
  - A 10×10 grid of faint `<rect>` tiles filled with `url(#stipple-skeleton)` at `opacity="0.25"`.
  - Three empty key-row placeholders to the right: leader line + small `<rect>` swatch placeholder + two grey-bar label placeholders per row.
  - Reads as "a specimen grid being prepared" — consistent with the d3-viz taxonomic-skeleton pattern.

### Layout integration — Career Shape section

Before (unbalanced, ~700px empty paper at 1440px):

```
CAREER SHAPE
[caption]

[coxcomb 260px]  [<dl> ~320px]  [~700px void]
```

After (balanced):

```
CAREER SHAPE
[caption]

[coxcomb 260px]  [waffle+key ~420px]  [<dl> ~200px, trimmed]
```

Desktop (`md:` and up): 3-column flex row. `md:flex md:gap-8 md:items-start`. Columns lay out left-to-right: coxcomb → waffle+key → compact `<dl>`.

Mobile: stack in order: coxcomb → waffle+key (420px scales to 100% container width via `viewBox` preservation — on mobile the key wraps beneath the waffle) → `<dl>`. No horizontal scroll.

Condensed `<dl>` (third column), unchanged from the previous revision:

```
DONATIONS RECEIVED
£1.3m · 111 from 64 donors

MINISTERIAL MEETINGS
122 across 2 years · 388 organisations
```

### Interconnectedness

The waffle doesn't show entity names, so there are no mandatory links. The key labels name categories, not entities. (If a future iteration deep-links each category to the timeline filtered by `donation_type`, that becomes the interconnectedness hook.)

### Data visibility

- `Impermissible Donor` and `Unidentifiable Donor` categories render as grey-stippled tiles and named key rows when present. Not filtered out, not merged into a single "Unknown".
- Any donation with a blank or NULL `donation_type` value should surface in the `category_breakdown` with `donation_type: 'Unknown'`. The waffle renders these in the `dtype-other` bucket with the label "Unknown type" so the data-quality issue is visible rather than silently suppressed. (The backend implementation must explicitly map NULL/empty to `'Unknown'` — `FundingSummaryView` already does this at `api/v2/views.py:1276`; the new `category_breakdown` field on `ActorActivityByYearView` should copy that pattern.)
- The `Total value of donations not reported individually` long-tail label is rendered verbatim if the EC bucket appears.

### Natural history treatment

- **Textured fills**: every tile uses an SVG `<pattern>`. No flat `bg-` fills. Passes d3-viz audit criterion 1.
- **Direct labelling**: the key sits immediately beside the grid; each row pairs a miniature tile (swatch) with its category name. No separate colour legend; the tiles and the swatches share an ID-linked pattern. Passes criterion 2.
- **Leader line**: exactly one dashed leader line from the dominant-category key row to the waffle's dominant block, terminating in a `.leader-dot` (accent red, 2px). Passes criterion 3.
- **Specimen density**: 100 tiles + 4–8 key rows + leader line + total caption + year anchor occupy the 420×240 slot edge-to-edge with no whitespace. Passes criterion 4.
- **Fine ink outline**: per-tile `stroke-width="0.4" stroke-opacity="0.6"` — the Audubon-plate inked border, lighter than the bar's because tiles are smaller and we don't want a grid effect.
- **19th-century journal test**: 100 patterned specimens arranged in a taxonomic grid, keyed by category at the margin, with a marginal annotation to the dominant species. Reads as a Haeckel plate — Pass.

### Fetch-site decision (resolved 2026-04-17)

Architect landed **Option B** in `docs/BACKEND_CONSTRAINTS_SNAPSHOT.md` §8. Summary:

- Extend `ActorActivityByYearView` with a `category_breakdown: [{donation_type, count, total}]` field (~10 backend lines).
- Canonical-correct via the existing `Q(recipient_id=pk) | Q(canonical_recipient_id=pk)` filter at `api/v2/views.py:1390`.
- Shares cache key (`activity_by_year:{pk}`) with the coxcomb — waffle and coxcomb invalidate together.
- No new fetch on the frontend: the endpoint is already requested for politicians at `[id].astro:50`.
- `FundingSummaryView.category_breakdown` stays party-focused where the full funding decomposition (public funds, union funding, top donors, cross-funding) makes sense.

Roadmap placement: `docs/BACKEND_DESIGN.md` §9, piggyback amendment to the already-shipped `activity-by-year/` item (#1). See snapshot §8 for full rationale.

Frontend implementation uses `breakdown = activityByYear.category_breakdown` in `[id].astro`. No blocker remains.

## Career Shape Coxcomb — Audit Fixes (2026-04-17)

Three audit findings on the existing `ActivityCoxcomb.svelte` are in-scope for the same mockup pass as the waffle. They're all one-file fixes, and two of them (the 2024 leader-line and the opacity tuning) interact with how the Career Shape section reads end-to-end. Splitting them into a separate pass would leave the section half-finished.

### CF1. Accessibility title/desc

**Current**: `aria-hidden="true"` at `ActivityCoxcomb.svelte:98`. The SVG is invisible to screen readers — a "Fail" in the audit accessibility row.

**Fix**:

```svelte
<svg
  width={size} height={size} viewBox="0 0 {size} {size}"
  class="coxcomb"
  role="img"
  aria-labelledby="cox-title-{uid} cox-desc-{uid}"
>
  <title id="cox-title-{uid}">Activity shape for {name}, {minYear}–{maxYear}</title>
  <desc id="cox-desc-{uid}">
    Donations received and meetings held each year.
    {totalDonations} {pluralize(totalDonations,'donation')} across {donationYears} {pluralize(donationYears,'year')},
    {totalMeetings} {pluralize(totalMeetings,'meeting')} across {meetingYears} {pluralize(meetingYears,'year')}.
    Peak donation year: {peakDonationYear} ({peakDonationCount}).
    Peak meeting year: {peakMeetingYear} ({peakMeetingCount}).
  </desc>
  <!-- ... -->
```

Unique `uid` generated via `$props.id()` (Svelte 5 idiomatic) or `crypto.randomUUID().slice(0,8)` in an onMount-compatible initialiser. Required for multiple-coxcomb pages (currently only one per politician, but future-proof).

The component must accept two new props: `name: string` and optionally `label?: string` (for the full natural-language description — allows a containing spec like "Career Shape" to override "Activity shape for …" wording without edits here). Keep `name` as the only required addition; default `label` to the current template string.

**Computed locally**: `totalDonations`, `donationYears`, `peakDonationYear`, `peakDonationCount`, etc. from the existing `donationCounts` / `meetingCounts` maps. No new data.

### CF2. Leader line on peak year

**Current**: No annotations; the 2024 peak (Kemi: 103 donations in one year, driven by her leadership campaign) reads as just "a big wedge" with no contextual anchor — a "Fail" on the d3-viz criterion 3 (leader lines) for this specific viz.

**Fix**: One dashed leader line from the outer edge of the peak-donation wedge to a small annotation text in a corner of the viewBox. Annotation text example: `"2024 · 103 donations · leadership campaign"` — but the third clause ("leadership campaign") is a data-driven derivation we don't have, so v1 ships as `"{peakDonationYear} · {peakDonationCount} donations"` and the contextual clause is deferred until the backend exposes role-at-time data (see existing spec §"Donation Context: Recipient Party & Role (PLANNED)").

```svelte
<!-- After all wedges are drawn, before the legend/axis text -->
{#if peakWedge}
  {@const angle = -Math.PI / 2 + (peakWedge.idx + 0.5) * wedgeAngle}
  {@const r = R * Math.sqrt(peakWedge.dCount / maxDonations)}
  {@const x1 = cx + r * Math.cos(angle)}
  {@const y1 = cy + r * Math.sin(angle)}
  {@const x2 = cx + (R + 18) * Math.cos(angle)}
  {@const y2 = cy + (R + 18) * Math.sin(angle)}
  <line x1={x1} y1={y1} x2={x2} y2={y2}
        stroke="#6b6b6b" stroke-width="0.8" stroke-opacity="0.45"
        stroke-dasharray="2 2"/>
  <circle cx={x2} cy={y2} r="2" fill="#C54B3C"/>
  <text x={x2 + 4} y={y2 + 3} font-size="9" fill="#4a4a4a"
        font-family="Satoshi, sans-serif" font-style="italic">
    {peakWedge.year} · {peakWedge.dCount} donations
  </text>
{/if}
```

Only drawn when `maxDonations >= 5 × medianDonations` (i.e. there's a clear peak worth annotating). Suppressed when every year has roughly the same donation count — no leader line to a non-peak.

The component's `size` prop (default 220) is not changing, but `.coxcomb` already has `overflow: visible` — the annotation extends past the SVG bounding box safely. Verify at mockup time that the parent Career Shape section gives the viz enough right-side padding to avoid clipping.

**Peak type**: v1 annotates the donation peak only (the dominant narrative for receipt-heavy politicians like Kemi). For a meeting-peak-dominant politician (e.g. a Prime Minister with heavy meeting load in one year), a second leader line to the meeting peak could be added — **deferred** to a follow-up pass to keep this change surgical.

### CF3. Opacity tuning on overlapping wedges

**Current**: Donation stipple (green) and meeting diagonal hatch (blue) overlap on wedges where both activities are present; the overlap can go muddy. Audit flagged as **Warn**.

**Fix**: Two changes in `ActivityCoxcomb.svelte`:

1. Drop the meeting-pattern line `stroke-opacity` from 0.55 (line 105) to 0.42.
2. Add `style="mix-blend-mode: multiply"` to the meeting `<path>` elements (lines 126 and 136).

```svelte
<!-- line 104-106: -->
<pattern id={meetingPatternId} width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
  <line x1="0" y1="0" x2="0" y2="4" stroke={meetingColor} stroke-width="0.9" stroke-opacity="0.42"/>
</pattern>

<!-- lines 126, 136 — add style attribute: -->
<path d={w.mPath} fill="url(#{meetingPatternId})" stroke={meetingColor}
      stroke-width="0.5" stroke-opacity="0.75"
      style="mix-blend-mode: multiply"/>
```

Mockup-phase validation: Playwright-screenshot Kemi (many 2024 overlap pixels), Johnson (broader year-by-year overlap), Starmer (sparse overlap). Eyeball the three; if the green still muddies, reduce donation stipple `fill-opacity` from 0.55/0.4 to 0.48/0.34. Further tuning is a follow-up if it still fails the 19th-century-journal test.

Respect `prefers-reduced-motion`: `mix-blend-mode` has no motion implication; no change needed for reduced-motion users.

### Why ship these three with the waffle

- All four changes are in the Career Shape section. Splitting them across two passes means the section is audit-red for longer than necessary.
- CF1 (a11y) is blocking an explicit audit "Fail" row.
- CF2 (leader line) interacts with the waffle: the waffle's leader line to the dominant-category block and the coxcomb's leader line to the peak year are the two Minard-style annotations that ground the Career Shape narrative. Shipping one without the other leaves the section lopsided on annotation density.
- CF3 (opacity) affects readability in exactly the same desktop screenshot where the waffle will be audited.

All three land in `frontend/src/components/ActivityCoxcomb.svelte`; none touch other files.

## d3-viz Review Corrections (2026-04-16)

Post-review corrections folded in:
- §7 "Role Rows (ALREADY PASSING)" → downgraded to **Warn**. Flat `rgba(197,75,60,0.03)` background should be stipple-patterned. Deferred to a follow-up pass but no longer claimed as passing.
- GN1 implementation updated to CSS `::before` approach (cleaner than inline `<span>` — applies via existing type-border classes, single source of truth).
- Former GN4 (SVG leader line at `width="12"`) would have rendered as a tick. Replaced by V1 (donation-concentration dot plot) which is a stronger, more informative element in the same slot.
- Stats strip treatment firmed up from "tiny Sparkline" vague-prescription to concrete V2 beeswarm spec.

## Overview

The politician profile is the most-linked page on the site. It answers: **"What is the full picture of this person's financial and political life?"** Roles, donations, and meetings are not separate categories — they're a single chronological story. A donation from a property developer means something different when you can see it arrived while the MP was Housing Secretary.

The page serves three types of reader:
1. **Journalist** scanning for patterns (donation clustering, meeting frequency during specific roles)
2. **Researcher** looking for specific relationships (did X donate to Y?)
3. **Casual browser** who clicked a name from the homepage and wants the quick story

All three should get value from the same page — the headline stat and stats strip serve type 3, the timeline serves types 1 and 2.

## What's Changing (from current implementation)

The current page is functional but has gaps identified in the UX audit:

| Change | Type | Priority |
|--------|------|----------|
| Link collapsed donor summary names | Frontend | **High** — interconnectedness |
| Rebuild meeting summary orgs from attendee data | Frontend | **High** — data quality + interconnectedness |
| Add button focus-visible styles | Frontend | **High** — accessibility |
| Semantic headings for year markers | Frontend | **High** — accessibility |
| Fix stats strip dynamic Tailwind class | Frontend | **High** — layout bug |
| Add unique donor count to stats strip | Backend + Frontend | **Medium** — data communication |
| Add party colour indicator | Frontend | **Medium** — visual recognition |
| Fix `on_behalf_of` N+1 query | Backend | **Medium** — performance |

## Layout & Hierarchy

### Grid Structure
- Container: `max-w-[1400px] mx-auto px-6`
- Header: 12-col grid, `lg:col-span-8` + `lg:col-span-4` (name/role left, headline stat right)
- Stats strip: equal columns with vertical dividers, centred
- Timeline: single column, 160px date gutter + fluid content

### Content Zones (top to bottom)

1. **Section Label** — "POLITICIAN" in accent red, underlined
2. **Profile Header** (~180px) — Name, role, party with colour dot, headline £ figure
3. **Stats Strip** (~80px) — Key counts with context (e.g. "97 donations from 62 donors")
4. **Timeline** (variable, scrollable) — Year-grouped chronological view with expand/collapse

### Responsive Behavior
- **Desktop (1440px)**: 8+4 header grid. Timeline: 160px date column + fluid content. Stats strip horizontal with dividers.
- **Tablet (768px)**: Header stacks. Timeline maintains two-column layout, tighter spacing.
- **Mobile (375px)**: Full stack. Timeline dates above content. Stats strip stacks vertically with horizontal dividers between items.

## Component Inventory

### Profile Header (Static Astro)

- **Type**: Static Astro (server-rendered, no JS)
- **Purpose**: Establish identity, role, political affiliation, and headline financial figure
- **Data source**: `/api/v2/actors/{id}/` + `/api/v2/actors/{id}/memberships/`

**Elements**:
- Section label: "POLITICIAN" — `.section-label` with `border-b border-accent pb-2 mb-6 inline-block`
- Name: `text-5xl md:text-6xl font-bold tracking-tight leading-[0.95] font-display`
- Role: Latest ministerial role (not "MP for X" if they also hold a ministerial role). `text-lg text-ink-light font-medium`
- **Party with colour dot** (NEW): `<span class="inline-block w-2.5 h-2.5 rounded-full mr-1.5" style="background:{partyColour}"></span>{partyName}` — Small coloured dot before the party name. Colour from the design system party palette. `text-sm text-ink-muted mt-1`
- Headline stat: `stat-figure` (4rem Zodiak bold) + `stat-label` ("RECEIVED" or "DONATED"). Right-aligned on desktop, below name on mobile.

**Party colour mapping** (in `frontend/src/lib/utils.ts`):
```typescript
export const PARTY_COLOURS: Record<string, string> = {
  'Conservative': '#4A7BA7',
  'Labour': '#B85450',
  'Liberal Democrat': '#C9A227',
  'Green': '#5B7355',
  'Scottish National Party': '#C9B84A',
  'Reform UK': '#4A8B9E',
  'Plaid Cymru': '#5B7355',
  'Democratic Unionist Party': '#4A4A4A',
  'Sinn Féin': '#5B7355',
  'Alliance': '#C9A227',
};
```

**States**:
- Default: Name, role, party dot + name, headline stat
- No ministerial role: Show latest role (MP for X, or committee)
- No party: Omit party line entirely (no empty dot)
- No financial data: Omit headline stat (header is just name + role)

### Stats Strip (Static Astro)

- **Type**: Static Astro
- **Purpose**: Quick numerical overview — how many relationships and from how many distinct sources
- **Aesthetic**: **Chronological Context**. Include a tiny, low-contrast **Sparkline** (area chart) behind each stat showing the distribution of that activity (donations or meetings) across the actor's timeline. This provides an instant "Field Study" of activity rhythm.

**Fix**: Use conditional classes and add context.

```astro
<!-- Stats strip grid — use explicit classes, not template literals -->
<div class:list={[
  'grid gap-0 border-y border-ink/10 py-6',
  stats.length === 1 && 'grid-cols-1',
  stats.length === 2 && 'grid-cols-2',
  stats.length === 3 && 'grid-cols-3',
  stats.length >= 4 && 'grid-cols-2 md:grid-cols-4',
]}>
```

**Stats to show** (only non-zero, in this order):
1. Donations received: **"97"** / "donations from **62** donors"
2. Donations made: **"3"** / "donations made"
3. Meetings: **"107"** / "meetings with **105** organisations"
4. Lobbying: **"5"** / "lobbying relationships"

### ActorTimeline (Svelte `client:visible`)

- **Type**: Svelte island with `client:visible`
- **Aesthetic**: **Marginalia**. Use the date column (left) for small annotations or "Specimen Notes" when significant events occur (e.g., "Promotion to Cabinet", "Dissolution of Parliament").
- **Year Headings**: Style as **"Plate Markers"** with a horizontal rule and a small red "specimen dot" (`#C54B3C`) at the intersection of the rule and the spine.

#### 1. Collapsed Donor Summary — Add Links (HIGH PRIORITY)

Currently `topDonors` in the collapsed summary are plain text. They already have `id` fields.

**Before**:
```svelte
<span class="text-[11px] font-display font-semibold truncate">{donor.name}</span>
```

**After**:
```svelte
<a href="/person/{donor.id}" class="text-[11px] font-display font-semibold truncate hover:text-accent transition-colors">{donor.name}</a>
```

#### 2. Collapsed Meeting Summary — Rebuild from Attendee Data (HIGH PRIORITY)

Currently `topMeetingOrgs` is built from `organisation_met_raw` — an unparsed comma-separated string. This produces messy names like "Katharine Viner, Editor-in-chief, The Guardian and Pippa Crerar, Political Editor, The Guardian".

**Fix**: Rebuild from `meeting.attendees[]` data:

```typescript
// In buildYearGroups(), replace the meetingOrgCounts logic:
// Instead of: meetingOrgCounts keyed by organisation_met_raw
// Use: attendees[].actor, deduplicated, filtered for self-references

for (const m of meetings.results) {
  if (!m.meeting_date) continue;
  const year = m.meeting_date.substring(0, 4);
  // ... existing meeting push ...

  // Build org counts from attendees (not organisation_met_raw)
  if (m.attendees && m.attendees.length > 0) {
    for (const att of m.attendees) {
      if (att.actor?.id === actor.id) continue; // skip self
      const orgKey = `${year}-${att.actor?.id || att.actor_name_raw}`;
      const existing = meetingOrgCounts.get(orgKey);
      if (existing) {
        existing.count++;
      } else {
        meetingOrgCounts.set(orgKey, {
          name: att.actor?.name || att.actor_name_raw || 'Unknown',
          id: att.actor?.id || null,
          count: 1
        });
      }
    }
  } else {
    // Fallback for meetings with no parsed attendees (0.6% of meetings)
    const orgKey = `${year}-raw-${m.organisation_met_raw}`;
    meetingOrgCounts.set(orgKey, {
      name: m.organisation_met_raw || 'Unknown',
      id: null,
      count: 1
    });
  }
}
```

Then in the template, link names that have IDs:
```svelte
{#if org.id}
  <a href="/person/{org.id}" class="text-[11px] truncate hover:text-accent transition-colors">{org.name}</a>
{:else}
  <span class="text-[11px] truncate">{org.name}</span>
{/if}
```

**Type change**: `topMeetingOrgs` becomes `Array<{ name: string; id: number | null; count: number }>` (add `id` field).

#### 3. Button Focus Styles (HIGH PRIORITY)

Add to `.clickable-row` in the `<style>` block:

```css
.clickable-row:focus-visible {
  outline: 2px solid #C54B3C;
  outline-offset: -2px;
}
```

#### 4. Semantic Year Headings (HIGH PRIORITY)

Change year markers from `<span>` to `<h2>` for screen reader navigation:

```svelte
<!-- Before -->
<div class="year-marker">
  <span class="year-label">{group.year}</span>
</div>

<!-- After -->
<h2 class="year-marker">
  <span class="year-label">{group.year}</span>
</h2>
```

No visual change — styling is on `.year-marker` and `.year-label`.

## Data Communication

### Page-Level Story

The page answers one question: **"What money and access flowed to this person, and in which roles?"**

For Badenoch the answer is: "She received £1.3m in donations from 58 donors, mostly while Leader of the Conservative Party and Secretary of State for Business — and held 122 meetings with external organisations in ministerial roles."

For Starmer: "He received £847k in donations from 62 donors, and as Prime Minister has held 107 meetings with 105 different organisations in a single year."

The two examples reveal what the page must communicate differently depending on the politician:
- **Badenoch**: The story is the money — £1.3m is the headline, the career trajectory provides context
- **Starmer**: The story is the access — 107 meetings in one year as PM, with an extraordinary breadth (105 different organisations)

The current design handles Badenoch well (money is prominent) but undersells the Starmer story (meeting density and breadth aren't emphasised enough in the header).

### Element-by-Element Interrogation

#### Header: Name + Role + Party

**Intent**: "Who is this person, what power do they hold, and which tribe are they from?"

**Does the visual weight match the importance?** Yes. The name is the largest element on the page (5xl/6xl Zodiak). The role is subordinate but immediately visible. Party name is tertiary — correct, since party matters less than what power they hold.

**Can a reader get the point in 5 seconds?** Yes for Badenoch — "Kemi Badenoch / Leader of the Conservative Party / Conservative" reads top to bottom instantly. For Starmer — "Keir Starmer / The Prime Minister / Labour" is equally clear.

**What's missing?** The party name alone is low-signal. "Conservative" in ink-muted text looks like metadata. Adding a **colour dot** transforms it from a label to instant visual recognition — readers know party colour before they read the word. This is particularly valuable when scanning between multiple politician pages.

**Verdict**: Working well. Add party colour dot to elevate from "metadata" to "instant recognition".

#### Headline Stat (£1.3m RECEIVED)

**Intent**: "The total scale of money flowing to this person."

**Does the visual weight match the importance?** Yes — 4rem Zodiak bold, right side of the header, is the second-largest element on the page after the name. The eye goes: name → money → role. This is the correct reading order for a political influence site.

**Is this the right number to feature?** For most politicians, yes — total received is the headline story. But consider edge cases:
- A politician with zero donations but 200 meetings: the headline stat space is empty. The meetings count, which IS the story, is buried in the stats strip. **This is a design gap** — the headline stat should adapt to show whatever is most significant, not just money.
- A politician who has *made* donations (e.g. someone who funded their own campaign): `total_donated` shows as the fallback, which is correct.

**Does the formatting serve the message?** Yes — `formatCurrency` produces "£1.3m" which communicates scale instantly. "£1,340,067.06" would communicate nothing.

**Verdict**: Strong for money-heavy politicians. Needs a fallback hierarchy: total received → total donated → meeting count → nothing.

#### Stats Strip (111 DONATIONS RECEIVED / 1 DONATIONS MADE / 122 MEETINGS)

**Intent**: "The breadth of this person's financial and access network — a quick inventory."

**Can a reader get the point in 5 seconds?** Partially. The numbers are clear, but they don't communicate the insight. "111 donations received" is a fact. "111 donations from 58 donors" is a story — it says "her donor base is moderately concentrated, averaging 2 donations per donor". "107 meetings with 105 organisations" is an even better story — it says "almost every meeting was with a different org, this is extraordinary breadth".

**Is the comparison the design enables the right comparison?** The stats sit in equal columns which implies they're equally important. But they're not — for Badenoch, donations matter most; for Starmer, meetings matter most. The equal-weight presentation doesn't help the reader see which story is dominant.

**Problem**: The stats strip currently uses `grid-cols-${Math.min(stats.length, 4)}` — a dynamic Tailwind class that **doesn't work with JIT compilation**. This could produce broken layouts unpredictably.

**Verdict**: Add context ("from X donors", "with X organisations"). Fix the broken Tailwind class. Consider whether the most important stat should be visually elevated, or whether equal weight is the right choice (equal weight is simpler and avoids value judgements — probably the right call for a neutral data journalism site).

#### Year Markers (2025, 2024, 2023...)

**Intent**: "Navigate through time — scan to the years you care about."

**Does the design communicate this?** Yes — bold Zodiak headings break the timeline into scannable chunks. The reverse chronological order puts the most newsworthy content at the top.

**Accessibility gap**: These are `<span>` elements, not headings. A screen reader user has no way to jump between years. For a long career (Badenoch: 2017–2025, 8 year markers), this forces linear scrolling through hundreds of timeline rows. Making them `<h2>` allows heading navigation at zero visual cost.

**Verdict**: Visually fine. Needs semantic `<h2>` for accessibility.

#### Role Spans

**Intent**: "When did this person hold power, and in what capacity?"

**Does the visual weight match the importance?** The red left border + subtle background tint makes roles visually distinct from donations and meetings. They stand out as "context" rather than "events", which is correct — they're the scaffolding that gives meaning to everything else.

**Is the temporal information clear?** Yes — "Nov 2024 — Present", "Jul 2024 — Nov 2024" uses the range format. The reader can see that Badenoch held 5 roles in 2024 alone (rapid reshuffling after losing the election).

**What's the relationship direction?** Clear — the role is something the person holds at an organisation (House of Commons). "Leader of the Conservative Party · House of Commons" reads naturally.

**Verdict**: Working well. No changes needed.

#### Collapsed Donation Summary

**Intent**: "At a glance: how much money, from how many sources, and who were the biggest donors?"

**Does the design communicate this?** The total (£1.1m), donor count (58), and ranked top 5 are all present. The format — total bold, donors as a list with amounts — is dense but readable.

**Is the comparison right?** Top 5 donors sorted by total contributed enables "who gave most?" The count × amount format (e.g. "5× £130k") communicates both frequency and total.

**Critical failure: Interconnectedness.** The top 5 donor names are plain text. The reader sees "Charles Keymer" and cannot click through to explore who this person is. The `id` field is available in the data. This breaks the core UX principle — every entity name must be a doorway. **Fix: wrap in `<a>` tags.**

**Verdict**: Data communication is strong. Interconnectedness is broken. Must link names.

#### Expanded Donation Rows

**Intent**: "The full ledger — every donation with who, when, how much, what type, and in which ministerial capacity."

**Does the visual weight match the importance?** The donor name (Zodiak semibold) and amount (Zodiak bold, right-aligned) are the two most prominent elements per row. This is correct — "who" and "how much" are the two things the reader wants to compare.

**Does the formatting serve the message?** Right-aligned tabular amounts enable rapid value scanning — the reader's eye can run down the right edge comparing donation sizes. Type badges (CASH, INKIND, VISIT) distinguish categories without cluttering.

**Is the "while serving as" context effective?** The role context text (e.g. "as Leader of the Conservative Party") appears below the date in the left column at 9px. This is subtle — which is correct. The role is context, not the primary information. But the truncation at 33 characters with "..." obscures long role names ("as Shadow Secretary of State for Lev..."). Consider truncating at the first natural break instead.

**Key people (directors/PSCs)**: Below corporate donations, a thin accent-bordered line shows "Carole Gray, Lady Bamford (Director) · Mark Joseph Cyril Bamford (Director)...". This is excellent — it answers "who are the humans behind this company?" But these names are **not linked**, even when actor IDs might be available. This is a data quality check (do `donor_key_people` include actor IDs?), flagged for investigation.

**Verdict**: Strong design. Role truncation could be improved. Key people linking needs investigation.

#### Collapsed Meeting Summary

**Intent**: "At a glance: how many meetings, with how many different organisations, and who had the most access?"

**Critical failure: Data quality.** The organisation names are built from `organisation_met_raw` — an unparsed comma-separated string from the CSV import. This produces entries like:

> "Katharine Viner, Editor-in-chief, The Guardian and Pippa Crerar, Political Editor, The Guardian"

This looks like a single entity but it's actually two people from one organisation. Compare with Badenoch's cleaner meeting data ("Post Office Limited", "Fujitsu") — the difference is likely that Badenoch's meetings were parsed from a different department's CSV format.

**The fix**: Rebuild `topMeetingOrgs` from the parsed `attendees[]` data instead of `organisation_met_raw`. This produces clean individual names with actor IDs, enabling proper linking. The 0.6% of meetings with no parsed attendees fall back to the raw string.

**Is the comparison right?** Ranked by meeting count, which enables "who had the most access?" — the right question. The format mirrors the donation summary (name + count), which creates visual consistency between the two summary types.

**Verdict**: Broken by data source. Must rebuild from attendee data. Once fixed, the design pattern is sound.

#### Expanded Meeting Rows

**Intent**: "Each meeting: what was discussed, who was there, and under which department."

**Is the information hierarchy correct?** Purpose text is first and most prominent (text-sm, font-medium). Attendee names are second (11px Zodiak semibold). Department is third (meta-text, muted). This hierarchy is right — "what was discussed" > "who was there" > "which department".

**Does context ground the data?** The "as President of the Board of Trade" role context and "Department for Business and Trade" department label together establish the institutional context. The reader knows the meeting happened in an official capacity.

**Is the relationship direction clear?** For politician pages: "Badenoch met [these organisations]" — the politician is implicit (it's their page), the organisations are named. The minister's name appears only on organisation pages (where it's the other side of the relationship). This is correct.

**Multi-attendee meetings**: The UK-Saudi partnership meeting shows "Airbus, Johnson Matthey, HYCAP, Business roundtable with Saudi Minister for Industry and Minerials, Rolls Royce (Middle-East & Africa), GlaxoSmithKline" — a dense list of linked names separated by commas. This is readable at desktop but could be challenging at mobile. The `flex-wrap` handling is correct but touch targets may be too small.

**Verdict**: Strong design. Works well for single-attendee meetings. Dense multi-attendee meetings acceptable at desktop, monitor at mobile.

### Donation Context: Recipient Party & Role (PLANNED)

**Intent**: "Who did this person donate to, and what power did the recipient hold at the time?"

Currently, donation-made rows show "DONATED TO Robert Jenrick £25k" — but not that Jenrick was a Conservative leadership candidate at the time. The party and role at the time of donation are critical context.

**Backend**: New fields `recipient_party` and `recipient_role_at_date` on `DonationDetailSerializer`. Uses batch membership lookup matching donation date against recipient's memberships. 1 extra query per page. See `docs/UX_IMPLEMENTATION_PLAN.md` for full constraints analysis.

**Frontend**: On donation-made rows, show recipient with party colour dot and role:
```
DONATED TO  Robert Jenrick  ● Conservative · MP for Newark    £25k
```

On donation-received rows (politician pages), the existing `activeRole` pattern shows the page actor's own role. Could also show the *donor's* party/role when the donor is a politician — but this is lower priority since most donors are individuals/companies.

**States**:
- Recipient is a politician with party: show dot + party + role
- Recipient is a party (e.g. "Conservative and Unionist Party"): show as-is, no extra context needed
- Recipient has no membership data: show name only (current behaviour)

### Data Display Rules
- **Money**: `formatCurrency` — £1.3m, £150k, £5k. Never raw decimals.
- **Dates**: Events: "8 Nov 2024". Spans: "Nov 2024 — Present". Partial dates: show year only.
- **Names**: Zodiak semibold. Truncate with `title` attr at ~60 chars desktop, ~35 mobile.
- **Counts**: Always with noun + context: "97 donations from 62 donors", "107 meetings with 105 organisations".
- **Types**: CASH, INKIND, VISIT, NON CASH — uppercase badge, `meta-text` styling.
- **Role context truncation**: Truncate at natural word boundary near 35 chars, not mid-word.

### Interconnectedness (CRITICAL)

Every entity name with an available actor ID **must** be a clickable link.

| Entity | Location | Link target | Current status |
|--------|----------|-------------|----------------|
| Donor names (expanded) | Donation rows | `/person/{donor.id}` | ✅ Working |
| Donor names (collapsed) | Summary top 5 | `/person/{donor.id}` | ❌ **FIX** — IDs available but not linked |
| Recipient names | Donations made rows | `/person/{recipient.id}` | ✅ Working |
| Meeting attendees (expanded) | Meeting rows | `/person/{attendee.actor.id}` | ✅ Working |
| Meeting orgs (collapsed) | Summary top 5 | `/person/{org.id}` | ❌ **FIX** — rebuild from attendee data |
| Minister names (org pages) | Meeting rows | `/person/{minister.id}` | ✅ Working |
| Consultancy names | Consultancy rows | `/person/{agency.id}` or `/person/{client.id}` | ✅ Working |
| Donor key people | Below donation rows | `/person/{person.id}` | ❌ Not started — check if API returns IDs |
| Department names | Meeting rows | `/department/{id}` | ❌ Blocked — department pages don't exist yet |
| Corporate connections (orgs directed) | New section | `/person/{org.id}` | ❌ **NEW** — needs bidirectional cross-connections API |

**Hover affordance**: All links use `hover:text-accent transition-colors`.
**Fallback**: Names without actor IDs render as plain text (no dead links).

### Corporate Connections (NEW — cross-connections person→org)

**Intent**: "What companies does this person direct, and do those companies have their own political activity?"

This is the reverse of the org page's "Staff With Political Ties". A politician who is also a company director creates an indirect influence path: the politician receives donations and attends meetings in their political role, while the company they direct lobbies government and attends its own meetings. The cross-connection makes this visible.

**Data source**: `GET /api/v2/actors/{id}/cross-connections/` — returns orgs where this person is a director/PSC/secretary, filtered to only those with political activity (lobbying, meetings, or donations).

**Data scale**: 29,374 people have directorships at politically-active orgs. 213 of those are MPs. Typical result: 1-5 orgs per person.

**Placement**: Between the profile header section and stats strip — same position as "Staff With Political Ties" on org pages.

**Design**:
```
CORPORATE CONNECTIONS

● BXB Caddick Developments — Director
  Hired 5 lobbying agencies

● SHAW HEALTHCARE LIMITED — Director
  Hired 1 lobbying agency

● Pegasus Life — Director
  Donated £10,000 to politicians
```

**Elements per entry**:
- Org name: `font-display font-semibold text-sm`, linked to `/person/{org.id}`
- Role: `text-xs text-ink-muted ml-1.5` (Director, PSC, Secretary)
- Activity summary: `text-xs text-ink-light mt-0.5` — dot-separated list of:
  - `Hired X lobbying {pluralize(X, 'agency', 'agencies')}` (if consultancy_count > 0)
  - `Attended X ministerial {pluralize(X, 'meeting')}` (if meeting_count > 0)
  - `Donated £{formatCurrency(total_donated)} to politicians` (if total_donated > 0)
  - `Received £{formatCurrency(total_received)} in donations` (if total_received > 0)
- Classification: `text-xs text-ink-muted` shown after role (e.g. "Private Limited Company")

**Styling**: Same `pl-3 border-l-2 border-accent/30` left-border treatment as the org page's Political Ties section. Consistent pattern across all profile types.

**Section label**: "CORPORATE CONNECTIONS" — `.section-label` with accent border-bottom.

**States**:
- No corporate connections: Section hidden entirely (no empty placeholder)
- 1 connection: Show without special treatment
- 5+ connections: Consider showing top 5 with "+X more" (unlikely for politicians — most have 1-3)

**Why this matters**: A politician who directs a company that hires lobbying agencies creates a structural conflict of interest. The cross-connection surfaces this without editorial judgment — it just shows the data.

### Empty & Edge Cases
- **No donations**: Omit from stats strip and timeline. No placeholder.
- **No meetings**: Omit from stats strip and timeline.
- **No roles**: Show donations/meetings without role context. Note: "No parliamentary roles recorded."
- **No data at all**: "No recorded activity for this actor." — italic, ink-muted.
- **>COLLAPSE_THRESHOLD events**: Auto-collapse into summary with expand button (current: 5, works well).
- **Duplicate donors**: Same donor appearing with slightly different names (e.g. "Lord Waheed Alli" / "Lord Waheed Ali") — this is a data quality issue, not a design issue. Entity resolution should handle it.

## Copy & Content

### Headlines & Labels
- **Section label**: "POLITICIAN"
- **Role line**: Most significant active role (ministerial > leadership > MP)
- **Party**: Full party name with colour dot ("Conservative", not "Con")
- **Stats labels**: "DONATIONS RECEIVED", "DONATIONS MADE", "MEETINGS", "LOBBYING RELATIONSHIPS" — uppercase, stat-label class
- **Expand/collapse**: "SHOW ALL 103 ▸" / "COLLAPSE ▾" — accent red, expand-label class
- **Empty state**: "No recorded activity for this actor."

### Tone
- Authoritative, neutral. State facts.
- Good: "Leader of the Conservative Party" / "The Prime Minister"
- Bad: "Top Tory" / "Controversial PM"

## Current Pass — Grace Notes + Data Clarity

Concrete implementation specs for the six items committed in §Current Pass Scope. Each is surgical; none require layout rewrites.

### GN1. Specimen Dots on Event Rows (natural history)

A 6px circle preceding every event row, colour-coded by event type. Reads as a field notebook specimen marker.

**Implementation** — `frontend/src/components/ActorTimeline.svelte`, in each event row template:
```svelte
<span
  class="inline-block w-[6px] h-[6px] rounded-full shrink-0 mt-[0.5em] mr-2"
  style={`background:${EVENT_DOT_COLOURS[event.type]}`}
  aria-hidden="true"
></span>
```

**Colour map** (new constant, top of component):
```ts
const EVENT_DOT_COLOURS: Record<string, string> = {
  'donation-received': '#5B7355',  // botanical green
  'donation-made':     '#6B5B4F',  // warm brown
  'meeting':           '#7B9E87',  // sage green
  'role':              '#4A7BA7',  // steel blue
  'consultancy':       '#B87333',  // copper
};
```

**Placement**: Inside the existing event row `<div>`, before the content. The dot must not break the existing `flex-wrap` flow. If the event row already uses `flex`, prepend the dot span. If not, make the row flex and align dot + content.

**States**:
- Default: coloured dot rendered.
- `aria-hidden="true"` — decorative only; not announced to screen readers (the row already has semantic content).

### GN2. Plate Rule on Year Markers (natural history)

A hairline horizontal rule extending from the year text to the right edge of the content column — the plate header treatment from bound natural-history volumes.

**Implementation** — `frontend/src/components/ActorTimeline.svelte`, year marker template:
```svelte
<h2 class="year-marker ...existing classes...">
  <span class="year-label">{group.year}</span>
  <span class="plate-rule" aria-hidden="true"></span>
</h2>
```

**CSS** (add to component `<style>`):
```css
.year-marker {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}
.plate-rule {
  flex: 1;
  height: 1px;
  background-color: rgba(26, 26, 26, 0.1);
  position: relative;
}
```

**Aspirational extension (deferred)**: a `.leader-dot` (4px circle, accent red) at the left end of the rule where it joins the spine. Included in the full Natural History treatment §1 below.

### GN3. Margin Activity Glyphs (natural history)

Three small shape glyphs — ●▲◆ — rendered in the left date gutter beside each year marker, indicating what activity types occurred that year. Function: at-a-glance year classification without reading any data. Pure marginalia.

**Implementation** — `frontend/src/components/ActorTimeline.svelte`:

Compute per year, inside `buildYearGroups`:
```ts
const yearActivityTypes = new Set(
  group.events.map(e => e.type)
);
```

Render in the date gutter column, on the year-marker row:
```svelte
<div class="year-glyphs" aria-hidden="true">
  {#if yearActivityTypes.has('donation-received') || yearActivityTypes.has('donation-made')}
    <span class="glyph" style="color:#5B7355">●</span>
  {/if}
  {#if yearActivityTypes.has('meeting')}
    <span class="glyph" style="color:#7B9E87">▲</span>
  {/if}
  {#if yearActivityTypes.has('role')}
    <span class="glyph" style="color:#4A7BA7">◆</span>
  {/if}
</div>
```

**CSS**:
```css
.year-glyphs {
  font-size: 8px;
  letter-spacing: 0.15em;
  line-height: 1;
}
```

**Placement**: In the 160px date column, aligned right, beside the year marker.

**Edge case**: A year with a single event type renders only one glyph. A year with no events should never have a year marker — current behaviour.

### GN4. Headline Stat Annotation (natural history)

A thin leader line and small annotation beside the headline stat, giving the number context: "from 119 donors · 2003–2022".

**Implementation** — `frontend/src/pages/person/[id].astro`, inside the headline stat column:

```astro
{/* Existing stat figure */}
<span class="stat-figure">{formatCurrency(actor.total_received)}</span>
<span class="stat-label block">Received</span>

{/* New annotation — desktop only */}
{actor.unique_donors_count && donationYearRange && (
  <div class="hidden md:block mt-2 relative">
    <svg class="absolute -left-4 top-1/2 -translate-y-1/2 overflow-visible" width="12" height="1" aria-hidden="true">
      <line x1="0" y1="0.5" x2="12" y2="0.5" stroke="#6b6b6b" stroke-width="1" opacity="0.3" stroke-dasharray="2 2"/>
      <circle cx="12" cy="0.5" r="2" fill="#C54B3C"/>
    </svg>
    <span class="text-[11px] text-ink-muted ml-2 italic">
      from {actor.unique_donors_count} donors · {donationYearRange}
    </span>
  </div>
)}
```

**Data dependencies**:
- `actor.unique_donors_count` — already in `ActorDetailSerializer` ✅
- `donationYearRange` — compute in the page frontmatter: `min(donation.date.year) — max(donation.date.year)`. Iterate `donations.results`; use `COALESCE(accepted_date, reported_date, received_date)`.

**States**:
- Only renders when both `total_received > 0` AND at least one donation has a parseable date.
- Mobile: hidden entirely (`hidden md:block`). Spec intentional — annotation on mobile would clutter.

**Alternative stats** (when headline is not `total_received`):
- `total_donated`: "to {unique_recipients} recipients · {year_range}"
- `meeting_attendance_count`: "with {unique_ministers_met_count} ministers · {year_range}"

### DC1. "MP since {year}" Tenure (data clarity)

Lifetime parliamentary tenure as a sub-line beneath the current role, giving overall orientation ("how long has this person been in politics?").

**Implementation** — `frontend/src/pages/person/[id].astro`, header block:

Compute in frontmatter:
```ts
const parliamentaryStart = parliamentaryRoles.length > 0
  ? parliamentaryRoles
      .map((m: any) => m.start_date)
      .filter(Boolean)
      .sort()[0]  // earliest start date, lexicographic works for ISO prefixes
  : null;
const tenureYear = parliamentaryStart?.slice(0, 4) || null;
```

Render below the existing role line:
```astro
{latestRole && (
  <p class="text-lg text-ink-light font-medium">
    {latestRole}
    {latestRoleDates && <span class="text-sm text-ink-muted ml-2">{latestRoleDates}</span>}
  </p>
)}
{tenureYear && (
  <p class="text-xs text-ink-muted mt-0.5 italic">In politics since {tenureYear}</p>
)}
```

**Copy**:
- Parliamentary role present → "In politics since {year}"
- No parliamentary role but some other political role → don't render (avoid over-claiming)
- Use lexicographic min of `start_date` across all parliamentary memberships (earliest record wins)

**States**:
- No parliamentary memberships: omit entirely.
- Partial date (YYYY only): display as-is ("In politics since 2001").

### DC2. Provenance Link (data clarity)

A small external link in the header gutter pointing to the canonical source (Parliament.uk member profile). Cites our data; matches UKGovScan's provenance pattern but fitted to our aesthetic.

**Implementation** — `frontend/src/pages/person/[id].astro`, below the headline stat column:

```astro
{/* Under the headline stat, provenance breadcrumb */}
{parliamentId && (
  <a
    href={`https://members.parliament.uk/member/${parliamentId}`}
    target="_blank"
    rel="noopener"
    class="block text-[11px] text-ink-muted hover:text-accent transition-colors mt-3 italic"
  >
    Verify on Parliament.uk →
  </a>
)}
```

**Data dependency**: `parliamentId` — pull from `actor.identifiers` if available. If not, skip this item until the backend exposes it (`Identifier.scheme = 'parliamentdotuk'`).

**Backend check needed**: Inspect `/api/v2/actors/{id}/` response for an identifier array. If the field isn't present, add it — single FK walk, already indexed.

**Placement**: Right column under the headline stat annotation. Small, quiet, italic.

**Fallback**: No `parliamentId` → omit link. Future: fall back to a "View on {source}" link keyed to the actor's primary external ID (Companies House for orgs, etc.).

---

## Victorian Natural History Treatment (aspirational / future)

**Status**: These seven techniques represent the full aesthetic vision. The current pass implements **four of them in simplified form** (GN1–GN4 above map to parts of §1, §2, §5 below). The remaining items — continuous spine, hatched year bars, full catalogue numerals — are deferred until the current pass ships and is evaluated.

Role rows and cross-connections already pass the aesthetic check; everything else reads as clean newspaper. Each section below prescribes specific techniques to bring the page into specimen study territory.

### 1. Timeline Spine & Year Plate Headers

**Current**: Year markers are plain Zodiak bold text with no visual connection to each other. Events sit in a bordered content area but there's no continuous spine linking the chronological record.

**Prescribed treatment**:

- **Spine connector**: A continuous `border-l-2 border-ink/10` vertical line running the full height of the timeline, positioned at the left edge of the content column (where the accent-coloured left borders currently start). This creates the visual spine of a bound specimen volume. All event left-borders connect to this spine.

- **Year plate header**: Each year marker becomes a plate header:
  ```
  ── 2024 ──────────────────────────────────────
  ●▲◆
  ```
  - Year in Zodiak bold (existing)
  - Horizontal rule extending from the year to the right edge of the content area
  - A small red specimen dot (`.leader-dot`, `#C54B3C`, 4px) at the junction of the spine and the year rule
  - Implementation: `border-b border-ink/10` on the year heading, `::before` pseudo-element or inline SVG for the dot

- **Margin activity glyphs**: Small icons in the left date column beside each year, showing what types of activity occurred that year:
  - ● (`#5B7355`, 6px circle) = donations present
  - ▲ (`#7B9E87`, 6px triangle) = meetings present  
  - ◆ (`#4A7BA7`, 6px diamond) = role changes present
  - Implementation: Computed from `yearGroup.events` types, rendered as small SVG shapes in the date gutter
  - These function like the marginal annotations in a field notebook — at a glance, you can see which years had which types of activity

### 2. Specimen Dots on Events

**Current**: Events have colour-coded left borders (green=donation, blue=meeting, red=role, gold=consultancy) but no per-event markers.

**Prescribed treatment**:

- Each event row gets a small coloured dot (6px circle) preceding it, positioned at the junction of the spine and the event's left border. The dot colour matches the event type:
  - Donation received: `#5B7355` (botanical green)
  - Donation made: `#6B5B4F` (warm brown)
  - Meeting: `#7B9E87` (sage green)
  - Role: `#4A7BA7` (steel blue)
  - Consultancy: `#B87333` (copper)
- Implementation: Small `<span>` with `rounded-full` positioned at `left: -5px` relative to the left border, or inline SVG circle

### 3. Collapsed Summary → Specimen Catalogue

**Current**: Collapsed donation/meeting summaries list names as plain text with basic formatting.

**Prescribed treatment**:

- **Rank numerals**: Each entry in the top-5 list gets a prominent Zodiak bold numeral:
  ```
  1.  Charles Keymer            5× £130k
  2.  JCB Research              3× £100k
  3.  Lady Bamford              2× £90k
  ```
  - Numeral: `font-display font-bold text-xs text-ink-muted w-5 text-right tabular`
  - Spacing: `gap-2` between numeral and name

- **Plate dividers**: `border-b border-ink/5` between each entry (already present on expanded rows, extend to collapsed summaries)

- **Classification metadata**: For donation summaries, show donation count as secondary annotation. For meeting summaries, show meeting count right-aligned. Already present as counts — ensure they use `tabular-nums text-ink-muted text-right`.

### 4. Year Summary Bar → Hatched SVG

**Current**: The year total header ("£233k from 15 donors") is text-only with a subtle background tint.

**Prescribed treatment**:

- Add a small proportional SVG bar below the total, showing this year's value relative to the politician's largest year:
  ```svg
  <svg width="100%" height="8" class="mt-1">
    <defs>
      <pattern id="hatch-donation" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="4" stroke="#5B7355" stroke-width="1" opacity="0.6"/>
      </pattern>
    </defs>
    <rect width="{yearPercentage}%" height="8" fill="url(#hatch-donation)" stroke="#5B7355" stroke-width="0.5" stroke-opacity="0.3"/>
    <rect x="{yearPercentage}%" width="{100 - yearPercentage}%" height="8" fill="#1a1a1a" opacity="0.03"/>
  </svg>
  ```
- The hatched fill uses the donation-green pattern. Meeting summaries use a sage-green pattern.
- This gives an instant visual sense of whether a year was large or small relative to the politician's career.

### 5. Headline Stat Annotation

**Current**: The £1.1m headline stat sits without context beyond the "RECEIVED" label.

**Prescribed treatment**:

- Add a leader-line annotation connecting the headline stat to a brief contextual note:
  ```
  £1.1m ←---  from 69 donors · 2003—2025
  RECEIVED
  ```
- Implementation: A thin dashed `<line>` in ink-muted (`#6b6b6b`, `opacity: 0.3`, `stroke-dasharray: 2,2`) from the stat figure to a small annotation text positioned nearby.
- Terminal dot: 3px circle in `#C54B3C` at the annotation end.
- The annotation text: `font-body text-[11px] text-ink-muted` — "from {unique_donors} donors · {first_year}—{last_year}"
- On mobile: annotation text appears below the stat instead of beside it (no leader line needed).

### 6. Cross-Connections → Taxonomic Branching (ALREADY PASSING)

The existing `border-l-2 border-accent/30` treatment with indented activity details reads as a specimen study. No changes needed.

### 7. Role Rows (ALREADY PASSING)

The accent-left-border + Zodiak title + classification annotation reads as a specimen mounting. No changes needed.

## Visual References

### Patterns to Follow
- **Section label**: `.section-label` class (global.css line 60)
- **Stats as typography**: `.stat-figure` + `.stat-label` (global.css lines 66-77)
- **Timeline borders**: Existing colour-coded left borders (green=donation, blue=meeting, red=role, gold=consultancy)
- **Expand/collapse**: `.expand-label` class (ActorTimeline.svelte line 559)
- **Hatched SVG fills**: Party bar pattern from `index.astro` `<defs>` block — adapt for donation/meeting types
- **Leader line annotations**: Network graph annotation pattern from `MinisterNetwork.svelte` — adapt for inline stat annotations

### Design System Departures
- **No tabs**: Timeline replaces the tabbed layout from FRONTEND_DESIGN.md Section 6.2. Temporal context is the core insight — separating by category would break the story.
- **Mixed event types**: Single stream of roles + donations + meetings is a new pattern not in the design system.
- **No departures on colour, typography, or spacing**: Standard design system applies.

## Backend Changes Required

### 1. Actor Detail — Unique Count Annotations

**File**: `api/v2/views.py` — `ActorDetailView.get_queryset()`
**File**: `api/v2/serializers.py` — `ActorDetailSerializer`

Add to queryset annotations:
```python
unique_donors_count=Count('received_donations_from__donor', distinct=True),
unique_meeting_orgs_count=Count('ministerial_meetings_as_minister__attendees__actor', distinct=True),
```

Add to serializer fields:
```python
unique_donors_count = serializers.IntegerField(read_only=True)
unique_meeting_orgs_count = serializers.IntegerField(read_only=True)
```

### 2. Cross-Connections — Bidirectional Support

**File**: `api/v2/views.py` — `ActorCrossConnectionsView`

Extend the existing endpoint to handle person→org direction:
- Detect actor type (check `datafetch_person` table)
- If person: query memberships where `person_id=actor_id` with roles Director/PSC/Secretary, annotate orgs with consultancy_count, meeting_count, total_donated, total_received, filter to orgs with activity
- Add `direction` field to response: `"person_to_org"` or `"org_to_person"`
- Add data quality filter to org→person: exclude names < 2 words, exclude role-title names

### 3. Memberships — Fix `on_behalf_of` N+1

**File**: `api/v2/views.py` — `ActorMembershipsView.get_queryset()`

Add `'on_behalf_of'` to the existing `select_related`:
```python
.select_related('person', 'organization', 'post', 'on_behalf_of')
```

## Backend — Items landed from this spec pass

Two backend items surfaced during the constraints phase.

### Resolved — Career Shape waffle data source

**Verdict: Option B** — extend `ActorActivityByYearView` with `category_breakdown`. Landed in `docs/BACKEND_CONSTRAINTS_SNAPSHOT.md` §8. Added to `docs/BACKEND_DESIGN.md` §9 as a piggyback amendment to item #1. See §Fetch-site decision above for the full rationale.

### §8 candidate — `DepartmentMeetingsSummaryView` silent-200

`DepartmentMeetingsSummaryView` at `/api/v2/actors/{id}/meetings-summary/` returns structural zeros when queried for a non-department actor (verified 2026-04-17 on Kemi). This is the silent-empty-200 pattern `BACKEND_DESIGN.md §3.4` / §4 checklist row 1 warns against. To be inserted into `BACKEND_DESIGN.md §8` "Medium — §4 checklist violations":

> **`DepartmentMeetingsSummaryView` returns 200 with zeros for non-department actors.** URL `/api/v2/actors/{id}/meetings-summary/` is polymorphic-over-actor but the implementation is department-only — non-department actors silently receive a structurally-empty success response. Violates §4 row 1 (404 for unknown scope). Fix: Option A — rename URL to `/api/v2/departments/{id}/meetings-summary/` and 404 on non-department actors. Option B — make it genuinely per-actor. Option A is the cheap honest fix.

## Audit Findings (2026-04-13 — Andrew Mitchell #546)

### Spec vs Design System Gaps
- **No donor concentration visualisation**: Flying Lion Ltd donated across 6 years (£90k+), Ms Helena Frost across 2007-2009 (£150k+). These recurring patterns are invisible in the linear timeline. Consider a "top lifetime donors" specimen-style ranked list.
- **No vintage natural history visualisation treatments**: Timeline is purely functional — no annotations, no year-margin event-type indicators, no taxonomic density. Pages read like a well-formatted spreadsheet, not a natural history plate.
- **Corporate Connections missing**: Mitchell directs GR No.30 Limited (3 lobbying agencies) — invisible on the page. Cross-connections API returns empty because person→org not implemented. Now specced above.
- **Donor key people unlinked**: "Lerong, Dr Lu (Director)" appears 4 times as plain text on African Development Corporation donations. `[upstream]` — check if `donor_key_people` API includes actor IDs.
- **No absent-data explanation**: Mitchell was Secretary of State for International Development but has 0 meeting records. Silent absence could be mistaken for a bug.

### Backend Assessment (python-architect)
- Cross-connections endpoint needs bidirectional support (person→org direction)
- Actor type detection: `actor.polymorphic_ctype.model == 'person'` — single indexed lookup
- Person→org query: CTE mirroring existing org→person, ~70 lines SQL
- Entity resolution: both directions should use `COALESCE(canonical_entry_id, id)` for dedup
- Duplicate org: GR No.30 Limited exists as both #51352 and #129017 — handle via canonical_entry in query
- Missing composite index on `membership(person_id, role)` — not blocking at current scale

## Revision History

| Date | Change |
|------|--------|
| 2026-04-12 | Initial generic `actor-profile.md` draft |
| 2026-04-13 | Split into politician-specific spec. Added audit findings, constraints analysis, specific fix instructions. |
| 2026-04-13 | Added Corporate Connections section, cross-connections backend spec, audit findings from Mitchell #546. |
| 2026-04-16 | **Victorian Natural History Treatment** — full aesthetic upgrade spec. 7 sections: timeline spine + plate headers, specimen dots, specimen catalogue summaries, hatched year bars, headline annotation, cross-connections (passing), roles (passing). Based on Lammy #487 audit findings. |
| 2026-04-16 | **Re-audited Johnson #2177.** Scope tightened: rather than full seven-point aesthetic rewrite, ship four natural-history grace notes (specimen dots, plate rules, margin glyphs, headline annotation) plus two UKGovScan-inspired data-clarity additions (MP-since year, Parliament.uk provenance link). Full aesthetic treatment marked aspirational / future. |
| 2026-04-17 | **Career Shape companion viz selected and specced.** Re-audited Kemi #2539; confirmed Career Shape row visual-imbalance (260px coxcomb + 320px `<dl>` + 700px void). Assessed four candidates against d3-viz vocabulary + backend cost + generalisation across audit archetypes. Selected **Donation-Type Composition Bar** (Minard horizontal stacked bar, direct-labelled, leader-line annotation on dominant segment). Rejected meetings-by-dept donut (degenerate for typical minister, poor aesthetic fit). Deferred in-and-out strip + top-donors sparkbar. Added backend addendum: ~10-line extension of shipped `activity-by-year/` endpoint; proposed as piggyback amendment to BACKEND_DESIGN §9 #1 rather than net-new queue item. Also surfaced latent `DepartmentMeetingsSummaryView` silent-200 bug for §8 insertion. Resolved captured-feedback item 3. |
| 2026-04-17 | **Career Shape pass revised (this file).** Second d3-viz review + architect-brief ingestion: (a) reversed stacked bar → **Donation-Type Waffle** (100 patterned tiles, stronger natural-history fit, better legibility at degenerate 94%/6% distributions, better data-visibility expressiveness for `Impermissible Donor` / `Unidentifiable Donor` EC categories); (b) removed the `activity-by-year` backend extension — architect ratified `FundingSummaryView.category_breakdown` at `api/v2/views.py:1268-1281` as the canonical source with no new backend work needed; (c) flagged open architect question on fetch-site (add `/funding-summary/` fetch for politicians vs. extend `activity-by-year` — trade-off between extra request + canonical-naive limitation vs. 10 backend lines + canonical-aware correctness); (d) added §Career Shape Coxcomb — Audit Fixes covering a11y title/desc (CF1), peak-year leader line (CF2), opacity tuning (CF3) — all one-file fixes, shipping together with the waffle. Previous stacked-bar spec moved to revision history only; not preserved inline. |
