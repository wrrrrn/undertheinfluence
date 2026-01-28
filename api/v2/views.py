"""
API v2 Views

Provides aggregate endpoints and actor detail endpoints with filtering and caching.
"""

import time
from django.db.models import Sum, Count, Q, Min, Max, Case, When, F, IntegerField, Prefetch
from rest_framework import generics, viewsets, views, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

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


class ActorMeetingsView(generics.ListAPIView):
    """
    GET /api/v2/actors/{id}/meetings/

    Returns ministerial meetings involving this actor.
    - If actor is a Minister: shows meetings hosted.
    - If actor is an External Organization/Person: shows meetings attended.

    Query Parameters:
    - date_after, date_before: Date filtering
    - limit, offset: Pagination
    """
    serializer_class = serializers.MinisterialMeetingSerializer
    pagination_class = pagination.DetailPagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        actor_id = self.kwargs['pk']
        
        # Check if actor is involved as minister or external actor
        # Also check canonical_actor in attendees for robust matching
        queryset = models.MinisterialMeeting.objects.filter(
            Q(minister_id=actor_id) |
            Q(attendees__actor_id=actor_id) |
            Q(attendees__canonical_actor_id=actor_id)
        ).select_related(
            'minister', 'department'
        ).prefetch_related(
            'attendees', 'attendees__actor'
        ).distinct().order_by('-meeting_date')

        # Apply filters
        filterset = filters.MinisterialMeetingFilterSet(
            self.request.query_params,
            queryset=queryset
        )
        return filterset.qs


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


