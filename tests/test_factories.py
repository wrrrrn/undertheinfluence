"""
Tests for factory fixtures.

These tests verify that factories create valid model instances
and demonstrate common usage patterns.
"""

import pytest
from decimal import Decimal
import datetime

from datafetch.models import Person, Organization, Donation, Consultancy, Membership, Post
from datafetch.models.influence_mapping import PartyMembership

from tests.factories import (
    PersonFactory,
    MPFactory,
    OrganizationFactory,
    PoliticalPartyFactory,
    CompanyFactory,
    TradeUnionFactory,
    ConsultancyFirmFactory,
    DonationFactory,
    CashDonationFactory,
    LargeDonationFactory,
    ConsultancyFactory,
    PostFactory,
    MPPostFactory,
    MembershipFactory,
    MPMembershipFactory,
    PartyMembershipFactory,
    AreaFactory,
)


# ===========================
# Actor Factory Tests
# ===========================

class TestPersonFactory:
    """Test PersonFactory creates valid Person instances."""

    def test_create_person(self, db):
        """Should create a valid person with all required fields."""
        person = PersonFactory()

        assert isinstance(person, Person)
        assert person.id is not None
        assert person.name
        assert person.family_name
        assert person.given_name
        assert person.name == f"{person.given_name} {person.family_name}"

    def test_create_person_with_override(self, db):
        """Should allow overriding factory attributes."""
        person = PersonFactory(
            given_name="Boris",
            family_name="Johnson",
            honorific_suffix="MP"
        )

        assert person.given_name == "Boris"
        assert person.family_name == "Johnson"
        assert person.name == "Boris Johnson"
        assert person.honorific_suffix == "MP"

    def test_create_mp(self, db):
        """Should create an MP with MP suffix."""
        mp = MPFactory()

        assert isinstance(mp, Person)
        assert mp.honorific_suffix == "MP"

    def test_create_batch_persons(self, db):
        """Should create multiple persons in batch."""
        persons = PersonFactory.create_batch(10)

        assert len(persons) == 10
        assert all(isinstance(p, Person) for p in persons)
        # Names should be unique (Faker generates random names)
        names = [p.name for p in persons]
        assert len(set(names)) == 10  # All unique


class TestOrganizationFactory:
    """Test OrganizationFactory creates valid Organization instances."""

    def test_create_organization(self, db):
        """Should create a valid organization."""
        org = OrganizationFactory()

        assert isinstance(org, Organization)
        assert org.id is not None
        assert org.name
        assert org.classification

    def test_create_political_party(self, db):
        """Should create a political party organization."""
        party = PoliticalPartyFactory()

        assert isinstance(party, Organization)
        assert party.classification == "Political Party"
        assert party.name in [
            'Labour Party',
            'Conservative Party',
            'Liberal Democrats',
            'Green Party',
            'Scottish National Party',
            'Plaid Cymru',
            'Democratic Unionist Party',
            'Sinn Féin',
        ]

    def test_create_company(self, db):
        """Should create a company organization."""
        company = CompanyFactory()

        assert isinstance(company, Organization)
        assert company.classification == "Company"

    def test_create_trade_union(self, db):
        """Should create a trade union organization."""
        union = TradeUnionFactory()

        assert isinstance(union, Organization)
        assert union.classification == "Trade Union"

    def test_organization_with_parent(self, db):
        """Should create organization with parent relationship."""
        parent = OrganizationFactory()
        child = OrganizationFactory(parent=parent)

        assert child.parent == parent
        assert parent.children.count() == 1
        assert child in parent.children.all()


# ===========================
# Relationship Factory Tests
# ===========================

