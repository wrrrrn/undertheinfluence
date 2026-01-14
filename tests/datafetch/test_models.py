"""
Unit tests for datafetch models.

Tests cover:
- Person and Organization creation
- Polymorphic Actor queries
- Donation relationships
- Temporal queries (date ranges)
"""

import pytest
from django.db import IntegrityError


class TestActorModels:
    """Tests for Actor, Person, and Organization models."""

    def test_person_creation(self, person):
        """Test that a Person can be created with required fields."""
        assert person.name == "John Smith"
        assert person.family_name == "Smith"
        assert person.given_name == "John"
        assert person.sort_name == "Smith, John"

    def test_organization_creation(self, organization):
        """Test that an Organization can be created."""
        assert organization.name == "Test Organization Ltd"
        assert organization.classification == "Company"

    def test_political_party_creation(self, political_party):
        """Test that a Political Party can be created."""
        assert political_party.name == "Test Party"
        assert political_party.classification == "Political Party"

    def test_actor_polymorphic_query(self, person, organization, db):
        """Test that Actor queries return both Person and Organization instances."""
        from datafetch.models import Actor

        actors = Actor.objects.all()
        assert actors.count() >= 2

        # Check that we can filter by instance type
        persons = Actor.objects.instance_of(person.__class__)
        assert person in persons

        orgs = Actor.objects.instance_of(organization.__class__)
        assert organization in orgs


class TestDonationModel:
    """Tests for Donation model."""

    def test_donation_creation(self, donation):
        """Test that a Donation can be created between actors."""
        assert donation.value == 10000.00
        # received_date is stored as DateField, gets converted to date object
        assert str(donation.received_date) == "2024-01-15"
        assert donation.donation_type == "Cash"
        assert donation.donor is not None
        assert donation.recipient is not None

    def test_donation_with_canonical_fields(self, db, person, organization):
        """Test canonical donor/recipient fields (Phase 3.1)."""
        from datafetch.models import Donation

        donation = Donation.objects.create(
            donor=organization,
            recipient=person,
            value=5000.00,
            received_date="2024-01-15",
            donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False,
            is_aggregation=False,
            is_sponsorship=False,
        )

        # Initially, canonical fields should be None
        # (Will be set by entity resolution in Phase 3.1)
        assert donation.donor == organization
        assert donation.recipient == person


class TestMembershipModel:
    """Tests for Membership model."""

    def test_membership_creation(self, membership):
        """Test that a Membership can link a person to an organization."""
        assert membership.person is not None
        assert membership.organization is not None
        assert membership.role == "Member"
        assert membership.start_date == "2020-01-01"

    def test_membership_temporal_query(self, db, person, political_party, sample_date):
        """Test temporal filtering of memberships (Phase 3.1 foundation)."""
        from datafetch.models import Membership

        # Create membership with date range
        membership = Membership.objects.create(
            person=person,
            organization=political_party,
            role="Member",
            start_date="2020-01-01",
            end_date="2023-12-31",
        )

        # Query memberships active at a specific date
        active_memberships = Membership.objects.filter(
            person=person,
            start_date__lte="2022-06-01",
        ).filter(
            end_date__gte="2022-06-01"
        )

        assert membership in active_memberships


class TestConsultancyModel:
    """Tests for Consultancy model."""

    def test_consultancy_creation(self, consultancy):
        """Test that a Consultancy relationship can be created."""
        assert consultancy.client is not None
        assert consultancy.agency is not None
        assert consultancy.start_date == "2024-01-01"

    def test_dual_influence_query(self, db, organization, donation, consultancy):
        """
        Test querying organizations that both donate and lobby.

        This tests the foundation for the "dual influence" analysis
        highlighted in the comprehensive data analysis report.
        """
        from datafetch.models import Consultancy, Donation, Organization

        # Find organizations that are both donation donors AND lobbying clients
        donor_org_ids = Donation.objects.values_list('donor_id', flat=True).distinct()
        client_org_ids = Consultancy.objects.values_list('client_id', flat=True).distinct()

        dual_influence_ids = set(donor_org_ids) & set(client_org_ids)

        # Should find at least our test organization
        assert len(dual_influence_ids) >= 1
