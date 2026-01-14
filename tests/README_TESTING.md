# Testing Documentation

This document describes the test suite for UnderTheInfluence.

## Test Suite Overview

**Total Tests**: 54 (all passing)

### Factory Fixtures (30 tests)
Defined in `tests/test_factories.py` and `tests/factories/`

Factory fixtures provide reusable test data creation using factory_boy with realistic British data.

**Coverage**:
- **Actor Factories** (4 tests) - Person, MP, Organization hierarchies
- **Organization Factories** (5 tests) - Political parties, companies, trade unions, parent/child relationships
- **Donation Factories** (6 tests) - Cash donations, large donations, entity resolution
- **Consultancy Factories** (4 tests) - Ongoing/completed lobbying relationships
- **Membership Factories** (4 tests) - MP memberships, party memberships, posts
- **Integration Tests** (4 tests) - MPs with donations, dual influence orgs, temporal party switching
- **Utility Tests** (3 tests) - Build vs create, stubs, sequences

**Key Features**:
- Uses Faker with en_GB locale for realistic British names and data
- Supports entity resolution via canonical_donor/canonical_recipient fields
- Handles temporal data with start_date/end_date ranges
- Creates realistic donation values (£100-£500k, with specialized factories for large/small donations)
- Proper relationship creation (SubFactory pattern)

### Data Quality Tests (24 tests)
Defined in `tests/test_data_quality.py`

Comprehensive data quality validation tests covering integrity, validation, and business logic.

**Coverage**:
- **Referential Integrity** (5 tests) - Orphaned records, post-organization relationships
- **Duplicate Detection** (3 tests) - Duplicate persons, organizations, donations
- **Data Validation** (8 tests) - Negative/zero values, date logic, partial date formats, empty names
- **Business Logic** (4 tests) - MP constituency requirements, party overlap detection, entity resolution
- **Data Completeness** (3 tests) - Required fields populated, donations/memberships/consultancies complete
- **Temporal Consistency** (1 test) - Overlapping party memberships

**Key Findings**:
- Donation/Consultancy models use `SET_NULL` on_delete to preserve audit trail
- When actors are deleted, related donations/consultancies remain with null foreign keys
- Tests validate this behavior and can detect orphaned records

## Management Commands

### check_data_quality

Runs data quality checks on production database and reports issues.

```bash
# Run all checks
python manage.py check_data_quality

# Run specific check category
python manage.py check_data_quality --check=duplicates
python manage.py check_data_quality --check=orphans
python manage.py check_data_quality --check=validation
python manage.py check_data_quality --check=completeness
python manage.py check_data_quality --check=temporal

# Show detailed output
python manage.py check_data_quality --verbose
```

**Check Categories**:
1. **Orphaned Records** - Donations/consultancies with null donor/recipient/client/agency
2. **Duplicates** - Duplicate persons, organizations, donations (same attributes)
3. **Validation** - Negative/zero donation values, invalid date logic, empty names
4. **Completeness** - Missing required fields (donation_type, start_date, etc.)
5. **Temporal Consistency** - Date logic errors, overlapping party memberships

**Example Output**:
```
================================================================================
Data Quality Check Report
================================================================================

## Orphaned Records Check
--------------------------------------------------------------------------------
⚠ 637 donations with null donor
  - Donation #119480: recipient=Stuart Polak, value=£0.00
  - Donation #119481: recipient=Stuart Polak, value=£0.00

## Duplicate Records Check
--------------------------------------------------------------------------------
⚠ 134 person names with duplicates
  - "John Smith" appears 3 times
⚠ 25539 potentially duplicate donations

## Data Validation Check
--------------------------------------------------------------------------------
⚠ 427 donations with zero value
⚠ 76 donations with accepted_date < received_date

================================================================================
⚠ Total issues found: 167967
================================================================================
```

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run specific test files
```bash
pytest tests/test_factories.py
pytest tests/test_data_quality.py
```

