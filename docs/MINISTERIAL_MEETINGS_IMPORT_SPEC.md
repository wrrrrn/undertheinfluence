# Ministerial Meetings Import - Specification & Implementation Plan

**Created:** January 2026
**Purpose:** Import UK ministerial meetings data to enable influence access analysis
**Use Case:** Answer questions like "Which organizations get the most ministerial access?" (e.g., tech companies vs child safety groups)

---

## Executive Summary

UK government departments publish quarterly transparency data on ministerial meetings with external organizations. This data reveals **who has access to decision-makers** and is a critical missing piece in our influence mapping.

**Key Insight:** The Guardian analyzed this data (Jan 2026) to show tech companies had far more ministerial meetings than child safety groups - exactly the type of analysis UnderTheInfluence should enable.

**Data Coverage:**
- **24 current ministerial departments** + historical predecessors
- **Time span:** 2009-2026 (varies by department)
- **Format:** CSV (post-April 2024), XLSX/XLS (2014-2024), PDF (pre-2014)
- **Publication:** Quarterly, ~3 months after quarter end
- **Volume:** Estimated 50,000+ meeting records across all departments since 2010

---

## Data Sources

### Primary Sources
- **GOV.UK Collections:** Each department publishes a collection page with quarterly data
- **Format Standard (April 2024+):** CSV, UTF-8 encoding, standardized columns
- **Historical Formats:** XLSX, XLS, PDF (requires parsing)

### Key Departments (by coverage)
1. **DfT (Department for Transport):** 2009-present (earliest data)
2. **DWP (Work & Pensions):** Aug 2010-present (most complete)
3. **Cabinet Office:** May 2010-present
4. **DfE (Education):** May 2010-present
5. **HM Treasury:** July 2013-present
6. **Home Office:** 2013-present
7. **FCDO (Foreign Office):** 2013-present
8. **MoD (Defence):** 2013-present
9. **DHSC (Health):** 2012-present
10. **MoJ (Justice):** 2011-present

See `docs/uk_ministerial_meetings_data_sources.md` for complete directory.

### Historical Challenges
- **Departmental reorganizations:** BIS → BEIS → DBT/DESNZ/DSIT; FCO+DFID → FCDO
- **Name changes:** DCLG → MHCLG → DLUHC → MHCLG
- **Format inconsistencies:** Pre-2014 data often in PDF
- **Collection gaps:** Some departments lack consolidated collection pages (DCMS, NI Office, Scotland Office)

---

## Data Model Design

### Proposed: `MinisterialMeeting` Model

```python
class MinisterialMeeting(Dateframeable, Timestampable):
    """
    Record of a meeting between a UK government minister and external organization/individual.

    Follows Popolo pattern of linking actors via relationships.
    """

    # Core relationship
    minister = ForeignKey(Person, related_name='ministerial_meetings')
    external_actor = ForeignKey(Actor, related_name='meetings_with_ministers')

    # Meeting details
    meeting_date = CharField(max_length=10)  # YYYY-MM-DD or YYYY-MM (partial dates common)
    purpose = TextField(blank=True)  # Meeting topic/purpose
    location = CharField(max_length=512, blank=True)  # Where meeting occurred

    # Minister context at time of meeting
    ministerial_role = CharField(max_length=512)  # "Secretary of State", "Minister of State", etc.
    department = ForeignKey(Organization, related_name='ministerial_meetings')

    # Metadata
    publication_date = DateField()  # When transparency data was published
    quarterly_period = CharField(max_length=20)  # "Q1 2024" or "Apr-Jun 2024"
    source_url = URLField()  # Link to GOV.UK publication
    source_file = CharField(max_length=512)  # Filename of CSV/XLSX

    # Data quality
    raw_external_name = CharField(max_length=512)  # As written in source data
    needs_resolution = BooleanField(default=False)  # Flag for manual entity matching

    # Generic relations (Popolo pattern)
    identifiers = GenericRelation(Identifier)
    links = GenericRelation(Link)
    sources = GenericRelation(Source)
    notes = GenericRelation(Note)

    class Meta:
        indexes = [
            Index(fields=['meeting_date']),
            Index(fields=['minister', 'meeting_date']),
            Index(fields=['external_actor', 'meeting_date']),
            Index(fields=['department', 'meeting_date']),
        ]
        ordering = ['-meeting_date', 'minister']
```

