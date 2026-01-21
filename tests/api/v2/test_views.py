"""
Tests for API v2 endpoints.

Tests cover:
- Aggregate endpoints (top-donors, top-recipients, network-stats)
- Filtering by date ranges, value brackets, actor types
- Pagination with custom limits
- Edge cases (null values, empty results)
- Response structure and data accuracy
- Regression tests for bugs caught in manual testing

TESTING STRATEGY:
-----------------
These tests use DRF's APIClient, which simulates the full HTTP request/response
cycle including all middleware, authentication, and serialization.

IMPORTANT: If manual testing catches a bug that tests didn't catch, add a
regression test to the TestRegressions class. Tests must reflect the actual
application behavior, not just the happy path.

Running tests:
    docker compose exec web pytest tests/api/v2/test_views.py -v

After code changes, ALWAYS:
1. Run tests
2. Restart web service: docker compose restart web
3. Manually test endpoints
4. If manual testing finds bugs, add regression tests BEFORE fixing
"""

import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status

from datafetch.models import Person, Organization, Donation, Consultancy


# ===========================
# Test Data Fixtures
# ===========================

@pytest.fixture
def rich_donation_dataset(db):
    """Create a rich dataset of donations for testing aggregates."""
    # Create donors
    person_donor1 = Person.objects.create(
        name="Alice Johnson",
        family_name="Johnson",
        given_name="Alice",
    )
    person_donor2 = Person.objects.create(
        name="Bob Williams",
        family_name="Williams",
        given_name="Bob",
    )
    org_donor1 = Organization.objects.create(
        name="Acme Corporation",
        classification="Company",
    )
    org_donor2 = Organization.objects.create(
        name="Big Tech Inc",
        classification="Company",
    )

    # Create recipients
    mp1 = Person.objects.create(
        name="Sarah Brown MP",
        family_name="Brown",
        given_name="Sarah",
    )
    mp2 = Person.objects.create(
        name="David Green MP",
        family_name="Green",
        given_name="David",
    )
    party = Organization.objects.create(
        name="Test Party",
        classification="Political Party",
    )

    # Create donations with varying dates and values
    donations = [
        # Large donor: Acme Corporation (total: 75,000)
        Donation.objects.create(
            donor=org_donor1, recipient=mp1, value=50000.00,
            received_date="2023-01-15", donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False, is_aggregation=False, is_sponsorship=False,
        ),
        Donation.objects.create(
            donor=org_donor1, recipient=party, value=25000.00,
            received_date="2023-06-20", donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False, is_aggregation=False, is_sponsorship=False,
        ),

        # Medium donor: Big Tech Inc (total: 40,000)
        Donation.objects.create(
            donor=org_donor2, recipient=mp2, value=40000.00,
            received_date="2024-01-10", donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False, is_aggregation=False, is_sponsorship=False,
        ),

        # Small donor: Alice Johnson (total: 15,000)
        Donation.objects.create(
            donor=person_donor1, recipient=party, value=10000.00,
            received_date="2023-03-01", donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False, is_aggregation=False, is_sponsorship=False,
        ),
        Donation.objects.create(
            donor=person_donor1, recipient=mp1, value=5000.00,
            received_date="2024-02-15", donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False, is_aggregation=False, is_sponsorship=False,
        ),

        # Minimal donor: Bob Williams (total: 2,000)
        Donation.objects.create(
            donor=person_donor2, recipient=mp2, value=2000.00,
            received_date="2023-12-01", donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False, is_aggregation=False, is_sponsorship=False,
        ),
    ]

    return {
        'donors': {
            'person_donor1': person_donor1,
            'person_donor2': person_donor2,
            'org_donor1': org_donor1,
            'org_donor2': org_donor2,
        },
        'recipients': {
            'mp1': mp1,
            'mp2': mp2,
            'party': party,
        },
        'donations': donations,
    }


@pytest.fixture
def consultancy_dataset(db):
    """Create consultancy relationships for network stats."""
    agency1 = Organization.objects.create(
        name="Lobbying Agency A",
        classification="Consultancy",
    )
    agency2 = Organization.objects.create(
        name="Lobbying Agency B",
        classification="Consultancy",
    )
    client1 = Organization.objects.create(
        name="Client Corp",
        classification="Company",
    )
    client2 = Organization.objects.create(
        name="Another Client Ltd",
        classification="Company",
    )

    consultancies = [
        Consultancy.objects.create(
            agency=agency1, client=client1,
            start_date="2023-01-01", end_date="2023-12-31",
        ),
        Consultancy.objects.create(
            agency=agency2, client=client2,
            start_date="2024-01-01",
        ),
    ]

    return {
        'agencies': [agency1, agency2],
        'clients': [client1, client2],
        'consultancies': consultancies,
    }


