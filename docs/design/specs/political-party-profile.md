# Political Party Profile — Design Spec

**Date**: 2026-04-13
**Status**: Implemented
**Author**: Claude + Warren
**Audit**: Pre-audit found page couldn't load (27k donations, cartesian join). Fixed: Subquery annotations, aggregate endpoint, conditional fetching.
**Constraints**: Performance analysis complete. All fixes applied.

## Overview

The political party profile answers: **"Where does this party's money come from?"**

Parties are unique: they're almost purely donation recipients. The Conservative Party has 27,633 donations totalling £607m but zero meetings, zero memberships, zero lobbying relationships. The page must communicate the funding story — who gives, how much, how often, and how that changes over time.

The current generic profile page cannot render party data — 27k donation rows overwhelm both the API serialization and Astro SSR. This spec defines a fundamentally different approach: **aggregate-first** data fetching with drill-down capability.

**Data profile** (from the database):

| Party | Donations | Total | Unique Donors | Date Range |
|-------|-----------|-------|---------------|------------|
| Conservative | 27,633 | £607m | 7,300+ | 2001–2025 |
| Liberal Democrats | 18,768 | £156m | 5,000+ | 2001–2025 |
| SNP | 815 | £31m | 400+ | 2001–2025 |
| Reform UK | 248 | £30m | 100+ | 2018–2025 |
| Co-operative | 665 | £21m | 200+ | 2001–2025 |

## Layout & Hierarchy

### Grid Structure
- Container: `max-w-[1400px] mx-auto px-6`
- Header: 12-col grid, `lg:col-span-8` + `lg:col-span-4` (name left, headline stat right)
- Funding sections: single column, full width
- Top donors: two-column grid on desktop

### Content Zones (top to bottom)

1. **Section Label** (~30px) — "POLITICAL PARTY" in accent red
2. **Profile Header** (~180px) — Party name, headline stat (total received)
3. **Stats Strip** (~80px) — Donation count, unique donor count, date range
4. **Funding by Year** (~300px) — Horizontal bar chart or timeline showing annual totals
5. **Top Donors** (~400px) — Ranked list of top 20 donors by lifetime total, linked
6. **Funding by Donor Type** (~200px) — Breakdown: individuals vs companies vs unions vs trusts
7. **Funding by Donation Type** (~150px) — Cash vs non-cash vs public funds
8. **Recent Donations** (~variable) — Timeline of most recent 50 individual donations (same ActorTimeline component, but limited)

### Responsive Behavior
- **Desktop (1440px)**: Full layout. Top donors in 2 columns. Bar chart full width.
- **Tablet (768px)**: Top donors single column. Chart compressed.
- **Mobile (375px)**: Full stack. Stats strip stacks vertically. Chart scrollable horizontally.

## Component Inventory

### Profile Header (Static Astro)
- **Type**: Static Astro
- **Purpose**: Establish party identity and headline funding scale
- **Data source**: `/api/v2/actors/{id}/`

**Elements**:
- Section label: "POLITICAL PARTY"
- Name: Zodiak 5xl/6xl (`Conservative and Unionist Party`)
- Headline stat: `stat-figure` (e.g. "£607m RECEIVED") — the total scale of funding

### Stats Strip (Static Astro)
- **Type**: Static Astro
- **Purpose**: Quick inventory of funding dimensions
- **Data source**: `/api/v2/actors/{id}/funding-summary/` (new endpoint)

**Stats to show**:
1. Total donations: "27,633 donations"
2. Unique donors: "from 7,312 donors"
3. Date range: "2001 — 2025"
4. Average donation: "£22k average" (total / count)

### Funding by Year (Svelte `client:visible`)
- **Type**: Svelte island with D3
- **Purpose**: Show how funding changes over time — election years spike, opposition years dip
- **Aesthetic**: **Lithographic Texture**. Bars must use a **stippled/hatched fill** instead of flat digital colors. 
- **Annotations**: Hand-written-style callouts with **leader lines** for election years (e.g., "2019 Election").

**Design**: Horizontal bar chart, one bar per year. Bar width proportional to total. Year labels on left axis. Total on right. Election years annotated. This is the **centrepiece visualisation** — it immediately communicates the funding rhythm.

**States**:
- Default: all years visible, scrollable if >15 years
- Hover: highlight bar with a subtle "paper" glow, show tooltip with total + donor count + top donor name

### Top Donors (Static Astro)
- **Type**: Static Astro
- **Purpose**: "Who are the biggest funders of this party?" — the power question
- **Aesthetic**: **Specimen Catalogue**. Rank numbers as bold Zodiak numerals. Classification labels (Person, Company, Trust) as specimen tags. Left accent border as a plate divider.

