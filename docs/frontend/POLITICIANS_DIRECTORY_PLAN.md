# Politicians Directory Implementation Plan

**Feature:** Politicians Directory Page (`/politicians/`)
**API Endpoint:** `/api/v2/politicians/`
**Status:** Ready for Development

---

## 1. Overview

The Politicians Directory provides a browseable, filterable list of all UK politicians (MPs, Lords, Ministers). It serves as the primary entry point for exploring individual political actors.

**Key Requirements:**
- Server-rendered initial state (SEO)
- Client-side filtering (Party, Role, Government Status)
- "Grouped" view mode (Government vs Opposition)
- Performant list rendering (virtualization or pagination)

---

## 2. Components Structure

### 2.1 Page Layout (`frontend/islands/PoliticianDirectory.tsx`)

A new Island component that manages the state for the entire page.

```tsx
<PoliticianDirectory>
  <FilterSidebar />
  <PoliticianList />
</PoliticianDirectory>
```

### 2.2 Filter Sidebar (`frontend/components/PoliticianFilters.tsx`)

Filters:
- **Search**: Text input (debounced)
- **Role**: Buttons/Chips (All | MP | Lord | Minister)
- **Party**: Dropdown (populated from `/api/v2/parties/`)
- **Status**: Buttons (Government | Opposition | Other)

### 2.3 Politician Card (`frontend/components/PoliticianCard.tsx`)

Enhanced version of `ActorCard` with specific political context:
- **Header**: Avatar + Name
- **Badges**: Party (colored), Role ("MP for Bristol West")
- **Stats**: Total Donations (small sparkline or number)
- **Visuals**: Party color border-left

### 2.4 List View (`frontend/components/PoliticianList.tsx`)

Renders the grid of cards. Supports two modes:
1.  **Flat List**: Simple grid, sorted by name.
2.  **Grouped View**: Sections for "Government", "Opposition", "Other".

---

## 3. State Management

Re-use `useFilterStore` but extend it or create a specific slice for politicians.

**New URL Params:**
- `role_type` (mp, lord, minister)
- `party` (id)
- `govt_status` (government, opposition)
- `q` (search)

---

## 4. Implementation Steps

### Step 1: Create the Page Template
Create `datafetch/templates/politicians.html` which extends `base.html`.
- Include the `[data-island="PoliticianDirectory"]` marker.
- Pre-render the first page of results (SEO).

### Step 2: Build the React Components
1.  **`PoliticianCard`**: Create the visual component.
2.  **`PoliticianFilters`**: Connect to URL state.
3.  **`PoliticianDirectory`**: Main island that fetches data via React Query.

### Step 3: Wire up Data Fetching
- Use `useQuery` to fetch from `/api/v2/politicians/`.
- Use `useQuery` to fetch parties from `/api/v2/parties/`.

### Step 4: Styling
- Use CSS Modules for layout.
- Ensure party colors are applied correctly (using CSS variables or inline styles from API data).

---

## 5. Design Mockup (Text)

```
[ Search Politicians...                                     ]
-------------------------------------------------------------
FILTERS            |  RESULTS (4,286)
                   |
Role:              |  [ Angela Rayner        ]  [ Keir Starmer         ]
[All] [MP] [Lord]  |  | LABOUR               |  | LABOUR               |
                   |  | MP for Ashton        |  | MP for Holborn       |
Status:            |  | Minister             |  | Prime Minister       |
[Govt] [Opp]       |  [ Donations: £15k      ]  [ Donations: £500k     ]
                   |
Party:             |  [ Rishi Sunak          ]  [ Ed Davey             ]
[ Select... ]      |  | CONSERVATIVE         |  | LIB DEM              |
                   |  | MP for Richmond      |  | MP for Kingston      |
                   |  [ Donations: £50k      ]  [ Donations: £100k     ]
                   |
```
