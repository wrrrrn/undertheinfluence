"""
Shared filter system for API v2

Provides common filter classes for date ranges, value brackets, actor types, etc.
Uses django-filter for declarative filtering.
"""

import django_filters
from django.db.models import Q
from datafetch import models


class DonationFilterSet(django_filters.FilterSet):
    """
    Filter donations by date ranges, value brackets, actor types, and search.
    """
    # Date range filters
    received_after = django_filters.DateFilter(
        field_name='received_date',
        lookup_expr='gte',
        help_text='Filter donations received on or after this date (YYYY-MM-DD)'
    )
    received_before = django_filters.DateFilter(
        field_name='received_date',
        lookup_expr='lte',
        help_text='Filter donations received on or before this date (YYYY-MM-DD)'
    )

    # Value bracket filters
    value_min = django_filters.NumberFilter(
        field_name='value',
        lookup_expr='gte',
        help_text='Filter donations with value >= this amount'
    )
    value_max = django_filters.NumberFilter(
        field_name='value',
        lookup_expr='lte',
        help_text='Filter donations with value <= this amount'
    )

    # Actor type filters
    donor_type = django_filters.ChoiceFilter(
        field_name='donor__polymorphic_ctype__model',
        choices=[
            ('person', 'Person'),
            ('organization', 'Organization'),
        ],
        help_text='Filter by donor type (person or organization)'
    )
    recipient_type = django_filters.ChoiceFilter(
        field_name='recipient__polymorphic_ctype__model',
        choices=[
            ('person', 'Person'),
            ('organization', 'Organization'),
        ],
        help_text='Filter by recipient type (person or organization)'
    )

    # Search filters
    donor_name = django_filters.CharFilter(
        field_name='donor__name',
        lookup_expr='icontains',
        help_text='Search for donors by name (case-insensitive)'
    )
    recipient_name = django_filters.CharFilter(
        field_name='recipient__name',
        lookup_expr='icontains',
        help_text='Search for recipients by name (case-insensitive)'
    )

    # Category/nature filters
    category = django_filters.CharFilter(
        field_name='category',
        lookup_expr='iexact',
        help_text='Filter by donation category'
    )
    nature = django_filters.CharFilter(
        field_name='nature',
        lookup_expr='iexact',
        help_text='Filter by donation nature'
    )

    class Meta:
        model = models.Donation
        fields = [
            'received_after', 'received_before',
            'value_min', 'value_max',
            'donor_type', 'recipient_type',
            'donor_name', 'recipient_name',
            'category', 'nature',
        ]


class ConsultancyFilterSet(django_filters.FilterSet):
    """
    Filter consultancies by date ranges, actor types, and search.
    """
    # Date range filters
    start_after = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='gte',
        help_text='Filter consultancies starting on or after this date (YYYY-MM-DD)'
    )
    start_before = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='lte',
        help_text='Filter consultancies starting on or before this date (YYYY-MM-DD)'
    )
    end_after = django_filters.DateFilter(
        field_name='end_date',
        lookup_expr='gte',
        help_text='Filter consultancies ending on or after this date (YYYY-MM-DD)'
    )
    end_before = django_filters.DateFilter(
        field_name='end_date',
        lookup_expr='lte',
        help_text='Filter consultancies ending on or before this date (YYYY-MM-DD)'
    )

    # Search filters
    agency_name = django_filters.CharFilter(
        field_name='agency__name',
        lookup_expr='icontains',
        help_text='Search for agencies by name (case-insensitive)'
    )
    client_name = django_filters.CharFilter(
        field_name='client__name',
        lookup_expr='icontains',
        help_text='Search for clients by name (case-insensitive)'
    )

    class Meta:
        model = models.Consultancy
        fields = [
            'start_after', 'start_before',
            'end_after', 'end_before',
            'agency_name', 'client_name',
        ]


class ActorFilterSet(django_filters.FilterSet):
    """
    Filter actors by type, name, and classification.
    """
    # Actor type filter
    actor_type = django_filters.ChoiceFilter(
        field_name='polymorphic_ctype__model',
        choices=[
            ('person', 'Person'),
            ('organization', 'Organization'),
        ],
        help_text='Filter by actor type (person or organization)'
    )

    # Name search
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        help_text='Search by actor name (case-insensitive)'
    )

    # Organization classification filter (only applies to organizations)
    classification = django_filters.CharFilter(
        field_name='organization__classification',
        lookup_expr='iexact',
        help_text='Filter organizations by classification (e.g., "Political Party")'
    )

    class Meta:
        model = models.Actor
        fields = ['actor_type', 'name', 'classification']


class DateRangeFilter(django_filters.Filter):
    """
    Custom filter for temporal queries with ?at_date= parameter.

    Filters objects that were active at a specific date based on start_date/end_date.
    """
    def filter(self, qs, value):
        if value is None:
            return qs

        # Filter for records active at the given date
        # Active means: start_date <= value AND (end_date >= value OR end_date is NULL)
        return qs.filter(
            Q(start_date__lte=value) &
            (Q(end_date__gte=value) | Q(end_date__isnull=True))
        )


class MembershipFilterSet(django_filters.FilterSet):
    """
    Filter memberships with temporal support.

    Supports ?at_date= for showing memberships active at a specific date.
    """
    # Temporal filter
    at_date = DateRangeFilter(
        help_text='Show memberships active at this date (YYYY-MM-DD)'
    )

    # Date range filters
    start_after = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='gte',
        help_text='Filter memberships starting on or after this date'
    )
    start_before = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='lte',
        help_text='Filter memberships starting on or before this date'
    )
    end_after = django_filters.DateFilter(
        field_name='end_date',
        lookup_expr='gte',
        help_text='Filter memberships ending on or after this date'
    )
    end_before = django_filters.DateFilter(
        field_name='end_date',
        lookup_expr='lte',
        help_text='Filter memberships ending on or before this date'
    )

    # Role/organization filters
    role = django_filters.CharFilter(
        field_name='role',
        lookup_expr='icontains',
        help_text='Filter by role'
    )
    organization_name = django_filters.CharFilter(
        field_name='organization__name',
        lookup_expr='icontains',
        help_text='Filter by organization name'
    )

    class Meta:
        model = models.Membership
        fields = [
            'at_date',
            'start_after', 'start_before',
            'end_after', 'end_before',
            'role', 'organization_name',
        ]
