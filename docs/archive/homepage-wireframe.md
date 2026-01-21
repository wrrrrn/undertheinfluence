# Under The Influence - Homepage Wireframe & Design

**Date**: January 2026
**Status**: Phase 1 IMPLEMENTED (Key Metrics + Party Breakdown)
**Target Audience**: Journalists, researchers, and citizens investigating political influence

---

## Implementation Status

### ✅ PHASE 1 COMPLETE: Homepage Essentials (January 2026)
- **StatsGrid Component**: 4-card metrics strip with live API data
  - Total donations, total value, concentration (65% from 1.3%), dual influence count
  - Filters: Date range, min value, donor type
  - Timestamp provenance ("Data as of...")
- **PartyBreakdown Component**: Donation breakdown by political party
  - Official party colors (Conservative blue, Labour red, etc.)
  - Responsive grid layout (2-3 columns)
  - Filters: Date range, min value, donor type
  - Shows: Total received, donor count, average donation per party
- **FilterPanel Component**: URL-synchronized filter controls
  - Date range picker, minimum value selector, donor type chips
  - URL state management (shareable, bookmarkable filters)
  - All islands respond to filter changes simultaneously
- **Wagtail CMS Integration**: Custom StreamField blocks
  - `StatsGridBlock`, `PartyBreakdownBlock`, `TopDonorsLeaderboardBlock`, `FilterPanelBlock`
  - Drag-and-drop page building for editors
- **API Endpoints**: All filtering support implemented
  - `/api/v2/aggregates/stats/` - Homepage statistics (with filters)
  - `/api/v2/aggregates/party-donations/` - Party breakdown (with filters)
  - `/api/v2/aggregates/top-donors/` - Top donors leaderboard (with filters, pagination)

### 🚧 IN PROGRESS: Phase 2-4
- SearchBar with autocomplete
- Featured Insight editorial blocks
- Dual Influence Spotlight
- MPs & Lords interests integration
- Network visualizations

### 📋 PENDING: Later Phases
- Time series charts
- Geographic mapping
- Advanced network graphs

---

## Design Goals

1. **All audiences**: Serve journalists (investigation), researchers (analysis), and citizens (transparency)
2. **Key stories**:
   - Breakdown by top political parties
   - Individual donor stories
   - MPs and Lords interests + their donors
   - Lobbyists and their lobbying/donation activity
3. **Homepage approach**: Mix of dashboard metrics, narrative introduction, and exploration jumping-off point
4. **Navigation**: Home | Explore | Lobbyists
5. **Headline data**:
   - 21,301 total donors
   - 119,599 donation records
   - £1.3B+ total value
   - 65% from just 1.3% of donors (277 donors = extreme concentration)
   - 62 organizations with dual influence (lobby AND donate)

---

