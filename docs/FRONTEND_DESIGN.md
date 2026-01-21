# Frontend Design System

**Date:** January 15, 2026
**Version:** 1.1 (Editorial Edition)
**Status:** Living Document
**Based on:** [Frontend Implementation Plan](FRONTEND_IMPLEMENTATION.md), [visual-design-interpretation.html](design/visual-design-interpretation.html)

**Version 1.1 Updates (Editorial Edition):**
- ✨ **Major Typography Upgrade**: Replaced system fonts with Playfair Display (editorial serif) + Inter (modern sans-serif)
- Added network visualization color palette (Section 2.1)
- Refined card design with softer shadows and larger radius (Section 3.1)
- Added Politician Card component specification (Section 3.1.C)
- Expanded timeline/activity feed design (Section 5.2)
- Added comprehensive network graph specifications (Section 5.3)
- Added Politicians Directory page pattern (Section 6.4)
- Added Politician Profile page pattern (Section 6.5)

**Design Philosophy Shift:**
This version embraces **"Editorial Authority meets Data Depth"** - using high-contrast serif typography to signal journalistic trustworthiness while maintaining accessibility and progressive complexity.

---

## 1. Design Philosophy

**"Radical Transparency, Accessible Depth"**

The design language of *UnderTheInfluence* serves two distinct masters: **journalistic authority** and **civic accessibility**. It must look trustworthy enough to be cited by the BBC, yet inviting enough for a concerned citizen to explore on their phone.

### Core Principles

1.  **Data is the Hero**: The interface recedes; data comes forward. We use whitespace and typographic hierarchy to make dense information scannable.
2.  **Intellectual Honesty**: We do not use "dark patterns" or misleading visualizations. Visual hierarchy reflects actual importance, not just aesthetic preference.
3.  **Progressive Complexity**: Surfaces are simple (cards, headlines), but depths are rich (tables, filters, raw data).
4.  **Systemic Consistency**: A politician's face, a party's color, or a donation amount looks the same whether it's on the homepage, a search result, or an editorial article.

---

## 2. Visual Identity

### 2.1 Color Palette

We utilize a modified Bootstrap 5 palette, extended with semantic colors for political entities and data visualizations.

#### Primary Brand Colors
Used for navigation, active states, and primary actions.

| Name | Hex | Usage |
|------|-----|-------|
| **Influence Blue** | `#0f172a` | (Slate 900) Primary navigation, footer backgrounds, text headings. Serious, authoritative. |
| **Action Blue** | `#0d6efd` | (Bootstrap Primary) Links, buttons, active states. |
| **Canvas White** | `#ffffff` | Page backgrounds, card backgrounds. |
| **Wash Gray** | `#f8f9fa` | (Bootstrap Light) Section backgrounds, subtle differentiation. |

#### Political Party Identity (Accessibility Verified)
Party colors are iconic but often fail WCAG AA contrast on white. We use **variants** for text/borders vs. backgrounds.

| Party | Brand Color | Accessible Text Variant (on White) | Background Context |
|-------|-------------|------------------------------------|-------------------|
| **Conservative** | `#0087DC` | `#005B94` | Donation bars, party badges |
| **Labour** | `#E4003B` | `#B0002E` | Donation bars, party badges |
| **Lib Dem** | `#FAA61A` | `#A86500` | Donation bars, party badges |
| **Green** | `#6AB023` | `#3D6E0E` | Donation bars, party badges |
| **SNP** | `#FDF38E` | `#8B8200` | Donation bars, party badges |
| **Reform** | `#12B6CF` | `#0C7A8B` | Donation bars, party badges |

*Rule: Never use raw brand colors for text on white backgrounds unless they pass WCAG AA (4.5:1).*

#### Data Visualization Colors
Used for charts and indicators.

