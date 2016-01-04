from rest_framework import serializers

from datafetch import models


class ActorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Actor
        fields = ('id', 'name', 'url',)


class MembershipSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Membership
        fields = ('role',)


class DonationSerializer(serializers.HyperlinkedModelSerializer):
    donor = ActorSerializer()
    recipient = ActorSerializer()
    class Meta:
        model = models.Donation
        fields = ('id', 'donor', 'recipient', 'value', 'nature_of_donation', 'donation_type', 'accepted_date', 'reported_date', 'source',)


class ConsultancySerializer(serializers.HyperlinkedModelSerializer):
    client = ActorSerializer()
    agency = ActorSerializer()
    class Meta:
        model = models.Consultancy
        fields = ('id', 'client', 'agency', 'source', 'start_date', 'end_date',)
