"""
URL routing for API v2
"""

from django.urls import path
from api.v2 import views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

app_name = 'api_v2'

urlpatterns = [
    # OpenAPI schema and documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api_v2:schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api_v2:schema'), name='redoc'),

    # Aggregate endpoints
    path('aggregates/stats/', views.HomepageStatsView.as_view(), name='homepage-stats'),
    path('aggregates/top-donors/', views.TopDonorsView.as_view(), name='top-donors'),
    path('aggregates/top-recipients/', views.TopRecipientsView.as_view(), name='top-recipients'),
    path('aggregates/network-stats/', views.NetworkStatsView.as_view(), name='network-stats'),
    path('aggregates/party-donations/', views.PartyDonationsView.as_view(), name='party-donations'),
    path('aggregates/dual-influence/', views.DualInfluenceView.as_view(), name='dual-influence'),
    path('aggregates/donor-concentration/', views.DonorConcentrationView.as_view(), name='donor-concentration'),
    path('aggregates/minister-network/', views.MinisterNetworkView.as_view(), name='minister-network'),

    # Actor detail endpoints
    path('actors/<int:pk>/', views.ActorDetailView.as_view(), name='actor-detail'),
    path('actors/<int:pk>/donations-made/', views.ActorDonationsMadeView.as_view(), name='actor-donations-made'),
    path('actors/<int:pk>/donations-received/', views.ActorDonationsReceivedView.as_view(), name='actor-donations-received'),
    path('actors/<int:pk>/consultancies/', views.ActorConsultanciesView.as_view(), name='actor-consultancies'),
    path('actors/<int:pk>/memberships/', views.ActorMembershipsView.as_view(), name='actor-memberships'),
]