### Alternative: Extend `Membership` Model?

**Consider:** Meetings could be modeled as temporary "memberships" with role="Meeting attendee"

**Pros:**
- Reuses existing Popolo pattern
- Leverages Dateframeable for temporal queries

**Cons:**
- Semantically incorrect (meetings ≠ memberships)
- Loses meeting-specific fields (purpose, location)
- Harder to query "who met with whom"

**Decision: Create dedicated `MinisterialMeeting` model** for clarity and query performance.

---

## Entity Resolution Strategy

### The Challenge
External organizations are listed by name (strings), not IDs:
- "Google UK" vs "Google" vs "Google LLC"
- "Meta" vs "Facebook" vs "Meta Platforms Inc"
- Individual names: "Elon Musk" vs "Elon Musk, Tesla CEO"

### Three-Phase Approach

#### Phase 1: Exact Matching (Automated)
```python
# Match existing Actor records by name
actor, created = Actor.objects.get_or_create(name=raw_name)
```

#### Phase 2: Fuzzy Matching (Semi-Automated)
```python
# Use django-fuzzywuzzy or similar
from fuzzywuzzy import fuzz

matches = Actor.objects.filter(
    name__icontains=core_keyword
)

for match in matches:
    ratio = fuzz.ratio(raw_name.lower(), match.name.lower())
    if ratio > 85:
        # Suggest match for review
        meeting.notes.add(Note(
            note=f"Possible match: {match.name} ({ratio}% similar)"
        ))
```

#### Phase 3: Manual Resolution (Admin Interface)
```python
# Flag records for manual review
meeting.needs_resolution = True
meeting.raw_external_name = "Google UK"
```

**Admin workflow:**
1. Query: `MinisterialMeeting.objects.filter(needs_resolution=True)`
2. Review suggestions from fuzzy matcher
3. Link to canonical `Actor` via `external_actor` FK
4. Set `needs_resolution = False`

### Canonical Organization Names

Create `OtherName` records for variants:
```python
google = Organization.objects.get(name="Google LLC")
google.other_names.add(OtherName(name="Google UK"))
google.other_names.add(OtherName(name="Google"))
```

---

## Import Command Design

### Command Structure

```bash
python manage.py import_ministerial_meetings \
    --department "cabinet-office" \
    --since 2020 \
    --format csv \
    --dry-run
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `--department` | String | Department slug (e.g., "cabinet-office", "hm-treasury", "all") |
| `--since` | Year | Import data from this year forward (default: 2020) |
| `--until` | Year | Import data up to this year (default: current year) |
| `--format` | Choice | File format to prioritize: "csv", "xlsx", "all" |
| `--dry-run` | Flag | Parse and validate without saving to database |
| `--refresh` | Flag | Re-download cached files |
| `--resolve-entities` | Flag | Enable fuzzy matching during import |

### Department Configuration

```python
# datafetch/management/commands/ministerial_meetings_config.py

DEPARTMENTS = {
    'cabinet-office': {
        'name': 'Cabinet Office',
        'collection_url': 'https://www.gov.uk/government/collections/ministers-transparency-publications',
        'coverage_start': '2010-05',
        'format': 'csv',  # Primary format
        'has_collection_page': True,
    },
    'hm-treasury': {
        'name': 'HM Treasury',
        'collection_url': 'https://www.gov.uk/government/collections/hm-treasury-ministerial-overseas-travel-and-meetings',
        'historical_url': 'https://www.gov.uk/government/collections/hmt-ministers-meetings-hospitality-gifts-and-overseas-travel',
        'coverage_start': '2013-07',
        'format': 'csv',
        'has_collection_page': True,
    },
    'home-office': {
        'name': 'Home Office',
        'collection_url': 'https://www.gov.uk/government/collections/home-office-ministers-hospitality-data',
        'coverage_start': '2013',
        'format': 'csv',
        'has_collection_page': True,
    },
    # ... 21 more departments
}

# Historical mappings
DEPARTMENT_SUCCESSORS = {
    'beis': ['dbt', 'desnz', 'dsit'],  # BEIS split into 3 departments Feb 2023
    'fco': ['fcdo'],  # FCO + DFID → FCDO Sep 2020
    'dclg': ['mhclg', 'dluhc'],  # Name changes
}
```

### CSV Column Mappings

**Standard columns (post-April 2024):**
```python
CSV_COLUMN_MAP = {
    'Minister': 'minister_name',
    'Ministerial Role': 'ministerial_role',
    'Date of Meeting': 'meeting_date',
    'Organisation/Individual': 'external_name',
    'Purpose of Meeting': 'purpose',
    'Location': 'location',
}

