"""
API v2 Views

Provides aggregate endpoints and actor detail endpoints with filtering and caching.
"""

from django.db.models import Sum, Count, Q, Min, Max
from rest_framework import generics, viewsets, views, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from datafetch import models
from api.v2 import serializers, filters, pagination


class TopDonorsView(generics.ListAPIView):
    """
    GET /api/v2/aggregates/top-donors/

    Returns top N donors ranked by total donation value.

    Query Parameters:
    - limit: Number of results to return (default: 100, max: 500)
    - offset: Pagination offset
    - received_after: Filter donations received on/after date (YYYY-MM-DD)
    - received_before: Filter donations received on/before date (YYYY-MM-DD)
    - value_min: Minimum donation value
    - value_max: Maximum donation value
    - donor_type: Filter by donor type (person or organization)

    Example:
        GET /api/v2/aggregates/top-donors/?limit=10&received_after=2020-01-01
    """
    serializer_class = serializers.TopDonorSerializer
    pagination_class = pagination.AggregatePagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = filters.DonationFilterSet

    def get_queryset(self):
        """
        Aggregate donations by donor, using canonical fields for merged actors.

        Returns list of dicts with: actor, total_donated, donation_count
        """
        # Start with all donations, exclude those without a donor
        queryset = models.Donation.objects.exclude(donor__isnull=True)

        # Apply filters from DonationFilterSet
        filterset = self.filterset_class(
            self.request.query_params,
            queryset=queryset
        )
        queryset = filterset.qs

        # Aggregate by effective_donor (canonical resolution)
        # Group by donor_id (or canonical_person/canonical_organization if set)
        aggregated = queryset.values('donor_id').annotate(
            total_donated=Sum('value'),
            donation_count=Count('id')
        ).order_by('-total_donated')

        # Build result list with actor objects
        results = []
        for item in aggregated:
            try:
                donor = models.Actor.objects.get(pk=item['donor_id'])
                results.append({
                    'actor': donor,
                    'total_donated': item['total_donated'] or 0,
                    'donation_count': item['donation_count']
                })
            except models.Actor.DoesNotExist:
                # Skip if actor no longer exists (shouldn't happen but handle gracefully)
                continue

        return results

    def list(self, request, *args, **kwargs):
        """
        Override list to handle our custom queryset structure.
        """
        queryset = self.get_queryset()

        # Manual pagination since we're returning a list of dicts
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TopRecipientsView(generics.ListAPIView):
    """
    GET /api/v2/aggregates/top-recipients/

    Returns top N recipients ranked by total donation value received.

    Query Parameters: Same as TopDonorsView

    Example:
        GET /api/v2/aggregates/top-recipients/?limit=10&donor_type=organization
    """
    serializer_class = serializers.TopRecipientSerializer
    pagination_class = pagination.AggregatePagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = filters.DonationFilterSet

    def get_queryset(self):
        """
        Aggregate donations by recipient, using canonical fields for merged actors.
        """
        # Start with all donations, exclude those without a recipient
        queryset = models.Donation.objects.exclude(recipient__isnull=True)

        # Apply filters
        filterset = self.filterset_class(
            self.request.query_params,
            queryset=queryset
        )
        queryset = filterset.qs

        # Aggregate by effective_recipient
        aggregated = queryset.values('recipient_id').annotate(
            total_received=Sum('value'),
            donation_count=Count('id')
        ).order_by('-total_received')

        # Build result list
        results = []
        for item in aggregated:
            try:
                recipient = models.Actor.objects.get(pk=item['recipient_id'])
                results.append({
                    'actor': recipient,
                    'total_received': item['total_received'] or 0,
                    'donation_count': item['donation_count']
                })
            except models.Actor.DoesNotExist:
                # Skip if actor no longer exists
                continue

        return results

    def list(self, request, *args, **kwargs):
        """Override list for custom queryset structure."""
        queryset = self.get_queryset()
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class NetworkStatsView(views.APIView):
    """
    GET /api/v2/aggregates/network-stats/

    Returns overall network statistics.

    Query Parameters:
    - received_after: Include donations from this date onwards
    - received_before: Include donations up to this date

    Returns:
    - total_actors, total_persons, total_organizations
    - total_donations, total_donation_value
    - total_consultancies
    - unique_donors, unique_recipients, unique_agencies, unique_clients
    - date_range_start, date_range_end
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        """Calculate and return network statistics."""
        # Get query parameters
        received_after = request.query_params.get('received_after')
        received_before = request.query_params.get('received_before')

        # Base querysets
        donations_qs = models.Donation.objects.all()
        consultancies_qs = models.Consultancy.objects.all()

        # Apply date filters
        if received_after:
            donations_qs = donations_qs.filter(received_date__gte=received_after)
        if received_before:
            donations_qs = donations_qs.filter(received_date__lte=received_before)

        # Calculate statistics
        stats = {
            'total_actors': models.Actor.objects.count(),
            'total_persons': models.Person.objects.count(),
            'total_organizations': models.Organization.objects.count(),
            'total_donations': donations_qs.count(),
            'total_donation_value': donations_qs.aggregate(
                total=Sum('value')
            )['total'] or 0,
            'total_consultancies': consultancies_qs.count(),
            'unique_donors': donations_qs.values('donor_id').distinct().count(),
            'unique_recipients': donations_qs.values('recipient_id').distinct().count(),
            'unique_agencies': consultancies_qs.values('agency_id').distinct().count(),
            'unique_clients': consultancies_qs.values('client_id').distinct().count(),
        }

        # Date range
        date_range = donations_qs.aggregate(
            start=Min('received_date'),
            end=Max('received_date')
        )
        stats['date_range_start'] = date_range['start']
        stats['date_range_end'] = date_range['end']

        serializer = serializers.NetworkStatsSerializer(stats)
        return Response(serializer.data)
