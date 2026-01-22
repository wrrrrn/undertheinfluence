from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
# PassThroughManager removed in django-model-utils 3.x - use QuerySet.as_manager() instead
from django.utils.translation import gettext_lazy as _

from .popolo.behaviors import Timestampable, Dateframeable, GenericRelatable
# from .popolo.querysets import DateframeableQuerySet
from datafetch.models import models as popolo_models


# class RelationshipQuerySet(DateframeableQuerySet):
#     pass

class Relationship(Dateframeable, Timestampable, models.Model):
    """
    A relationship between two actors
    see schema at http://popoloproject.com/schemas/membership.json#
    """

    label = models.CharField(_("label"), max_length=512, blank=True, help_text=_("A label describing the relationship"))

    # array of items referencing "http://popoloproject.com/schemas/link.json#"
    links = GenericRelation('Link', help_text="URLs to documents about the relationship")

    source = models.URLField(_("source"), blank=True, null=True, help_text=_("URL to the source that documents the relationship"))

    # array of items referencing "http://popoloproject.com/schemas/identifier.json#"
    identifiers = GenericRelation('Identifier', help_text="Issued identifiers")

    # objects = PassThroughManager.for_queryset_class(RelationshipQuerySet)()

    class Meta:
        abstract = True

    def __str__(self):
        return self.label


class Consultancy(Relationship):
    """
    Lobbying relationship between a client organization and a lobbying agency.

    Phase 3.1 Enhancement: Non-Destructive Entity Resolution
    --------------------------------------------------------
    The canonical_client and canonical_agency fields enable entity resolution
    without losing the original data. When duplicate actors are identified:

    1. Original fields (client, agency) are NEVER modified - audit trail preserved
    2. Canonical fields point to the resolved "true" entity
    3. Use effective_client/effective_agency properties in queries for accuracy

    Example:
        # Unite the Union appears as both "Unite the Union" and "Unite"
        consultancy.client.name = "Unite"  # Original (preserved)
        consultancy.canonical_client.name = "Unite the Union"  # Resolved
        consultancy.effective_client.name = "Unite the Union"  # Use this!
    """
    client = models.ForeignKey(
        popolo_models.Actor,
        related_name='consulting_agencies',
        null=True,
        on_delete=models.SET_NULL,
        help_text="Original client from data source (never modified)"
    )
    agency = models.ForeignKey(
        popolo_models.Actor,
        related_name='consulting_clients',
        null=True,
        on_delete=models.SET_NULL,
        help_text="Original agency from data source (never modified)"
    )

    # Phase 3.1: Canonical fields for entity resolution (non-destructive)
    canonical_client = models.ForeignKey(
        popolo_models.Actor,
        related_name='canonical_consulting_agencies',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Resolved canonical client (set by entity resolution system)"
    )
    canonical_agency = models.ForeignKey(
        popolo_models.Actor,
        related_name='canonical_consulting_clients',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Resolved canonical agency (set by entity resolution system)"
    )

    @property
    def effective_client(self):
        """
        Returns the canonical client if resolved, otherwise the original client.
        Use this property in queries and templates for accurate entity references.
        """
        return self.canonical_client or self.client

    @property
    def effective_agency(self):
        """
        Returns the canonical agency if resolved, otherwise the original agency.
        Use this property in queries and templates for accurate entity references.
        """
        return self.canonical_agency or self.agency

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Consultancy"
        verbose_name_plural = "Consultancies"
        indexes = [
            # Core indexes for aggregate queries
            models.Index(fields=['client', '-start_date'], name='consultancy_client_idx'),
            models.Index(fields=['agency', '-start_date'], name='consultancy_agency_idx'),

            # Canonical field indexes for entity-resolved queries
            models.Index(fields=['canonical_client', '-start_date'], name='consultancy_canon_client_idx'),
            models.Index(fields=['canonical_agency', '-start_date'], name='consultancy_canon_agency_idx'),

            # Date range filtering
            models.Index(fields=['start_date'], name='consultancy_start_idx'),
            models.Index(fields=['end_date'], name='consultancy_end_idx'),
        ]