@pytest.fixture
def dual_influence_dataset(db):
    """
    Create dataset for testing dual-influence detection.

    Organizations that both donate AND lobby (use consultancy agencies).
    """
    # Create lobbying agencies
    agency1 = Organization.objects.create(
        name="Top Lobbying Firm",
        classification="Consultancy",
    )

    # Create organizations that both donate and lobby
    dual_org1 = Organization.objects.create(
        name="Dual Corp",
        classification="Company",
    )
    dual_org2 = Organization.objects.create(
        name="Influential Ltd",
        classification="Company",
    )

    # Create organization that only donates (no lobbying)
    donor_only = Organization.objects.create(
        name="Donor Only Inc",
        classification="Company",
    )

    # Create organization that only lobbies (no donations)
    lobby_only = Organization.objects.create(
        name="Lobby Only Corp",
        classification="Company",
    )

    # Create recipients
    mp = Person.objects.create(
        name="MP Person",
        family_name="Person",
        given_name="MP",
    )
    party = Organization.objects.create(
        name="Major Party",
        classification="Political Party",
    )

    # Dual org #1: Donates AND lobbies
    Donation.objects.create(
        donor=dual_org1, recipient=mp, value=25000.00,
        received_date="2023-06-01", donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False, is_aggregation=False, is_sponsorship=False,
    )
    Donation.objects.create(
        donor=dual_org1, recipient=party, value=15000.00,
        received_date="2024-01-15", donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False, is_aggregation=False, is_sponsorship=False,
    )
    Consultancy.objects.create(
        agency=agency1, client=dual_org1,
        start_date="2023-01-01", end_date="2023-12-31",
    )
    Consultancy.objects.create(
        agency=agency1, client=dual_org1,
        start_date="2024-01-01",
    )

    # Dual org #2: Donates AND lobbies
    Donation.objects.create(
        donor=dual_org2, recipient=party, value=50000.00,
        received_date="2023-03-10", donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False, is_aggregation=False, is_sponsorship=False,
    )
    Consultancy.objects.create(
        agency=agency1, client=dual_org2,
        start_date="2023-02-01",
    )

    # Donor only: Donates but doesn't lobby
    Donation.objects.create(
        donor=donor_only, recipient=party, value=10000.00,
        received_date="2024-02-01", donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False, is_aggregation=False, is_sponsorship=False,
    )

    # Lobby only: Lobbies but doesn't donate
    Consultancy.objects.create(
        agency=agency1, client=lobby_only,
        start_date="2024-03-01",
    )

    return {
        'dual_orgs': [dual_org1, dual_org2],
        'donor_only': donor_only,
        'lobby_only': lobby_only,
        'agency': agency1,
        'recipients': [mp, party],
    }


@pytest.fixture
def enhanced_filter_dataset(db):
    """
    Create dataset for testing enhanced filter functionality.

    Includes Trade Unions, Companies, persons, and lobbying relationships.
    Used for testing donor_classification, exclude_donor_classification, and has_lobbying filters.
    """
    # Create lobbying agency
    agency = Organization.objects.create(
        name="Lobbying Agency",
        classification="Consultancy",
    )

    # Create Trade Union donors (some with lobbying)
    union1 = Organization.objects.create(
        name="Workers Union",
        classification="Trade Union",
    )
    union2 = Organization.objects.create(
        name="Teachers Union",
        classification="Trade Union",
    )
    union3 = Organization.objects.create(
        name="Transport Union",
        classification="Trade Union",
    )

    # Create Company donors (some with lobbying)
    company1 = Organization.objects.create(
        name="Tech Corp",
        classification="Company",
    )
    company2 = Organization.objects.create(
        name="Finance Ltd",
        classification="Company",
    )
    company3 = Organization.objects.create(
        name="Energy Inc",
        classification="Company",
    )

    # Create person donors
    person1 = Person.objects.create(
        name="John Smith",
        family_name="Smith",
        given_name="John",
    )
    person2 = Person.objects.create(
        name="Jane Doe",
        family_name="Doe",
        given_name="Jane",
    )

    # Create recipients
    mp = Person.objects.create(
        name="MP Recipient",
        family_name="Recipient",
        given_name="MP",
    )
    party = Organization.objects.create(
        name="Test Party",
        classification="Political Party",
    )

    # Create donations from Trade Unions
    Donation.objects.create(
        donor=union1, recipient=party, value=50000.00,
        received_date="2023-06-01", donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False, is_aggregation=False, is_sponsorship=False,
    )
    Donation.objects.create(
        donor=union2, recipient=mp, value=25000.00,
        received_date="2023-09-15", donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False, is_aggregation=False, is_sponsorship=False,
    )
    Donation.objects.create(
        donor=union3, recipient=party, value=15000.00,
        received_date="2024-01-20", donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False, is_aggregation=False, is_sponsorship=False,
    )

    # Create donations from Companies
    Donation.objects.create(
        donor=company1, recipient=party, value=75000.00,
        received_date="2023-05-10", donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False, is_aggregation=False, is_sponsorship=False,
    )
    Donation.objects.create(
        donor=company2, recipient=mp, value=40000.00,
        received_date="2023-11-01", donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False, is_aggregation=False, is_sponsorship=False,
    )
    Donation.objects.create(
        donor=company3, recipient=party, value=20000.00,
        received_date="2024-02-15", donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False, is_aggregation=False, is_sponsorship=False,
    )

    # Create donations from persons
    Donation.objects.create(
        donor=person1, recipient=party, value=8000.00,
        received_date="2023-08-01", donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False, is_aggregation=False, is_sponsorship=False,
    )
    Donation.objects.create(
        donor=person2, recipient=mp, value=12000.00,
        received_date="2024-03-01", donation_type="Cash",
        accounting_units_as_central_party=False,
        is_bequest=False, is_aggregation=False, is_sponsorship=False,
    )

    # Create lobbying relationships
    # union1 and company1 also lobby (dual influence)
    Consultancy.objects.create(
        agency=agency, client=union1,
        start_date="2023-01-01",
    )
    Consultancy.objects.create(
        agency=agency, client=company1,
        start_date="2023-01-01",
    )
    # union2 also lobbies
    Consultancy.objects.create(
        agency=agency, client=union2,
        start_date="2024-01-01",
    )

    # union3, company2, company3, person1, person2 do NOT lobby

    return {
        'unions': [union1, union2, union3],
        'companies': [company1, company2, company3],
        'persons': [person1, person2],
        'lobbying_clients': [union1, union2, company1],  # Actors with Consultancy records
        'non_lobbyists': [union3, company2, company3, person1, person2],
        'agency': agency,
        'recipients': [mp, party],
    }


# ===========================
# TopDonorsView Tests
# ===========================

