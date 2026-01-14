"""
Pytest configuration and shared fixtures for UnderTheInfluence test suite.

This module provides:
- Django test database configuration
- Common fixtures for models (Actor, Person, Organization, Donation, etc.)
- Factory fixtures using factory_boy
- API client fixtures
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


# ===========================
# Database Configuration
# ===========================

@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Custom database setup for tests.
    Uses the default Django test database configuration.
    """
    pass


@pytest.fixture
def db_access(db):
    """
    Fixture that provides database access.
    Use this instead of @pytest.mark.django_db for better readability.
    """
    return db


# ===========================
# User Fixtures
# ===========================

@pytest.fixture
def user(db):
    """Create a regular user for testing."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def superuser(db):
    """Create a superuser for admin testing."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass123",
    )


# ===========================
# API Client Fixtures
# ===========================

@pytest.fixture
def api_client():
    """Provide an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def authenticated_api_client(user):
    """Provide an API client authenticated as a regular user."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_api_client(superuser):
    """Provide an API client authenticated as a superuser."""
    client = APIClient()
    client.force_authenticate(user=superuser)
    return client


# ===========================
# Actor Model Fixtures
# ===========================

@pytest.fixture
def person(db):
    """Create a sample Person instance."""
    from datafetch.models import Person

    return Person.objects.create(
        name="John Smith",
        family_name="Smith",
        given_name="John",
        sort_name="Smith, John",
    )


@pytest.fixture
def organization(db):
    """Create a sample Organization instance."""
    from datafetch.models import Organization

    return Organization.objects.create(
        name="Test Organization Ltd",
        classification="Company",
    )


@pytest.fixture
def political_party(db):
    """Create a sample Political Party organization."""
    from datafetch.models import Organization

    return Organization.objects.create(
        name="Test Party",
        classification="Political Party",
    )


# ===========================
# Donation Fixtures
# ===========================

@pytest.fixture
def donation(db, person, organization):
    """Create a sample Donation from organization to person."""
    from datafetch.models import Donation

    return Donation.objects.create(
        donor=organization,
        recipient=person,
        value=10000.00,
        received_date="2024-01-15",
        donation_type="Cash",
        nature_of_donation="Donation",
        accounting_units_as_central_party=False,
        is_bequest=False,
        is_aggregation=False,
        is_sponsorship=False,
    )


# ===========================
# Membership Fixtures
# ===========================

@pytest.fixture
def membership(db, person, political_party):
    """Create a sample Membership linking person to party."""
    from datafetch.models import Membership

    return Membership.objects.create(
        person=person,
        organization=political_party,
        role="Member",
        start_date="2020-01-01",
    )


# ===========================
# Consultancy Fixtures
# ===========================

@pytest.fixture
def consultancy(db, organization):
    """Create a sample Consultancy/lobbying relationship."""
    from datafetch.models import Consultancy, Organization

    # Create a lobbying agency
    agency = Organization.objects.create(
        name="Lobbying Agency Ltd",
        classification="Consultancy",
    )

    return Consultancy.objects.create(
        client=organization,
        agency=agency,
        start_date="2024-01-01",
    )


# ===========================
# Utility Fixtures
# ===========================

@pytest.fixture
def sample_date():
    """Provide a consistent sample date for testing."""
    from datetime import date
    return date(2024, 1, 15)


@pytest.fixture
def date_range():
    """Provide a sample date range for filtering tests."""
    from datetime import date
    return {
        "start": date(2020, 1, 1),
        "end": date(2024, 12, 31),
    }