class Donation(Relationship):
    CATEGORY_CHOICES = (
        "Non Cash",
        "Cash",
        "Impermissible Donor",
        "Visit",
        "Public Funds",
        "Exempt Trust",
        "Permissible Donor Exempt Trust",
        "Total value of donations not reported individually",
        "Unidentified Donor",
    )
    NATURE_CHOICES = (
        "Travel",
        "Sponsorship",
        "Auction prizes",
        "Administration services",
        "Other",
        "Premises",
        "Consultancy services",
        "Staff costs",
        "Advertising",
        "Hospitality",
        "Loan conversion",
        "Short Money (House of Commons)",
        "Designated Organisation (Referendum)",
        "Assistance for Parties (Scottish Parliament)",
        "Policy Development Grant",
        "Cranborne Money (House of Lords)",
        "Other Payment",
        "Start Up Grant (Discontinued)",
    )

    donor = models.ForeignKey(
        popolo_models.Actor,
        related_name='donated_to',
        null=True,
        on_delete=models.SET_NULL,
        help_text="Original donor from data source (never modified)"
    )
    recipient = models.ForeignKey(
        popolo_models.Actor,
        related_name='received_donations_from',
        null=True,
        on_delete=models.SET_NULL,
        help_text="Original recipient from data source (never modified)"
    )

    # Phase 3.1: Canonical fields for entity resolution (non-destructive)
    canonical_donor = models.ForeignKey(
        popolo_models.Actor,
        related_name='canonical_donated_to',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Resolved canonical donor (set by entity resolution system)"
    )
    canonical_recipient = models.ForeignKey(
        popolo_models.Actor,
        related_name='canonical_received_donations_from',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Resolved canonical recipient (set by entity resolution system)"
    )

    value = models.DecimalField(_("value"), blank=True, max_digits=12, decimal_places=2, help_text=_("The monetary value of the donation"))
    donation_type = models.CharField(_("donation type"), max_length=128, help_text=_("The type of donation e.g. cash"))
    nature_of_donation = models.CharField(_("nature of donation"), max_length=128, blank=True, help_text=_("The nature of the donation e.g. hospitality"))
    received_date = models.DateField(_("received date"), null=True, blank=True)
    accepted_date = models.DateField(_("accepted date"), null=True, blank=True)
    reported_date = models.DateField(_("reported date"), null=True, blank=True)
    accounting_unit_name = models.CharField(_("accounting unit name"), max_length=128, blank=True)
    accounting_units_as_central_party = models.BooleanField(_("accounting units as central party"))
    purpose_of_visit = models.CharField(_("purpose of visit"), max_length=512, blank=True)
    is_bequest = models.BooleanField(_("is bequest"))
    is_aggregation = models.BooleanField(_("is aggregation"))
    is_sponsorship = models.BooleanField(_("is sponsorship"))

    def start_date(self):
        return self.accepted_date

    @property
    def effective_donor(self):
        """
        Returns the canonical donor if resolved, otherwise the original donor.

        Use this property in queries, aggregations, and templates for accurate
        entity references. This ensures that donations from duplicate actors
        (e.g., "Unite" and "Unite the Union") are correctly attributed to the
        canonical entity.

        Example:
            # Query top donors using effective (canonical) entities
            from django.db.models import Sum, F, Case, When
            top_donors = Donation.objects.annotate(
                resolved_donor=Case(
                    When(canonical_donor__isnull=False, then=F('canonical_donor')),
                    default=F('donor')
                )
            ).values('resolved_donor').annotate(
                total=Sum('value')
            ).order_by('-total')
        """
        return self.canonical_donor or self.donor

    @property
    def effective_recipient(self):
        """
        Returns the canonical recipient if resolved, otherwise the original recipient.

        Use this property in queries, aggregations, and templates for accurate
        entity references.
        """
        return self.canonical_recipient or self.recipient

    def __str__(self):
        if self.donation_type == "Cash":
            return "Donation of £{:,d}".format(int(self.value))
        if self.donation_type == "Visit":
            return "Donation of £{:,d} (Visit to {})".format(int(self.value), self.purpose_of_visit)
        if self.donation_type == "Non Cash":
            return "Donation of £{:,d} ({})".format(int(self.value), self.nature_of_donation)

    class Meta:
        ordering = ['-received_date']
        verbose_name = "Donation"
        verbose_name_plural = "Donations"
        indexes = [
            # Core indexes for aggregate queries
            models.Index(fields=['donor', '-received_date'], name='donation_donor_date_idx'),
            models.Index(fields=['recipient', '-received_date'], name='donation_recip_date_idx'),
            models.Index(fields=['donor', '-value'], name='donation_donor_val_idx'),
            models.Index(fields=['recipient', '-value'], name='donation_recip_val_idx'),

            # Date range filtering (common query pattern)
            models.Index(fields=['received_date'], name='donation_date_idx'),

            # Canonical field indexes for entity-resolved queries
            models.Index(fields=['canonical_donor', '-received_date'], name='donation_canon_donor_idx'),
            models.Index(fields=['canonical_recipient', '-received_date'], name='donation_canon_recip_idx'),

            # Value filtering
            models.Index(fields=['-value'], name='donation_value_idx'),
        ]