# Historical variations
CSV_COLUMN_VARIATIONS = {
    'minister_name': ['Minister', 'Minister Name', 'Ministerial Name'],
    'meeting_date': ['Date of Meeting', 'Date', 'Meeting Date'],
    'external_name': [
        'Organisation/Individual',
        'Organisation',
        'External Organisation',
        'Name of Organisation/Individual'
    ],
}
```

### Import Flow

```python
# Pseudocode for import_ministerial_meetings command

def handle(self, **options):
    department_slug = options['department']
    since_year = options['since']

    # Step 1: Discover quarterly publications
    publications = discover_publications(
        department=department_slug,
        since=since_year
    )

    for pub in publications:
        # Step 2: Download and cache
        file_path = helpers.fetch_file(
            url=pub['url'],
            cache_dir=f'data/ministerial_meetings/{department_slug}/'
        )

        # Step 3: Parse based on format
        if pub['format'] == 'csv':
            meetings = parse_csv(file_path, pub['quarter'])
        elif pub['format'] == 'xlsx':
            meetings = parse_xlsx(file_path, pub['quarter'])
        else:
            self.stderr.write(f"Unsupported format: {pub['format']}")
            continue

        # Step 4: Import to database
        for meeting_data in meetings:
            import_meeting(
                data=meeting_data,
                department=department_slug,
                source_url=pub['url'],
                dry_run=options['dry_run']
            )
```

---

## Parsing Strategy

### CSV Parsing (Python stdlib)

```python
import csv
from datetime import datetime

def parse_csv(file_path, quarter):
    """Parse CSV meeting data into structured format."""
    meetings = []

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Map columns
            meeting = {
                'minister_name': row.get('Minister', '').strip(),
                'ministerial_role': row.get('Ministerial Role', '').strip(),
                'meeting_date': parse_date(row.get('Date of Meeting', '')),
                'external_name': row.get('Organisation/Individual', '').strip(),
                'purpose': row.get('Purpose of Meeting', '').strip(),
                'location': row.get('Location', '').strip(),
                'quarterly_period': quarter,
            }

            # Validate required fields
            if meeting['minister_name'] and meeting['external_name']:
                meetings.append(meeting)

    return meetings

def parse_date(date_str):
    """Parse date string with fallback for partial dates."""
    date_str = date_str.strip()

    # Try full date: "2024-01-15"
    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    # Try month/year: "January 2024"
    for fmt in ['%B %Y', '%b %Y', '%m/%Y']:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m')
        except ValueError:
            continue

    # Return as-is if unparseable (will be reviewed)
    return date_str
```

### XLSX Parsing (openpyxl)

```python
from openpyxl import load_workbook

def parse_xlsx(file_path, quarter):
    """Parse XLSX meeting data."""
    wb = load_workbook(file_path, read_only=True)
    ws = wb.active

    # Find header row
    header_row = None
    for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if 'Minister' in row or 'Ministerial Name' in row:
            header_row = idx
            headers = row
            break

    if not header_row:
        raise ValueError("Cannot find header row in XLSX")

    # Parse data rows
    meetings = []
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        row_dict = dict(zip(headers, row))

        meeting = {
            'minister_name': str(row_dict.get('Minister', '')).strip(),
            # ... same mapping as CSV
        }

        if meeting['minister_name'] and meeting['external_name']:
            meetings.append(meeting)

    return meetings
```

---

## Entity Matching Logic

### Minister Matching

```python
def match_minister(minister_name, department_org, meeting_date):
    """
    Match minister name to Person record.

    Strategy:
    1. Exact name match with membership in department at meeting date
    2. Fuzzy match on family name + department
    3. Create new Person if no match (flag for review)
    """

    # Parse name
    parsed = parse_name(minister_name)  # Existing helper

    # Try exact match with temporal filter
    minister = Person.objects.filter(
        family_name__iexact=parsed['family_name'],
        given_name__iexact=parsed['given_name'],
        memberships__organization=department_org,
        memberships__start_date__lte=meeting_date,
        memberships__end_date__gte=meeting_date  # Or null
    ).first()

    if minister:
        return minister, 'exact'

    # Try family name only
    candidates = Person.objects.filter(
        family_name__iexact=parsed['family_name'],
        memberships__organization=department_org
    )

    if candidates.count() == 1:
        return candidates.first(), 'fuzzy'

    # Create new Person
    minister = Person.objects.create(
        name=minister_name,
        family_name=parsed['family_name'],
        given_name=parsed['given_name']
    )

    return minister, 'created'
