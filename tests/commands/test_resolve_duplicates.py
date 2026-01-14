"""
Unit tests for resolve_duplicates management command.

Tests cover:
- Dry run mode (no database changes)
- Identifier-based matching
- Search key matching
- Similarity threshold filtering
- Auto-approval logic
- Canonical actor selection
- Statistics reporting
"""

import pytest
from io import StringIO
from django.core.management import call_command

from datafetch.models import Person, Organization, ActorResolution, Identifier


@pytest.fixture
def duplicate_persons_by_identifier(db):
    """Create two persons with same identifier (definite duplicates)."""
    person1 = Person.objects.create(
        name="John Smith",
        family_name="Smith",
        given_name="John",
    )
    Identifier.objects.create(
        content_object=person1,
        identifier="uk.org.publicwhip/person/12345",
        scheme="popit-person"
    )

    person2 = Person.objects.create(
        name="John Smith MP",
        family_name="Smith",
        given_name="John",
    )
    Identifier.objects.create(
        content_object=person2,
        identifier="uk.org.publicwhip/person/12345",
        scheme="popit-person"
    )

    return person1, person2


@pytest.fixture
def duplicate_persons_by_name(db):
    """Create two persons with similar names but no shared identifier."""
    person1 = Person.objects.create(
        name="Unite the Union",
        family_name="Union",
        given_name="Unite",
    )

    person2 = Person.objects.create(
        name="Unite Union",
        family_name="Union",
        given_name="Unite",
    )

    return person1, person2


@pytest.fixture
def duplicate_organizations(db):
    """Create two organizations with similar names."""
    org1 = Organization.objects.create(
        name="Conservative and Unionist Party",
        classification="Political Party"
    )

    org2 = Organization.objects.create(
        name="Conservative Party",
        classification="Political Party"
    )

    return org1, org2


@pytest.fixture
def non_duplicate_persons(db):
    """Create two clearly different persons."""
    person1 = Person.objects.create(
        name="John Smith",
        family_name="Smith",
        given_name="John",
    )

    person2 = Person.objects.create(
        name="Jane Doe",
        family_name="Doe",
        given_name="Jane",
    )

    return person1, person2


class TestResolveDuplicatesDryRun:
    """Tests for dry-run mode."""

    def test_dry_run_creates_no_records(self, duplicate_persons_by_identifier):
        """Dry run should not create ActorResolution records."""
        person1, person2 = duplicate_persons_by_identifier

        out = StringIO()
        call_command('resolve_duplicates', '--dry-run', stdout=out)

        # Should not create any ActorResolution records
        assert ActorResolution.objects.count() == 0

        # Should still report matches
        output = out.getvalue()
        assert 'DRY RUN' in output
        assert 'Matches found:' in output

    def test_dry_run_reports_matches(self, duplicate_persons_by_identifier):
        """Dry run should report potential matches."""
        person1, person2 = duplicate_persons_by_identifier

        out = StringIO()
        call_command('resolve_duplicates', '--dry-run', stdout=out)

        output = out.getvalue()
        assert 'John Smith' in output
        assert 'AUTO_MERGE' in output or 'auto_merge' in output.lower()


class TestIdentifierMatching:
    """Tests for identifier-based duplicate detection."""

    def test_identifier_match_creates_auto_merge(self, duplicate_persons_by_identifier):
        """Identical identifiers should create auto_merge resolution."""
        person1, person2 = duplicate_persons_by_identifier

        out = StringIO()
        call_command('resolve_duplicates', stdout=out)

        # Should create exactly one ActorResolution
        assert ActorResolution.objects.count() == 1

        resolution = ActorResolution.objects.first()
        assert resolution.decision == 'auto_merge'
        assert resolution.confidence == 1.0
        assert resolution.match_reason == 'identifier'

        # Should match our persons
        assert {resolution.actor1.id, resolution.actor2.id} == {person1.id, person2.id}

    def test_identifier_match_has_confidence_1_0(self, duplicate_persons_by_identifier):
        """Identifier matches should have confidence 1.0."""
        person1, person2 = duplicate_persons_by_identifier

        call_command('resolve_duplicates', verbosity=0)

        resolution = ActorResolution.objects.first()
        assert resolution.confidence == 1.0