class PartyMembership(Dateframeable, Timestampable, models.Model):
    """
    Temporal tracking of a person's political party affiliation.

    Phase 3.1 Enhancement: Historical Party Attribution
    ---------------------------------------------------
    This model enables accurate historical party attribution for donations
    and other relationships. When aggregating donations by party, we can
    determine which party an MP belonged to at the time of the donation.

    Key Features:
    1. Temporal ranges (start_date, end_date) track party changes over time
    2. Allows querying "What party was this person in on date X?"
    3. Supports overlapping memberships (e.g., Labour + Co-operative Party)
    4. Null end_date indicates current membership

    Example Usage:
        # Find person's party on a specific date
        from datafetch.utils.temporal import get_party_at_date
        party = get_party_at_date(person, date(2015, 5, 7))

        # Query donations with party context at time of donation
        donations = Donation.objects.filter(
            recipient__person_memberships__party=party,
            recipient__person_memberships__start_date__lte=F('received_date'),
        ).filter(
            Q(recipient__person_memberships__end_date__gte=F('received_date')) |
            Q(recipient__person_memberships__end_date__isnull=True)
        )

    Data Sources:
    - ParlParse (MPs' party history from Parliament data)
    - TheyWorkForYou API (party changes)
    - Electoral Commission (party registration changes)
    """
    person = models.ForeignKey(
        'Person',
        related_name='party_memberships',
        on_delete=models.CASCADE,
        help_text="The person who is a member of the political party"
    )

    party = models.ForeignKey(
        'Organization',
        related_name='party_members',
        on_delete=models.CASCADE,
        limit_choices_to={'classification': 'Political Party'},
        help_text="The political party (must have classification='Political Party')"
    )

    role = models.CharField(
        _("role"),
        max_length=128,
        blank=True,
        help_text=_("Role within the party (e.g., 'Leader', 'Deputy Leader', 'Member')")
    )

    # Note: start_date and end_date are inherited from Dateframeable behavior
    # start_date: When the person joined this party
    # end_date: When the person left (null = current member)

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Party Membership"
        verbose_name_plural = "Party Memberships"
        indexes = [
            # Index for temporal queries - finding party at specific date
            models.Index(fields=['person', 'start_date', 'end_date']),
            # Index for finding all members of a party
            models.Index(fields=['party', 'start_date']),
        ]

    def __str__(self):
        date_range = f"{self.start_date or 'Unknown'}"
        if self.end_date:
            date_range += f" - {self.end_date}"
        else:
            date_range += " - Present"

        return f"{self.person.name} → {self.party.name} ({date_range})"

    @property
    def is_current(self):
        """Returns True if this membership has no end_date (currently active)."""
        return self.end_date is None

    def overlaps_with(self, other_membership):
        """
        Check if this membership overlaps with another party membership.

        This is useful for detecting data quality issues (person in two parties
        simultaneously) or legitimate cases (e.g., Labour + Co-operative Party).
        """
        if not isinstance(other_membership, PartyMembership):
            return False

        # If either has no start_date, can't determine overlap
        if not self.start_date or not other_membership.start_date:
            return False

        # Check for overlap
        self_end = self.end_date or '9999-12-31'
        other_end = other_membership.end_date or '9999-12-31'

        return (self.start_date <= other_end and
                self_end >= other_membership.start_date)


