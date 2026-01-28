"""
Pytest configuration and fixtures for datafetch tests.
"""

import pytest
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType


@pytest.fixture
def person_factory(db):
    """Factory for creating Person objects."""
    from datafetch.models import Person

    def _create_person(name="Test Person", **kwargs):
        defaults = {
            'family_name': name.split()[-1] if ' ' in name else name,
            'given_name': name.split()[0] if ' ' in name else '',
        }
        defaults.update(kwargs)
        return Person.objects.create(name=name, **defaults)

    return _create_person


@pytest.fixture
def organization_factory(db):
    """Factory for creating Organization objects."""
    from datafetch.models import Organization

    def _create_org(name="Test Organization", classification="Company", **kwargs):
        return Organization.objects.create(
            name=name,
            classification=classification,
            **kwargs
        )

    return _create_org


@pytest.fixture
def donation_factory(db, organization_factory):
    """Factory for creating Donation objects."""
    from datafetch.models import Donation

    def _create_donation(
        donor=None,
        recipient=None,
        value=1000,
        donation_type="Cash",
        **kwargs
    ):
        if donor is None:
            donor = organization_factory(name="Donor Corp")
        if recipient is None:
            recipient = organization_factory(
                name="Political Party",
                classification="Political Party"
            )

        defaults = {
            'value': Decimal(str(value)),
            'donation_type': donation_type,
            'accounting_units_as_central_party': False,
            'is_bequest': False,
            'is_aggregation': False,
            'is_sponsorship': False,
        }
        defaults.update(kwargs)

        return Donation.objects.create(donor=donor, recipient=recipient, **defaults)

    return _create_donation


@pytest.fixture
def meeting_factory(db, person_factory, organization_factory):
    """Factory for creating MinisterialMeeting objects."""
    from datafetch.models import MinisterialMeeting

    def _create_meeting(
        minister=None,
        department=None,
        meeting_date="2024-01-15",
        purpose="Test meeting",
        organisation_met_raw="Test Organization",
        **kwargs
    ):
        if minister is None:
            minister = person_factory(name="John Smith MP")
        if department is None:
            department = organization_factory(
                name="Department for Testing",
                classification="Government Department"
            )

        return MinisterialMeeting.objects.create(
            minister=minister,
            department=department,
            meeting_date=meeting_date,
            purpose=purpose,
            organisation_met_raw=organisation_met_raw,
            **kwargs
        )

    return _create_meeting


@pytest.fixture
def attendee_factory(db, organization_factory, meeting_factory):
    """Factory for creating MeetingAttendee objects."""
    from datafetch.models import MeetingAttendee

    def _create_attendee(
        meeting=None,
        actor=None,
        actor_name_raw=None,
        **kwargs
    ):
        if meeting is None:
            meeting = meeting_factory()
        if actor is None:
            actor = organization_factory(name="Attendee Org")
        if actor_name_raw is None:
            actor_name_raw = actor.name

        return MeetingAttendee.objects.create(
            meeting=meeting,
            actor=actor,
            actor_name_raw=actor_name_raw,
            **kwargs
        )

    return _create_attendee
