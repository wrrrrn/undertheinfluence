# API Proposal: Politicians Directory

**Date:** January 26, 2026
**Status:** Draft / Proposal
**Target Component:** `api/v2/views.py`, `api/v2/serializers.py`

---

## 1. Executive Summary

This document proposes new API endpoints to support the **Politicians Directory** feature (`/politicians/`). The frontend requires a performant, filterable list of political actors that provides "current state" context (Current Party, Current Role, Government vs Opposition status) without requiring heavy client-side processing.

## 2. New Endpoints

### 2.1 Politicians List
**URL:** `GET /api/v2/politicians/`

Returns a paginated list of people who hold (or held) political office, annotated with their current status.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Search by name (e.g., "Keir") |
| `party` | integer | Filter by Party ID |
| `role_type` | string | Filter by role category: `mp`, `lord`, `minister` |
| `is_current` | boolean | If `true` (default), only return currently serving politicians |
| `govt_status` | string | `government`, `opposition`, or `other` (requires party mapping) |
| `ordering` | string | `name`, `-name`, `party` |
| `limit` | integer | Pagination limit (default 20) |
| `offset` | integer | Pagination offset |

#### Response Schema

```json
{
  "count": 650,
  "next": "...",
  "previous": null,
  "results": [
    {
      "id": 12345,
      "name": "Angela Rayner",
      "image": "https://...",
      "current_party": {
        "id": 44,
        "name": "Labour Party",
        "image": "https://..."
      },
      "current_role": {
        "title": "MP for Ashton-under-Lyne",
        "start_date": "2015-05-07",
        "type": "Member of Parliament"
      },
      "is_minister": true,
      "ministerial_role": "Secretary of State for...",
      "stats": {
        "total_donations_received": 15000.00,
        "meetings_count": 45
      }
    }
  ]
}
```

### 2.2 Political Parties List
**URL:** `GET /api/v2/parties/`

Returns a list of political parties to populate filter dropdowns and the "Government/Opposition" grouping logic.

#### Query Parameters
- `has_seats`: boolean (default true) - Only show parties with current MPs/Lords

#### Response Schema
```json
[
  {
    "id": 44,
    "name": "Labour Party",
    "short_name": "Labour",
    "mp_count": 412,
    "lord_count": 178,
    "is_governing": true
  }
]
```

---

## 3. Implementation Strategy

### 3.1 The "Current Status" Challenge

The Popolo model stores roles as `Membership` records with `start_date` and `end_date`. Determining "Current Party" and "Current Role" for 650+ items efficiently requires optimization to avoid N+1 queries.

**Approach A: Annotation (Recommended for Read-Only API)**
Use Django's `Prefetch` and `SerializerMethodField` to inject the data.

```python
# api/v2/views.py

class PoliticianViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        today = date.today()
        
        # 1. Base Query: People with political memberships
        qs = Person.objects.filter(
            memberships__organization__classification__in=['Legislature', 'Executive']
        ).distinct()

        # 2. Prefetch "Current" memberships for serialization
        current_memberships = Membership.objects.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today),
            start_date__lte=today
        ).select_related('organization', 'post', 'on_behalf_of')

        qs = qs.prefetch_related(
            Prefetch('memberships', queryset=current_memberships, to_attr='active_memberships')
        )
        
        return qs
```

**Approach B: Denormalization (Long-term)**
As proposed in the Backend Strategy, adding `current_party` and `current_role` fields to the `Person` model would make filtering significantly faster and easier.
*   *Proposal:* For Phase 4, add these fields. For Phase 3 (Now), use Approach A.

### 3.2 Government vs. Opposition Logic

The API needs to know which parties are in Government to support the `govt_status` filter.

**Configuration:**
Add a setting `GOVERNING_PARTY_IDS` or `GOVERNING_PARTY_NAMES` in `settings.py` (e.g., `["Labour Party"]`).

**Filter Implementation:**
```python
class PoliticianFilter(filters.FilterSet):
    govt_status = filters.CharFilter(method='filter_govt_status')

    def filter_govt_status(self, queryset, name, value):
        governing_parties = ["Labour Party"] # In reality, fetch from settings
        
        if value == 'government':
            return queryset.filter(
                memberships__on_behalf_of__name__in=governing_parties,
                memberships__end_date__isnull=True  # Ensure current
            )
        elif value == 'opposition':
            # Logic for major opposition parties
            pass
```

### 3.3 Serializer Logic

The serializer needs to parse the `active_memberships` attribute (populated by Prefetch) to determine the primary display role.

*   **Priority:** Minister > MP > Lord
*   If a person has multiple active roles, pick the highest priority one for the "primary role" display, or return a list.

---

## 4. Work Required

1.  **Create Serializers**: `PoliticianSerializer`, `PartySerializer` in `api/v2/serializers.py`.
2.  **Create FilterSet**: `PoliticianFilter` in `api/v2/filters.py` handling the complex date/party logic.
3.  **Create ViewSet**: `PoliticianViewSet` in `api/v2/views.py`.
4.  **Register URLs**: Add to `api/v2/urls.py`.

## 5. Future Expansion (Network)

In the future, this endpoint can optionally include a `network_summary` field:

```json
"network_summary": {
  "connected_donors": 12,
  "connected_lobbyists": 3,
  "top_donor": { "name": "Unite", "value": 5000 }
}
```
This would be enabled via a query param `?include_network=true` to avoid performance costs on the main directory listing.
