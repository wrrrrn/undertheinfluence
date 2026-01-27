"""
Serializers for API v2

Provides JSON serialization for API responses with canonical field resolution.
"""

from rest_framework import serializers
from datafetch import models


class ActorSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight actor summary for Data Cards and listings.

    Includes: id, name, actor_type, classification (for orgs), image (for persons)
    """
    actor_type = serializers.SerializerMethodField()
    classification = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = models.Actor
        fields = ['id', 'name', 'actor_type', 'classification', 'image']

    def get_actor_type(self, obj):
        """Return 'person' or 'organization'"""
        return obj.polymorphic_ctype.model

    def get_classification(self, obj):
        """Return classification for organizations, None for persons"""
        if isinstance(obj, models.Organization):
            return obj.classification
        return None

    def get_image(self, obj):
        """Return image URL for persons, None for organizations"""
        if isinstance(obj, models.Person):
            return obj.image
        return None


class DonationSerializer(serializers.ModelSerializer):
    """
    Donation serializer with canonical field resolution.

    Uses effective_donor and effective_recipient to resolve merged actors.
    """
    donor = ActorSummarySerializer(source='effective_donor', read_only=True)
    recipient = ActorSummarySerializer(source='effective_recipient', read_only=True)

    class Meta:
        model = models.Donation
        fields = [
            'id', 'donor', 'recipient',
            'value', 'received_date', 'accepted_date', 'reported_date',
            'category', 'nature', 'purpose',
            'created', 'modified'
        ]


class ConsultancySerializer(serializers.ModelSerializer):
    """
    Consultancy serializer with canonical field resolution.

    Uses effective_agency to resolve merged agencies.
    """
    agency = ActorSummarySerializer(source='effective_agency', read_only=True)
    client = ActorSummarySerializer(read_only=True)

    class Meta:
        model = models.Consultancy
        fields = [
            'id', 'agency', 'client',
            'start_date', 'end_date',
            'label', 'source',
            'created', 'modified'
        ]


class MeetingAttendeeSerializer(serializers.ModelSerializer):
    """
    Serializer for attendees of ministerial meetings.
    """
    actor = ActorSummarySerializer(source='effective_actor', read_only=True)

    class Meta:
        model = models.MeetingAttendee
        fields = ['id', 'actor', 'actor_name_raw']


class MinisterialMeetingSerializer(serializers.ModelSerializer):
    """
    Serializer for ministerial meetings.
    """
    minister = ActorSummarySerializer(read_only=True)
    department = ActorSummarySerializer(read_only=True)
    attendees = MeetingAttendeeSerializer(many=True, read_only=True)

    class Meta:
        model = models.MinisterialMeeting
        fields = [
            'id', 'minister', 'department', 'meeting_date',
            'purpose', 'organisation_met_raw', 'is_roundtable',
            'attendees', 'source_url'
        ]


class TopDonorSerializer(serializers.Serializer):
    """
    Serializer for top donor aggregate results.

    Returns: actor (summary), total_donated, donation_count, is_lobbying_client
    """
    actor = ActorSummarySerializer()
    total_donated = serializers.DecimalField(max_digits=15, decimal_places=2)
    donation_count = serializers.IntegerField()
    is_lobbying_client = serializers.BooleanField(required=False)


class TopRecipientSerializer(serializers.Serializer):
    """
    Serializer for top recipient aggregate results.

    Returns: actor (summary), total_received, donation_count
    """
    actor = ActorSummarySerializer()
    total_received = serializers.DecimalField(max_digits=15, decimal_places=2)
    donation_count = serializers.IntegerField()


class PartyDonationSerializer(serializers.Serializer):
    """
    Serializer for party-level donation aggregates.

    Returns: party (name, id), total_received, donation_count, donor_count
    """
    party = ActorSummarySerializer()
    total_received = serializers.DecimalField(max_digits=15, decimal_places=2)
    donation_count = serializers.IntegerField()
    donor_count = serializers.IntegerField()


class DualInfluenceSerializer(serializers.Serializer):
    """
    Serializer for organizations that both lobby AND donate.

    Returns: organization, total_donated, total_lobbied_for, activity_span
    """
    organization = ActorSummarySerializer()
    total_donated = serializers.DecimalField(max_digits=15, decimal_places=2)
    donation_count = serializers.IntegerField()
    lobbying_count = serializers.IntegerField()
    first_activity = serializers.DateField()
    last_activity = serializers.DateField()


class NetworkStatsSerializer(serializers.Serializer):
    """
    Serializer for relationship network statistics.

    Returns: total_actors, total_donations, total_consultancies, network_density, etc.
    """
    total_actors = serializers.IntegerField()
    total_persons = serializers.IntegerField()
    total_organizations = serializers.IntegerField()
    total_donations = serializers.IntegerField()
    total_donation_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_consultancies = serializers.IntegerField()
    unique_donors = serializers.IntegerField()
    unique_recipients = serializers.IntegerField()
    unique_agencies = serializers.IntegerField()
    unique_clients = serializers.IntegerField()
    date_range_start = serializers.DateField()
    date_range_end = serializers.DateField()


# ===========================
# Actor Detail Serializers
# ===========================

class ActorDetailSerializer(serializers.ModelSerializer):
    """
    Detailed actor serializer with relationship counts and aggregates.

    Used for /api/v2/actors/{id}/ endpoint.
    """
    actor_type = serializers.SerializerMethodField()
    classification = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    # Aggregated relationship data (annotated in view)
    donations_made_count = serializers.IntegerField(read_only=True, required=False)
    donations_received_count = serializers.IntegerField(read_only=True, required=False)
    total_donated = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True, required=False)
    total_received = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True, required=False)
    consultancies_as_client = serializers.IntegerField(read_only=True, required=False)
    consultancies_as_agency = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = models.Actor
        fields = [
            'id', 'name', 'actor_type', 'classification', 'image',
            'start_date', 'end_date',
            'donations_made_count', 'donations_received_count',
            'total_donated', 'total_received',
            'consultancies_as_client', 'consultancies_as_agency',
        ]

    def get_actor_type(self, obj):
        """Return 'person' or 'organization'"""
        return obj.polymorphic_ctype.model

    def get_classification(self, obj):
        """Return classification for organizations, None for persons"""
        if isinstance(obj, models.Organization):
            return obj.classification
        return None

    def get_image(self, obj):
        """Return image URL for persons, None for organizations"""
        if isinstance(obj, models.Person):
            return obj.image
        return None


class DonationDetailSerializer(serializers.ModelSerializer):
    """
    Detailed donation serializer for relationship endpoints.

    Used for /api/v2/actors/{id}/donations-made/, etc.
    """
    donor = ActorSummarySerializer(read_only=True)
    recipient = ActorSummarySerializer(read_only=True)
    donor_key_people = serializers.SerializerMethodField()

    class Meta:
        model = models.Donation
        fields = [
            'id', 'donor', 'recipient', 'value',
            'donation_type', 'nature_of_donation',
            'received_date', 'accepted_date', 'reported_date',
            'accounting_unit_name', 'accounting_units_as_central_party',
            'purpose_of_visit',
            'is_bequest', 'is_aggregation', 'is_sponsorship',
            'donor_key_people'
        ]

    def get_donor_key_people(self, obj):
        """Fetch up to 3 key people (Directors/PSCs) for the donor organization."""
        if not obj.donor_id:
            return []
            
        # Only relevant if donor is an Organization
        if obj.donor.polymorphic_ctype.model != 'organization':
            return []

        # Find key memberships: Directors and Beneficial Owners
        from django.db.models import Q
        from datafetch.models import Membership
        
        # We query Membership directly using organization_id=donor_id
        # This works because Organization inherits from Actor (shared PK)
        key_memberships = Membership.objects.filter(
            organization_id=obj.donor_id
        ).filter(
            Q(role__iexact='Director') | 
            Q(role__icontains='Beneficial Owner') |
            Q(role__icontains='Secretary')
        ).select_related('person').order_by('role')[:4]

        return [
            {
                'id': m.person.id,
                'name': m.person.name,
                'role': m.role
            }
            for m in key_memberships
        ]


class ConsultancyDetailSerializer(serializers.ModelSerializer):
    """
    Detailed consultancy serializer for relationship endpoints.

    Used for /api/v2/actors/{id}/consultancies/, etc.
    """
    agency = ActorSummarySerializer(read_only=True)
    client = ActorSummarySerializer(read_only=True)

    class Meta:
        model = models.Consultancy
        fields = [
            'id', 'agency', 'client',
            'label', 'start_date', 'end_date',
            'source',
        ]


class MembershipDetailSerializer(serializers.ModelSerializer):
    """
    Detailed membership serializer for actor relationship endpoints.
    """
    person = ActorSummarySerializer(read_only=True)
    organization = ActorSummarySerializer(read_only=True)

    class Meta:
        from datafetch.models import Membership
        model = Membership
        fields = [
            'id', 'person', 'organization',
            'label', 'role', 'start_date', 'end_date',
        ]


class DonorConcentrationSerializer(serializers.Serializer):
    """
    Serializer for donor concentration analysis.

    Returns:
    - total_donors: Total number of donors
    - total_donated: Total amount donated
    - herfindahl_index: Concentration metric (0-1, higher = more concentrated)
    - top_10_percent_share: % of total donated by top 10% of donors
    - top_donor_share: % of total donated by single largest donor
    - gini_coefficient: Income inequality metric (0-1, higher = more unequal)
    - concentration_category: 'highly_concentrated', 'moderately_concentrated', or 'dispersed'
    """
    total_donors = serializers.IntegerField()
    total_donated = serializers.DecimalField(max_digits=15, decimal_places=2)
    herfindahl_index = serializers.FloatField()
    top_10_percent_share = serializers.FloatField()
    top_donor_share = serializers.FloatField()
    gini_coefficient = serializers.FloatField()
    concentration_category = serializers.CharField()


class HomepageStatsSerializer(serializers.Serializer):
    """
    Serializer for homepage key metrics.

    Returns:
    - total_donations: Count of all donation records
    - total_value: Sum of all donation values (in pence)
    - concentration_top_1_percent: Decimal percentage (0.65 = 65%)
    - concentration_donors_count: Number of donors in top 1.3%
    - dual_influence_count: Count of organizations that both donate and lobby
    - timestamp: ISO timestamp for "Data as of" display
    """
    total_donations = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    concentration_top_1_percent = serializers.FloatField()
    concentration_donors_count = serializers.IntegerField()
    dual_influence_count = serializers.IntegerField()
    timestamp = serializers.DateTimeField()


class PoliticalPartySerializer(serializers.ModelSerializer):
    """
    Serializer for political parties.
    """
    is_governing = serializers.SerializerMethodField()
    mp_count = serializers.IntegerField(read_only=True)
    lord_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.Organization
        fields = ['id', 'name', 'is_governing', 'mp_count', 'lord_count']

    def get_is_governing(self, obj):
        # TODO: Move to settings
        GOVERNING_PARTIES = ['Labour Party', 'Labour', 'Labour/Co-operative']
        return obj.name in GOVERNING_PARTIES


class PoliticianSerializer(serializers.ModelSerializer):
    """
    Serializer for politicians with current status annotations.
    """
    image = serializers.SerializerMethodField()
    current_party = serializers.SerializerMethodField()
    current_role = serializers.SerializerMethodField()
    is_minister = serializers.SerializerMethodField()
    ministerial_role = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Person
        fields = [
            'id', 'name', 'image', 
            'current_party', 'current_role', 
            'is_minister', 'ministerial_role'
        ]

    def get_image(self, obj):
        return obj.image

    def get_current_party(self, obj):
        # Look for active party membership
        if hasattr(obj, 'active_memberships'):
            for m in obj.active_memberships:
                if m.on_behalf_of and m.on_behalf_of.classification == 'Political Party':
                    return ActorSummarySerializer(m.on_behalf_of).data
        return None

    def get_current_role(self, obj):
        if hasattr(obj, 'active_memberships'):
            # Prefer MP role
            for m in obj.active_memberships:
                if 'Member of Parliament' in (m.role or ''):
                    return {
                        'title': m.label or m.role,
                        'start_date': m.start_date,
                        'type': 'Member of Parliament'
                    }
            # Fallback to Lord/Peer
            for m in obj.active_memberships:
                role = m.role or ''
                if 'Lord' in role or 'Peer' in role or 'Baron' in role:
                    return {
                        'title': m.label or m.role,
                        'start_date': m.start_date,
                        'type': 'Peer'
                    }
        return None

    def get_is_minister(self, obj):
        if hasattr(obj, 'active_memberships'):
            for m in obj.active_memberships:
                if m.organization and m.organization.classification == 'Executive':
                    return True
        return False

    def get_ministerial_role(self, obj):
        if hasattr(obj, 'active_memberships'):
            for m in obj.active_memberships:
                if m.organization and m.organization.classification == 'Executive':
                    return m.role
        return None