class HomepageStatsView(views.APIView):
    """
    GET /api/v2/aggregates/stats/

    Returns key statistics for the homepage metrics strip.

    **Query Parameters:**
    - received_after: Filter donations received on/after date (YYYY-MM-DD)
    - received_before: Filter donations received on/before date (YYYY-MM-DD)
    - value_min: Minimum donation value
    - donor_type: Filter by donor type (person or organization)

    **Returns:**
    - total_donations: Count of all donation records
    - total_value: Sum of all donation values (in pence)
    - concentration_top_1_percent: Decimal percentage (e.g., 0.65 for 65%)
    - concentration_donors_count: Number of donors in top 1.3% (277 donors)
    - dual_influence_count: Count of organizations that both donate and lobby
    - timestamp: ISO timestamp for "Data as of" display

    **Note:** These are expensive calculations. In production, this endpoint
    should read from materialized views refreshed nightly.

    Example:
        GET /api/v2/aggregates/stats/?received_after=2020-01-01
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        """Calculate homepage statistics with optional filtering."""
        
        # Start with base queryset
        donations_qs = models.Donation.objects.all()

        # Apply filters using DonationFilterSet
        filterset = filters.DonationFilterSet(
            request.query_params,
            queryset=donations_qs
        )
        donations_qs = filterset.qs

        # Total donations and value
        donation_stats = donations_qs.aggregate(
            total_donations=Count('id'),
            total_value=Sum('value')
        )

        # Donor concentration calculation
        # Get all donors ranked by total donated (with filters applied)
        donor_totals = donations_qs.exclude(
            donor__isnull=True
        ).values('donor_id').annotate(
            total=Sum('value')
        ).order_by('-total')

        donor_totals_list = list(donor_totals)
        total_donors = len(donor_totals_list)
        total_value = donation_stats['total_value'] or 0

        # Calculate top 1.3% concentration
        # 1.3% of ~21k donors = ~277 donors
        top_1_3_percent_count = max(1, int(total_donors * 0.013))
        top_1_3_percent_total = sum(
            item['total'] for item in donor_totals_list[:top_1_3_percent_count]
        )
        concentration_percentage = (
            float(top_1_3_percent_total) / float(total_value)
            if total_value else 0
        )

        # Dual influence count
        # Count organizations that both donate AND use lobbying agencies (respecting filters)
        from django.db.models import Exists, OuterRef

        # Use filtered donations queryset for dual influence calculation
        donors = donations_qs.filter(
            donor_id=OuterRef('pk')
        ).values('donor_id')

        clients = models.Consultancy.objects.filter(
            client_id=OuterRef('pk')
        ).values('client_id')

        dual_influence_count = models.Actor.objects.annotate(
            has_donated=Exists(donors),
            has_lobbied=Exists(clients)
        ).filter(has_donated=True, has_lobbied=True).count()

        data = {
            'total_donations': donation_stats['total_donations'] or 0,
            'total_value': donation_stats['total_value'] or 0,
            'concentration_top_1_percent': concentration_percentage,
            'concentration_donors_count': top_1_3_percent_count,
            'dual_influence_count': dual_influence_count,
            'timestamp': timezone.now().isoformat(),
        }

        serializer = serializers.HomepageStatsSerializer(data)
        return Response(serializer.data)


class MinisterNetworkView(views.APIView):
    """
    GET /api/v2/aggregates/minister-network/

    Returns D3-compatible network graph data showing connections to government ministers.

    **Nodes:**
    - Ministers (persons with ministerial roles, excluding shadow ministers)
    - Donors (persons/organizations who donated to ministers)

    **Links:**
    - Donation relationships between donors and ministers

    **Query Parameters:**
    - limit: Maximum number of ministers to include (default: 50)
    - min_value: Minimum total donation value to include a connection (default: 1000)
    - min_meetings: Minimum meeting count to include an attendee (default: 3)
    - received_after: Filter donations from this date (YYYY-MM-DD)
    - received_before: Filter donations up to this date (YYYY-MM-DD)
    - current_only: If 'true', only include current ministers (default: false)

    **Returns:**
    - nodes: Array of {id, name, type, total_value, ...}
    - links: Array of {source, target, value, count}
    - stats: Summary statistics

    Example:
        GET /api/v2/aggregates/minister-network/?limit=30&min_value=10000&current_only=true
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        """Build and return the minister network graph."""
        # Get query parameters
        limit = int(request.query_params.get('limit', 50))
        min_value = float(request.query_params.get('min_value', 1000))
        min_meetings = int(request.query_params.get('min_meetings', 5))
        received_after = request.query_params.get('received_after')
        received_before = request.query_params.get('received_before')
        current_only = request.query_params.get('current_only', 'false').lower() == 'true'

        # Find ministers - look for specific ministerial titles
        # Use exact patterns to avoid false matches
        minister_patterns = [
            'Secretary of State',
            'Minister of State',
            'Parliamentary Under-Secretary',
            'Parliamentary Under Secretary',
            'Chancellor of the Exchequer',
            'Prime Minister',
            'Attorney General',
            'Solicitor General',
            'Chief Secretary',
            'Paymaster General',
            'Minister for',
            'Minister without Portfolio',
        ]

        # Build Q objects for OR query
        minister_q = Q()
        for pattern in minister_patterns:
            minister_q |= Q(role__icontains=pattern)

        minister_memberships = models.Membership.objects.filter(
            minister_q
        ).exclude(
            role__icontains='shadow'
        ).exclude(
            role__icontains='pps'
        )

        # Filter to current ministers only (no end_date)
        if current_only:
            minister_memberships = minister_memberships.filter(
                Q(end_date__isnull=True) | Q(end_date='')
            )

        minister_memberships = minister_memberships.values('person_id').distinct()

        minister_ids = list(minister_memberships.values_list('person_id', flat=True))

        # Get donations to ministers
        donations_qs = models.Donation.objects.filter(
            recipient_id__in=minister_ids
        ).exclude(donor__isnull=True)

        # Apply date filters
        if received_after:
            donations_qs = donations_qs.filter(received_date__gte=received_after)
        if received_before:
            donations_qs = donations_qs.filter(received_date__lte=received_before)

        # Get top ministers by total received - apply limit here
        minister_totals = donations_qs.values('recipient_id').annotate(
            total_received=Sum('value')
        ).order_by('-total_received')[:limit]

        top_minister_ids = [m['recipient_id'] for m in minister_totals]

        # Aggregate donations by donor -> minister (only for top ministers)
        connections = donations_qs.filter(
            recipient_id__in=top_minister_ids
        ).values(
            'donor_id', 'recipient_id'
        ).annotate(
            total_value=Sum('value'),
            donation_count=Count('id')
        ).filter(
            total_value__gte=min_value
        ).order_by('-total_value')

        # Build node and link sets
        nodes_dict = {}
        links = []

        # Get all unique actor IDs
        donor_ids = set(c['donor_id'] for c in connections)
        all_actor_ids = set(top_minister_ids) | donor_ids

        # Fetch all actors
        actors = {
            a.id: a for a in models.Actor.objects.filter(id__in=all_actor_ids)
        }

        # Get minister roles for display
        minister_roles = {}
        for m in models.Membership.objects.filter(
            person_id__in=top_minister_ids,
            role__icontains='minister'
        ).exclude(role__icontains='shadow').exclude(role__icontains='pps'):
            if m.person_id not in minister_roles:
                minister_roles[m.person_id] = m.role

        # Get meeting counts for ministers
        minister_meeting_counts = dict(
            models.MinisterialMeeting.objects.filter(
                minister_id__in=top_minister_ids
            ).values('minister_id').annotate(
                meeting_count=Count('id')
            ).values_list('minister_id', 'meeting_count')
        )

        # Get meeting counts for donors/organizations (as attendees)
        donor_meeting_counts = dict(
            models.MeetingAttendee.objects.filter(
                Q(actor_id__in=donor_ids) | Q(canonical_actor_id__in=donor_ids)
            ).values('actor_id').annotate(
                meeting_count=Count('meeting_id', distinct=True)
            ).values_list('actor_id', 'meeting_count')
        )
        # Also check canonical_actor_id
        canonical_meeting_counts = dict(
            models.MeetingAttendee.objects.filter(
                canonical_actor_id__in=donor_ids
            ).values('canonical_actor_id').annotate(
                meeting_count=Count('meeting_id', distinct=True)
            ).values_list('canonical_actor_id', 'meeting_count')
        )
        # Merge canonical into donor counts
        for actor_id, count in canonical_meeting_counts.items():
            if actor_id:
                donor_meeting_counts[actor_id] = donor_meeting_counts.get(actor_id, 0) + count

        # Build minister nodes
        for m in minister_totals:
            mid = m['recipient_id']
            if mid in actors:
                actor = actors[mid]
                nodes_dict[mid] = {
                    'id': mid,
                    'name': actor.name,
                    'type': 'minister',
                    'role': minister_roles.get(mid, 'Minister'),
                    'total_value': float(m['total_received']),
                    'meeting_count': minister_meeting_counts.get(mid, 0),
                    'url': f'/person/{mid}/'
                }

        # Build donor nodes and links
        for conn in connections:
            donor_id = conn['donor_id']
            recipient_id = conn['recipient_id']

            if donor_id in actors and recipient_id in nodes_dict:
                donor = actors[donor_id]

                # Add donor node if not exists
                if donor_id not in nodes_dict:
                    # Determine donor type
                    try:
                        donor_type = 'organization' if hasattr(donor, 'organization') else 'person'
                    except:
                        donor_type = 'donor'

                    nodes_dict[donor_id] = {
                        'id': donor_id,
                        'name': donor.name,
                        'type': donor_type,
                        'total_value': 0,
                        'donation_count': 0,
                        'meeting_count': donor_meeting_counts.get(donor_id, 0),
                        'url': f'/actor/{donor_id}/'
                    }

                # Update donor total
                nodes_dict[donor_id]['total_value'] += float(conn['total_value'])
                nodes_dict[donor_id]['donation_count'] = nodes_dict[donor_id].get('donation_count', 0) + conn['donation_count']

                # Add donation link
                links.append({
                    'source': donor_id,
                    'target': recipient_id,
                    'value': float(conn['total_value']),
                    'count': conn['donation_count'],
                    'link_type': 'donation'
                })

        # ============================================
        # Add meeting attendees as nodes and links
        # ============================================

        # Get all meetings for top ministers
        minister_meetings = models.MinisterialMeeting.objects.filter(
            minister_id__in=top_minister_ids
        )

        # Get meeting attendees with counts, ordered by meeting count
        attendee_data = models.MeetingAttendee.objects.filter(
            meeting__minister_id__in=top_minister_ids
        ).values(
            'meeting__minister_id'
        ).annotate(
            # Use canonical_actor if available, else actor
            effective_actor_id=Case(
                When(canonical_actor_id__isnull=False, then=F('canonical_actor_id')),
                default=F('actor_id'),
                output_field=IntegerField()
            )
        ).values(
            'meeting__minister_id', 'effective_actor_id'
        ).annotate(
            meeting_count=Count('meeting_id', distinct=True)
        ).filter(
            meeting_count__gte=min_meetings  # Filter by minimum meetings
        ).order_by('-meeting_count')

        # Collect unique attendee IDs
        attendee_ids = set()
        meeting_links_data = []
        for item in attendee_data:
            attendee_ids.add(item['effective_actor_id'])
            meeting_links_data.append({
                'attendee_id': item['effective_actor_id'],
                'minister_id': item['meeting__minister_id'],
                'meeting_count': item['meeting_count']
            })

        # Remove ministers from attendee list (don't want self-links)
        attendee_ids = attendee_ids - set(top_minister_ids)

        # Fetch attendee actors
        attendee_actors = {
            a.id: a for a in models.Actor.objects.filter(id__in=attendee_ids)
        }

        # Add attendee nodes
        for attendee_id in attendee_ids:
            if attendee_id in attendee_actors and attendee_id not in nodes_dict:
                actor = attendee_actors[attendee_id]
                try:
                    actor_type = 'organization' if hasattr(actor, 'organization') else 'person'
                except:
                    actor_type = 'attendee'

                # Count total meetings for this attendee
                total_meetings = sum(
                    m['meeting_count'] for m in meeting_links_data
                    if m['attendee_id'] == attendee_id
                )

                nodes_dict[attendee_id] = {
                    'id': attendee_id,
                    'name': actor.name,
                    'type': actor_type,
                    'total_value': 0,  # No donations
                    'donation_count': 0,
                    'meeting_count': total_meetings,
                    'url': f'/actor/{attendee_id}/'
                }

        # Add meeting links
        for ml in meeting_links_data:
            attendee_id = ml['attendee_id']
            minister_id = ml['minister_id']

            # Only add if both nodes exist and not self-link
            if attendee_id in nodes_dict and minister_id in nodes_dict and attendee_id != minister_id:
                links.append({
                    'source': attendee_id,
                    'target': minister_id,
                    'value': ml['meeting_count'] * 1000,  # Scale for visibility
                    'count': ml['meeting_count'],
                    'link_type': 'meeting'
                })

        # Convert nodes dict to list
        nodes = list(nodes_dict.values())

        # Calculate stats
        donation_links = [l for l in links if l.get('link_type') == 'donation']
        meeting_links = [l for l in links if l.get('link_type') == 'meeting']

        # Count nodes by connection type
        nodes_with_donations = set()
        nodes_with_meetings = set()
        for l in donation_links:
            nodes_with_donations.add(l['source'])
        for l in meeting_links:
            nodes_with_meetings.add(l['source'])

        stats = {
            'total_ministers': len([n for n in nodes if n['type'] == 'minister']),
            'total_donors': len(nodes_with_donations),
            'total_attendees': len(nodes_with_meetings - nodes_with_donations),  # Only meeting attendees
            'total_connections': len(links),
            'donation_connections': len(donation_links),
            'meeting_connections': len(meeting_links),
            'total_value': sum(l['value'] for l in donation_links),
        }

        return Response({
            'nodes': nodes,
            'links': links,
            'stats': stats
        })


class PoliticianViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v2/politicians/

    Returns a paginated list of politicians with current status annotations.
    """
    serializer_class = serializers.PoliticianSerializer
    filterset_class = filters.PoliticianFilter
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        from django.utils import timezone
        from django.db.models import Prefetch

        today = timezone.now().date().isoformat()

        # 1. Base Query: People with political memberships (MPs, Lords)
        # We look for memberships in organizations classified as 'Legislature'
        # (House of Commons, House of Lords, Scottish Parliament, Senedd, NI Assembly)
        # This covers almost all politicians including Ministers (who are usually MPs/Lords)
        qs = models.Person.objects.filter(
            memberships__organization__classification='Legislature'
        ).distinct().order_by('name')

        # 2. Prefetch "Current" memberships for serialization
        # This avoids N+1 queries when determining current party/role
        current_memberships = models.Membership.objects.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today),
            start_date__lte=today
        ).select_related('organization', 'post', 'on_behalf_of')

        qs = qs.prefetch_related(
            Prefetch('memberships', queryset=current_memberships, to_attr='active_memberships')
        )
        
        return qs


class PartyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v2/parties/

    Returns a list of political parties with current MP/Lord counts.
    """
    serializer_class = serializers.PoliticalPartySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None  # No pagination for party lists (usually < 20)

    def get_queryset(self):
        # Get IDs for House of Commons and House of Lords
        # Organization inherits name from Actor via actor_ptr
        commons_id = models.Organization.objects.filter(
            name='House of Commons'
        ).values_list('actor_ptr_id', flat=True).first()
        lords_id = models.Organization.objects.filter(
            name='House of Lords'
        ).values_list('actor_ptr_id', flat=True).first()

        # Return parties that have been used as on_behalf_of in Legislature memberships
        # This captures all parliamentary parties, not just those classified as 'Political Party'
        return models.Organization.objects.filter(
            Q(classification='Political Party') |
            Q(memberships_on_behalf_of__organization__classification='Legislature')
        ).distinct().annotate(
            # Count current MPs: memberships in House of Commons on_behalf_of this party
            # Current = end_date is empty string, NULL, or >= today (dates stored as YYYY-MM-DD strings)
            mp_count=Count(
                'memberships_on_behalf_of',
                filter=Q(
                    memberships_on_behalf_of__organization_id=commons_id
                ) & (
                    Q(memberships_on_behalf_of__end_date='') |
                    Q(memberships_on_behalf_of__end_date__isnull=True) |
                    Q(memberships_on_behalf_of__end_date__gte='2026-01-01')
                ),
                distinct=True
            ),
            # Count current Lords: memberships in House of Lords on_behalf_of this party
            lord_count=Count(
                'memberships_on_behalf_of',
                filter=Q(
                    memberships_on_behalf_of__organization_id=lords_id
                ) & (
                    Q(memberships_on_behalf_of__end_date='') |
                    Q(memberships_on_behalf_of__end_date__isnull=True) |
                    Q(memberships_on_behalf_of__end_date__gte='2026-01-01')
                ),
                distinct=True
            )
        ).order_by('-mp_count', '-lord_count')