| Name | Hex | Meaning |
|------|-----|---------|
| **Inequality Red** | `#dc3545` | Extreme concentration, "danger" thresholds. |
| **Growth Green** | `#198754` | Positive trends, transparency score high. |
| **Neutral Gray** | `#6c757d` | "Other" categories, null states. |
| **Lobbying Gold** | `#ffc107` | Dual-influence indicators (caution/attention). |

#### Network Visualization Colors
Used specifically for network graphs and relationship mapping.

| Name | Hex | Usage |
|------|-----|-------|
| **Network Node - Person** | `#3b82f6` | (Blue 500) Person nodes in network graphs |
| **Network Node - Organization** | `#10b981` | (Green 500) Organization nodes in network graphs |
| **Network Node - Default** | `#94a3b8` | (Slate 400) Generic/unknown actor type |
| **Network Edge - Donation** | `#8b5cf6` | (Purple 500) Donation relationship edges |
| **Network Edge - Membership** | `#6c757d` | (Gray 600) Organizational membership edges |
| **Network Edge - Lobbying** | `#f59e0b` | (Amber 500) Consultancy/lobbying edges |
| **Cluster Highlight** | `rgba(59, 130, 246, 0.1)` | Semi-transparent blue for cluster boundaries |

*Design rationale: Network colors use saturated, distinct hues to differentiate relationship types at a glance. Opacity variations indicate strength/importance.*

---

### 2.2 Typography (Editorial Edition)

We use a **dual-font strategy** that combines editorial authority with interface clarity:

**Font Stack**:
```scss
// Primary Serif (Editorial Headings)
--font-serif: 'Playfair Display', Georgia, 'Times New Roman', serif;

// Primary Sans-Serif (Interface & Body)
--font-sans: 'Inter', system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
```

**Why These Fonts?**
- **Playfair Display**: High-contrast serif with journalistic authority. Used by major publications for gravitas and readability. Provides instant "serious journalism" credibility.
- **Inter**: Modern sans-serif designed specifically for UI. Variable font with excellent rendering at all sizes. Industry standard for data applications (GitHub, Vercel, Linear).

**Font Loading** (Google Fonts):
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&family=Playfair+Display:ital,wght@0,400..900;1,400..900&display=swap" rel="stylesheet">
```

**Type Scale (Mobile / Desktop)**:

| Level | Size | Weight | Font Family | Letter-Spacing | Usage |
|-------|------|--------|-------------|----------------|-------|
| **Hero** | 2rem / 3.5rem | 800 | Playfair Display | -0.02em | Homepage hero, major page titles |
| **H1** | 1.75rem / 2.5rem | 800 | Playfair Display | -0.02em | Actor names, page headers |
| **H2** | 1.5rem / 2rem | 700 | Playfair Display | -0.01em | Section headers |
| **H3** | 1.25rem / 1.5rem | 600 | Playfair Display | normal | Card titles, subsections |
| **Body** | 1rem / 1rem | 400 | Inter | normal | Standard text, paragraphs |
| **Small** | 0.875rem | 400 | Inter | normal | Metadata, secondary text |
| **Tiny** | 0.75rem | 500 | Inter | 0.05em | Labels, uppercase accents |

**Typography Rules**:

1. **Editorial Headings** (Playfair Display):
   - Use for all `<h1>`, `<h2>`, `<h3>` elements
   - Apply tight letter-spacing (`-0.02em` to `-0.01em`)
   - Heavy weights (700-900) for impact
   - Color: `--influence-blue` (#0f172a)

2. **Interface Text** (Inter):
   - Use for all body copy, UI labels, buttons, metadata
   - Line-height: 1.6 for readability
   - Color: `--influence-slate` (#1e293b) for body, `#64748b` for secondary

3. **Numeric Typography** (CRITICAL):
   ```scss
   .tabular-nums {
     font-variant-numeric: tabular-nums;
     letter-spacing: -0.01em;
   }
   ```
   - Apply to ALL financial figures, donation amounts, stats
   - Ensures alignment in tables and grids
   - Example: `<span class="tabular-nums">£1,240,500.00</span>`

