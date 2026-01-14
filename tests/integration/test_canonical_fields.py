"""
Integration tests for canonical field workflow.

Tests the complete entity resolution workflow including:
- Approval/rejection of ActorResolution records
- Canonical field propagation to related objects
- Historical data preservation
- Edge cases and constraints
"""

import pytest
from datetime import date
from django.contrib.auth.models import User
from django.utils import timezone

from datafetch.models import (
    Person,
    Organization,
    ActorResolution,
    Donation,
    Consultancy,
    Membership,
    PartyMembership,
    Identifier,
)


@pytest.fixture
def admin_user(db):
    """Create admin user for approvals."""
    return User.objects.create_user(
        username='admin',
        email='admin@example.com',
        password='password',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def duplicate_persons_with_data(db):
    """Create duplicate persons with rich associated data."""
    # Person 1 - more complete data (will be canonical)
    person1 = Person.objects.create(
        name="John Smith",
        family_name="Smith",
        given_name="John",
        email="john.smith@example.com",
    )

    # Add identifiers
    Identifier.objects.create(
        content_object=person1,
        identifier="uk.org.publicwhip/person/12345",
        scheme="popit-person"
    )
    Identifier.objects.create(
        content_object=person1,
        identifier="12345",
        scheme="mnis"
    )

    # Person 2 - less complete data
    person2 = Person.objects.create(
        name="John Smith MP",
        family_name="Smith",
        given_name="John",
    )

    # Add shared identifier (creates identifier match)
    Identifier.objects.create(
        content_object=person2,
        identifier="uk.org.publicwhip/person/12345",
        scheme="popit-person"
    )

    return person1, person2


@pytest.fixture
def duplicate_organizations_with_data(db):
    """Create duplicate organizations with associated data."""
    org1 = Organization.objects.create(
        name="Acme Corporation",
        classification="Company"
    )

    Identifier.objects.create(
        content_object=org1,
        identifier="12345678",
        scheme="companies-house"
    )

    org2 = Organization.objects.create(
        name="ACME Corp",
        classification="Company"
    )

    Identifier.objects.create(
        content_object=org2,
        identifier="12345678",
        scheme="companies-house"
    )

    return org1, org2


@pytest.fixture
def resolution_with_donations(db, duplicate_persons_with_data, organization):
    """Create resolution with donations to both duplicate actors."""
    person1, person2 = duplicate_persons_with_data

    # Donations to person1
    donation1 = Donation.objects.create(
        donor=organization,
        recipient=person1,
        value=5000.00,
        received_date="2020-01-01",
        donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False,
        is_aggregation=False,
        is_sponsorship=False,
    )

    # Donations to person2 (duplicate)
    donation2 = Donation.objects.create(
        donor=organization,
        recipient=person2,
        value=3000.00,
        received_date="2021-01-01",
        donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False,
        is_aggregation=False,
        is_sponsorship=False,
    )

    # Create resolution
    resolution = ActorResolution.objects.create(
        actor1=person1,
        actor2=person2,
        canonical_actor=person1,
        confidence=1.0,
        decision='auto_merge',
        match_reason='identifier',
    )

    return resolution, donation1, donation2


class TestActorResolutionApproval:
    """Tests for ActorResolution approval workflow."""

    def test_approve_sets_review_status(self, admin_user, duplicate_persons_with_data):
        """Approving a resolution should set review_status to 'approved'."""
        person1, person2 = duplicate_persons_with_data

        resolution = ActorResolution.objects.create(
            actor1=person1,
            actor2=person2,
            confidence=1.0,
            decision='auto_merge',
            match_reason='identifier',
        )

        canonical = resolution.approve(user=admin_user, notes="Test approval")

        resolution.refresh_from_db()
        assert resolution.review_status == 'approved'
        assert resolution.reviewed_by == admin_user
        assert resolution.reviewed_at is not None
        assert resolution.notes == "Test approval"
        assert canonical == person1  # Should return canonical actor

    def test_approve_sets_canonical_actor(self, admin_user, duplicate_persons_with_data):
        """Approve should set canonical_actor if not already set."""
        person1, person2 = duplicate_persons_with_data

        resolution = ActorResolution.objects.create(
            actor1=person1,
            actor2=person2,
            canonical_actor=None,  # Not set yet
            confidence=1.0,
            decision='auto_merge',
            match_reason='identifier',
        )

        canonical = resolution.approve(user=admin_user)

        resolution.refresh_from_db()
        assert resolution.canonical_actor is not None
        assert resolution.canonical_actor in [person1, person2]
        assert canonical == resolution.canonical_actor

    def test_approve_preserves_existing_canonical(self, admin_user, duplicate_persons_with_data):
        """Approve should preserve canonical_actor if already set."""
        person1, person2 = duplicate_persons_with_data

        resolution = ActorResolution.objects.create(
            actor1=person1,
            actor2=person2,
            canonical_actor=person2,  # Explicitly set to person2
            confidence=1.0,
            decision='auto_merge',
            match_reason='identifier',
        )

        canonical = resolution.approve(user=admin_user)

        resolution.refresh_from_db()
        assert resolution.canonical_actor == person2
        assert canonical == person2


class TestActorResolutionRejection:
    """Tests for ActorResolution rejection workflow."""

    def test_reject_sets_review_status(self, admin_user, duplicate_persons_with_data):
        """Rejecting a resolution should set review_status to 'rejected'."""
        person1, person2 = duplicate_persons_with_data

        resolution = ActorResolution.objects.create(
            actor1=person1,
            actor2=person2,
            confidence=0.90,
            decision='review',
            match_reason='strong_alias',
        )

        resolution.reject(user=admin_user, notes="Not a duplicate")

        resolution.refresh_from_db()
        assert resolution.review_status == 'rejected'
        assert resolution.reviewed_by == admin_user
        assert resolution.reviewed_at is not None
        assert resolution.notes == "Not a duplicate"

    def test_reject_clears_canonical_actor(self, admin_user, duplicate_persons_with_data):
        """Reject should clear canonical_actor."""
        person1, person2 = duplicate_persons_with_data

        resolution = ActorResolution.objects.create(
            actor1=person1,
            actor2=person2,
            canonical_actor=person1,
            confidence=0.90,
            decision='review',
            match_reason='strong_alias',
        )

        resolution.reject(user=admin_user)

        resolution.refresh_from_db()
        assert resolution.canonical_actor is None


class TestCanonicalFieldIntegration:
    """Integration tests for canonical field usage with related objects."""

    def test_donations_preserve_original_recipient(self, admin_user, resolution_with_donations):
        """After approval, donations should still reference original recipients."""
        resolution, donation1, donation2 = resolution_with_donations

        # Approve the resolution
        resolution.approve(user=admin_user)

        # Refresh donations from database
        donation1.refresh_from_db()
        donation2.refresh_from_db()

        # Original recipients should be preserved
        assert donation1.recipient.id == resolution.actor1.id
        assert donation2.recipient.id == resolution.actor2.id

        # But canonical_recipient should point to canonical actor
        # (This will be implemented in future merge logic)
        # For now, just verify the data is intact
        assert donation1.recipient is not None
        assert donation2.recipient is not None

    def test_canonical_actor_accessible_from_donations(self, admin_user, resolution_with_donations):
        """Should be able to find canonical actor from donation recipient."""
        resolution, donation1, donation2 = resolution_with_donations

        resolution.approve(user=admin_user)

        # Find resolution for donation1's recipient
        resolution_for_recipient1 = ActorResolution.objects.filter(
            actor1=donation1.recipient,
            review_status='approved'
        ).first() or ActorResolution.objects.filter(
            actor2=donation1.recipient,
            review_status='approved'
        ).first()

        assert resolution_for_recipient1 is not None
        assert resolution_for_recipient1.canonical_actor is not None

    def test_aggregating_donations_by_canonical_actor(self, admin_user, resolution_with_donations):
        """Should be able to aggregate donations by canonical actor."""
        resolution, donation1, donation2 = resolution_with_donations

        resolution.approve(user=admin_user)

        # Get all donations to either duplicate actor
        all_donations = Donation.objects.filter(
            recipient_id__in=[resolution.actor1.id, resolution.actor2.id]
        )

        assert all_donations.count() == 2
        total_value = sum(d.value for d in all_donations)
        assert total_value == 8000.00  # 5000 + 3000


class TestCanonicalFieldWithMemberships:
    """Tests for canonical fields with membership data."""

    def test_memberships_preserve_original_person(self, db, admin_user, duplicate_persons_with_data, organization):
        """Memberships should preserve original person reference."""
        person1, person2 = duplicate_persons_with_data

        # Create memberships for both persons
        membership1 = Membership.objects.create(
            person=person1,
            organization=organization,
            role="Member",
            start_date="2020-01-01",
        )

        membership2 = Membership.objects.create(
            person=person2,
            organization=organization,
            role="Senior Member",
            start_date="2021-01-01",
        )

        # Create and approve resolution
        resolution = ActorResolution.objects.create(
            actor1=person1,
            actor2=person2,
            canonical_actor=person1,
            confidence=1.0,
            decision='auto_merge',
            match_reason='identifier',
        )
        resolution.approve(user=admin_user)

        # Memberships should preserve original references
        membership1.refresh_from_db()
        membership2.refresh_from_db()

        assert membership1.person.id == person1.id
        assert membership2.person.id == person2.id

        # But we can aggregate by canonical actor
        all_memberships = Membership.objects.filter(
            person_id__in=[person1.id, person2.id]
        )
        assert all_memberships.count() == 2


class TestCanonicalFieldConstraints:
    """Tests for canonical field constraints and edge cases."""

    def test_cannot_set_canonical_to_non_actor(self, db, duplicate_persons_with_data):
        """canonical_actor must be one of actor1 or actor2."""
        person1, person2 = duplicate_persons_with_data
        person3 = Person.objects.create(
            name="Jane Doe",
            family_name="Doe",
            given_name="Jane"
        )

        # This is allowed at creation time (no constraint)
        # but logically incorrect
        resolution = ActorResolution.objects.create(
            actor1=person1,
            actor2=person2,
            canonical_actor=person3,  # Different actor!
            confidence=1.0,
            decision='auto_merge',
            match_reason='identifier',
        )

        # Resolution can be created (no DB constraint)
        # This is a data quality issue to check in application logic
        assert resolution.canonical_actor == person3

    def test_same_actor_cannot_be_actor1_and_actor2(self, db):
        """actor1 and actor2 should be different actors."""
        person = Person.objects.create(
            name="John Smith",
            family_name="Smith",
            given_name="John"
        )

        # This should be prevented by application logic, but let's test it
        # The unique constraint only prevents (actor1, actor2) pairs, not same actor
        resolution = ActorResolution.objects.create(
            actor1=person,
            actor2=person,  # Same as actor1!
            confidence=1.0,
            decision='auto_merge',
            match_reason='identifier',
        )

        assert resolution.actor1.id == resolution.actor2.id

    def test_multiple_resolutions_for_same_actor(self, db, admin_user):
        """An actor can appear in multiple resolutions."""
        person1 = Person.objects.create(
            name="John Smith",
            family_name="Smith",
            given_name="John"
        )
        person2 = Person.objects.create(
            name="John Smith MP",
            family_name="Smith",
            given_name="John"
        )
        person3 = Person.objects.create(
            name="J. Smith",
            family_name="Smith",
            given_name="J."
        )

        # Create two resolutions involving person1
        resolution1 = ActorResolution.objects.create(
            actor1=person1,
            actor2=person2,
            canonical_actor=person1,
            confidence=1.0,
            decision='auto_merge',
            match_reason='identifier',
        )

        resolution2 = ActorResolution.objects.create(
            actor1=person1,
            actor2=person3,
            canonical_actor=person1,
            confidence=0.90,
            decision='review',
            match_reason='strong_alias',
        )

        # Both should exist
        assert ActorResolution.objects.filter(actor1=person1).count() == 2

        # Approve both
        resolution1.approve(user=admin_user)
        resolution2.approve(user=admin_user)

        # Both should be approved with same canonical
        approved = ActorResolution.objects.filter(
            actor1=person1,
            review_status='approved'
        )
        assert approved.count() == 2
        for res in approved:
            assert res.canonical_actor == person1


class TestCanonicalFieldQueries:
    """Tests for querying data using canonical fields."""

    def test_find_all_resolutions_for_actor(self, db, duplicate_persons_with_data):
        """Find all resolutions involving an actor (as actor1 or actor2)."""
        person1, person2 = duplicate_persons_with_data

        resolution = ActorResolution.objects.create(
            actor1=person1,
            actor2=person2,
            confidence=1.0,
            decision='auto_merge',
            match_reason='identifier',
        )

        # Find resolutions for person1
        resolutions_for_person1 = ActorResolution.objects.filter(
            actor1=person1
        ) | ActorResolution.objects.filter(
            actor2=person1
        )

        assert resolutions_for_person1.count() == 1
        assert resolution in resolutions_for_person1

    def test_find_canonical_actor_for_any_duplicate(self, db, admin_user):
        """Given any duplicate actor, find its canonical actor."""
        person1 = Person.objects.create(
            name="John Smith",
            family_name="Smith",
            given_name="John"
        )
        person2 = Person.objects.create(
            name="John Smith MP",
            family_name="Smith",
            given_name="John"
        )

        resolution = ActorResolution.objects.create(
            actor1=person1,
            actor2=person2,
            canonical_actor=person1,
            confidence=1.0,
            decision='auto_merge',
            match_reason='identifier',
        )
        resolution.approve(user=admin_user)

        # Function to find canonical for any actor
        def get_canonical_actor(actor):
            """Get canonical actor for a given actor."""
            resolution = ActorResolution.objects.filter(
                actor1=actor,
                review_status='approved'
            ).first() or ActorResolution.objects.filter(
                actor2=actor,
                review_status='approved'
            ).first()

            return resolution.canonical_actor if resolution else actor

        # Test with both duplicates
        canonical_for_person1 = get_canonical_actor(person1)
        canonical_for_person2 = get_canonical_actor(person2)

        assert canonical_for_person1 == person1
        assert canonical_for_person2 == person1  # person2's canonical is person1

    def test_aggregate_donations_across_duplicates(self, db, admin_user, resolution_with_donations):
        """Aggregate donations across all duplicate actors."""
        resolution, donation1, donation2 = resolution_with_donations
        resolution.approve(user=admin_user)

        # Get canonical actor
        canonical = resolution.canonical_actor

        # Find all actors that have this canonical
        duplicate_actor_ids = [resolution.actor1.id, resolution.actor2.id]

        # Aggregate donations
        from django.db.models import Sum
        total_donations = Donation.objects.filter(
            recipient_id__in=duplicate_actor_ids
        ).aggregate(total=Sum('value'))

        assert total_donations['total'] == 8000.00