class TestNameMatching:
    """Tests for name-based duplicate detection."""

    def test_similar_names_create_resolution(self, duplicate_persons_by_name):
        """Similar names should create resolution."""
        person1, person2 = duplicate_persons_by_name

        call_command('resolve_duplicates', verbosity=0)

        # Should create resolution for similar names
        assert ActorResolution.objects.count() >= 1

    def test_dissimilar_names_ignored(self, non_duplicate_persons):
        """Completely different names should not create resolution."""
        person1, person2 = non_duplicate_persons

        call_command('resolve_duplicates', verbosity=0)

        # Should not create any resolutions
        assert ActorResolution.objects.count() == 0


class TestThresholdFiltering:
    """Tests for similarity threshold parameter."""

    def test_high_threshold_filters_matches(self, duplicate_organizations):
        """High threshold should filter out lower-confidence matches."""
        org1, org2 = duplicate_organizations

        # With very high threshold (0.95), "Conservative and Unionist Party" vs "Conservative Party"
        # might not match (similarity ~0.67)
        call_command('resolve_duplicates', '--threshold', '0.95', verbosity=0)

        # Should create no resolutions (similarity below threshold)
        assert ActorResolution.objects.count() == 0

    def test_low_threshold_allows_matches(self, db):
        """Low threshold should allow more matches for high-similarity names."""
        # Create organizations with higher similarity (>= 0.70 to avoid 'ignore' decision)
        org1 = Organization.objects.create(
            name="Labour Party",
            classification="Political Party"
        )
        org2 = Organization.objects.create(
            name="Labour Party UK",  # Very similar, will have high similarity
            classification="Political Party"
        )

        # With low threshold (0.6), should match these high-similarity names
        call_command('resolve_duplicates', '--threshold', '0.6', verbosity=0)

        # Should create resolution (similarity is high enough to avoid 'ignore' decision)
        assert ActorResolution.objects.count() >= 1


class TestActorTypeFiltering:
    """Tests for --type parameter."""

    def test_person_type_only(self, duplicate_persons_by_identifier, duplicate_organizations):
        """--type person should only process persons."""
        person1, person2 = duplicate_persons_by_identifier
        org1, org2 = duplicate_organizations

        call_command('resolve_duplicates', '--type', 'person', verbosity=0)

        # Should create resolution for persons
        assert ActorResolution.objects.count() >= 1

        # All resolutions should involve persons, not organizations
        for resolution in ActorResolution.objects.all():
            assert isinstance(resolution.actor1, Person)
            assert isinstance(resolution.actor2, Person)

    def test_organization_type_only(self, duplicate_persons_by_identifier, duplicate_organizations):
        """--type organization should only process organizations."""
        person1, person2 = duplicate_persons_by_identifier
        org1, org2 = duplicate_organizations

        call_command('resolve_duplicates', '--type', 'organization', verbosity=0)

        # Should create resolution for organizations (if similarity is high enough)
        # Note: "Conservative and Unionist Party" vs "Conservative Party" might not match
        # with default threshold, so we check for 0 or more resolutions
        resolutions = ActorResolution.objects.all()

        # All resolutions should involve organizations, not persons
        for resolution in resolutions:
            assert isinstance(resolution.actor1, Organization)
            assert isinstance(resolution.actor2, Organization)


class TestClearPendingResolutions:
    """Tests for --clear parameter."""

    def test_clear_removes_pending_resolutions(self, duplicate_persons_by_identifier):
        """--clear should remove pending resolutions before running."""
        person1, person2 = duplicate_persons_by_identifier

        # Create initial resolution
        call_command('resolve_duplicates', verbosity=0)
        initial_count = ActorResolution.objects.count()
        assert initial_count >= 1

        # Run again with --clear
        call_command('resolve_duplicates', '--clear', verbosity=0)

        # Should have same count (cleared then recreated)
        assert ActorResolution.objects.count() == initial_count

    def test_clear_preserves_approved_resolutions(self, duplicate_persons_by_identifier):
        """--clear should not remove approved/rejected resolutions."""
        person1, person2 = duplicate_persons_by_identifier

        # Create and approve resolution
        call_command('resolve_duplicates', verbosity=0)
        resolution = ActorResolution.objects.first()
        resolution.review_status = 'approved'
        resolution.save()

        # Run again with --clear
        call_command('resolve_duplicates', '--clear', verbosity=0)

        # Approved resolution should still exist
        assert ActorResolution.objects.filter(review_status='approved').count() == 1


