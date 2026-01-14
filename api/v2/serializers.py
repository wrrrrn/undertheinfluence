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


class TopDonorSerializer(serializers.Serializer):
    """
    Serializer for top donor aggregate results.

    Returns: actor (summary), total_donated, donation_count
    """
    actor = ActorSummarySerializer()
    total_donated = serializers.DecimalField(max_digits=15, decimal_places=2)
    donation_count = serializers.IntegerField()


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

    class Meta:
        model = models.Donation
        fields = [
            'id', 'donor', 'recipient', 'value',
            'donation_type', 'nature_of_donation',
            'received_date', 'accepted_date', 'reported_date',
            'accounting_unit_name', 'accounting_units_as_central_party',
            'purpose_of_visit',
            'is_bequest', 'is_aggregation', 'is_sponsorship',
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
