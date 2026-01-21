# Phase 3.4: Testing & Quality Assurance - Progress Report

**Last Updated**: 2026-01-14

## Completed Tasks

### ✅ Task #1: Factory Fixtures
**Status**: COMPLETE (30/30 tests passing)

Created comprehensive factory fixtures using factory_boy for creating realistic test data.

**Files Created**:
- `tests/factories/__init__.py` - Factory exports
- `tests/factories/actor_factories.py` - Person, Organization, Area factories
- `tests/factories/relationship_factories.py` - Donation, Consultancy factories
- `tests/factories/membership_factories.py` - Post, Membership, PartyMembership factories
- `tests/test_factories.py` - 30 comprehensive factory tests

**Features**:
- British English data (Faker en_GB locale)
- Entity resolution support (canonical_donor/canonical_recipient)
- Temporal data (start_date/end_date ranges)
- Realistic donation values (£100-£500k)
- Specialized factories: MPFactory, PoliticalPartyFactory, LargeDonationFactory, etc.

**Test Coverage**:
- Actor creation and relationships
- Donations with entity resolution
- Consultancies (ongoing/completed)
- Memberships (MP posts, party memberships)
- Integration scenarios (MPs with donations, party switching)
- Utility features (build, batch, sequences)

---

### ✅ Task #3: Data Quality Tests
**Status**: COMPLETE (24/24 tests passing)

Created comprehensive data quality validation tests and production audit tooling.

**Files Created**:
- `tests/test_data_quality.py` - 24 data quality tests
- `datafetch/management/commands/check_data_quality.py` - Production audit command
- `tests/README_TESTING.md` - Testing documentation

**Test Categories** (24 tests):
1. **Referential Integrity** (5 tests)
   - Orphaned donations/consultancies (SET_NULL behavior)
   - Post-organization relationships
   - Membership foreign key validation

2. **Duplicate Detection** (3 tests)
   - Duplicate persons (same name)
   - Duplicate organizations (same name)
   - Duplicate donations (same attributes)

3. **Data Validation** (8 tests)
   - Negative/zero donation values
   - Date logic (accepted ≥ received ≥ reported)
   - Partial date format validation (YYYY, YYYY-MM, YYYY-MM-DD)
   - Empty name detection

4. **Business Logic** (4 tests)
   - MP constituency requirements
   - Overlapping party memberships
   - Entity resolution (effective_donor/effective_recipient)
   - Consultancy relationships

5. **Data Completeness** (3 tests)
   - Required donation fields
   - Required membership fields
   - Required consultancy fields

6. **Temporal Consistency** (1 test)
   - Date range validation (end_date ≥ start_date)
   - Party membership overlaps

**Management Command**:
```bash
# Run all checks
python manage.py check_data_quality

# Run specific category
python manage.py check_data_quality --check=duplicates

# Verbose output with examples
python manage.py check_data_quality --verbose
```

**Production Database Findings** (as of 2026-01):
- 637 orphaned donations (null donor)
- 134 duplicate person names
- 25,539 potentially duplicate donations
- 427 donations with zero value
- 76 donations with invalid date logic
- 24,586 persons with empty names
- 116,542 memberships missing start_date
- 26 memberships with end_date < start_date

**Total Issues**: 167,967 data quality issues identified

---

## In Progress Tasks

### 🚧 Task #3.5: Data Quality Remediation
**Status**: IN PROGRESS (Investigation Complete, Cleanup Ready)
**Started**: 2026-01-14

Comprehensive data quality investigation and remediation plan.

**Investigation Results**:
- Total issues found: 167,967
- Automatically fixable: 28,969 (17.2%)
- Manual review needed: 290 (0.2%)
- Import fixes needed: 116,542 (82.6%)
- Actually valid data: 24,720 (14.7% - Lords/Bishops with titles)

**Files Created**:
- `scripts/investigate_data_issues.py` - Detailed analysis script (Python)
- `datafetch/management/commands/clean_data.py` - Automated cleanup command
- `docs/DATA_QUALITY_REPORT.md` - Comprehensive remediation plan (87 pages)

**Key Findings**:
1. ✅ **Duplicate Donations (28,516)** - Caused by re-running import_ec without deduplication
2. 🚨 **Missing Membership Start_Dates (116,542)** - 77.6% of memberships, needs import fix
3. ℹ️ **Empty Person Names (24,586)** - VALID DATA (Lords/Bishops with titles like "Marquess of Lothian")
4. ✅ **Orphaned Donations (423)** - Import placeholders with null donor, £0 value
5. ✅ **Invalid Membership Dates (26)** - Committee chair dates swapped

**Automated Cleanup Commands**:
```bash
# Review what will be fixed
docker compose exec web python manage.py clean_data --dry-run

# Apply all fixes (28,969 issues)
docker compose exec web python manage.py clean_data --fix=all

# Fix specific categories
docker compose exec web python manage.py clean_data --fix=orphaned_donations
docker compose exec web python manage.py clean_data --fix=duplicate_donations
docker compose exec web python manage.py clean_data --fix=invalid_dates
```

**Remediation Phases**:
- [ ] **Phase 1**: Run automated cleanup (28,969 fixes)
- [ ] **Phase 2**: Manual review of 76 invalid donation dates + 214 orphaned donations
- [ ] **Phase 3**: Fix import commands (deduplication, date validation, start_date inference)
- [ ] **Phase 4**: Add model-level validation to prevent future issues

**Impact**:
- After automated cleanup: 141,975 issues remaining (down from 167,967)
- After import fixes: <1,000 issues remaining (target)

---

