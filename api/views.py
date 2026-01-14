from django.shortcuts import get_object_or_404
from django.db.models import Prefetch, Q
from rest_framework import viewsets, permissions, generics

from api import serializers
from datafetch import models


class DonationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = models.Donation.objects.all().order_by('-received_date')
    serializer_class = serializers.DonationSerializer


class InfluenceListViewSet(generics.ListAPIView):
    # permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def apply_filters(self, fk, search_field):
        actor = get_object_or_404(models.Actor, pk=self.kwargs['pk'])
        queryset = getattr(actor, fk)

        search = self.request.query_params.get('search')
        if search:
            query = {'{}__icontains'.format(search_field): search}
            queryset = queryset.filter(**query)
        sort = self.request.query_params.get('sort')
        if sort:
            # if sort == 'donor':
            #     sort = 'donor__name'
            order = '-' if self.request.query_params.get('order') == 'desc' else ''
            queryset = queryset.order_by(order + sort)
        return queryset.all()


class ActorViewSet(InfluenceListViewSet):
    serializer_class = serializers.ActorSerializer

    def get_queryset(self):
        queryset = models.Actor.objects.all()
        search = self.request.query_params.get('search')
        if search is not None:
            queryset = queryset.filter(name__icontains=search)
        return queryset


class PoliticianViewSet(InfluenceListViewSet):
    serializer_class = serializers.ActorSerializer

    def get_queryset(self):
        queryset = models.Person.objects.filter(memberships__isnull=False).distinct().order_by('name').prefetch_related(Prefetch('memberships'))
        search = self.request.query_params.get('search')
        if search is not None:
            queryset = queryset.filter(name__icontains=search)
        role = self.request.query_params.get('role')
        if role is not None:
            k = { "memberships__role": role }
            date = self.request.query_params.get('date')
            if date is not None:
                k["memberships__start_date__lte"] = date
                queryset = queryset.filter(Q(memberships__end_date__gte=date, **k) | Q(memberships__end_date__isnull=True, **k))
            else:
                queryset = queryset.filter(**k)
        return queryset


class MembershipViewSet(InfluenceListViewSet):
    serializer_class = serializers.MembershipSerializer

    def get_queryset(self):
        queryset = models.Membership.objects.distinct('role')
        search = self.request.query_params.get('search')
        if search is not None:
            queryset = queryset.filter(role__icontains=search)
        return queryset


class ActorReceivedDonationsFromListViewSet(InfluenceListViewSet):
    serializer_class = serializers.DonationSerializer

    def get_queryset(self):
        return self.apply_filters("received_donations_from", search_field="donor__name")


class ActorDonatedToListViewSet(InfluenceListViewSet):
    serializer_class = serializers.DonationSerializer

    def get_queryset(self):
        return self.apply_filters("donated_to", search_field="recipient__name")


class ActorHasUsedAgenciesListViewSet(InfluenceListViewSet):
    serializer_class = serializers.ConsultancySerializer

    def get_queryset(self):
        return self.apply_filters("consulting_agencies", search_field="agency__name")


class ActorHasConsultedForListViewSet(InfluenceListViewSet):
    serializer_class = serializers.ConsultancySerializer

    def get_queryset(self):
        return self.apply_filters("consulting_clients", search_field="client__name")
