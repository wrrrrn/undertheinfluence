from django.conf.urls import url, include
from rest_framework import routers
from api import views


router = routers.DefaultRouter()

# router.register(r'actors', views.ActorViewSet)
# router.register(r'donations', views.DonationViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),

    url(r'^actors/(?P<pk>\d+)/donations-from', views.ActorReceivedDonationsFromListViewSet.as_view(), name='api_donations_from'),
    url(r'^actors/(?P<pk>\d+)/donations-to', views.ActorDonatedToListViewSet.as_view(), name='api_donations_to'),

    url(r'^actors/(?P<pk>\d+)/consulting-agencies', views.ActorHasUsedAgenciesListViewSet.as_view(), name='api_consulting_agencies'),
    url(r'^actors/(?P<pk>\d+)/consulting-clients', views.ActorHasConsultedForListViewSet.as_view(), name='api_consulting_clients'),
]