4. **Accent Text** (Editorial Italics):
   ```scss
   .text-accent {
     font-style: italic;
     font-family: var(--font-serif);
     color: var(--action-blue);
   }
   ```
   - Use for emphasis in editorial content
   - Dates in timelines
   - Pull quotes or callouts

---

## 3. Component Design System

### 3.1 Cards (The "Atomic" Unit - Editorial Edition)

Cards are the primary container for entities. The Editorial Edition uses **softer, more sophisticated shadows** and **larger radii** for a premium, journalistic feel.

**Base Card Styles (`.uti-card`)**:
```scss
.uti-card {
  background: white;
  border: 1px solid rgba(15, 23, 42, 0.05);  // Subtle hairline
  border-radius: 20px;  // Larger, softer corners
  box-shadow:
    0 1px 2px rgba(0, 0, 0, 0.01),
    0 10px 15px -3px rgba(15, 23, 42, 0.05);  // Layered depth
  padding: 2rem;  // Generous padding
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);  // Smooth easing

  &:hover {
    transform: translateY(-5px);  // Stronger lift
    box-shadow: 0 20px 25px -5px rgba(15, 23, 42, 0.1);
  }
}
```

**Why This Design?**
- **20px radius**: Modern, friendly, premium (vs. 12px which feels generic)
- **Layered shadows**: Creates realistic depth without being heavy
- **Cubic-bezier easing**: Smoother, more natural motion than linear
- **Stronger hover lift**: More tactile, confirms interactivity

**Background Context**:
- **Page Background**: Wash Gray (`#f8fafc`) - lighter, cleaner
- **Card Background**: Pure white (`#ffffff`) - creates strong elevation

#### A. Actor Card (Person/Organization)
Standard representation of any entity in lists or search.

*   **Avatar**:
    *   **Person**: Circle (`rounded-circle`, 72px diameter in Editorial Edition).
    *   **Organization**: Squircle (`rounded-3`) – better fits corporate logos/crests.
*   **Layout**:
    *   **Horizontal**: Avatar left, Name + Classification center, Stats right
    *   **Vertical (Compact)**: Avatar top, Name + Classification below, Stats bottom
*   **Border Accent**: Optional 5px colored top border for party affiliation

#### B. Stat Card (Metrics)
Used in dashboards and summary strips.

*   **Layout**: Big Number (Top), Sparkline/Trend (Middle), Label (Bottom).
*   **Style**: Minimalist, focusing on the numeral.

#### C. Politician Card (Enhanced Actor Card)
Specialized variant for politician listings. Emphasizes party affiliation and current role.

*   **Avatar**: Circle (`rounded-circle`) for person photos.
*   **Party Color Accent**: Left border (4px) in party's brand color OR pastel background (party color at 10% opacity).
*   **Layout (Full Mode)**:
    *   **Header**: Photo + Name + Current Position (e.g., "MP for Bristol West")
    *   **Badges**: Party badge + Role badge ("Minister", "Shadow Cabinet", etc.)
    *   **Stats Row**: Donations Received | Donations Made
*   **Layout (Compact Mode)**: Photo + Name + Party badge only
*   **Party Badge Style**: Pastel background with accessible text variant
    *   Example (Labour): `background: #fae6ea; color: #b0002e; border-radius: 1rem; padding: 0.25rem 0.75rem`

**Why Different from Actor Card?**
Politicians need party context immediately visible. The party color accent provides at-a-glance affiliation without overwhelming the design.

---

### 3.2 UI Elements

#### Badges & Chips
We avoid heavy solid-color badges in favor of **Pastel/Subtle** badges (`dashboard-02.png`) for better legibility and lower visual noise.

*   **Structure**: Light background (10-15% opacity), dark text (100% opacity).
*   **Example (Labour)**: `bg-red-100` (`#fae6ea`) text `text-red-800` (`#b0002e`).
*   **Shape**: `rounded-pill` for status, `rounded` for categories.

