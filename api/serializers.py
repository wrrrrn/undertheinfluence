from django.contrib.auth.models import User, Group
from rest_framework import serializers

from datafetch import models


class ActorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Actor
        fields = ('id', 'name', 'url',)

class DonationSerializer(serializers.HyperlinkedModelSerializer):
    donor = ActorSerializer()
    recipient = ActorSerializer()
    class Meta:
        model = models.Donation
        fields = ('id', 'donor', 'recipient', 'value', 'nature_of_donation', 'donation_type', 'accepted_date', 'reported_date', 'source',)