class MinisterialMeeting(Dateframeable, Timestampable, models.Model):
    """
    Records meetings between UK ministers and external actors.

    Data source: GOV.UK ministerial transparency publications (quarterly CSV/XLSX files)
    from all government departments (2010-present).

    Roundtable Meetings:
    -------------------
    Meetings with multiple attendees are tracked via MeetingAttendee junction table.
    - is_roundtable=True: Meeting has multiple attendees
    - is_roundtable=False: One-on-one meeting
    - external_actor: Primary/first attendee (for backwards compatibility)
    - attendees: All individual attendees (via MeetingAttendee)

    Entity Resolution Pattern (Phase 3):
    ------------------------------------
    Follows the same non-destructive canonical pattern as Donation/Consultancy:
    - external_actor: Original actor from data source (never modified)
    - canonical_external_actor: Resolved canonical actor (set by entity resolution)
    - Use effective_external_actor property in queries for accuracy

    Example Usage:
        # Query meetings by canonical actor (handles duplicates correctly)
        meetings = MinisterialMeeting.objects.filter(
            canonical_external_actor=google_canonical
        )

        # Count meetings by effective external actor (including roundtable attendees)
        top_actors = MeetingAttendee.objects.values(
            'canonical_actor__name'
        ).annotate(
            meeting_count=Count('meeting', distinct=True)
        ).order_by('-meeting_count')
    """
    # Minister (always Person, not polymorphic Actor)
    minister = models.ForeignKey(
        'Person',
        related_name='ministerial_meetings_as_minister',
        on_delete=models.CASCADE,
        help_text="The minister who attended the meeting"
    )

    # External actor (polymorphic - can be Person or Organization)
    external_actor = models.ForeignKey(
        popolo_models.Actor,
        related_name='ministerial_meetings_as_external',
        null=True,
        on_delete=models.SET_NULL,
        help_text="Original external actor from data source (never modified)"
    )

    # Phase 3: Canonical field for entity resolution (same pattern as Donation)
    canonical_external_actor = models.ForeignKey(
        popolo_models.Actor,
        related_name='canonical_ministerial_meetings',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Resolved canonical actor (set by entity resolution system)"
    )

    # Department
    department = models.ForeignKey(
        popolo_models.Organization,
        related_name='ministerial_meetings',
        on_delete=models.CASCADE,
        help_text="The government department publishing this meeting record"
    )

    # Meeting metadata
    meeting_date = models.DateField(
        help_text="Date the meeting took place"
    )
    purpose = models.TextField(
        blank=True,
        help_text="Purpose or subject of the meeting"
    )
    external_actor_name_raw = models.CharField(
        max_length=2048,
        help_text="Preserve original external actor name exactly as published"
    )
    source_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL to the GOV.UK transparency publication"
    )
    source_quarter = models.CharField(
        max_length=7,
        blank=True,
        help_text="Publication quarter (e.g., '2024-Q1')"
    )

    # Roundtable tracking
    is_roundtable = models.BooleanField(
        default=False,
        help_text="True if meeting has multiple attendees (comma-separated in source)"
    )

    @property
    def effective_external_actor(self):
        """
        Returns the canonical external actor if resolved, otherwise the original.
        Use this property in queries and templates for accurate entity references.
        """
        return self.canonical_external_actor or self.external_actor

    class Meta:
        ordering = ['-meeting_date']
        verbose_name = "Ministerial Meeting"
        verbose_name_plural = "Ministerial Meetings"
        indexes = [
            # Query patterns for aggregate endpoints
            models.Index(fields=['minister', '-meeting_date'], name='meeting_minister_idx'),
            models.Index(fields=['external_actor', '-meeting_date'], name='meeting_external_idx'),
            models.Index(fields=['department', '-meeting_date'], name='meeting_dept_idx'),
            models.Index(fields=['canonical_external_actor', '-meeting_date'], name='meeting_canon_idx'),

            # Date range filtering
            models.Index(fields=['meeting_date'], name='meeting_date_idx'),

            # Source tracking
            models.Index(fields=['source_quarter'], name='meeting_quarter_idx'),
        ]
        constraints = [
            # Prevent exact duplicates from same data source
            models.UniqueConstraint(
                fields=['minister', 'external_actor_name_raw', 'meeting_date', 'department'],
                name='unique_ministerial_meeting'
            )
        ]

    def __str__(self):
        return f"{self.minister.name} met {self.external_actor_name_raw} on {self.meeting_date}"


