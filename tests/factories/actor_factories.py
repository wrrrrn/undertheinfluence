"""
Factories for Actor models (Person, Organization, Area).
"""

import factory
from factory import fuzzy
from faker import Faker

from datafetch.models import Person, Organization, Area

fake = Faker('en_GB')  # British English for realistic UK data


class AreaFactory(factory.django.DjangoModelFactory):
    """
    Factory for Area (geographic regions).

    Creates areas like constituencies, counties, regions.
    """
    class Meta:
        model = Area

    name = factory.Faker('city')
    identifier = factory.Sequence(lambda n: f'area-{n:05d}')
    classification = factory.Iterator(['constituency', 'county', 'region', 'country'])

    # Dateframeable fields (optional)
    start_date = None
    end_date = None


class PersonFactory(factory.django.DjangoModelFactory):
    """
    Factory for Person actors.

    Creates realistic British politicians and individuals with proper name structure.
    Uses Faker for names but ensures family_name and given_name match the full name.
    """
    class Meta:
        model = Person

    # Core name fields - must be consistent
    family_name = factory.Faker('last_name')
    given_name = factory.Faker('first_name')

    # Full name composed from parts
    name = factory.LazyAttribute(
        lambda obj: f"{obj.given_name} {obj.family_name}"
    )

    # Optional name fields
    additional_name = ""
    honorific_prefix = factory.Iterator(['', 'Mr', 'Ms', 'Mrs', 'Dr', 'Sir', 'Dame', 'Rt Hon'])
    honorific_suffix = factory.Iterator(['', 'MP', 'OBE', 'CBE', 'QC'])
    patronymic_name = ""
    sort_name = factory.LazyAttribute(
        lambda obj: f"{obj.family_name}, {obj.given_name}"
    )

    # Contact information
    email = factory.LazyAttribute(
        lambda obj: f"{obj.given_name.lower()}.{obj.family_name.lower()}@example.com"
    )

    # Demographic information
    gender = factory.Iterator(['male', 'female', 'non-binary', ''])
    birth_date = factory.Faker('date_of_birth', minimum_age=25, maximum_age=85)
    death_date = ''  # Empty string, not None (database has NOT NULL constraint)

    # Biography
    summary = factory.Faker('sentence', nb_words=10)
    biography = factory.Faker('paragraph', nb_sentences=5)
    national_identity = 'British'

    # Image (optional)
    image = None

    # Dateframeable fields
    start_date = None
    end_date = None


class MPFactory(PersonFactory):
    """
    Factory for Members of Parliament (MPs).

    Creates persons with MP-specific attributes.
    """
    honorific_suffix = 'MP'
    summary = factory.LazyAttribute(
        lambda obj: f"Member of Parliament"
    )


class OrganizationFactory(factory.django.DjangoModelFactory):
    """
    Factory for Organization actors.

    Creates companies, political parties, charities, etc.
    """
    class Meta:
        model = Organization

    name = factory.Faker('company')

    # Organization-specific fields
    classification = factory.Iterator([
        'Company',
        'Political Party',
        'Trade Union',
        'Charity',
        'Lobby Group',
        'Consultancy',
        'chamber',  # House of Commons/Lords
    ])

    summary = factory.Faker('catch_phrase')
    description = factory.Faker('paragraph', nb_sentences=3)

    # Hierarchical relationships
    parent = None  # Can be set via SubFactory if needed
    area = None    # Can be set via SubFactory(AreaFactory)

    # Dates (partial dates supported: YYYY, YYYY-MM, YYYY-MM-DD)
    founding_date = factory.Faker('date', pattern='%Y-%m-%d')
    dissolution_date = None

    # Dateframeable fields
    start_date = None
    end_date = None

    # Image
    image = None


class PoliticalPartyFactory(OrganizationFactory):
    """
    Factory for Political Party organizations.

    Creates major UK political parties.
    """
    classification = 'Political Party'

    name = factory.Iterator([
        'Labour Party',
        'Conservative Party',
        'Liberal Democrats',
        'Green Party',
        'Scottish National Party',
        'Plaid Cymru',
        'Democratic Unionist Party',
        'Sinn Féin',
    ])


class CompanyFactory(OrganizationFactory):
    """
    Factory for Company organizations.
    """
    classification = 'Company'
    name = factory.Faker('company')


class TradeUnionFactory(OrganizationFactory):
    """
    Factory for Trade Union organizations.
    """
    classification = 'Trade Union'

    name = factory.Iterator([
        'Unite the Union',
        'UNISON',
        'GMB',
        'USDAW',
        'National Education Union',
        'Royal College of Nursing',
    ])


class ConsultancyFirmFactory(OrganizationFactory):
    """
    Factory for lobbying/consultancy firms.
    """
    classification = 'Consultancy'
    name = factory.Faker('company')
    summary = factory.LazyAttribute(
        lambda obj: f"{obj.name} - Public Affairs and Government Relations"
    )