## Homepage Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ HEADER                                                           │
│ Logo: Under The Influence    [ Home | Explore | Lobbyists ]    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ HERO SECTION                                                     │
│                                                                  │
│   Follow the Money in UK Politics                               │
│   Track £XXX million in political donations from 21,000 donors  │
│   and uncover the lobbying connections behind the funding       │
│                                                                  │
│   [ Search for an MP, donor, or organization... ]               │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ KEY METRICS STRIP (4 stat cards in a row)                        │
│ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐        │
│ │  119,599  │ │  £1.3B+   │ │    62     │ │    65%    │        │
│ │ Donation  │ │  Total    │ │ Dual      │ │ From Top  │        │
│ │  Records  │ │ Donated   │ │ Influence │ │  1.3%     │        │
│ └───────────┘ └───────────┘ └───────────┘ └───────────┘        │
│                                                                   │
│ Note: Emphasizing 1.3% concentration (277 donors) is more        │
│ impactful than "top 10%" and "journalist-proof"                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ FEATURED INSIGHT (Editorial block)                               │
│                                                                   │
│  "The Concentration Problem"                                      │
│  Just 277 donors (1.3%) contribute 65% of all political funding. │
│  Here's who they are and what they want.                         │
│                                                                   │
│  [→ Read the full analysis]                                      │
│                                                                   │
│  Note: Should include source_query metadata to link back to      │
│  /explore/ with filters preset (e.g., top 1.3% donors)           │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ EXPLORE BY PARTY (Interactive cards)                             │
│                                                                   │
│  See who funds each major party                                  │
│                                                                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │
│  │ Labour  │ │  Tory   │ │ Lib Dem │ │  Other  │              │
│  │ £XXXm   │ │ £XXXm   │ │ £XXXm   │ │ £XXXm   │              │
│  │ XXX     │ │ XXX     │ │ XXX     │ │ XXX     │              │
│  │ donors  │ │ donors  │ │ donors  │ │ donors  │              │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘              │
│       ↓           ↓           ↓           ↓                      │
│  [Explore]   [Explore]   [Explore]   [Explore]                 │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ WHO'S WHO (3 column layout)                                      │
│                                                                   │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│ │ Biggest      │ │ MPs & Lords  │ │ Lobbyist-    │            │
│ │ Donors       │ │ Interests    │ │ Donors       │            │
│ │              │ │              │ │              │            │
│ │ 1. David S.  │ │ Top 10 MPs   │ │ Who lobbies  │            │
│ │    £47.9m    │ │ receiving    │ │ AND donates? │            │
│ │              │ │ most         │ │              │            │
│ │ 2. Unite     │ │              │ │ XXX orgs     │            │
│ │    £12.5m    │ │ [View All]   │ │ with dual    │            │
│ │              │ │              │ │ influence    │            │
│ │ [See Top 50] │ │              │ │ [Explore]    │            │
│ └──────────────┘ └──────────────┘ └──────────────┘            │
│                                                                   │
│ ⚠️  Note: Biggest Donors should flag public funds (House of     │
│ Commons, Electoral Commission) which appear in top donors due to │
│ "Short Money" grants but may confuse citizens looking for        │
│ private influence. Consider filtering them out or marking them.  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ LATEST ANALYSIS (Editorial stream)                               │
│                                                                   │
│  • "How Trade Unions Fund Labour" - 15 Jan 2026                  │
│  • "The Rise of Crypto Donations" - 10 Jan 2026                  │
│  • "Lord Sainsbury's £47M Political Project" - 5 Jan 2026        │
│                                                                   │
│  [View All Articles]                                             │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ FOOTER                                                            │
│ About | Methodology | Data Sources | API | GitHub                │
└──────────────────────────────────────────────────────────────────┘
```

---

## Design Principles

### 1. Progressive Disclosure
Start broad with key metrics, then allow drilling down into specific areas:
- **First glance**: Hero + 4 key stats (donors, total £, dual influence, concentration)
- **Second level**: Party breakdown, top lists
- **Deep dive**: Click through to Explore page with full filtering

### 2. Multiple Entry Points
Every user type has a path in:
- **Journalists**: Featured insight + Latest analysis
- **Researchers**: Search bar + Explore by party
- **Citizens**: "Who's Who" sections (biggest donors, MPs interests, dual influence)

### 3. Editorial + Data Mix
Combine curated storytelling with live data:
- **Editorial**: Featured insights, latest articles
- **Live data**: Metrics, party cards, top donor lists
- **Interactive**: All powered by React islands (ConcentrationChart, filters, etc.)

### 4. Clear Calls-to-Action
Every section drives to deeper exploration:
- Party cards → Explore with party filter preset
- Top donors → Full leaderboard with filters
- Dual influence → Lobbyists page
- Featured insight → Full article
- Latest analysis → Article archive

---

## Page Structure Details

### Key Metrics Strip
**Implementation**: 4 StatCard components in a row

```jsx
<StatCardsRow>
  <StatCard
    value="119,599"
    label="Donation Records"
    icon="database"
    live={true}  // Fetches from /api/v2/aggregates/stats/
    timestamp="2026-01-15"  // "Data as of" for intellectual honesty
  />
  <StatCard
    value="£1.3B+"
    label="Total Donated"
    icon="pound"
    live={true}
    timestamp="2026-01-15"
  />
  <StatCard
    value="62"
    label="Dual Influence"
    subtext="Donors who also lobby"
    icon="link"
    live={true}
    timestamp="2026-01-15"
  />
  <StatCard
    value="65%"
    label="From Top 1.3%"
    subtext="277 donors control 65% of funding"
    icon="chart"
    variant="danger"  // Red to highlight extreme inequality
    live={true}
    timestamp="2026-01-15"
  />
</StatCardsRow>
```

**Important**: Each StatCard with `live={true}` should:
- Fetch from materialized views (`/api/v2/aggregates/stats/`) for performance
- Display a "Data as of" timestamp to maintain intellectual honesty with researchers
- Timestamp should update when materialized views refresh (daily or after imports)

### Featured Insight
**Implementation**: Wagtail StreamField block (RichTextBlock + ImageBlock + LinkBlock)

Allows editors to:
- Highlight current investigation
- Link to full article
- Update regularly with new stories

**Critical**: Use FactCalloutBlock for statistical claims:
- When highlighting stats like "1.3% concentration," include `source_query` metadata
- The block should link back to `/explore/` with filters preset (e.g., `?value_percentile=99`)
- This maintains data provenance and allows users to verify claims
- Example: Clicking "277 donors" opens Explore page filtered to show those exact 277 donors

### Explore by Party
**Implementation**: React island fetching party aggregates

```jsx
<PartyBreakdown>
  {parties.map(party => (
    <PartyCard
      name={party.name}
      totalDonated={party.total}
      donorCount={party.donor_count}
      topDonor={party.top_donor}
      onExplore={() => navigate(`/explore?recipient_party=${party.id}`)}
    />
  ))}
