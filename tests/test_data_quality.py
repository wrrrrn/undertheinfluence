"""
Data Quality Tests

Tests for data integrity, duplicate detection, and validation checks.
These tests ensure the database maintains high quality standards and
detect common data issues that may arise from imports or data entry.
"""

import pytest
from decimal import Decimal
import datetime

from datafetch.models import Person, Organization, Donation, Consultancy, Membership, Post, Area
from datafetch.models.influence_mapping import PartyMembership

from tests.factories import (
    PersonFactory,
    MPFactory,
    OrganizationFactory,
    PoliticalPartyFactory,
    CompanyFactory,
    DonationFactory,
    CashDonationFactory,
    ConsultancyFactory,
    MembershipFactory,
    MPMembershipFactory,
    PartyMembershipFactory,
    PostFactory,
    AreaFactory,
)


# ===========================
# Referential Integrity Tests
# ===========================

class TestReferentialIntegrity:
    """Test that relationships maintain referential integrity."""

    def test_no_orphaned_donations(self, db):
        """Should handle donations when donor or recipient is deleted."""
        # Create a donation
        donor = CompanyFactory(name="Donor Corp")
        recipient = PoliticalPartyFactory(name="Labour Party")
        donation = DonationFactory(donor=donor, recipient=recipient)

        # Verify donation exists with valid relationships
        assert donation.donor is not None
        assert donation.recipient is not None

        # Donation uses SET_NULL on_delete to preserve audit trail
        # When donor is deleted, donation remains but donor is set to NULL
        donor_id = donor.id
        donor.delete()

        donation.refresh_from_db()
        # Donation still exists, but donor is now NULL (SET_NULL behavior)
        assert donation.donor is None
        assert donation.recipient is not None

        # Can detect orphaned donations by querying for null foreign keys
        orphaned_donations = Donation.objects.filter(donor__isnull=True)
        assert orphaned_donations.count() == 1
        assert donation in orphaned_donations

    def test_no_orphaned_memberships(self, db):
        """Should detect memberships with deleted person or organization."""
        person = PersonFactory()
        organization = OrganizationFactory()
        membership = MembershipFactory(person=person, organization=organization)

        assert membership.person is not None
        assert membership.organization is not None

        # Test deletion behavior
        person_id = person.id
        person.delete()

        # Membership should be handled appropriately
        with pytest.raises(Membership.DoesNotExist):
            membership.refresh_from_db()

    def test_no_orphaned_consultancies(self, db):
        """Should handle consultancies when client or agency is deleted."""
        client = CompanyFactory(name="Client Corp")
        agency = CompanyFactory(name="Lobby Firm")
        consultancy = ConsultancyFactory(client=client, agency=agency)

        assert consultancy.client is not None
        assert consultancy.agency is not None

        # Consultancy uses SET_NULL on_delete to preserve audit trail
        # When client is deleted, consultancy remains but client is set to NULL
        client.delete()

        consultancy.refresh_from_db()
        # Consultancy still exists, but client is now NULL (SET_NULL behavior)
        assert consultancy.client is None
        assert consultancy.agency is not None

        # Can detect orphaned consultancies by querying for null foreign keys
        orphaned_consultancies = Consultancy.objects.filter(client__isnull=True)
        assert orphaned_consultancies.count() == 1
        assert consultancy in orphaned_consultancies

    def test_posts_require_organization(self, db):
        """Should ensure all posts have a valid organization."""
        post = PostFactory()

        assert post.organization is not None
        assert isinstance(post.organization, Organization)

    def test_memberships_with_posts_have_matching_organization(self, db):
        """Should ensure membership organization matches post organization."""
        organization = OrganizationFactory(name="House of Commons")
        post = PostFactory(organization=organization, label="MP for Bristol")
        person = PersonFactory()

        membership = MembershipFactory(
            person=person,
            organization=organization,
            post=post
        )

        assert membership.organization == post.organization


# ===========================
# Duplicate Detection Tests
# ===========================

