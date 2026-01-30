# Frontend Design System

**Date:** January 28, 2026
**Version:** 2.0 (Natural History Edition)
**Status:** Living Document
**Inspiration:** Victorian natural history illustrations, vintage newspaper infographics, scientific taxonomy plates

**Version 2.0 Updates (Natural History Edition):**
- **Major Aesthetic Shift**: From modern editorial to vintage natural history information design
- Warm cream/parchment backgrounds replacing stark whites
- Earth-tone color palette with muted reds, browns, and botanical greens
- Dense, layered information design inspired by scientific illustrations
- Network visualizations styled as taxonomic relationship diagrams
- Typography emphasizing timeless authority over modern minimalism

**Design Philosophy Shift:**
This version embraces **"Clean Data Journalism"** - the precision of Victorian natural history illustration meets the restraint of modern newspaper design. Dense information, minimal chrome.

---

## 1. Design Philosophy

**"Let the Data Breathe"**

The design language of *UnderTheInfluence* combines two traditions: the meticulous classification systems of Victorian naturalists, and the clean typography-driven layouts of quality newspapers. No decorative boxes. No heavy shadows. Just clear hierarchy through type, whitespace, and restrained color.

### Core Principles

1. **Typography Over Chrome**: Establish hierarchy through font size, weight, and spacing - not boxes and borders.
2. **Density Without Clutter**: Pack information tightly, but give it room to breathe. Like a well-designed newspaper spread.
3. **One Accent Color**: A single red (`#C54B3C`) for section labels and highlights. Everything else is ink on paper.
4. **Warm Paper, Dark Ink**: The off-white background (`#FAF9F6`) and near-black text (`#1a1a1a`) create comfortable contrast.
5. **Data as the Hero**: Visualizations and numbers take center stage. The interface recedes.

### Inspirations

- **Natural History Illustration**: Ernst Haeckel's *Kunstformen der Natur*, Audubon's bird studies - the precision of scientific classification applied to political relationships
- **Victorian Infographics**: Charles Minard's flow maps, Florence Nightingale's rose diagrams - data visualization as a serious discipline
- **Quality Newspapers**: The Economist, Financial Times - clean typography, dense but readable, restrained use of color
- **Scientific Diagrams**: Botanical taxonomy charts, anatomical plates - everything labeled, nothing ambiguous

---

## 2. Visual Identity

### 2.1 Color Palette

A restrained palette that lets data and typography do the work. Warm paper background, near-black ink, and a single accent color.

#### Surface & Text Colors

| Name | Hex | Usage |
|------|-----|-------|
| **Paper** | `#FAF9F6` | Page background - warm off-white |
| **Ink** | `#1a1a1a` | Primary text, headlines |
| **Ink Light** | `#4a4a4a` | Secondary text, body copy |
| **Ink Muted** | `#6b6b6b` | Tertiary text, metadata, sources |

#### Accent Color

| Name | Hex | Usage |
|------|-----|-------|
| **Accent Red** | `#C54B3C` | Section labels, highlights, selection, leader dots |

This red is used sparingly - for section labels, text selection, and small accent elements. It's the only "brand" color.

#### Network Visualization Colors
Muted, natural tones that work together harmoniously.

| Name | Hex | Usage |
|------|-----|-------|
| **Minister Node** | `#B85450` | Minister/politician nodes (warm red) |
| **Donor Node** | `#5B7355` | Donor organization/person nodes (botanical green) |
| **Director Node** | `#4A7BA7` | Director relationship nodes (steel blue) |
| **PSC Node** | `#B87333` | Persons of Significant Control (copper) |
| **Donation Edge** | `#2C2C2C` | Donation relationship lines (dark, 30% opacity) |
| **Role Edge** | `#8B7355` | Director/membership lines (tan, dashed) |
| **Key Connector Ring** | `#DAA520` | Bridge node highlight (goldenrod) |

#### Political Party Colors (Muted)
Party colors are desaturated to avoid visual noise while remaining recognizable.

| Party | Muted Color | Usage |
|-------|-------------|-------|
| **Conservative** | `#4A7BA7` | Nodes, badges |
| **Labour** | `#B85450` | Nodes, badges |
| **Lib Dem** | `#C9A227` | Nodes, badges |
| **Green** | `#5B7355` | Nodes, badges |
| **SNP** | `#C9B84A` | Nodes, badges |
| **Reform** | `#4A8B9E` | Nodes, badges |

