"""
API v2 Views

Provides aggregate endpoints and actor detail endpoints with filtering and caching.
"""

import logging
import time
from decimal import Decimal
from django.core.cache import cache
from django.db.models import Sum, Count, Q, Min, Max, Case, When, F, IntegerField, DecimalField, Prefetch, Subquery, OuterRef, Value
from django.db.models.functions import Coalesce
from rest_framework import generics, viewsets, views, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

logger = logging.getLogger(__name__)

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
        aggregated = queryset.annotate(
            effective_donor_id=Coalesce('canonical_donor_id', 'donor_id')
        ).values('effective_donor_id').annotate(
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
            donor_ids = [item['effective_donor_id'] for item in page]

            # Fetch only the actors we need (e.g., 10-100, not 21k)
            actors_dict = {
                actor.id: actor
                for actor in models.Actor.objects.filter(id__in=donor_ids)
            }

            # Check which donors are lobbying clients (have Consultancy records)
            # Use effective_client_id here too? 
            # ideally yes, but Consultancy model changes needed for full consistency.
            # For now, check based on the resolved donor IDs.
            lobbying_donor_ids = set(
                models.Consultancy.objects.annotate(
                    effective_client_id=Coalesce('canonical_client_id', 'client_id')
                ).filter(effective_client_id__in=donor_ids)
                .values_list('effective_client_id', flat=True)
                .distinct()
            )

            # Build result list with actor objects
            results = []
            for item in page:
                donor_id = item['effective_donor_id']
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
        donor_ids = [item['effective_donor_id'] for item in aggregated_qs]
        actors_dict = {
            actor.id: actor
            for actor in models.Actor.objects.filter(id__in=donor_ids)
        }
        lobbying_donor_ids = set(
            models.Consultancy.objects.annotate(
                effective_client_id=Coalesce('canonical_client_id', 'client_id')
            ).filter(effective_client_id__in=donor_ids)
            .values_list('effective_client_id', flat=True)
            .distinct()
        )
        results = [
            {
                'actor': actors_dict[item['effective_donor_id']],
                'total_donated': item['total_donated'] or 0,
                'donation_count': item['donation_count'],
                'is_lobbying_client': item['effective_donor_id'] in lobbying_donor_ids
            }
            for item in aggregated_qs
            if item['effective_donor_id'] in actors_dict
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
        aggregated = queryset.annotate(
            effective_recipient_id=Coalesce('canonical_recipient_id', 'recipient_id')
        ).values('effective_recipient_id').annotate(
            total_received=Sum('value'),
            donation_count=Count('id')
        ).order_by('-total_received')

        return aggregated

    def _get_party_memberships(self, person_ids):
        """
        Look up current party for a list of person IDs.
        Party comes from Membership.on_behalf_of where the membership is active.
        Returns dict mapping person_id -> party Organization (or None).
        """
        from datafetch.models import Membership

        # Get memberships with on_behalf_of (party) set, prefer current ones
        # First try to find current memberships (no end_date)
        memberships = Membership.objects.filter(
            person_id__in=person_ids,
            on_behalf_of__isnull=False,
            on_behalf_of__classification='Political Party'
        ).select_related('on_behalf_of').order_by('person_id', '-start_date')

        # Build dict - take the most recent membership for each person
        result = {}
        for m in memberships:
            if m.person_id not in result:
                result[m.person_id] = m.on_behalf_of

        return result

    def list(self, request, *args, **kwargs):
        """
        Override list to handle aggregation and pagination efficiently. Cached 1hr.

        Key optimization: Only fetch Actor objects for the paginated subset.
        """
        from api.v2.cache_utils import make_aggregate_cache_key, AGGREGATE_CACHE_TTL

        cache_key = make_aggregate_cache_key('top_recipients', dict(request.query_params))
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        # Get aggregated queryset (still a QuerySet, not materialized)
        aggregated_qs = self.get_queryset()

        # Apply pagination to the QuerySet BEFORE fetching actors
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(aggregated_qs, request, view=self)

        # Now fetch Actor objects only for the paginated results
        if page is not None:
            # Extract recipient_ids from the paginated subset only
            recipient_ids = [item['effective_recipient_id'] for item in page]

            # Fetch only the actors we need (with polymorphic_ctype to avoid N+1)
            actors_dict = {
                actor.id: actor
                for actor in models.Actor.objects.filter(
                    id__in=recipient_ids
                ).select_related('polymorphic_ctype')
            }

            # Identify person IDs and fetch their party memberships
            person_ids = [
                actor_id for actor_id, actor in actors_dict.items()
                if actor.polymorphic_ctype.model == 'person'
            ]
            party_dict = self._get_party_memberships(person_ids) if person_ids else {}

            # Build result list with actor objects
            results = []
            for item in page:
                recipient_id = item['effective_recipient_id']
                if recipient_id in actors_dict:
                    results.append({
                        'actor': actors_dict[recipient_id],
                        'total_received': item['total_received'] or 0,
                        'donation_count': item['donation_count'],
                        'current_party': party_dict.get(recipient_id)
                    })

            serializer = self.get_serializer(results, many=True)
            response_data = paginator.get_paginated_response(serializer.data).data
            cache.set(cache_key, response_data, AGGREGATE_CACHE_TTL)
            return Response(response_data)

        # Fallback for no pagination
        recipient_ids = [item['effective_recipient_id'] for item in aggregated_qs]
        actors_dict = {
            actor.id: actor
            for actor in models.Actor.objects.filter(
                id__in=recipient_ids
            ).select_related('polymorphic_ctype')
        }
        person_ids = [
            actor_id for actor_id, actor in actors_dict.items()
            if actor.polymorphic_ctype.model == 'person'
        ]
        party_dict = self._get_party_memberships(person_ids) if person_ids else {}

        results = [
            {
                'actor': actors_dict[item['effective_recipient_id']],
                'total_received': item['total_received'] or 0,
                'donation_count': item['donation_count'],
                'current_party': party_dict.get(item['effective_recipient_id'])
            }
            for item in aggregated_qs
            if item['effective_recipient_id'] in actors_dict
        ]
        serializer = self.get_serializer(results, many=True)
        cache.set(cache_key, serializer.data, AGGREGATE_CACHE_TTL)
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

        Uses canonical recipient resolution to properly aggregate donations
        to parties that may have multiple actor records.

        Returns: party, total_received, donation_count, donor_count
        """
        # Start with all donations that have recipients
        queryset = models.Donation.objects.exclude(recipient__isnull=True)

        # Apply date filters
        filterset = filters.DonationFilterSet(
            self.request.query_params,
            queryset=queryset
        )
        queryset = filterset.qs

        # Get IDs of all Political Party organizations — used as SQL filter
        party_ids = list(
            models.Organization.objects.filter(
                classification='Political Party'
            ).values_list('id', flat=True)
        )

        # Annotate with effective recipient ID and filter to parties in SQL
        queryset = queryset.annotate(
            effective_recipient_id=Coalesce('canonical_recipient_id', 'recipient_id')
        ).filter(
            effective_recipient_id__in=party_ids
        )

        # Aggregate by party — already filtered, no Python post-filter needed
        aggregated = queryset.values('effective_recipient_id').annotate(
            total_received=Sum('value'),
            donation_count=Count('id'),
            donor_count=Count('donor_id', distinct=True)
        ).order_by('-total_received')

        return aggregated

    def list(self, request, *args, **kwargs):
        """Handle pagination and actor fetching. Cached 1hr."""
        from api.v2.cache_utils import make_aggregate_cache_key, AGGREGATE_CACHE_TTL

        cache_key = make_aggregate_cache_key('party_donations', dict(request.query_params))
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        aggregated_qs = self.get_queryset()
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(list(aggregated_qs), request, view=self)

        if page is not None:
            # Fetch party actors for paginated results only
            party_ids = [item['effective_recipient_id'] for item in page]
            parties_dict = {
                actor.id: actor
                for actor in models.Actor.objects.filter(id__in=party_ids)
            }

            results = []
            for item in page:
                party_id = item['effective_recipient_id']
                if party_id in parties_dict:
                    results.append({
                        'party': parties_dict[party_id],
                        'total_received': item['total_received'] or 0,
                        'donation_count': item['donation_count'],
                        'donor_count': item['donor_count'],
                    })

            serializer = self.get_serializer(results, many=True)
            response_data = paginator.get_paginated_response(serializer.data).data
            cache.set(cache_key, response_data, AGGREGATE_CACHE_TTL)
            return Response(response_data)

        # Fallback without pagination
        party_ids = [item['effective_recipient_id'] for item in aggregated_qs]
        parties_dict = {
            actor.id: actor
            for actor in models.Actor.objects.filter(id__in=party_ids)
        }
        results = [
            {
                'party': parties_dict[item['effective_recipient_id']],
                'total_received': item['total_received'] or 0,
                'donation_count': item['donation_count'],
                'donor_count': item['donor_count'],
            }
            for item in aggregated_qs
            if item['effective_recipient_id'] in parties_dict
        ]
        serializer = self.get_serializer(results, many=True)
        cache.set(cache_key, serializer.data, AGGREGATE_CACHE_TTL)
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

        Uses set intersection of effective (canonical) actors.
        """
        # Get set of unique effective donors (with filters applied later for sums, but here for existence)
        # Use unfiltered base for existence check first? Or filtered?
        # Usually dual influence means "is a donor (ever) AND is a client (ever)".
        # But here we filter donations by date.
        
        # Base querysets
        donations_all = models.Donation.objects.exclude(donor__isnull=True)
        consultancies_all = models.Consultancy.objects.exclude(client__isnull=True)

        effective_donors = set(donations_all.annotate(
            effective_donor_id=Coalesce('canonical_donor_id', 'donor_id')
        ).values_list('effective_donor_id', flat=True).distinct())

        effective_clients = set(consultancies_all.annotate(
            effective_client_id=Coalesce('canonical_client_id', 'client_id')
        ).values_list('effective_client_id', flat=True).distinct())

        # Intersection
        actor_ids = list(effective_donors.intersection(effective_clients))

        # Now aggregate their activity
        # Filter donations by these actors (as effective donor)
        donation_queryset = models.Donation.objects.annotate(
            effective_donor_id=Coalesce('canonical_donor_id', 'donor_id')
        ).filter(
            effective_donor_id__in=actor_ids
        )

        # Apply date filters from query parameters
        filterset = filters.DonationFilterSet(
            self.request.query_params,
            queryset=donation_queryset
        )
        donation_queryset = filterset.qs

        donation_agg = donation_queryset.values('effective_donor_id').annotate(
            total_donated=Sum('value'),
            donation_count=Count('id'),
            first_donation=Min('received_date'),
            last_donation=Max('received_date')
        )

        # Aggregate consultancies
        consultancy_agg = models.Consultancy.objects.annotate(
            effective_client_id=Coalesce('canonical_client_id', 'client_id')
        ).filter(
            effective_client_id__in=actor_ids
        ).values('effective_client_id').annotate(
            lobbying_count=Count('id'),
            first_consultancy=Min('start_date'),
            last_consultancy=Max('start_date')
        )

        # Build lookup dicts
        donation_data = {item['effective_donor_id']: item for item in donation_agg}
        consultancy_data = {item['effective_client_id']: item for item in consultancy_agg}

        # Combine data
        results = []
        for actor_id in actor_ids:
            don_data = donation_data.get(actor_id, {})
            cons_data = consultancy_data.get(actor_id, {})

            if don_data and cons_data:
                # Calculate activity span
                first_donation = don_data.get('first_donation')
                last_donation = don_data.get('last_donation')
                first_consultancy = cons_data.get('first_consultancy')
                last_consultancy = cons_data.get('last_consultancy')

                results.append({
                    'actor_id': actor_id,
                    'total_donated': don_data.get('total_donated', 0),
                    'donation_count': don_data.get('donation_count', 0),
                    'lobbying_count': cons_data.get('lobbying_count', 0),
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


class TopLobbyingClientsView(generics.ListAPIView):
    """
    GET /api/v2/aggregates/top-lobbying-clients/

    Returns organizations ranked by number of lobbying agencies they hire.

    Query Parameters:
    - limit: Number of results (default: 50, max: 200)
    - offset: Pagination offset

    Example:
        GET /api/v2/aggregates/top-lobbying-clients/?limit=10
    """
    serializer_class = serializers.TopLobbyingClientSerializer
    pagination_class = pagination.AggregatePagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """
        Aggregate consultancies by effective client, counting unique agencies.
        """
        # Group by effective client (using canonical_client if available)
        aggregated_qs = models.Consultancy.objects.exclude(
            client__isnull=True
        ).annotate(
            effective_client_id=Coalesce('canonical_client_id', 'client_id')
        ).values('effective_client_id').annotate(
            agency_count=Count('agency_id', distinct=True)
        ).order_by('-agency_count')

        return aggregated_qs

    def list(self, request, *args, **kwargs):
        """Handle pagination and actor fetching. Cached 1hr."""
        from api.v2.cache_utils import make_aggregate_cache_key, AGGREGATE_CACHE_TTL

        cache_key = make_aggregate_cache_key('top_lobbying_clients', dict(request.query_params))
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        aggregated_qs = self.get_queryset()

        # Manual pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(list(aggregated_qs), request, view=self)

        if page is not None:
            client_ids = [item['effective_client_id'] for item in page]
            actors_dict = {
                actor.id: actor
                for actor in models.Actor.objects.filter(id__in=client_ids)
            }

            # Batch-fetch agencies for all clients in one query
            agency_rows = models.Consultancy.objects.filter(
                Q(client_id__in=client_ids) | Q(canonical_client_id__in=client_ids)
            ).exclude(agency__isnull=True).annotate(
                effective_client_id=Coalesce('canonical_client_id', 'client_id')
            ).values(
                'effective_client_id', 'agency_id', 'agency__name'
            ).annotate(
                count=Count('id')
            ).order_by('effective_client_id', '-count')

            # Group by client, keeping top 10 agencies per client as {id, name} objects
            client_agencies = {}
            for row in agency_rows:
                cid = row['effective_client_id']
                if cid not in client_agencies:
                    client_agencies[cid] = []
                if len(client_agencies[cid]) < 10 and row['agency__name']:
                    client_agencies[cid].append({
                        'id': row['agency_id'],
                        'name': row['agency__name'],
                    })

            results = []
            for item in page:
                client_id = item['effective_client_id']
                if client_id in actors_dict:
                    results.append({
                        'actor': actors_dict[client_id],
                        'agency_count': item['agency_count'],
                        'agencies': client_agencies.get(client_id, []),
                    })

            serializer = self.get_serializer(results, many=True)
            response_data = paginator.get_paginated_response(serializer.data).data
            cache.set(cache_key, response_data, AGGREGATE_CACHE_TTL)
            return Response(response_data)

        # Fallback without pagination
        client_ids = [item['effective_client_id'] for item in aggregated_qs]
        actors_dict = {
            actor.id: actor
            for actor in models.Actor.objects.filter(id__in=client_ids)
        }
        results = [
            {
                'actor': actors_dict[item['effective_client_id']],
                'agency_count': item['agency_count'],
                'agencies': [],
            }
            for item in aggregated_qs
            if item['effective_client_id'] in actors_dict
        ]
        serializer = self.get_serializer(results, many=True)
        cache.set(cache_key, serializer.data, AGGREGATE_CACHE_TTL)
        return Response(serializer.data)


class DepartmentMeetingsView(generics.ListAPIView):
    """
    GET /api/v2/aggregates/department-meetings/

    Returns government departments ranked by number of ministerial meetings,
    with top attendees for each department.

    Query Parameters:
    - limit: Number of departments to return (default: 10, max: 50)
    - offset: Pagination offset
    - date_after: Filter meetings from this date (YYYY-MM-DD)
    - date_before: Filter meetings up to this date (YYYY-MM-DD)
    - top_attendees: Number of top attendees per department (default: 3, max: 10)

    Example:
        GET /api/v2/aggregates/department-meetings/?limit=5&top_attendees=3
    """
    serializer_class = serializers.DepartmentMeetingsSerializer
    pagination_class = pagination.AggregatePagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """
        Aggregate meetings by department, counting unique meetings.
        """
        # Get query parameters for date filtering
        date_after = self.request.query_params.get('date_after')
        date_before = self.request.query_params.get('date_before')

        # Base queryset - all meetings
        queryset = models.MinisterialMeeting.objects.all()

        # Apply date filters
        if date_after:
            queryset = queryset.filter(meeting_date__gte=date_after)
        if date_before:
            queryset = queryset.filter(meeting_date__lte=date_before)

        # Aggregate by department
        aggregated = queryset.values('department_id').annotate(
            total_meetings=Count('id', distinct=True)
        ).order_by('-total_meetings')

        return aggregated

    def list(self, request, *args, **kwargs):
        """Handle pagination, department fetching, and top attendees. Cached 1hr."""
        from api.v2.cache_utils import make_aggregate_cache_key, AGGREGATE_CACHE_TTL

        cache_key = make_aggregate_cache_key('department_meetings', dict(request.query_params))
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        aggregated_qs = self.get_queryset()

        # Get parameters
        date_after = request.query_params.get('date_after')
        date_before = request.query_params.get('date_before')
        top_attendees_count = min(int(request.query_params.get('top_attendees', 3)), 10)

        # Manual pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(list(aggregated_qs), request, view=self)

        if page is not None:
            dept_ids = [item['department_id'] for item in page]

            # Fetch department actors
            departments_dict = {
                d.id: d for d in models.Actor.objects.filter(id__in=dept_ids)
            }

            # Get top attendees for each department
            # Query attendees grouped by (department, effective_actor)
            attendee_queryset = models.MeetingAttendee.objects.exclude(actor__isnull=True)
            if date_after:
                attendee_queryset = attendee_queryset.filter(meeting__meeting_date__gte=date_after)
            if date_before:
                attendee_queryset = attendee_queryset.filter(meeting__meeting_date__lte=date_before)

            attendee_breakdown = attendee_queryset.filter(
                meeting__department_id__in=dept_ids
            ).annotate(
                effective_actor_id=Coalesce('canonical_actor_id', 'actor_id')
            ).values(
                'meeting__department_id', 'effective_actor_id'
            ).annotate(
                meeting_count=Count('meeting_id', distinct=True)
            ).order_by('meeting__department_id', '-meeting_count')

            # Build dict: department_id -> [{actor_id, meeting_count}, ...]
            attendees_by_dept = {}
            for item in attendee_breakdown:
                did = item['meeting__department_id']
                if did not in attendees_by_dept:
                    attendees_by_dept[did] = []
                # Only keep top N attendees per department
                if len(attendees_by_dept[did]) < top_attendees_count:
                    attendees_by_dept[did].append({
                        'actor_id': item['effective_actor_id'],
                        'meeting_count': item['meeting_count']
                    })

            # Fetch all attendee actors
            all_actor_ids = set()
            for attendee_list in attendees_by_dept.values():
                for a in attendee_list:
                    all_actor_ids.add(a['actor_id'])

            actors_dict = {
                a.id: a for a in models.Actor.objects.filter(id__in=all_actor_ids)
            }

            # Build results
            results = []
            for item in page:
                dept_id = item['department_id']
                if dept_id in departments_dict:
                    # Build top attendees with actor objects
                    top_attendees = []
                    for a in attendees_by_dept.get(dept_id, []):
                        if a['actor_id'] in actors_dict:
                            top_attendees.append({
                                'actor': actors_dict[a['actor_id']],
                                'meeting_count': a['meeting_count']
                            })

                    results.append({
                        'department': departments_dict[dept_id],
                        'total_meetings': item['total_meetings'],
                        'top_attendees': top_attendees
                    })

            serializer = self.get_serializer(results, many=True)
            response_data = paginator.get_paginated_response(serializer.data).data
            cache.set(cache_key, response_data, AGGREGATE_CACHE_TTL)
            return Response(response_data)

        # Fallback without pagination
        dept_ids = [item['department_id'] for item in aggregated_qs]
        departments_dict = {
            d.id: d for d in models.Actor.objects.filter(id__in=dept_ids)
        }
        results = [
            {
                'department': departments_dict[item['department_id']],
                'total_meetings': item['total_meetings'],
                'top_attendees': []
            }
            for item in aggregated_qs
            if item['department_id'] in departments_dict
        ]
        serializer = self.get_serializer(results, many=True)
        cache.set(cache_key, serializer.data, AGGREGATE_CACHE_TTL)
        return Response(serializer.data)


# ===========================
# Actor Detail Endpoints
# ===========================

class ActorDetailView(generics.RetrieveAPIView):
    """
    GET /api/v2/actors/{id}/

    Returns detailed information about a specific actor (person or organization).

    Includes aggregated relationship counts and totals.

    Cached in Redis for 1 hour per actor ID. Pass ?bust_cache=1 to force refresh.
    """
    queryset = models.Actor.objects.all()
    serializer_class = serializers.ActorDetailSerializer
    permission_classes = [permissions.AllowAny]

    CACHE_TTL = 3600  # 1 hour

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to add Redis caching."""
        pk = self.kwargs['pk']
        cache_key = f'actor_detail:{pk}'
        bust = request.query_params.get('bust_cache', '').strip()

        if not bust:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug('Cache HIT for %s', cache_key)
                return Response(cached)

        logger.debug('Cache MISS for %s — running annotated query', cache_key)
        response = super().retrieve(request, *args, **kwargs)

        # Cache the serialized data (not the Response object)
        cache.set(cache_key, response.data, self.CACHE_TTL)
        return response

    def get_queryset(self):
        """Annotate with relationship aggregates."""
        from datafetch.models.influence_mapping import MeetingAttendee

        # Subqueries to avoid cartesian joins with the main annotations
        unique_donors_sq = models.Donation.objects.filter(
            recipient_id=OuterRef('pk')
        ).values('recipient_id').annotate(
            cnt=Count('donor', distinct=True)
        ).values('cnt')

        # For ministers: unique orgs that attended their meetings
        unique_meeting_orgs_sq = MeetingAttendee.objects.filter(
            meeting__minister_id=OuterRef('pk')
        ).values('meeting__minister_id').annotate(
            cnt=Count('actor', distinct=True)
        ).values('cnt')

        # For orgs: count of meetings attended as an attendee
        meeting_attendance_count_sq = MeetingAttendee.objects.filter(
            actor_id=OuterRef('pk')
        ).order_by().values('actor_id').annotate(
            cnt=Count('meeting', distinct=True)
        ).values('cnt')

        # For orgs: unique ministers met (via meetings attended)
        unique_ministers_met_sq = MeetingAttendee.objects.filter(
            actor_id=OuterRef('pk')
        ).order_by().values('actor_id').annotate(
            cnt=Count('meeting__minister', distinct=True)
        ).values('cnt')

        # All annotations use Subqueries to avoid cartesian joins between
        # donated_to and received_donations_from (27k × 288 = 8M rows for Conservative Party)
        donations_made_sq = models.Donation.objects.filter(
            donor_id=OuterRef('pk')
        ).order_by().values('donor_id').annotate(
            cnt=Count('id')
        ).values('cnt')

        donations_received_sq = models.Donation.objects.filter(
            recipient_id=OuterRef('pk')
        ).order_by().values('recipient_id').annotate(
            cnt=Count('id')
        ).values('cnt')

        total_donated_sq = models.Donation.objects.filter(
            donor_id=OuterRef('pk')
        ).order_by().values('donor_id').annotate(
            total=Sum('value')
        ).values('total')

        total_received_sq = models.Donation.objects.filter(
            recipient_id=OuterRef('pk')
        ).order_by().values('recipient_id').annotate(
            total=Sum('value')
        ).values('total')

        from datafetch.models.influence_mapping import Consultancy
        consultancies_as_client_sq = Consultancy.objects.filter(
            client_id=OuterRef('pk')
        ).order_by().values('client_id').annotate(
            cnt=Count('agency', distinct=True)
        ).values('cnt')

        consultancies_as_agency_sq = Consultancy.objects.filter(
            agency_id=OuterRef('pk')
        ).order_by().values('agency_id').annotate(
            cnt=Count('client', distinct=True)
        ).values('cnt')

        return models.Actor.objects.annotate(
            donations_made_count=Coalesce(Subquery(donations_made_sq, output_field=IntegerField()), 0),
            donations_received_count=Coalesce(Subquery(donations_received_sq, output_field=IntegerField()), 0),
            total_donated=Coalesce(Subquery(total_donated_sq, output_field=DecimalField()), Decimal('0')),
            total_received=Coalesce(Subquery(total_received_sq, output_field=DecimalField()), Decimal('0')),
            consultancies_as_client=Coalesce(Subquery(consultancies_as_client_sq, output_field=IntegerField()), 0),
            consultancies_as_agency=Coalesce(Subquery(consultancies_as_agency_sq, output_field=IntegerField()), 0),
            unique_donors_count=Coalesce(Subquery(unique_donors_sq, output_field=IntegerField()), 0),
            unique_meeting_orgs_count=Coalesce(Subquery(unique_meeting_orgs_sq, output_field=IntegerField()), 0),
            meeting_attendance_count=Coalesce(Subquery(meeting_attendance_count_sq, output_field=IntegerField()), 0),
            unique_ministers_met_count=Coalesce(Subquery(unique_ministers_met_sq, output_field=IntegerField()), 0),
        )


class FundingSummaryView(views.APIView):
    """
    GET /api/v2/actors/{id}/funding-summary/

    Pre-aggregated funding overview for actors that receive donations (parties, politicians).
    Designed for the party profile page hero section.

    Returns:
    - total_received: Total donation value
    - donation_count: Total number of donations
    - unique_donors: Count of distinct donors
    - yearly_totals: [{year, total, count, avg_donation}] — most recent first
    - top_donors: [{id, name, total, count, actor_type}] — top 20 by value
    - category_breakdown: [{category, total, count}] — by donation type
    - largest_donation: {value, donor_name, donor_id, date}

    Cached in Redis for 1 hour. Pass ?bust_cache=1 to force refresh.
    """
    permission_classes = [permissions.AllowAny]

    CACHE_TTL = 3600  # 1 hour — data only changes on import

    def get(self, request, pk):
        cache_key = f'funding_summary:{pk}'
        bust = request.query_params.get('bust_cache', '').strip()

        if not bust:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug('Cache HIT for %s', cache_key)
                return Response(cached)

        logger.debug('Cache MISS for %s — computing funding summary', cache_key)
        t0 = time.monotonic()

        # Verify actor exists
        if not models.Actor.objects.filter(pk=pk).exists():
            return Response({'error': 'Actor not found'}, status=404)

        # Base queryset: all donations received by this actor
        base_qs = models.Donation.objects.filter(recipient_id=pk)

        # --- Totals (single query with aggregation) ---
        totals = base_qs.aggregate(
            total_received=Coalesce(Sum('value'), Decimal('0')),
            donation_count=Count('id'),
            unique_donors=Count('donor', distinct=True),
        )

        # --- Yearly totals (single query) ---
        from django.db.models.functions import ExtractYear, Cast
        from django.db.models import CharField
        yearly_qs = base_qs.annotate(
            effective_date=Coalesce('accepted_date', 'reported_date', 'received_date'),
        ).exclude(effective_date__isnull=True).annotate(
            year=Cast(ExtractYear('effective_date'), output_field=CharField()),
        ).values('year').annotate(
            total=Sum('value'),
            count=Count('id'),
            unique_donors=Count('donor', distinct=True),
        ).order_by('-year')

        yearly_totals = []
        for row in yearly_qs:
            year_data = {
                'year': row['year'],
                'total': str(row['total'] or 0),
                'count': row['count'],
                'unique_donors': row['unique_donors'],
                'avg_donation': str(round(row['total'] / row['count'], 2)) if row['count'] else '0',
            }
            yearly_totals.append(year_data)

        # Per-year top donors (top 5 per year, single query)
        from django.db.models.functions import Coalesce as CoalesceFunc
        yearly_donors_qs = base_qs.annotate(
            effective_date=Coalesce('accepted_date', 'reported_date', 'received_date'),
        ).exclude(effective_date__isnull=True).annotate(
            year=Cast(ExtractYear('effective_date'), output_field=CharField()),
        ).values('year', 'donor_id', 'donor__name').annotate(
            total=Sum('value'),
            count=Count('id'),
        ).order_by('year', '-total')

        # Group by year, take top 5 per year
        yearly_top_donors: dict = {}
        for row in yearly_donors_qs:
            yr = row['year']
            if yr not in yearly_top_donors:
                yearly_top_donors[yr] = []
            if len(yearly_top_donors[yr]) < 5:
                yearly_top_donors[yr].append({
                    'id': row['donor_id'],
                    'name': row['donor__name'] or 'Unknown',
                    'total': str(row['total'] or 0),
                    'count': row['count'],
                })

        # Attach to yearly_totals
        for yt in yearly_totals:
            yt['top_donors'] = yearly_top_donors.get(yt['year'], [])

        # --- Top private donors (exclude public funds and union funding) ---
        from datafetch.models.models import Organization as OrgModel
        union_ids = set(OrgModel.objects.filter(classification='Trade Union').values_list('actor_ptr_id', flat=True))
        private_qs = base_qs.exclude(donation_type='Public Funds').exclude(donor_id__in=union_ids)
        top_donors_qs = private_qs.exclude(
            donor__isnull=True
        ).annotate(
            effective_donor_id=Coalesce('canonical_donor_id', 'donor_id')
        ).values('effective_donor_id').annotate(
            total=Sum('value'),
            count=Count('id'),
        ).order_by('-total')[:20]

        # Fetch actor details for the top 20 only
        donor_ids = [row['effective_donor_id'] for row in top_donors_qs]
        donor_actors = {
            a.id: a
            for a in models.Actor.objects.filter(id__in=donor_ids).select_related('polymorphic_ctype')
        }

        # Check if these donors also fund individual MPs/members of this party
        # Find people who are members of this party (on_behalf_of)
        party_mp_ids = set(
            models.Membership.objects.filter(on_behalf_of_id=pk)
            .values_list('person_id', flat=True)
        )
        mp_funding = {}
        if party_mp_ids and donor_ids:
            mp_donations = models.Donation.objects.filter(
                donor_id__in=donor_ids,
                recipient_id__in=party_mp_ids,
            ).values('donor_id').annotate(
                to_mps_total=Sum('value'),
                mps_funded=Count('recipient_id', distinct=True),
            )
            mp_funding = {
                r['donor_id']: {'total': float(r['to_mps_total'] or 0), 'count': r['mps_funded']}
                for r in mp_donations
            }

        top_donors = []
        for row in top_donors_qs:
            did = row['effective_donor_id']
            actor = donor_actors.get(did)
            if actor:
                entry = {
                    'id': actor.id,
                    'name': actor.name,
                    'total': str(row['total'] or 0),
                    'count': row['count'],
                    'actor_type': actor.polymorphic_ctype.model,
                }
                mp_data = mp_funding.get(did)
                if mp_data and mp_data['total'] > 0:
                    entry['to_party_mps'] = str(mp_data['total'])
                    entry['mps_funded'] = mp_data['count']
                top_donors.append(entry)

        # --- Public funds summary ---
        public_qs = base_qs.filter(donation_type='Public Funds')
        public_funds_totals = public_qs.aggregate(
            total=Coalesce(Sum('value'), Decimal('0')),
            count=Count('id'),
            sources=Count('donor', distinct=True),
        )
        public_funds_top = list(
            public_qs.exclude(donor__isnull=True).annotate(
                effective_donor_id=Coalesce('canonical_donor_id', 'donor_id')
            ).values('effective_donor_id').annotate(
                total=Sum('value'), count=Count('id'),
            ).order_by('-total')[:5]
        )
        # Resolve names for public fund sources
        pf_donor_ids = [r['effective_donor_id'] for r in public_funds_top]
        pf_actors = {a.id: a for a in models.Actor.objects.filter(id__in=pf_donor_ids)}
        public_funds = {
            'total': str(public_funds_totals['total']),
            'count': public_funds_totals['count'],
            'sources': public_funds_totals['sources'],
            'top_sources': [
                {'id': r['effective_donor_id'], 'name': pf_actors[r['effective_donor_id']].name,
                 'total': str(r['total']), 'count': r['count']}
                for r in public_funds_top if r['effective_donor_id'] in pf_actors
            ],
        }

        # --- Trade union funding summary ---
        union_donor_ids = list(
            OrgModel.objects.filter(classification='Trade Union').values_list('actor_ptr_id', flat=True)
        )
        union_qs = base_qs.filter(donor_id__in=union_donor_ids)
        union_totals = union_qs.aggregate(
            total=Coalesce(Sum('value'), Decimal('0')),
            count=Count('id'),
            sources=Count('donor', distinct=True),
        )
        union_top = list(
            union_qs.exclude(donor__isnull=True).annotate(
                effective_donor_id=Coalesce('canonical_donor_id', 'donor_id')
            ).values('effective_donor_id').annotate(
                total=Sum('value'), count=Count('id'),
            ).order_by('-total')[:10]
        )
        uf_donor_ids = [r['effective_donor_id'] for r in union_top]
        uf_actors = {a.id: a for a in models.Actor.objects.filter(id__in=uf_donor_ids)}
        union_funding = {
            'total': str(union_totals['total']),
            'count': union_totals['count'],
            'sources': union_totals['sources'],
            'top_sources': [
                {'id': r['effective_donor_id'], 'name': uf_actors[r['effective_donor_id']].name,
                 'total': str(r['total']), 'count': r['count']}
                for r in union_top if r['effective_donor_id'] in uf_actors
            ],
        }

        # --- Category breakdown (single query) ---
        category_qs = base_qs.values('donation_type').annotate(
            total=Sum('value'),
            count=Count('id'),
        ).order_by('-total')

        category_breakdown = [
            {
                'category': row['donation_type'] or 'Unknown',
                'total': str(row['total'] or 0),
                'count': row['count'],
            }
            for row in category_qs
        ]

        # --- Largest single donation (single query) ---
        largest = base_qs.select_related(
            'donor', 'donor__polymorphic_ctype'
        ).order_by('-value').values(
            'value', 'donor__name', 'donor_id',
            'accepted_date', 'reported_date', 'received_date'
        ).first()

        largest_donation = None
        if largest:
            date = largest['accepted_date'] or largest['reported_date'] or largest['received_date']
            largest_donation = {
                'value': str(largest['value'] or 0),
                'donor_name': largest['donor__name'] or 'Unknown',
                'donor_id': largest['donor_id'],
                'date': str(date) if date else None,
            }

        elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

        result = {
            'actor_id': pk,
            'total_received': str(totals['total_received']),
            'donation_count': totals['donation_count'],
            'unique_donors': totals['unique_donors'],
            'yearly_totals': yearly_totals,
            'top_donors': top_donors,
            'public_funds': public_funds,
            'union_funding': union_funding,
            'category_breakdown': category_breakdown,
            'largest_donation': largest_donation,
            'computed_in_ms': elapsed_ms,
        }

        # Cache the result
        cache.set(cache_key, result, self.CACHE_TTL)
        logger.info(
            'Funding summary for actor %s computed in %sms, cached as %s',
            pk, elapsed_ms, cache_key,
        )

        return Response(result)


class ActorActivityByYearView(views.APIView):
    """
    GET /api/v2/actors/{id}/activity-by-year/

    Pre-aggregated per-year activity counts for any actor. Designed to feed
    the Career Shape coxcomb and similar shape-of-activity visualisations
    without moving the underlying rows to the browser.

    Returns four series, sorted most-recent-first. Each series is `[]` when
    the actor has no activity of that kind:

    - donations_received: [{year, count, total}]
    - donations_made:     [{year, count, total}]
    - meetings:           [{year, count}] — minister, attendee, or canonical attendee
    - consultancies:      [{year, count}] — client/agency or their canonical equivalents

    Plus a compositional slice of donations_received:

    - category_breakdown: [{category, count, total}] — by Donation.donation_type,
      sorted descending by total. NULL/empty donation_type maps to 'Unknown'.

    Entity resolution: every actor match includes the canonical_* field.

    Date sources:
    - Donations use Coalesce(accepted_date, reported_date, received_date).
    - Meetings use meeting_date (DateField).
    - Consultancies use Dateframeable start_date (CharField YYYY[-MM[-DD]]).

    Cached in Redis for 1 hour, invalidated via cache_utils.invalidate_actor().
    Pass ?bust_cache=1 to force refresh.
    """
    permission_classes = [permissions.AllowAny]

    CACHE_TTL = 3600  # 1 hour — changes only on import

    def get(self, request, pk):
        from django.db.models.functions import ExtractYear, Cast, Substr
        from django.db.models import CharField

        cache_key = f'activity_by_year:{pk}'
        bust = request.query_params.get('bust_cache', '').strip()

        if not bust:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

        t0 = time.monotonic()

        if not models.Actor.objects.filter(pk=pk).exists():
            return Response({'error': 'Actor not found'}, status=404)

        def _donation_series(base_qs):
            rows = base_qs.annotate(
                effective_date=Coalesce('accepted_date', 'reported_date', 'received_date'),
            ).exclude(effective_date__isnull=True).annotate(
                year=Cast(ExtractYear('effective_date'), output_field=CharField()),
            ).values('year').annotate(
                count=Count('id'),
                total=Sum('value'),
            ).order_by('-year')
            return [
                {'year': r['year'], 'count': r['count'], 'total': str(r['total'] or 0)}
                for r in rows
            ]

        received_qs = models.Donation.objects.filter(
            Q(recipient_id=pk) | Q(canonical_recipient_id=pk)
        )
        donations_received = _donation_series(received_qs)
        donations_made = _donation_series(
            models.Donation.objects.filter(
                Q(donor_id=pk) | Q(canonical_donor_id=pk)
            )
        )

        category_rows = received_qs.values('donation_type').annotate(
            count=Count('id'),
            total=Sum('value'),
        ).order_by('-total')
        category_breakdown = [
            {
                'category': r['donation_type'] or 'Unknown',
                'count': r['count'],
                'total': str(r['total'] or 0),
            }
            for r in category_rows
        ]

        # Meetings: Count('id', distinct=True) because a meeting with multiple
        # matching attendees would otherwise be counted more than once.
        meeting_rows = models.MinisterialMeeting.objects.filter(
            Q(minister_id=pk) |
            Q(attendees__actor_id=pk) |
            Q(attendees__canonical_actor_id=pk)
        ).exclude(meeting_date__isnull=True).annotate(
            year=Cast(ExtractYear('meeting_date'), output_field=CharField()),
        ).values('year').annotate(
            count=Count('id', distinct=True),
        ).order_by('-year')
        meetings = [{'year': r['year'], 'count': r['count']} for r in meeting_rows]

        consultancy_rows = models.Consultancy.objects.filter(
            Q(client_id=pk) | Q(canonical_client_id=pk) |
            Q(agency_id=pk) | Q(canonical_agency_id=pk)
        ).exclude(start_date__isnull=True).exclude(start_date='').annotate(
            year=Substr('start_date', 1, 4),
        ).values('year').annotate(
            count=Count('id', distinct=True),
        ).order_by('-year')
        consultancies = [{'year': r['year'], 'count': r['count']} for r in consultancy_rows]

        elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

        result = {
            'actor_id': pk,
            'donations_received': donations_received,
            'donations_made': donations_made,
            'meetings': meetings,
            'consultancies': consultancies,
            'category_breakdown': category_breakdown,
            'computed_in_ms': elapsed_ms,
        }

        cache.set(cache_key, result, self.CACHE_TTL)
        logger.info(
            'activity-by-year for actor %s computed in %sms, cached as %s',
            pk, elapsed_ms, cache_key,
        )
        return Response(result)


class DepartmentMeetingsSummaryView(views.APIView):
    """
    GET /api/v2/departments/{id}/meetings-summary/

    Per-department summary of ministerial meeting activity. The detail analog
    of the aggregate /aggregates/department-meetings/ endpoint: instead of
    ranking all departments, this answers "what did this one department do?".

    Designed for the department profile page, which today has nothing but an
    actor detail row to render. See BACKEND_DESIGN §8 (department pages).

    Scope is department-only. The `id` must be an Organization with
    classification in {'Government Department', 'Legislature'}; non-department
    actors 404. (Previously mounted at /actors/{id}/meetings-summary/ where
    non-department actors silently returned 200 with zeros — see
    BACKEND_DESIGN.md §8 #25.)

    Returns:
    - total_meetings: int
    - unique_attendees: distinct effective_actor_id count across all attendees
    - unique_ministers: distinct minister_id count on this department's meetings
    - by_year: [{year, count}] — most recent first
    - top_attendees: [{id, name, actor_type, classification, meeting_count}] — top 20
    - top_ministers: [{id, name, meeting_count}] — top 20

    Entity resolution: attendees are rolled up via Coalesce(canonical_actor_id,
    actor_id) so an organisation and its merged alias count as one.

    Cached 1 hour, keyed by `meetings_summary:{pk}`. Invalidated alongside
    other per-actor caches in cache_utils.invalidate_actor().
    Pass ?bust_cache=1 to force refresh.
    """
    permission_classes = [permissions.AllowAny]

    CACHE_TTL = 3600

    DEPARTMENT_CLASSIFICATIONS = ('Government Department', 'Legislature')

    def get(self, request, pk):
        from django.db.models.functions import ExtractYear, Cast
        from django.db.models import CharField

        cache_key = f'meetings_summary:{pk}'
        bust = request.query_params.get('bust_cache', '').strip()

        if not bust:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

        t0 = time.monotonic()

        if not models.Organization.objects.filter(
            pk=pk, classification__in=self.DEPARTMENT_CLASSIFICATIONS
        ).exists():
            return Response({'error': 'Department not found'}, status=404)

        meetings_qs = models.MinisterialMeeting.objects.filter(department_id=pk)

        # Top-level counters
        totals = meetings_qs.aggregate(
            total_meetings=Count('id'),
            unique_ministers=Count('minister_id', distinct=True),
        )

        # Unique attendees — rolled up via canonical where present
        effective_attendee = Coalesce('canonical_actor_id', 'actor_id')
        attendees_qs = models.MeetingAttendee.objects.filter(
            meeting__department_id=pk,
        ).exclude(actor__isnull=True, canonical_actor__isnull=True)
        unique_attendees = attendees_qs.annotate(
            effective_actor_id=effective_attendee,
        ).aggregate(
            unique=Count('effective_actor_id', distinct=True),
        )['unique'] or 0

        # By-year count of meetings
        by_year_rows = meetings_qs.exclude(meeting_date__isnull=True).annotate(
            year=Cast(ExtractYear('meeting_date'), output_field=CharField()),
        ).values('year').annotate(
            count=Count('id'),
        ).order_by('-year')
        by_year = [{'year': r['year'], 'count': r['count']} for r in by_year_rows]

        # Top attendees — canonical-resolved, ranked by distinct meetings attended
        top_attendee_rows = list(
            attendees_qs.annotate(
                effective_actor_id=effective_attendee,
            ).values('effective_actor_id').annotate(
                meeting_count=Count('meeting_id', distinct=True),
            ).order_by('-meeting_count')[:20]
        )
        top_attendee_ids = [r['effective_actor_id'] for r in top_attendee_rows]
        attendee_actors = {
            a.id: a
            for a in models.Actor.objects.filter(id__in=top_attendee_ids).select_related('polymorphic_ctype')
        }
        top_attendees = []
        for r in top_attendee_rows:
            a = attendee_actors.get(r['effective_actor_id'])
            if a:
                top_attendees.append({
                    'id': a.id,
                    'name': a.name,
                    'actor_type': a.polymorphic_ctype.model,
                    'classification': getattr(a, 'classification', None),
                    'meeting_count': r['meeting_count'],
                })

        # Top ministers — ranked by meetings hosted in this department
        top_minister_rows = list(
            meetings_qs.exclude(minister__isnull=True).values('minister_id').annotate(
                meeting_count=Count('id'),
            ).order_by('-meeting_count')[:20]
        )
        top_minister_ids = [r['minister_id'] for r in top_minister_rows]
        minister_actors = {
            a.id: a
            for a in models.Actor.objects.filter(id__in=top_minister_ids).select_related('polymorphic_ctype')
        }
        top_ministers = []
        for r in top_minister_rows:
            a = minister_actors.get(r['minister_id'])
            if a:
                top_ministers.append({
                    'id': a.id,
                    'name': a.name,
                    'meeting_count': r['meeting_count'],
                })

        elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

        result = {
            'actor_id': pk,
            'total_meetings': totals['total_meetings'] or 0,
            'unique_attendees': unique_attendees,
            'unique_ministers': totals['unique_ministers'] or 0,
            'by_year': by_year,
            'top_attendees': top_attendees,
            'top_ministers': top_ministers,
            'computed_in_ms': elapsed_ms,
        }

        cache.set(cache_key, result, self.CACHE_TTL)
        logger.info(
            'meetings-summary for actor %s computed in %sms, cached as %s',
            pk, elapsed_ms, cache_key,
        )
        return Response(result)


def _build_actor_context(actor_ids):
    """
    Batch-lookup party and role memberships for a set of actors.
    Returns {actor_id: {party: {id, name}, memberships: [{start, end, role, is_senior}, ...]}}.
    """
    if not actor_ids:
        return {}

    memberships = models.Membership.objects.filter(
        person_id__in=actor_ids
    ).select_related('on_behalf_of').order_by('person_id', 'start_date')

    context = {}
    for m in memberships:
        pid = m.person_id
        if pid not in context:
            context[pid] = {'party': None, 'memberships': []}

        # Extract party from on_behalf_of (only on parliamentary memberships)
        if m.on_behalf_of_id and not context[pid]['party']:
            context[pid]['party'] = {'id': m.on_behalf_of.id, 'name': m.on_behalf_of.name}

        if m.role:
            is_senior = ('Secretary of State' in m.role or 'Minister' in m.role
                         or 'Mayor' in m.role) and not m.role.startswith('Member of Parliament')
            context[pid]['memberships'].append({
                'start': m.start_date or '',
                'end': m.end_date or '',
                'role': m.role,
                'is_senior': is_senior,
            })

    return context


class _DonationContextMixin:
    """Mixin that enriches paginated donation results with recipient party/role and donor key people."""

    def list(self, request, *args, **kwargs):
        from django.db.models import Q

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        donations = page if page is not None else queryset

        # Build actor context for recipient party/role (from paginated results only)
        recipient_ids = list({d.recipient_id for d in donations if d.recipient_id})
        actor_context = _build_actor_context(recipient_ids)

        # Batch-fetch donor key people (eliminates N+1 from get_donor_key_people)
        donor_ids = list({d.donor_id for d in donations if d.donor_id})
        key_people_qs = models.Membership.objects.filter(
            organization_id__in=donor_ids
        ).filter(
            Q(role__iexact='Director') |
            Q(role__icontains='Beneficial Owner') |
            Q(role__icontains='Secretary')
        ).select_related('person').order_by('organization_id', 'role')

        key_people_map = {}
        for m in key_people_qs:
            org_id = m.organization_id
            if org_id not in key_people_map:
                key_people_map[org_id] = []
            if len(key_people_map[org_id]) < 4:
                key_people_map[org_id].append({
                    'id': m.person.id,
                    'name': m.person.name,
                    'role': m.role,
                })

        serializer = self.get_serializer(donations, many=True, context={
            **self.get_serializer_context(),
            'actor_context': actor_context,
            'key_people_map': key_people_map,
        })

        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ActorDonationsView(_DonationContextMixin, generics.ListAPIView):
    """
    GET /api/v2/actors/{id}/donations/?role=<donor|recipient>

    Returns donations where this actor is on the specified side of the
    relation, enriched with recipient party/role at donation date.

    `role` is required. `donor` returns donations made by this actor;
    `recipient` returns donations received. Missing or invalid role → 400.

    Canonical-aware: each side matches both the raw id and the matching
    canonical_* id, so merged actors see their full history on either side.
    """
    serializer_class = serializers.DonationDetailSerializer
    pagination_class = pagination.DetailPagination
    permission_classes = [permissions.AllowAny]

    VALID_ROLES = ('donor', 'recipient')

    def get_queryset(self):
        actor_id = self.kwargs['pk']
        role = self.request.query_params.get('role', '').lower()
        if role == 'recipient':
            q = Q(recipient_id=actor_id) | Q(canonical_recipient_id=actor_id)
        elif role == 'donor':
            q = Q(donor_id=actor_id) | Q(canonical_donor_id=actor_id)
        else:
            return models.Donation.objects.none()

        queryset = models.Donation.objects.filter(q).select_related(
            'donor', 'donor__polymorphic_ctype',
            'recipient', 'recipient__polymorphic_ctype',
            'canonical_donor', 'canonical_donor__polymorphic_ctype',
            'canonical_recipient', 'canonical_recipient__polymorphic_ctype',
        ).order_by('-received_date').distinct()

        filterset = filters.DonationFilterSet(
            self.request.query_params,
            queryset=queryset
        )
        return filterset.qs

    def get(self, request, *args, **kwargs):
        role = request.query_params.get('role', '').lower()
        if role not in self.VALID_ROLES:
            return Response(
                {'error': f'`role` query parameter is required. Must be one of: {", ".join(self.VALID_ROLES)}.'},
                status=400,
            )
        return super().get(request, *args, **kwargs)


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


class AgencyClientsView(views.APIView):
    """
    GET /api/v2/actors/{id}/agency-clients/

    Returns aggregated client list for a lobbying agency, with each client's
    political activity stats (meetings, donations, other agencies hired).

    Sorted by total political activity (most active clients first).
    Uses pre-aggregated JOINs instead of correlated subqueries for performance.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            limit = min(int(request.query_params.get('limit', 20)), 100)
        except (ValueError, TypeError):
            limit = 20

        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH agency_clients AS (
                    SELECT DISTINCT client_id
                    FROM datafetch_consultancy
                    WHERE agency_id = %s
                ),
                meeting_counts AS (
                    SELECT actor_id, COUNT(DISTINCT meeting_id) as cnt
                    FROM datafetch_meetingattendee
                    WHERE actor_id IN (SELECT client_id FROM agency_clients)
                    GROUP BY actor_id
                ),
                donation_counts AS (
                    SELECT actor_id, COUNT(*) as cnt FROM (
                        SELECT donor_id as actor_id FROM datafetch_donation WHERE donor_id IN (SELECT client_id FROM agency_clients)
                        UNION ALL
                        SELECT recipient_id FROM datafetch_donation WHERE recipient_id IN (SELECT client_id FROM agency_clients)
                    ) d GROUP BY actor_id
                ),
                other_agency_counts AS (
                    SELECT client_id, COUNT(DISTINCT agency_id) - 1 as cnt
                    FROM datafetch_consultancy
                    WHERE client_id IN (SELECT client_id FROM agency_clients)
                    GROUP BY client_id
                ),
                engagement_counts AS (
                    SELECT client_id, COUNT(*) as cnt
                    FROM datafetch_consultancy
                    WHERE agency_id = %s AND client_id IN (SELECT client_id FROM agency_clients)
                    GROUP BY client_id
                )
                SELECT
                    a.id,
                    a.name,
                    COALESCE(mc.cnt, 0) as meeting_count,
                    COALESCE(dc.cnt, 0) as donation_count,
                    COALESCE(oa.cnt, 0) as other_agencies_count,
                    COALESCE(ec.cnt, 0) as engagement_count
                FROM agency_clients ac
                JOIN datafetch_actor a ON a.id = ac.client_id
                LEFT JOIN meeting_counts mc ON mc.actor_id = ac.client_id
                LEFT JOIN donation_counts dc ON dc.actor_id = ac.client_id
                LEFT JOIN other_agency_counts oa ON oa.client_id = ac.client_id
                LEFT JOIN engagement_counts ec ON ec.client_id = ac.client_id
                ORDER BY COALESCE(mc.cnt, 0) * 10 + COALESCE(dc.cnt, 0) * 20 + COALESCE(oa.cnt, 0) * 5 DESC
                LIMIT %s
            """, [pk, pk, limit])

            columns = ['id', 'name', 'meeting_count', 'donation_count', 'other_agencies_count', 'engagement_count']
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Get total unique client count
        total = models.Consultancy.objects.filter(agency_id=pk).values('client_id').distinct().count()

        return Response({
            'count': total,
            'results': results,
        })


class ActorCrossConnectionsView(views.APIView):
    """
    GET /api/v2/actors/{id}/cross-connections/

    Bidirectional cross-connections endpoint.

    For organisations: returns members (directors/lobbyists) who have political
    connections (donations, meeting attendances, or parliamentary roles).
    Data quality filter excludes single-word names and role-title names.

    For persons: returns organisations they direct/control that have political
    activity (lobbying, meetings, donations). Uses canonical_entry for dedup.
    """
    permission_classes = [permissions.AllowAny]

    CACHE_TTL = 3600  # 1 hour

    def get(self, request, pk):
        from datafetch.models import Actor
        from django.db import connection

        cache_key = f'cross_connections:{pk}'
        bust = request.query_params.get('bust_cache', '').strip()

        if not bust:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

        try:
            actor = Actor.objects.get(pk=pk)
        except Actor.DoesNotExist:
            return Response({'error': 'Actor not found'}, status=404)

        is_person = actor.polymorphic_ctype.model == 'person'

        if is_person:
            response = self._person_to_orgs(connection, pk)
        else:
            response = self._org_to_persons(connection, pk)

        # Cache the successful response
        cache.set(cache_key, response.data, self.CACHE_TTL)
        return response

    def _person_to_orgs(self, connection, pk):
        """Person → Orgs they direct that have political activity."""
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH person_orgs AS (
                    SELECT DISTINCT ON (COALESCE(a.canonical_entry_id, a.id))
                           COALESCE(a.canonical_entry_id, a.id) AS org_id,
                           COALESCE(canon.name, a.name) AS org_name,
                           m.role,
                           org.classification
                    FROM datafetch_membership m
                    JOIN datafetch_actor a ON m.organization_id = a.id
                    LEFT JOIN datafetch_actor canon ON a.canonical_entry_id = canon.id
                    LEFT JOIN datafetch_organization org
                        ON COALESCE(a.canonical_entry_id, a.id) = org.actor_ptr_id
                    WHERE m.person_id = %s
                      AND m.role IN ('Director', 'Person with Significant Control', 'Secretary')
                    ORDER BY COALESCE(a.canonical_entry_id, a.id), m.organization_id DESC
                )
                SELECT
                    po.org_id AS id,
                    po.org_name AS name,
                    po.role,
                    COALESCE(po.classification, '') AS classification,
                    COALESCE(c.consultancy_count, 0) AS consultancy_count,
                    COALESCE(ma.meeting_count, 0) AS meeting_count,
                    COALESCE(d_made.donation_count, 0) AS donations_made_count,
                    COALESCE(d_made.total_donated, 0) AS total_donated,
                    COALESCE(d_recv.donation_count, 0) AS donations_received_count,
                    COALESCE(d_recv.total_received, 0) AS total_received
                FROM person_orgs po
                LEFT JOIN (
                    SELECT client_id AS org_id, COUNT(DISTINCT agency_id) AS consultancy_count
                    FROM datafetch_consultancy
                    GROUP BY client_id
                ) c ON c.org_id = po.org_id
                LEFT JOIN (
                    SELECT COALESCE(canonical_actor_id, actor_id) AS org_id,
                           COUNT(DISTINCT meeting_id) AS meeting_count
                    FROM datafetch_meetingattendee
                    GROUP BY COALESCE(canonical_actor_id, actor_id)
                ) ma ON ma.org_id = po.org_id
                LEFT JOIN (
                    SELECT COALESCE(canonical_donor_id, donor_id) AS org_id,
                           COUNT(*) AS donation_count, SUM(value) AS total_donated
                    FROM datafetch_donation
                    GROUP BY COALESCE(canonical_donor_id, donor_id)
                ) d_made ON d_made.org_id = po.org_id
                LEFT JOIN (
                    SELECT COALESCE(canonical_recipient_id, recipient_id) AS org_id,
                           COUNT(*) AS donation_count, SUM(value) AS total_received
                    FROM datafetch_donation
                    GROUP BY COALESCE(canonical_recipient_id, recipient_id)
                ) d_recv ON d_recv.org_id = po.org_id
                WHERE c.consultancy_count > 0
                   OR ma.meeting_count > 0
                   OR d_made.donation_count > 0
                   OR d_recv.donation_count > 0
                ORDER BY
                    COALESCE(c.consultancy_count, 0) DESC,
                    COALESCE(ma.meeting_count, 0) DESC,
                    COALESCE(d_made.total_donated, 0) + COALESCE(d_recv.total_received, 0) DESC
            """, [pk])

            columns = ['id', 'name', 'role', 'classification', 'consultancy_count',
                       'meeting_count', 'donations_made_count', 'total_donated',
                       'donations_received_count', 'total_received']
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        for r in results:
            r['total_donated'] = float(r['total_donated'] or 0)
            r['total_received'] = float(r['total_received'] or 0)

        return Response({
            'direction': 'person_to_orgs',
            'count': len(results),
            'results': results,
        })

    def _org_to_persons(self, connection, pk):
        """Org → Members who have political activity. With data quality filter."""
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH org_members AS (
                    SELECT DISTINCT ON (m.person_id) m.person_id, a.name, m.role
                    FROM datafetch_membership m
                    JOIN datafetch_actor a ON m.person_id = a.id
                    WHERE m.organization_id = %s
                      AND a.name ~ '.+ .+'
                      AND a.name !~* '^(Director|Secretary|Lobbyist|Member|Trustee|Chair|Partner|Consultant|Councillor|Minister|Person with Significant Control)$'
                      AND length(a.name) > 3
                    ORDER BY m.person_id, m.role DESC NULLS LAST
                )
                SELECT
                    om.person_id as id,
                    om.name,
                    om.role,
                    COALESCE(d.donation_count, 0) as donation_count,
                    COALESCE(d.total_donated, 0) as total_donated,
                    COALESCE(ma.meeting_count, 0) as meeting_count,
                    COALESCE(mp.mp_roles, '') as parliamentary_roles,
                    COALESCE(dir.other_orgs, 0) as other_directorships,
                    COALESCE(party.party_name, '') as party
                FROM org_members om
                LEFT JOIN (
                    SELECT COALESCE(canonical_donor_id, donor_id) as person_id,
                           COUNT(*) as donation_count, SUM(value) as total_donated
                    FROM datafetch_donation
                    GROUP BY COALESCE(canonical_donor_id, donor_id)
                ) d ON d.person_id = om.person_id
                LEFT JOIN (
                    SELECT COALESCE(canonical_actor_id, actor_id) as actor_id,
                           COUNT(DISTINCT meeting_id) as meeting_count
                    FROM datafetch_meetingattendee
                    GROUP BY COALESCE(canonical_actor_id, actor_id)
                ) ma ON ma.actor_id = om.person_id
                LEFT JOIN (
                    SELECT person_id, string_agg(DISTINCT role, ', ') as mp_roles
                    FROM datafetch_membership
                    WHERE role LIKE 'Member of Parliament%%'
                       OR role LIKE '%%Secretary of State%%'
                       OR role LIKE '%%Minister%%'
                    GROUP BY person_id
                ) mp ON mp.person_id = om.person_id
                LEFT JOIN (
                    SELECT person_id, COUNT(DISTINCT organization_id) - 1 as other_orgs
                    FROM datafetch_membership
                    WHERE role IN ('Director', 'Lobbyist')
                    GROUP BY person_id
                ) dir ON dir.person_id = om.person_id
                LEFT JOIN (
                    SELECT DISTINCT ON (m.person_id) m.person_id, a.name as party_name
                    FROM datafetch_membership m
                    JOIN datafetch_actor a ON m.on_behalf_of_id = a.id
                    JOIN datafetch_organization o ON m.on_behalf_of_id = o.actor_ptr_id
                    WHERE o.classification = 'Political Party'
                    ORDER BY m.person_id, m.start_date DESC NULLS LAST
                ) party ON party.person_id = om.person_id
                WHERE d.donation_count > 0
                   OR ma.meeting_count > 0
                   OR mp.mp_roles IS NOT NULL
                ORDER BY
                    CASE WHEN mp.mp_roles IS NOT NULL THEN 1 ELSE 0 END DESC,
                    COALESCE(d.total_donated, 0) DESC,
                    COALESCE(ma.meeting_count, 0) DESC
            """, [pk])

            columns = ['id', 'name', 'role', 'donation_count', 'total_donated',
                       'meeting_count', 'parliamentary_roles', 'other_directorships', 'party']
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        for r in results:
            r['total_donated'] = float(r['total_donated'] or 0)

        return Response({
            'direction': 'org_to_persons',
            'count': len(results),
            'results': results,
        })


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
        """Get memberships for this actor with temporal filtering.

        Auto-detects direction: if the actor is a Person, returns their memberships.
        If the actor is an Organization, returns people who are members of it
        (directors, PSCs, etc.).
        """
        actor_id = self.kwargs['pk']

        # Detect actor type to determine query direction
        is_org = models.Organization.objects.filter(actor_ptr_id=actor_id).exists()

        if is_org:
            # Org direction: people who are members of this organization
            queryset = models.Membership.objects.filter(
                organization_id=actor_id
            ).select_related('person', 'organization', 'post', 'on_behalf_of')
        else:
            # Person direction: organizations this person belongs to
            queryset = models.Membership.objects.filter(
                person_id=actor_id
            ).select_related('person', 'organization', 'post', 'on_behalf_of')

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
        # Also check canonical_actor in attendees for robust matching.
        #
        # Prefetch strategy: MinisterialMeetingSerializer uses ActorSummarySerializer
        # for minister/department/attendees.actor, which calls polymorphic_ctype.model
        # per actor. Without select_related on polymorphic_ctype this produces hundreds
        # of lazy ContentType fetches per page load — the cause of the 2026-04-16
        # hydration freeze when meeting limits were bumped. attendees.actor is
        # sourced from effective_actor (canonical_actor or actor), so canonical_actor
        # must be prefetched too.
        queryset = models.MinisterialMeeting.objects.filter(
            Q(minister_id=actor_id) |
            Q(attendees__actor_id=actor_id) |
            Q(attendees__canonical_actor_id=actor_id)
        ).select_related(
            'minister', 'minister__polymorphic_ctype',
            'department', 'department__polymorphic_ctype',
        ).prefetch_related(
            Prefetch(
                'attendees',
                queryset=models.MeetingAttendee.objects.select_related(
                    'actor', 'actor__polymorphic_ctype',
                    'canonical_actor', 'canonical_actor__polymorphic_ctype',
                ),
            ),
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
    Cached for 1 hour via Redis.

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

    Example:
        GET /api/v2/aggregates/stats/?received_after=2020-01-01
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        """Calculate homepage statistics with optional filtering. Cached 1hr."""
        from api.v2.cache_utils import make_aggregate_cache_key, AGGREGATE_CACHE_TTL

        cache_key = make_aggregate_cache_key('homepage_stats', dict(request.query_params))
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

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
        ).annotate(
            effective_donor_id=Coalesce('canonical_donor_id', 'donor_id')
        ).values('effective_donor_id').annotate(
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
        
        # Get set of unique effective donors
        effective_donor_ids = set(donations_qs.exclude(
            donor__isnull=True
        ).annotate(
            effective_donor_id=Coalesce('canonical_donor_id', 'donor_id')
        ).values_list('effective_donor_id', flat=True).distinct())

        # Get set of unique effective clients (lobbying)
        # Note: Consultancies don't have filters applied here usually, but if we wanted to be strict we could.
        # Ideally we should filter consultancies by date too if date filters are present, but for now take all.
        effective_client_ids = set(models.Consultancy.objects.exclude(
            client__isnull=True
        ).annotate(
            effective_client_id=Coalesce('canonical_client_id', 'client_id')
        ).values_list('effective_client_id', flat=True).distinct())

        dual_influence_count = len(effective_donor_ids.intersection(effective_client_ids))

        data = {
            'total_donations': donation_stats['total_donations'] or 0,
            'total_value': donation_stats['total_value'] or 0,
            'concentration_top_1_percent': concentration_percentage,
            'concentration_donors_count': top_1_3_percent_count,
            'dual_influence_count': dual_influence_count,
            'timestamp': timezone.now().isoformat(),
        }

        serializer = serializers.HomepageStatsSerializer(data)
        cache.set(cache_key, serializer.data, AGGREGATE_CACHE_TTL)
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
        """Build and return the minister network graph. Cached 1hr."""
        from api.v2.cache_utils import make_aggregate_cache_key, AGGREGATE_CACHE_TTL

        cache_key = make_aggregate_cache_key('minister_network', dict(request.query_params))
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

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

        # For current_only mode, include ALL current ministers (full government)
        # Otherwise, limit to top N by donation value
        if current_only:
            # Include all current ministers - no limit
            minister_totals = donations_qs.values('recipient_id').annotate(
                total_received=Sum('value')
            ).order_by('-total_received')

            # Build dict of donation totals
            minister_donation_totals = {m['recipient_id']: m['total_received'] for m in minister_totals}

            # Use ALL minister_ids, not just those with donations
            top_minister_ids = minister_ids
        else:
            # Original behavior: top N by donations
            minister_totals = donations_qs.values('recipient_id').annotate(
                total_received=Sum('value')
            ).order_by('-total_received')[:limit]

            minister_donation_totals = {m['recipient_id']: m['total_received'] for m in minister_totals}
            top_minister_ids = [m['recipient_id'] for m in minister_totals]
        
        from django.db.models.functions import Coalesce

        # Aggregate donations by donor -> minister (only for top ministers)
        # Use effective_donor_id to group resolved duplicates
        connections = donations_qs.filter(
            recipient_id__in=top_minister_ids
        ).annotate(
            effective_donor_id=Coalesce('canonical_donor_id', 'donor_id')
        ).values(
            'effective_donor_id', 'recipient_id'
        ).annotate(
            total_value=Sum('value'),
            donation_count=Count('id')
        ).filter(
            total_value__gte=min_value
        ).order_by('-total_value')

        # Build node and link sets
        nodes_dict = {}
        links = []

        # Get all unique actor IDs (include ALL ministers, not just those with donations)
        donor_ids = set(c['effective_donor_id'] for c in connections)
        all_actor_ids = set(top_minister_ids) | donor_ids

        # Fetch all actors (ministers + donors)
        actors = {
            a.id: a for a in models.Actor.objects.filter(id__in=all_actor_ids)
        }

        # Fetch Companies House identifiers
        from django.contrib.contenttypes.models import ContentType
        # We need to find identifiers for these actors.
        # Identifiers are generic relations, so we need content type for Actor/Organization
        # But efficiently, we can just query Identifier where object_id matches (if IDs are unique across models or we know the type)
        # Actor IDs are unique.
        
        ch_identifiers = {}
        # Get content types for Actor and its subclasses if needed, but usually we just query by object_id if we assume unique IDs or check generic relation
        # Easier: Filter by scheme and object_id
        
        # Note: Identifiers are attached to Actor (parent of Person/Org)
        identifiers_qs = models.Identifier.objects.filter(
            scheme='uk.gov.companieshouse',
            object_id__in=all_actor_ids
        ).values('object_id', 'identifier')
        
        for item in identifiers_qs:
            ch_identifiers[item['object_id']] = item['identifier']

        # Get minister roles and departments for display
        import re

        def parse_department_from_role(role):
            """Extract department name from ministerial role string."""
            if not role:
                return None

            # Patterns to extract department:
            # "The Minister of State, Home Department" -> "Home Department"
            # "The Secretary of State for Northern Ireland" -> "Northern Ireland"
            # "Parliamentary Under-Secretary (Department for Transport)" -> "Department for Transport"
            # "Minister of State (Cabinet Office)" -> "Cabinet Office"

            # Pattern 1: "Secretary of State for X" or "Secretary of State, X"
            match = re.search(r'Secretary of State (?:for |, )(.+?)(?:\s*$|\s*\()', role)
            if match:
                return match.group(1).strip()

            # Pattern 2: "Minister of State, X" or "Minister of State (X)"
            match = re.search(r'Minister of State[,\s]+(.+?)(?:\s*$|\s*\()', role)
            if match:
                dept = match.group(1).strip()
                if dept and not dept.startswith('('):
                    return dept

            # Pattern 3: Parentheses with department
            match = re.search(r'\(([^)]+)\)\s*$', role)
            if match:
                return match.group(1).strip()

            # Pattern 4: "Under-Secretary of State for X" or "Under-Secretary, X"
            match = re.search(r'Under-Secretary[^,]*[,\s]+(?:for\s+)?(.+?)(?:\s*$|\s*\()', role)
            if match:
                return match.group(1).strip()

            return None

        minister_roles = {}
        minister_departments = {}
        minister_memberships_detail = models.Membership.objects.filter(
            person_id__in=top_minister_ids
        ).filter(minister_q).exclude(
            role__icontains='shadow'
        ).exclude(
            role__icontains='pps'
        ).select_related('organization').order_by('-start_date')

        if current_only:
            minister_memberships_detail = minister_memberships_detail.filter(
                Q(end_date__isnull=True) | Q(end_date='')
            )

        for m in minister_memberships_detail:
            # Check if organization is an actual department (not Legislature)
            is_department_org = m.organization and m.organization.classification not in ['Legislature', 'Political Party']

            if m.person_id not in minister_roles:
                minister_roles[m.person_id] = m.role

                if is_department_org:
                    # Use the organization directly
                    minister_departments[m.person_id] = {
                        'id': m.organization.id,
                        'name': m.organization.name
                    }
                else:
                    # Parse department from role string
                    dept_name = parse_department_from_role(m.role)
                    if dept_name:
                        minister_departments[m.person_id] = {
                            'id': None,
                            'name': dept_name
                        }
            elif m.person_id not in minister_departments:
                # We have a role but no department yet
                if is_department_org:
                    minister_departments[m.person_id] = {
                        'id': m.organization.id,
                        'name': m.organization.name
                    }
                else:
                    dept_name = parse_department_from_role(m.role)
                    if dept_name:
                        minister_departments[m.person_id] = {
                            'id': None,
                            'name': dept_name
                        }

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

        # Build minister nodes (all ministers, even those without donations)
        for mid in top_minister_ids:
            if mid in actors:
                actor = actors[mid]
                nodes_dict[mid] = {
                    'id': mid,
                    'name': actor.name,
                    'type': 'minister',
                    'role': minister_roles.get(mid, 'Minister'),
                    'department': minister_departments.get(mid),
                    'total_value': float(minister_donation_totals.get(mid, 0) or 0),
                    'meeting_count': minister_meeting_counts.get(mid, 0),
                    'companies_house_number': ch_identifiers.get(mid),
                    'url': f'/person/{mid}/'
                }

        # Build donor nodes and links
        for conn in connections:
            donor_id = conn['effective_donor_id']
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
                        'companies_house_number': ch_identifiers.get(donor_id),
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
        # Add Directors and PSCs for Organization nodes
        # ============================================
        
        # Identify organization nodes
        org_ids = [
            nid for nid, node in nodes_dict.items()
            if node['type'] == 'organization'
        ]

        if org_ids:
            # Fetch memberships with canonical entry for entity resolution
            memberships = models.Membership.objects.filter(
                organization_id__in=org_ids
            ).filter(
                Q(end_date__isnull=True) | Q(end_date='')
            ).filter(
                Q(role__icontains='director') |
                Q(role__icontains='significant control') |
                Q(role__icontains='shareholder')
            ).select_related('person', 'person__canonical_entry')

            # Map role to simpler type
            def get_role_type(role_name):
                r = role_name.lower()
                if 'significant control' in r or 'shareholder' in r:
                    return 'psc'
                return 'director'

            for m in memberships:
                # Use canonical entry if this person is a duplicate
                person = m.person
                if person.canonical_entry_id:
                    # Use the canonical entry instead
                    canonical_person = person.canonical_entry
                    pid = canonical_person.id
                    person_name = canonical_person.name
                else:
                    pid = person.id
                    person_name = person.name

                oid = m.organization_id

                # Only add if organization is still in nodes (it should be)
                if oid in nodes_dict:
                    # Add person node if not exists
                    if pid not in nodes_dict:
                        nodes_dict[pid] = {
                            'id': pid,
                            'name': person_name,
                            'type': get_role_type(m.role),
                            'role': m.role,
                            'total_value': 0,
                            'donation_count': 0,
                            'meeting_count': 0,
                            'url': f'/person/{pid}/'
                        }

                    # Add link
                    links.append({
                        'source': pid,
                        'target': oid,
                        'value': 1, # Visual weight
                        'count': 1,
                        'link_type': 'role', # New link type
                        'role_name': m.role
                    })

        # ============================================
        # Add meeting attendees as nodes and links
        # ============================================

        # Get all meetings for top ministers
        minister_meetings = models.MinisterialMeeting.objects.filter(
            minister_id__in=top_minister_ids
        )

        # Get meeting attendees with counts, ordered by meeting count
        # Use canonical resolution
        attendee_data = models.MeetingAttendee.objects.filter(
            meeting__minister_id__in=top_minister_ids
        ).annotate(
            effective_actor_id=Coalesce('canonical_actor_id', 'actor_id')
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

        # Fetch attendee actors with canonical entry for additional resolution
        attendee_actors = {
            a.id: a for a in models.Actor.objects.filter(
                id__in=attendee_ids
            ).select_related('canonical_entry')
        }

        # Build resolution map: attendee_id -> canonical_id
        # This handles cases where MeetingAttendee.canonical_actor wasn't set
        # but the Actor itself is marked as a duplicate
        attendee_resolution = {}
        for aid, actor in attendee_actors.items():
            if actor.canonical_entry_id:
                attendee_resolution[aid] = actor.canonical_entry_id
            else:
                attendee_resolution[aid] = aid

        # Fetch canonical actors that weren't in original set
        extra_canonical_ids = set(attendee_resolution.values()) - set(attendee_actors.keys())
        if extra_canonical_ids:
            extra_actors = {
                a.id: a for a in models.Actor.objects.filter(id__in=extra_canonical_ids)
            }
            attendee_actors.update(extra_actors)

        # Add attendee nodes (using resolved canonical IDs)
        processed_canonical_ids = set()
        for attendee_id in attendee_ids:
            canonical_id = attendee_resolution.get(attendee_id, attendee_id)

            # Skip if we've already processed this canonical ID
            if canonical_id in processed_canonical_ids:
                continue
            processed_canonical_ids.add(canonical_id)

            if canonical_id in attendee_actors and canonical_id not in nodes_dict:
                actor = attendee_actors[canonical_id]
                try:
                    actor_type = 'organization' if hasattr(actor, 'organization') else 'person'
                except:
                    actor_type = 'attendee'

                # Count total meetings for this attendee (aggregate across duplicates)
                total_meetings = sum(
                    m['meeting_count'] for m in meeting_links_data
                    if attendee_resolution.get(m['attendee_id'], m['attendee_id']) == canonical_id
                )

                nodes_dict[canonical_id] = {
                    'id': canonical_id,
                    'name': actor.name,
                    'type': actor_type,
                    'total_value': 0,  # No donations
                    'donation_count': 0,
                    'meeting_count': total_meetings,
                    'companies_house_number': None,
                    'url': f'/actor/{canonical_id}/'
                }

                # Add Companies House number if available
                if hasattr(actor, 'identifiers'):
                    ch = actor.identifiers.filter(scheme='uk.gov.companieshouse').first()
                    if ch:
                        nodes_dict[canonical_id]['companies_house_number'] = ch.identifier

        # Add meeting links (using resolved canonical IDs)
        # Aggregate links by canonical_attendee -> minister to avoid duplicate edges
        meeting_link_aggregates = {}
        for ml in meeting_links_data:
            # Resolve attendee to canonical ID
            raw_attendee_id = ml['attendee_id']
            canonical_attendee_id = attendee_resolution.get(raw_attendee_id, raw_attendee_id)
            minister_id = ml['minister_id']

            # Skip self-links
            if canonical_attendee_id == minister_id:
                continue

            # Aggregate by (canonical_attendee, minister) pair
            key = (canonical_attendee_id, minister_id)
            if key not in meeting_link_aggregates:
                meeting_link_aggregates[key] = 0
            meeting_link_aggregates[key] += ml['meeting_count']

        # Create links from aggregated data
        for (canonical_attendee_id, minister_id), meeting_count in meeting_link_aggregates.items():
            # Only add if both nodes exist
            if canonical_attendee_id in nodes_dict and minister_id in nodes_dict:
                links.append({
                    'source': canonical_attendee_id,
                    'target': minister_id,
                    'value': meeting_count * 1000,  # Scale for visibility
                    'count': meeting_count,
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

        response_data = {
            'nodes': nodes,
            'links': links,
            'stats': stats
        }
        cache.set(cache_key, response_data, AGGREGATE_CACHE_TTL)
        return Response(response_data)


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