# UnderTheInfluence Systems Architecture

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Component Overview](#component-overview)
4. [Data Flow](#data-flow)
5. [Data Model Architecture](#data-model-architecture)
6. [External Dependencies](#external-dependencies)
7. [API Architecture](#api-architecture)
8. [Deployment Architecture](#deployment-architecture)
9. [Key Design Decisions](#key-design-decisions)
10. [Future Considerations](#future-considerations)

---

## System Overview

UnderTheInfluence is a web application designed to track and expose the influence of lobbying in UK politics. The system aggregates data from multiple authoritative sources to create a comprehensive database of:

- **Politicians** (MPs, Lords, MSPs, MLAs)
- **Political Organizations** (parties, legislatures, lobbying agencies)
- **Financial Relationships** (donations to politicians and parties)
- **Lobbying Relationships** (consultancy arrangements between organizations)

The application serves three primary purposes:

1. **Data Aggregation**: Importing and normalizing political data from diverse sources
2. **Data Presentation**: Providing a web interface for exploring political influence relationships
3. **Data Access**: Exposing a REST API for programmatic data consumption

### Technology Stack

| Layer | Technology |
|-------|------------|
| Framework | Django 1.8 |
| CMS | Wagtail 1.1 |
| API | Django REST Framework |
| Database | PostgreSQL (production) / SQLite (development) |
| Search | Elasticsearch |
| Frontend | Bootstrap, jQuery, Bootstrap Material Design |
| Asset Management | django-bower, django-compressor |

---

## Architecture Diagram

### High-Level System Architecture

```
                                    +------------------+
                                    |   External Data  |
                                    |     Sources      |
                                    +--------+---------+
                                             |
        +------------------------------------+------------------------------------+
        |                    |               |               |                    |
        v                    v               v               v                    v
+---------------+  +----------------+  +-----------+  +------------+  +------------------+
| ParlParse     |  | Electoral      |  | APPC      |  | Every      |  | Companies House  |
| (MySociety)   |  | Commission     |  | Register  |  | Politician |  | / Open Corporates|
+-------+-------+  +-------+--------+  +-----+-----+  +------+-----+  +--------+---------+
        |                  |                 |               |                  |
        +------------------+-----------------+---------------+------------------+
                                             |
                                             v
                              +------------------------------+
                              |    Management Commands       |
                              |      (Data Import Layer)     |
                              |                              |
                              | - import_parlparse           |
                              | - import_ec                  |
                              | - import_appc                |
                              | - import_everypolitician     |
                              | - import_companieshouse      |
                              | - import_ministers           |
                              | - import_twfy                |
                              | - import_mpsinterests        |
                              | - import_lordsinterests      |
                              +-------------+----------------+
                                            |
                                            v
+-----------------------------------------------------------------------------------+
|                              DJANGO APPLICATION                                    |
|                                                                                   |
|  +------------------+    +------------------+    +------------------+             |
|  |   datafetch      |    |       api        |    |       cms        |             |
|  |                  |    |                  |    |                  |             |
|  | - Popolo Models  |<-->| - REST ViewSets  |    | - Wagtail Pages  |             |
|  | - Influence      |    | - Serializers    |    | - Snippets       |             |
|  |   Mapping Models |    | - URL Routing    |    | - StreamFields   |             |
|  | - Admin Config   |    |                  |    |                  |             |
|  | - Views          |    |                  |    |                  |             |
|  +--------+---------+    +--------+---------+    +--------+---------+             |
|           |                       |                       |                       |
|           +-----------------------+-----------------------+                       |
|                                   |                                               |
|                                   v                                               |
|                        +--------------------+                                     |
|                        |    PostgreSQL      |                                     |
|                        |    Database        |                                     |
|                        +--------------------+                                     |
|                                                                                   |
+-----------------------------------------------------------------------------------+
                                    |
          +-------------------------+-------------------------+
          |                         |                         |
          v                         v                         v
   +-------------+          +---------------+         +----------------+
   | Web Browser |          | API Clients   |         | Wagtail Admin  |
   | (Frontend)  |          | (JSON/REST)   |         | (CMS Backend)  |
   +-------------+          +---------------+         +----------------+
```

### Component Interaction Diagram

```
+------------------+     +------------------+     +------------------+
|                  |     |                  |     |                  |
|  appc_redirect   |     |    datafetch     |     |       cms        |
|                  |     |                  |     |                  |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         |                        |                        |
         v                        v                        v
+------------------------------------------------------------------------+
|                                                                        |
|                          URL Router (urls.py)                          |
|                                                                        |
| /appc-redirect/*  --> appc_redirect.urls                               |
| /api/*            --> api.urls                                         |
| /search/*         --> datafetch.views.SearchView                       |
| /person/*         --> datafetch.views.ActorView                        |
| /organization/*   --> datafetch.views.ActorView                        |
| /admin/*          --> wagtail.wagtailadmin                             |
| /django-admin/*   --> django.contrib.admin                             |
| /*                --> wagtail.wagtailcore (CMS pages)                  |
|                                                                        |
+------------------------------------------------------------------------+
```

---

## Component Overview

### 1. datafetch App

The `datafetch` app is the core data layer of the application, responsible for:

- **Data Models**: Implementing the Popolo-based data schema
- **Data Import**: Management commands for fetching and importing external data
- **Web Views**: Public-facing views for displaying actors (people and organizations)
- **Admin Configuration**: Django admin customizations for data management

#### Directory Structure

```
datafetch/
├── __init__.py
├── admin.py              # Django admin configuration
├── apps.py               # App configuration
├── helpers.py            # Utility functions for data fetching
├── urls.py               # URL routing for public views
├── views.py              # View classes (ActorView, SearchView)
├── management/
│   └── commands/         # Data import management commands
│       ├── import_appc.py
│       ├── import_companieshouse.py
│       ├── import_ec.py
│       ├── import_everypolitician.py
│       ├── import_lordsinterests.py
│       ├── import_ministers.py
│       ├── import_mpsinterests.py
│       ├── import_parlparse.py
│       ├── import_powerbase.py
│       └── import_twfy.py
└── models/
    ├── __init__.py       # Model exports
    ├── models.py         # Popolo-based core models
    ├── influence_mapping.py  # Relationship models (Donation, Consultancy)
    └── popolo/
        ├── behaviors.py  # Abstract base classes (Timestampable, Dateframeable)
        └── querysets.py  # Custom QuerySet classes
```

#### Key Views

| View | URL Pattern | Purpose |
|------|-------------|---------|
| `SearchView` | `/search/` | Full-text search across actors |
| `ActorView` | `/person/<pk>/`, `/organization/<pk>/` | Detail pages for actors |
| `ActorRedirectView` | `/actor/<pk>/` | Redirects to appropriate actor type |

#### Management Commands

| Command | Data Source | Status |
|---------|-------------|--------|
| `import_parlparse` | MySociety ParlParse | Complete |
| `import_ministers` | MySociety ParlParse | Complete |
| `import_ec` | Electoral Commission | Complete |
| `import_appc` | APPC Register | Complete |
| `import_everypolitician` | EveryPolitician | Complete |
| `import_companieshouse` | Companies House | Partial |
| `import_twfy` | TheyWorkForYou | Partial |
| `import_mpsinterests` | Register of MPs' Interests | Partial |
| `import_lordsinterests` | Register of Lords' Interests | Partial |
| `import_powerbase` | Powerbase Wiki | Partial |

---

### 2. api App

The `api` app provides a RESTful JSON API for programmatic access to the data using Django REST Framework.

#### Directory Structure

```
api/
├── __init__.py
├── serializers.py        # DRF serializers for models
├── urls.py               # API URL routing
└── views.py              # DRF ViewSets and APIViews
```

#### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/actors` | GET | List all actors with search support |
| `/api/politicians` | GET | List politicians with role/date filtering |
| `/api/memberships` | GET | List unique membership roles |
| `/api/actors/<pk>/donations-from` | GET | Donations received by an actor |
| `/api/actors/<pk>/donations-to` | GET | Donations made by an actor |
| `/api/actors/<pk>/consulting-agencies` | GET | Lobbying agencies used by an actor |
| `/api/actors/<pk>/consulting-clients` | GET | Clients of a lobbying agency |

#### Serializers

```python
# Core serializers
ActorSerializer       # id, name, url
MembershipSerializer  # role
DonationSerializer    # id, donor, recipient, value, dates, etc.
ConsultancySerializer # id, client, agency, source, dates
```

---

### 3. cms App

The `cms` app integrates Wagtail CMS for editorial content management, allowing non-technical users to create and manage content pages.

#### Directory Structure

```
cms/
├── __init__.py
├── models.py             # Wagtail page and snippet models
├── migrations/           # Database migrations
└── templatetags/
    └── cms_tags.py       # Custom template tags
```

#### Wagtail Models

| Model | Type | Purpose |
|-------|------|---------|
| `MyPage` | Page | Standard content page with rich text body |
| `DataPage` | Page | Content page designed for data-driven content |
| `Profile` | Snippet | Reusable profile blocks (name, body, image) |
| `Analysis` | Snippet | Editorial analysis with StreamField content |
| `Quote` | Snippet | Reusable quotation blocks |

#### StreamField Blocks (Analysis)

```python
StreamField([
    ('heading', blocks.CharBlock(classname="full title")),
    ('paragraph', blocks.RichTextBlock()),
    ('image', ImageChooserBlock()),
])
```

---

### 4. appc_redirect App

A minimal app providing redirect functionality for APPC (Association of Professional Political Consultants) register links.

#### Directory Structure

```
appc_redirect/
├── __init__.py
├── migrations/
└── urls.py               # Single redirect route
```

#### Purpose

The APPC register URLs are dynamic and require POST requests. This app provides a stable URL that can be used as a source reference in the database, which then redirects users to the appropriate APPC profile page.

---

## Data Flow

### Data Import Pipeline

```
+-------------------+
| External Sources  |
| (APIs, CSV, HTML) |
+--------+----------+
         |
         | 1. Fetch (HTTP requests with caching)
         v
+-------------------+
| Local Cache       |
| (data/ directory) |
+--------+----------+
         |
         | 2. Parse (JSON, CSV, BeautifulSoup)
         v
+-------------------+
| Python Objects    |
| (dicts, lists)    |
+--------+----------+
         |
         | 3. Transform (normalize, deduplicate)
         v
+-------------------+
| Django Models     |
| (ORM operations)  |
+--------+----------+
         |
         | 4. Persist (get_or_create, update)
         v
+-------------------+
| PostgreSQL        |
| Database          |
+-------------------+
```

### Request/Response Flow

```
+-------------+     +---------------+     +------------------+
|   Browser   | --> | Django URLs   | --> | View/ViewSet     |
+-------------+     +---------------+     +--------+---------+
                                                   |
                    +------------------------------+
                    |
                    v
+------------------+     +------------------+     +------------------+
| Model Manager    | --> | QuerySet         | --> | Database         |
+------------------+     +------------------+     +------------------+
                                                          |
                    +-------------------------------------+
                    |
                    v
+------------------+     +------------------+     +------------------+
| Model Instances  | --> | Serializer/      | --> | HTTP Response    |
|                  |     | Template         |     | (JSON/HTML)      |
+------------------+     +------------------+     +------------------+
```

### Caching Strategy

The helpers module (`datafetch/helpers.py`) implements a simple file-based caching strategy for external data:

```python
def fetch_text(url, filename, method="get", path=None, refresh=False, ...):
    """
    1. Check if file exists locally
    2. If exists and refresh=False, return cached content
    3. If not exists or refresh=True, fetch from URL
    4. Save to local cache with 0.5s rate limiting
    5. Return content
    """
```

---

## Data Model Architecture

### Popolo Standard

The data model is based on the [Popolo Project](http://www.popoloproject.com/) open government data specification. This provides:

- **Interoperability**: Common vocabulary with other civic tech projects
- **Completeness**: Rich model for political data
- **Flexibility**: Support for partial dates, multiple identifiers, generic relations

### Model Hierarchy

```
                          +-------------------+
                          |  PolymorphicModel |
                          |  (django-polymorphic)
                          +--------+----------+
                                   |
                                   v
+-------------+           +--------+----------+           +-------------+
| Dateframeable|--------->|       Actor       |<---------| Timestampable|
| (abstract)  |           |   (polymorphic)   |          | (abstract)   |
+-------------+           +--------+----------+           +-------------+
                                   |
                    +--------------+--------------+
                    |                             |
                    v                             v
            +-------+-------+             +-------+-------+
            |    Person     |             | Organization  |
            +---------------+             +---------------+
```

### Core Models

#### Actor (Base Class)

```python
class Actor(PolymorphicModel, Dateframeable, Timestampable, GenericRelatable):
    name = CharField(max_length=512)
    image = URLField(blank=True, null=True)

    # Generic Relations
    other_names = GenericRelation('OtherName')
    identifiers = GenericRelation('Identifier')
    contact_details = GenericRelation('ContactDetail')
    links = GenericRelation('Link')
    sources = GenericRelation('Source')
    notes = GenericRelation('Note')
```

#### Person

```python
class Person(Actor):
    family_name = CharField(max_length=128, blank=True)
    given_name = CharField(max_length=128, blank=True)
    honorific_prefix = CharField(max_length=128, blank=True)
    honorific_suffix = CharField(max_length=128, blank=True)
    email = EmailField(blank=True, null=True)
    gender = CharField(max_length=128, blank=True)
    birth_date = CharField(max_length=10, blank=True)
    death_date = CharField(max_length=10, blank=True)
    summary = CharField(max_length=1024, blank=True)
    biography = TextField(blank=True)
```

#### Organization

```python
class Organization(Actor):
    summary = CharField(max_length=1024, blank=True)
    description = TextField(blank=True)
    classification = CharField(max_length=512, blank=True)
    parent = ForeignKey('Organization', blank=True, null=True)
    area = ForeignKey('Area', blank=True, null=True)
    founding_date = CharField(max_length=10, blank=True)
    dissolution_date = CharField(max_length=10, blank=True)
```

### Relationship Models

```
+---------------+          +---------------+          +---------------+
|    Person     |          |  Membership   |          | Organization  |
|               |<-------->|               |<-------->|               |
+---------------+          +---------------+          +---------------+
       ^                          |                          ^
       |                          v                          |
       |                   +---------------+                 |
       |                   |     Post      |                 |
       |                   +---------------+                 |
       |                                                     |
       |    +---------------+        +---------------+       |
       +--->|   Donation    |<------>|               |<------+
       |    +---------------+        +---------------+       |
       |                                                     |
       |    +---------------+        +---------------+       |
       +--->|  Consultancy  |<------>|               |<------+
            +---------------+        +---------------+
```

### Supporting Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `Post` | Position independent of holder | label, role, organization |
| `Membership` | Person-Organization relationship | person, organization, post, role, dates |
| `Donation` | Financial contribution | donor, recipient, value, type, dates |
| `Consultancy` | Lobbying relationship | client, agency, dates |
| `Identifier` | External IDs (EC ref, Companies House) | identifier, scheme |
| `OtherName` | Aliases and former names | name, note |
| `ContactDetail` | Contact information | type, value, label |
| `Link` | Related URLs | url, note |
| `Source` | Source documentation URLs | url, note |
| `Area` | Geographic regions | name, identifier, geom |

### Abstract Behaviors

#### Timestampable

```python
class Timestampable(models.Model):
    created_at = AutoCreatedField('creation time')
    updated_at = AutoLastModifiedField('last modification time')

    class Meta:
        abstract = True
```

#### Dateframeable

```python
class Dateframeable(models.Model):
    start_date = CharField(max_length=10, blank=True, null=True)  # YYYY-MM-DD or YYYY-MM or YYYY
    end_date = CharField(max_length=10, blank=True, null=True)

    class Meta:
        abstract = True
```

### Custom QuerySets

The `DateframeableQuerySet` provides temporal filtering:

```python
class DateframeableQuerySet(QuerySet):
    def past(self, moment=None)    # Items that have ended
    def future(self, moment=None)  # Items that haven't started
    def current(self, moment=None) # Items active at given moment
```

---

## External Dependencies

### Python Packages

| Package | Version | Purpose |
|---------|---------|---------|
| Django | >=1.8,<1.9 | Web framework |
| wagtail | 1.1 | Content management system |
| djangorestframework | latest | REST API framework |
| django-polymorphic | 0.7.2 | Polymorphic model inheritance |
| django-model-utils | 2.3.1 | Model utilities (Choices, managers) |
| beautifulsoup4 | 4.4.0 | HTML parsing for web scraping |
| requests | 2.7.0 | HTTP client for API calls |
| psycopg2 | 2.6.1 | PostgreSQL adapter |
| PyYAML | 3.11 | YAML configuration parsing |
| gunicorn | 19.3.0 | WSGI HTTP server |
| markdown | 2.6.2 | Markdown processing |
| django-filter | 0.11.0 | Filtering for DRF |
| django-bower | 5.0.4 | Bower integration |
| bootstrap-admin | 0.3.6 | Admin theme |

### Frontend Libraries (via Bower)

| Library | Version | Purpose |
|---------|---------|---------|
| jQuery | 2.1.1 | DOM manipulation |
| Bootstrap | latest | CSS framework |
| bootstrap-material-design | latest | Material design theme |
| bootstrap-table | latest | Data tables |
| moment | latest | Date/time handling |

### External Data Sources

| Source | URL | Data Type |
|--------|-----|-----------|
| ParlParse | cdn.rawgit.com/mysociety/parlparse | JSON (Popolo) |
| Electoral Commission | search.electoralcommission.org.uk/api | CSV |
| APPC Register | www.appc.org.uk/members/register | HTML (scrape) |
| EveryPolitician | cdn.rawgit.com/everypolitician/everypolitician-data | JSON (Popolo) |
| TheyWorkForYou API | www.theyworkforyou.com/api | JSON |
| data.parliament.uk | data.parliament.uk | XML |
| Open Corporates | api.opencorporates.com | JSON |

### External Services

| Service | Purpose | Configuration |
|---------|---------|---------------|
| Elasticsearch | Full-text search | Local installation required |
| TheyWorkForYou API | Politician data | API key in `conf/general.yml` |

---

## API Architecture

### Design Principles

1. **Read-Only**: All endpoints are read-only (GET requests only)
2. **Hypermedia**: Responses include URLs for related resources
3. **Pagination**: Results paginated with limit/offset
4. **Filtering**: Query parameters for search and filtering
5. **Nested Resources**: Actor-specific endpoints for relationships

### Authentication & Permissions

```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 10,
}
```

- Anonymous users: Read-only access
- Authenticated users: Model-level permissions apply

### API Endpoint Details

#### GET /api/actors

List and search actors (persons and organizations).

**Query Parameters:**
- `search`: Filter by name (case-insensitive contains)

**Response:**
```json
{
  "count": 1234,
  "next": "/api/actors?offset=10",
  "previous": null,
  "results": [
    {"id": 1, "name": "Example Actor", "url": "http://..."}
  ]
}
```

#### GET /api/politicians

List politicians with advanced filtering.

**Query Parameters:**
- `search`: Filter by name
- `role`: Filter by membership role (e.g., "Member of Parliament")
- `date`: Filter memberships active on specific date (YYYY-MM-DD)

#### GET /api/actors/{pk}/donations-from

List donations received by an actor.

**Query Parameters:**
- `search`: Filter by donor name
- `sort`: Field to sort by
- `order`: Sort direction (`asc` or `desc`)

---

## Deployment Architecture

### Production Environment

```
                                    +------------------+
                                    |   Load Balancer  |
                                    |    (Optional)    |
                                    +--------+---------+
                                             |
                              +--------------+--------------+
                              |                             |
                              v                             v
                    +---------+---------+         +---------+---------+
                    |   Gunicorn WSGI   |         |   Gunicorn WSGI   |
                    |   (app server)    |         |   (app server)    |
                    +---------+---------+         +---------+---------+
                              |                             |
                              +--------------+--------------+
                                             |
                    +------------------------+------------------------+
                    |                        |                        |
                    v                        v                        v
          +---------+---------+    +---------+---------+    +---------+---------+
          |    PostgreSQL     |    |   Elasticsearch   |    |   Static Files    |
          |    (database)     |    |    (search)       |    |   (nginx/CDN)     |
          +-------------------+    +-------------------+    +-------------------+
```

### Configuration

Configuration is managed via YAML file (`conf/general.yml`):

```yaml
STAGING: '0'                    # 0 for production
DATABASE_SYSTEM: 'postgresql'   # Use PostgreSQL in production
UTI_DB_USER: 'db_user'
UTI_DB_NAME: 'undertheinfluence'
UTI_DB_PASS: '***'
UTI_DB_HOST: 'localhost'
UTI_DB_PORT: '5432'
SECRET_KEY: '***'               # Cryptographic key
TWFY_API_KEY: '***'             # TheyWorkForYou API
ALLOWED_HOSTS:
  - 'undertheinfluence.org.uk'
BASE_URL: 'https://www.undertheinfluence.org.uk'
```

### Security Settings

```python
# Production security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "SAMEORIGIN"
CSRF_COOKIE_HTTPONLY = True
```

### Deployment Process

Deployment is managed via a separate repository: `github.com/spudmind/uti-deploy`

Typical deployment steps:

1. Pull latest code from repository
2. Install/update Python dependencies: `pip install -r requirements.txt`
3. Install/update frontend dependencies: `python manage.py bower_install`
4. Run database migrations: `python manage.py migrate`
5. Collect static files: `python manage.py collectstatic`
6. Restart Gunicorn workers

---

## Key Design Decisions

### 1. Popolo Standard Adoption

**Decision**: Use the Popolo open government data specification as the foundation for data models.

**Rationale**:
- Interoperability with other civic tech projects (EveryPolitician, ParlParse)
- Rich, well-documented schema for political data
- Reduces data transformation overhead when importing from Popolo-compliant sources
- Community-maintained standard with ongoing development

**Trade-offs**:
- Some complexity for simpler use cases
- Partial date handling adds string-based date fields

### 2. Polymorphic Models for Actors

**Decision**: Use django-polymorphic for the Actor base class with Person and Organization as subclasses.

**Rationale**:
- Single table for querying all actors (for search, relationships)
- Type-specific fields in subclasses
- Automatic downcasting to correct type
- Foreign keys can reference any actor type

**Trade-offs**:
- Additional database joins for type resolution
- More complex queries
- ContentType dependency

### 3. Generic Relations for Metadata

**Decision**: Use Django's ContentType framework for OtherName, Identifier, ContactDetail, Link, Source, and Note.

**Rationale**:
- Avoids creating separate join tables for each model
- Consistent interface across different parent types
- Follows Popolo specification structure
- Flexible for future model additions

**Trade-offs**:
- Slightly slower queries than direct ForeignKey
- More complex ORM queries
- Generic foreign keys not supported by all database features

### 4. String-Based Partial Dates

**Decision**: Store dates as CharField with YYYY-MM-DD, YYYY-MM, or YYYY format instead of DateField.

**Rationale**:
- Supports partial dates (common in political data: "born 1945")
- Matches Popolo specification
- Lexicographic ordering works correctly

**Trade-offs**:
- Cannot use database date functions directly
- Requires custom validation (regex + strptime)
- String comparison edge cases

### 5. File-Based Import Caching

**Decision**: Cache imported data files locally in the `data/` directory.

**Rationale**:
- Reduces load on external APIs
- Enables offline development
- Provides data backup
- Supports incremental imports

**Trade-offs**:
- Manual cache invalidation
- Disk space usage
- Potential for stale data

### 6. Wagtail for CMS

**Decision**: Use Wagtail CMS for editorial content management.

**Rationale**:
- Django-native CMS
- Flexible StreamField for structured content
- Snippet system for reusable content blocks
- Good admin UX for non-technical editors

**Trade-offs**:
- Adds significant dependencies
- Learning curve for custom development
- Version compatibility considerations

### 7. Separate Relationship Models

**Decision**: Create explicit Donation and Consultancy models rather than generic Relationship.

**Rationale**:
- Domain-specific fields (value, donation_type for Donation)
- Type-safe queries
- Clear API semantics
- Better admin experience

**Trade-offs**:
- More models to maintain
- Code duplication for common patterns

---

## Future Considerations

### Architectural Improvements

#### 1. Database Optimization

**Current State**: Standard Django ORM usage without significant optimization.

**Recommendations**:
- Add database indexes on frequently queried fields (name, identifier)
- Consider denormalization for search queries
- Implement query result caching (Redis/Memcached)
- Review N+1 query patterns in views

#### 2. Search Architecture

**Current State**: Basic Django QuerySet filtering with LIKE queries.

**Recommendations**:
- Full Elasticsearch integration for text search
- Implement faceted search (by type, date range, classification)
- Add autocomplete functionality
- Consider Haystack abstraction layer

#### 3. API Versioning

**Current State**: No explicit API versioning.

**Recommendations**:
- Implement URL-based versioning (`/api/v1/`, `/api/v2/`)
- Add API deprecation policy
- Document breaking changes
- Consider GraphQL for flexible queries

#### 4. Async Data Import

**Current State**: Synchronous management commands that block during execution.

**Recommendations**:
- Implement Celery for background task processing
- Add progress reporting and logging
- Enable partial/incremental imports
- Implement import scheduling

#### 5. Data Validation Pipeline

**Current State**: Basic validation during import.

**Recommendations**:
- Add data quality scoring
- Implement entity resolution/deduplication
- Create validation reports
- Add manual review workflow

### Feature Enhancements

#### 1. Data Completeness

- Complete import implementations for partial importers
- Add new data sources (Wikidata, official government APIs)
- Implement historical data tracking

#### 2. User Features

- User accounts and saved searches
- Email alerts for tracked entities
- Data export functionality (CSV, JSON)
- Embedded widgets for third-party sites

#### 3. Visualization

- Network graphs of relationships
- Timeline views of memberships/donations
- Geographic mapping of constituencies
- Aggregated statistics dashboards

### Technical Debt

1. **Django Version**: Upgrade from Django 1.8 (EOL) to current LTS
2. **Wagtail Version**: Upgrade from Wagtail 1.1 to current version
3. **Python Version**: Ensure Python 3.10+ compatibility
4. **Test Coverage**: Implement comprehensive test suite
5. **Documentation**: API documentation (OpenAPI/Swagger)
6. **CI/CD**: Automated testing and deployment pipeline

### Scalability Considerations

1. **Read Replicas**: Database read replicas for API traffic
2. **CDN**: Static asset delivery via CDN
3. **Rate Limiting**: API rate limiting for external consumers
4. **Horizontal Scaling**: Stateless application design for container deployment

---

## Appendix A: Model Schema Reference

### Entity-Relationship Diagram

```
+------------------+       +------------------+       +------------------+
|      Actor       |       |    Membership    |       |      Post        |
+------------------+       +------------------+       +------------------+
| PK id            |<---+  | PK id            |   +-->| PK id            |
| name             |    |  | FK person_id     |---|   | label            |
| image            |    +--| FK organization_id|   |  | role             |
| start_date       |    |  | FK on_behalf_of_id|---|  | FK organization_id|-->+
| end_date         |    |  | FK post_id       |---+  | FK area_id       |   |
| created_at       |    |  | FK area_id       |      | start_date       |   |
| updated_at       |    |  | label            |      | end_date         |   |
+------------------+    |  | role             |      +------------------+   |
        ^               |  | start_date       |                             |
        |               |  | end_date         |      +------------------+   |
+-------+--------+      |  +------------------+      |   Organization   |   |
|     Person     |      |                           +------------------+   |
+----------------+      +-------------------------->| (inherits Actor) |<--+
| family_name    |      |                           | summary          |
| given_name     |      |                           | description      |
| email          |      |                           | classification   |
| gender         |      |                           | FK parent_id     |--+
| birth_date     |      |                           | FK area_id       |  |
| death_date     |      |                           | founding_date    |  |
| summary        |      |                           | dissolution_date |  |
| biography      |      |                           +------------------+  |
+----------------+      |                                    ^            |
                        +------------------------------------+------------+
                        |
+------------------+    |    +------------------+
|    Donation      |    |    |   Consultancy    |
+------------------+    |    +------------------+
| PK id            |    |    | PK id            |
| FK donor_id      |----+    | FK client_id     |----+
| FK recipient_id  |----+    | FK agency_id     |----+
| value            |         | label            |
| donation_type    |         | source           |
| nature_of_donation|        | start_date       |
| received_date    |         | end_date         |
| accepted_date    |         +------------------+
| reported_date    |
| source           |
+------------------+
```

---

## Appendix B: Configuration Reference

### Environment Variables (via conf/general.yml)

| Variable | Required | Description |
|----------|----------|-------------|
| `STAGING` | Yes | '0' for production, '1' for development |
| `DATABASE_SYSTEM` | Yes | 'postgresql' or 'sqlite' |
| `UTI_DB_USER` | If PostgreSQL | Database username |
| `UTI_DB_NAME` | If PostgreSQL | Database name |
| `UTI_DB_PASS` | If PostgreSQL | Database password |
| `UTI_DB_HOST` | If PostgreSQL | Database host |
| `UTI_DB_PORT` | If PostgreSQL | Database port |
| `SECRET_KEY` | Yes | Django secret key |
| `TWFY_API_KEY` | Optional | TheyWorkForYou API key |
| `ADMINS` | Optional | Admin email addresses |
| `ALLOWED_HOSTS` | Yes | Permitted hostnames |
| `BASE_URL` | Yes | Public base URL |
| `SUPPORT_EMAIL` | Optional | Support contact email |
| `SERVER_EMAIL` | Optional | Error email from address |
| `DEFAULT_FROM_EMAIL` | Optional | General email from address |

---

*Document Version: 1.0*
*Last Updated: January 2026*
*Generated from codebase analysis*