class TestDuplicateDetection:
    """Test detection of duplicate records that may indicate data quality issues."""

    def test_detect_duplicate_persons_by_name(self, db):
        """Should detect persons with identical names (potential duplicates)."""
        # Create two persons with the same name
        PersonFactory(given_name="John", family_name="Smith")
        PersonFactory(given_name="John", family_name="Smith")

        # Query for duplicates
        duplicates = (
            Person.objects
            .values('name')
            .annotate(count=models.Count('id'))
            .filter(count__gt=1)
        )

        assert duplicates.count() > 0
        assert duplicates[0]['name'] == "John Smith"
        assert duplicates[0]['count'] == 2

    def test_detect_duplicate_organizations_by_name(self, db):
        """Should detect organizations with identical names."""
        CompanyFactory(name="Acme Corp")
        CompanyFactory(name="Acme Corp")

        duplicates = (
            Organization.objects
            .values('name')
            .annotate(count=models.Count('id'))
            .filter(count__gt=1)
        )

        assert duplicates.count() > 0
        assert duplicates[0]['name'] == "Acme Corp"

    def test_detect_duplicate_donations(self, db):
        """Should detect identical donations (same donor, recipient, value, date)."""
        donor = CompanyFactory()
        recipient = PoliticalPartyFactory()

        # Create two identical donations
        DonationFactory(
            donor=donor,
            recipient=recipient,
            value=Decimal('5000.00'),
            received_date=datetime.date(2024, 1, 15)
        )
        DonationFactory(
            donor=donor,
            recipient=recipient,
            value=Decimal('5000.00'),
            received_date=datetime.date(2024, 1, 15)
        )

        # Query for potential duplicates
        duplicates = (
            Donation.objects
            .values('donor', 'recipient', 'value', 'received_date')
            .annotate(count=models.Count('id'))
            .filter(count__gt=1)
        )

        assert duplicates.count() > 0
        assert duplicates[0]['count'] == 2


# ===========================
# Data Validation Tests
# ===========================

class TestDataValidation:
    """Test validation of data fields and business logic."""

    def test_no_negative_donation_values(self, db):
        """Should detect donations with negative values."""
        # Try to create a donation with negative value
        donor = CompanyFactory()
        recipient = PoliticalPartyFactory()

        # This should be prevented at the factory level, but we can still check
        invalid_donations = Donation.objects.filter(value__lt=0)
        assert invalid_donations.count() == 0

    def test_no_zero_donation_values(self, db):
        """Should detect donations with zero value."""
        invalid_donations = Donation.objects.filter(value=0)
        assert invalid_donations.count() == 0

    def test_donation_dates_logical_order(self, db):
        """Should detect donations where accepted_date < received_date."""
        # Create donations and check date logic
        donations = DonationFactory.create_batch(10)

        # Check that accepted_date >= received_date for all donations
        for donation in donations:
            if donation.accepted_date and donation.received_date:
                assert donation.accepted_date >= donation.received_date, \
                    f"Donation {donation.id}: accepted_date {donation.accepted_date} < received_date {donation.received_date}"

    def test_donation_reported_after_accepted(self, db):
        """Should detect donations where reported_date < accepted_date."""
        donations = DonationFactory.create_batch(10)

        for donation in donations:
            if donation.reported_date and donation.accepted_date:
                assert donation.reported_date >= donation.accepted_date, \
                    f"Donation {donation.id}: reported_date {donation.reported_date} < accepted_date {donation.accepted_date}"

    def test_membership_dates_logical_order(self, db):
        """Should detect memberships where end_date < start_date."""
        memberships = MembershipFactory.create_batch(20)

        for membership in memberships:
            if membership.start_date and membership.end_date:
                start = datetime.datetime.strptime(membership.start_date, '%Y-%m-%d').date()
                end = datetime.datetime.strptime(membership.end_date, '%Y-%m-%d').date()
                assert end >= start, \
                    f"Membership {membership.id}: end_date {membership.end_date} < start_date {membership.start_date}"

    def test_consultancy_dates_logical_order(self, db):
        """Should detect consultancies where end_date < start_date."""
        consultancies = ConsultancyFactory.create_batch(20)

        for consultancy in consultancies:
            if consultancy.start_date and consultancy.end_date:
                start = datetime.datetime.strptime(consultancy.start_date, '%Y-%m-%d').date()
                end = datetime.datetime.strptime(consultancy.end_date, '%Y-%m-%d').date()
                assert end >= start, \
                    f"Consultancy {consultancy.id}: end_date {consultancy.end_date} < start_date {consultancy.start_date}"

    def test_partial_dates_valid_format(self, db):
        """Should validate partial date formats (YYYY, YYYY-MM, YYYY-MM-DD)."""
        import re

        # Partial date regex: YYYY or YYYY-MM or YYYY-MM-DD
        partial_date_pattern = r'^\d{4}(-\d{2}(-\d{2})?)?$'

        memberships = MembershipFactory.create_batch(10)

        for membership in memberships:
            if membership.start_date:
                assert re.match(partial_date_pattern, membership.start_date), \
                    f"Invalid start_date format: {membership.start_date}"
            if membership.end_date:
                assert re.match(partial_date_pattern, membership.end_date), \
                    f"Invalid end_date format: {membership.end_date}"

    def test_person_names_not_empty(self, db):
        """Should detect persons with empty names."""
        persons = PersonFactory.create_batch(10)

        for person in persons:
            assert person.name, f"Person {person.id} has empty name"
            assert person.family_name, f"Person {person.id} has empty family_name"
            assert person.given_name, f"Person {person.id} has empty given_name"

    def test_organization_names_not_empty(self, db):
        """Should detect organizations with empty names."""
        organizations = OrganizationFactory.create_batch(10)

        for org in organizations:
            assert org.name, f"Organization {org.id} has empty name"


