from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from api.serializers import DonationSerializer, ActorSerializer, RelationshipSerializer

from datafetch import models


class ActorViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = models.Actor.objects.all()
    serializer_class = ActorSerializer


class DonationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = models.Donation.objects.all().order_by('-received_date')
    serializer_class = DonationSerializer


class RelationshipViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = models.Relationship.objects.all().order_by('-received_date')
    serializer_class = RelationshipSerializer