```

### External Actor Matching

```python
def match_external_actor(external_name):
    """
    Match external organization/person to Actor.

    Returns: (actor, match_confidence, needs_review)
    """

    # Try exact match
    try:
        actor = Actor.objects.get(name__iexact=external_name)
        return actor, 1.0, False
    except Actor.DoesNotExist:
        pass

    # Try OtherName lookup
    other_name = OtherName.objects.filter(
        name__iexact=external_name
    ).first()

    if other_name:
        actor = other_name.content_object
        return actor, 0.95, False

    # Fuzzy match on existing actors
    from fuzzywuzzy import fuzz, process

    all_actors = Actor.objects.all().values_list('id', 'name')
    actor_names = {actor_id: name for actor_id, name in all_actors}

    match = process.extractOne(
        external_name,
        actor_names.values(),
        scorer=fuzz.token_sort_ratio
    )

    if match and match[1] > 85:  # 85% confidence threshold
        matched_name = match[0]
        actor_id = [id for id, name in actor_names.items() if name == matched_name][0]
        actor = Actor.objects.get(id=actor_id)
        return actor, match[1] / 100, True  # Flag for review

    # Create new actor (default to Organization)
    # Check if name looks like a person (heuristic: first + last name)
    if is_person_name(external_name):
        actor = Person.objects.create(name=external_name)
        parse_and_populate_person_fields(actor, external_name)
    else:
        actor = Organization.objects.create(name=external_name)

    return actor, 0.0, True  # Definitely needs review

def is_person_name(name):
    """Heuristic: does name look like a person vs organization?"""
    # Simple check: 2-4 words, no corporate suffixes
    words = name.split()
    corporate_keywords = ['ltd', 'limited', 'inc', 'llc', 'plc', 'group', 'association']

    has_corporate = any(kw in name.lower() for kw in corporate_keywords)

    return 2 <= len(words) <= 4 and not has_corporate
```

---

## Web Scraping Strategy

### GOV.UK Collection Page Scraping

```python
from bs4 import BeautifulSoup
import requests
from datafetch.helpers import fetch_text

def discover_publications(department_slug, since_year):
    """
    Scrape GOV.UK collection page to find all quarterly publication URLs.
    """
    config = DEPARTMENTS[department_slug]
    collection_url = config['collection_url']

    html = fetch_text(collection_url)
    soup = BeautifulSoup(html, 'html.parser')

    publications = []

    # Find all publication links
    for link in soup.find_all('a', href=True):
        href = link['href']
        text = link.get_text(strip=True)

        # Match pattern: "Q1 2024" or "April to June 2024"
        if 'transparency' in text.lower() or 'meetings' in text.lower():
            # Extract quarter/year from text
            quarter_info = extract_quarter_from_text(text)

            if quarter_info and quarter_info['year'] >= since_year:
                # Find CSV/XLSX download link
                pub_page_url = f"https://www.gov.uk{href}"
                download_url = find_data_file_url(pub_page_url)

                if download_url:
                    publications.append({
                        'quarter': quarter_info['label'],
                        'year': quarter_info['year'],
                        'url': download_url,
                        'format': download_url.split('.')[-1].lower(),
                        'title': text,
                    })

    return publications

def find_data_file_url(publication_page_url):
    """
    Navigate to publication page and find CSV/XLSX attachment.
    """
    html = fetch_text(publication_page_url)
    soup = BeautifulSoup(html, 'html.parser')

    # GOV.UK uses attachment sections
    for attachment in soup.find_all('section', class_='attachment'):
        link = attachment.find('a', href=True)
        if link:
            href = link['href']
            # Prioritize CSV over XLSX
            if href.endswith('.csv'):
                return f"https://www.gov.uk{href}"

    # Fallback to XLSX
    for attachment in soup.find_all('section', class_='attachment'):
        link = attachment.find('a', href=True)
        if link:
            href = link['href']
            if href.endswith('.xlsx') or href.endswith('.xls'):
                return f"https://www.gov.uk{href}"

    return None