class MeetingAttendee(Timestampable, models.Model):
    """
    Individual attendee at a ministerial meeting.

    Purpose:
    --------
    Accurately tracks individual organization access to ministers, especially
    for roundtable meetings where multiple organizations attend.

    For one-on-one meetings: Single attendee (same as external_actor)
    For roundtables: Multiple attendees (split from comma-separated list)

    Entity Resolution:
    -----------------
    - actor: Original actor from data source (never modified)
    - canonical_actor: Resolved canonical actor (set by entity resolution)
    - Use effective_actor property in queries for accurate counting

    Example Usage:
        # Count meetings each organization attended (Guardian-style analysis)
        top_actors = MeetingAttendee.objects.values(
            'canonical_actor__name'
        ).annotate(
            meeting_count=Count('meeting', distinct=True),
            one_on_one=Count(Case(When(meeting__is_roundtable=False, then=1))),
            roundtables=Count(Case(When(meeting__is_roundtable=True, then=1)))
        ).order_by('-meeting_count')

        # Tech company access (including roundtables)
        google_access = MeetingAttendee.objects.filter(
            canonical_actor__name='Google LLC'
        ).values('meeting__meeting_date', 'meeting__minister__name')
    """
    meeting = models.ForeignKey(
        'MinisterialMeeting',
        related_name='attendees',
        on_delete=models.CASCADE,
        help_text="The meeting this actor attended"
    )

    actor = models.ForeignKey(
        popolo_models.Actor,
        related_name='meeting_attendances',
        on_delete=models.CASCADE,
        help_text="Original actor from data source (never modified)"
    )

    # Phase 3: Entity resolution
    canonical_actor = models.ForeignKey(
        popolo_models.Actor,
        related_name='canonical_meeting_attendances',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Resolved canonical actor (set by entity resolution system)"
    )

    actor_name_raw = models.CharField(
        max_length=512,
        help_text="Original name as it appeared in source data"
    )

    @property
    def effective_actor(self):
        """
        Returns the canonical actor if resolved, otherwise the original actor.
        Use this property in queries for accurate entity references.
        """
        return self.canonical_actor or self.actor

    class Meta:
        ordering = ['meeting', 'actor']
        verbose_name = "Meeting Attendee"
        verbose_name_plural = "Meeting Attendees"
        indexes = [
            # Query patterns for access analysis
            models.Index(fields=['meeting', 'actor']),
            models.Index(fields=['actor']),
            models.Index(fields=['canonical_actor']),

            # Combined queries
            models.Index(fields=['canonical_actor', 'meeting']),
        ]
        constraints = [
            # Prevent duplicate attendees at same meeting
            models.UniqueConstraint(
                fields=['meeting', 'actor_name_raw'],
                name='unique_meeting_attendee'
            )
        ]

    def __str__(self):
        return f"{self.actor.name} at {self.meeting}"


