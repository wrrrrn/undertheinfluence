"""
Factories for membership models (Post, Membership, PartyMembership).
"""

import factory
from factory import fuzzy
import datetime
import random

from datafetch.models import Post, Membership
from datafetch.models.influence_mapping import PartyMembership

from .actor_factories import (
    PersonFactory,
    MPFactory,
    OrganizationFactory,
    PoliticalPartyFactory,
    AreaFactory,
)


class PostFactory(factory.django.DjangoModelFactory):
    """
    Factory for Post (positions/roles that exist independently of people).

    Examples: "MP for Bristol West", "Leader of the Opposition", "Minister for Education"
    """
    class Meta:
        model = Post

    label = factory.Faker('job')
    other_label = ""
    role = factory.LazyAttribute(lambda obj: obj.label)

    # Post belongs to an organization
    organization = factory.SubFactory(OrganizationFactory)

    # Geographic area (optional)
    area = None

    # Dateframeable fields
    start_date = None
    end_date = None


class MPPostFactory(PostFactory):
    """
    Factory for MP constituency posts.

    Creates posts like "MP for Bristol West".
    """
    area = factory.SubFactory(AreaFactory, classification='constituency')
    label = factory.LazyAttribute(
        lambda obj: f"Member of Parliament for {obj.area.name}"
    )
    role = "Member of Parliament"

    # MPs are typically in House of Commons
    organization = factory.SubFactory(
        OrganizationFactory,
        name="House of Commons",
        classification="chamber"
    )


class MembershipFactory(factory.django.DjangoModelFactory):
    """
    Factory for Membership (person ↔ organization relationships).

    Creates relationships like "John Smith is a member of Labour Party"
    or "Jane Doe is MP for Bristol West".

    By default, creates a simple membership without a specific post.
    Use MPMembershipFactory for MP posts.
    """
    class Meta:
        model = Membership

    # Who and where
    person = factory.SubFactory(PersonFactory)
    organization = factory.SubFactory(OrganizationFactory)

    # Optional: specific post within the organization
    post = None

    # Optional: on behalf of another organization
    on_behalf_of = None

    # Optional: geographic area
    area = None

    # Membership details
    label = ""
    role = factory.Iterator([
        'Member',
        'Director',
        'Trustee',
        'Secretary',
        'Treasurer',
        'Chair',
    ])

    # Dateframeable fields - most memberships are ongoing
    start_date = factory.LazyFunction(
        lambda: fuzzy.FuzzyDate(
            datetime.date(2000, 1, 1),
            datetime.date(2025, 12, 31)
        ).fuzz().strftime('%Y-%m-%d')
    )

    # 80% of memberships are ongoing (no end date)
    # 20% chance of having an end date
    @factory.lazy_attribute
    def end_date(obj):
        if random.random() < 0.20:
            # Has end date - 1-10 years after start
            start = datetime.datetime.strptime(obj.start_date, '%Y-%m-%d').date()
            days = fuzzy.FuzzyInteger(365, 3650).fuzz()
            end = start + datetime.timedelta(days=days)
            return end.strftime('%Y-%m-%d')
        return None


class MPMembershipFactory(MembershipFactory):
    """
    Factory for MP memberships.

    Creates a person as MP for a constituency with proper Post relationship.
    """
    person = factory.SubFactory(MPFactory)
    post = factory.SubFactory(MPPostFactory)
    organization = factory.LazyAttribute(lambda obj: obj.post.organization)
    area = factory.LazyAttribute(lambda obj: obj.post.area)
    role = "Member of Parliament"
    label = factory.LazyAttribute(
        lambda obj: f"MP for {obj.area.name if obj.area else 'Unknown'}"
    )


class PartyMembershipFactory(factory.django.DjangoModelFactory):
    """
    Factory for PartyMembership (person ↔ political party).

    Creates party affiliation memberships used for temporal party queries.
    PartyMembership is a separate model (not a proxy) with person/party fields.
    """
    class Meta:
        model = PartyMembership

    person = factory.SubFactory(PersonFactory)
    party = factory.SubFactory(PoliticalPartyFactory)
    role = "Member"

    # Party memberships often align with parliamentary terms
    start_date = factory.Iterator([
        '2010-05-06',  # 2010 election
        '2015-05-07',  # 2015 election
        '2017-06-08',  # 2017 election
        '2019-12-12',  # 2019 election
        '2024-07-04',  # 2024 election
    ])
    end_date = None


class CurrentPartyMembershipFactory(PartyMembershipFactory):
    """
    Factory for current (ongoing) party memberships.

    No end date - person is currently in this party.
    """
    start_date = '2024-07-04'  # Latest election
    end_date = None


class HistoricalPartyMembershipFactory(PartyMembershipFactory):
    """
    Factory for historical party memberships.

    Has both start and end dates - person was in this party previously.
    """
    start_date = factory.Iterator([
        '2010-05-06',
        '2015-05-07',
        '2017-06-08',
    ])

    end_date = factory.LazyAttribute(
        lambda obj: (
            datetime.datetime.strptime(obj.start_date, '%Y-%m-%d').date() +
            datetime.timedelta(days=fuzzy.FuzzyInteger(365, 1826).fuzz())  # 1-5 years
        ).strftime('%Y-%m-%d')
    )