### Run specific test classes
```bash
pytest tests/test_factories.py::TestDonationFactory
pytest tests/test_data_quality.py::TestDuplicateDetection
```

### Run with coverage
```bash
pytest tests/ --cov=datafetch --cov-report=html
```

### Run with verbose output
```bash
pytest tests/ -v
```

## Factory Usage Examples

### Creating test data

```python
from tests.factories import (
    PersonFactory, MPFactory, CompanyFactory,
    PoliticalPartyFactory, DonationFactory
)

# Create a simple person
person = PersonFactory()

# Create an MP
mp = MPFactory(given_name="Boris", family_name="Johnson")

# Create a donation
company = CompanyFactory(name="Donor Corp")
party = PoliticalPartyFactory(name="Labour Party")
donation = DonationFactory(
    donor=company,
    recipient=party,
    value=Decimal('50000.00')
)

# Create batch
persons = PersonFactory.create_batch(10)
donations = DonationFactory.create_batch(20)

# Build without saving
person = PersonFactory.build()  # Not saved to DB
```

### Testing entity resolution

```python
# Create original and canonical entities
original_donor = CompanyFactory(name="Unite")
canonical_donor = CompanyFactory(name="Unite the Union")

# Create donation with entity resolution
donation = DonationFactory(
    donor=original_donor,
    canonical_donor=canonical_donor,
    recipient=party
)

# effective_donor returns canonical if set
assert donation.donor.name == "Unite"
assert donation.effective_donor.name == "Unite the Union"
```

### Testing temporal data

```python
from tests.factories import PartyMembershipFactory, HistoricalPartyMembershipFactory

mp = MPFactory()

# Historical membership (ended)
old_membership = HistoricalPartyMembershipFactory(
    person=mp,
    party=conservative,
    start_date='2010-05-06',
    end_date='2019-12-11'
)

# Current membership (ongoing)
current_membership = PartyMembershipFactory(
    person=mp,
    party=labour,
    start_date='2019-12-12',
    end_date=None
)

# Query by date
memberships_2015 = mp.party_memberships.filter(
    start_date__lte='2015-01-01',
    end_date__gte='2015-01-01'
)
```

## Code Coverage

Current model coverage from tests:
- `datafetch/models/influence_mapping.py`: 76.03%
- `datafetch/models/models.py`: 86.11%
- `datafetch/models/popolo/behaviors.py`: 64.71%
- `datafetch/models/popolo/querysets.py`: 59.46%

Areas not covered (0%):
- Management commands (import_parlparse, import_ministers, etc.)
- API views and serializers
- Helper utilities
- Services (parsers)

## Future Test Additions

Based on Phase 3.4 roadmap:

### 1. Import Command Tests (Pending)
Test `import_parlparse` and `import_ministers` commands:
- Data integrity after import
- Duplicate detection and deduplication
- Relationship creation (memberships, posts)
- Idempotency (re-running import doesn't create duplicates)

### 2. CI/CD Setup (Pending)
- GitHub Actions workflow for automated testing
- Run tests on push/PR
- Coverage reporting
- Test database setup in CI

### 3. API Tests (Future)
- API endpoint tests (already exist in Phase 3.2 notes)
- Serializer tests
- Filter tests
- Pagination tests

### 4. Performance Tests (Future)
- Load testing with k6 or Locust
- Query profiling
- N+1 query detection
- Response time benchmarks

## Known Data Quality Issues

From production database scan (as of 2026-01):
- 637 orphaned donations (null donor)
- 134 duplicate person names
- 25,539 potentially duplicate donations
- 427 donations with zero value
- 76 donations with invalid date logic
- 24,586 persons with empty names
- 116,542 memberships missing start_date
- 26 memberships with end_date < start_date

These issues should be addressed through:
1. Data cleaning scripts
2. Enhanced import validation
3. Model-level constraints
4. Regular data quality audits