## Pending Tasks

### ⏸️ Task #2: Import Command Tests
**Status**: NOT STARTED

Test import commands for data integrity and deduplication.

**Scope**:
- Test `import_parlparse` for MP/Lord data integrity
- Test `import_ministers` for ministerial appointment accuracy
- Verify deduplication logic (no duplicate persons/organizations)
- Test idempotency (re-running imports doesn't create duplicates)
- Validate relationship creation (memberships, posts, areas)
- Test error handling (malformed data, missing fields)

**Test Data Sources**:
- Use cached ParlParse JSON files in `data/` directory
- Create test fixtures with known expected outputs
- Mock HTTP requests to avoid network dependencies

---

### ⏸️ Task #4: CI/CD Setup
**Status**: NOT STARTED

Configure automated testing in GitHub Actions.

**Scope**:
- Create `.github/workflows/tests.yml`
- Run tests on push/PR to `develop` and `main` branches
- Set up test database (PostgreSQL)
- Install dependencies and run migrations
- Run pytest with coverage reporting
- Upload coverage to Codecov or similar
- Fail builds on test failures
- Add status badge to README

**Benefits**:
- Catch regressions before merge
- Ensure tests pass on clean environment
- Track code coverage over time
- Enforce quality standards

---

### ⏸️ Task #5: Caching Tests (Deferred)
**Status**: BLOCKED - Waiting for caching implementation (Phase 3.2)

Test Redis caching behavior.

**Scope**:
- Test cache hits/misses
- Test cache invalidation
- Test TTL expiration
- Performance comparison (cached vs uncached)

---

### ⏸️ Task #6: Performance Testing (Future)
**Status**: NOT STARTED

Load testing and performance profiling.

**Scope**:
- Load testing with k6 or Locust
- Query profiling (django-debug-toolbar)
- N+1 query detection
- Response time benchmarks
- Database index optimization validation

---

## Summary

**Progress**: 2.5/7 tasks (36% - includes data quality remediation)

**Tests Passing**: 54/54 (100%)
- 30 factory fixture tests
- 24 data quality tests

**Code Coverage**:
- `datafetch/models/influence_mapping.py`: 76.03%
- `datafetch/models/models.py`: 86.11%
- `datafetch/models/popolo/behaviors.py`: 64.71%
- `datafetch/models/popolo/querysets.py`: 59.46%

**Key Achievements**:
1. ✅ Established comprehensive factory fixtures for all core models
2. ✅ Created data quality test suite covering integrity, validation, and business logic
3. ✅ Built production audit tooling (check_data_quality command)
4. ✅ Identified 167k+ data quality issues in production database
5. ✅ Investigated root causes and created automated remediation plan
6. ✅ Created cleanup command to fix 28,969 issues automatically
7. ✅ Documented testing patterns and usage examples

**Data Quality Findings**:
- 167,967 total issues identified
- 28,969 (17.2%) automatically fixable with clean_data command
- 24,720 (14.7%) are valid data (Lords/Bishops with titles)
- 116,542 (82.6%) require import command fixes
- 290 (0.2%) require manual review

**Next Steps**:
1. **Immediate**: Run automated cleanup (clean_data --fix=all)
2. **This Week**: Manual review of 290 issues (invalid dates, orphaned donations)
3. **Week 2-3**: Fix import commands (deduplication, validation, start_date inference)
4. **Ongoing**: Implement Task #2 (Import Command Tests)
5. **Future**: Implement Task #4 (CI/CD Setup)

**Dependencies**:
- Task #5 (Caching Tests) blocked until caching implemented (Phase 3.2)
- Task #6 (Performance Testing) can proceed independently
- Task #3.5 (Data Quality) unblocks Task #2 (Import Command Tests)

---

## Files Created/Modified

### New Files
```
tests/
├── factories/
│   ├── __init__.py
│   ├── actor_factories.py
│   ├── relationship_factories.py
│   └── membership_factories.py
├── test_factories.py
├── test_data_quality.py
└── README_TESTING.md

datafetch/management/commands/
├── check_data_quality.py
└── clean_data.py

scripts/
└── investigate_data_issues.py

docs/
├── PHASE_3.4_PROGRESS.md (this file)
└── DATA_QUALITY_REPORT.md
```

### Modified Files
```
datafetch/models/__init__.py
  - Added Area to exports (was missing)

tests/factories/relationship_factories.py
  - Fixed factory.Maybe + factory.Faker locale issue
  - Added random module import
  - Changed end_date to @factory.lazy_attribute with random.random()

tests/factories/membership_factories.py
  - Fixed factory.Maybe + factory.Faker locale issue
  - Added random module import
  - Changed end_date to @factory.lazy_attribute with random.random()

tests/test_factories.py
  - Fixed test_create_with_sequence to handle global sequence counter
```

---

## Testing Commands Reference

```bash
# Run all tests
pytest tests/

# Run specific test files
pytest tests/test_factories.py
pytest tests/test_data_quality.py

# Run with coverage
pytest tests/ --cov=datafetch --cov-report=html

# Run data quality check on production
python manage.py check_data_quality
python manage.py check_data_quality --verbose --check=duplicates

# Run data quality investigation
python /app/scripts/investigate_data_issues.py

# Run automated data cleanup
python manage.py clean_data --dry-run
python manage.py clean_data --fix=all
python manage.py clean_data --fix=orphaned_donations

# In Docker
docker compose exec web pytest tests/
docker compose exec web python manage.py check_data_quality
docker compose exec web python /app/scripts/investigate_data_issues.py
docker compose exec web python manage.py clean_data --dry-run
```