```

---

## Use Cases & Queries

### Use Case 1: Tech Companies vs Child Safety Groups

**Question:** "Which tech companies had the most meetings with ministers in 2024?"

```python
# Query: Top tech companies by meeting count
tech_orgs = Organization.objects.filter(
    classification__icontains='tech'  # Or sector='Technology'
)

from django.db.models import Count

tech_meetings = MinisterialMeeting.objects.filter(
    external_actor__in=tech_orgs,
    meeting_date__gte='2024-01-01',
    meeting_date__lt='2025-01-01'
).values(
    'external_actor__name'
).annotate(
    meeting_count=Count('id')
).order_by('-meeting_count')
```

**Question:** "Compare tech company vs child safety group ministerial access"

```sql
-- SQL version for analysis
WITH tech_meetings AS (
  SELECT COUNT(*) as meeting_count
  FROM datafetch_ministerialmeeting mm
  INNER JOIN datafetch_organization org ON mm.external_actor_id = org.actor_ptr_id
  WHERE org.classification ILIKE '%tech%'
    AND mm.meeting_date >= '2024-01-01'
    AND mm.meeting_date < '2025-01-01'
),
child_safety_meetings AS (
  SELECT COUNT(*) as meeting_count
  FROM datafetch_ministerialmeeting mm
  INNER JOIN datafetch_organization org ON mm.external_actor_id = org.actor_ptr_id
  WHERE (org.classification ILIKE '%child%' OR org.classification ILIKE '%safety%')
    AND mm.meeting_date >= '2024-01-01'
    AND mm.meeting_date < '2025-01-01'
)
SELECT
  'Tech Companies' as sector,
  meeting_count
FROM tech_meetings
UNION ALL
SELECT
  'Child Safety Groups',
  meeting_count
FROM child_safety_meetings;
```

### Use Case 2: Lobbying → Donations → Meetings Triangle

**Question:** "Which organizations lobby, donate, AND meet with ministers?"

```python
# Triple influence channels
from django.db.models import Q, Count, Sum

triple_influence = Actor.objects.annotate(
    consultancy_count=Count('consulting_agencies', distinct=True),
    donation_count=Count('donations_made', filter=Q(donations_made__value__gt=0), distinct=True),
    meeting_count=Count('meetings_with_ministers', distinct=True),
    total_donated=Sum('donations_made__value')
).filter(
    consultancy_count__gt=0,
    donation_count__gt=0,
    meeting_count__gt=0
).order_by('-meeting_count', '-total_donated')
```

### Use Case 3: Minister Access Patterns

**Question:** "Which ministers meet most frequently with private sector?"

```python
from datafetch.models import MinisterialMeeting, Person

minister_meetings = Person.objects.filter(
    ministerial_meetings__isnull=False
).annotate(
    total_meetings=Count('ministerial_meetings'),
    private_sector_meetings=Count(
        'ministerial_meetings',
        filter=Q(ministerial_meetings__external_actor__organization__classification='Private sector')
    ),
    public_sector_meetings=Count(
        'ministerial_meetings',
        filter=Q(ministerial_meetings__external_actor__organization__classification='Public sector')
    )
).order_by('-total_meetings')
```

---

## API Endpoints

### New Endpoints Required

```python
# api/v2/urls.py

urlpatterns = [
    # ... existing endpoints

    # Ministerial meetings
    path('meetings/', MinisterialMeetingListView.as_view(), name='meeting-list'),
    path('meetings/<int:pk>/', MinisterialMeetingDetailView.as_view(), name='meeting-detail'),

    # Aggregates
    path('aggregates/meeting-stats/', MeetingStatsView.as_view(), name='meeting-stats'),
    path('aggregates/top-meeting-orgs/', TopMeetingOrgsView.as_view(), name='top-meeting-orgs'),
    path('aggregates/minister-access/', MinisterAccessView.as_view(), name='minister-access'),

    # Actor-specific
    path('actors/<int:pk>/meetings/', ActorMeetingsView.as_view(), name='actor-meetings'),
]
```

### Example: Top Meeting Orgs

```python
# api/v2/views.py

