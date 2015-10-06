from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User, Group
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, permissions, generics, renderers
from rest_framework.pagination import PageNumberPagination
from api.serializers import DonationSerializer, ActorSerializer

from datafetch import models


class ActorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = models.Actor.objects.all()
    serializer_class = ActorSerializer


class DonationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = models.Donation.objects.all().order_by('-received_date')
    serializer_class = DonationSerializer


class ActorReceivedDonationsFromListViewSet(generics.ListAPIView):

    serializer_class = DonationSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        actor = get_object_or_404(models.Actor, pk=self.kwargs['pk'])
        queryset = actor.received_donations_from.all()
        return queryset


class ActorDonatedToListViewSet(generics.ListAPIView):

    serializer_class = DonationSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        actor = get_object_or_404(models.Actor, pk=self.kwargs['pk'])
        queryset = actor.donated_to.all()
        return queryset