class TestTopDonorsView:
    """Tests for /api/v2/aggregates/top-donors/ endpoint."""

    def test_basic_top_donors(self, api_client, rich_donation_dataset):
        """Should return donors ranked by total donation value."""
        url = reverse('api_v2:top-donors')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'count' in response.data

        # Should have 4 donors total
        assert response.data['count'] == 4

        # Check ordering (highest to lowest)
        results = response.data['results']
        assert len(results) >= 3

        # First donor should be Acme Corporation (75,000)
        assert results[0]['actor']['name'] == "Acme Corporation"
        assert Decimal(str(results[0]['total_donated'])) == Decimal('75000.00')
        assert results[0]['donation_count'] == 2

        # Second should be Big Tech Inc (40,000)
        assert results[1]['actor']['name'] == "Big Tech Inc"
        assert Decimal(str(results[1]['total_donated'])) == Decimal('40000.00')
        assert results[1]['donation_count'] == 1

        # Third should be Alice Johnson (15,000)
        assert results[2]['actor']['name'] == "Alice Johnson"
        assert Decimal(str(results[2]['total_donated'])) == Decimal('15000.00')
        assert results[2]['donation_count'] == 2

    def test_top_donors_pagination(self, api_client, rich_donation_dataset):
        """Should paginate results with limit parameter."""
        url = reverse('api_v2:top-donors')
        response = api_client.get(url, {'limit': 2})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
        assert response.data['count'] == 4

        # Should have next page
        assert response.data['next'] is not None

    def test_top_donors_filter_by_date(self, api_client, rich_donation_dataset):
        """Should filter donations by received_after date."""
        url = reverse('api_v2:top-donors')
        response = api_client.get(url, {'received_after': '2024-01-01'})

        assert response.status_code == status.HTTP_200_OK

        # Only donations from 2024 onwards
        # Big Tech Inc: 40,000 (2024-01-10)
        # Alice Johnson: 5,000 (2024-02-15)
        results = response.data['results']
        assert len(results) == 2
        assert results[0]['actor']['name'] == "Big Tech Inc"
        assert results[1]['actor']['name'] == "Alice Johnson"

    def test_top_donors_filter_by_date_range(self, api_client, rich_donation_dataset):
        """Should filter donations by date range."""
        url = reverse('api_v2:top-donors')
        response = api_client.get(url, {
            'received_after': '2023-01-01',
            'received_before': '2023-12-31',
        })

        assert response.status_code == status.HTTP_200_OK

        # Only 2023 donations
        # Acme: 75,000 (both in 2023)
        # Alice: 10,000 (one in 2023)
        # Bob: 2,000
        results = response.data['results']
        assert len(results) == 3

    def test_top_donors_filter_by_value(self, api_client, rich_donation_dataset):
        """Should filter by minimum donation value."""
        url = reverse('api_v2:top-donors')
        response = api_client.get(url, {'value_min': 10000})

        assert response.status_code == status.HTTP_200_OK

        # Only donations >= 10,000
        # Acme: 50,000 + 25,000 = 75,000
        # Big Tech: 40,000
        # Alice: 10,000 (5,000 donation excluded)
        results = response.data['results']
        assert len(results) == 3
        assert results[0]['actor']['name'] == "Acme Corporation"
        assert results[1]['actor']['name'] == "Big Tech Inc"
        assert results[2]['actor']['name'] == "Alice Johnson"
        assert Decimal(str(results[2]['total_donated'])) == Decimal('10000.00')

    def test_top_donors_filter_by_donor_type(self, api_client, rich_donation_dataset):
        """Should filter by donor type (person or organization)."""
        url = reverse('api_v2:top-donors')

        # Only organization donors
        response = api_client.get(url, {'donor_type': 'organization'})
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 2
        assert results[0]['actor']['name'] == "Acme Corporation"
        assert results[1]['actor']['name'] == "Big Tech Inc"

        # Only person donors
        response = api_client.get(url, {'donor_type': 'person'})
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 2
        assert results[0]['actor']['name'] == "Alice Johnson"
        assert results[1]['actor']['name'] == "Bob Williams"

    def test_top_donors_empty_result(self, api_client, db):
        """Should handle empty database gracefully."""
        url = reverse('api_v2:top-donors')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_top_donors_response_structure(self, api_client, rich_donation_dataset):
        """Should return properly structured response."""
        url = reverse('api_v2:top-donors')
        response = api_client.get(url, {'limit': 1})

        assert response.status_code == status.HTTP_200_OK

        # Check pagination structure
        assert 'count' in response.data
        assert 'next' in response.data
        assert 'previous' in response.data
        assert 'results' in response.data

        # Check result structure
        result = response.data['results'][0]
        assert 'actor' in result
        assert 'total_donated' in result
        assert 'donation_count' in result

        # Check actor structure
        actor = result['actor']
        assert 'id' in actor
        assert 'name' in actor
        assert 'actor_type' in actor


# ===========================
# TopRecipientsView Tests
# ===========================

class TestTopRecipientsView:
    """Tests for /api/v2/aggregates/top-recipients/ endpoint."""

    def test_basic_top_recipients(self, api_client, rich_donation_dataset):
        """Should return recipients ranked by total received."""
        url = reverse('api_v2:top-recipients')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

        results = response.data['results']

        # Top recipient should be Sarah Brown MP (55,000)
        # 50,000 from Acme + 5,000 from Alice
        assert results[0]['actor']['name'] == "Sarah Brown MP"
        assert Decimal(str(results[0]['total_received'])) == Decimal('55000.00')
        assert results[0]['donation_count'] == 2

        # Second: David Green MP (42,000)
        assert results[1]['actor']['name'] == "David Green MP"
        assert Decimal(str(results[1]['total_received'])) == Decimal('42000.00')

        # Third: Test Party (35,000)
        assert results[2]['actor']['name'] == "Test Party"
        assert Decimal(str(results[2]['total_received'])) == Decimal('35000.00')

    def test_top_recipients_pagination(self, api_client, rich_donation_dataset):
        """Should paginate results correctly."""
        url = reverse('api_v2:top-recipients')
        response = api_client.get(url, {'limit': 1, 'offset': 1})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

        # Should be second recipient
        assert response.data['results'][0]['actor']['name'] == "David Green MP"

    def test_top_recipients_filter_by_donor_type(self, api_client, rich_donation_dataset):
        """Should filter by donor type."""
        url = reverse('api_v2:top-recipients')

        # Only donations from organizations
        response = api_client.get(url, {'donor_type': 'organization'})
        assert response.status_code == status.HTTP_200_OK

        results = response.data['results']
        # Sarah Brown: 50,000 (from Acme only, Alice excluded)
        # David Green: 40,000 (from Big Tech)
        # Test Party: 25,000 (from Acme only, Alice excluded)
        assert results[0]['actor']['name'] == "Sarah Brown MP"
        assert Decimal(str(results[0]['total_received'])) == Decimal('50000.00')