class TopMeetingOrgsView(APIView):
    """
    Returns organizations with most ministerial meetings.

    Filters:
    - since: YYYY-MM-DD
    - until: YYYY-MM-DD
    - department: department slug
    - minister: person ID
    - classification: org classification
    """

    def get(self, request):
        qs = MinisterialMeeting.objects.all()

        # Apply filters
        since = request.GET.get('since')
        if since:
            qs = qs.filter(meeting_date__gte=since)

        until = request.GET.get('until')
        if until:
            qs = qs.filter(meeting_date__lte=until)

        department_slug = request.GET.get('department')
        if department_slug:
            qs = qs.filter(department__slug=department_slug)

        # Aggregate by organization
        results = qs.values(
            'external_actor__id',
            'external_actor__name',
            'external_actor__polymorphic_ctype__model'
        ).annotate(
            meeting_count=Count('id'),
            first_meeting=Min('meeting_date'),
            last_meeting=Max('meeting_date'),
            ministers_met=Count('minister', distinct=True),
            departments_met=Count('department', distinct=True)
        ).order_by('-meeting_count')[:50]

        return Response(results)
```

---

## Implementation Phases

### Phase 1: MVP ✅ COMPLETE (January 21, 2026)
**Goal:** Import recent data from 3-5 key departments

- [x] Create `MinisterialMeeting` model and migrations
- [x] Build CSV parser for standardized format (April 2024+)
- [x] Implement basic entity matching (exact name only)
- [x] Create import command with `--department` and `--since` parameters
- [x] Import DSIT Q1 2024 data (170 meetings)
- [ ] Create admin interface for reviewing unmatched entities
- [ ] Add basic API endpoints: list, detail, top orgs

**Deliverable:** Working import command, CSV parser, entity matching

### Phase 2: Bulk Import ✅ COMPLETE (January 21, 2026)
**Goal:** Expand to multiple departments with auto-discovery

- [x] Add XLSX parser
- [ ] Add PDF parser (pdfplumber or tabula-py) - deferred to Phase 4
- [x] Handle departmental reorganizations (BEIS → DBT/DESNZ/DSIT, etc.)
- [x] Build web scraper for auto-discovering quarterly publications
- [x] Import 8 departments (7,183 meetings total)
- [x] Entity resolution for major duplicates (OpenAI, DeepMind, GSK, Oxford)

**Deliverable:** 7,183 meetings from 8 departments

### Phase 3: Full Coverage ✅ COMPLETE (January 21, 2026)
**Goal:** Import remaining departments, fix parser issues

- [x] Import 6 additional departments (HMT, DESNZ, MoD, Defra, FCDO, Cabinet Office)
- [x] Fix parser column variations for older file formats
- [x] Add minister OtherName records (Sir Keir Starmer, Jennifer Chapman)
- [x] Recovery of 1,375 additional meetings via parser improvements

**Deliverable:** 12,023 meetings from 14 departments:
- DBT (2,172), DESNZ (1,436), DSIT (1,211), CO (1,034), Defra (1,024)
- HMT (920), Home Office (798), DWP (793), DfT (782), DHSC (543)
- MoJ (532), FCDO (391), DfE (352), MoD (35)

### Phase 4: Historical & Visualization (Planned)
**Goal:** Import 2010-2019 data, build analysis capabilities

- [ ] Parse historical XLSX/XLS formats with non-standard column layouts
- [ ] Handle early PDF formats (OCR if needed)
- [ ] Create historical department mapping
- [ ] Validate temporal consistency (minister was in role at meeting date)
- [ ] Create influence scoring system (meetings + donations + lobbying)
- [ ] Build sector comparison queries
- [ ] Create "access inequality" metrics
- [ ] Add meeting timeline visualizations
- [ ] Build "influence network" graph

**Deliverable:** Complete dataset 2010-2026, API endpoints, dashboard widgets

- [ ] Create influence scoring system (meetings + donations + lobbying)
- [ ] Build sector comparison queries
- [ ] Create "access inequality" metrics
- [ ] Add meeting timeline visualizations
- [ ] Build "influence network" graph (who met whom when)

**Deliverable:** Analysis suite, dashboard widgets, SQL query library

---

## Technical Challenges & Solutions

### Challenge 1: Entity Resolution at Scale

**Problem:** 50,000 meetings × fuzzy matching against 25,000 actors = expensive

**Solution:**
- Cache fuzzy match results in `EntityMatch` lookup table
- Run batch fuzzy matching offline (management command)
- Use probabilistic blocking (only compare within same first letter, etc.)
- Provide admin interface for quick manual resolution

### Challenge 2: Departmental Reorganizations

**Problem:** BEIS split into DBT, DESNZ, DSIT - which department "owns" historical meetings?

**Solution:**
- Store original department name in `source_department` field
- Link to canonical `Organization` via FK
- Create `DepartmentSuccession` model to track lineage
- Queries can follow succession chain

```python
class DepartmentSuccession(models.Model):
    """Tracks departmental reorganizations."""
    predecessor = ForeignKey(Organization, related_name='successors')
    successor = ForeignKey(Organization, related_name='predecessors')
    effective_date = DateField()
    succession_type = CharField(choices=[
        ('merger', 'Merged into successor'),
        ('split', 'Split from predecessor'),
        ('rename', 'Renamed to successor'),
    ])
