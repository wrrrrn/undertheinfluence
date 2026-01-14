"""
Temporal query utilities for UnderTheInfluence.

This module provides functions for querying time-bound relationships,
particularly party affiliations at specific historical dates.

Phase 3.1 Implementation - Historical Party Attribution
"""

from datetime import date
from typing import Optional

from django.db.models import Q


def get_party_at_date(person, query_date: date):
    """
    Get the political party a person belonged to at a specific date.

    This function performs a temporal query on PartyMembership records to
    find the party affiliation that was active on the given date.

    Args:
        person: A Person instance
        query_date: A date object or string (YYYY-MM-DD) to query

    Returns:
        Organization instance (the party) or None if no membership found

    Example:
        >>> from datetime import date
        >>> from datafetch.models import Person
        >>> from datafetch.utils.temporal import get_party_at_date
        >>>
        >>> person = Person.objects.get(name="Tony Blair")
        >>> party = get_party_at_date(person, date(1997, 5, 1))
        >>> print(party.name)  # "Labour Party"
        >>>
        >>> # Can also use string dates
        >>> party = get_party_at_date(person, "1997-05-01")

    Implementation Notes:
        - If multiple parties match (e.g., Labour + Co-operative Party),
          returns the first match ordered by start_date DESC
        - Handles both current memberships (end_date=NULL) and historical ones
        - Returns None if person has no party membership on that date

    Related:
        - PartyMembership model (datafetch.models.influence_mapping)
        - API endpoint: /api/v2/aggregates/party-donations/?at_date=YYYY-MM-DD
    """
    # Import here to avoid circular import
    from datafetch.models import PartyMembership

    # Convert string to date if needed
    if isinstance(query_date, str):
        from datetime import datetime
        query_date = datetime.strptime(query_date, '%Y-%m-%d').date()

    # Query for party membership active on the given date
    membership = PartyMembership.objects.filter(
        person=person,
        start_date__lte=query_date,
    ).filter(
        # Either end_date is after query_date, or end_date is null (current)
        Q(end_date__gte=query_date) | Q(end_date__isnull=True)
    ).order_by('-start_date').first()

    return membership.party if membership else None


def get_all_parties_at_date(person, query_date: date):
    """
    Get all political parties a person belonged to at a specific date.

    Some people hold dual party memberships (e.g., Labour + Co-operative Party).
    This function returns all matching parties.

    Args:
        person: A Person instance
        query_date: A date object or string (YYYY-MM-DD) to query

    Returns:
        QuerySet of Organization instances (parties)

    Example:
        >>> parties = get_all_parties_at_date(person, "2015-05-07")
        >>> for party in parties:
        ...     print(party.name)
        Labour Party
        Co-operative Party
    """
    from datafetch.models import PartyMembership, Organization

    # Convert string to date if needed
    if isinstance(query_date, str):
        from datetime import datetime
        query_date = datetime.strptime(query_date, '%Y-%m-%d').date()

    # Get all matching party memberships
    party_ids = PartyMembership.objects.filter(
        person=person,
        start_date__lte=query_date,
    ).filter(
        Q(end_date__gte=query_date) | Q(end_date__isnull=True)
    ).values_list('party_id', flat=True)

    return Organization.objects.filter(id__in=party_ids)


def get_party_membership_timeline(person):
    """
    Get the complete party membership timeline for a person.

    Returns all party memberships ordered chronologically, useful for
    displaying a person's party history on their profile page.

    Args:
        person: A Person instance

    Returns:
        QuerySet of PartyMembership instances, ordered by start_date DESC

    Example:
        >>> timeline = get_party_membership_timeline(person)
        >>> for membership in timeline:
        ...     print(f"{membership.start_date}: {membership.party.name}")
        2020-01-01: Labour Party
        2015-05-07: Conservative and Unionist Party
        2010-05-06: Conservative and Unionist Party
    """
    from datafetch.models import PartyMembership

    return PartyMembership.objects.filter(
        person=person
    ).select_related('party').order_by('-start_date')


def get_donations_by_party_at_date(query_date: date, party_id: Optional[int] = None):
    """
    Aggregate donations by the recipient's party affiliation at the time of donation.

    This enables accurate historical party attribution - donations to an MP are
    attributed to the party they belonged to when the donation was received.

    Args:
        query_date: Filter donations received on or before this date
        party_id: Optional party ID to filter by specific party

    Returns:
        QuerySet with aggregated donation totals by party

    Example:
        >>> from datafetch.utils.temporal import get_donations_by_party_at_date
        >>> from datetime import date
        >>>
        >>> # Get all party donations up to 2015 election
        >>> results = get_donations_by_party_at_date(date(2015, 5, 7))
        >>>
        >>> # Get Labour party donations only
        >>> labour_donations = get_donations_by_party_at_date(
        ...     date(2020, 1, 1),
        ...     party_id=labour_party.id
        ... )

    API Endpoint:
        This function powers the /api/v2/aggregates/party-donations/ endpoint:
        GET /api/v2/aggregates/party-donations/?at_date=2015-05-07&party_id=123
    """
    from django.db.models import Sum, Count, F
    from datafetch.models import Donation, PartyMembership

    # Base query: donations to people with party memberships
    donations = Donation.objects.filter(
        received_date__lte=query_date,
        recipient__person_memberships__start_date__lte=F('received_date'),
    ).filter(
        Q(recipient__person_memberships__end_date__gte=F('received_date')) |
        Q(recipient__person_memberships__end_date__isnull=True)
    )

    # Filter by specific party if provided
    if party_id:
        donations = donations.filter(recipient__person_memberships__party_id=party_id)

    # Aggregate by party
    return donations.values(
        'recipient__person_memberships__party__id',
        'recipient__person_memberships__party__name',
    ).annotate(
        total_donated=Sum('value'),
        donation_count=Count('id'),
    ).order_by('-total_donated')