class TestDonationFactory:
    """Test DonationFactory creates valid Donation instances."""

    def test_create_donation(self, db):
        """Should create a valid donation."""
        donation = DonationFactory()

        assert isinstance(donation, Donation)
        assert donation.id is not None
        assert donation.donor is not None
        assert donation.recipient is not None
        assert donation.value > 0
        assert donation.donation_type
        assert donation.received_date

    def test_create_cash_donation(self, db):
        """Should create a cash donation."""
        donation = CashDonationFactory()

        assert donation.donation_type == 'Cash'
        assert donation.nature_of_donation == 'Cash'

    def test_create_large_donation(self, db):
        """Should create a large donation (£50k+)."""
        donation = LargeDonationFactory()

        assert donation.value >= Decimal('50000.00')

    def test_donation_with_specific_actors(self, db):
        """Should create donation with specific donor and recipient."""
        company = CompanyFactory(name="Acme Corp")
        party = PoliticalPartyFactory(name="Labour Party")

        donation = DonationFactory(donor=company, recipient=party)

        assert donation.donor.name == "Acme Corp"
        assert donation.recipient.name == "Labour Party"
        assert donation.donor.classification == "Company"
        assert donation.recipient.classification == "Political Party"

    def test_donation_effective_properties(self, db):
        """Should use effective_donor/recipient for entity resolution."""
        donor = CompanyFactory(name="Original Donor")
        canonical_donor = CompanyFactory(name="Canonical Donor")
        recipient = PoliticalPartyFactory()

        donation = DonationFactory(
            donor=donor,
            recipient=recipient,
            canonical_donor=canonical_donor
        )

        # Original preserved
        assert donation.donor.name == "Original Donor"
        # Canonical resolution works
        assert donation.canonical_donor.name == "Canonical Donor"
        assert donation.effective_donor.name == "Canonical Donor"

    def test_create_batch_donations(self, db):
        """Should create multiple donations in batch."""
        donations = DonationFactory.create_batch(20)

        assert len(donations) == 20
        assert all(isinstance(d, Donation) for d in donations)


class TestConsultancyFactory:
    """Test ConsultancyFactory creates valid Consultancy instances."""

    def test_create_consultancy(self, db):
        """Should create a valid consultancy relationship."""
        consultancy = ConsultancyFactory()

        assert isinstance(consultancy, Consultancy)
        assert consultancy.id is not None
        assert consultancy.client is not None
        assert consultancy.agency is not None
        assert consultancy.start_date

    def test_consultancy_with_specific_actors(self, db):
        """Should create consultancy with specific client and agency."""
        client = CompanyFactory(name="Client Corp")
        agency = ConsultancyFirmFactory(name="Lobby Firm Ltd")

        consultancy = ConsultancyFactory(client=client, agency=agency)

        assert consultancy.client.name == "Client Corp"
        assert consultancy.agency.name == "Lobby Firm Ltd"

    def test_ongoing_consultancy(self, db):
        """Should create ongoing consultancy with no end date."""
        from tests.factories.relationship_factories import OngoingConsultancyFactory

        consultancy = OngoingConsultancyFactory()

        assert consultancy.start_date is not None
        assert consultancy.end_date is None

    def test_completed_consultancy(self, db):
        """Should create completed consultancy with end date."""
        from tests.factories.relationship_factories import CompletedConsultancyFactory

        consultancy = CompletedConsultancyFactory()

        assert consultancy.start_date is not None
        assert consultancy.end_date is not None
        assert consultancy.end_date > consultancy.start_date


# ===========================
# Membership Factory Tests
# ===========================

class TestMembershipFactory:
    """Test MembershipFactory creates valid Membership instances."""

    def test_create_membership(self, db):
        """Should create a valid membership."""
        membership = MembershipFactory()

        assert isinstance(membership, Membership)
        assert membership.id is not None
        assert membership.person is not None
        assert membership.organization is not None
        assert membership.start_date

    def test_create_mp_membership(self, db):
        """Should create MP membership with post."""
        membership = MPMembershipFactory()

        assert isinstance(membership, Membership)
        assert membership.person.honorific_suffix == "MP"
        assert membership.post is not None
        assert membership.post.role == "Member of Parliament"
        assert membership.area is not None
        assert membership.organization.name == "House of Commons"

    def test_create_party_membership(self, db):
        """Should create party membership."""
        person = PersonFactory()
        party = PoliticalPartyFactory(name="Labour Party")

        membership = PartyMembershipFactory(person=person, party=party)

        assert isinstance(membership, PartyMembership)
        assert membership.person == person
        assert membership.party == party
        assert membership.party.classification == "Political Party"

    def test_membership_with_post(self, db):
        """Should create membership with specific post."""
        person = PersonFactory()
        organization = OrganizationFactory()
        post = PostFactory(organization=organization, label="Director")

        membership = MembershipFactory(
            person=person,
            organization=organization,
            post=post,
            role="Director"
        )

        assert membership.person == person
        assert membership.organization == organization
        assert membership.post == post
        assert membership.post.label == "Director"


# ===========================
# Integration Tests
# ===========================

