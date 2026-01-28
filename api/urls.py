from django.urls import path, re_path, include
from rest_framework import routers
from api import views


router = routers.SimpleRouter()

# router.register(r'actors', views.ActorViewSet)
# router.register(r'donations', views.DonationViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # API v2 - Analysis-first API with aggregates and temporal queries
    path('v2/', include('api.v2.urls')),

    # API v1 (legacy) - Keep for backwards compatibility
    path('actors', views.ActorViewSet.as_view(), name='api_actors'),
    path('politicians', views.PoliticianViewSet.as_view(), name='api_politicians'),
    path('memberships', views.MembershipViewSet.as_view(), name='api_memberships'),

    re_path(r'^actors/(?P<pk>\d+)/donations-from', views.ActorReceivedDonationsFromListViewSet.as_view(), name='api_donations_from'),
    re_path(r'^actors/(?P<pk>\d+)/donations-to', views.ActorDonatedToListViewSet.as_view(), name='api_donations_to'),

    re_path(r'^actors/(?P<pk>\d+)/consulting-agencies', views.ActorHasUsedAgenciesListViewSet.as_view(), name='api_consulting_agencies'),
    re_path(r'^actors/(?P<pk>\d+)/consulting-clients', views.ActorHasConsultedForListViewSet.as_view(), name='api_consulting_clients'),
]