class ActorResolution(Timestampable, models.Model):
    """
    Tracks potential duplicate actors that should be merged (entity resolution).

    Phase 3.1 Enhancement: Entity Resolution Pipeline
    -------------------------------------------------
    This model stores merge candidates discovered by the entity resolution system.
    Each record represents a potential duplicate pair with a confidence score.

    Confidence Levels:
    1. 1.00 - Identifier Match: External ID match (e.g., Electoral Commission donor ID)
    2. 0.90 - Strong Alias: High-confidence name variant match
    3. 0.85 - Exact Normalization: Exact after strong normalization
    4. 0.70 - Weak Alias: Match after aggressive normalization
    5. 0.40 - Fuzzy: Levenshtein distance suggests similarity

    Resolution Decisions:
    - auto_merge: >= 1.0 (identifier match only, requires manual approval first)
    - review: >= 0.85 (requires manual review and approval)
    - suggest: >= 0.70 (shown to user, not auto-applied)
    - ignore: < 0.70 (not shown, too uncertain)

    Workflow:
    1. Entity resolution command discovers potential duplicates
    2. Creates ActorResolution records with confidence scores
    3. Admin reviews suggestions and approves/rejects
    4. Approved merges set canonical_donor/recipient fields
    5. Original data preserved for audit trail

    Example:
        # "Unite the Union" vs "Unite" discovered during import
        resolution = ActorResolution.objects.create(
            actor1=actor_unite_full,
            actor2=actor_unite_short,
            confidence=0.90,
            decision='review',
            match_reason='strong_alias',
            reviewed_by=None,  # Awaiting review
        )
    """
    DECISION_CHOICES = [
        ('auto_merge', 'Auto-Merge (Identifier Match)'),
        ('review', 'Requires Review'),
        ('suggest', 'Suggestion Only'),
        ('ignore', 'Ignore (Low Confidence)'),
    ]

    MATCH_REASON_CHOICES = [
        ('identifier', 'External Identifier Match'),
        ('exact', 'Exact Name Match'),
        ('known_alias', 'Known Alias (Manual Mapping)'),
        ('substring', 'Substring Match'),
        ('strong_alias', 'Strong Alias Match'),
        ('weak_alias', 'Weak Alias Match'),
        ('fuzzy', 'Fuzzy Name Match'),
        ('acronym', 'Acronym Match'),
    ]

    REVIEW_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved - Merge'),
        ('rejected', 'Rejected - Not Duplicate'),
    ]

    # The two actors being compared
    actor1 = models.ForeignKey(
        'Actor',
        related_name='resolutions_as_actor1',
        on_delete=models.CASCADE,
        help_text="First actor in potential duplicate pair"
    )

    actor2 = models.ForeignKey(
        'Actor',
        related_name='resolutions_as_actor2',
        on_delete=models.CASCADE,
        help_text="Second actor in potential duplicate pair"
    )

    # Which one should be the canonical actor (if approved)
    canonical_actor = models.ForeignKey(
        'Actor',
        related_name='resolutions_as_canonical',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="The canonical actor to use (typically the one with more data)"
    )

    # Confidence and decision
    confidence = models.FloatField(
        help_text="Confidence score (0.0-1.0) based on match quality"
    )

    decision = models.CharField(
        max_length=15,
        choices=DECISION_CHOICES,
        help_text="Recommended action based on confidence level"
    )

    match_reason = models.CharField(
        max_length=20,
        choices=MATCH_REASON_CHOICES,
        help_text="What matched (identifier, strong alias, weak alias, fuzzy)"
    )

    # Review tracking
    review_status = models.CharField(
        max_length=10,
        choices=REVIEW_STATUS_CHOICES,
        default='pending',
        help_text="Whether this has been reviewed and approved/rejected"
    )

    reviewed_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Admin user who reviewed this resolution"
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this was reviewed"
    )

    notes = models.TextField(
        blank=True,
        help_text="Admin notes about why this was approved/rejected"
    )

    class Meta:
        ordering = ['-confidence', '-created_at']
        verbose_name = "Actor Resolution"
        verbose_name_plural = "Actor Resolutions"
        indexes = [
            # Index for finding pending reviews
            models.Index(fields=['review_status', '-confidence']),
            # Index for finding resolutions for a specific actor
            models.Index(fields=['actor1', 'review_status']),
            models.Index(fields=['actor2', 'review_status']),
        ]
        # Prevent duplicate resolution records
        constraints = [
            models.UniqueConstraint(
                fields=['actor1', 'actor2'],
                name='unique_actor_pair'
            ),
        ]

    def __str__(self):
        status_icon = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌',
        }.get(self.review_status, '?')

        return (
            f"{status_icon} {self.actor1.name} ↔ {self.actor2.name} "
            f"({self.confidence:.2f}, {self.get_decision_display()})"
        )

    def approve(self, user, notes=''):
        """Approve this merge and set canonical fields."""
        from django.utils import timezone

        self.review_status = 'approved'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.notes = notes
        self.save()

        # Set canonical actor (use actor1 if not specified)
        if not self.canonical_actor:
            self.canonical_actor = self.actor1
            self.save()

        return self.canonical_actor

    def reject(self, user, notes=''):
        """Reject this merge and clear canonical_actor."""
        from django.utils import timezone

        self.review_status = 'rejected'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.notes = notes
        self.canonical_actor = None  # Clear canonical since not a duplicate
        self.save()