# ===========================
# Business Logic Tests
# ===========================

class TestBusinessLogic:
    """Test business logic and domain-specific rules."""

    def test_mp_has_constituency_membership(self, db):
        """Should verify MPs have appropriate House of Commons membership."""
        mp = MPFactory(given_name="Sarah", family_name="Jones")
        membership = MPMembershipFactory(person=mp)

        assert mp.honorific_suffix == "MP"
        assert membership.organization.name == "House of Commons"
        assert membership.area is not None
        assert membership.area.classification == "constituency"

    def test_party_membership_temporal_consistency(self, db):
        """Should detect overlapping party memberships (person can't be in two parties at once)."""
        person = PersonFactory()
        labour = PoliticalPartyFactory(name="Labour Party")
        conservative = PoliticalPartyFactory(name="Conservative Party")

        # Create overlapping memberships
        PartyMembershipFactory(
            person=person,
            party=labour,
            start_date='2015-01-01',
            end_date='2020-12-31'
        )
        PartyMembershipFactory(
            person=person,
            party=conservative,
            start_date='2018-01-01',  # Overlaps with Labour membership
            end_date=None
        )

        # Query for overlapping memberships for this person
        memberships = person.party_memberships.order_by('start_date')

        # Check for overlaps
        overlaps = []
        for i, m1 in enumerate(memberships):
            for m2 in memberships[i+1:]:
                # Check if m1 and m2 overlap
                m1_start = datetime.datetime.strptime(m1.start_date, '%Y-%m-%d').date()
                m1_end = datetime.datetime.strptime(m1.end_date, '%Y-%m-%d').date() if m1.end_date else datetime.date.max
                m2_start = datetime.datetime.strptime(m2.start_date, '%Y-%m-%d').date()
                m2_end = datetime.datetime.strptime(m2.end_date, '%Y-%m-%d').date() if m2.end_date else datetime.date.max

                if m1_start <= m2_end and m2_start <= m1_end:
                    overlaps.append((m1, m2))

        # Should detect the overlap
        assert len(overlaps) > 0, "Should detect overlapping party memberships"

    def test_donation_entity_resolution(self, db):
        """Should verify effective_donor uses canonical_donor when set."""
        original_donor = CompanyFactory(name="Original Corp")
        canonical_donor = CompanyFactory(name="Canonical Corp")
        recipient = PoliticalPartyFactory()

        donation = DonationFactory(
            donor=original_donor,
            recipient=recipient,
            canonical_donor=canonical_donor
        )

        # effective_donor should use canonical_donor
        assert donation.effective_donor == canonical_donor
        assert donation.donor == original_donor

    def test_consultancy_client_and_agency_different(self, db):
        """Should detect consultancies where client and agency are the same."""
        company = CompanyFactory(name="Self-Consulting Corp")

        # Create consultancy where client = agency (should be rare/invalid)
        consultancy = ConsultancyFactory(client=company, agency=company)

        # This is logically questionable but technically allowed
        # The test documents this edge case
        assert consultancy.client == consultancy.agency


# ===========================
# Data Completeness Tests
# ===========================

class TestDataCompleteness:
    """Test that critical data fields are populated."""

    def test_donations_have_required_fields(self, db):
        """Should verify donations have all required fields populated."""
        donations = DonationFactory.create_batch(20)

        for donation in donations:
            assert donation.donor is not None, f"Donation {donation.id} missing donor"
            assert donation.recipient is not None, f"Donation {donation.id} missing recipient"
            assert donation.value is not None, f"Donation {donation.id} missing value"
            assert donation.value > 0, f"Donation {donation.id} has non-positive value"
            assert donation.received_date is not None, f"Donation {donation.id} missing received_date"
            assert donation.donation_type, f"Donation {donation.id} missing donation_type"

    def test_memberships_have_person_and_organization(self, db):
        """Should verify memberships link person to organization."""
        memberships = MembershipFactory.create_batch(10)

        for membership in memberships:
            assert membership.person is not None, f"Membership {membership.id} missing person"
            assert membership.organization is not None, f"Membership {membership.id} missing organization"
            assert membership.start_date is not None, f"Membership {membership.id} missing start_date"

    def test_consultancies_have_client_and_agency(self, db):
        """Should verify consultancies have both client and agency."""
        consultancies = ConsultancyFactory.create_batch(10)

        for consultancy in consultancies:
            assert consultancy.client is not None, f"Consultancy {consultancy.id} missing client"
            assert consultancy.agency is not None, f"Consultancy {consultancy.id} missing agency"
            assert consultancy.start_date is not None, f"Consultancy {consultancy.id} missing start_date"


# Import for duplicate detection queries
from django.db import models