#### Filter Panel (The "Control Room")
*   **Background**: White card.
*   **Input Style**: Standard Bootstrap form controls, but with refined borders (`#ced4da`).

---

## 4. Layout & Spacing

### 4.1 Grid System
We adhere strictly to the **Bootstrap 5 12-column grid**.

*   **Container**: `container-xl` (Max width 1320px) for most pages.
*   **Page Background**: `#f8f9fa` (Wash Gray) is mandatory to support the white card design.

### 4.2 Spacing Scale (Rem-based)
Consistent spacing ensures rhythm.

*   **Tight**: `0.5rem` (8px) - Between list items, tags.
*   **Card**: `1.5rem` (24px) - Standard card padding.
*   **Section**: `4rem` (64px) - Vertical space between major page sections.

---

## 5. Visualizations

Charts must be comprehensible at a glance but reveal detail on hover (`dashboard-03.png`).

### 5.1 Rules of Engagement
1.  **Direct Labeling**: Avoid legends where possible; label lines/bars directly.
2.  **Tooltips**: Essential for "long tail" data where bars are small.
3.  **Palette**: Use desaturated/sophisticated variants of political colors to avoid visual vibration.

### 5.2 Specific Charts

#### The "Activity Feed" (Timeline)
*   **Inspiration**: `timeline.png` (cardiology timeline design)
*   **Structure**: Vertical line connecting chronological nodes
*   **Visual Elements**:
    *   **Timeline Spine**: 2px vertical line in Neutral Gray (`#6c757d`)
    *   **Event Nodes**: Circles (24px diameter) with icon glyphs inside
        *   Donation: `£` symbol or money bag icon
        *   Lobbying: Handshake icon
        *   Membership: Building/organization icon
        *   Appointment: Star or badge icon
    *   **Node Colors**: Match event type (donation = purple, lobbying = amber, etc.)
    *   **Connection Lines**: Horizontal connector from spine to event card (1px, same color as node)
*   **Grouping**: Events grouped by Year/Month with section headers
*   **Event Cards**: Mini cards with:
    *   Date (small, gray text)
    *   Event description (e.g., "Received £50,000 from Unite the Union")
    *   Related party badge (if applicable)
*   **Responsive**: On mobile, cards stack directly on timeline; on desktop, alternating left/right

**Use Cases**: Politician profile "Timeline" tab, donor activity history, organization event chronology

#### The "Concentration" Bar (Pareto)
*   **Concept**: A stacked bar showing the "Whale" vs. "Minnow" split.
*   **Style**: Top segment in **Inequality Red**, rest in **Neutral Gray**.
*   **Labels**: Direct labeling with percentage annotations
*   **Interactivity**: Hover to see exact figures and donor names

### 5.3 Network Visualizations

#### Network Graph (Force-Directed Layout)
**Inspiration**: D3.js force simulations, but with political data context

**Core Elements**:
*   **Nodes**:
    *   **Size**: Proportional to `log10(total_donations + 1)` — prevents outlier domination
    *   **Minimum**: 15px radius (legibility)
    *   **Maximum**: 40px radius (prevents overwhelming small nodes)
    *   **Color**: Person (blue), Organization (green), by actor type
    *   **Stroke**: White 2px outline for separation
    *   **Label**: Last name only for people, abbreviated name for orgs (prevents clutter)