class CompaniesHouseMatch(Timestampable, models.Model):
    """
    Stores potential Companies House matches for Organizations.

    Similar to ActorResolution, this stores matches with confidence scores
    for review before enriching organization data.

    Workflow:
    1. enrich_companies_house command searches CH API
    2. Creates CompaniesHouseMatch records with confidence scores
    3. High confidence (≥0.95) matches are auto-approved
    4. Medium confidence (0.75-0.94) matches await review
    5. Approved matches trigger enrichment (add identifier, founding_date, etc.)

    Confidence Thresholds:
    - ≥ 0.85: auto_approve - Enrich immediately
    - 0.75-0.84: review - Store for admin review
    - < 0.75: ignore - Don't store

    Example:
        match = CompaniesHouseMatch.objects.create(
            organization=org,
            company_number='03140273',
            company_name='GRAYLING COMMUNICATIONS LIMITED',
            confidence=0.90,
            match_reason='exact_core',
            status='pending',
        )
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('auto_approved', 'Auto-Approved (High Confidence)'),
    ]

    MATCH_REASON_CHOICES = [
        ('identifier', 'Existing Identifier'),
        ('exact', 'Exact Name Match'),
        ('exact_normalized', 'Exact After Normalization'),
        ('exact_camelcase', 'Exact After CamelCase Split'),
        ('exact_core', 'Exact Core Name'),
        ('exact_core_camel', 'Exact Core (CamelCase)'),
        ('query_subset', 'Query Words Subset of CH'),
        ('ch_subset', 'CH Words Subset of Query'),
        ('jaccard', 'Jaccard Word Similarity'),
        ('first_word_match', 'First Word Match'),
        ('prefix_match', 'Prefix Match'),
        ('fuzzy', 'Fuzzy Levenshtein Match'),
    ]

    # The organization being matched
    organization = models.ForeignKey(
        'Organization',
        related_name='companies_house_matches',
        on_delete=models.CASCADE,
        help_text="Organization to match to Companies House"
    )

    # Companies House data
    company_number = models.CharField(
        max_length=20,
        help_text="Companies House company number"
    )

    company_name = models.CharField(
        max_length=500,
        help_text="Company name from Companies House"
    )

    company_status = models.CharField(
        max_length=50,
        blank=True,
        help_text="Company status (active, dissolved, etc.)"
    )

    company_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Company type from CH (ltd, plc, llp, etc.)"
    )

    # Match quality
    confidence = models.FloatField(
        help_text="Confidence score (0.0-1.0) based on match quality"
    )

    match_reason = models.CharField(
        max_length=30,
        help_text="How the match was determined"
    )

    match_details = models.TextField(
        blank=True,
        help_text="Detailed description of match (e.g., 'Grayling → GRAYLING COMMUNICATIONS LIMITED')"
    )

    # Review status
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Review status"
    )

    reviewed_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Admin who reviewed this match"
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this was reviewed"
    )

    notes = models.TextField(
        blank=True,
        help_text="Admin notes"
    )

    # Track if enrichment has been applied
    enriched = models.BooleanField(
        default=False,
        help_text="Whether organization has been enriched with CH data"
    )

    enriched_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When enrichment was applied"
    )

    class Meta:
        ordering = ['-confidence', '-created_at']
        verbose_name = "Companies House Match"
        verbose_name_plural = "Companies House Matches"
        indexes = [
            models.Index(fields=['status', '-confidence']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['company_number']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'company_number'],
                name='unique_org_company_match'
            ),
        ]

    def __str__(self):
        status_icon = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌',
            'auto_approved': '🤖',
        }.get(self.status, '?')

        return (
            f"{status_icon} {self.organization.name} → {self.company_name} "
            f"({self.confidence:.2f})"
        )

    def approve(self, user=None, notes='', auto=False):
        """
        Approve this match and trigger enrichment.

        Args:
            user: Admin user who approved (None for auto-approval)
            notes: Optional notes
            auto: If True, mark as auto_approved
        """
        from django.utils import timezone

        self.status = 'auto_approved' if auto else 'approved'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.notes = notes
        self.save()

        # Trigger enrichment
        self.enrich_organization()

    def reject(self, user, notes=''):
        """Reject this match."""
        from django.utils import timezone

        self.status = 'rejected'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.notes = notes
        self.save()

    def enrich_organization(self):
        """
        Apply Companies House data to the organization.

        Adds:
        - Company number as Identifier
        - Fetches full profile and applies additional data
        """
        from django.contrib.contenttypes.models import ContentType
        from django.utils import timezone
        from datafetch.models import Identifier

        if self.enriched:
            return  # Already enriched

        org = self.organization
        org_content_type = ContentType.objects.get_for_model(org.__class__)

        # Add company number as identifier
        Identifier.objects.get_or_create(
            content_type=org_content_type,
            object_id=org.pk,
            scheme='uk.gov.companieshouse',
            defaults={'identifier': self.company_number}
        )

        self.enriched = True
        self.enriched_at = timezone.now()
        self.save()

    @classmethod
    def get_pending_for_review(cls, min_confidence=0.75):
        """Get pending matches ordered by confidence for review."""
        return cls.objects.filter(
            status='pending',
            confidence__gte=min_confidence
        ).select_related('organization').order_by('-confidence')


class Note(Timestampable, GenericRelatable, models.Model):
    content = models.TextField(_("content"), blank=True, help_text=_("A note about this person or organization"))
