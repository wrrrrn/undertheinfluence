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

    # Classification filters (for organizations)
    donor_classification = django_filters.CharFilter(
        field_name='donor__organization__classification',
        lookup_expr='iexact',
        help_text='Filter by donor organization classification (e.g., "Trade Union", "Company")'
    )
    exclude_donor_classification = django_filters.CharFilter(
        field_name='donor__organization__classification',
        lookup_expr='iexact',
        exclude=True,
        help_text='Exclude donors with this classification'
    )

    # Lobbying overlap filter
    has_lobbying = django_filters.BooleanFilter(
        method='filter_has_lobbying',
        help_text='Filter to show only donors who are also lobbying clients (true) or non-lobbyists (false)'
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

    def filter_has_lobbying(self, queryset, name, value):
        """
        Filter donations to show only donors who are also lobbying clients.

        If value is True: only show donations from donors who are lobbying clients
        If value is False: only show donations from donors who are NOT lobbying clients
        """
        if value is None:
            return queryset

        # Get all donor IDs who are lobbying clients
        lobbying_donor_ids = models.Consultancy.objects.values_list('client_id', flat=True).distinct()

        if value:
            # Only donors who are lobbying clients
            return queryset.filter(donor_id__in=lobbying_donor_ids)
        else:
            # Only donors who are NOT lobbying clients
            return queryset.exclude(donor_id__in=lobbying_donor_ids)

    class Meta:
        model = models.Donation
        fields = [
            'received_after', 'received_before',
            'value_min', 'value_max',
            'donor_type', 'recipient_type',
            'donor_classification', 'exclude_donor_classification',
            'has_lobbying',
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


class MinisterialMeetingFilterSet(django_filters.FilterSet):
    """
    Filter ministerial meetings by date, department, minister, etc.
    """
    # Date range filters
    date_after = django_filters.DateFilter(
        field_name='meeting_date',
        lookup_expr='gte',
        help_text='Filter meetings on or after this date (YYYY-MM-DD)'
    )
    date_before = django_filters.DateFilter(
        field_name='meeting_date',
        lookup_expr='lte',
        help_text='Filter meetings on or before this date (YYYY-MM-DD)'
    )

    # Entity filters
    department = django_filters.NumberFilter(
        field_name='department__id',
        help_text='Filter by department ID'
    )
    minister = django_filters.NumberFilter(
        field_name='minister__id',
        help_text='Filter by minister (person ID)'
    )
    external_actor = django_filters.NumberFilter(
        method='filter_external_actor',
        help_text='Filter by external actor ID (via attendees)'
    )

    # Text search
    organisation_search = django_filters.CharFilter(
        field_name='organisation_met_raw',
        lookup_expr='icontains',
        help_text='Search raw organisation name'
    )
    purpose_search = django_filters.CharFilter(
        field_name='purpose',
        lookup_expr='icontains',
        help_text='Search meeting purpose'
    )

    # Roundtable filter
    is_roundtable = django_filters.BooleanFilter(
        field_name='is_roundtable',
        help_text='Filter by roundtable status'
    )

    def filter_external_actor(self, queryset, name, value):
        """
        Filter meetings where a specific actor (or its canonical version) attended.
        """
        if not value:
            return queryset
        
        # Find meetings where this actor attended
        # Note: MeetingAttendee has 'actor' and 'canonical_actor'
        # We should check both to be comprehensive, or rely on effective_actor logic in queries
        return queryset.filter(
            Q(attendees__actor_id=value) | 
            Q(attendees__canonical_actor_id=value)
        ).distinct()

    class Meta:
        model = models.MinisterialMeeting
        fields = [
            'date_after', 'date_before',
            'department', 'minister', 'external_actor',
            'is_roundtable'
        ]


class PoliticianFilter(django_filters.FilterSet):
    """
    Filter politicians by party, role, and government status.
    """
    search = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        help_text='Search by name'
    )
    party = django_filters.NumberFilter(
        method='filter_party',
        help_text='Filter by current party ID'
    )
    role_type = django_filters.ChoiceFilter(
        method='filter_role_type',
        choices=[
            ('mp', 'MP'),
            ('lord', 'Peer'),
            ('minister', 'Minister'),
        ],
        help_text='Filter by role type'
    )
    is_current = django_filters.BooleanFilter(
        method='filter_is_current',
        help_text='Show only currently serving politicians'
    )
    govt_status = django_filters.ChoiceFilter(
        method='filter_govt_status',
        choices=[
            ('government', 'Government'),
            ('opposition', 'Opposition'),
            ('other', 'Other'),
        ],
        help_text='Filter by government status'
    )

    def filter_party(self, queryset, name, value):
        # Filter by active party membership
        # Note: This is an approximation until we denormalize current_party
        from django.utils import timezone
        today = timezone.now().date().isoformat()
        
        return queryset.filter(
            memberships__on_behalf_of_id=value,
            memberships__start_date__lte=today,
            memberships__end_date__isnull=True
        ).distinct()

    def filter_role_type(self, queryset, name, value):
        from django.utils import timezone
        today = timezone.now().date().isoformat()
        
        if value == 'mp':
            return queryset.filter(
                memberships__role__icontains='Member of Parliament',
                memberships__end_date__isnull=True  # Simplification for "current"
            ).distinct()
        elif value == 'lord':
            return queryset.filter(
                memberships__role__icontains='Lord',
                memberships__end_date__isnull=True
            ).distinct()
        elif value == 'minister':
            return queryset.filter(
                memberships__organization__classification='Executive',
                memberships__end_date__isnull=True
            ).distinct()
        return queryset

    def filter_is_current(self, queryset, name, value):
        if not value:
            return queryset
            
        from django.utils import timezone
        today = timezone.now().date().isoformat()
        
        return queryset.filter(
            Q(memberships__end_date__isnull=True) | 
            Q(memberships__end_date__gte=today)
        ).distinct()

    def filter_govt_status(self, queryset, name, value):
        # Hardcoded for now - should come from settings
        GOVERNING_PARTIES = ['Labour Party', 'Labour', 'Labour/Co-operative']
        MAJOR_OPPOSITION = ['Conservative Party', 'Liberal Democrats', 'Scottish National Party', 'Reform UK', 'Green Party']
        
        if value == 'government':
            return queryset.filter(
                memberships__on_behalf_of__name__in=GOVERNING_PARTIES,
                memberships__end_date__isnull=True
            ).distinct()
        elif value == 'opposition':
            return queryset.filter(
                memberships__on_behalf_of__name__in=MAJOR_OPPOSITION,
                memberships__end_date__isnull=True
            ).distinct()
        elif value == 'other':
            return queryset.exclude(
                memberships__on_behalf_of__name__in=GOVERNING_PARTIES + MAJOR_OPPOSITION
            ).distinct()
        return queryset

    class Meta:
        model = models.Person
        fields = ['search']