**Design**: Ranked specimen-style list. Each entry:
```
1.  John Sainsbury                                               £11.5m
    15 donations · 2004 — 2023
    Person
```


### Funding by Donor Type (Static Astro)
- **Type**: Static Astro
- **Purpose**: "Is this party funded by individuals, companies, or institutional money?"
- **Data source**: `by_donor_type` from funding-summary endpoint

**Design**: Compact proportional display. Each type as a row:
```
Individuals           £351m   58%   5,263 donors
Companies             £155m   25%   2,171 donors
Public Funds           £52m    9%      20 sources
Unincorporated Assns   £30m    5%     441 donors
```

Percentage could be shown as a proportional bar or as a number. The key insight is the split — are individuals or corporates the dominant funders?

### Funding by Donation Type (Static Astro)
- **Type**: Static Astro
- **Purpose**: "How is the money given?" — cash vs non-cash vs public funds
- **Data source**: `by_type` from funding-summary endpoint

**Design**: Simple breakdown, same format as donor type.

### Recent Donations Timeline (Svelte `client:visible`)
- **Type**: Svelte (reuse ActorTimeline)
- **Purpose**: "What's happening now?" — the most recent activity
- **Data source**: `/api/v2/actors/{id}/donations-received/?limit=50` (existing endpoint)

**Design**: Standard ActorTimeline component with year groups. Limited to 50 most recent donations. Shows individual donor names (linked), amounts, dates. This is the drill-down from the aggregate views above.

**Note**: For parties with 27k+ donations, this shows "Showing 50 of 27,633 events" — acceptable as a preview. Full browse would need timeline pagination (separate feature).

## Data Communication

### Page-Level Story

**"The Conservative Party has received £607m in donations from 7,312 donors since 2001 — dominated by wealthy individuals (58%) and companies (25%), with election years seeing dramatic funding spikes."**

The headline stat (£607m) communicates absolute scale. The yearly chart communicates rhythm and political context. The top donors list communicates concentration — is funding broad-based or dominated by a few large donors?

### Element-by-Element Intent

| Element | Communicative Intent | Visual Treatment |
|---------|---------------------|-----------------|
| Headline stat (£607m) | "The sheer scale of this party's funding" | 4rem Zodiak bold, right-aligned |
| Stats strip (27,633 / 7,312 / 2001-2025) | "How many gifts, from how many people, over what period" | Centred stat figures with context labels |
| Funding by year chart | "When does money flow — elections, leadership contests, government vs opposition" | Horizontal bars, full width, election year annotations |
| Top donors list | "Who holds the purse strings? Is funding concentrated or distributed?" | Ranked specimen list, top 20, linked names |
| Donor type breakdown | "Individual vs institutional — who is this party beholden to?" | Proportional rows with percentages |
| Recent donations | "What's happening now — who's giving today?" | Standard timeline, 50 most recent |

### Data Display Rules
- **Money**: `formatCurrency` — £607m, £11.5m, £22k. Never raw decimals.
- **Dates**: Year ranges: "2004 — 2023". Individual dates: "31 Oct 2024".
- **Counts**: Always with context: "27,633 donations from 7,312 donors"
- **Percentages**: Whole numbers for >1%, one decimal for <1%. "58%" not "57.87%"

### Comparisons & Sorting
- Top donors: sorted by total value descending (who gives most)
- Yearly funding: chronological (temporal pattern)
- Donor type: sorted by total value descending (who dominates)

### Relationships & Direction
- Money flows FROM donors TO party — direction is clear in the "DONATED TO" label on timeline rows
- Each donor name links to their profile (interconnectedness)
- "House of Commons Fees Office" is the #1 donor — this is public funds, not private donations. The donor type breakdown disambiguates this.

### Interconnectedness (CRITICAL)

| Entity | Location | Link target |
|--------|----------|-------------|
| Donor names (top donors list) | Top Donors section | `/person/{donor.id}` |
| Donor names (recent timeline) | Recent Donations section | `/person/{donor.id}` |
| Donor names (collapsed summaries) | Timeline year groups | `/person/{donor.id}` |
| Donor key people | Below corporate donations | `/person/{person.id}` |

### Empty & Edge Cases
- **New party with few donations** (e.g. Reform UK, 248 donations): Skip the yearly chart (not enough data for a meaningful pattern). Show top donors and recent donations directly.
- **Party with zero donations**: "No recorded donations for this party." — italic, ink-muted.
- **Very large donor names**: Truncate with `title` attribute.

## Backend Changes Required

### New Endpoint: `/api/v2/actors/{id}/funding-summary/`

A dedicated aggregate endpoint returning pre-computed funding data in a single response. This replaces the slow `donations-received/?limit=200` for the party page's primary display.

