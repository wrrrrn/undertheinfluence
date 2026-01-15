"""
API v2 Views

Provides aggregate endpoints and actor detail endpoints with filtering and caching.
"""

import time
from django.db.models import Sum, Count, Q, Min, Max
from rest_framework import generics, viewsets, views, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

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
    permission_classes = [permissions.AllowAny]
    # Note: We apply filters manually in get_queryset() before aggregation
    # Don't use filter_backends here as get_queryset() returns a list, not a QuerySet

    def get_queryset(self):
        """
        Aggregate donations by donor, using canonical fields for merged actors.

        Returns list of dicts with: actor, total_donated, donation_count
        """
        # Start with all donations, exclude those without a donor
        # Use select_related to pre-fetch donor objects
        queryset = models.Donation.objects.exclude(donor__isnull=True).select_related('donor')

        # Apply filters from DonationFilterSet
        filterset = filters.DonationFilterSet(
            self.request.query_params,
            queryset=queryset
        )
        queryset = filterset.qs

        # Aggregate by effective_donor (canonical resolution)
        # Group by donor_id and include donor object
        # Note: Don't materialize the full queryset yet - let pagination slice it first
        aggregated = queryset.values('donor_id', 'donor__name').annotate(
            total_donated=Sum('value'),
            donation_count=Count('id')
        ).order_by('-total_donated')

        return aggregated

    def list(self, request, *args, **kwargs):
        """
        Override list to handle aggregation and pagination efficiently.

        Key optimization: Only fetch Actor objects for the paginated subset,
        not all 21k donors. This reduces query time from ~3s to <0.5s.
        """
        # Get aggregated queryset (still a QuerySet, not materialized)
        aggregated_qs = self.get_queryset()

        # Apply pagination to the QuerySet BEFORE fetching actors
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(aggregated_qs, request, view=self)

        # Now fetch Actor objects only for the paginated results
        if page is not None:
            # Extract donor_ids from the paginated subset only
            donor_ids = [item['donor_id'] for item in page]

            # Fetch only the actors we need (e.g., 10-100, not 21k)
            actors_dict = {
                actor.id: actor
                for actor in models.Actor.objects.filter(id__in=donor_ids)
            }

            # Check which donors are lobbying clients (have Consultancy records)
            lobbying_donor_ids = set(
                models.Consultancy.objects.filter(client_id__in=donor_ids)
                .values_list('client_id', flat=True)
                .distinct()
            )

            # Build result list with actor objects
            results = []
            for item in page:
                donor_id = item['donor_id']
                if donor_id in actors_dict:
                    results.append({
                        'actor': actors_dict[donor_id],
                        'total_donated': item['total_donated'] or 0,
                        'donation_count': item['donation_count'],
                        'is_lobbying_client': donor_id in lobbying_donor_ids
                    })

            serializer = self.get_serializer(results, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Fallback for no pagination (shouldn't happen with our pagination class)
        donor_ids = [item['donor_id'] for item in aggregated_qs]
        actors_dict = {
            actor.id: actor
            for actor in models.Actor.objects.filter(id__in=donor_ids)
        }
        lobbying_donor_ids = set(
            models.Consultancy.objects.filter(client_id__in=donor_ids)
            .values_list('client_id', flat=True)
            .distinct()
        )
        results = [
            {
                'actor': actors_dict[item['donor_id']],
                'total_donated': item['total_donated'] or 0,
                'donation_count': item['donation_count'],
                'is_lobbying_client': item['donor_id'] in lobbying_donor_ids
            }
            for item in aggregated_qs
            if item['donor_id'] in actors_dict
        ]
        serializer = self.get_serializer(results, many=True)
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
    permission_classes = [permissions.AllowAny]
    # Note: We apply filters manually in get_queryset() before aggregation
    # Don't use filter_backends here as get_queryset() returns a list, not a QuerySet

    def get_queryset(self):
        """
        Aggregate donations by recipient, using canonical fields for merged actors.
        """
        # Start with all donations, exclude those without a recipient
        # Use select_related to pre-fetch recipient objects
        queryset = models.Donation.objects.exclude(recipient__isnull=True).select_related('recipient')

        # Apply filters
        filterset = filters.DonationFilterSet(
            self.request.query_params,
            queryset=queryset
        )
        queryset = filterset.qs

        # Aggregate by effective_recipient
        # Note: Don't materialize the full queryset - let pagination slice it first
        aggregated = queryset.values('recipient_id', 'recipient__name').annotate(
            total_received=Sum('value'),
            donation_count=Count('id')
        ).order_by('-total_received')

        return aggregated

    def list(self, request, *args, **kwargs):
        """
        Override list to handle aggregation and pagination efficiently.

        Key optimization: Only fetch Actor objects for the paginated subset.
        """
        # Get aggregated queryset (still a QuerySet, not materialized)
        aggregated_qs = self.get_queryset()

        # Apply pagination to the QuerySet BEFORE fetching actors
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(aggregated_qs, request, view=self)

        # Now fetch Actor objects only for the paginated results
        if page is not None:
            # Extract recipient_ids from the paginated subset only
            recipient_ids = [item['recipient_id'] for item in page]

            # Fetch only the actors we need
            actors_dict = {
                actor.id: actor
                for actor in models.Actor.objects.filter(id__in=recipient_ids)
            }

            # Build result list with actor objects
            results = []
            for item in page:
                recipient_id = item['recipient_id']
                if recipient_id in actors_dict:
                    results.append({
                        'actor': actors_dict[recipient_id],
                        'total_received': item['total_received'] or 0,
                        'donation_count': item['donation_count']
                    })

            serializer = self.get_serializer(results, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Fallback for no pagination
        recipient_ids = [item['recipient_id'] for item in aggregated_qs]
        actors_dict = {
            actor.id: actor
            for actor in models.Actor.objects.filter(id__in=recipient_ids)
        }
        results = [
            {
                'actor': actors_dict[item['recipient_id']],
                'total_received': item['total_received'] or 0,
                'donation_count': item['donation_count']
            }
            for item in aggregated_qs
            if item['recipient_id'] in actors_dict
        ]
        serializer = self.get_serializer(results, many=True)
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


class PartyDonationsView(generics.ListAPIView):
    """
    GET /api/v2/aggregates/party-donations/

    Returns donations aggregated by political party (direct donations to parties).

    Query Parameters:
    - limit: Number of results (default: 50, max: 200)
    - offset: Pagination offset
    - received_after: Filter by date
    - received_before: Filter by date

    Example:
        GET /api/v2/aggregates/party-donations/?limit=10&received_after=2020-01-01
    """
    serializer_class = serializers.PartyDonationSerializer
    pagination_class = pagination.AggregatePagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """
        Aggregate donations to political party organizations.

        Returns: party, total_received, donation_count, donor_count
        """
        # Filter for political party organizations only
        queryset = models.Donation.objects.filter(
            recipient__organization__classification='Political Party'
        ).exclude(recipient__isnull=True)

        # Apply date filters
        filterset = filters.DonationFilterSet(
            self.request.query_params,
            queryset=queryset
        )
        queryset = filterset.qs

        # Aggregate by party (recipient)
        aggregated = queryset.values('recipient_id', 'recipient__name').annotate(
            total_received=Sum('value'),
            donation_count=Count('id'),
            donor_count=Count('donor_id', distinct=True)
        ).order_by('-total_received')

        return aggregated

    def list(self, request, *args, **kwargs):
        """Handle pagination and actor fetching efficiently."""
        aggregated_qs = self.get_queryset()
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(aggregated_qs, request, view=self)

        if page is not None:
            # Fetch party actors for paginated results only
            party_ids = [item['recipient_id'] for item in page]
            parties_dict = {
                actor.id: actor
                for actor in models.Actor.objects.filter(id__in=party_ids)
            }

            results = []
            for item in page:
                party_id = item['recipient_id']
                if party_id in parties_dict:
                    results.append({
                        'party': parties_dict[party_id],
                        'total_received': item['total_received'] or 0,
                        'donation_count': item['donation_count'],
                        'donor_count': item['donor_count'],
                    })

            serializer = self.get_serializer(results, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Fallback without pagination
        party_ids = [item['recipient_id'] for item in aggregated_qs]
        parties_dict = {
            actor.id: actor
            for actor in models.Actor.objects.filter(id__in=party_ids)
        }
        results = [
            {
                'party': parties_dict[item['recipient_id']],
                'total_received': item['total_received'] or 0,
                'donation_count': item['donation_count'],
                'donor_count': item['donor_count'],
            }
            for item in aggregated_qs
            if item['recipient_id'] in parties_dict
        ]
        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)


class DualInfluenceView(generics.ListAPIView):
    """
    GET /api/v2/aggregates/dual-influence/

    Returns organizations that both donate AND use lobbying agencies.

    This identifies actors with dual channels of political influence:
    directly donating and hiring lobbyists.

    Query Parameters:
    - limit: Number of results (default: 50, max: 200)
    - min_donated: Minimum total donated
    - min_lobbying: Minimum lobbying relationships

    Example:
        GET /api/v2/aggregates/dual-influence/?limit=20&min_donated=10000
    """
    serializer_class = serializers.DualInfluenceSerializer
    pagination_class = pagination.AggregatePagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """
        Find organizations that both donate and lobby.

        Uses subqueries to find actors present in both donations (as donor)
        and consultancies (as client).
        """
        from django.db.models import Exists, OuterRef

        # Actors who have donated
        donors = models.Donation.objects.filter(
            donor_id=OuterRef('pk')
        ).values('donor_id')

        # Actors who have used lobbying agencies
        clients = models.Consultancy.objects.filter(
            client_id=OuterRef('pk')
        ).values('client_id')

        # Find actors in both sets
        dual_influence_actors = models.Actor.objects.annotate(
            has_donated=Exists(donors),
            has_lobbied=Exists(clients)
        ).filter(has_donated=True, has_lobbied=True)

        # Now aggregate their activity
        actor_ids = list(dual_influence_actors.values_list('id', flat=True))

        # Aggregate donations (apply date filters)
        donation_queryset = models.Donation.objects.filter(
            donor_id__in=actor_ids
        )

        # Apply date filters from query parameters
        filterset = filters.DonationFilterSet(
            self.request.query_params,
            queryset=donation_queryset
        )
        donation_queryset = filterset.qs

        donation_agg = donation_queryset.values('donor_id').annotate(
            total_donated=Sum('value'),
            donation_count=Count('id'),
            first_donation=Min('received_date'),
            last_donation=Max('received_date')
        )

        # Aggregate consultancies
        consultancy_agg = models.Consultancy.objects.filter(
            client_id__in=actor_ids
        ).values('client_id').annotate(
            lobbying_count=Count('id'),
            first_consultancy=Min('start_date'),
            last_consultancy=Max('start_date')
        )

        # Build lookup dicts
        donation_data = {item['donor_id']: item for item in donation_agg}
        consultancy_data = {item['client_id']: item for item in consultancy_agg}

        # Combine data
        results = []
        for actor_id in actor_ids:
            don_data = donation_data.get(actor_id, {})
            cons_data = consultancy_data.get(actor_id, {})

            if don_data and cons_data:
                # Calculate activity span (handle that consultancy dates are strings)
                first_donation = don_data.get('first_donation')
                last_donation = don_data.get('last_donation')
                # Consultancy dates are stored as strings, use them directly
                first_consultancy = cons_data.get('first_consultancy')
                last_consultancy = cons_data.get('last_consultancy')

                results.append({
                    'actor_id': actor_id,
                    'total_donated': don_data.get('total_donated', 0),
                    'donation_count': don_data.get('donation_count', 0),
                    'lobbying_count': cons_data.get('lobbying_count', 0),
                    # Use donation dates since they're actual dates
                    'first_activity': first_donation,
                    'last_activity': last_donation,
                })

        # Sort by total donated descending
        results.sort(key=lambda x: x['total_donated'], reverse=True)

        return results

    def list(self, request, *args, **kwargs):
        """Handle pagination and actor fetching."""
        results = self.get_queryset()

        # Manual pagination on list
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(results, request, view=self)

        if page is not None:
            # Fetch actors for paginated results
            actor_ids = [item['actor_id'] for item in page]
            actors_dict = {
                actor.id: actor
                for actor in models.Actor.objects.filter(id__in=actor_ids)
            }

            enriched_results = []
            for item in page:
                actor_id = item['actor_id']
                if actor_id in actors_dict:
                    enriched_results.append({
                        'organization': actors_dict[actor_id],
                        'total_donated': item['total_donated'],
                        'donation_count': item['donation_count'],
                        'lobbying_count': item['lobbying_count'],
                        'first_activity': item['first_activity'],
                        'last_activity': item['last_activity'],
                    })

            serializer = self.get_serializer(enriched_results, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Fallback without pagination
        actor_ids = [item['actor_id'] for item in results]
        actors_dict = {
            actor.id: actor
            for actor in models.Actor.objects.filter(id__in=actor_ids)
        }
        enriched_results = [
            {
                'organization': actors_dict[item['actor_id']],
                'total_donated': item['total_donated'],
                'donation_count': item['donation_count'],
                'lobbying_count': item['lobbying_count'],
                'first_activity': item['first_activity'],
                'last_activity': item['last_activity'],
            }
            for item in results
            if item['actor_id'] in actors_dict
        ]
        serializer = self.get_serializer(enriched_results, many=True)
        return Response(serializer.data)


# ===========================
# Actor Detail Endpoints
# ===========================

class ActorDetailView(generics.RetrieveAPIView):
    """
    GET /api/v2/actors/{id}/

    Returns detailed information about a specific actor (person or organization).

    Includes aggregated relationship counts and totals.
    """
    queryset = models.Actor.objects.all()
    serializer_class = serializers.ActorDetailSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Annotate with relationship aggregates."""
        return models.Actor.objects.annotate(
            donations_made_count=Count('donated_to', distinct=True),
            donations_received_count=Count('received_donations_from', distinct=True),
            total_donated=Sum('donated_to__value'),
            total_received=Sum('received_donations_from__value'),
            consultancies_as_client=Count('consulting_agencies', distinct=True),
            consultancies_as_agency=Count('consulting_clients', distinct=True),
        )


class ActorDonationsMadeView(generics.ListAPIView):
    """
    GET /api/v2/actors/{id}/donations-made/

    Returns all donations made by this actor.

    Query Parameters:
    - received_after, received_before: Date filtering
    - limit, offset: Pagination
    """
    serializer_class = serializers.DonationDetailSerializer
    pagination_class = pagination.DetailPagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Get donations made by this actor."""
        actor_id = self.kwargs['pk']
        queryset = models.Donation.objects.filter(donor_id=actor_id).select_related(
            'donor', 'recipient'
        ).order_by('-received_date')

        # Apply filters
        filterset = filters.DonationFilterSet(
            self.request.query_params,
            queryset=queryset
        )
        return filterset.qs


class ActorDonationsReceivedView(generics.ListAPIView):
    """
    GET /api/v2/actors/{id}/donations-received/

    Returns all donations received by this actor.

    Query Parameters:
    - received_after, received_before: Date filtering
    - limit, offset: Pagination
    """
    serializer_class = serializers.DonationDetailSerializer
    pagination_class = pagination.DetailPagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Get donations received by this actor."""
        actor_id = self.kwargs['pk']
        queryset = models.Donation.objects.filter(recipient_id=actor_id).select_related(
            'donor', 'recipient'
        ).order_by('-received_date')

        # Apply filters
        filterset = filters.DonationFilterSet(
            self.request.query_params,
            queryset=queryset
        )
        return filterset.qs


class ActorConsultanciesView(generics.ListAPIView):
    """
    GET /api/v2/actors/{id}/consultancies/

    Returns consultancy relationships for this actor (as client or agency).

    Query Parameters:
    - role: 'client' or 'agency' (default: both)
    - limit, offset: Pagination
    """
    serializer_class = serializers.ConsultancyDetailSerializer
    pagination_class = pagination.DetailPagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Get consultancies involving this actor."""
        actor_id = self.kwargs['pk']
        role = self.request.query_params.get('role')

        if role == 'client':
            queryset = models.Consultancy.objects.filter(client_id=actor_id)
        elif role == 'agency':
            queryset = models.Consultancy.objects.filter(agency_id=actor_id)
        else:
            # Both client and agency roles
            queryset = models.Consultancy.objects.filter(
                Q(client_id=actor_id) | Q(agency_id=actor_id)
            )

        return queryset.select_related('client', 'agency').order_by('-start_date')


class ActorMembershipsView(generics.ListAPIView):
    """
    GET /api/v2/actors/{id}/memberships/

    Returns membership relationships for this actor (organizations they belong to).

    **Temporal Querying:**
    Use ?at_date=YYYY-MM-DD to see memberships active at a specific date.

    Query Parameters:
    - at_date: Show memberships active at this date (YYYY-MM-DD)
    - role: Filter by role/position
    - organization_name: Filter by organization name
    - limit, offset: Pagination

    Example:
        GET /api/v2/actors/123/memberships/?at_date=2020-01-01
        Returns: Memberships active on January 1st, 2020
    """
    serializer_class = serializers.MembershipDetailSerializer
    pagination_class = pagination.DetailPagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Get memberships for this actor with temporal filtering."""
        actor_id = self.kwargs['pk']

        # Base queryset - find memberships for this person
        queryset = models.Membership.objects.filter(
            person_id=actor_id
        ).select_related('person', 'organization', 'post')

        # Apply temporal and other filters
        filterset = filters.MembershipFilterSet(
            self.request.query_params,
            queryset=queryset
        )

        return filterset.qs.order_by('-start_date')


class DonorConcentrationView(views.APIView):
    """
    GET /api/v2/aggregates/donor-concentration/

    Returns donor concentration metrics to identify monopolistic vs. dispersed donor bases.

    **Metrics:**
    - Herfindahl-Hirschman Index (HHI): 0-1, higher = more concentrated
    - Top 10% share: % of total donated by top 10% of donors
    - Top donor share: % of total donated by single largest donor
    - Gini coefficient: 0-1, higher = more unequal distribution
    - Concentration category: Classification (highly/moderately/dispersed)

    **Interpretation:**
    - HHI > 0.25: Highly concentrated (monopolistic)
    - HHI 0.15-0.25: Moderately concentrated
    - HHI < 0.15: Dispersed (competitive)

    Query Parameters:
    - received_after: Filter donations from this date
    - received_before: Filter donations up to this date
    - recipient: Filter by specific recipient ID

    Example:
        GET /api/v2/aggregates/donor-concentration/?received_after=2020-01-01
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        """Calculate donor concentration metrics."""
        # Get query parameters
        recipient_id = request.query_params.get('recipient')

        # Base queryset
        queryset = models.Donation.objects.exclude(donor__isnull=True)

        # Apply filters
        filterset = filters.DonationFilterSet(request.query_params, queryset=queryset)
        queryset = filterset.qs

        # Filter by specific recipient if provided
        if recipient_id:
            queryset = queryset.filter(recipient_id=recipient_id)

        # Aggregate by donor
        donor_totals = queryset.values('donor_id').annotate(
            total=Sum('value')
        ).order_by('-total')

        # Convert to list of amounts (sorted descending) - convert Decimal to float
        amounts = [float(item['total']) for item in donor_totals if item['total']]

        if not amounts:
            # No data - return zeros
            return Response({
                'total_donors': 0,
                'total_donated': 0,
                'herfindahl_index': 0,
                'top_10_percent_share': 0,
                'top_donor_share': 0,
                'gini_coefficient': 0,
                'concentration_category': 'no_data',
            })

        # Calculate metrics
        total_donors = len(amounts)
        total_donated = sum(amounts)

        # Herfindahl-Hirschman Index (HHI)
        # Sum of squared market shares
        market_shares = [amount / total_donated for amount in amounts]
        hhi = sum(share ** 2 for share in market_shares)

        # Top 10% share
        top_10_count = max(1, int(total_donors * 0.1))
        top_10_total = sum(amounts[:top_10_count])
        top_10_share = (top_10_total / total_donated * 100) if total_donated else 0

        # Top donor share
        top_donor_share = (amounts[0] / total_donated * 100) if total_donated else 0

        # Gini coefficient
        # Measures inequality: 0 = perfect equality, 1 = perfect inequality
        gini = self._calculate_gini(amounts)

        # Concentration category
        if hhi > 0.25:
            category = 'highly_concentrated'
        elif hhi > 0.15:
            category = 'moderately_concentrated'
        else:
            category = 'dispersed'

        data = {
            'total_donors': total_donors,
            'total_donated': total_donated,
            'herfindahl_index': round(hhi, 4),
            'top_10_percent_share': round(top_10_share, 2),
            'top_donor_share': round(top_donor_share, 2),
            'gini_coefficient': round(gini, 4),
            'concentration_category': category,
        }

        serializer = serializers.DonorConcentrationSerializer(data)
        return Response(serializer.data)

    def _calculate_gini(self, amounts):
        """
        Calculate Gini coefficient for income inequality.

        Args:
            amounts: List of donation amounts (sorted descending)

        Returns:
            float: Gini coefficient (0-1)
        """
        if not amounts or sum(amounts) == 0:
            return 0

        # Sort ascending for Gini calculation
        sorted_amounts = sorted(amounts)
        n = len(sorted_amounts)
        cumsum = 0
        total = sum(sorted_amounts)

        # Calculate Gini using the formula:
        # G = (2 * sum(i * x_i)) / (n * sum(x_i)) - (n + 1) / n
        for i, amount in enumerate(sorted_amounts, 1):
            cumsum += i * amount

        gini = (2 * cumsum) / (n * total) - (n + 1) / n
        return max(0, min(1, gini))  # Clamp to [0, 1]
