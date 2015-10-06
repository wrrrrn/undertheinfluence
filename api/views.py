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
        queryset = actor.received_donations_from
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(donor__name__icontains=search)
        sort = self.request.GET.get('sort')
        if sort:
            if sort == 'donor':
                sort = 'donor__name'
            order = '-' if self.request.GET.get('order') == 'desc' else ''
            queryset = queryset.order_by(order + sort)
        return queryset.all()


class ActorDonatedToListViewSet(generics.ListAPIView):
    serializer_class = DonationSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        actor = get_object_or_404(models.Actor, pk=self.kwargs['pk'])
        queryset = actor.donated_to
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(donor__name__icontains=search)
        sort = self.request.GET.get('sort')
        if sort:
            if sort == 'recipient':
                sort = 'recipient__name'
            order = '-' if self.request.GET.get('order') == 'desc' else ''
            queryset = queryset.order_by(order + sort)
        return queryset.all()