```

### Challenge 3: Date Parsing Variability

**Problem:** Dates appear as "15/01/2024", "January 2024", "Q1 2024", "2024"

**Solution:**
- Store dates as strings (existing Popolo pattern)
- Parse to most specific possible format
- Add `date_precision` field: 'day', 'month', 'quarter', 'year'
- Queries use date ranges based on precision

### Challenge 4: GOV.UK HTML Changes

**Problem:** Web scraping breaks when GOV.UK redesigns pages

**Solution:**
- Use multiple CSS selectors with fallbacks
- Cache parsed publication lists
- Manual fallback: CSV of publication URLs
- Log scraping failures to Sentry/monitoring

---

## Data Quality Measures

### Validation Rules

```python
def validate_meeting(meeting_data):
    """Validate meeting data before import."""
    errors = []

    # Required fields
    if not meeting_data.get('minister_name'):
        errors.append("Missing minister name")

    if not meeting_data.get('external_name'):
        errors.append("Missing external organization/person")

    if not meeting_data.get('meeting_date'):
        errors.append("Missing meeting date")

    # Date validation
    date = meeting_data.get('meeting_date')
    if date and not is_valid_date_format(date):
        errors.append(f"Invalid date format: {date}")

    # Ministerial role validation
    role = meeting_data.get('ministerial_role', '')
    valid_roles = [
        'Secretary of State',
        'Minister of State',
        'Parliamentary Under-Secretary',
        'Parliamentary Private Secretary',
        'Minister without Portfolio'
    ]

    if role and not any(r in role for r in valid_roles):
        errors.append(f"Unusual ministerial role: {role}")

    return errors
```

### Quality Dashboard

Track:
- Import success rate by department
- Entity match confidence distribution
- Records needing manual review
- Data freshness (last import date by department)
- Completeness (% of quarters imported for each dept)

---

## Testing Strategy

### Unit Tests

```python
# datafetch/tests/test_ministerial_meetings.py

class MinisterialMeetingImportTest(TestCase):
    def test_csv_parsing(self):
        """Test CSV parser handles standard format."""
        csv_content = """Minister,Ministerial Role,Date of Meeting,Organisation/Individual,Purpose of Meeting
John Smith,Secretary of State,2024-01-15,Google UK,Discuss AI regulation
Jane Doe,Minister of State,2024-02-20,Meta,Social media safety"""

        # Parse and validate
        meetings = parse_csv_from_string(csv_content, 'Q1 2024')

        self.assertEqual(len(meetings), 2)
        self.assertEqual(meetings[0]['minister_name'], 'John Smith')
        self.assertEqual(meetings[0]['external_name'], 'Google UK')

    def test_minister_matching(self):
        """Test minister name matching logic."""
        # Create test minister
        dept = Organization.objects.create(name='Department for Test')
        minister = Person.objects.create(
            name='John Smith',
            family_name='Smith',
            given_name='John'
        )

        # Match by name
        matched, confidence = match_minister(
            minister_name='John Smith',
            department_org=dept,
            meeting_date='2024-01-15'
        )

        self.assertEqual(matched, minister)

    def test_entity_resolution_exact(self):
        """Test exact entity matching."""
        org = Organization.objects.create(name='Google UK')

        matched, confidence, needs_review = match_external_actor('Google UK')

        self.assertEqual(matched, org)
        self.assertEqual(confidence, 1.0)
        self.assertFalse(needs_review)
