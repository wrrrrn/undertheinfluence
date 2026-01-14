"""
Factories for relationship models (Donation, Consultancy).
"""

import factory
from factory import fuzzy
from decimal import Decimal
import datetime
import random

from datafetch.models import Donation, Consultancy

from .actor_factories import (
    PersonFactory,
    OrganizationFactory,
    PoliticalPartyFactory,
    CompanyFactory,
    ConsultancyFirmFactory,
)


class DonationFactory(factory.django.DjangoModelFactory):
    """
    Factory for Donation relationships.

    Creates realistic political donations from individuals/companies to politicians/parties.

    By default, creates a donation from a Company to a Political Party.
    Override donor/recipient as needed:
        DonationFactory(donor=person, recipient=mp)
    """
    class Meta:
        model = Donation

    # Actors - default to organization → party
    donor = factory.SubFactory(CompanyFactory)
    recipient = factory.SubFactory(PoliticalPartyFactory)

    # Canonical fields (entity resolution) - initially None
    canonical_donor = None
    canonical_recipient = None

    # Monetary value
    value = factory.Faker(
        'pydecimal',
        left_digits=6,
        right_digits=2,
        positive=True,
        min_value=Decimal('100.00'),
        max_value=Decimal('500000.00')
    )

    # Donation type and nature
    donation_type = factory.Iterator(['Cash', 'Non Cash', 'Visit'])
    nature_of_donation = factory.Iterator([
        'Cash',
        'Travel',
        'Sponsorship',
        'Hospitality',
        'Consultancy services',
        'Other',
    ])

    # Dates
    received_date = factory.Faker(
        'date_between',
        start_date=datetime.date(2010, 1, 1),
        end_date=datetime.date(2025, 12, 31)
    )
    accepted_date = factory.LazyAttribute(
        lambda obj: obj.received_date
    )
    reported_date = factory.LazyAttribute(
        lambda obj: obj.received_date + datetime.timedelta(days=30)
    )

    # Accounting details
    accounting_unit_name = ''
    accounting_units_as_central_party = False

    # Additional fields
    purpose_of_visit = ''
    is_bequest = False
    is_aggregation = False
    is_sponsorship = False

    # Relationship base class fields
    label = factory.LazyAttribute(
        lambda obj: f"Donation from {obj.donor.name} to {obj.recipient.name}"
    )
    source = factory.Faker('url')

    # Note: Donation model doesn't use start_date/end_date
    # It has a start_date() method that returns accepted_date


class CashDonationFactory(DonationFactory):
    """
    Factory for cash donations.

    Most common donation type.
    """
    donation_type = 'Cash'
    nature_of_donation = 'Cash'


class VisitDonationFactory(DonationFactory):
    """
    Factory for visit donations (sponsored trips).
    """
    donation_type = 'Visit'
    nature_of_donation = 'Travel'
    purpose_of_visit = factory.Faker('sentence', nb_words=8)


class LargeDonationFactory(DonationFactory):
    """
    Factory for large donations (£50k+).

    Used for testing whale donor scenarios.
    """
    value = factory.Faker(
        'pydecimal',
        left_digits=7,  # Need 7 digits for max value 9,999,999.99
        right_digits=2,
        positive=True,
        min_value=Decimal('50000.00'),
        max_value=Decimal('999999.99')  # Reduced to fit left_digits constraint
    )


class SmallDonationFactory(DonationFactory):
    """
    Factory for small donations (<£1k).
    """
    value = factory.Faker(
        'pydecimal',
        left_digits=3,
        right_digits=2,
        positive=True,
        min_value=Decimal('10.00'),
        max_value=Decimal('999.99')
    )


class ConsultancyFactory(factory.django.DjangoModelFactory):
    """
    Factory for Consultancy relationships.

    Creates lobbying relationships between clients and consultancy firms.

    By default, creates a relationship: Company ←→ Consultancy Firm.
    """
    class Meta:
        model = Consultancy

    # Actors
    client = factory.SubFactory(CompanyFactory)
    agency = factory.SubFactory(ConsultancyFirmFactory)

    # Canonical fields (entity resolution) - initially None
    canonical_client = None
    canonical_agency = None

    # Relationship base class fields
    label = factory.LazyAttribute(
        lambda obj: f"{obj.client.name} ↔ {obj.agency.name}"
    )
    source = factory.Faker('url')

    # Dateframeable fields
    start_date = factory.LazyFunction(
        lambda: fuzzy.FuzzyDate(
            datetime.date(2010, 1, 1),
            datetime.date(2025, 12, 31)
        ).fuzz().strftime('%Y-%m-%d')
    )

    # 70% of consultancies are ongoing (no end date)
    # 30% chance of having an end date
    @factory.lazy_attribute
    def end_date(obj):
        if random.random() < 0.30:
            # Has end date - 1 year after start
            start = datetime.datetime.strptime(obj.start_date, '%Y-%m-%d').date()
            end = start + datetime.timedelta(days=365)
            return end.strftime('%Y-%m-%d')
        return None


class OngoingConsultancyFactory(ConsultancyFactory):
    """
    Factory for ongoing (current) consultancies.

    No end date.
    """
    end_date = None


class CompletedConsultancyFactory(ConsultancyFactory):
    """
    Factory for completed consultancies.

    Has both start and end dates.
    """
    end_date = factory.LazyAttribute(
        lambda obj: (
            datetime.datetime.strptime(obj.start_date, '%Y-%m-%d').date() +
            datetime.timedelta(days=fuzzy.FuzzyInteger(30, 730).fuzz())
        ).strftime('%Y-%m-%d')
    )
