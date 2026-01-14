"""
Factory fixtures for UnderTheInfluence models.

These factories use factory_boy to create realistic test data.
All factories use Faker for generating realistic names, dates, and values.
"""

from .actor_factories import (
    PersonFactory,
    MPFactory,
    OrganizationFactory,
    PoliticalPartyFactory,
    CompanyFactory,
    TradeUnionFactory,
    ConsultancyFirmFactory,
    AreaFactory,
)
from .relationship_factories import (
    DonationFactory,
    CashDonationFactory,
    VisitDonationFactory,
    LargeDonationFactory,
    SmallDonationFactory,
    ConsultancyFactory,
    OngoingConsultancyFactory,
    CompletedConsultancyFactory,
)
from .membership_factories import (
    PostFactory,
    MPPostFactory,
    MembershipFactory,
    MPMembershipFactory,
    PartyMembershipFactory,
    CurrentPartyMembershipFactory,
    HistoricalPartyMembershipFactory,
)

__all__ = [
    # Actors
    'PersonFactory',
    'MPFactory',
    'OrganizationFactory',
    'PoliticalPartyFactory',
    'CompanyFactory',
    'TradeUnionFactory',
    'ConsultancyFirmFactory',
    'AreaFactory',
    # Relationships
    'DonationFactory',
    'CashDonationFactory',
    'VisitDonationFactory',
    'LargeDonationFactory',
    'SmallDonationFactory',
    'ConsultancyFactory',
    'OngoingConsultancyFactory',
    'CompletedConsultancyFactory',
    # Memberships
    'PostFactory',
    'MPPostFactory',
    'MembershipFactory',
    'MPMembershipFactory',
    'PartyMembershipFactory',
    'CurrentPartyMembershipFactory',
    'HistoricalPartyMembershipFactory',
]
