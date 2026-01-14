# Frontend and Editorial Strategy - Phase 3 (REVISED)

This document outlines the strategy for modernizing the UnderTheInfluence frontend and integrating Wagtail CMS with the political influence dataset, incorporating architectural feedback on interaction models, data coupling, and signal-to-complexity prioritization.

---

## 1. Frontend Architecture: The "Island" Model

To balance SEO, performance, and maintainability, we will move away from a monolithic "SPA vs. Multi-page" debate toward a hybrid interaction-driven model.

### 1.1 Technical Stack
- **Build System:** **Vite** via `django-vite`. Vite will build a single JS bundle for interaction "islands," served selectively in Django templates.
- **UI Framework:** **Bootstrap 5** for core layout and utility classes.
- **JS Framework:** **React** (or Preact for smaller footprint) for high-interaction islands.
- **Visualization:** **D3.js** or **Recharts** for data-heavy components.

### 1.2 Splitting by Interaction Model
- **Server-Rendered (Django/Wagtail Templates):**
    - Article and Analysis pages.
    - Static "About," "Methodology," and "Topic Hub" headers.
    - **Actor Profiles:** Primarily server-rendered text + summary widgets (Data Cards).
- **React Islands:**
    - **Search & Filters:** Real-time filtering, faceted navigation, and autocomplete.
    - **High-Interaction Views:** Network/flow views and time-scrubbing timelines.
    - **Data Tables:** Complex, virtualized tables with client-side sorting/filtering.

---

## 2. Interactive Features: Signal vs. Complexity

Visualizations are ranked by their robustness against data imperfections and their narrative "signal."

### 2.1 High Priority (Build Early)
- **Power Concentration (Pareto):** Stark 65/1.3 split visualization.
- **Top Donor Leaderboards:** Deeply filterable tables.
- **Recipient Dependency:** Visualizing the funding share from top donors.
- **Interactive Timelines:** Aggregated donation trends by year/quarter.

### 2.2 Medium Priority (Build After Overlap Stability)
- **Industry Strategy Scatter Plot:** Only once sector/industry classification is auditable and stable.

### 2.3 Low Priority / Highest Risk (Build Last)
- **Influence Triangle (Sankey):** Constrained to top N flows, requiring a time window, and allowing exclusions (e.g., "unions/public funds"). Treated as a visualization of *overlap*, not a proxy for "influence."

---

## 3. Wagtail Editorial Integration

Wagtail will be coupled to the data layer via stable identifiers and neutral join models to prevent core model contamination.

### 3.1 Data-Aware StreamField Blocks
Blocks will reference stable identifiers and query types rather than ad-hoc logic:
- **Block Schema:** Stores `actor_id`, `query_type` (enum), `params` (JSON for filters/time windows), and optional `cached_snapshot`.
- **Reproducible Callouts:** Editorial "Fact Blocks" (e.g., "Unite accounts for 92%...") must include query metadata, dataset version timestamps, and last-computed dates to be "journalist-proof."

### 3.2 Neutral Join Models (`editorial.ActorMention`)
To keep Popolo models clean, relationships between CMS pages and Actors will live in a neutral app:
- **ActorMention Model:** `page_id`, `actor_id`, `relationship_type` (mentioned/profiled/etc.), and `weight` (editorial importance).
- This allows Actor profiles to pull "Related Analysis" without the `datafetch` app needing to know about Wagtail.

### 3.3 Topic Pages
Managed as curated hubs with:
- **Membership Rules:** Based on classification or keywords.
- **Curation Override:** Editors can explicitly "pin" or "ban" entities from a topic to prevent nonsense drift.

---

## 4. UI Architecture Recommendations

### 4.1 "Data Cards" as the Universal Unit
Every key entity and metric will be built as a reusable **Card component** (e.g., `ActorCard`, `OverlapSummaryCard`). These cards will be used across Actor profiles, Topic pages, and embedded in articles via StreamField.

### 4.2 "Filters as First-Class Objects"
A standardized filter schema will be used across the UI, API, and editorial blocks:
- Time Range (Start/End)
- Include/Exclude Donor Types (Trade Union, Company, Public Fund, etc.)
- Recipient Type (MP, Peer, Party)
- Minimum Value Threshold
- In-kind Toggle

---

## 5. Implementation Roadmap (Updated)

### Phase 2.4: The API Contract
Before any UI work, define 10–15 stable read endpoints covering:
- Leaderboards (Top donors/recipients).
- Actor profile summary cards.
- Donations time series (aggregated).
- Overlap queries (clients who donate).
- Dependency metrics.

### Phase 2.5: Frontend Foundation
- Integrate Vite + Bootstrap 5.
- Build the "Data Card" library.
- Implement Search & Filter island.

### Phase 3: Identity & Search
- Unify Actor identity (canonical names, aliases, facets).
- Unified Elasticsearch indexing (Wagtail content + Actors + Computed metrics).

### Phase 4: Complex Visualizations
- Power Concentration and Timelines.
- (Conditional) Industry Scatter and Sankey.