class TestFactoryIntegration:
    """Test factories working together for complex scenarios."""

    def test_create_mp_with_donations(self, db):
        """Should create an MP who receives donations."""
        # Create an MP
        mp = MPFactory(
            given_name="Sarah",
            family_name="Brown"
        )

        # Create donors
        company = CompanyFactory(name="Donor Corp")
        union = TradeUnionFactory(name="Unite the Union")

        # Create donations to the MP
        donation1 = DonationFactory(donor=company, recipient=mp, value=Decimal('5000.00'))
        donation2 = DonationFactory(donor=union, recipient=mp, value=Decimal('10000.00'))

        # Verify relationships
        assert mp.received_donations_from.count() == 2
        total_received = sum(d.value for d in mp.received_donations_from.all())
        assert total_received == Decimal('15000.00')

    def test_create_party_with_donors(self, db):
        """Should create a party that receives multiple donations."""
        party = PoliticalPartyFactory(name="Labour Party")

        # Create 10 random donors
        donors = [
            CompanyFactory() if i % 2 == 0 else PersonFactory()
            for i in range(10)
        ]

        # Create donations from each donor
        donations = [
            DonationFactory(donor=donor, recipient=party)
            for donor in donors
        ]

        # Verify
        assert party.received_donations_from.count() == 10
        assert len(donations) == 10

    def test_create_dual_influence_organization(self, db):
        """Should create organization that both donates AND lobbies."""
        # Organization that both donates and uses lobbying services
        corp = CompanyFactory(name="Dual Influence Corp")
        party = PoliticalPartyFactory()
        lobby_firm = ConsultancyFirmFactory()

        # Donate to party
        donation = DonationFactory(donor=corp, recipient=party, value=Decimal('50000.00'))

        # Hire lobbying firm
        consultancy = ConsultancyFactory(client=corp, agency=lobby_firm)

        # Verify dual influence
        assert corp.donated_to.count() == 1
        assert corp.consulting_agencies.count() == 1
        assert donation.donor == corp
        assert consultancy.client == corp

    def test_create_mp_with_party_timeline(self, db):
        """Should create MP with historical party memberships."""
        mp = MPFactory(given_name="Jane", family_name="Smith")

        # Historical party membership (changed parties)
        from tests.factories.membership_factories import (
            HistoricalPartyMembershipFactory,
            CurrentPartyMembershipFactory
        )

        # Was in Conservative Party 2010-2019
        old_party = PoliticalPartyFactory(name="Conservative Party")
        old_membership = HistoricalPartyMembershipFactory(
            person=mp,
            party=old_party,
            start_date='2010-05-06',
            end_date='2019-12-11'
        )

        # Now in Labour Party 2019-present
        new_party = PoliticalPartyFactory(name="Labour Party")
        current_membership = CurrentPartyMembershipFactory(
            person=mp,
            party=new_party,
            start_date='2019-12-12',
            end_date=None
        )

        # Verify timeline
        assert mp.party_memberships.count() == 2

        # Test temporal queries (at_date parameter from Phase 3.2)
        # On 2015-01-01, should be in Conservative Party
        memberships_2015 = mp.party_memberships.filter(
            start_date__lte='2015-01-01',
            end_date__gte='2015-01-01'
        )
        assert memberships_2015.count() == 1
        assert memberships_2015.first().party.name == "Conservative Party"

        # On 2024-01-01, should be in Labour Party
        memberships_2024 = mp.party_memberships.filter(
            start_date__lte='2024-01-01'
        ).filter(
            models.Q(end_date__gte='2024-01-01') | models.Q(end_date__isnull=True)
        )
        assert memberships_2024.count() == 1
        assert memberships_2024.first().party.name == "Labour Party"


# ===========================
# Utility Tests
# ===========================

class TestFactoryUtilities:
    """Test factory utility features."""

    def test_build_without_saving(self, db):
        """Should build instance without saving to database."""
        person = PersonFactory.build()

        assert isinstance(person, Person)
        assert person.id is None  # Not saved
        assert person.name

    def test_stub_for_attributes_only(self):
        """Should create stub with attributes but no database interaction."""
        person = PersonFactory.stub()

        assert person.name
        assert person.family_name
        assert person.given_name
        # Stub has no database methods
        assert not hasattr(person, 'save')

    def test_create_with_sequence(self, db):
        """Should create instances with sequential attributes."""
        persons = PersonFactory.create_batch(
            3,
            given_name=factory.Sequence(lambda n: f'Person{n}')
        )

        # Sequences should be sequential (not checking exact values as sequence is global)
        given_names = [p.given_name for p in persons]
        assert all(name.startswith('Person') for name in given_names)
        # All should be unique
        assert len(set(given_names)) == 3
        # Extract numbers and verify they're sequential
        numbers = [int(name.replace('Person', '')) for name in given_names]
        assert numbers[1] == numbers[0] + 1
        assert numbers[2] == numbers[1] + 1


# Import for temporal query test
from django.db import models
import factory