```

### Integration Tests

```python
class MinisterialMeetingCommandTest(TestCase):
    @mock.patch('datafetch.management.commands.import_ministerial_meetings.discover_publications')
    @mock.patch('datafetch.helpers.fetch_file')
    def test_full_import_flow(self, mock_fetch, mock_discover):
        """Test complete import flow."""
        # Mock publication discovery
        mock_discover.return_value = [{
            'quarter': 'Q1 2024',
            'url': 'https://example.gov.uk/data.csv',
            'format': 'csv',
        }]

        # Mock file download
        mock_fetch.return_value = '/tmp/test_meetings.csv'

        # Create test CSV
        create_test_csv('/tmp/test_meetings.csv')

        # Run command
        call_command(
            'import_ministerial_meetings',
            department='cabinet-office',
            since=2024
        )

        # Verify imports
        self.assertEqual(MinisterialMeeting.objects.count(), 2)
```

---

## Dependencies

### Python Packages

```python
# Add to requirements.txt

# Excel parsing
openpyxl==3.1.2

# PDF parsing (Phase 2)
pdfplumber==0.10.3
# OR
tabula-py==2.8.2

# Fuzzy matching
fuzzywuzzy==0.18.0
python-Levenshtein==0.23.0  # Speed up fuzzywuzzy

# Web scraping (already have beautifulsoup4)
beautifulsoup4==4.12.2
```

### Database

```sql
-- Estimated storage requirements
-- 50,000 meetings × ~500 bytes/record = 25MB (negligible)

-- Index requirements (most important)
CREATE INDEX idx_meeting_date ON datafetch_ministerialmeeting(meeting_date);
CREATE INDEX idx_meeting_minister ON datafetch_ministerialmeeting(minister_id);
CREATE INDEX idx_meeting_external_actor ON datafetch_ministerialmeeting(external_actor_id);
CREATE INDEX idx_meeting_department ON datafetch_ministerialmeeting(department_id);
```

---

## Success Metrics

### Data Coverage (Current Status: Phase 3 Complete)
- ✅ 14 departments imported (14/24 with data available)
- ✅ 12,023 meetings imported
- ✅ 161 unique ministers tracked
- ✅ 8,443 unique external actors identified
- ⏳ Historical expansion to 2010-2019 (Phase 4)

### Data Quality (Current Status)
- ✅ ~60% entities matched exactly
- ✅ ~5% matched via OtherName aliases
- ✅ ~35% new actors created
- ✅ Major duplicates resolved (OpenAI, DeepMind, GSK, Oxford)
- ✅ Key minister aliases added (Sir Keir Starmer, Jennifer Chapman)

### Performance (Achieved)
- ✅ Full 14-department import: ~20 minutes
- ✅ Web scraper succeeds for 90%+ of publications
- ✅ ~600 meetings/minute import rate

### User Value (Achieved)
- ✅ Can analyze ministerial access by organization
- ✅ Cross-reference with donations and lobbying data
- ✅ Analysis queries available in `analysis/11_ministerial_meetings.sql`
- ⏳ API endpoints and frontend visualization (Phase 4)

---

## Future Enhancements

### Phase 5: Real-time Monitoring
- Automated quarterly checks for new publications
- Email alerts when new data published
- Automatic re-import and entity matching

### Phase 6: Attendee Details
- Parse "also present" fields (junior officials, advisers)
- Track corporate representatives (which exec attended)
- Link to Register of Interests declarations

### Phase 7: Meeting Outcomes
- Link meetings to subsequent policy announcements
- Track follow-up meetings
- Analyze "meeting → decision" lag time

### Phase 8: International Comparison
- Import EU lobbying transparency data
- US lobbying disclosure act data
- Compare ministerial access patterns across countries

---

## References

**Data Sources:**
- `docs/uk_ministerial_meetings_data_sources.md` - Complete directory
- GOV.UK Transparency Guidance: https://assets.publishing.service.gov.uk/media/6604110bf9ab41001aeea39c/2024_04_02-Ministers-Transparency-Guidance.pdf

**Inspiration:**
- The Guardian analysis (Jan 2026): Tech companies vs child safety groups ministerial access

**Technical:**
- Popolo Specification: http://www.popoloproject.com/
- Django Polymorphic: https://django-polymorphic.readthedocs.io/

---

**Document Status:** Active implementation (Phase 3 complete)
**Current Status:** 12,023 meetings imported from 14 departments
**Next Steps:** Phase 4 (Historical data + API & visualization)