# ===========================
# NetworkStatsView Tests
# ===========================

class TestNetworkStatsView:
    """Tests for /api/v2/aggregates/network-stats/ endpoint."""

    def test_basic_network_stats(self, api_client, rich_donation_dataset, consultancy_dataset):
        """Should return comprehensive network statistics."""
        url = reverse('api_v2:network-stats')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.data

        # Check all required fields are present
        assert 'total_actors' in data
        assert 'total_persons' in data
        assert 'total_organizations' in data
        assert 'total_donations' in data
        assert 'total_donation_value' in data
        assert 'total_consultancies' in data
        assert 'unique_donors' in data
        assert 'unique_recipients' in data
        assert 'unique_agencies' in data
        assert 'unique_clients' in data
        assert 'date_range_start' in data
        assert 'date_range_end' in data

    def test_network_stats_counts(self, api_client, rich_donation_dataset, consultancy_dataset):
        """Should calculate correct counts."""
        url = reverse('api_v2:network-stats')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # 6 donations in rich_donation_dataset
        assert data['total_donations'] == 6

        # 2 consultancies in consultancy_dataset
        assert data['total_consultancies'] == 2

        # 4 unique donors
        assert data['unique_donors'] == 4

        # 3 unique recipients
        assert data['unique_recipients'] == 3

        # 2 unique agencies
        assert data['unique_agencies'] == 2

        # 2 unique clients
        assert data['unique_clients'] == 2

    def test_network_stats_total_value(self, api_client, rich_donation_dataset):
        """Should calculate total donation value correctly."""
        url = reverse('api_v2:network-stats')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Total: 50k + 25k + 40k + 10k + 5k + 2k = 132,000
        expected_total = Decimal('132000.00')
        assert Decimal(str(response.data['total_donation_value'])) == expected_total

    def test_network_stats_date_range(self, api_client, rich_donation_dataset):
        """Should return correct date range."""
        url = reverse('api_v2:network-stats')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Earliest: 2023-01-15, Latest: 2024-02-15
        assert response.data['date_range_start'] == "2023-01-15"
        assert response.data['date_range_end'] == "2024-02-15"

    def test_network_stats_filter_by_date(self, api_client, rich_donation_dataset):
        """Should filter statistics by date range."""
        url = reverse('api_v2:network-stats')
        response = api_client.get(url, {
            'received_after': '2024-01-01',
            'received_before': '2024-12-31',
        })

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Only 2024 donations (2 total: Big Tech 40k, Alice 5k)
        assert data['total_donations'] == 2

        # Total value: 45,000
        assert Decimal(str(data['total_donation_value'])) == Decimal('45000.00')

        # 2 unique donors (Big Tech, Alice)
        assert data['unique_donors'] == 2

        # Date range should reflect filtered data
        assert data['date_range_start'] == "2024-01-10"
        assert data['date_range_end'] == "2024-02-15"

    def test_network_stats_empty_database(self, api_client, db):
        """Should handle empty database gracefully."""
        url = reverse('api_v2:network-stats')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert data['total_donations'] == 0
        # total_donation_value is formatted as decimal string "0.00"
        assert Decimal(str(data['total_donation_value'])) == Decimal('0.00')
        assert data['unique_donors'] == 0
        assert data['unique_recipients'] == 0


# ===========================
# PartyDonationsView Tests
# ===========================

class TestPartyDonationsView:
    """Tests for /api/v2/aggregates/party-donations/ endpoint."""

    def test_basic_party_donations(self, api_client, rich_donation_dataset):
        """Should return parties with their total donations."""
        url = reverse('api_v2:party-donations')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

        results = response.data['results']
        # Only one political party in dataset
        assert len(results) == 1

        # Test Party received 35,000 (25k from Acme + 10k from Alice)
        party_result = results[0]
        assert party_result['party']['name'] == "Test Party"
        assert Decimal(str(party_result['total_received'])) == Decimal('35000.00')
        assert party_result['donation_count'] == 2
        assert party_result['donor_count'] == 2  # Acme and Alice

    def test_party_donations_pagination(self, api_client, rich_donation_dataset):
        """Should paginate party results."""
        url = reverse('api_v2:party-donations')
        response = api_client.get(url, {'limit': 1})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['count'] == 1

    def test_party_donations_filter_by_date(self, api_client, rich_donation_dataset):
        """Should filter party donations by date range."""
        url = reverse('api_v2:party-donations')

        # Only 2023 donations
        response = api_client.get(url, {
            'received_after': '2023-01-01',
            'received_before': '2023-12-31',
        })

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']

        # Test Party received 35,000 in 2023 (Acme 25k + Alice 10k)
        # Both donations are in 2023: Acme on 2023-06-20, Alice on 2023-03-01
        assert Decimal(str(results[0]['total_received'])) == Decimal('35000.00')
        assert results[0]['donation_count'] == 2
        assert results[0]['donor_count'] == 2  # Acme and Alice

    def test_party_donations_filter_by_donor_type(self, api_client, rich_donation_dataset):
        """Should filter by donor type."""
        url = reverse('api_v2:party-donations')

        # Only organization donors
        response = api_client.get(url, {'donor_type': 'organization'})
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']

        # Only Acme's 25,000 donation
        assert Decimal(str(results[0]['total_received'])) == Decimal('25000.00')
        assert results[0]['donor_count'] == 1

    def test_party_donations_response_structure(self, api_client, rich_donation_dataset):
        """Should return properly structured response."""
        url = reverse('api_v2:party-donations')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        result = response.data['results'][0]
        assert 'party' in result
        assert 'total_received' in result
        assert 'donation_count' in result
        assert 'donor_count' in result

        # Check party actor structure
        party = result['party']
        assert 'id' in party
        assert 'name' in party
        assert 'actor_type' in party
        assert party['actor_type'] == 'organization'
        assert 'classification' in party
        assert party['classification'] == 'Political Party'

    def test_party_donations_empty_result(self, api_client, db):
        """Should handle no political parties gracefully."""
        # Create non-party organization
        org = Organization.objects.create(
            name="Company",
            classification="Company",
        )
        donor = Person.objects.create(
            name="Test Person",
            family_name="Person",
            given_name="Test",
        )

        # Donation to non-party
        Donation.objects.create(
            donor=donor, recipient=org, value=1000.00,
            received_date="2024-01-01", donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False, is_aggregation=False, is_sponsorship=False,
        )

        url = reverse('api_v2:party-donations')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []


