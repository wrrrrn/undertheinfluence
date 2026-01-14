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
