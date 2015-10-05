from django.contrib.auth.models import User, Group
from rest_framework import serializers

from datafetch import models


class DonationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Donation
        fields = ('id', 'value', 'donor', 'recipient', 'source',)


class ActorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Actor
        fields = ('id', 'name', 'received_donations_from', 'donated_to',)