---

### 2.2 Typography

We use a **clean dual-font strategy** from Fontshare - contemporary fonts with editorial authority:

**Font Stack**:
```scss
// Display/Headlines - Editorial serif
--font-display: 'Zodiak', serif;

// Body/UI - Clean geometric sans
--font-body: 'Satoshi', sans-serif;
```

**Why These Fonts?**
- **Zodiak**: A contemporary serif with sharp, elegant letterforms. Authoritative without being stuffy. Variable weight for flexibility.
- **Satoshi**: Clean geometric sans-serif designed for interfaces. Highly legible at all sizes, neutral but not cold.

Both fonts are from [Fontshare](https://www.fontshare.com/) (free for commercial use).

**Font Loading** (Self-hosted):
```scss
/* Zodiak - Display/Headlines */
@font-face {
  font-family: 'Zodiak';
  src: url('/fonts/Zodiak-Variable.woff2') format('woff2');
  font-weight: 400 700;
  font-style: normal;
  font-display: swap;
}

/* Satoshi - Body/UI */
@font-face {
  font-family: 'Satoshi';
  src: url('/fonts/Satoshi-Variable.woff2') format('woff2');
  font-weight: 400 700;
  font-style: normal;
  font-display: swap;
}
```

**Type Scale**:

| Level | Size | Weight | Font | Usage |
|-------|------|--------|------|-------|
| **Display** | 4rem | 700 | Zodiak | Hero headlines, major page titles |
| **H1** | 2.5rem | 700 | Zodiak | Section headers, actor names |
| **H2** | 1.75rem | 600 | Zodiak | Card titles, subsections |
| **H3** | 1.25rem | 600 | Zodiak | Tertiary headers |
| **Body** | 1rem | 400 | Satoshi | Paragraphs, UI text |
| **Small** | 0.875rem | 400 | Satoshi | Metadata, captions |
| **Label** | 0.75rem | 600 | Satoshi | Section labels, uppercase |
| **Stat Figure** | 4rem | 700 | Zodiak | Large numbers, metrics |

**Typography Patterns**:

1. **Headlines** (Zodiak):
   - Tight letter-spacing (`-0.02em`) for display sizes
   - Color: `#1a1a1a` (ink)

2. **Body Text** (Satoshi):
   - Line-height: 1.5-1.6 for comfortable reading
   - Color: `#1a1a1a` for primary, `#4a4a4a` for secondary

3. **Section Labels**:
   ```scss
   .section-label {
     font-family: 'Satoshi', sans-serif;
     font-size: 0.75rem;
     font-weight: 600;
     text-transform: uppercase;
     letter-spacing: 0.1em;
     color: #C54B3C;  // Accent red
   }
   ```

4. **Tabular Numbers** (for data):
   ```scss
   .tabular {
     font-variant-numeric: tabular-nums;
   }
   ```

---

## 3. Component Design System

**Design Principle: Typography Over Chrome**

We avoid decorative boxes, heavy shadows, and ornate borders. Information hierarchy is established through typography, whitespace, and subtle color accents. This follows the clean newspaper tradition - let the content speak.

### 3.1 Stats as Typography (Not Cards)

Large metrics are displayed as pure typography, not contained in boxes.

```scss
.stat-figure {
  font-family: 'Zodiak', serif;
  font-size: 4rem;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: #1a1a1a;
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-family: 'Satoshi', sans-serif;
  font-size: 0.875rem;
  font-weight: 400;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #6b6b6b;
}
```

### 3.2 Section Labels

Red accent labels mark section boundaries - the primary use of accent color.

```scss
.section-label {
  font-family: 'Satoshi', sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #C54B3C;  // Economist red
}
```

### 3.3 Rules & Dividers

Simple horizontal lines - no ornamentation.

```scss
.rule {
  border-top: 1px solid rgba(26, 26, 26, 0.1);
  margin: 2rem 0;
}

.rule-thick {
  border-top: 2px solid #1a1a1a;
  margin: 2rem 0;
}
```

### 3.4 Accent Borders

Left border accent for emphasis (pull quotes, highlighted sections).

```scss
.accent-border-left {
  border-left: 4px solid #C54B3C;
  padding-left: 1rem;
}
```

### 3.5 Annotations

Small explanatory text with leader lines pointing to visualizations.

```scss
.annotation {
  font-family: 'Satoshi', sans-serif;
  font-size: 0.875rem;
  line-height: 1.4;
  max-width: 200px;
  color: #4a4a4a;
}

.leader-dot {
  fill: #C54B3C;  // Red dot at annotation endpoint
}
```

---

## 4. Layout & Spacing

### 4.1 The Newspaper Grid

We embrace dense, multi-column layouts inspired by broadsheet newspapers.

- **Container**: Max width 1400px, generous side margins
- **Page Background**: `--parchment` (#F5F0E8) always
- **Columns**: 12-column grid, but favor asymmetric layouts (8+4, 5+7, 3+6+3)

### 4.2 Spacing Scale

| Name | Size | Usage |
|------|------|-------|
| **Hairline** | 0.25rem (4px) | Between inline elements |
| **Tight** | 0.5rem (8px) | List items, badge margins |
| **Base** | 1rem (16px) | Default paragraph spacing |
| **Comfortable** | 1.5rem (24px) | Card padding, section gaps |
| **Generous** | 2.5rem (40px) | Major section breaks |
| **Spread** | 4rem (64px) | Page section dividers |

---

## 5. Visualizations

### 5.1 Design Principles

Inspired by Victorian scientific illustration and quality newspaper graphics:

1. **Direct Labeling**: Label elements on the visualization, not in separate legends where possible
2. **Density With Clarity**: Pack information tightly, but maintain clear visual hierarchy
3. **Muted Palette**: Earth tones that work together, no jarring contrast
4. **Annotation**: Explanatory text with leader lines pointing to specific elements

### 5.2 Network Graph

The centerpiece visualization - a force-directed relationship diagram.

**Node Styling**:
- Solid fill with subtle cream stroke
- Size encodes importance/value
- Color encodes type (minister, donor, director, PSC)

**Edge Styling**:
- Thin lines (1-2px) in muted colors
- Donation links: solid, dark
- Role links: dashed, tan
- Opacity reduces visual noise

**Key Connector Highlight**:
- Gold ring (`#DAA520`) around bridge nodes
- Bridge nodes = entities connecting 2+ ministers
- Slight repulsion keeps them visible

**Interactivity**:
- Hover: Enlarge node, highlight all connected nodes (2-hop traversal for minister→org→director/PSC chains)
- Click: Pin detail panel, dim unconnected nodes
- Connected highlighting uses reduced opacity on non-connected nodes

**Legend**:
- Bottom-left position
- Uses actual SVG elements matching the graph
- Compact, unobtrusive

### 5.3 Radial Charts

For categorical breakdowns (party donations, donor types), use radial/polar layouts inspired by Florence Nightingale.

**Style**:
- Segments radiate from center
- Width encodes value (not radius - avoids area distortion)
- Muted colors from the specimen palette
- Direct labeling on or near segments

### 5.4 Timeline

Chronological data displayed as a vertical annotated timeline.

**Visual Elements**:
- Central spine: 2px line in muted color
- Event nodes: Small circles in event-type color
- Connection lines: Horizontal stems to event descriptions
- Year markers: Bold labels
- Event descriptions: Date + description + value

---

## 6. Page Patterns

### 6.1 Homepage

**Pattern**: "The Front Page" - newspaper-style density with clear hierarchy.

**Sections**:
1. **Header**: Site title (Zodiak), navigation, search
2. **Hero**: Large headline + subhead establishing the investigation
3. **Metrics Strip**: Key numbers as large typography (donations tracked, total value, dual-influence count)
4. **Lead Visualization**: The Government Ministers Network - full-width force-directed graph
5. **Content Columns**: Three-column layout with Top Recipients + Deep Dive cards
6. **Methodology**: Source attribution and explanation
7. **Footer**: Links, legal, data access

**Top Recipients Column**:
- Ranked list of top 20 MP donation recipients
- Each entry: rank, name, party affiliation, total received, donation count
- Links to individual actor pages

**Deep Dive Section** (spans 2 columns):
Three analysis teaser cards, each with:
- Section label (red uppercase)
- Headline + editorial quote
- Data visualization preview
- "Explore" link with arrow

| Card | Visualization Style |
|------|---------------------|
| **Party Funding** | Horizontal bar chart showing donations by party |
| **Ministerial Access** | Department list with meeting counts + top attendees |
| **Lobbying Influence** | Organization list with their agencies (see below) |

**Lobbying Clients Display Pattern**:
Shows top clients and the agencies they've hired:
```
SANOFI                           16 agencies
M&F Health · Incisive Health · Brands2Life · ...

NOVARTIS                         14 agencies
Weber Shandwick · Burson · FTI Consulting · ...
```
- Organization name (bold) with agency count on right
- Full list of agencies below, separated by middle dots (·)
- Left border accent in muted red

### 6.2 Entity Profile

**Pattern**: Typography-driven single-entity view.

**Layout**:
- **Header**: Large name (Zodiak), section label, key stats
- **Sidebar**: Related entities, external links
- **Main**: Tabbed content (Network, Donations, Timeline)
- **Annotations**: Contextual notes where needed

### 6.3 Network Visualization Page

**Pattern**: Full-canvas interactive diagram.

**Layout**:
- **Canvas**: Full-width network visualization on paper background
- **Legend**: Bottom-left, always visible
- **Controls**: Top-right, collapsible settings panel
- **Detail Panel**: Right sidebar, slides in on selection

---

## 7. Implementation Notes

### Current Implementation (MinisterNetwork.svelte)

The network graph currently implements:

**Node Types & Colors**:
- Ministers: `#B85450` (warm red)
- Donors: `#5B7355` (botanical green)
- Directors: `#4A7BA7` (steel blue)
- PSCs: `#B87333` (copper)

**Key Features**:
- Bridge node detection (nodes connecting 2+ ministers)
- Gold ring highlight for key connectors (`#DAA520`)
- Slight repulsion between bridge nodes for visibility
- Force-directed layout with configurable physics
- Detail panel on node selection showing:
  - For ministers: name, position (parsed from role), department, total received
  - For donors: name, classification, total donated, donation count
  - For directors/PSCs: name, role, connected organizations
- 2-hop connected node highlighting on hover

**Settings Panel**:
- Global repulsion strength
- Minister repulsion (keeps ministers spread)
- Link distances (donation vs role)
- Gravity (x/y center pull)
- Collision padding
- Key connector highlight toggle

---

## 8. Accessibility

Clean design and accessibility go hand in hand:

- **Contrast**: All text meets WCAG AA (4.5:1 for body, 3:1 for large)
- **Color Independence**: Never rely on color alone - use shapes, labels, patterns
- **Focus States**: Visible focus rings on all interactive elements
- **Motion**: Respect `prefers-reduced-motion` for animations
- **Screen Readers**: Proper ARIA labels, especially for data visualizations
- **Keyboard Navigation**: Full keyboard support for network graph

---

## Appendix: Color Reference

### Quick Copy Palette

```scss
// Surfaces
--bg-paper: #FAF9F6;

// Text
--ink: #1a1a1a;
--ink-light: #4a4a4a;
--ink-muted: #6b6b6b;

// Accent
--accent-red: #C54B3C;

// Network nodes
--minister-node: #B85450;
--donor-node: #5B7355;
--director-node: #4A7BA7;
--psc-node: #B87333;
--key-connector: #DAA520;

// Network edges
--edge-donation: rgba(44, 44, 44, 0.3);
--edge-role: #8B7355;

// Party colors (muted)
--party-conservative: #4A7BA7;
--party-labour: #B85450;
--party-libdem: #C9A227;
--party-green: #5B7355;
--party-snp: #C9B84A;
--party-reform: #4A8B9E;
```

### CSS Custom Properties (from global.css)

```css
html {
  font-family: 'Satoshi', sans-serif;
  color: #1a1a1a;
  background-color: #FAF9F6;
}

h1, h2, h3, h4, h5, h6 {
  font-family: 'Zodiak', serif;
}

::selection {
  background-color: #C54B3C;
  color: white;
}
```
