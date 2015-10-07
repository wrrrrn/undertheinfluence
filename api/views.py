from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User, Group
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, permissions, generics, renderers
from rest_framework.pagination import PageNumberPagination
from api.serializers import DonationSerializer, ActorSerializer, ConsultancySerializer

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


class InfluenceListViewSet(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def apply_filters(self, fk, search_field):
        actor = get_object_or_404(models.Actor, pk=self.kwargs['pk'])
        queryset = getattr(actor, fk)

        search = self.request.GET.get('search')
        if search:
            query = {'{}__icontains'.format(search_field): search}
            queryset = queryset.filter(**query)
        sort = self.request.GET.get('sort')
        if sort:
            # if sort == 'donor':
            #     sort = 'donor__name'
            order = '-' if self.request.GET.get('order') == 'desc' else ''
            queryset = queryset.order_by(order + sort)
        return queryset.all()


class ActorReceivedDonationsFromListViewSet(InfluenceListViewSet):
    serializer_class = DonationSerializer

    def get_queryset(self):
        return self.apply_filters("received_donations_from", search_field="donor__name")


class ActorDonatedToListViewSet(InfluenceListViewSet):
    serializer_class = DonationSerializer

    def get_queryset(self):
        return self.apply_filters("donated_to", search_field="recipient__name")


class ActorHasUsedAgenciesListViewSet(InfluenceListViewSet):
    serializer_class = ConsultancySerializer

    def get_queryset(self):
        return self.apply_filters("consulting_agencies", search_field="agency__name")


class ActorHasConsultedForListViewSet(InfluenceListViewSet):
    serializer_class = ConsultancySerializer

    def get_queryset(self):
        return self.apply_filters("consulting_clients", search_field="client__name")
