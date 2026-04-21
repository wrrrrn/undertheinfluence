# Data Models Reference

**Last Updated**: April 16, 2026
**Status**: Living Document

---

## Overview

UnderTheInfluence uses the [Popolo Project](http://www.popoloproject.com/) open government data specification as the foundation for its data models. Popolo provides a rich, interoperable schema for political data that enables:

- **Interoperability** with other civic tech projects (EveryPolitician, ParlParse)
- **Completeness** for complex political relationships
- **Flexibility** for partial dates, multiple identifiers, and metadata

---

## Model Architecture

### Polymorphic Base (Actor)

The core design uses **django-polymorphic** to allow both Person and Organization to share a single `Actor` base class while maintaining type-specific fields.

```
Actor (Polymorphic Base)
├── Person (MPs, Lords, individual donors)
└── Organization (Parties, companies, trade unions, lobbying agencies)
```

**Benefits**:
- Single table for querying all actors (search, relationships)
- Foreign keys can reference any actor type (Donation.donor → Person OR Organization)
- Automatic type casting when querying

**Trade-offs**:
- Additional database joins for type resolution
- More complex ORM queries

---

## Core Models

### Actor (Base Class)

**File**: `datafetch/models/models.py`

**Purpose**: Polymorphic base class for all political actors (people and organizations).

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `name` | CharField(512) | Display name |
| `image` | URLField | Profile image URL (optional) |
| `start_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `end_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `created_at` | DateTimeField | Auto-created timestamp |
| `updated_at` | DateTimeField | Auto-updated timestamp |

**Generic Relations** (Popolo metadata):
- `identifiers` (GenericRelation → Identifier)
- `other_names` (GenericRelation → OtherName)
- `contact_details` (GenericRelation → ContactDetail)
- `links` (GenericRelation → Link)
- `sources` (GenericRelation → Source)
- `notes` (GenericRelation → Note)

**Why Generic Relations?**
- Allows any model to have identifiers, links, sources without separate join tables
- Follows Popolo specification pattern
- Consistent interface across all models

---

### Person (Extends Actor)

**File**: `datafetch/models/models.py`

**Purpose**: Represents real people (MPs, Lords, donors, lobbyists).

| Field | Type | Description |
|-------|------|-------------|
| *(inherits Actor fields)* | | |
| `family_name` | CharField(128) | Last name |
| `given_name` | CharField(128) | First name |
| `additional_name` | CharField(128) | Middle name (optional) |
| `honorific_prefix` | CharField(128) | Title (e.g., "Sir", "Dr", optional) |
| `honorific_suffix` | CharField(128) | Suffix (e.g., "MP", "OBE", optional) |
| `patronymic_name` | CharField(128) | Patronymic (optional) |
| `sort_name` | CharField(128) | For alphabetization (optional) |
| `email` | EmailField | Contact email (optional) |
| `gender` | CharField(128) | Gender (optional) |
| `birth_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `death_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `summary` | CharField(1024) | One-line bio (optional) |
| `biography` | TextField | Full biography (optional) |
| `national_identity` | CharField(128) | Nationality (optional) |

**Example**:
```python
person = Person.objects.create(
    name="Keir Starmer",
    family_name="Starmer",
    given_name="Keir",
    honorific_prefix="Sir",
    birth_date="1962"  # Partial date (year only)
)
```

---

### Organization (Extends Actor)

**File**: `datafetch/models/models.py`

**Purpose**: Represents political organizations, companies, trade unions, lobbying agencies.

| Field | Type | Description |
|-------|------|-------------|
| *(inherits Actor fields)* | | |
| `summary` | CharField(1024) | One-line description (optional) |
| `description` | TextField | Full description (optional) |
| `classification` | CharField(512) | Type (e.g., "Political Party", "Trade Union") |
| `parent` | ForeignKey(Organization) | Parent organization (optional) |
| `area` | ForeignKey(Area) | Geographic area (optional) |
| `founding_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `dissolution_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |

**Common Classifications**:
- `Political Party`
- `Trade Union`
- `Company`
- `Lobbying Agency`
- `Charitable Organization`
- `Legislature` (e.g., House of Commons)

**Example**:
```python
labour = Organization.objects.create(
    name="Labour Party",
    classification="Political Party",
    founding_date="1900"
)
```

---

## Relationship Models

### Membership

**File**: `datafetch/models/models.py`

**Purpose**: Links a Person to an Organization (e.g., MP membership in House of Commons).

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `label` | CharField(512) | Human-readable description (optional) |
| `role` | CharField(512) | Role name (e.g., "Member of Parliament") |
| `person` | ForeignKey(Person) | The person |
| `organization` | ForeignKey(Organization) | The organization |
| `on_behalf_of` | ForeignKey(Organization) | Party affiliation (optional) |
| `post` | ForeignKey(Post) | Position held (optional) |
| `area` | ForeignKey(Area) | Constituency/region (optional) |
| `start_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `end_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |

**Generic Relations**:
- `contact_details`, `links`, `sources`

**Use Cases**:
- MP membership in House of Commons
- Minister appointment
- Party membership
- Committee membership

**Example**:
```python
membership = Membership.objects.create(
    person=keir_starmer,
    organization=house_of_commons,
    on_behalf_of=labour,
    post=holborn_and_st_pancras_post,
    role="Member of Parliament",
    start_date="2015-05-07"
)
```

---

### Post

**File**: `datafetch/models/models.py`

**Purpose**: Represents a position independent of the person holding it (e.g., "MP for Bristol West").

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `label` | CharField(512) | Display name (e.g., "MP for Bristol West") |
| `other_label` | CharField(512) | Alternative name (optional) |
| `role` | CharField(512) | Role type (e.g., "Member of Parliament") |
| `organization` | ForeignKey(Organization) | Parent organization |
| `area` | ForeignKey(Area) | Constituency/region (optional) |
| `start_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `end_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |

**Generic Relations**:
- `contact_details`, `links`, `sources`

**Why Separate from Membership?**
- Posts exist independently of holders (constituency seat exists even if vacant)
- Enables historical tracking (all people who held this post)
- Matches real-world political structure

---

### Donation

**File**: `datafetch/models/influence_mapping.py`

**Purpose**: Financial contribution from one actor to another.

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `donor` | ForeignKey(Actor) | Donor (Person or Organization, optional) |
| `recipient` | ForeignKey(Actor) | Recipient (Person or Organization) |
| `canonical_donor` | ForeignKey(Actor) | For entity resolution (optional) |
| `canonical_recipient` | ForeignKey(Actor) | For entity resolution (optional) |
| `value` | DecimalField(max_digits=15, decimal_places=2) | £ amount |
| `donation_type` | CharField(128) | Type (e.g., "Cash", "Visit", "Gift") |
| `nature_of_donation` | CharField(512) | Nature (e.g., "hospitality") |
| `received_date` | DateField | Date received (optional) |
| `accepted_date` | DateField | Date accepted (optional) |
| `reported_date` | DateField | Date reported (optional) |
| `accounting_unit_name` | CharField(512) | Accounting unit (optional) |
| `accounting_units_as_central_party` | BooleanField | Central party flag |
| `purpose_of_visit` | CharField(512) | For visit donations (optional) |
| `is_bequest` | BooleanField | Bequest flag |
| `is_aggregation` | BooleanField | Aggregated donation flag |
| `is_sponsorship` | BooleanField | Sponsorship flag |
| `start_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `end_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `source` | URLField | Source URL (optional) |

**Generic Relations**:
- `identifiers`, `links`, `sources`

**Entity Resolution Fields**:
- `canonical_donor` / `canonical_recipient`: When multiple Actor records refer to the same entity, these fields point to the "canonical" (authoritative) Actor record. This allows merging duplicates without deleting data.

**Effective Donor/Recipient** (properties):
```python
@property
def effective_donor(self):
    return self.canonical_donor if self.canonical_donor else self.donor

@property
def effective_recipient(self):
    return self.canonical_recipient if self.canonical_recipient else self.recipient
```

**Data Sources**:
- Electoral Commission (91,000+ donations)
- MPs' Register of Interests (Categories 2 & 3)
- Lords' Register of Interests (Sponsorship, Visits, Gifts)

**Example**:
```python
donation = Donation.objects.create(
    donor=unite_union,
    recipient=labour,
    value=Decimal("50000.00"),
    donation_type="Cash",
    received_date="2024-01-15"
)
```

---

### Consultancy

**File**: `datafetch/models/influence_mapping.py`

**Purpose**: Lobbying relationship between a client organization and a lobbying agency.

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `client` | ForeignKey(Organization) | Client organization |
| `agency` | ForeignKey(Organization) | Lobbying agency |
| `canonical_client` | ForeignKey(Organization) | For entity resolution (optional) |
| `canonical_agency` | ForeignKey(Organization) | For entity resolution (optional) |
| `label` | CharField(512) | Description (optional) |
| `start_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `end_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `source` | URLField | Source URL (optional) |

**Generic Relations**:
- `identifiers`, `links`, `sources`

**Data Sources**:
- PRCA Professional Lobbying Register (current)
- PRCA Historical Archive (2019-2025, 26 PDF registers)

**Example**:
```python
consultancy = Consultancy.objects.create(
    client=acme_corp,
    agency=public_affairs_ltd,
    start_date="2023-01"
)
```

---

## Supporting Models (Popolo Metadata)

### Identifier

**File**: `datafetch/models/models.py`

**Purpose**: External identifiers for actors (e.g., Electoral Commission reference, Companies House number).

| Field | Type | Description |
|-------|------|-------------|
| `identifier` | CharField(512) | The identifier value |
| `scheme` | CharField(128) | Identifier scheme (e.g., "ElectoralCommission", "CompaniesHouse") |
| `content_type` | ForeignKey(ContentType) | Parent model type |
| `object_id` | PositiveIntegerField | Parent object ID |
| `content_object` | GenericForeignKey | Generic relation to parent |

**Common Schemes**:
- `ElectoralCommission`
- `CompaniesHouse`
- `ParlParse`
- `TheyWorkForYou`

**Example**:
```python
Identifier.objects.create(
    content_object=labour,
    identifier="PP53",
    scheme="ElectoralCommission"
)
```

---

### OtherName

**File**: `datafetch/models/models.py`

**Purpose**: Alternative or former names for actors.

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(512) | Alternative name |
| `note` | CharField(1024) | Context (e.g., "maiden name", "alias") |
| `start_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `end_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `content_type` | ForeignKey(ContentType) | Parent model type |
| `object_id` | PositiveIntegerField | Parent object ID |
| `content_object` | GenericForeignKey | Generic relation to parent |

**Use Cases**:
- Former names (maiden names, stage names)
- Common abbreviations
- Misspellings to improve search

---

### ContactDetail

**File**: `datafetch/models/models.py`

**Purpose**: Contact information for actors or memberships.

| Field | Type | Description |
|-------|------|-------------|
| `type` | CharField(12) | Contact type (e.g., "email", "phone", "address") |
| `value` | CharField(512) | Contact value |
| `label` | CharField(512) | Human-readable label (optional) |
| `note` | CharField(1024) | Additional context (optional) |
| `content_type` | ForeignKey(ContentType) | Parent model type |
| `object_id` | PositiveIntegerField | Parent object ID |
| `content_object` | GenericForeignKey | Generic relation to parent |

---

### Link

**File**: `datafetch/models/models.py`

**Purpose**: Related URLs (websites, social media, Wikipedia).

| Field | Type | Description |
|-------|------|-------------|
| `url` | URLField | URL |
| `note` | CharField(1024) | Description (e.g., "Official website", "Twitter") |
| `content_type` | ForeignKey(ContentType) | Parent model type |
| `object_id` | PositiveIntegerField | Parent object ID |
| `content_object` | GenericForeignKey | Generic relation to parent |

---

### Source

**File**: `datafetch/models/models.py`

**Purpose**: Documentation URLs for data provenance.

| Field | Type | Description |
|-------|------|-------------|
| `url` | URLField | Source URL |
| `note` | CharField(1024) | Description (optional) |
| `content_type` | ForeignKey(ContentType) | Parent model type |
| `object_id` | PositiveIntegerField | Parent object ID |
| `content_object` | GenericForeignKey | Generic relation to parent |

**Example**:
```python
Source.objects.create(
    content_object=membership,
    url="https://www.parliament.uk/mps-lords-and-offices/mps/",
    note="Official Parliament website"
)
```

---

### Note

**File**: `datafetch/models/models.py`

**Purpose**: Free-text annotations.

| Field | Type | Description |
|-------|------|-------------|
| `note` | TextField | Note content |
| `content_type` | ForeignKey(ContentType) | Parent model type |
| `object_id` | PositiveIntegerField | Parent object ID |
| `content_object` | GenericForeignKey | Generic relation to parent |

---

### Area

**File**: `datafetch/models/models.py`

**Purpose**: Geographic areas (constituencies, regions, nations).

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `name` | CharField(256) | Area name (e.g., "Bristol West") |
| `identifier` | CharField(512) | External identifier (optional) |
| `classification` | CharField(512) | Area type (e.g., "constituency") |
| `geom` | TextField | Geometry data (optional) |
| `parent` | ForeignKey(Area) | Parent area (optional) |

**Generic Relations**:
- `identifiers`, `sources`

**Use Cases**:
- Parliamentary constituencies
- London boroughs
- Devolved nations

---

## Abstract Behaviors

### Timestampable

**File**: `datafetch/models/popolo/behaviors.py`

**Purpose**: Automatic created/updated timestamps.

| Field | Type | Description |
|-------|------|-------------|
| `created_at` | DateTimeField | Auto-created timestamp |
| `updated_at` | DateTimeField | Auto-updated timestamp |

**Usage**: All models inherit from Timestampable via Actor or Relationship base classes.

---

### Dateframeable

**File**: `datafetch/models/popolo/behaviors.py`

**Purpose**: Start/end date tracking with custom QuerySet methods.

| Field | Type | Description |
|-------|------|-------------|
| `start_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |
| `end_date` | CharField(10) | YYYY, YYYY-MM, or YYYY-MM-DD (optional) |

**Custom QuerySet Methods** (`DateframeableQuerySet`):
```python
# Filter for items active at a specific moment
Membership.objects.current(moment="2024-01-01")

# Filter for items that have ended
Membership.objects.past(moment="2024-01-01")

# Filter for items that haven't started yet
Membership.objects.future(moment="2024-01-01")
```

**Partial Date Support**:
- `YYYY` (year only): "2020"
- `YYYY-MM` (year-month): "2020-06"
- `YYYY-MM-DD` (full date): "2020-06-15"

**Why CharField (Not DateField)?**
- Political data often has incomplete dates ("elected 1997", "died 2015")
- Popolo specification uses partial dates
- Lexicographic ordering works correctly for YYYY[-MM[-DD]] format

---

## Data Import Sources

### Working Imports

**ParlParse** (MySociety):
- **Command**: `import_parlparse --since 2010`
- **URL**: https://github.com/mysociety/parlparse
- **Format**: JSON (Popolo-compliant)
- **Data**: MPs, Lords, MSPs, MLAs with memberships
- **Status**: ✅ Working (URLs updated from cdn.rawgit.com)

**Ministers** (MySociety):
- **Command**: `import_ministers --since 2010`
- **URL**: https://github.com/mysociety/parlparse
- **Format**: JSON
- **Data**: Ministerial appointments
- **Status**: ✅ Working

**MPs' Register of Interests** (TheyWorkForYou XML):
- **Command**: `import_mpsinterests`
- **URL**: https://www.theyworkforyou.com/pwdata/scrapedxml/regmem/
- **Format**: XML
- **Data**: Categories 2 (Donations) and 3 (Gifts/Hospitality)
- **Status**: ✅ Working

### Partially Working / Needs Update

**Electoral Commission**:
- **Command**: `import_ec`
- **URL**: https://search.electoralcommission.org.uk/
- **Format**: CSV (API changed)
- **Data**: Political donations
- **Status**: ⚠️ Needs update for new API

**APPC Lobbying Register**:
- **Command**: `import_appc`
- **URL**: https://www.prca.org.uk/register/ (formerly appc.org.uk)
- **Format**: HTML scraping
- **Data**: Current lobbying relationships
- **Status**: ⚠️ Needs rewrite (APPC merged with PRCA in 2018)

---

## Database Statistics (April 2026)

**Current Data Volume**:
- **Actors**: 155,077 (90,727 persons + 64,349 organizations)
- **Memberships**: 136,588
- **Donations**: 91,513 (MPs' Register of Interests + Electoral Commission)
- **Consultancies**: 62,916
- **Ministerial Meetings**: 41,362 (from 23 departments)
- **Meeting Attendees**: 119,793
- **Time Range**: 1996-2026 (30 years)

**Data Quality**:
- See `docs/DATA_PIPELINE.md` for detailed analysis
- Entity resolution via `canonical_entry` fields on Actor, Donation, Consultancy
- Companies House enrichment: 51,157 organizations matched
- 127,600+ data quality issues resolved

---

## Key Design Decisions

### 1. Polymorphic Models

**Decision**: Use django-polymorphic for Actor base class.

**Rationale**:
- Single table for querying all actors (search, donations)
- Foreign keys can reference any actor type
- Automatic type casting

**Trade-offs**:
- Additional joins for type resolution
- More complex queries

---

### 2. Partial Dates as Strings

**Decision**: Store dates as CharField with YYYY[-MM[-DD]] format.

**Rationale**:
- Matches Popolo specification
- Supports incomplete dates (common in political data)
- Lexicographic ordering works

**Trade-offs**:
- Cannot use database date functions
- Requires custom validation

---

### 3. Generic Relations for Metadata

**Decision**: Use Django's ContentType framework for Identifier, OtherName, etc.

**Rationale**:
- Avoids separate join tables for each model
- Consistent interface across types
- Follows Popolo specification

**Trade-offs**:
- Slightly slower queries than direct ForeignKey
- Cannot use database foreign key constraints

---

### 4. Entity Resolution via Canonical Fields

**Decision**: Add `canonical_donor` / `canonical_recipient` fields instead of deleting duplicates.

**Rationale**:
- Non-destructive (preserves audit trail)
- Allows gradual resolution
- Reversible if mistakes are made

**Trade-offs**:
- More complex queries (need to check both fields)
- Database still contains duplicate records

---

## References

**Popolo Specification**:
- http://www.popoloproject.com/
- http://popoloproject.com/schemas/person.json
- http://popoloproject.com/schemas/organization.json
- http://popoloproject.com/schemas/membership.json

**Related Documentation**:
- `docs/systems-architecture.md` - Overall system architecture
- `docs/CURRENT_STATE.md` - Feature inventory
- `docs/DATA_PIPELINE.md` - Data import, quality & remediation

---

**Document Maintenance**: Update this document when:
- New models are added
- Model fields change
- Data sources change
- Import commands are fixed/added

**Last Major Update**: January 19, 2026 (refreshed for current state)