</PartyBreakdown>
```

**API needed**: `/api/v2/aggregates/by-party/`
Returns total donations, donor count, top donor for each major party

### Who's Who Section

#### Column 1: Biggest Donors
- TopDonorsLeaderboard component (limit=10, compact mode)
- Click donor → goes to actor profile
- "See Top 50" → goes to /explore

#### Column 2: MPs & Lords Interests
- TopRecipientsLeaderboard (limit=10, filter to person recipients)
- Shows who's receiving the most donations
- "View All" → /explore?recipient_type=person

#### Column 3: Lobbyist-Donors
- TopDonorsLeaderboard (limit=10, filter: has_lobbying=true)
- Highlights dual influence
- "Explore" → /lobbyists

### Latest Analysis
**Implementation**: Wagtail blog/article listing

Query recent articles from Wagtail:
```python
# In HomePage.get_context()
context['latest_articles'] = ArticlePage.objects.live().order_by('-date')[:3]
```

---

## Other Pages (Brief Specs)

### Explore Page (`/explore/`)

**Purpose**: Full data exploration with filtering

**Layout**:
```
┌─────────────────────────────────────────┐
│ HEADER                                   │
└─────────────────────────────────────────┘
┌──────────┬──────────────────────────────┐
│          │                              │
│ FILTER   │   TOP DONORS LEADERBOARD     │
│ PANEL    │   (with pagination)          │
│          │                              │
│ • Date   │   [Full TopDonorsLeaderboard │
│ • Amount │    with all filters applied] │
│ • Type   │                              │
│ • Party  │                              │
│          │   [Pagination controls]      │
│          │                              │
├──────────┴──────────────────────────────┤
│                                          │
│   CONCENTRATION CHART                    │
│   (responds to filters above)            │
│                                          │
└──────────────────────────────────────────┘
```

**Features**:
- All filters from FilterPanel
- Results update live
- URL state preserved (shareable filtered views)
- Export to CSV button

---

### Lobbyists Page (`/lobbyists/`)

**Purpose**: Focus on dual influence (lobbying + donations)

**Layout**:
```
┌─────────────────────────────────────────┐
│ HERO: The Lobbying-Donation Connection  │
│ XXX organizations both lobby AND donate │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ FILTER: has_lobbying=true preset        │
│ + additional lobbying-specific filters  │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ DUAL INFLUENCE LEADERBOARD              │
│ Actors sorted by: donation + lobbying   │
│ Shows both amounts side-by-side         │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ NETWORK GRAPH (future)                  │
│ Visual connections between:             │
│ - Lobbying agencies                     │
│ - Clients (who also donate)             │
│ - Recipients (MPs, parties)             │
└─────────────────────────────────────────┘
```

**API needed**:
- `/api/v2/aggregates/dual-influence/`
- Returns actors with both donation totals AND lobbying activity

---

### Actor Profile Pages (`/person/<id>/`, `/organization/<id>/`)

**Purpose**: Deep dive on individual actors

**Current state**: Basic template exists in `datafetch/templates/`

**Enhancements needed**:
```
┌─────────────────────────────────────────┐
│ HERO SECTION                             │
│ [Photo] Name                             │
│ Classification (e.g., "Trade Union")     │
│ Active: 2010-present                     │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ KEY STATS (3 cards)                      │
│ ┌────────┐ ┌────────┐ ┌────────┐       │
│ │ £XXXm  │ │ £XXXm  │ │  Yes   │       │
│ │Donated │ │Received│ │Lobbyist│       │
│ └────────┘ └────────┘ └────────┘       │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ DONATION HISTORY (Timeline chart)        │
│ Bar chart showing donations over time    │
│ Filterable by recipient                  │
└─────────────────────────────────────────┘
┌──────────────┬──────────────────────────┐
│ DONATED TO   │ RECEIVED FROM            │
│ (if donor)   │ (if recipient)           │
│              │                          │
│ List of      │ List of                  │
│ recipients   │ donors                   │
└──────────────┴──────────────────────────┘
┌─────────────────────────────────────────┐
│ LOBBYING ACTIVITY (if applicable)        │
│ Agencies hired, clients represented      │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ RELATED ARTICLES                         │
│ Editorial pieces mentioning this actor   │
│ (via ActorMention model - Phase 5.2)     │
└─────────────────────────────────────────┘
```

---

## Components Needed (Summary)

### New components to build:
1. **StatCard** - Metric display (live or static)
2. **PartyCard** - Party funding summary with CTA
3. **PartyBreakdown** - Grid of party cards
4. **SearchBar** - Autocomplete search (person/org/party)
5. **DualInfluenceCard** - Shows both donation + lobbying for one actor
6. **TimelineChart** - D3.js timeline of donations over time
7. **NetworkGraph** - D3.js force-directed graph (future)

### Existing components to enhance:
1. **TopDonorsLeaderboard** - Add "compact mode" variant
2. **ConcentrationChart** - Already done ✓
3. **FilterPanel** - Add party filter
4. **ActorCard** - Already done ✓

### API endpoints needed:
1. `/api/v2/aggregates/by-party/` - Party funding breakdown
2. `/api/v2/aggregates/dual-influence/` - Lobbyist-donors ranking
3. `/api/v2/aggregates/stats/` - Overall stats for homepage metrics
4. `/api/v2/actors/search/` - Autocomplete search
5. `/api/v2/actors/<id>/timeline/` - Donation history over time

---

## Implementation Priority

### Phase 1: Homepage Essentials (Week 1)
1. StatCard component + Key metrics strip
2. Party breakdown API + PartyCard component
3. Search bar (basic version)
4. Layout structure with all sections

### Phase 2: Explore Page Polish (Week 2)
1. Enhanced FilterPanel (add party filter)
2. Improve TopDonorsLeaderboard compact mode
3. Export to CSV functionality

### Phase 3: Lobbyists Page (Week 3)
1. Dual influence API endpoint
2. DualInfluenceCard component
3. Lobbyists page layout

### Phase 4: Actor Profiles (Week 4)
1. Timeline chart component
2. Enhanced actor profile template
3. "Donated to" / "Received from" sections

### Phase 5: Network Visualizations (Future)
1. Network graph component
2. Interactive exploration

---

## Design System Notes

### Color Palette
- **Primary**: Bootstrap default blue (links, CTAs)
- **Danger/Warning**: Red for inequality metrics (concentration %)
- **Success**: Green for positive metrics
- **Parties**: Use official party colors **with WCAG contrast validation**
  - Labour: Red (#E4003B)
  - Conservative: Blue (#0087DC)
  - Lib Dem: Orange (#FAA61A) ⚠️ **Often fails WCAG AA contrast on white backgrounds**
  - Green: Green (#6AB023)
  - **Important**: Test all party colors for 4.5:1 contrast ratio before using for text
  - Consider darker variants for text or use party colors only for backgrounds/borders

### Typography
- **Headings**: Keep Bootstrap defaults
- **Body**: Clean, readable (current setup is good)
- **Numbers/Stats**: Bold, large for emphasis

### Spacing
- **Sections**: Generous whitespace between major sections
- **Cards**: Consistent padding (1.5rem)
- **Grid**: Bootstrap grid (12 columns)

---

## Mobile Considerations

### Responsive breakpoints:
- **Desktop** (>992px): Full 3/4 column layouts as shown
- **Tablet** (768-991px): 2 column layouts, stack party cards
- **Mobile** (<768px): Single column, simplified metrics

### Mobile-first optimizations:
1. Key metrics: Show 2x2 grid instead of 1x4 row
2. Party cards: Vertical stack
3. Who's Who: Collapse to accordion or tabs
4. FilterPanel: Collapsible drawer
5. Charts: Responsive SVG, simplified on small screens

---

## Accessibility

### WCAG 2.1 AA compliance:
- **Color contrast**: All text meets 4.5:1 ratio
- **Keyboard navigation**: All interactive elements tabbable
- **Screen readers**: Proper ARIA labels on all islands
- **Focus indicators**: Visible focus states
- **Alt text**: All images and charts described

### Specific considerations:
- **Charts include text descriptions** and accessible alternatives
- **Responsive charts**: ConcentrationChart and other D3.js visualizations must have:
  - Simplified "mobile-first" views for small screens
  - Example: On mobile, complex Pareto chart → simple "Top 1% vs. Others" bar chart
  - Text-based summary always visible alongside visual
  - SVG elements should degrade gracefully
- Tables have proper headers
- Forms have labels
- Skip navigation link for screen readers

---

## Next Steps

1. **Review this wireframe** - Get feedback, adjust as needed
2. **Create component library** - Build StatCard, PartyCard, etc.
3. **Build homepage** - Implement section by section
4. **API development** - Add missing endpoints (by-party, dual-influence)
5. **User testing** - Test with journalists, researchers
6. **Iterate** - Refine based on feedback

---

**Document Status**: Draft - awaiting review and approval
**Last Updated**: January 15, 2026