*   **Edges (Relationships)**:
    *   **Color**: Donation (purple), Membership (gray), Lobbying (amber)
    *   **Width**: Proportional to relationship strength (donation value, # of connections)
    *   **Minimum**: 1px (low-value relationships visible but subtle)
    *   **Maximum**: 5px (major relationships prominent)
    *   **Opacity**: 60% to reduce visual noise
*   **Layout Algorithm**:
    *   D3 force simulation with:
        *   **Link force**: Stronger relationships = shorter distance
        *   **Charge force**: -300 repulsion (prevents overlap)
        *   **Center force**: Keeps graph centered
        *   **Collision force**: 30px radius (prevents node overlap)

**Interactions**:
*   **Drag**: Rearrange nodes (pin with double-click)
*   **Zoom/Pan**: Standard D3 zoom behavior (0.5x - 3x scale)
*   **Click Node**: Highlight ego network, show detail panel
*   **Hover Node**: Enlarge + show tooltip with stats
*   **Hover Edge**: Highlight + show relationship details

**Controls**:
*   **Degrees Slider**: 1-3 hops (default 2)
*   **Relationship Filter**: Toggle donation/membership/lobbying edges
*   **Layout Preset**: "Force" | "Hierarchical" | "Circular"

**Legend**:
*   Visual key for node types and edge types (positioned top-right)

**Performance Considerations**:
*   Limit to 100 nodes max (paginate or cluster beyond that)
*   Use canvas rendering for >50 nodes (SVG for smaller networks)
*   Debounce force simulation updates

#### Cluster View (Community Detection)
**Concept**: Highlight tightly-connected groups within the network

*   **Visual Treatment**: Convex hulls around clusters (semi-transparent party color fill)
*   **Cluster Labels**: Centered text showing cluster name (e.g., "Trade Union Donors")
*   **Color Coding**: Each cluster gets a distinct pastel background
*   **Interaction**: Click cluster to expand/focus on that subgraph

#### Influence Path Diagram (Sankey)
**Concept**: Show money flows from donor → intermediaries → politician through the network

**Why Sankey (Not Tree/Hierarchy)?**
- Sankey diagrams excel at showing **flow magnitude** through paths
- Width visually encodes donation amounts — immediately shows "big money" routes
- Supports **convergence** (multiple donors → one recipient) and **divergence** (one donor → multiple recipients)
- Familiar from energy/resource flow visualizations

**Visual Design**:
*   **Layout**: Strict left-to-right flow in columns
    *   **Column 1**: Source donors
    *   **Columns 2-N**: Intermediate actors (if multi-hop)
    *   **Final Column**: Target recipient (politician)
*   **Node Representation**:
    *   Rectangles (not circles) with actor name
    *   Height proportional to total flow through that node
    *   Color by actor type (person blue, organization green)
*   **Link/Flow Representation**:
    *   **Width**: Proportional to £ value (logarithmic scale for extreme outliers)
    *   **Color**: Gradient from donor's party color → recipient's party color
        *   Neutral gray if no party affiliation
        *   For multi-hop: intermediate color blending
    *   **Opacity**: 50% to allow overlaps to be visible
*   **Labels**:
    *   Actor names inside node rectangles (truncate if needed)
    *   Donation amounts on hover (tooltip)
    *   Total flow amounts on node labels
*   **Multiple Paths**: All paths shown simultaneously (stacked flows)
*   **Interactivity**:
    *   **Hover link**: Highlight path, show exact amount
    *   **Hover node**: Highlight all flows through that node
    *   **Click node**: Filter to show only paths involving that actor
    *   **Toggle**: Show top N paths only (default top 10 by value)

**Implementation Notes**:
- Use D3.js `d3-sankey` plugin
- Set `nodeWidth: 20px` for consistent node sizing
- Set `nodePadding: 10px` for vertical spacing
- Enable `iterations: 32` for optimal layout
- Responsive: Stack vertically on mobile (<768px)

**Data Requirements**:
- Input: Array of paths from `/api/v2/actors/{id}/paths-to/{target}/`
- Transform to Sankey format:
  ```javascript
  {
    nodes: [{id: "123", name: "Unite the Union", party: null}],
    links: [{source: 0, target: 1, value: 50000}]
  }
  ```

**Use Cases**:
1. "How does money from Corporation X reach Politician Y?"
2. "Show all indirect funding routes to this MP"
3. "Trace lobbying firm's influence through donation chains"

**Example**:
```
Hedge Fund A (£500K) ━━━━━━━━┓
                             ┣━━━> Consulting Firm B (£800K) ━━━> MP Jones (£800K)
Trade Union C (£300K) ━━━━━━━┛
```

---

## 6. Page Types & Patterns

### 6.1 Homepage
*   **Pattern**: "Dashboard First". Hero → Metrics → Narrative → Exploration.
*   **Key**: High-contrast metrics strip to establish the scale of data immediately.

### 6.2 Entity Profile (Person/Org)
*   **Pattern**: "Identity Header". Large name, clear classification badges.
*   **Tabs**: "Overview", "Donations", "Lobbying", "Network".
*   **Sidebar**: Related entities, "See Also" (CMS links).

### 6.3 Search Results / Explore
*   **Pattern**: "Faceted Browsing".
*   **Left Column**: Sticky Filter Panel.
*   **Right Column**: Infinite scroll or paginated cards.
*   **Empty States**: "No donors found matching these criteria." with a "Reset Filters" CTA.

### 6.4 Politicians Directory
*   **Pattern**: "Grouped Listings". Three-tier hierarchy: Government Status → Party → Individuals
*   **Page Structure**:
    *   **Header**: Page title "Politicians" + total count
    *   **Filter Sidebar** (Left, 3 columns): Party, Role (MP/Minister), Status, Date range
    *   **Content Area** (Right, 9 columns): Three sections:
        1. **Government** (MPs + Ministers in governing party/coalition)
        2. **Opposition** (MPs in non-governing parties)
        3. **Other** (Former MPs, non-MPs with political activity)
*   **Within Each Section**:
    *   **Party Subheadings**: "Labour (213)" with party color accent bar
    *   **Politician Grid**: 3-4 columns of compact PoliticianCards
*   **Empty State**: "No politicians match these filters" with party/role suggestions
*   **Responsive**: Stack to 2 columns on tablet, 1 column on mobile

**Why This Pattern?**
Users primarily navigate UK politics by government vs. opposition, then by party. This mirrors mental models and reduces cognitive load compared to alphabetical listing.

### 6.5 Politician Profile (Enhanced Entity Profile)
*   **Pattern**: "Identity + Network". Emphasizes relationships over biography.
*   **Header Section**:
    *   Large photo (150px circle)
    *   Name (H1) + Current Position (H3)
    *   Party Badge + Role Badges ("Minister", "Shadow Cabinet", etc.)
    *   Quick Stats Row: Donations Received | Donations Made | Network Size
*   **Tab Navigation**:
    1. **Overview**: Bio, key stats, recent activity summary
    2. **Network** (Default View): Interactive network graph
    3. **Donations Received**: Paginated table/cards
    4. **Donations Made**: Paginated table/cards (if any)
    5. **Timeline**: Chronological activity feed
    6. **Lobbying**: Connected consultancy relationships (if any)
*   **Sidebar** (Right, 3 columns):
    *   Related Politicians (network neighbors)
    *   Party Information card
    *   Constituency Map (for MPs)
    *   Related Articles (from CMS)
*   **Responsive**: Sidebar moves below tabs on mobile

**Why Network Tab is Default?**
The network view immediately answers "Who influences this politician?" — the core question of the site. Bio information is secondary context.

---

## 7. Accessibility Checklist

*   **Focus Indicators**: Default browser focus outline preserved or enhanced (thick blue ring), never removed.
*   **Contrast**: Text `< Small` size must be `#495057` or darker on white.
*   **Motion**: `prefers-reduced-motion` media query respected (disable hover lifts/chart animations).
*   **Semantic HTML**: Proper `<h1>` through `<h6>` hierarchy, `<ul>` for lists, `<button>` for actions.
*   **Data Tables**: `<th>` with scope attributes, captions for complex data.