```python
class ActorFundingSummaryView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        top_donors = (
            Donation.objects.filter(recipient_id=pk)
            .values('donor_id', donor_name=F('donor__name'))
            .annotate(total_value=Sum('value'), donation_count=Count('id'),
                      first_date=Min(Coalesce('accepted_date', 'received_date')),
                      last_date=Max(Coalesce('accepted_date', 'received_date')))
            .order_by('-total_value')[:20]
        )

        by_year = (
            Donation.objects.filter(recipient_id=pk)
            .annotate(year=ExtractYear(Coalesce('accepted_date', 'received_date', 'reported_date')))
            .values('year')
            .annotate(total=Sum('value'), count=Count('id'), unique_donors=Count('donor_id', distinct=True))
            .order_by('year')
        )

        by_donor_type = (
            Donation.objects.filter(recipient_id=pk)
            .values(donor_type=Coalesce('donor__organization__classification', Value('Person')))
            .annotate(total=Sum('value'), count=Count('id'), unique_donors=Count('donor_id', distinct=True))
            .order_by('-total')
        )

        by_type = (
            Donation.objects.filter(recipient_id=pk)
            .values('donation_type')
            .annotate(total=Sum('value'), count=Count('id'))
            .order_by('-total')
        )

        return Response({
            'total_donations': Donation.objects.filter(recipient_id=pk).count(),
            'total_value': Donation.objects.filter(recipient_id=pk).aggregate(Sum('value'))['value__sum'],
            'unique_donors': Donation.objects.filter(recipient_id=pk).values('donor_id').distinct().count(),
            'top_donors': list(top_donors),
            'by_year': list(by_year),
            'by_donor_type': list(by_donor_type),
            'by_type': list(by_type),
        })
```

**Performance**: All aggregations on indexed columns. Expected response time <100ms for any party.

**URL**: Add to `api/v2/urls.py`: `path('actors/<int:pk>/funding-summary/', views.ActorFundingSummaryView.as_view())`

### Frontend: Conditional Data Fetching

The `[id].astro` page should detect Political Party classification and fetch differently:

```astro
// For political parties: fetch aggregate summary instead of raw donations
const isParty = !isPerson && actor.classification === 'Political Party';
if (isParty) {
  fundingSummary = await fetch(`${API_URL}/actors/${id}/funding-summary/`);
  // Still fetch donations-received with limit=50 for the recent timeline
}
```

## Copy & Content

### Headlines & Labels
- **Section label**: "POLITICAL PARTY"
- **Headline stat label**: "RECEIVED"
- **Section labels**: "TOP DONORS", "FUNDING BY YEAR", "FUNDING BY DONOR TYPE", "FUNDING BY TYPE", "RECENT DONATIONS"
- **Empty state**: "No recorded donations for this party."

### Tone
- Authoritative, neutral. "Conservative and Unionist Party" not "the Tories".
- Let numbers tell the story. "£607m from 7,312 donors" — no editorial judgment.

## Visual References

### Patterns to Follow
- Stats strip pattern from politician profile
- Section label pattern (`.section-label` class)
- Top donors list: adapt the "Top Clients by Political Activity" two-column grid from lobbying agency pages
- Recent timeline: standard ActorTimeline component

### Vintage Natural History Treatment

The party profile is an opportunity to create the site's strongest natural history aesthetic:

- **Yearly funding chart**: Horizontal bars with stippled fills, Zodiak year labels, election year annotations as leader-line callouts. Inspired by Nightingale's rose diagrams — temporal data with clear visual weight.
- **Top donors list**: Ranked like a specimen catalogue. Rank numbers as bold Zodiak numerals. Classification labels (Person, Company, Trust) as specimen tags. Left accent border as plate divider.
- **Donor type breakdown**: Could be a simple proportional bar or a radial/polar segment — the key is showing relative scale with the natural history palette (botanical green for individuals, copper for companies, steel blue for institutional).

### Design System Departures
- **New component: Funding by Year chart** — Svelte + D3 bar chart. New pattern, but follows the D3-for-math + Svelte-for-rendering approach established in MinisterNetwork.
- **Aggregate data fetching** — Political parties skip the standard 8-endpoint parallel fetch in favour of a single aggregate endpoint. This is a performance necessity, not a design choice.

## Revision History

| Date | Change |
|------|--------|
| 2026-04-13 | Initial spec. Performance constraints identified: page cannot load with raw donation rows. Aggregate endpoint required. |
| 2026-04-13 | Implemented. Funding-summary endpoint with Redis caching. Conditional data fetching (3 API calls instead of 8). Top private donors separated from union funding and public funds. Clickable funding-by-year with per-year top 5 donors. Government/opposition/election annotations. Labour data fix (Person→Organization). Cartesian join fix on ActorDetailView. client:only timeline for parties. Synthetic timeline data from per-year top donors. |
