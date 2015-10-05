from django.contrib.auth.models import User, Group
from rest_framework import serializers

from datafetch import models


class ActorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Actor
        fields = ('id', 'name', 'influenced_by', 'influences',)


class DonationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Donation
        fields = ('id', 'value', 'influenced_by', 'influences', 'source',)


class RelationshipSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Relationship
        fields = ('id', 'influenced_by', 'influences', 'source',)
