from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User, Group
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, permissions
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


class ActorReceivedDonationsFromListViewSet(APIView):

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get(self, request, pk):
        actor = get_object_or_404(models.Actor, pk=pk)
        queryset = actor.received_donations_from.all()
        serializer = DonationSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


class ActorDonatedToListViewSet(APIView):

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get(self, request, pk):
        actor = get_object_or_404(models.Actor, pk=pk)
        queryset = actor.donated_to.all()
        serializer = DonationSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
