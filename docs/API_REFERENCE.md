# API Reference

**Version**: v2
**Base URL**: `/api/v2/`
**Last Updated**: January 22, 2026

---

## Interactive Documentation

The API includes interactive documentation:

- **Swagger UI**: `/api/v2/docs/` - Interactive API explorer
- **ReDoc**: `/api/v2/redoc/` - Detailed API documentation
- **OpenAPI Schema**: `/api/v2/schema/` - Raw OpenAPI 3.0 JSON

---

## Authentication

All endpoints are currently **read-only** and **publicly accessible** (no authentication required).

---

## Aggregate Endpoints

These endpoints return pre-aggregated data optimized for dashboard widgets.

### Homepage Statistics
```
GET /api/v2/aggregates/stats/
```
Returns key metrics for the homepage dashboard.

**Response:**
```json
{
  "total_donations": 91281,
  "total_donation_value": 1234567890.50,
  "total_consultancies": 26000,
  "total_meetings": 41362,
  "total_actors": 25000
}
```

---

### Top Donors
```
GET /api/v2/aggregates/top-donors/
```
Returns top donors ranked by total donation value.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Results per page (default: 100, max: 500) |
| `offset` | int | Pagination offset |
| `received_after` | date | Filter by donation date (YYYY-MM-DD) |
| `received_before` | date | Filter by donation date (YYYY-MM-DD) |
| `value_min` | decimal | Minimum donation value |
| `value_max` | decimal | Maximum donation value |
| `donor_type` | string | Filter by type: `person` or `organization` |

**Example:**
```
GET /api/v2/aggregates/top-donors/?limit=10&received_after=2020-01-01
```

**Response:**
```json
{
  "count": 21414,
  "next": "/api/v2/aggregates/top-donors/?limit=10&offset=10",
  "previous": null,
  "results": [
    {
      "id": 12345,
      "name": "Example Donor Ltd",
      "actor_type": "organization",
      "total_donated": 1500000.00,
      "donation_count": 25,
      "is_lobbying_client": true
    }
  ]
}
```

---

### Top Recipients
```
GET /api/v2/aggregates/top-recipients/
```
Returns top recipients ranked by total donations received.

**Query Parameters:** Same as Top Donors.

---

### Party Donations
```
GET /api/v2/aggregates/party-donations/
```
Returns donation totals grouped by political party.

**Response:**
```json
{
  "results": [
    {
      "party_name": "Conservative Party",
      "total_donated": 85000000.00,
      "donation_count": 5000,
      "donor_count": 2500
    }
  ]
}
```

---

### Network Statistics
```
GET /api/v2/aggregates/network-stats/
```
Returns network-level statistics for influence mapping.

---

### Dual Influence
```
GET /api/v2/aggregates/dual-influence/
```
Returns organizations that both donate AND lobby (dual influence channels).

---

### Donor Concentration
```
GET /api/v2/aggregates/donor-concentration/
```
Returns metrics on donation concentration (e.g., top 10 donors as % of total).

---

## Actor Endpoints

These endpoints return detailed data for individual actors (persons or organizations).

### Actor Detail
```
GET /api/v2/actors/{id}/
```
Returns full detail for an actor including basic info and related counts.

**Response:**
```json
{
  "id": 12345,
  "name": "John Smith",
  "actor_type": "person",
  "classification": null,
  "identifiers": [
    {"scheme": "uk.org.publicwhip", "identifier": "uk.org.publicwhip/person/10001"}
  ],
  "summary": {
    "donations_made_count": 5,
    "donations_made_total": 50000.00,
    "donations_received_count": 0,
    "consultancies_count": 0,
    "memberships_count": 3
  }
}
```

---

### Actor Donations Made
```
GET /api/v2/actors/{id}/donations-made/
```
Returns donations made by this actor.

**Query Parameters:** Standard pagination (`limit`, `offset`).

---

### Actor Donations Received
```
GET /api/v2/actors/{id}/donations-received/
```
Returns donations received by this actor.

---

### Actor Consultancies
```
GET /api/v2/actors/{id}/consultancies/
```
Returns lobbying consultancy relationships for this actor.

---

### Actor Memberships
```
GET /api/v2/actors/{id}/memberships/
```
Returns organizational memberships for this actor.

---

## Common Response Formats

### Pagination
All list endpoints use limit/offset pagination:

```json
{
  "count": 1000,
  "next": "/api/v2/endpoint/?limit=100&offset=100",
  "previous": null,
  "results": [...]
}
```

### Error Responses
```json
{
  "detail": "Not found."
}
```

---

## Rate Limiting

No rate limiting is currently implemented. Please be respectful of server resources.

---

## Examples

### Get top 10 organizational donors in 2024
```bash
curl "http://localhost:8000/api/v2/aggregates/top-donors/?limit=10&donor_type=organization&received_after=2024-01-01"
```

### Get party donation breakdown
```bash
curl "http://localhost:8000/api/v2/aggregates/party-donations/"
```

### Get details for a specific actor
```bash
curl "http://localhost:8000/api/v2/actors/12345/"
```

---

## Development

The API is built with:
- Django REST Framework
- drf-spectacular (OpenAPI schema generation)
- django-filter (query parameter filtering)

See `api/v2/` directory for implementation details.