# ===========================
# DualInfluenceView Tests
# ===========================

class TestDualInfluenceView:
    """Tests for /api/v2/aggregates/dual-influence/ endpoint."""

    def test_basic_dual_influence(self, api_client, dual_influence_dataset):
        """Should return only organizations that both donate AND lobby."""
        url = reverse('api_v2:dual-influence')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

        results = response.data['results']
        # Should only return the 2 dual-influence orgs (not donor-only or lobby-only)
        assert response.data['count'] == 2

        # Check first result (highest donated)
        # Influential Ltd: 50,000 donation
        assert results[0]['organization']['name'] == "Influential Ltd"
        assert Decimal(str(results[0]['total_donated'])) == Decimal('50000.00')
        assert results[0]['donation_count'] == 1
        assert results[0]['lobbying_count'] == 1

        # Check second result
        # Dual Corp: 40,000 total (25k + 15k)
        assert results[1]['organization']['name'] == "Dual Corp"
        assert Decimal(str(results[1]['total_donated'])) == Decimal('40000.00')
        assert results[1]['donation_count'] == 2
        assert results[1]['lobbying_count'] == 2

    def test_dual_influence_excludes_single_activity(self, api_client, dual_influence_dataset):
        """Should exclude orgs that only donate OR only lobby."""
        url = reverse('api_v2:dual-influence')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Extract all organization names from results
        org_names = [r['organization']['name'] for r in response.data['results']]

        # Should NOT include donor-only or lobby-only orgs
        assert "Donor Only Inc" not in org_names
        assert "Lobby Only Corp" not in org_names

        # Should ONLY include dual-influence orgs
        assert "Dual Corp" in org_names
        assert "Influential Ltd" in org_names

    def test_dual_influence_activity_dates(self, api_client, dual_influence_dataset):
        """Should return correct first and last activity dates."""
        url = reverse('api_v2:dual-influence')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']

        # Check date fields are present
        for result in results:
            assert 'first_activity' in result
            assert 'last_activity' in result

        # Dual Corp: first donation 2023-06-01, last 2024-01-15
        dual_corp = [r for r in results if r['organization']['name'] == "Dual Corp"][0]
        assert dual_corp['first_activity'] == "2023-06-01"
        assert dual_corp['last_activity'] == "2024-01-15"

    def test_dual_influence_pagination(self, api_client, dual_influence_dataset):
        """Should paginate dual-influence results."""
        url = reverse('api_v2:dual-influence')
        response = api_client.get(url, {'limit': 1})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['count'] == 2
        assert response.data['next'] is not None

    def test_dual_influence_filter_by_date(self, api_client, dual_influence_dataset):
        """Should filter by donation date range."""
        url = reverse('api_v2:dual-influence')

        # Only 2024 donations
        response = api_client.get(url, {
            'received_after': '2024-01-01',
        })

        assert response.status_code == status.HTTP_200_OK

        # Only Dual Corp has 2024 donation (15,000)
        results = response.data['results']
        assert len(results) == 1
        assert results[0]['organization']['name'] == "Dual Corp"
        assert Decimal(str(results[0]['total_donated'])) == Decimal('15000.00')

    def test_dual_influence_response_structure(self, api_client, dual_influence_dataset):
        """Should return properly structured response."""
        url = reverse('api_v2:dual-influence')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        result = response.data['results'][0]
        assert 'organization' in result
        assert 'total_donated' in result
        assert 'donation_count' in result
        assert 'lobbying_count' in result
        assert 'first_activity' in result
        assert 'last_activity' in result

        # Check organization structure
        org = result['organization']
        assert 'id' in org
        assert 'name' in org
        assert 'actor_type' in org
        assert org['actor_type'] == 'organization'

    def test_dual_influence_empty_result(self, api_client, db):
        """Should handle no dual-influence orgs gracefully."""
        # Create only donor-only org
        donor = Organization.objects.create(
            name="Simple Donor",
            classification="Company",
        )
        recipient = Person.objects.create(
            name="MP",
            family_name="MP",
            given_name="Test",
        )
        Donation.objects.create(
            donor=donor, recipient=recipient, value=1000.00,
            received_date="2024-01-01", donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False, is_aggregation=False, is_sponsorship=False,
        )

        url = reverse('api_v2:dual-influence')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []


# ===========================
# ActorDetailView Tests
# ===========================