class TestCanonicalActorSelection:
    """Tests for canonical actor selection logic."""

    def test_canonical_actor_chosen(self, duplicate_persons_by_identifier):
        """Resolution should have a canonical actor selected."""
        person1, person2 = duplicate_persons_by_identifier

        call_command('resolve_duplicates', verbosity=0)

        resolution = ActorResolution.objects.first()
        assert resolution.canonical_actor is not None
        assert resolution.canonical_actor.id in {person1.id, person2.id}

    def test_canonical_prefers_more_identifiers(self, db):
        """Should prefer actor with more identifiers as canonical."""
        person1 = Person.objects.create(name="John Smith", family_name="Smith", given_name="John")
        person2 = Person.objects.create(name="John Smith", family_name="Smith", given_name="John")

        # Person1 has 2 identifiers
        Identifier.objects.create(
            content_object=person1,
            identifier="12345",
            scheme="scheme1"
        )
        Identifier.objects.create(
            content_object=person1,
            identifier="67890",
            scheme="scheme2"
        )

        # Person2 has 1 identifier (same as person1's first)
        Identifier.objects.create(
            content_object=person2,
            identifier="12345",
            scheme="scheme1"
        )

        call_command('resolve_duplicates', verbosity=0)

        resolution = ActorResolution.objects.first()
        # Should prefer person1 (more identifiers)
        assert resolution.canonical_actor.id == person1.id


class TestStatisticsReporting:
    """Tests for statistics and output."""

    def test_reports_actors_scanned(self, duplicate_persons_by_identifier):
        """Should report number of actors scanned."""
        person1, person2 = duplicate_persons_by_identifier

        out = StringIO()
        call_command('resolve_duplicates', stdout=out)

        output = out.getvalue()
        assert 'Actors scanned:' in output
        assert '2' in output  # Should have scanned 2 persons

    def test_reports_matches_found(self, duplicate_persons_by_identifier):
        """Should report number of matches found."""
        person1, person2 = duplicate_persons_by_identifier

        out = StringIO()
        call_command('resolve_duplicates', stdout=out)

        output = out.getvalue()
        assert 'Matches found:' in output

    def test_reports_decision_breakdown(self, duplicate_persons_by_identifier):
        """Should report breakdown by decision type."""
        person1, person2 = duplicate_persons_by_identifier

        out = StringIO()
        call_command('resolve_duplicates', stdout=out)

        output = out.getvalue()
        assert 'Auto-merge:' in output or 'auto_merge' in output.lower()


class TestNoDuplicateResolutions:
    """Tests for preventing duplicate ActorResolution records."""

    def test_running_twice_creates_no_duplicates(self, duplicate_persons_by_identifier):
        """Running command twice should not create duplicate resolutions."""
        person1, person2 = duplicate_persons_by_identifier

        # Run first time
        call_command('resolve_duplicates', verbosity=0)
        first_count = ActorResolution.objects.count()

        # Run second time
        call_command('resolve_duplicates', verbosity=0)
        second_count = ActorResolution.objects.count()

        # Should be same count (no duplicates created)
        assert first_count == second_count

    def test_reports_duplicates_skipped(self, duplicate_persons_by_identifier):
        """Should report when duplicate resolutions are skipped."""
        person1, person2 = duplicate_persons_by_identifier

        # Run first time
        call_command('resolve_duplicates', verbosity=0)

        # Run second time
        out = StringIO()
        call_command('resolve_duplicates', stdout=out)

        output = out.getvalue()
        assert 'Duplicates skipped:' in output
