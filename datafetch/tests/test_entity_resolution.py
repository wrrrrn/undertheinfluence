"""
Unit tests for datafetch/services/entity_resolution.py

Tests the EntityResolutionService with:
- Resolution by identifier
- Resolution by exact name
- Resolution by normalized name
- Canonical linking
- Entity scoring
- Actor merging
"""

import pytest
from decimal import Decimal
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from datafetch.models import (
    Person, Organization, Actor, Donation, Consultancy,
    MeetingAttendee, MinisterialMeeting, Identifier, OtherName,
    CompaniesHouseMatch, Membership, Post,
)
from datafetch.services.entity_resolution import (
    EntityResolutionService, ResolutionResult
)


@pytest.mark.django_db
class TestEntityResolutionService:
    """Tests for EntityResolutionService class."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        return EntityResolutionService()

    @pytest.fixture
    def org_with_ch_match(self, db):
        """Create an organization with an approved Companies House match."""
        org = Organization.objects.create(
            name="Acme Ltd",
            classification="Company"
        )
        CompaniesHouseMatch.objects.create(
            organization=org,
            company_number="12345678",
            company_name="ACME LIMITED",
            status="approved",
            confidence=0.95,
            match_reason="exact"
        )
        return org

    @pytest.fixture
    def org_without_match(self, db):
        """Create an organization without any matches."""
        return Organization.objects.create(
            name="New Company",
            classification="Company"
        )

    @pytest.fixture
    def person_with_donations(self, db):
        """Create a person with donation relationships."""
        person = Person.objects.create(
            name="John Smith",
            family_name="Smith",
            given_name="John"
        )
        # Create recipient org for donations
        recipient = Organization.objects.create(
            name="Political Party",
            classification="Political Party"
        )
        # Add some donations
        for i in range(5):
            Donation.objects.create(
                donor=person,
                recipient=recipient,
                value=Decimal("1000.00"),
                donation_type="Cash",
                accounting_units_as_central_party=False,
                is_bequest=False,
                is_aggregation=False,
                is_sponsorship=False
            )
        return person

    @pytest.fixture
    def duplicate_orgs(self, db):
        """Create duplicate organizations with same name."""
        org1 = Organization.objects.create(
            name="Tech Corp",
            classification="Company"
        )
        org2 = Organization.objects.create(
            name="Tech Corp",
            classification="Company"
        )
        # Give org1 more relationships to make it canonical
        recipient = Organization.objects.create(
            name="Charity",
            classification="Charity"
        )
        Donation.objects.create(
            donor=org1,
            recipient=recipient,
            value=Decimal("5000.00"),
            donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False,
            is_aggregation=False,
            is_sponsorship=False
        )
        return org1, org2

    def test_resolve_returns_none_for_new_actor(self, service, org_without_match):
        """New actors without matches should return None."""
        result = service.resolve(org_without_match)
        assert result is None

    def test_resolve_by_exact_name(self, service, duplicate_orgs):
        """Resolution should find duplicates by exact name."""
        org1, org2 = duplicate_orgs
        result = service.resolve(org2)
        # Should find org1 (has more data)
        assert result is not None
        assert result.pk == org1.pk

    def test_resolve_with_confidence_returns_result(self, service, duplicate_orgs):
        """resolve_with_confidence should return ResolutionResult."""
        org1, org2 = duplicate_orgs
        result = service.resolve_with_confidence(org2)
        assert isinstance(result, ResolutionResult)
        assert result.is_resolved
        assert result.confidence >= 0.70

    def test_calculate_entity_score_donations(self, service, person_with_donations):
        """Actors with donations should have higher scores."""
        score = service.calculate_entity_score(person_with_donations)
        assert score > 0
        assert score >= 100  # 5 donations * 20 points each

    def test_calculate_entity_score_ch_identifier(self, service, org_with_ch_match):
        """Actors with CH identifier should have high scores."""
        # Add identifier
        ct = ContentType.objects.get_for_model(org_with_ch_match)
        Identifier.objects.create(
            content_type=ct,
            object_id=org_with_ch_match.pk,
            scheme="uk.gov.companieshouse",
            identifier="12345678"
        )
        score = service.calculate_entity_score(org_with_ch_match)
        assert score >= 50  # CH identifier worth 50 points

    def test_calculate_entity_score_empty_actor(self, service, org_without_match):
        """Actors without relationships should have score of 0."""
        score = service.calculate_entity_score(org_without_match)
        assert score == 0

    def test_get_stats_returns_dict(self, service):
        """get_stats should return statistics dictionary."""
        stats = service.get_stats()
        assert isinstance(stats, dict)
        assert 'identifier_matches' in stats
        assert 'exact_matches' in stats
        assert 'no_match' in stats

    def test_clear_cache(self, service, duplicate_orgs):
        """clear_cache should empty the resolution cache."""
        org1, org2 = duplicate_orgs
        # Resolve to populate cache
        service.resolve(org2)
        assert len(service._cache) > 0

        # Clear cache
        service.clear_cache()
        assert len(service._cache) == 0

    def test_find_duplicates(self, service, duplicate_orgs):
        """find_duplicates should return potential duplicates."""
        org1, org2 = duplicate_orgs
        duplicates = service.find_duplicates(org2)
        assert len(duplicates) >= 1
        # Should find org1
        assert any(r.canonical.pk == org1.pk for r in duplicates)


@pytest.mark.django_db
class TestEntityResolutionMerge:
    """Tests for actor merging functionality."""

    @pytest.fixture
    def service(self):
        return EntityResolutionService()

    @pytest.fixture
    def source_target_orgs(self, db):
        """Create source and target organizations for merging."""
        source = Organization.objects.create(
            name="Old Company Name",
            classification="Company"
        )
        target = Organization.objects.create(
            name="Canonical Company",
            classification="Company"
        )
        # Add donation to source
        recipient = Organization.objects.create(
            name="Charity",
            classification="Charity"
        )
        Donation.objects.create(
            donor=source,
            recipient=recipient,
            value=Decimal("1000.00"),
            donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False,
            is_aggregation=False,
            is_sponsorship=False
        )
        return source, target

    def test_merge_actors_dry_run(self, service, source_target_orgs):
        """Dry run should not modify database."""
        source, target = source_target_orgs

        counts = service.merge_actors(source, target, dry_run=True)

        # Should return counts
        assert counts['donations_donor'] == 1

        # Source should still exist
        assert Organization.objects.filter(pk=source.pk).exists()

    def test_merge_actors_updates_donations(self, service, source_target_orgs):
        """Merging should update donation relationships."""
        source, target = source_target_orgs
        source_pk = source.pk  # Save pk before merge deletes source

        counts = service.merge_actors(source, target, dry_run=False)

        # Donations should now point to target
        assert counts['donations_donor'] == 1
        assert Donation.objects.filter(donor=target).count() == 1
        # Source is deleted, so query by pk (should find 0)
        assert Donation.objects.filter(donor_id=source_pk).count() == 0

    def test_merge_actors_deletes_source(self, service, source_target_orgs):
        """Merging should delete source actor."""
        source, target = source_target_orgs
        source_pk = source.pk

        service.merge_actors(source, target, dry_run=False)

        # Source should be deleted
        assert not Organization.objects.filter(pk=source_pk).exists()

    def test_merge_actors_creates_other_name(self, service, source_target_orgs):
        """Merging should add source name as OtherName on target."""
        source, target = source_target_orgs
        source_name = source.name

        service.merge_actors(source, target, dry_run=False)

        # Check OtherName was created
        ct = ContentType.objects.get_for_model(target)
        assert OtherName.objects.filter(
            content_type=ct,
            object_id=target.pk,
            name=source_name
        ).exists()


@pytest.mark.django_db
class TestResolutionResult:
    """Tests for ResolutionResult dataclass."""

    def test_is_resolved_true(self, db):
        """is_resolved should be True when canonical exists with good confidence."""
        org = Organization.objects.create(name="Test", classification="Company")
        result = ResolutionResult(
            canonical=org,
            confidence=0.85,
            match_reason="exact"
        )
        assert result.is_resolved is True

    def test_is_resolved_false_no_canonical(self):
        """is_resolved should be False when canonical is None."""
        result = ResolutionResult(
            canonical=None,
            confidence=0.0,
            match_reason="no_match"
        )
        assert result.is_resolved is False

    def test_is_resolved_false_low_confidence(self, db):
        """is_resolved should be False when confidence is too low."""
        org = Organization.objects.create(name="Test", classification="Company")
        result = ResolutionResult(
            canonical=org,
            confidence=0.50,  # Below threshold
            match_reason="fuzzy"
        )
        assert result.is_resolved is False