class TestActorDetailView:
    """Tests for /api/v2/actors/{id}/ endpoint."""

    def test_person_detail(self, api_client, rich_donation_dataset):
        """Should return detailed person information with aggregates."""
        donors = rich_donation_dataset['donors']
        person = donors['person_donor1']  # Alice Johnson

        url = reverse('api_v2:actor-detail', kwargs={'pk': person.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert data['id'] == person.pk
        assert data['name'] == "Alice Johnson"
        assert data['actor_type'] == 'person'
        assert data['image'] is None  # No image set

        # Alice made 2 donations totaling 15,000
        assert data['donations_made_count'] == 2
        assert Decimal(str(data['total_donated'])) == Decimal('15000.00')

        # Alice received 0 donations
        assert data['donations_received_count'] == 0
        assert data['total_received'] is None or Decimal(str(data['total_received'])) == Decimal('0.00')

    def test_organization_detail(self, api_client, rich_donation_dataset):
        """Should return detailed organization information."""
        donors = rich_donation_dataset['donors']
        org = donors['org_donor1']  # Acme Corporation

        url = reverse('api_v2:actor-detail', kwargs={'pk': org.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert data['id'] == org.pk
        assert data['name'] == "Acme Corporation"
        assert data['actor_type'] == 'organization'
        assert data['classification'] == 'Company'

        # Acme made 2 donations totaling 75,000
        assert data['donations_made_count'] == 2
        assert Decimal(str(data['total_donated'])) == Decimal('75000.00')

    def test_actor_detail_not_found(self, api_client, db):
        """Should return 404 for non-existent actor."""
        url = reverse('api_v2:actor-detail', kwargs={'pk': 99999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_actor_detail_response_structure(self, api_client, rich_donation_dataset):
        """Should return properly structured actor detail."""
        person = rich_donation_dataset['donors']['person_donor1']
        url = reverse('api_v2:actor-detail', kwargs={'pk': person.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Check all expected fields
        data = response.data
        assert 'id' in data
        assert 'name' in data
        assert 'actor_type' in data
        assert 'classification' in data
        assert 'image' in data
        assert 'donations_made_count' in data
        assert 'donations_received_count' in data
        assert 'total_donated' in data
        assert 'total_received' in data
        assert 'consultancies_as_client' in data
        assert 'consultancies_as_agency' in data


# ===========================
# ActorDonationsMadeView Tests
# ===========================

class TestActorDonationsMadeView:
    """Tests for /api/v2/actors/{id}/donations-made/ endpoint."""

    def test_donations_made(self, api_client, rich_donation_dataset):
        """Should return all donations made by an actor."""
        donors = rich_donation_dataset['donors']
        person = donors['person_donor1']  # Alice Johnson - made 2 donations

        url = reverse('api_v2:actor-donations-made', kwargs={'pk': person.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

        results = response.data['results']
        # Should be ordered by received_date descending
        assert len(results) == 2

        # First result should be most recent (2024-02-15)
        assert results[0]['donor']['name'] == "Alice Johnson"
        assert Decimal(str(results[0]['value'])) == Decimal('5000.00')
        assert results[0]['received_date'] == "2024-02-15"

    def test_donations_made_pagination(self, api_client, rich_donation_dataset):
        """Should paginate donations made."""
        donors = rich_donation_dataset['donors']
        org = donors['org_donor1']  # Acme Corporation - made 2 donations

        url = reverse('api_v2:actor-donations-made', kwargs={'pk': org.pk})
        response = api_client.get(url, {'limit': 1})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['count'] == 2
        assert response.data['next'] is not None

    def test_donations_made_filter_by_date(self, api_client, rich_donation_dataset):
        """Should filter donations by date range."""
        donors = rich_donation_dataset['donors']
        org = donors['org_donor1']  # Acme - 2 donations (2023-01-15, 2023-06-20)

        url = reverse('api_v2:actor-donations-made', kwargs={'pk': org.pk})
        response = api_client.get(url, {
            'received_after': '2023-06-01',
        })

        assert response.status_code == status.HTTP_200_OK
        # Only one donation on/after 2023-06-01
        assert response.data['count'] == 1
        assert response.data['results'][0]['received_date'] == "2023-06-20"

    def test_donations_made_empty_result(self, api_client, rich_donation_dataset):
        """Should handle actors with no donations made."""
        recipients = rich_donation_dataset['recipients']
        mp = recipients['mp1']  # Sarah Brown MP - received donations, made none

        url = reverse('api_v2:actor-donations-made', kwargs={'pk': mp.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_donations_made_response_structure(self, api_client, rich_donation_dataset):
        """Should return properly structured donation details."""
        person = rich_donation_dataset['donors']['person_donor1']
        url = reverse('api_v2:actor-donations-made', kwargs={'pk': person.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        result = response.data['results'][0]
        assert 'id' in result
        assert 'donor' in result
        assert 'recipient' in result
        assert 'value' in result
        assert 'received_date' in result
        assert 'donation_type' in result

        # Check nested actor structure
        assert 'id' in result['donor']
        assert 'name' in result['donor']


# ===========================
# ActorDonationsReceivedView Tests
# ===========================

class TestActorDonationsReceivedView:
    """Tests for /api/v2/actors/{id}/donations-received/ endpoint."""

    def test_donations_received(self, api_client, rich_donation_dataset):
        """Should return all donations received by an actor."""
        recipients = rich_donation_dataset['recipients']
        mp = recipients['mp1']  # Sarah Brown MP - received 2 donations

        url = reverse('api_v2:actor-donations-received', kwargs={'pk': mp.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

        results = response.data['results']
        # Most recent first (2024-02-15)
        assert results[0]['received_date'] == "2024-02-15"
        assert Decimal(str(results[0]['value'])) == Decimal('5000.00')
        assert results[0]['recipient']['name'] == "Sarah Brown MP"

    def test_donations_received_pagination(self, api_client, rich_donation_dataset):
        """Should paginate donations received."""
        recipients = rich_donation_dataset['recipients']
        party = recipients['party']  # Test Party - received 2 donations

        url = reverse('api_v2:actor-donations-received', kwargs={'pk': party.pk})
        response = api_client.get(url, {'limit': 1})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['count'] == 2

    def test_donations_received_filter_by_value(self, api_client, rich_donation_dataset):
        """Should filter by minimum value."""
        recipients = rich_donation_dataset['recipients']
        mp = recipients['mp1']  # Received 50k and 5k

        url = reverse('api_v2:actor-donations-received', kwargs={'pk': mp.pk})
        response = api_client.get(url, {'value_min': 10000})

        assert response.status_code == status.HTTP_200_OK
        # Only the 50,000 donation
        assert response.data['count'] == 1
        assert Decimal(str(response.data['results'][0]['value'])) == Decimal('50000.00')

    def test_donations_received_empty_result(self, api_client, rich_donation_dataset):
        """Should handle actors with no donations received."""
        donors = rich_donation_dataset['donors']
        org = donors['org_donor1']  # Acme - made donations, received none

        url = reverse('api_v2:actor-donations-received', kwargs={'pk': org.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []


# ===========================
# ActorConsultanciesView Tests
# ===========================

class TestActorConsultanciesView:
    """Tests for /api/v2/actors/{id}/consultancies/ endpoint."""

    def test_consultancies_as_client(self, api_client, dual_influence_dataset):
        """Should return consultancies where actor is the client."""
        dual_orgs = dual_influence_dataset['dual_orgs']
        dual_corp = dual_orgs[0]  # Dual Corp - client in 2 consultancies

        url = reverse('api_v2:actor-consultancies', kwargs={'pk': dual_corp.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2

        results = response.data['results']
        # All should have dual_corp as client
        for result in results:
            assert result['client']['name'] == "Dual Corp"
            assert result['agency']['name'] == "Top Lobbying Firm"

    def test_consultancies_as_agency(self, api_client, dual_influence_dataset):
        """Should return consultancies where actor is the agency."""
        agency = dual_influence_dataset['agency']  # Top Lobbying Firm

        url = reverse('api_v2:actor-consultancies', kwargs={'pk': agency.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Agency for all 4 consultancies in dataset
        assert response.data['count'] == 4

        results = response.data['results']
        for result in results:
            assert result['agency']['name'] == "Top Lobbying Firm"

    def test_consultancies_pagination(self, api_client, dual_influence_dataset):
        """Should paginate consultancy results."""
        agency = dual_influence_dataset['agency']

        url = reverse('api_v2:actor-consultancies', kwargs={'pk': agency.pk})
        response = api_client.get(url, {'limit': 2})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
        assert response.data['count'] == 4

    def test_consultancies_empty_result(self, api_client, rich_donation_dataset):
        """Should handle actors with no consultancies."""
        person = rich_donation_dataset['donors']['person_donor1']

        url = reverse('api_v2:actor-consultancies', kwargs={'pk': person.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_consultancies_response_structure(self, api_client, dual_influence_dataset):
        """Should return properly structured consultancy details."""
        dual_corp = dual_influence_dataset['dual_orgs'][0]
        url = reverse('api_v2:actor-consultancies', kwargs={'pk': dual_corp.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        result = response.data['results'][0]
        assert 'id' in result
        assert 'agency' in result
        assert 'client' in result
        assert 'label' in result
        assert 'start_date' in result
        assert 'source' in result

        # Check nested actor structures
        assert 'id' in result['agency']
        assert 'name' in result['agency']
        assert 'id' in result['client']
        assert 'name' in result['client']


# ===========================
# Edge Cases and Error Handling
# ===========================

class TestRegressions:
    """Regression tests for specific bugs that were caught in manual testing."""

    def test_filter_backends_not_applied_to_list_results(self, api_client, rich_donation_dataset):
        """
        REGRESSION: Verify that filter_backends aren't incorrectly applied to list results.

        Previously, we had filter_backends defined on the view class, which caused
        DRF to try applying filters to the list returned by get_queryset(), causing:
        AttributeError: 'list' object has no attribute 'model'

        This test verifies that filtering works correctly through the full HTTP request path.
        """
        url = reverse('api_v2:top-donors')

        # Test that basic request works (no filter_backends crash)
        response = api_client.get(url, {'limit': 3})
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

        # Test that filtering still works (filters applied manually in get_queryset)
        response_filtered = api_client.get(url, {
            'limit': 3,
            'received_after': '2024-01-01'
        })
        assert response_filtered.status_code == status.HTTP_200_OK

        # Filtered results should be different from unfiltered
        assert response_filtered.data['count'] != response.data['count']

        # Test donor_type filter
        response_persons = api_client.get(url, {'donor_type': 'person', 'limit': 1})
        assert response_persons.status_code == status.HTTP_200_OK
        assert response_persons.data['results'][0]['actor']['actor_type'] == 'person'

    def test_donor_classification_filter(self, api_client, enhanced_filter_dataset):
        """
        REGRESSION: Test donor_classification filter correctly filters by organization type.

        Verifies that filtering by 'Trade Union' only returns Trade Union donors,
        and filtering by 'Company' only returns Company donors.
        """
        url = reverse('api_v2:top-donors')

        # Test Trade Union filter
        response_unions = api_client.get(url, {'donor_classification': 'Trade Union'})
        assert response_unions.status_code == status.HTTP_200_OK
        assert response_unions.data['count'] > 0

        # All results should be Trade Unions
        for result in response_unions.data['results']:
            assert result['actor']['classification'] == 'Trade Union'

        # Test Company filter
        response_companies = api_client.get(url, {'donor_classification': 'Company'})
        assert response_companies.status_code == status.HTTP_200_OK
        assert response_companies.data['count'] > 0

        # All results should be Companies
        for result in response_companies.data['results']:
            assert result['actor']['classification'] == 'Company'

    def test_exclude_donor_classification_filter(self, api_client, enhanced_filter_dataset):
        """
        REGRESSION: Test exclude_donor_classification filter correctly excludes types.

        Verifies that excluding 'Trade Union' removes all Trade Union donors,
        and excluding 'Company' removes all Company donors.
        """
        url = reverse('api_v2:top-donors')

        # Get baseline count
        response_all = api_client.get(url)
        total_count = response_all.data['count']

        # Exclude Trade Unions
        response_no_unions = api_client.get(url, {'exclude_donor_classification': 'Trade Union'})
        assert response_no_unions.status_code == status.HTTP_200_OK

        # Should have fewer results than baseline
        assert response_no_unions.data['count'] < total_count

        # No results should be Trade Unions
        for result in response_no_unions.data['results']:
            assert result['actor']['classification'] != 'Trade Union'

        # Exclude Companies
        response_no_companies = api_client.get(url, {'exclude_donor_classification': 'Company'})
        assert response_no_companies.status_code == status.HTTP_200_OK
        assert response_no_companies.data['count'] < total_count

        # No results should be Companies
        for result in response_no_companies.data['results']:
            assert result['actor']['classification'] != 'Company'

    def test_has_lobbying_filter(self, api_client, enhanced_filter_dataset):
        """
        REGRESSION: Test has_lobbying filter shows only donors who are lobbying clients.

        Verifies that has_lobbying=true only returns donors with Consultancy records,
        and has_lobbying=false only returns donors without Consultancy records.
        """
        url = reverse('api_v2:top-donors')

        # Test has_lobbying=true
        response_lobbyists = api_client.get(url, {'has_lobbying': 'true'})
        assert response_lobbyists.status_code == status.HTTP_200_OK
        assert response_lobbyists.data['count'] > 0

        # All results should have is_lobbying_client=True
        for result in response_lobbyists.data['results']:
            assert result.get('is_lobbying_client') is True

        # Test has_lobbying=false
        response_non_lobbyists = api_client.get(url, {'has_lobbying': 'false'})
        assert response_non_lobbyists.status_code == status.HTTP_200_OK

        # All results should have is_lobbying_client=False or None
        for result in response_non_lobbyists.data['results']:
            assert result.get('is_lobbying_client') in (False, None)

    def test_combined_filters(self, api_client, enhanced_filter_dataset):
        """
        REGRESSION: Test combining multiple filters works correctly.

        Verifies that donor_classification + has_lobbying filters work together,
        and that exclusion filters combine with other filters.
        """
        url = reverse('api_v2:top-donors')

        # Test: Trade Unions who also lobby
        response = api_client.get(url, {
            'donor_classification': 'Trade Union',
            'has_lobbying': 'true'
        })
        assert response.status_code == status.HTTP_200_OK

        # All results should be Trade Unions AND lobbying clients
        for result in response.data['results']:
            assert result['actor']['classification'] == 'Trade Union'
            assert result.get('is_lobbying_client') is True

        # Test: Exclude Companies, only show lobbyists
        response = api_client.get(url, {
            'exclude_donor_classification': 'Company',
            'has_lobbying': 'true'
        })
        assert response.status_code == status.HTTP_200_OK

        # No results should be Companies, all should be lobbyists
        for result in response.data['results']:
            assert result['actor']['classification'] != 'Company'
            assert result.get('is_lobbying_client') is True

        # Test: Date range + classification + value filter
        response = api_client.get(url, {
            'donor_classification': 'Trade Union',
            'value_min': '10000',
            'received_after': '2023-01-01'
        })
        assert response.status_code == status.HTTP_200_OK

        # All results should meet all criteria
        for result in response.data['results']:
            assert result['actor']['classification'] == 'Trade Union'
            assert Decimal(result['total_donated']) >= Decimal('10000')


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_donations_with_null_donor(self, api_client, db):
        """Should handle donations with null donor gracefully."""
        recipient = Person.objects.create(
            name="Test Person",
            family_name="Person",
            given_name="Test",
        )

        # Create donation with null donor
        Donation.objects.create(
            donor=None,  # Null donor
            recipient=recipient,
            value=1000.00,
            received_date="2024-01-01",
            donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False,
            is_aggregation=False,
            is_sponsorship=False,
        )

        url = reverse('api_v2:top-donors')
        response = api_client.get(url)

        # Should not crash, should exclude null donors
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_donations_with_null_recipient(self, api_client, db):
        """Should handle donations with null recipient gracefully."""
        donor = Organization.objects.create(
            name="Test Org",
            classification="Company",
        )

        # Create donation with null recipient
        Donation.objects.create(
            donor=donor,
            recipient=None,  # Null recipient
            value=1000.00,
            received_date="2024-01-01",
            donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False,
            is_aggregation=False,
            is_sponsorship=False,
        )

        url = reverse('api_v2:top-recipients')
        response = api_client.get(url)

        # Should not crash, should exclude null recipients
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_invalid_date_format(self, api_client, rich_donation_dataset):
        """Should handle invalid date formats gracefully."""
        url = reverse('api_v2:top-donors')
        response = api_client.get(url, {'received_after': 'not-a-date'})

        # Django-filter silently ignores invalid dates (treats as no filter)
        # This is reasonable behavior - doesn't crash
        assert response.status_code == status.HTTP_200_OK
        # Should return all donors since filter is ignored
        assert response.data['count'] == 4

    def test_invalid_pagination_params(self, api_client, rich_donation_dataset):
        """Should handle invalid pagination parameters."""
        url = reverse('api_v2:top-donors')

        # Negative limit should be rejected or handled
        response = api_client.get(url, {'limit': -1})
        # DRF typically returns the data anyway with corrected limit
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

        # Exceeding max limit (500)
        response = api_client.get(url, {'limit': 1000})
        assert response.status_code == status.HTTP_200_OK
        # Should be capped at max_limit (500)
        assert len(response.data['results']) <= 500

    def test_unauthenticated_access(self, api_client, rich_donation_dataset):
        """All endpoints should allow unauthenticated access (public API)."""
        endpoints = [
            reverse('api_v2:top-donors'),
            reverse('api_v2:top-recipients'),
            reverse('api_v2:network-stats'),
        ]

        for url in endpoints:
            response = api_client.get(url)
            assert response.status_code == status.HTTP_200_OK
